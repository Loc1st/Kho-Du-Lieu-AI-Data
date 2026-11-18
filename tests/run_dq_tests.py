"""Database-backed phone warehouse quality checks; failures remain visible in JSON/CSV."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
from common.db import get_engine

OUTPUT = Path(__file__).resolve().parents[1] / 'output' / 'phone_sales'

def _scalar(sql):
    with get_engine('phone_dw').connect() as conn:
        return int(conn.execute(text(sql)).scalar() or 0)

def _zero(sql):
    count = _scalar(sql)
    return count == 0, {'violations': count}

def _snapshot():
    tables = ['dim_thoi_gian','dim_san_pham','dim_cua_hang','dim_khach_hang','dim_kenh_ban','dim_khuyen_mai','fact_ban_hang','fact_tra_hang']
    result = {}
    with get_engine('phone_dw').connect() as conn:
        for table in tables:
            rows = conn.execute(text(f'SELECT * FROM {table} ORDER BY 1')).fetchall()
            digest = hashlib.sha256()
            for row in rows:
                digest.update(json.dumps(list(row), default=str, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
                digest.update(b'\n')
            result[table] = {'rows': len(rows), 'sha256': digest.hexdigest()}
    return result

def _rerun():
    from etl.pipeline import run_etl
    before = _snapshot()
    run_id = run_etl(init_dw=False)
    after = _snapshot()
    return before == after, {'run_id': str(run_id), 'before': before, 'after': after}

def _foreign_keys():
    checks = []
    for dim, key in [('dim_thoi_gian','thoi_gian_key'),('dim_san_pham','san_pham_key'),('dim_cua_hang','cua_hang_key'),('dim_khach_hang','khach_hang_key'),('dim_kenh_ban','kenh_ban_key'),('dim_khuyen_mai','khuyen_mai_key')]:
        checks.append(f'(SELECT COUNT(*) FROM fact_ban_hang f LEFT JOIN {dim} d ON f.{key}=d.{key} WHERE d.{key} IS NULL)')
    checks.extend(['(SELECT COUNT(*) FROM fact_tra_hang r LEFT JOIN fact_ban_hang f ON r.ban_hang_key=f.ban_hang_key WHERE f.ban_hang_key IS NULL)', '(SELECT COUNT(*) FROM fact_tra_hang r LEFT JOIN dim_thoi_gian d ON r.thoi_gian_key=d.thoi_gian_key WHERE d.thoi_gian_key IS NULL)'])
    return _zero('SELECT ' + '+'.join(checks))

def _scd():
    sql = '''SELECT
    (SELECT COUNT(*) FROM (SELECT ma_cua_hang FROM dim_cua_hang GROUP BY ma_cua_hang HAVING SUM(is_current)<>1) x)+
    (SELECT COUNT(*) FROM dim_cua_hang WHERE ngay_hieu_luc>=ngay_het_han OR is_current<>(ngay_het_han='9999-12-31'))+
    (SELECT COUNT(*) FROM dim_cua_hang a JOIN dim_cua_hang b ON a.ma_cua_hang=b.ma_cua_hang AND a.cua_hang_key<b.cua_hang_key AND a.ngay_hieu_luc<b.ngay_het_han AND b.ngay_hieu_luc<a.ngay_het_han)+
    (SELECT COUNT(*) FROM fact_ban_hang f JOIN dim_cua_hang d ON f.cua_hang_key=d.cua_hang_key JOIN dim_thoi_gian t ON f.thoi_gian_key=t.thoi_gian_key WHERE t.ngay<d.ngay_hieu_luc OR t.ngay>=d.ngay_het_han)'''
    ok, detail = _zero(sql)
    detail['historical_versions'] = _scalar('SELECT COUNT(*) FROM dim_cua_hang WHERE is_current=0')
    return ok and detail['historical_versions'] > 0, detail

def _olap():
    from analysis.benchmark import reconcile_queries, export_olap
    rows = reconcile_queries(export=False)
    business = export_olap()
    return all(r['equal'] for r in rows + business) and len(rows) == len(business) == 5, {'benchmark_queries': rows, 'business_questions': business}

def run_tests() -> list[dict]:
    cases = [
        ('TC01 source processed accounting', _accounting),
        ('TC02 natural keys deduplicated', lambda: _zero('SELECT (SELECT COUNT(*)-COUNT(DISTINCT ma_chi_tiet) FROM fact_ban_hang)+(SELECT COUNT(*)-COUNT(DISTINCT ma_chi_tiet_tra) FROM fact_tra_hang)')),
        ('TC03 positive price and quantity', lambda: _zero('SELECT COUNT(*) FROM fact_ban_hang WHERE so_luong IS NULL OR so_luong<=0 OR don_gia IS NULL OR don_gia<=0 OR giam_gia<0 OR giam_gia>so_luong*don_gia OR gia_von<0')),
        ('TC04 fact foreign keys', _foreign_keys),
        ('TC05 revenue arithmetic', lambda: _zero('SELECT COUNT(*) FROM vw_sales_net WHERE doanh_thu<>ROUND(so_luong*don_gia-giam_gia,2) OR doanh_thu_thuan<>doanh_thu-tien_hoan')),
        ('TC06 profit and net cost arithmetic', lambda: _zero('SELECT COUNT(*) FROM vw_sales_net WHERE gia_von_thuan<>gia_von-gia_von_hoan OR loi_nhuan<>doanh_thu_thuan-gia_von_thuan')),
        ('TC07 cumulative returns bounded', lambda: _zero('SELECT (SELECT COUNT(*) FROM vw_sales_net WHERE so_luong_tra>so_luong OR tien_hoan>doanh_thu OR gia_von_hoan>gia_von)+(SELECT COUNT(*) FROM fact_tra_hang WHERE so_luong_tra<=0 OR tien_hoan<0 OR gia_von_hoan<0)')),
        ('TC08 SCD2 intervals and historical keys', _scd),
        ('TC09 actual ETL rerun preserves every key/value', _rerun),
        ('TC10 five OLAP source/DW reconciliations', _olap),
    ]
    results = []
    for name, check in cases:
        try:
            passed, detail = check()
            results.append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'detail': detail})
        except Exception as exc:
            results.append({'name': name, 'status': 'FAIL', 'detail': {'error': str(exc)}})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT/'test_cases_result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    with (OUTPUT/'test_cases_result.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['name','status','detail'])
        writer.writeheader()
        writer.writerows({**r, 'detail': json.dumps(r['detail'], ensure_ascii=False, default=str)} for r in results)
    return results

def _accounting():
    with get_engine('phone_source').connect() as src, get_engine('phone_dw').connect() as dw:
        def count(conn, sql, params=None):
            return int(conn.execute(text(sql), params or {}).scalar() or 0)
        source_orders = count(src, 'SELECT COUNT(*) FROM don_hang')
        completed = count(src, "SELECT COUNT(*) FROM chi_tiet_don_hang c JOIN don_hang d ON c.ma_don_hang=d.ma_don_hang WHERE d.trang_thai<>'CANCELLED'")
        cancelled = count(src, "SELECT COUNT(*) FROM chi_tiet_don_hang c JOIN don_hang d ON c.ma_don_hang=d.ma_don_hang WHERE d.trang_thai='CANCELLED'")
        returns = count(src, 'SELECT COUNT(*) FROM chi_tiet_tra_hang')
        raw = count(src, 'SELECT COUNT(*) FROM raw_import_error')
        sales_fact = count(dw, 'SELECT COUNT(*) FROM fact_ban_hang')
        return_fact = count(dw, 'SELECT COUNT(*) FROM fact_tra_hang')
        latest = dw.execute(text("SELECT run_id FROM etl_log WHERE status='SUCCESS' ORDER BY log_id DESC LIMIT 1")).scalar()
        if not latest:
            return False, {'error': 'No completed ETL audit available'}
        rejects = count(dw, 'SELECT COUNT(*) FROM etl_reject WHERE run_id=:r', {'r': latest})
        audit = [dict(row) for row in dw.execute(text('SELECT bang,so_dong_doc,so_dong_nap,so_dong_loai FROM etl_log WHERE run_id=:r'), {'r': latest}).mappings()]
        balances = all(row['so_dong_doc'] == row['so_dong_nap'] + row['so_dong_loai'] for row in audit)
        tracked = {row['bang']: row for row in audit}
        expected_reads = {'fact_ban_hang': completed+cancelled, 'fact_tra_hang': returns, 'raw_import_error': raw}
        reads_match = all(table in tracked and tracked[table]['so_dong_doc'] == n for table,n in expected_reads.items())
        detail = {'run_id': latest, 'source_orders': source_orders, 'completed_lines': completed,
                  'cancelled_lines': cancelled, 'source_returns': returns, 'raw_invalid': raw,
                  'sale_facts': sales_fact, 'return_facts': return_fact, 'latest_rejects': rejects, 'audit': audit}
        # Every extracted row must have a visible final disposition. Cancelled rows
        # are excluded from the sale fact and retained in per-run rejection audit.
        passed = (source_orders >= 50000 and completed == sales_fact and returns == return_fact
                  and balances and reads_match
                  and completed + cancelled + returns + raw == sales_fact + return_fact + rejects)
        return passed, detail

def main() -> int:
    results = run_tests()
    for row in results:
        print(f"{row['status']} {row['name']}: {json.dumps(row['detail'], ensure_ascii=False, default=str)}")
    return int(any(row['status'] != 'PASS' for row in results))

if __name__ == '__main__':
    raise SystemExit(main())
