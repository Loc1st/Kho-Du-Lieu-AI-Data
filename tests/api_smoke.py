"""Live HTTP verification. Run after web_app.py; no reset or fixture generation.

--run-tests executes the real 10-case suite through the HTTP endpoint.
The SCD requests reuse an existing historical boundary and preserve data.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-tests', action='store_true')
    args = parser.parse_args()
    results = []
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf8')
        req = urllib.request.Request('http://127.0.0.1:8050' + path, data=data,
                                     headers={'Content-Type': 'application/json'})
        started = time.perf_counter()
        try:
            response = opener.open(req, timeout=300)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            content_type = response.headers.get('Content-Type', '')
            body = json.loads(raw) if 'application/json' in content_type else raw
            return response.status, body, round((time.perf_counter()-started)*1000, 2)

    def check(name, fn):
        try:
            detail = fn()
            results.append({'name': name, 'status': 'PASS', 'detail': detail})
        except Exception as exc:
            results.append({'name': name, 'status': 'FAIL', 'detail': str(exc)})

    def get_json(path, keys):
        status, data, elapsed = request(path)
        assert status == 200, (status, data)
        assert all(key in data for key in keys), data
        return {'http': status, 'elapsed_ms': elapsed, 'keys': list(data)}

    def assets():
        details = {}
        for path in ['/', '/app.js', '/vendor/chart.umd.min.js']:
            code, body, elapsed = request(path)
            assert code == 200 and len(body) > 100
            details[path] = {'http': code, 'bytes': len(body), 'elapsed_ms': elapsed}
        return details

    def overview():
        code, data, elapsed = request('/api/overview')
        assert code == 200 and data['kpi']['so_don_hang'] > 0
        chart_keys = ['top_models', 'monthly', 'brand_channel', 'scatter', 'brand_trend', 'regions']
        assert all(len(data[key]) > 0 for key in chart_keys)
        assert data['kpi']['doanh_thu_thuan'] == data['kpi']['doanh_thu_ban']-data['kpi']['tien_hoan']
        return {'http': code, 'elapsed_ms': elapsed, 'kpi': data['kpi'],
                'chart_rows': {key: len(data[key]) for key in chart_keys}}

    def filtered():
        code, data, _ = request('/api/overview?nam=2025&quy=1&thuong_hieu=Apple&ma_kenh=WEB')
        assert code == 200 and data['kpi']['so_don_hang'] > 0
        assert all(row['thang'].startswith('2025-0') and int(row['thang'][-2:]) <= 3 for row in data['monthly'])
        assert all(row['thuong_hieu'] == 'Apple' for row in data['top_models'])
        assert all(row['ten_kenh'] == 'Website' for row in data['brand_channel'])
        return {'orders': data['kpi']['so_don_hang'], 'months': [r['thang'] for r in data['monthly']]}

    def empty():
        code, data, _ = request('/api/overview?nam=2001')
        assert code == 200 and data['kpi']['so_don_hang'] == 0 and not data['monthly']
        return {'http': code, 'orders': 0}

    def scd():
        code, detail, _ = request('/api/store?ma_cua_hang=CH00')
        assert code == 200 and detail['history']
        history = detail['history']
        row = history[-1]
        payload = {'ma_cua_hang': 'CH00', 'khu_vuc': row['khu_vuc_quan_ly'],
                   'ngay_hieu_luc': row['ngay_hieu_luc']}
        for _ in range(2):
            code, data, _ = request('/api/scd2_change', payload)
            assert code == 200 and data['change']['changed'] is False
            assert len(data['history']) == len(history)
        code, data, _ = request('/api/scd2_change', {**payload, 'khu_vuc': 'Conflicting region'})
        assert code == 400 and data['error']
        return {'versions': len(history), 'repeated_change': False, 'conflict_http': code}

    def sql():
        detail = {}
        for db, query in [('phone_dw', 'SELECT COUNT(*) n FROM fact_ban_hang'),
                          ('phone_source', 'SELECT COUNT(*) n FROM don_hang')]:
            code, data, _ = request('/api/sql', {'database': db, 'sql': query})
            assert code == 200 and data['rows'][0]['n'] > 0 and data['elapsed_ms'] >= 0
            detail[db] = data
        code, data, _ = request('/api/sql', {'database': 'phone_dw', 'sql': 'SELECT * FROM fact_ban_hang'})
        assert code == 200 and len(data['rows']) == 500 and data['truncated']
        detail['row_limit'] = len(data['rows'])
        return detail

    def bad_requests():
        code, data, _ = request('/api/overview?thang=13')
        assert code == 400 and data['error']
        code, data, _ = request('/api/missing')
        assert code == 404 and data['error']
        code, data, _ = request('/api/sql', {'database': 'phone_dw', 'sql': 'DELETE FROM fact_ban_hang'})
        assert code == 400 and data['error']
        return {'invalid_filter': 400, 'missing_endpoint': 404, 'write_query': 400}

    def tests():
        code, data, elapsed = request('/api/run_tests', {})
        assert code == 200 and len(data['tests']) == 10
        assert all(row['status'] == 'PASS' for row in data['tests']), data
        return {'http': code, 'elapsed_ms': elapsed, 'passed': 10}

    check('local HTML and JavaScript assets', assets)
    check('filter options', lambda: get_json('/api/filters', ['nam', 'thuong_hieu', 'ma_kenh']))
    check('real KPI and six chart payloads', overview)
    check('combined filters', filtered)
    check('empty result', empty)
    check('store search', lambda: get_json('/api/search_store?q=CH00', []))
    check('SCD repeat and collision preservation', scd)
    check('ETL audit endpoint', lambda: get_json('/api/etl', ['logs', 'quality', 'rejects', 'tests', 'benchmark']))
    check('SELECT both databases and row limit', sql)
    check('clear HTTP validation errors', bad_requests)
    if args.run_tests:
        check('real 10-case suite through POST API', tests)
    else:
        results.append({'name': 'real 10-case suite through POST API', 'status': 'SKIP',
                        'detail': 'Enable --run-tests to execute the ETL rerun through HTTP.'})
    out = Path(__file__).resolve().parents[1]/'output'/'phone_sales'
    out.mkdir(parents=True, exist_ok=True)
    (out/'api_smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    for row in results:
        print(row['status'], row['name'])
    return int(any(row['status'] == 'FAIL' for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
