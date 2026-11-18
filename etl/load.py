"""Parameterized batch warehouse loaders."""
from generator.generate_data import upsert_rows

def load_sales(conn,rows):
    upsert_rows(conn,'fact_ban_hang',rows)

def sync_stores(conn):
    from etl.pipeline import sync_stores as synchronize
    return synchronize(conn)
