"""Offline SCD2 interval regression tests: python -m unittest etl.test_scd2."""
import unittest
from datetime import date
from unittest.mock import patch,MagicMock
from etl.pipeline import sync_stores

class Result:
    def __init__(self,rows):self.rows=rows
    def mappings(self):return self
    def all(self):return self.rows
class Connection:
    def __init__(self,rows):self.rows=rows
    def execute(self,*args):return Result(self.rows)
class SCDIntervals(unittest.TestCase):
    def test_exclusive_intervals_and_separate_stores(self):
        rows=[dict(ma_cua_hang='A',ngay_hieu_luc=date(2024,1,1),khu_vuc_quan_ly='Old',ten_cua_hang='A',ten_tinh='Ha Noi'),dict(ma_cua_hang='A',ngay_hieu_luc=date(2025,7,1),khu_vuc_quan_ly='New',ten_cua_hang='A',ten_tinh='Ha Noi'),dict(ma_cua_hang='B',ngay_hieu_luc=date(2024,1,1),khu_vuc_quan_ly='South',ten_cua_hang='B',ten_tinh='Can Tho')]
        with patch('etl.pipeline.upsert_rows') as load:
            self.assertEqual(sync_stores(Connection(rows)),3)
            result=load.call_args.args[2]
        self.assertEqual(result[0]['ngay_het_han'],date(2025,7,1))
        self.assertEqual(result[1]['ngay_hieu_luc'],date(2025,7,1))
        self.assertFalse(result[0]['is_current'])
        self.assertTrue(result[1]['is_current']);self.assertTrue(result[2]['is_current'])
        self.assertEqual(result[2]['ngay_het_han'],date(9999,12,31))
        self.assertTrue(result[0]['ngay_hieu_luc']<=date(2025,6,30)<result[0]['ngay_het_han'])
        self.assertFalse(result[0]['ngay_hieu_luc']<=date(2025,7,1)<result[0]['ngay_het_han'])
    def test_conflicting_effective_date_preserves_history(self):
        from etl.demo_scd2 import change_store
        conn=MagicMock();engine=MagicMock();engine.connect.return_value.__enter__.return_value=conn
        lock=MagicMock();lock.scalar.return_value=1
        exists=MagicMock();exists.first.return_value=('CH00',)
        current=MagicMock();current.mappings.return_value.first.return_value=dict(ngay_hieu_luc=date(2025,7,1),khu_vuc_quan_ly='Metro')
        conn.execute.side_effect=[lock,exists,current,MagicMock()]
        with patch('etl.demo_scd2.get_engine',return_value=engine):
            with self.assertRaisesRegex(ValueError,'preserve history'):
                change_store('CH00','Conflicting region','2025-07-01')
        statements=[str(c.args[0]) for c in conn.execute.call_args_list]
        self.assertFalse(any(q.startswith(('INSERT','UPDATE','DELETE')) for q in statements))

if __name__=='__main__':unittest.main()
