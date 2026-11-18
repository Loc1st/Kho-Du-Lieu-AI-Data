"""Reproducible phone commerce source. No database reset is performed."""
from __future__ import annotations
import argparse, csv, json, random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from sqlalchemy import text
from common.db import DATA_DIR, SQL_DIR, SOURCE_DB, get_engine, run_sql_file

PROVINCES=['Ha Noi','Ho Chi Minh','Da Nang','Can Tho','Hai Phong','Binh Duong']

def generate(orders=60000,seed=2026):
    if orders < 50000: raise ValueError('At least 50000 orders required')
    rng=random.Random(seed); tables={}
    tables['thuong_hieu']=[dict(ma_thuong_hieu=f'B{i}',ten_thuong_hieu=n) for i,n in enumerate(['Apple','Samsung','Xiaomi','OPPO','Vivo'])]
    tables['san_pham']=[dict(ma_san_pham=f'P{i:03}',ten_san_pham=f'{tables["thuong_hieu"][i%5]["ten_thuong_hieu"]} {["iPhone","Galaxy S","Redmi Note","Reno","V series"][i%5]} {14+i//5}',ma_thuong_hieu=f'B{i%5}') for i in range(25)]
    tables['phien_ban_san_pham']=[dict(ma_sku=f'SKU{i:03}',ma_san_pham=f'P{i//4:03}',ram_gb=[6,8,12,16][i%4],bo_nho_gb=[128,256,512,1024][i%4],mau_sac=['Black','Blue','White','Gold'][i%4]) for i in range(100)]
    tables['tinh_thanh']=[dict(ma_tinh=f'T{i}',ten_tinh=n) for i,n in enumerate(PROVINCES)]
    tables['cua_hang']=[dict(ma_cua_hang=f'CH{i:02}',ten_cua_hang=f'Phone Store {i:02}',ma_tinh=f'T{i%6}') for i in range(18)]
    tables['nhan_vien']=[dict(ma_nhan_vien=f'NV{i:03}',ho_ten=f'Employee {i}',ma_cua_hang=f'CH{i%18:02}') for i in range(90)]
    tables['khach_hang']=[dict(ma_khach_hang=f'KH{i:05}',ho_ten=f'Customer {i:05}',ma_tinh=f'T{i%6}') for i in range(12000)]
    tables['kenh_ban']=[dict(ma_kenh=k,ten_kenh=n) for k,n in [('STORE','In store'),('WEB','Website'),('APP','Mobile app'),('MARKET','Marketplace')]]
    tables['khuyen_mai']=[dict(ma_khuyen_mai='NONE',ten_khuyen_mai='No promotion',ngay_bat_dau=date(2024,1,1),ngay_ket_thuc=date(2026,12,31))]
    for year in [2024,2025,2026]:
        for code,name,start,end in [('TET','Tet sale',date(year,1,1),date(year,2,28)),('SUMMER','Summer sale',date(year,6,1),date(year,8,31)),('DOUBLE','Double day',date(year,1,1),date(year,12,31)),('YEAR_END','Year end',date(year,11,1),date(year,12,31)),('LOYALTY','Loyalty offer',date(year,1,1),date(year,12,31))]:
            tables['khuyen_mai'].append(dict(ma_khuyen_mai=f'{code}{year}',ten_khuyen_mai=f'{name} {year}',ngay_bat_dau=start,ngay_ket_thuc=end))
    tables['don_hang']=[];tables['chi_tiet_don_hang']=[];tables['tra_hang']=[];tables['chi_tiet_tra_hang']=[]
    days=[date(2024,1,1)+timedelta(days=i) for i in range(1096)]
    weights=[2.5 if d.month in (1,11,12) else 1.6 if d.day==d.month else 1 for d in days]
    for i,d in enumerate(rng.choices(days,weights=weights,k=orders)):
        oid=f'DH{i:07}';cancel=rng.random()<.035
        tables['don_hang'].append(dict(ma_don_hang=oid,ngay_dat=d,ma_nhan_vien=f'NV{i%90:03}',ma_cua_hang=f'CH{rng.randrange(18):02}',ma_khach_hang=f'KH{rng.randrange(12000):05}',ma_kenh=rng.choices(['STORE','WEB','APP','MARKET'],[5,3,2,1])[0],trang_thai='CANCELLED' if cancel else 'COMPLETED'))
        for j,sku in enumerate(rng.sample(range(100),rng.choices([1,2,3],[7,2,1])[0])):
            lid=f'{oid}-{j}';qty=rng.choices([1,2,3],[8,2,1])[0];price=Decimal(3000000+(sku//4)*650000);promo='TET' if d.month==1 else 'YEAR_END' if d.month>=11 else 'DOUBLE' if d.day==d.month else rng.choice(['NONE','NONE','SUMMER' if d.month in (6,7,8) else 'LOYALTY']);discount=(price*qty*Decimal('.08' if promo!='NONE' else '0')).quantize(Decimal('.01'));cost=(price*qty*Decimal('.73')).quantize(Decimal('.01'))
            tables['chi_tiet_don_hang'].append(dict(ma_chi_tiet=lid,ma_don_hang=oid,ma_sku=f'SKU{sku:03}',ma_khuyen_mai=promo+str(d.year) if promo!='NONE' else promo,so_luong=qty,don_gia=price,giam_gia=discount,gia_von=cost))
            if not cancel and rng.random()<.065:
                # Some lines receive two separate partial returns: verifies preaggregation.
                total=rng.randint(1,qty);parts=[1,total-1] if total>1 else [1]
                for part,rqty in enumerate(parts):
                    rid=f'R{lid}-{part}';tables['tra_hang'].append(dict(ma_tra_hang=rid,trang_thai='FULL' if total==qty else 'PARTIAL',ngay_tra=d+timedelta(days=rng.randint(1,30)),ly_do=rng.choice(['Defect','Changed mind','Wrong model'])))
                    tables['chi_tiet_tra_hang'].append(dict(ma_chi_tiet_tra=rid,ma_tra_hang=rid,ma_chi_tiet=lid,so_luong_tra=rqty,tien_hoan=((price*qty-discount)*rqty/qty).quantize(Decimal('.01'))))
    returned={}
    for row in tables['chi_tiet_tra_hang']:returned[row['ma_chi_tiet']]=returned.get(row['ma_chi_tiet'],0)+row['so_luong_tra']
    by_order={}
    for row in tables['chi_tiet_don_hang']:by_order.setdefault(row['ma_don_hang'],[]).append(row)
    for order in tables['don_hang']:
        lines=by_order[order['ma_don_hang']]
        if any(line['ma_chi_tiet'] in returned for line in lines):order['trang_thai']='RETURNED' if all(returned.get(line['ma_chi_tiet'],0)==line['so_luong'] for line in lines) else 'PARTIALLY_RETURNED'
    tables['lich_su_cua_hang']=[]
    for i in range(18):
        tables['lich_su_cua_hang'].append(dict(ma_cua_hang=f'CH{i:02}',ngay_hieu_luc=date(2024,1,1),khu_vuc_quan_ly=['North','South','Central'][i%3]))
        if i<6:tables['lich_su_cua_hang'].append(dict(ma_cua_hang=f'CH{i:02}',ngay_hieu_luc=date(2025,7,1),khu_vuc_quan_ly='Metro'))
    for order in tables['don_hang']:order['ma_nhan_vien']='NV'+order['ma_cua_hang'][2:].zfill(3)
    tables['raw_import_error']=[]
    kinds=['duplicate','missing_required','negative_quantity','negative_price','negative_cost','bad_sku','bad_date','bad_province','excess_return']
    base={**tables['chi_tiet_don_hang'][0],**tables['don_hang'][0]}
    for kind in kinds:
        for j in range(10):
            row=dict(base);row['ma_chi_tiet']=f'BAD-{kind}-{j}'
            if kind=='duplicate':row['ma_chi_tiet']=base['ma_chi_tiet']
            elif kind=='missing_required':row['ma_khach_hang']=None
            elif kind=='negative_quantity':row['so_luong']=-1
            elif kind=='negative_price':row['don_gia']='-1'
            elif kind=='negative_cost':row['gia_von']='-1'
            elif kind=='bad_sku':row['ma_sku']='UNKNOWN'
            elif kind=='bad_date':row['ngay_dat']='2025-02-30'
            elif kind=='bad_province':row['tinh_thanh']='Atlantis'
            elif kind=='excess_return':row['so_luong_tra']=999
            tables['raw_import_error'].append(dict(raw_id=f'{kind}-{j}',loai_loi=kind,payload=json.dumps(row,default=str)))
    return tables

def upsert_rows(conn,table,rows,update=True):
    if not rows:return
    cols=list(rows[0]);stmt=f'INSERT INTO {table} ('+','.join(cols)+') VALUES ('+','.join(':'+c for c in cols)+')'
    stmt+=' ON DUPLICATE KEY UPDATE '+','.join(f'{c}=VALUES({c})' for c in cols) if update else ' ON DUPLICATE KEY UPDATE '+cols[0]+'=VALUES('+cols[0]+')'
    for start in range(0,len(rows),2000):conn.execute(text(stmt),rows[start:start+2000])

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--csv-only',action='store_true');parser.add_argument('--orders',type=int,default=60000);parser.add_argument('--seed',type=int,default=2026);args=parser.parse_args(argv)
    if not args.csv_only:
        with get_engine().connect() as conn:
            exists=conn.execute(text("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='phone_source' AND TABLE_NAME='don_hang'")).scalar()
            if exists and conn.execute(text('SELECT COUNT(*) FROM phone_source.don_hang')).scalar():
                print('Source already contains orders; generation skipped to preserve existing data.');return {'skipped':True}
    tables=generate(args.orders,args.seed);out=DATA_DIR/'phone_sales';out.mkdir(parents=True,exist_ok=True)
    for name,rows in tables.items():
        with (out/f'{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    manifest={'seed':args.seed,'orders':args.orders,'row_counts':{k:len(v) for k,v in tables.items()},'error_counts':dict(Counter(r['loai_loi'] for r in tables['raw_import_error'])),'errors':tables['raw_import_error']}
    (out/'error_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    if not args.csv_only:
        engine=get_engine();run_sql_file(engine,SQL_DIR/'01_create_source_db.sql')
        with get_engine(SOURCE_DB).connect() as conn:
            if conn.execute(text("SELECT GET_LOCK('phone_dw_pipeline',60)")).scalar()!=1:raise TimeoutError('Pipeline lock unavailable')
            conn.commit()
            try:
                with conn.begin():
                    for name,rows in tables.items():upsert_rows(conn,name,rows,update=name!='lich_su_cua_hang')
            finally:
                conn.execute(text("SELECT RELEASE_LOCK('phone_dw_pipeline')"));conn.commit()
    print(json.dumps({k:v for k,v in manifest.items() if k!='errors'},indent=2));return manifest

if __name__=='__main__':main()
