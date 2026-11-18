"""Database extraction helper; the pipeline stages a consistent transactional snapshot."""
from sqlalchemy import text

def extract_all(source_engine,dw_engine=None,run_id=None,copy_raw_to_dw=True):
    tables=['thuong_hieu','san_pham','phien_ban_san_pham','tinh_thanh','cua_hang','nhan_vien','khach_hang','kenh_ban','khuyen_mai','don_hang','chi_tiet_don_hang','tra_hang','chi_tiet_tra_hang','lich_su_cua_hang','raw_import_error']
    with source_engine.connect() as c:return {t:[dict(r) for r in c.execute(text('SELECT * FROM '+t)).mappings()] for t in tables}


def extract_sales(conn):
    return conn.execute(text("SELECT c.*,d.ngay_dat,d.ma_cua_hang,d.ma_khach_hang,d.ma_kenh,d.trang_thai FROM phone_source.chi_tiet_don_hang c JOIN phone_source.don_hang d USING(ma_don_hang)")).mappings().all()
