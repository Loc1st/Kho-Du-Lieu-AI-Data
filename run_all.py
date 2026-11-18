"""Safe orchestration for the phone sales warehouse; preserves legacy databases."""
from __future__ import annotations
import argparse
from sqlalchemy import text
from common.db import get_engine, run_sql_file, SQL_DIR

def _initialize():
    engine=get_engine()
    for name in ['01_create_source_db.sql','02_create_dw.sql','03_procedures.sql','04_olap_views.sql']:
        run_sql_file(engine, SQL_DIR/name)

def _populated():
    with get_engine('phone_source').connect() as conn:
        return int(conn.execute(text('SELECT COUNT(*) FROM don_hang')).scalar())>=50000

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',nargs='?',default='all',choices=['init','generate','etl','scd2','tests','olap','benchmark','all'])
    parser.add_argument('--orders',type=int,default=60000)
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--reset',action='store_true')
    parser.add_argument('--confirm-reset')
    args=parser.parse_args(argv)
    if args.orders<50000:
        parser.error('--orders must be at least 50000')
    if args.reset and args.confirm_reset!='phone-sales':
        parser.error('reset requires --reset --confirm-reset phone-sales')
    if args.confirm_reset and not args.reset:
        parser.error('--confirm-reset requires --reset')
    if args.reset:
        with get_engine().begin() as conn:
            # Literal allowlist: never use names supplied by environment or CLI.
            conn.execute(text('DROP DATABASE IF EXISTS phone_dw'))
            conn.execute(text('DROP DATABASE IF EXISTS phone_source'))
    if args.mode in ('init','generate','all') or args.reset:
        _initialize()
    if args.mode=='init':
        return 0
    if args.mode=='generate' or (args.mode=='all' and not _populated()):
        from generator.generate_data import main as generate
        generate(['--orders',str(args.orders),'--seed',str(args.seed)])
    if args.mode in ('etl','all'):
        from etl.pipeline import run_etl
        print('ETL run:',run_etl(init_dw=False))
    if args.mode in ('scd2','all'):
        from etl.demo_scd2 import main as demo
        demo()
    rc=0
    if args.mode in ('tests','all'):
        from tests.run_dq_tests import main as tests
        rc=max(rc,tests())
    if args.mode in ('olap','all'):
        from analysis.benchmark import export_olap
        rows=export_olap()
        print(rows)
        rc=max(rc,int(any(not row['equal'] for row in rows)))
    if args.mode in ('benchmark','all'):
        from analysis.benchmark import main as benchmark
        rc=max(rc,benchmark())
    return rc

if __name__=='__main__':
    raise SystemExit(main())
