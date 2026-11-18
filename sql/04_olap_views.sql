USE phone_dw;
CREATE OR REPLACE VIEW vw_sales_net AS
SELECT f.*, COALESCE(r.so_luong_tra,0) so_luong_tra, COALESCE(r.tien_hoan,0) tien_hoan, COALESCE(r.gia_von_hoan,0) gia_von_hoan,
f.doanh_thu-COALESCE(r.tien_hoan,0) doanh_thu_thuan, f.gia_von-COALESCE(r.gia_von_hoan,0) gia_von_thuan,
f.doanh_thu-COALESCE(r.tien_hoan,0)-f.gia_von+COALESCE(r.gia_von_hoan,0) loi_nhuan
FROM fact_ban_hang f LEFT JOIN (SELECT ban_hang_key,SUM(so_luong_tra) so_luong_tra,SUM(tien_hoan) tien_hoan,SUM(gia_von_hoan) gia_von_hoan FROM fact_tra_hang GROUP BY ban_hang_key) r ON f.ban_hang_key=r.ban_hang_key;
CREATE OR REPLACE VIEW vw_olap_thoi_gian AS SELECT d.nam,d.quy,d.thang,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra FROM vw_sales_net f JOIN dim_thoi_gian d ON f.thoi_gian_key=d.thoi_gian_key GROUP BY d.nam,d.quy,d.thang;
CREATE OR REPLACE VIEW vw_olap_san_pham AS SELECT d.thuong_hieu,d.ten_san_pham,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra FROM vw_sales_net f JOIN dim_san_pham d ON f.san_pham_key=d.san_pham_key GROUP BY d.thuong_hieu,d.ten_san_pham;
CREATE OR REPLACE VIEW vw_olap_cua_hang AS SELECT d.khu_vuc_quan_ly,d.tinh_thanh,d.ten_cua_hang,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra FROM vw_sales_net f JOIN dim_cua_hang d ON f.cua_hang_key=d.cua_hang_key GROUP BY d.khu_vuc_quan_ly,d.tinh_thanh,d.ten_cua_hang;
CREATE OR REPLACE VIEW vw_olap_kenh_ban AS SELECT d.ten_kenh,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra FROM vw_sales_net f JOIN dim_kenh_ban d ON f.kenh_ban_key=d.kenh_ban_key GROUP BY d.ten_kenh;
CREATE OR REPLACE VIEW vw_olap_khuyen_mai AS SELECT d.ten_khuyen_mai,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.so_luong_tra)/NULLIF(SUM(f.so_luong),0) ty_le_tra FROM vw_sales_net f JOIN dim_khuyen_mai d ON f.khuyen_mai_key=d.khuyen_mai_key GROUP BY d.ten_khuyen_mai;
CREATE OR REPLACE VIEW vw_olap_cube AS
SELECT p.thuong_hieu,k.ten_kenh,SUM(f.doanh_thu_thuan) doanh_thu_thuan FROM vw_sales_net f JOIN dim_san_pham p ON p.san_pham_key=f.san_pham_key JOIN dim_kenh_ban k ON k.kenh_ban_key=f.kenh_ban_key GROUP BY p.thuong_hieu,k.ten_kenh
UNION ALL SELECT p.thuong_hieu,NULL,SUM(f.doanh_thu_thuan) FROM vw_sales_net f JOIN dim_san_pham p ON p.san_pham_key=f.san_pham_key GROUP BY p.thuong_hieu
UNION ALL SELECT NULL,k.ten_kenh,SUM(f.doanh_thu_thuan) FROM vw_sales_net f JOIN dim_kenh_ban k ON k.kenh_ban_key=f.kenh_ban_key GROUP BY k.ten_kenh
UNION ALL SELECT NULL,NULL,SUM(doanh_thu_thuan) FROM vw_sales_net;
CREATE OR REPLACE VIEW vw_olap_gia_tieu_thu AS
SELECT p.ma_sku,p.ten_san_pham,p.thuong_hieu,d.nam,d.thang,SUM(f.doanh_thu)/NULLIF(SUM(f.so_luong),0) gia_ban_binh_quan,SUM(f.so_luong) so_luong_ban,SUM(f.so_luong_tra) so_luong_tra,SUM(f.doanh_thu_thuan) doanh_thu_thuan
FROM vw_sales_net f JOIN dim_san_pham p USING(san_pham_key) JOIN dim_thoi_gian d USING(thoi_gian_key)
GROUP BY p.ma_sku,p.ten_san_pham,p.thuong_hieu,d.nam,d.thang;
CREATE OR REPLACE VIEW vw_olap_thuong_hieu_kenh AS
SELECT p.thuong_hieu,k.ten_kenh,SUM(f.so_luong) so_luong_ban,SUM(f.doanh_thu_thuan) doanh_thu_thuan,SUM(f.loi_nhuan) loi_nhuan,COUNT(DISTINCT f.ma_don_hang) so_don_hang
FROM vw_sales_net f JOIN dim_san_pham p USING(san_pham_key) JOIN dim_kenh_ban k USING(kenh_ban_key)
GROUP BY p.thuong_hieu,k.ten_kenh;
