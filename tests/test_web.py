"""Offline regressions for filter validation and SQL playground isolation."""
import unittest


class WebSafetyTests(unittest.TestCase):
    def test_select_allows_warehouse_aggregate(self):
        from mvc.models.sql_model import validate_select
        validate_select('SELECT SUM(doanh_thu) FROM fact_ban_hang', 'phone_dw')

    def test_select_rejects_unsafe_inputs(self):
        from mvc.models.sql_model import validate_select
        for sql in ['DELETE FROM fact_ban_hang', 'SELECT * FROM edu_dw.secret',
                    'SELECT SLEEP(10)', "SELECT LOAD_FILE('x')", 'SELECT 1 INTO OUTFILE \'x\'',
                    'SELECT 1; SELECT 2', 'SELECT @@version', 'SELECT * FROM mysql.user',
                    'SELECT * FROM (information_schema.tables)', 'SELECT * FROM (phone_source.don_hang)',
                    'SELECT * FROM { OJ information_schema.tables }',
                    'SELECT * FROM dim_san_pham p STRAIGHT_JOIN information_schema.tables i ON 1=1',
                    'SELECT COUNT(*) FROM dim_san_pham p JOIN dim_kenh_ban k ON EXISTS (SELECT 1 FROM dim_thoi_gian WHERE nam=2024), information_schema.tables i',
                    'SELECT /* hidden */ 1', 'SELECT GET_LOCK(\'x\',1)']:
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_select(sql, 'phone_dw')

    def test_filter_ranges(self):
        from mvc.models.olap_model import build_filters
        for filters in [{'thang': '13'}, {'quy': '0'}, {'nam': 'bad'}, {'unknown': 'x'}]:
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                build_filters(filters)
        where, params = build_filters({'thuong_hieu': "a' OR 1=1", 'thang': '1'})
        self.assertNotIn("a' OR", where)
        self.assertEqual(params['thang'], 1)


if __name__ == '__main__':
    unittest.main()
