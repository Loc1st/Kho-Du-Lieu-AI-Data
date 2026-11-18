"""Deliberately restricted SELECT playground: approved tables/functions only."""
import re
import time
from sqlalchemy import text
from mvc.models.base import dw_engine,src_engine

DW_TABLES=set('dim_thoi_gian dim_san_pham dim_cua_hang dim_khach_hang dim_kenh_ban dim_khuyen_mai fact_ban_hang fact_tra_hang vw_sales_net vw_olap_thoi_gian vw_olap_san_pham vw_olap_cua_hang vw_olap_kenh_ban vw_olap_khuyen_mai vw_olap_cube vw_olap_gia_tieu_thu vw_olap_thuong_hieu_kenh etl_log etl_data_quality etl_reject'.split())
SOURCE_TABLES=set('thuong_hieu san_pham phien_ban_san_pham tinh_thanh cua_hang khach_hang kenh_ban khuyen_mai don_hang chi_tiet_don_hang tra_hang chi_tiet_tra_hang lich_su_cua_hang nhan_vien'.split())
FUNCTIONS=set('count sum avg min max round coalesce nullif abs floor ceil year quarter month date concat lpad ifnull cast decimal signed unsigned date_format lower upper in as select from where exists over partition using'.split())

def validate_select(sql,db):
    if db not in ('phone_source','phone_dw'): raise ValueError('Chỉ chọn phone_source hoặc phone_dw')
    if not isinstance(sql,str) or len(sql)>12000: raise ValueError('SQL không hợp lệ hoặc quá dài')
    if not re.match(r'^\s*SELECT\b',sql,re.I): raise ValueError('Chỉ hỗ trợ một câu SELECT')
    if any(token in sql for token in (';', '--', '/*', '#', '@', '`', '\\', '{', '}')): raise ValueError('SQL chứa ký tự không được hỗ trợ')
    # Strip single-quoted string literals, then validate all identifiers.
    clean=re.sub(r"'(?:''|[^'])*'", "''",sql)
    if "'" in clean.replace("''",'') or '"' in clean: raise ValueError('Chuỗi SQL không hợp lệ')
    if len(re.findall(r'\bSELECT\b',clean,re.I)) != 1:
        raise ValueError('SQL Playground không hỗ trợ truy vấn con; dùng các view phân tích')
    if re.search(r'\b(into|outfile|dumpfile|procedure|for|lock|update|delete|insert|replace|drop|alter|create|grant|revoke|set|handler|load|union|straight_join)\b',clean,re.I):
        raise ValueError('SQL chỉ cho phép đọc dữ liệu đã chọn')
    if re.search(r'\b(?:FROM|JOIN)\s*\(',clean,re.I):
        raise ValueError('Chỉ hỗ trợ tham chiếu bảng trực tiếp')
    allowed=DW_TABLES if db=='phone_dw' else SOURCE_TABLES
    for table in re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*)',clean,re.I):
        if table.lower() not in allowed: raise ValueError('Bảng không được phép: '+table)
    # Comma joins are excluded; this avoids unvalidated secondary table references.
    for clause in re.findall(r'\bFROM\s+(.*?)(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|$)',clean,re.I|re.S):
        if ',' in clause: raise ValueError('Dùng JOIN thay cho danh sách bảng phân cách dấu phẩy')
    for function in re.findall(r'([a-zA-Z_][\w.]*)\s*\(',clean):
        if function.lower() not in FUNCTIONS: raise ValueError('Hàm không được phép: '+function)
    return sql.strip()

def run_custom_query(db_choice,sql_stmt):
    sql=validate_select(sql_stmt,db_choice);started=time.perf_counter()
    engine=dw_engine if db_choice=='phone_dw' else src_engine
    with engine.connect() as conn:
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        conn.exec_driver_sql('START TRANSACTION READ ONLY')
        try:
            conn.exec_driver_sql('SET SESSION SQL_SELECT_LIMIT=501')
            result=conn.execute(text('SET STATEMENT max_statement_time=3 FOR '+sql))
            columns=list(result.keys());rows=[dict(r) for r in result.mappings().fetchmany(501)]
        finally:
            conn.rollback()
            conn.exec_driver_sql('SET SESSION SQL_SELECT_LIMIT=DEFAULT')
    return {'columns':columns,'rows':rows[:500],'truncated':len(rows)>500,'total_returned':min(len(rows),500),'elapsed_ms':round((time.perf_counter()-started)*1000,2)}
