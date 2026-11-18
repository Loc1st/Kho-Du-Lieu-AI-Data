"""Check configured MariaDB and phone schema connectivity without printing secrets."""
from sqlalchemy import text
from common.db import get_engine,SOURCE_DB,DW_DB

def main():
    try:
        with get_engine().connect() as conn:
            print('MariaDB:',conn.execute(text('SELECT VERSION()')).scalar())
            names=set(conn.execute(text('SHOW DATABASES')).scalars())
            for db in [SOURCE_DB,DW_DB]:print(db,'present' if db in names else 'not initialized')
        return 0
    except Exception as exc:
        print('Database connection failed:',type(exc).__name__);return 1
if __name__=='__main__':raise SystemExit(main())
