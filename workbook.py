"""Lossless .xlsx mapping: one contact per row, one method per indexed column."""
from io import BytesIO
import re
from zipfile import ZipFile, BadZipFile
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from model import TYPES, normalize

BASE = ['姓名', '分组', '收藏', '备注']
HEADER = re.compile(r'^(电话|邮箱|微信|QQ|地址|其他)([1-9][0-9]*)_(标签|值)$')


def export_xlsx(contacts):
    counts = {kind: max([sum(m['type'] == kind for m in c['methods'])
                         for c in contacts] + [1]) for kind in TYPES}
    headers = BASE + [f'{kind}{i}_{field}' for kind in TYPES
                      for i in range(1, counts[kind] + 1) for field in ('标签', '值')]
    wb = Workbook()
    ws = wb.active
    ws.title = '通讯录'
    ws.append(headers)
    for contact in contacts:
        row = [contact['name'], contact['group'], '是' if contact['favorite'] else '否', contact['note']]
        for kind in TYPES:
            methods = [m for m in contact['methods'] if m['type'] == kind]
            for i in range(counts[kind]):
                row += [methods[i]['label'], methods[i]['value']] if i < len(methods) else ['', '']
        ws.append(row)
    # Strings remain text, including leading zeroes and values starting with '='.
    for row in ws:
        for cell in row:
            cell.data_type = 's'
            cell.number_format = '@'
    for cell in ws[1]:
        cell.font = Font(color='FFFFFF', bold=True)
        cell.fill = PatternFill('solid', fgColor='24584B')
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 24
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def import_xlsx(raw):
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('Excel 文件不能超过 5 MB')
    try:
        with ZipFile(BytesIO(raw)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 30 * 1024 * 1024:
                raise ValueError('Excel 解压后不能超过 30 MB')
        wb = load_workbook(BytesIO(raw), read_only=True, data_only=False)
    except (BadZipFile, OSError, KeyError) as exc:
        raise ValueError('请导入有效的 .xlsx 文件') from exc
    try:
        if '通讯录' not in wb.sheetnames:
            raise ValueError('缺少“通讯录”工作表，请使用下载的模板')
        ws = wb['通讯录']
        if ws.max_row > 1001 or ws.max_column > 604:
            raise ValueError('最多导入 1000 人、604 列')
        rows = ws.iter_rows()
        header_cells = next(rows, ())
        headers = [c.value for c in header_cells]
        if len(headers) != len(set(headers)):
            raise ValueError('表头重复')
        if headers[:4] != BASE:
            raise ValueError('前四列表头须依次为：姓名、分组、收藏、备注')
        mapping = []
        for column in headers[4:]:
            match = HEADER.fullmatch(str(column))
            if not match or int(match[2]) > 50:
                raise ValueError(f'无法识别的表头：{column}')
            mapping.append(match.groups())
        pairs = {(kind, index, field) for kind, index, field in mapping}
        if any((k, i, '标签') not in pairs or (k, i, '值') not in pairs
               for k, i, _ in mapping):
            raise ValueError('每条联系方式需要同时保留“标签”和“值”两列')
        contacts = []
        for number, cells in enumerate(rows, 2):
            if all(c.value is None for c in cells):
                continue
            if any(c.data_type == 'f' for c in cells):
                raise ValueError(f'第 {number} 行包含公式，请转换为文本')
            values = ['' if c.value is None else str(c.value) for c in cells]
            if values[2] not in ('是', '否', ''):
                raise ValueError(f'第 {number} 行收藏须为“是”或“否”')
            methods = {}
            for (kind, index, field), value in zip(mapping, values[4:]):
                methods.setdefault((kind, index), dict(type=kind, label='', value=''))[
                    'label' if field == '标签' else 'value'] = value
            if any(m['label'] and not m['value'] for m in methods.values()):
                raise ValueError(f'第 {number} 行存在只有标签、没有值的联系方式')
            try:
                contacts.append(normalize(dict(name=values[0], group=values[1],
                    favorite=values[2] == '是', note=values[3],
                    methods=[m for m in methods.values() if m['value']])))
            except ValueError as exc:
                raise ValueError(f'第 {number} 行：{exc}') from exc
        return contacts
    finally:
        wb.close()
