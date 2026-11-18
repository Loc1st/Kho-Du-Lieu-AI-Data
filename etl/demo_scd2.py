"""Serialized SCD2 store changes with exclusive intervals and historical fact keys."""
from datetime import date
from sqlalchemy import text
from common.db import get_engine,DW_DB
from etl.pipeline import sync_stores

def change_store(ma_cua_hang,khu_vuc,ngay_hieu_luc):
    effective=date.fromisoformat(str(ngay_hieu_luc));region=str(khu_vuc).strip()
    if not region or len(region)>100:raise ValueError('Region required (1-100 characters)')
    if not date(2024,1,1)<=effective<date(9999,12,31):raise ValueError('Invalid effective date')
    with get_engine(DW_DB).connect() as conn:
        if conn.execute(text("SELECT GET_LOCK('phone_dw_pipeline',60)")).scalar()!=1:raise TimeoutError('ETL/SCD lock unavailable')
        conn.commit()
        try:
            with conn.begin():
                if not conn.execute(text('SELECT ma_cua_hang FROM phone_source.cua_hang WHERE ma_cua_hang=:m FOR UPDATE'),dict(m=ma_cua_hang)).first():raise ValueError('Unknown store')
                current=conn.execute(text('SELECT * FROM phone_source.lich_su_cua_hang WHERE ma_cua_hang=:m AND ngay_hieu_luc<=:d ORDER BY ngay_hieu_luc DESC LIMIT 1'),dict(m=ma_cua_hang,d=effective)).mappings().first()
                if current and current['khu_vuc_quan_ly']==region:return dict(changed=False,ma_cua_hang=ma_cua_hang,khu_vuc_quan_ly=region,ngay_hieu_luc=str(effective))
                if current and current['ngay_hieu_luc']==effective:
                    raise ValueError('Conflicting region at existing effective date; choose a new date to preserve history')
                conn.execute(text('INSERT INTO phone_source.lich_su_cua_hang(ma_cua_hang,ngay_hieu_luc,khu_vuc_quan_ly) VALUES(:m,:d,:r)'),dict(m=ma_cua_hang,d=effective,r=region))
                sync_stores(conn)
                result=conn.execute(text('UPDATE fact_ban_hang f JOIN phone_source.don_hang o ON o.ma_don_hang=f.ma_don_hang JOIN dim_cua_hang d ON d.ma_cua_hang=o.ma_cua_hang AND o.ngay_dat>=d.ngay_hieu_luc AND o.ngay_dat<d.ngay_het_han SET f.cua_hang_key=d.cua_hang_key WHERE o.ma_cua_hang=:m'),dict(m=ma_cua_hang))
                versions=[dict(r) for r in conn.execute(text('SELECT * FROM dim_cua_hang WHERE ma_cua_hang=:m ORDER BY ngay_hieu_luc'),dict(m=ma_cua_hang)).mappings()]
                return dict(changed=True,ma_cua_hang=ma_cua_hang,khu_vuc_quan_ly=region,ngay_hieu_luc=str(effective),facts_updated=result.rowcount,versions=versions)
        finally:
            conn.execute(text("SELECT RELEASE_LOCK('phone_dw_pipeline')"));conn.commit()

def main():
    result=change_store('CH00','Metro demo','2026-01-01')
    print(result);return result

if __name__=='__main__':main()
