from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import Store, normalize
from workbook import export_xlsx, import_xlsx


def sample(**values):
    return dict(name='林同学（虚构）', group='同学', note='课程演示', favorite=False,
                methods=[dict(type='电话', label='宿舍', value='00123456789'),
                         dict(type='邮箱', label='学习', value='demo@example.com')], **values)


class AddressBookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.db')
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_favorite_survives_reopen(self):
        saved = self.store.save(sample())
        saved['favorite'] = True
        self.store.save(saved, saved['id'])
        self.assertTrue(Store(self.path).all()[0]['favorite'])

    def test_update_and_delete(self):
        saved = self.store.save(sample())
        saved['name'] = '新名字'
        self.store.save(saved, saved['id'])
        self.assertEqual(self.store.all()[0]['name'], '新名字')
        self.store.delete(saved['id'])
        self.assertEqual(self.store.all(), [])
        with self.assertRaises(KeyError):
            self.store.delete(saved['id'])

    def test_multiple_methods_roundtrip(self):
        contact = sample()
        contact['favorite'] = True
        contact['methods'] += [dict(type='电话', label='备用', value='0000123'),
                               dict(type='微信', label='个人', value='demo;with|delimiters'),
                               dict(type='地址', label='通信', value='示例楼\n二层'),
                               dict(type='其他', label='测试', value='=1+1')]
        output = import_xlsx(export_xlsx([contact]))
        self.assertEqual(output[0]['name'], contact['name'])
        self.assertTrue(output[0]['favorite'])
        self.assertEqual({tuple(m.items()) for m in output[0]['methods']},
                         {tuple(m.items()) for m in contact['methods']})

    def test_one_row_per_contact_and_text_cells(self):
        raw = export_xlsx([sample(), sample()])
        wb = load_workbook(BytesIO(raw))
        ws = wb.active
        self.assertEqual(ws.max_row, 3)
        self.assertEqual(ws['F2'].value, '00123456789')
        self.assertEqual(ws['F2'].data_type, 's')
        wb.close()

    def test_empty_template(self):
        self.assertEqual(import_xlsx(export_xlsx([])), [])

    def test_bad_header(self):
        wb = load_workbook(BytesIO(export_xlsx([sample()])))
        wb.active['A1'] = '错误'
        raw = BytesIO(); wb.save(raw); wb.close()
        with self.assertRaisesRegex(ValueError, '表头'):
            import_xlsx(raw.getvalue())

    def test_formula_is_rejected(self):
        wb = load_workbook(BytesIO(export_xlsx([sample()])))
        wb.active['A2'] = '=1+1'
        raw = BytesIO(); wb.save(raw); wb.close()
        with self.assertRaisesRegex(ValueError, '公式'):
            import_xlsx(raw.getvalue())

    def test_import_is_atomic(self):
        invalid = sample(); invalid['name'] = ''
        with self.assertRaises(ValueError):
            self.store.import_all([sample(), invalid])
        self.assertEqual(self.store.all(), [])

    def test_import_appends_same_name(self):
        self.store.save(sample())
        self.assertEqual(self.store.import_all([sample()]), 1)
        contacts = self.store.all()
        self.assertEqual(len(contacts), 2)
        self.assertNotEqual(contacts[0]['id'], contacts[1]['id'])

    def test_input_validation(self):
        for key, value in [('name', ''), ('favorite', 'yes'), ('methods', []), ('group', 'x' * 81)]:
            data = sample(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                normalize(data)

    def test_broken_file(self):
        with self.assertRaises(ValueError):
            import_xlsx(b'not excel')

    def test_label_without_value_is_rejected(self):
        wb = load_workbook(BytesIO(export_xlsx([sample()])))
        wb.active['F2'] = ''
        raw = BytesIO(); wb.save(raw); wb.close()
        with self.assertRaisesRegex(ValueError, '只有标签'):
            import_xlsx(raw.getvalue())


if __name__ == '__main__':
    unittest.main()
