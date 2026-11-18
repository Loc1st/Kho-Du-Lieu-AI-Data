# Từ điển dữ liệu

Nguồn chuẩn: `sql/01_create_source_db.sql`, `sql/02_create_dw.sql`. PK = khóa chính, FK = khóa ngoại, UK = duy nhất. Chuỗi dùng utf8mb4. Tiền có đơn vị đồng Việt Nam trong dữ liệu demo, `DECIMAL(18,2)`; số lượng là số nguyên chiếc. Giá trị tiền của một dòng là tổng dòng trừ khi ghi rõ đơn giá.

## Nguồn `phone_source`

13 bảng nghiệp vụ + `lich_su_cua_hang`, `raw_import_error` = 15 bảng. Generator sinh 16 mã khuyến mại mùa vụ; database nâng cấp giữ thêm 4 mã cũ không dùng nên có thể đếm 20. Đây là bảo toàn danh mục, không phải 20 chương trình được generator hiện hành sinh.

| Bảng | Cột và kiểu | Ý nghĩa / ràng buộc |
|---|---|---|
| `thuong_hieu` | `ma_thuong_hieu VARCHAR(20)` PK; `ten_thuong_hieu VARCHAR(100)` | Danh mục hãng |
| `san_pham` | `ma_san_pham VARCHAR(20)` PK; `ten_san_pham VARCHAR(120)`; `ma_thuong_hieu VARCHAR(20)` FK | Dòng máy thuộc một hãng |
| `phien_ban_san_pham` | `ma_sku VARCHAR(30)` PK; `ma_san_pham VARCHAR(20)` FK; `ram_gb INT`, `bo_nho_gb INT`; `mau_sac VARCHAR(30)` | SKU theo cấu hình/màu; RAM và bộ nhớ > 0 |
| `tinh_thanh` | `ma_tinh VARCHAR(10)` PK; `ten_tinh VARCHAR(100)` UK | Danh mục địa lý mô phỏng; không tuyên bố danh mục hành chính hiện hành |
| `cua_hang` | `ma_cua_hang VARCHAR(20)` PK; `ten_cua_hang VARCHAR(100)`; `ma_tinh VARCHAR(10)` FK | Điểm bán; khu vực quản lý lưu riêng trong lịch sử |
| `khach_hang` | `ma_khach_hang VARCHAR(20)` PK; `ho_ten VARCHAR(100)`; `ma_tinh VARCHAR(10)` FK | Khách hàng giả lập |
| `kenh_ban` | `ma_kenh VARCHAR(20)` PK; `ten_kenh VARCHAR(100)` | Kênh giao dịch |
| `khuyen_mai` | `ma_khuyen_mai VARCHAR(20)` PK; `ten_khuyen_mai VARCHAR(100)`; `ngay_bat_dau DATE`, `ngay_ket_thuc DATE` | Chương trình áp dụng cho dòng hàng; bắt đầu ≤ kết thúc; ngày bán nằm trong khoảng gồm hai cận |
| `nhan_vien` | `ma_nhan_vien VARCHAR(20)` PK; `ho_ten VARCHAR(100)`; `ma_cua_hang VARCHAR(20)` FK | Nhân viên thuộc cửa hàng, đơn tham chiếu nhân viên phụ trách |
| `don_hang` | `ma_don_hang VARCHAR(25)` PK; `ngay_dat DATE`; `ma_nhan_vien`, `ma_cua_hang`, `ma_khach_hang`, `ma_kenh VARCHAR(20)` FK; `trang_thai VARCHAR(20)` | `COMPLETED`, `PARTIALLY_RETURNED`, `RETURNED`, `CANCELLED`; ba trạng thái đầu vào fact bán, hủy bị loại; index ngày đặt |
| `chi_tiet_don_hang` | `ma_chi_tiet VARCHAR(30)` PK; `ma_don_hang VARCHAR(25)` FK; `ma_sku VARCHAR(30)` FK; `ma_khuyen_mai VARCHAR(20)` FK; `so_luong INT`; `don_gia`, `giam_gia`, `gia_von DECIMAL(18,2)` | Lượng > 0; tiền ≥ 0; giảm giá tổng dòng ≤ lượng × đơn giá; giá vốn tổng dòng |
| `tra_hang` | `ma_tra_hang VARCHAR(30)` PK; `ngay_tra DATE`; `trang_thai VARCHAR(20)`; `ly_do VARCHAR(100)` | Đầu phiếu trả; `PARTIAL` hoặc `FULL`, index ngày trả. Nhãn thể hiện mức trả của dòng bán liên quan; tiền/lượng vẫn tính từ chi tiết, không suy ra từ nhãn |
| `chi_tiet_tra_hang` | `ma_chi_tiet_tra VARCHAR(30)` PK; `ma_tra_hang`, `ma_chi_tiet VARCHAR(30)` FK; `so_luong_tra INT`; `tien_hoan DECIMAL(18,2)` | Lượng trả > 0, tiền hoàn ≥ 0; ETL kiểm tra lũy kế và ngày |
| `lich_su_cua_hang` | PK (`ma_cua_hang VARCHAR(20)`, `ngay_hieu_luc DATE`); `khu_vuc_quan_ly VARCHAR(100)` | Một mốc thay đổi khu vực; mã cửa hàng là FK |
| `raw_import_error` | `raw_id VARCHAR(40)` PK; `loai_loi VARCHAR(50)`; `payload LONGTEXT` | JSON_VALID; không FK để giữ được lỗi tham chiếu; không phải giao dịch hợp lệ |

