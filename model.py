"""Contact validation and transactional SQLite persistence."""
import json
import sqlite3
import uuid
from contextlib import contextmanager

TYPES = ('电话', '邮箱', '微信', 'QQ', '地址', '其他')


def normalize(contact):
    if not isinstance(contact, dict):
        raise ValueError('联系人必须为对象')
    name = str(contact.get('name', '')).strip()
    if not name or len(name) > 80:
        raise ValueError('姓名必填，最多 80 字')
    methods = contact.get('methods', [])
    if not isinstance(methods, list) or not 1 <= len(methods) <= 50:
        raise ValueError('每位联系人须有 1 至 50 条联系方式')
    cleaned, seen = [], set()
    for item in methods:
        if not isinstance(item, dict):
            raise ValueError('联系方式格式错误')
        kind = str(item.get('type', '')).strip()
        label = str(item.get('label', '')).strip()
        value = str(item.get('value', '')).strip()
        if kind not in TYPES or not value or len(value) > 500 or len(label) > 40:
            raise ValueError('联系方式类型、标签或内容不符合要求')
        if kind == '邮箱' and ('@' not in value or ' ' in value):
            raise ValueError('邮箱须包含 @ 且不含空格')
        key = (kind, label, value)
        if key not in seen:
            cleaned.append(dict(type=kind, label=label, value=value))
            seen.add(key)
    favorite = contact.get('favorite', False)
    if not isinstance(favorite, bool):
        raise ValueError('收藏状态必须为布尔值')
    group = str(contact.get('group', '')).strip()
    note = str(contact.get('note', '')).strip()
    if len(group) > 80 or len(note) > 2000:
        raise ValueError('分组最多 80 字，备注最多 2000 字')
    return dict(name=name, group=group, note=note, favorite=favorite, methods=cleaned)


class Store:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS contacts '
                       '(id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def all(self):
        with self.connect() as db:
            rows = db.execute('SELECT id, data FROM contacts ORDER BY rowid DESC').fetchall()
        return [dict(id=key, **json.loads(value)) for key, value in rows]

    def save(self, contact, key=None):
        data = normalize(contact)
        with self.connect() as db:
            if key:
                updated = db.execute('UPDATE contacts SET data=? WHERE id=?',
                                     (json.dumps(data, ensure_ascii=False), key))
                if not updated.rowcount:
                    raise KeyError('联系人不存在')
            else:
                key = str(uuid.uuid4())
                db.execute('INSERT INTO contacts VALUES (?,?)',
                           (key, json.dumps(data, ensure_ascii=False)))
        return dict(id=key, **data)

    def delete(self, key):
        with self.connect() as db:
            if not db.execute('DELETE FROM contacts WHERE id=?', (key,)).rowcount:
                raise KeyError('联系人不存在')

    def import_all(self, contacts):
        # Validate the entire workbook before any write. Import always appends;
        # names are not unique identifiers and never trigger silent overwrites.
        data = [normalize(c) for c in contacts]
        with self.connect() as db:
            db.executemany('INSERT INTO contacts VALUES (?,?)',
                           [(str(uuid.uuid4()), json.dumps(c, ensure_ascii=False)) for c in data])
        return len(data)
