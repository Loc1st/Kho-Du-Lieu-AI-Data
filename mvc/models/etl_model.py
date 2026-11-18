"""ETL audit data read from the database; benchmark/test artifacts are measured results."""
import json
import csv
from pathlib import Path
from common.db import OUTPUT_DIR
from mvc.models.base import dw_engine,query_records

def artifact(name,default):
    path=Path(OUTPUT_DIR)/'phone_sales'/name
    if not path.exists():return default
    if path.suffix=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    return json.loads(path.read_text(encoding='utf8'))

def get_etl_and_quality_data():
    latest=query_records(dw_engine,"SELECT run_id FROM etl_log ORDER BY log_id DESC LIMIT 1")
    run=latest[0]['run_id'] if latest else ''
    return {'run_id':run,
      'logs':query_records(dw_engine,'SELECT * FROM etl_log WHERE run_id=:r ORDER BY log_id',{'r':run}),
      'quality':query_records(dw_engine,'SELECT * FROM etl_data_quality WHERE run_id=:r ORDER BY dq_id',{'r':run}),
      'rejects':query_records(dw_engine,'SELECT reject_id,bang,source_id,reason FROM etl_reject WHERE run_id=:r ORDER BY reject_id LIMIT 100',{'r':run}),
      'reject_summary':query_records(dw_engine,'SELECT reason,COUNT(*) so_dong FROM etl_reject WHERE run_id=:r GROUP BY reason',{'r':run}),
      'tests':artifact('test_cases_result.json',[]),'benchmark':artifact('benchmark_result.csv',[])}

def execute_test_suite():
    from tests.run_dq_tests import run_tests
    return run_tests()
