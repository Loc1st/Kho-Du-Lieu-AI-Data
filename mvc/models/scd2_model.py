"""Store history and effective-date revenue comparison."""
from datetime import date
from mvc.models.base import dw_engine,query_records

def search_stores(query):
    return query_records(dw_engine,"SELECT DISTINCT ma_cua_hang,ten_cua_hang FROM dim_cua_hang WHERE ma_cua_hang LIKE :q OR ten_cua_hang LIKE :q ORDER BY ma_cua_hang LIMIT 50",{'q':'%'+str(query)[:100]+'%'})

def get_store_scd2_detail(ma_cua_hang):
    rows=query_records(dw_engine,"""SELECT s.*,COUNT(DISTINCT f.ma_don_hang) so_don_hang,
    COALESCE(SUM(f.doanh_thu_thuan),0) doanh_thu_thuan,COALESCE(SUM(f.loi_nhuan),0) loi_nhuan
    FROM dim_cua_hang s LEFT JOIN vw_sales_net f USING(cua_hang_key)
    WHERE s.ma_cua_hang=:id GROUP BY s.cua_hang_key ORDER BY s.ngay_hieu_luc""",{'id':ma_cua_hang})
    return {'ma_cua_hang':ma_cua_hang,'history':rows}

def simulate_scd2_change(payload):
    from etl.demo_scd2 import change_store
    code=str(payload.get('ma_cua_hang','')).strip(); region=str(payload.get('khu_vuc','')).strip()
    if not code or not region or len(region)>100: raise ValueError('Nhập mã cửa hàng và khu vực (tối đa 100 ký tự)')
    effective=date.fromisoformat(str(payload.get('ngay_hieu_luc','')))
    result=change_store(code,region,effective.isoformat())
    return {'change':result,**get_store_scd2_detail(code)}
