"""Equivalent source/warehouse OLAP with measured repetitions and equality evidence."""
from __future__ import annotations
import csv
import json
import statistics
import time
from pathlib import Path
from sqlalchemy import text
from common.db import get_engine

OUTPUT = Path(__file__).resolve().parents[1] / 'output' / 'phone_sales'
SOURCE_BASE = '''SELECT ct.ma_don_hang, dh.ngay_dat AS ngay, ct.ma_sku, dh.ma_cua_hang,
 dh.ma_kenh, ct.ma_khuyen_mai, ct.so_luong,ct.so_luong*ct.don_gia-ct.giam_gia AS doanh_thu,
 COALESCE(r.so_luong_tra,0) AS so_luong_tra,
 ct.so_luong*ct.don_gia-ct.giam_gia-COALESCE(r.tien_hoan,0) AS doanh_thu_thuan,
 ct.gia_von-COALESCE(r.gia_von_hoan,0) AS gia_von_thuan,
 ct.so_luong*ct.don_gia-ct.giam_gia-COALESCE(r.tien_hoan,0)-ct.gia_von+COALESCE(r.gia_von_hoan,0) AS loi_nhuan
 FROM chi_tiet_don_hang ct JOIN don_hang dh ON ct.ma_don_hang=dh.ma_don_hang
 LEFT JOIN (SELECT rt.ma_chi_tiet,SUM(rt.so_luong_tra) so_luong_tra,SUM(rt.tien_hoan) tien_hoan,
 SUM(ROUND(c.gia_von*rt.so_luong_tra/c.so_luong,2)) gia_von_hoan
 FROM chi_tiet_tra_hang rt JOIN chi_tiet_don_hang c ON rt.ma_chi_tiet=c.ma_chi_tiet
 GROUP BY rt.ma_chi_tiet) r ON ct.ma_chi_tiet=r.ma_chi_tiet WHERE dh.trang_thai<>'CANCELLED' '''
DW_BASE = '''SELECT f.ma_don_hang,t.ngay,p.ma_sku,c.ma_cua_hang,k.ma_kenh,m.ma_khuyen_mai,
 f.so_luong,f.doanh_thu,f.so_luong_tra,f.doanh_thu_thuan,f.gia_von_thuan,f.loi_nhuan
 FROM vw_sales_net f JOIN dim_thoi_gian t ON f.thoi_gian_key=t.thoi_gian_key
 JOIN dim_san_pham p ON f.san_pham_key=p.san_pham_key
 JOIN dim_cua_hang c ON f.cua_hang_key=c.cua_hang_key
 JOIN dim_kenh_ban k ON f.kenh_ban_key=k.kenh_ban_key
 JOIN dim_khuyen_mai m ON f.khuyen_mai_key=m.khuyen_mai_key'''
# All monetary sums remain DECIMAL; grouping on business keys survives SCD versions.
GROUPS = [('Q1_month','YEAR(ngay),MONTH(ngay)'),('Q2_sku','ma_sku'),('Q3_store','ma_cua_hang'),('Q4_channel','ma_kenh'),('Q5_promotion','ma_khuyen_mai')]
METRICS = '''COUNT(DISTINCT ma_don_hang) orders, SUM(so_luong) sold_units,
 SUM(so_luong_tra) returned_units,SUM(doanh_thu_thuan) net_revenue,
 SUM(gia_von_thuan) net_cost,SUM(loi_nhuan) gross_profit,
 ROUND(SUM(doanh_thu_thuan)/NULLIF(COUNT(DISTINCT ma_don_hang),0),2) aov,
 ROUND(SUM(so_luong_tra)/NULLIF(SUM(so_luong),0),6) return_rate'''
BENCHMARK_QUERIES = [(name, f'SELECT {group},{METRICS} FROM ({SOURCE_BASE}) n GROUP BY {group} ORDER BY {group}', f'SELECT {group},{METRICS} FROM ({DW_BASE}) n GROUP BY {group} ORDER BY {group}') for name,group in GROUPS]

def _fetch(conn, sql):
    result = conn.execute(text(sql))
    return list(result.keys()), [tuple(row) for row in result.fetchall()]

def reconcile_queries(export=True):
    rows = []
    if export:
        OUTPUT.mkdir(parents=True,exist_ok=True)
    with get_engine('phone_source').connect() as src, get_engine('phone_dw').connect() as dw:
        for name, source_sql, dw_sql in BENCHMARK_QUERIES:
            _, expected = _fetch(src, source_sql)
            columns, actual = _fetch(dw, dw_sql)
            rows.append({'name': name,'equal': expected == actual,'source_rows': len(expected),'dw_rows': len(actual)})
            if export:
                with (OUTPUT / f'benchmark_query_{name}.csv').open('w',newline='',encoding='utf-8-sig') as file:
                    writer=csv.writer(file); writer.writerow(columns); writer.writerows(actual)
    return rows

