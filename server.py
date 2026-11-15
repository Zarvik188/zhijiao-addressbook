"""Local single-user address book. Run: python server.py"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
import json
import os
from model import Store
from workbook import export_xlsx, import_xlsx

ROOT = Path(__file__).resolve().parent
store = Store(os.environ.get('CONTACTS_DB', str(ROOT / 'contacts.db')))


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, mime='application/json; charset=utf-8'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def handle_api(self):
        path = urlsplit(self.path).path
        # Local API is same-origin only. Do not expose this demo publicly.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.send(403, {'error': '不允许跨站请求'})
        try:
            if self.command == 'GET':
                if path == '/api/contacts':
                    return self.send(200, store.all())
                if path in ('/api/export', '/api/template'):
                    return self.send(200, export_xlsx(store.all() if path.endswith('export') else []),
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                files = {'/': ('index.html', 'text/html; charset=utf-8'),
                         '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                         '/style.css': ('style.css', 'text/css; charset=utf-8')}
                if path in files:
                    file, mime = files[path]
                    return self.send(200, (ROOT / 'static' / file).read_bytes(), mime)
            size = int(self.headers.get('Content-Length', 0))
            if size < 0 or size > 5 * 1024 * 1024:
                return self.send(413, {'error': '请求不能超过 5 MB'})
            if self.command == 'POST' and path == '/api/import':
                contacts = import_xlsx(self.rfile.read(size))
                return self.send(200, {'imported': store.import_all(contacts)})
            if self.command in ('POST', 'PUT') and (path == '/api/contacts' or path.startswith('/api/contacts/')):
                if self.command == 'POST' and path != '/api/contacts':
                    return self.send(404, {'error': '接口不存在'})
                key = path.split('/')[-1] if self.command == 'PUT' else None
                data = json.loads(self.rfile.read(size))
                return self.send(200, store.save(data, key))
            if self.command == 'DELETE' and path.startswith('/api/contacts/'):
                store.delete(path.split('/')[-1])
                return self.send(200, {'deleted': True})
            return self.send(404, {'error': '页面或接口不存在'})
        except KeyError:
            return self.send(404, {'error': '联系人不存在'})
        except (ValueError, TypeError) as exc:
            return self.send(400, {'error': str(exc)})
        except Exception:
            return self.send(400, {'error': '文件格式无法读取，请使用提供的 Excel 模板'})

    do_GET = do_POST = do_PUT = do_DELETE = handle_api


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5188))
    print(f'Address Book: http://127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
