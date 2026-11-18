"""Atomic, repeatable database ETL with per-run staging and rejection audit."""
from __future__ import annotations
import argparse,json,uuid
from datetime import date,datetime,timedelta
from decimal import Decimal,ROUND_HALF_UP
from sqlalchemy import text
from common.db import get_engine,SOURCE_DB,DW_DB,SQL_DIR,OUTPUT_DIR,run_sql_file
from generator.generate_data import upsert_rows,PROVINCES


def reject_reason(row,existing,skus):
    if not all(row.get(k) for k in ('ma_chi_tiet','ma_don_hang','ma_khach_hang','ma_sku','ngay_dat')):return 'missing_required'
    if row['ma_chi_tiet'] in existing:return 'duplicate'
    try:
        d=date.fromisoformat(str(row['ngay_dat']))
        if not date(2024,1,1)<=d<=date(2026,12,31):return 'bad_date'
    except (ValueError,TypeError):return 'bad_date'
    for col,reason in [('so_luong','negative_quantity'),('don_gia','negative_price'),('gia_von','negative_cost')]:
        try:
            value=Decimal(str(row.get(col)))
            if not value.is_finite() or value<0 or (col=='so_luong' and value<=0):return reason
        except Exception:return 'missing_required'
    if row['ma_sku'] not in skus:return 'bad_sku'
    if 'tinh_thanh' in row and row['tinh_thanh'] not in PROVINCES:return 'bad_province'
    if Decimal(str(row.get('so_luong_tra',0)))>Decimal(str(row['so_luong'])):return 'excess_return'
    return None


def sync_stores(conn):
    rows=conn.execute(text('SELECT h.*,c.ten_cua_hang,t.ten_tinh FROM phone_source.lich_su_cua_hang h JOIN phone_source.cua_hang c USING(ma_cua_hang) JOIN phone_source.tinh_thanh t USING(ma_tinh) ORDER BY ma_cua_hang,ngay_hieu_luc')).mappings().all()
    result=[]
    for i,r in enumerate(rows):
        end=rows[i+1]['ngay_hieu_luc'] if i+1<len(rows) and rows[i+1]['ma_cua_hang']==r['ma_cua_hang'] else date(9999,12,31)
        result.append(dict(ma_cua_hang=r['ma_cua_hang'],ten_cua_hang=r['ten_cua_hang'],tinh_thanh=r['ten_tinh'],khu_vuc_quan_ly=r['khu_vuc_quan_ly'],ngay_hieu_luc=r['ngay_hieu_luc'],ngay_het_han=end,is_current=int(end==date(9999,12,31))))
    upsert_rows(conn,'dim_cua_hang',result)
    return len(result)