# Required management questions, distinct from the five benchmark grains.
SOURCE_BUSINESS = f"""SELECT n.*,p.ten_san_pham,b.ten_thuong_hieu thuong_hieu,k.ten_kenh,
 h.khu_vuc_quan_ly,t.ten_tinh tinh_thanh,c.ten_cua_hang
 FROM ({SOURCE_BASE}) n JOIN phien_ban_san_pham v ON n.ma_sku=v.ma_sku
 JOIN san_pham p ON p.ma_san_pham=v.ma_san_pham
 JOIN thuong_hieu b ON b.ma_thuong_hieu=p.ma_thuong_hieu
 JOIN kenh_ban k ON k.ma_kenh=n.ma_kenh
 JOIN cua_hang c ON c.ma_cua_hang=n.ma_cua_hang JOIN tinh_thanh t ON t.ma_tinh=c.ma_tinh
 JOIN lich_su_cua_hang h ON h.ma_cua_hang=n.ma_cua_hang AND h.ngay_hieu_luc<=n.ngay
 WHERE NOT EXISTS (SELECT 1 FROM lich_su_cua_hang newer WHERE newer.ma_cua_hang=h.ma_cua_hang
 AND newer.ngay_hieu_luc>h.ngay_hieu_luc AND newer.ngay_hieu_luc<=n.ngay)"""
DW_BUSINESS = f"""SELECT n.*,p.ten_san_pham,p.thuong_hieu,k.ten_kenh,
 c.khu_vuc_quan_ly,c.tinh_thanh,c.ten_cua_hang
 FROM ({DW_BASE}) n JOIN dim_san_pham p ON p.ma_sku=n.ma_sku
 JOIN dim_kenh_ban k ON k.ma_kenh=n.ma_kenh
 JOIN dim_cua_hang c ON c.ma_cua_hang=n.ma_cua_hang AND n.ngay>=c.ngay_hieu_luc AND n.ngay<c.ngay_het_han"""
BUSINESS_GROUPS = [
 ('business_Q1_brand_model','thuong_hieu,ten_san_pham',True),
 ('business_Q2_year_quarter_month','YEAR(ngay),QUARTER(ngay),MONTH(ngay)',True),
 ('business_Q3_brand_channel','thuong_hieu,ten_kenh',True),
 ('business_Q4_sku_month_price_quantity','ma_sku,YEAR(ngay),MONTH(ngay)',False),
 ('business_Q5_region_store','khu_vuc_quan_ly,tinh_thanh,ma_cua_hang,ten_cua_hang',True),
]
BUSINESS_QUERIES = []
for name,group,rollup in BUSINESS_GROUPS:
    metrics = METRICS
    if name=='business_Q4_sku_month_price_quantity':
        metrics += ',ROUND(SUM(doanh_thu)/NULLIF(SUM(so_luong),0),2) average_sale_price'
    tail = f' GROUP BY {group}' + (' WITH ROLLUP' if rollup else '')
    BUSINESS_QUERIES.append((name,f'SELECT {group},{metrics} FROM ({SOURCE_BUSINESS}) n'+tail,
                            f'SELECT {group},{metrics} FROM ({DW_BUSINESS}) n'+tail))

def reconcile_business_queries(export=True):
    results=[]
    if export: OUTPUT.mkdir(parents=True,exist_ok=True)
    with get_engine('phone_source').connect() as src,get_engine('phone_dw').connect() as dw:
        for name,source_sql,dw_sql in BUSINESS_QUERIES:
            _,expected=_fetch(src,source_sql); columns,actual=_fetch(dw,dw_sql)
            # ROLLUP guarantees subtotals, not a shared source/DW physical ordering.
            normalize=lambda rows: sorted(rows,key=lambda row: tuple('' if v is None else str(v) for v in row))
            equal=normalize(expected)==normalize(actual)
            results.append({'name':name,'equal':equal,'source_rows':len(expected),'dw_rows':len(actual)})
            if export:
                with (OUTPUT/f'olap_{name}.csv').open('w',newline='',encoding='utf-8-sig') as file:
                    writer=csv.writer(file);writer.writerow(columns);writer.writerows(actual)
    return results

def export_olap():
    rows=reconcile_business_queries(export=True)
    (OUTPUT/'olap_reconciliation.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return rows

def _measure(conn, sql, repeat):
    _fetch(conn,sql)  # One untimed warmup; fetch is included in every measurement.
    elapsed=[]
    for _ in range(repeat):
        start=time.perf_counter(); _fetch(conn,sql)
        elapsed.append((time.perf_counter()-start)*1000)
    return elapsed

def main(repeat=5) -> int:
    if repeat<2:
        raise ValueError('benchmark requires at least two repetitions')
    export_olap(); reconciled=reconcile_queries(export=True); rows=[]
    with get_engine('phone_source').connect() as src, get_engine('phone_dw').connect() as dw:
        for (name, source_sql, dw_sql), check in zip(BENCHMARK_QUERIES,reconciled):
            a=_measure(src,source_sql,repeat); b=_measure(dw,dw_sql,repeat)
            rows.append({'name': name, 'equal': check['equal'], 'repeat': repeat,
                         'source_ms_median': statistics.median(a),'dw_ms_median': statistics.median(b),
                         'source_over_dw': statistics.median(a)/statistics.median(b),
                         'source_samples_ms': json.dumps(a),'dw_samples_ms': json.dumps(b)})
    with (OUTPUT/'benchmark_result.csv').open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for row in rows:
        print(json.dumps(row))
    return int(any(not r['equal'] for r in rows))

if __name__=='__main__':
    raise SystemExit(main())
