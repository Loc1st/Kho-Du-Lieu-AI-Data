"""Decimal and temporal transformations for source sale rows."""
from datetime import date
from decimal import Decimal,ROUND_HALF_UP

def money(value):return Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)

def transform_sales(source_sales,maps,stores,promotions):
    sales=[]
    for r in source_sales:
        if r['trang_thai']=='CANCELLED':continue
        if not date(2024,1,1)<=r['ngay_dat']<=date(2026,12,31):raise ValueError('Sale date outside allowed period: '+r['ma_chi_tiet'])
        if r['so_luong']<=0 or r['don_gia']<0 or r['gia_von']<0 or not 0<=r['giam_gia']<=r['so_luong']*r['don_gia']:raise ValueError('Invalid constrained sale '+r['ma_chi_tiet'])
        promo=promotions[r['ma_khuyen_mai']]
        if not promo['ngay_bat_dau']<=r['ngay_dat']<=promo['ngay_ket_thuc']:raise ValueError('Promotion outside validity '+r['ma_chi_tiet'])
        versions=[v for v in stores.get(r['ma_cua_hang'],[]) if v['ngay_hieu_luc']<=r['ngay_dat']<v['ngay_het_han']]
        if len(versions)!=1:raise ValueError('Store history gap/overlap '+r['ma_chi_tiet'])
        item={k:r[k] for k in ['ma_chi_tiet','ma_don_hang','so_luong','don_gia','giam_gia','gia_von']}
        item.update(thoi_gian_key=int(r['ngay_dat'].strftime('%Y%m%d')),cua_hang_key=versions[0]['cua_hang_key'],doanh_thu=r['so_luong']*r['don_gia']-r['giam_gia'])
        for name,natural in [('san_pham','ma_sku'),('khach_hang','ma_khach_hang'),('kenh_ban','ma_kenh'),('khuyen_mai','ma_khuyen_mai')]:item[name+'_key']=maps[name][r[natural]]
        sales.append(item)
    return sales

def reject_reason(*args):
    from etl.pipeline import reject_reason as validate
    return validate(*args)
