"""Sales-cohort analytics. Every chart uses the same parameterized filter."""
from mvc.models.base import dw_engine, query_records

JOINS = """ FROM vw_sales_net f JOIN dim_thoi_gian t USING(thoi_gian_key)
JOIN dim_san_pham p USING(san_pham_key) JOIN dim_cua_hang s USING(cua_hang_key)
JOIN dim_kenh_ban k USING(kenh_ban_key) """
FIELDS = {'thuong_hieu':'p.thuong_hieu','ten_san_pham':'p.ten_san_pham','nam':'t.nam',
'quy':'t.quy','thang':'t.thang','khu_vuc':'s.khu_vuc_quan_ly','ma_cua_hang':'s.ma_cua_hang','ma_kenh':'k.ma_kenh'}

def build_filters(filters):
    conditions=[]; params={}
    for key,value in filters.items():
        if key not in FIELDS: raise ValueError('Bộ lọc không hợp lệ: '+key)
        if value in ('',None): continue
        if key in ('nam','quy','thang'):
            try: value=int(value)
            except (ValueError,TypeError): raise ValueError('Bộ lọc thời gian phải là số')
            lo,hi={'nam':(2000,2100),'quy':(1,4),'thang':(1,12)}[key]
            if not lo<=value<=hi: raise ValueError('Bộ lọc ngoài phạm vi: '+key)
        elif len(str(value))>120: raise ValueError('Bộ lọc quá dài')
        conditions.append(FIELDS[key]+' = :'+key); params[key]=value
    return ' WHERE '+(' AND '.join(conditions) or '1=1'),params

def get_filter_options():
    result={}
    for key,column in FIELDS.items():
        result[key]=[r['value'] for r in query_records(dw_engine,'SELECT DISTINCT '+column+' AS value '+JOINS+' ORDER BY value')]
    return result

def get_overview_data(filters):
    where,params=build_filters(filters)
    def q(select,tail=''): return query_records(dw_engine,'SELECT '+select+JOINS+where+tail,params)
    kpi=q("""COALESCE(SUM(doanh_thu),0) doanh_thu_ban, COALESCE(SUM(tien_hoan),0) tien_hoan,
    COALESCE(SUM(doanh_thu_thuan),0) doanh_thu_thuan, COUNT(DISTINCT ma_don_hang) so_don_hang,
    COALESCE(SUM(so_luong),0) so_dien_thoai, COALESCE(SUM(gia_von_thuan),0) gia_von,
    COALESCE(SUM(loi_nhuan),0) loi_nhuan,
    COALESCE(100*SUM(loi_nhuan)/NULLIF(SUM(doanh_thu_thuan),0),0) bien_loi_nhuan,
    COALESCE(100*SUM(so_luong_tra)/NULLIF(SUM(so_luong),0),0) ty_le_tra,
    COALESCE(SUM(doanh_thu_thuan)/NULLIF(COUNT(DISTINCT ma_don_hang),0),0) gia_tri_don_tb""")[0]
    scatter=q('p.ma_sku,t.nam,t.thang,SUM(doanh_thu)/SUM(so_luong) gia_ban_tb,SUM(so_luong) so_luong',
              ' GROUP BY p.ma_sku,t.nam,t.thang ORDER BY p.ma_sku,t.nam,t.thang')
    # Pearson over SKU-month observations; descriptive, not causal. Zero-demand SKUs excluded.
    n=len(scatter); correlation=None
    if n>1:
        xs=[float(r['gia_ban_tb']) for r in scatter]; ys=[float(r['so_luong']) for r in scatter]
        mx=sum(xs)/n;my=sum(ys)/n
        den=(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))**0.5
        if den: correlation=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den
    return {'kpi':kpi,'top_models':q('p.thuong_hieu,p.ten_san_pham,SUM(doanh_thu_thuan) doanh_thu,SUM(so_luong) so_luong,SUM(loi_nhuan) loi_nhuan',
      ' GROUP BY p.thuong_hieu,p.ten_san_pham ORDER BY doanh_thu DESC LIMIT 15'),
      'monthly':q("CONCAT(t.nam,'-',LPAD(t.thang,2,'0')) thang,SUM(doanh_thu_thuan) doanh_thu,SUM(so_luong) so_luong",' GROUP BY t.nam,t.thang ORDER BY t.nam,t.thang'),
      'brand_channel':q('p.thuong_hieu,k.ten_kenh,SUM(doanh_thu_thuan) doanh_thu',' GROUP BY p.thuong_hieu,k.ten_kenh'),
      'scatter':scatter,'correlation':{'pearson_r':correlation,'observations':n,'grain':'SKU × tháng; chỉ các SKU có bán'},
      'brand_trend':q("p.thuong_hieu,CONCAT(t.nam,'-',LPAD(t.thang,2,'0')) thang,SUM(so_luong) so_luong",' GROUP BY p.thuong_hieu,t.nam,t.thang ORDER BY t.nam,t.thang'),
      'regions':q('s.khu_vuc_quan_ly,SUM(doanh_thu_thuan) doanh_thu,SUM(loi_nhuan) loi_nhuan,100*SUM(so_luong_tra)/NULLIF(SUM(so_luong),0) ty_le_tra',' GROUP BY s.khu_vuc_quan_ly ORDER BY doanh_thu DESC'),
      'stores':q('s.ma_cua_hang,s.ten_cua_hang,SUM(doanh_thu_thuan) doanh_thu,SUM(loi_nhuan) loi_nhuan,100*SUM(so_luong_tra)/NULLIF(SUM(so_luong),0) ty_le_tra',' GROUP BY s.ma_cua_hang,s.ten_cua_hang ORDER BY doanh_thu DESC')}