def run_etl(init_dw=False,copy_raw_to_dw=True):
    run_id=uuid.uuid4().hex
    engine=get_engine()
    for file in ['02_create_dw.sql','03_procedures.sql','04_olap_views.sql']:run_sql_file(engine,SQL_DIR/file)
    engine=get_engine(DW_DB)
    with engine.connect() as conn:
        if conn.execute(text("SELECT GET_LOCK('phone_dw_pipeline',60)")).scalar()!=1:raise TimeoutError('ETL/SCD lock unavailable')
        conn.commit()
        try:
            with conn.begin():
                def log(table,read,loaded,rejected=0,note='',step='LOAD'):
                    conn.execute(text('INSERT INTO etl_log(run_id,buoc,bang,so_dong_doc,so_dong_nap,so_dong_loai,ghi_chu,status) VALUES(:r,:step,:t,:a,:b,:c,:n,\'SUCCESS\')'),dict(r=run_id,t=table,a=read,b=loaded,c=rejected,n=note,step=step))
                dims=[('san_pham','SELECT v.ma_sku,p.ten_san_pham,b.ten_thuong_hieu thuong_hieu,v.ram_gb,v.bo_nho_gb,v.mau_sac FROM phone_source.phien_ban_san_pham v JOIN phone_source.san_pham p USING(ma_san_pham) JOIN phone_source.thuong_hieu b USING(ma_thuong_hieu)'),('khach_hang','SELECT k.ma_khach_hang,k.ho_ten,t.ten_tinh tinh_thanh FROM phone_source.khach_hang k JOIN phone_source.tinh_thanh t USING(ma_tinh)'),('kenh_ban','SELECT * FROM phone_source.kenh_ban'),('khuyen_mai','SELECT ma_khuyen_mai,ten_khuyen_mai FROM phone_source.khuyen_mai')]
                for name,query in dims:
                    rows=[dict(r) for r in conn.execute(text(query)).mappings()];upsert_rows(conn,'dim_'+name,rows);log('dim_'+name,len(rows),len(rows))
                n=sync_stores(conn);log('dim_cua_hang',n,n)
                dates=[];d=date(2024,1,1)
                while d<=date(2027,12,31):
                    dates.append(dict(thoi_gian_key=int(d.strftime('%Y%m%d')),ngay=d,nam=d.year,quy=(d.month-1)//3+1,thang=d.month));d+=timedelta(days=1)
                upsert_rows(conn,'dim_thoi_gian',dates)
                # Keep a per-run immutable extract envelope for all business sale and return rows.
                conn.execute(text("INSERT INTO stg_import(run_id,source_table,source_id,payload) SELECT :r,'chi_tiet_don_hang',c.ma_chi_tiet,JSON_OBJECT('ma_chi_tiet',c.ma_chi_tiet,'ma_don_hang',c.ma_don_hang,'so_luong',c.so_luong,'don_gia',c.don_gia,'giam_gia',c.giam_gia,'gia_von',c.gia_von,'ma_sku',c.ma_sku,'ngay_dat',d.ngay_dat,'trang_thai',d.trang_thai) FROM phone_source.chi_tiet_don_hang c JOIN phone_source.don_hang d USING(ma_don_hang)"),dict(r=run_id))
                conn.execute(text("INSERT INTO stg_import(run_id,source_table,source_id,payload) SELECT :r,'chi_tiet_tra_hang',c.ma_chi_tiet_tra,JSON_OBJECT('ma_chi_tiet',c.ma_chi_tiet,'so_luong_tra',c.so_luong_tra,'tien_hoan',c.tien_hoan,'ngay_tra',t.ngay_tra) FROM phone_source.chi_tiet_tra_hang c JOIN phone_source.tra_hang t USING(ma_tra_hang)"),dict(r=run_id))
                source_count=conn.execute(text('SELECT COUNT(*) FROM phone_source.chi_tiet_don_hang')).scalar()
                cancelled=conn.execute(text("SELECT COUNT(*) FROM phone_source.chi_tiet_don_hang c JOIN phone_source.don_hang d USING(ma_don_hang) WHERE d.trang_thai='CANCELLED'")).scalar()
                maps={}
                for name,natural in [('san_pham','ma_sku'),('khach_hang','ma_khach_hang'),('kenh_ban','ma_kenh'),('khuyen_mai','ma_khuyen_mai')]:
                    maps[name]={r[natural]:r[name+'_key'] for r in conn.execute(text('SELECT * FROM dim_'+name)).mappings()}
                stores={}
                for r in conn.execute(text('SELECT * FROM dim_cua_hang ORDER BY ngay_hieu_luc')).mappings():stores.setdefault(r['ma_cua_hang'],[]).append(r)
                from etl.extract import extract_sales
                source_sales=extract_sales(conn)
                promotions={r['ma_khuyen_mai']:r for r in conn.execute(text('SELECT * FROM phone_source.khuyen_mai')).mappings()}
                from etl.transform import transform_sales
                sales=transform_sales(source_sales,maps,stores,promotions)
                log('stg_sales_extract',len(source_sales),len(source_sales),step='EXTRACT')
                log('validated_sales',len(source_sales),len(sales),cancelled,'Validate dates, amounts, temporal promotions, natural keys and SCD intervals',step='TRANSFORM')
                from etl.load import load_sales
                load_sales(conn,sales)
                # Propagate subsequent cancellations without leaving stale return facts.
                conn.execute(text("DELETE r FROM fact_tra_hang r JOIN fact_ban_hang f USING(ban_hang_key) JOIN phone_source.don_hang d ON d.ma_don_hang=f.ma_don_hang WHERE d.trang_thai='CANCELLED'"))
                conn.execute(text("DELETE f FROM fact_ban_hang f JOIN phone_source.don_hang d ON d.ma_don_hang=f.ma_don_hang WHERE d.trang_thai='CANCELLED'"))
                log('fact_ban_hang',source_count,source_count-cancelled,cancelled,'Cancelled lines excluded')
                returns=conn.execute(text('SELECT r.*,t.ngay_tra,f.ban_hang_key,f.so_luong,f.doanh_thu,f.gia_von,dt.ngay ngay_ban FROM phone_source.chi_tiet_tra_hang r JOIN phone_source.tra_hang t USING(ma_tra_hang) LEFT JOIN fact_ban_hang f USING(ma_chi_tiet) LEFT JOIN dim_thoi_gian dt ON dt.thoi_gian_key=f.thoi_gian_key ORDER BY r.ma_chi_tiet,t.ngay_tra,r.ma_chi_tiet_tra')).mappings().all()
                cumulative={};good=[];rejects=[]
                for row in conn.execute(text("SELECT c.ma_chi_tiet,c.ma_don_hang FROM phone_source.chi_tiet_don_hang c JOIN phone_source.don_hang d USING(ma_don_hang) WHERE d.trang_thai='CANCELLED'")).mappings():
                    rejects.append(dict(run_id=run_id,bang='chi_tiet_don_hang',source_id=row['ma_chi_tiet'],reason='cancelled_order',payload=json.dumps(dict(row))))
                cancelled_rejects=len(rejects)
                for r in returns:
                    key=r['ma_chi_tiet'];q,m,returned_cost=cumulative.get(key,(0,Decimal(0),Decimal(0)));reason=None
                    if not r['ban_hang_key']:reason='missing_sale'
                    elif r['ngay_tra']<r['ngay_ban']:reason='return_before_sale'
                    elif q+r['so_luong_tra']>r['so_luong'] or m+r['tien_hoan']>r['doanh_thu']:reason='excess_return'
                    if reason:
                        rejects.append(dict(run_id=run_id,bang='chi_tiet_tra_hang',source_id=r['ma_chi_tiet_tra'],reason=reason,payload=json.dumps(dict(r),default=str)));continue
                    cost=min(r['gia_von']-returned_cost,(r['gia_von']*r['so_luong_tra']/r['so_luong']).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
                    cumulative[key]=(q+r['so_luong_tra'],m+r['tien_hoan'],returned_cost+cost)
                    good.append(dict(ma_chi_tiet_tra=r['ma_chi_tiet_tra'],ban_hang_key=r['ban_hang_key'],thoi_gian_key=int(r['ngay_tra'].strftime('%Y%m%d')),so_luong_tra=r['so_luong_tra'],tien_hoan=r['tien_hoan'],gia_von_hoan=cost))
                # Reconcile removal or invalidation of formerly valid return rows in this same transaction.
                valid_ids={r['ma_chi_tiet_tra'] for r in good}
                obsolete=[r[0] for r in conn.execute(text('SELECT ma_chi_tiet_tra FROM fact_tra_hang')) if r[0] not in valid_ids]
                for start in range(0,len(obsolete),1000):
                    conn.execute(text('DELETE FROM fact_tra_hang WHERE ma_chi_tiet_tra=:id'),[dict(id=i) for i in obsolete[start:start+1000]])
                upsert_rows(conn,'fact_tra_hang',good);log('fact_tra_hang',len(returns),len(good),len(rejects)-cancelled_rejects)
                raw=conn.execute(text('SELECT * FROM phone_source.raw_import_error')).mappings().all()
                existing=set(conn.execute(text('SELECT ma_chi_tiet FROM phone_source.chi_tiet_don_hang')).scalars());skus=set(conn.execute(text('SELECT ma_sku FROM dim_san_pham')).scalars())
                for r in raw:
                    payload=json.loads(r['payload']);reason=reject_reason(payload,existing,skus)
                    if reason is None:raise ValueError('Unexpected valid raw error envelope '+r['raw_id'])
                    rejects.append(dict(run_id=run_id,bang='raw_import_error',source_id=r['raw_id'],reason=reason,payload=r['payload']))
                upsert_rows(conn,'etl_reject',rejects)
                upsert_rows(conn,'stg_import',[dict(run_id=run_id,source_table='raw_import_error',source_id=r['raw_id'],payload=r['payload']) for r in raw])
                log('raw_import_error',len(raw),0,len(raw),'Invalid envelope validated and rejected')
                log('stg_returns_extract',len(returns),len(returns),step='EXTRACT')
                log('validated_returns',len(returns),len(good),len(returns)-len(good),'Cumulative unit/refund/cost bounds and return chronology',step='TRANSFORM')
                conn.execute(text("INSERT INTO etl_data_quality(run_id,bang,loai_kiem_tra,so_dong_truoc,so_dong_sau,cach_xu_ly) VALUES(:r,'sales','validated_source_rows',:a,:b,'Constrained source + Decimal and temporal validation')"),dict(r=run_id,a=len(source_sales),b=len(sales)))
                from collections import Counter
                for reason,count in Counter(r['reason'] for r in rejects).items():
                    conn.execute(text("INSERT INTO etl_data_quality(run_id,bang,loai_kiem_tra,so_dong_truoc,so_dong_sau,cach_xu_ly) VALUES(:r,'imports',:reason,:n,0,'Rejected with source envelope')"),dict(r=run_id,reason=reason,n=count))
            out=OUTPUT_DIR/'phone_sales';out.mkdir(parents=True,exist_ok=True)
            for table in ['etl_log','etl_data_quality','etl_reject']:
                rows=[dict(r) for r in conn.execute(text(f'SELECT * FROM {table} WHERE run_id=:r'),dict(r=run_id)).mappings()]
                (out/(table+'_latest.json')).write_text(json.dumps(rows,default=str,indent=2),encoding='utf-8')
            conn.commit()
        except Exception as exc:
            conn.rollback()
            with conn.begin():conn.execute(text("INSERT INTO etl_log(run_id,buoc,bang,status,ghi_chu) VALUES(:r,'PIPELINE','ALL','FAILED',:e)"),dict(r=run_id,e=str(exc)[:2000]))
            raise
        finally:
            conn.execute(text("SELECT RELEASE_LOCK('phone_dw_pipeline')"));conn.commit()
    print('ETL complete run_id='+run_id);return run_id


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--init-dw',action='store_true');args=p.parse_args(argv);return run_etl(args.init_dw)
if __name__=='__main__':main()