Các cột nguồn trên đều NOT NULL theo DDL. PK/FK/check bảo vệ nguồn hợp lệ; các ràng buộc liên dòng như tổng lượng trả cần kiểm tra nghiệp vụ bổ sung.

## Dimension `phone_dw`

| Bảng | Cột | Kiểu / ý nghĩa |
|---|---|---|
| `dim_thoi_gian` | `thoi_gian_key`, `ngay`, `nam`, `quy`, `thang` | INT PK dạng YYYYMMDD; DATE UK; các phần lịch INT, NOT NULL |
| `dim_san_pham` | `san_pham_key`, `ma_sku`, `ten_san_pham`, `thuong_hieu`, `ram_gb`, `bo_nho_gb`, `mau_sac` | INT PK tự tăng; VARCHAR(30) UK NOT NULL; VARCHAR(120), VARCHAR(100), INT, INT, VARCHAR(30) |
| `dim_cua_hang` | `cua_hang_key`, `ma_cua_hang`, `ten_cua_hang`, `tinh_thanh`, `khu_vuc_quan_ly`, `ngay_hieu_luc`, `ngay_het_han`, `is_current` | INT PK; VARCHAR(20); ba nhãn VARCHAR(100); DATE, DATE, BOOLEAN. UK (mã, hiệu lực); hiệu lực < hết hạn |
| `dim_khach_hang` | `khach_hang_key`, `ma_khach_hang`, `ho_ten`, `tinh_thanh` | INT PK; VARCHAR(20) UK NOT NULL; hai VARCHAR(100) |
| `dim_kenh_ban` | `kenh_ban_key`, `ma_kenh`, `ten_kenh` | INT PK; VARCHAR(20) UK NOT NULL; VARCHAR(100) |
| `dim_khuyen_mai` | `khuyen_mai_key`, `ma_khuyen_mai`, `ten_khuyen_mai` | INT PK; VARCHAR(20) UK NOT NULL; VARCHAR(100) |

Các khóa dimension tự tăng trừ khóa lịch. Nhãn mô tả có thể NULL theo DDL; ETL có trách nhiệm chuẩn hóa/kiểm tra. `dim_cua_hang` có mã, khu vực và trường hiệu lực NOT NULL; hết hạn là cận **loại trừ**, current dùng mốc kết thúc xa theo triển khai. Không nối fact theo `is_current=1` để làm báo cáo lịch sử.

## Fact và view

| Bảng / cột | Kiểu / ý nghĩa |
|---|---|
| `fact_ban_hang.ban_hang_key` | BIGINT PK tự tăng |
| `ma_chi_tiet`, `ma_don_hang` | VARCHAR(30) UK và VARCHAR(25), NOT NULL; mã đơn có thể lặp trên nhiều dòng |
| `thoi_gian_key`, `san_pham_key`, `cua_hang_key`, `khach_hang_key`, `kenh_ban_key`, `khuyen_mai_key` | INT FK NOT NULL; khóa thời gian là ngày bán |
| `so_luong` | INT NOT NULL > 0 |
| `don_gia`, `giam_gia`, `doanh_thu`, `gia_von` | DECIMAL(18,2) NOT NULL ≥ 0; đơn giá mỗi chiếc, còn lại tổng dòng |
| `fact_tra_hang.tra_hang_key` | BIGINT PK tự tăng |
| `ma_chi_tiet_tra`, `ban_hang_key`, `thoi_gian_key` | VARCHAR(30) UK; BIGINT FK tới dòng bán; INT FK ngày trả; đều NOT NULL |
| `so_luong_tra`, `tien_hoan`, `gia_von_hoan` | INT > 0; hai DECIMAL(18,2) ≥ 0, NOT NULL; giá vốn hoàn theo lượng trả |
| `vw_sales_net` | Mỗi dòng bán + tổng `so_luong_tra`, `tien_hoan`, `gia_von_hoan`; dẫn xuất `doanh_thu_thuan`, `gia_von_thuan`, `loi_nhuan` |

## Staging và audit

| Bảng | Trường chính | Công dụng |
|---|---|---|
| `stg_import` | `staging_id BIGINT` PK; `run_id VARCHAR(32)`; `source_table VARCHAR(80)`, `source_id VARCHAR(50)`, `payload LONGTEXT` | Giữ bản thô theo lượt |
| `etl_log` | `log_id BIGINT` PK; `run_id VARCHAR(32)`; `buoc VARCHAR(40)`, `bang VARCHAR(80)`; `so_dong_doc/nap/loai INT`; `ghi_chu TEXT`, `status VARCHAR(20)`, `created_at TIMESTAMP` | Tiến độ và kết quả lượt chạy |
| `etl_data_quality` | `dq_id BIGINT` PK; `run_id VARCHAR(32)`; `bang VARCHAR(80)`, `loai_kiem_tra VARCHAR(80)`; `so_dong_truoc/sau INT`, `cach_xu_ly TEXT` | Số lượng và xử lý lỗi |
| `etl_reject` | `reject_id BIGINT` PK; `run_id VARCHAR(32)`; `bang VARCHAR(80)`, `source_id VARCHAR(50)`, `reason VARCHAR(100)`, `payload LONGTEXT` | Truy nguyên dòng bị loại |

`run_id` NOT NULL và có index ở cả bốn bảng. Không cộng reject của nhiều lượt để đối soát một lượt; không dùng MAX của UUID để xác định thời gian mới nhất. Kiểm tra log theo thời điểm và run_id cụ thể.
