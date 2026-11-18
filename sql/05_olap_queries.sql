USE phone_dw;
-- Q1: Which products sell the most and produce the most net revenue/profit?
SELECT p.thuong_hieu,p.ma_sku,p.ten_san_pham,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan
FROM vw_sales_net f JOIN dim_san_pham p USING(san_pham_key)
GROUP BY p.thuong_hieu,p.ma_sku,p.ten_san_pham ORDER BY doanh_thu_thuan DESC;
-- Q2: Seasonal revenue, year -> quarter -> month roll-up / drill-down.
SELECT d.nam,d.quy,d.thang,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan
FROM vw_sales_net f JOIN dim_thoi_gian d USING(thoi_gian_key)
GROUP BY d.nam,d.quy,d.thang WITH ROLLUP;
-- Q3: Brand x channel: all grouping sets emulate CUBE on MariaDB.
SELECT * FROM vw_olap_cube;
-- Example slice/dice: choose brand/channel; replace literals as needed.
SELECT * FROM vw_olap_thuong_hieu_kenh WHERE thuong_hieu IN ('Apple','Samsung') AND ten_kenh IN ('Website','In store');
-- Q4: Price versus demand. Observations can be exported for plotting.
SELECT * FROM vw_olap_gia_tieu_thu ORDER BY ma_sku,nam,thang;
-- Pearson across SKU-month observations (association, not causal elasticity).
SELECT (COUNT(*)*SUM(gia_ban_binh_quan*so_luong_ban)-SUM(gia_ban_binh_quan)*SUM(so_luong_ban))/NULLIF(SQRT((COUNT(*)*SUM(gia_ban_binh_quan*gia_ban_binh_quan)-POW(SUM(gia_ban_binh_quan),2))*(COUNT(*)*SUM(so_luong_ban*so_luong_ban)-POW(SUM(so_luong_ban),2))),0) pearson_price_units FROM vw_olap_gia_tieu_thu;
-- Q5: Management region -> province -> store, historical SCD2 attribution.
SELECT s.khu_vuc_quan_ly,s.tinh_thanh,s.ten_cua_hang,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra
FROM vw_sales_net f JOIN dim_cua_hang s USING(cua_hang_key)
GROUP BY s.khu_vuc_quan_ly,s.tinh_thanh,s.ten_cua_hang WITH ROLLUP;
