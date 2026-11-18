# Mapping nguồn → kho và định nghĩa KPI

Tên bảng/cột chuẩn căn cứ `sql/01_create_source_db.sql`, `sql/02_create_dw.sql`; ERD ở [ARCHITECTURE.md](ARCHITECTURE.md), kiểu dữ liệu ở [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Dimension

| Đích | Nguồn | Chuyển đổi / lookup |
|---|---|---|
| `dim_thoi_gian` | Lịch ngày bao phủ ngày bán và trả | `thoi_gian_key = YYYYMMDD`, tách năm/quý/tháng |
| `dim_san_pham` | `phien_ban_san_pham` → `san_pham` → `thuong_hieu` | Một SKU một khóa; phi chuẩn hóa tên, thương hiệu, RAM, bộ nhớ, màu |
| `dim_cua_hang` | `cua_hang` → `tinh_thanh` + `lich_su_cua_hang` | SCD2 khu vực; duy nhất mã + ngày hiệu lực; một current; khoảng nửa mở |
| `dim_khach_hang` | `khach_hang` → `tinh_thanh` | Khóa theo mã khách; chuẩn hóa khoảng trắng ở tên/nhãn |
| `dim_kenh_ban` | `kenh_ban` | Mã kênh duy nhất, giữ tên mô tả |
| `dim_khuyen_mai` | `khuyen_mai` | Mã khuyến mại duy nhất; không khuyến mại dùng mã NONE; kiểm tra ngày bán trong hiệu lực chương trình ở nguồn, không đưa ngày khuyến mại thành chiều mới |

## Fact và kiểm tra nghiệp vụ

| Đích | Nguồn | Quy tắc |
|---|---|---|
| `fact_ban_hang.ma_chi_tiet`, `ma_don_hang` | `chi_tiet_don_hang` + `don_hang` | Nạp `COMPLETED`, `PARTIALLY_RETURNED`, `RETURNED`; loại `CANCELLED`; mã dòng là khóa nghiệp vụ để chạy lặp |
| Sáu FK của fact bán | Đầu đơn, SKU, mã khuyến mại | Lookup dimension; cửa hàng theo **ngày đặt** trong khoảng hiệu lực |
| `so_luong`, `don_gia`, `giam_gia`, `gia_von` | Chi tiết đơn | Số lượng > 0; tiền không âm; giảm giá là tổng dòng, không vượt số lượng × đơn giá; giá vốn là tổng dòng |
| `doanh_thu` | Số lượng × đơn giá − giảm giá | Tính bằng Decimal, lưu `DECIMAL(18,2)` |
| `fact_tra_hang.ma_chi_tiet_tra` | `chi_tiet_tra_hang` + `tra_hang` | Mỗi dòng trả một record; tra fact bán gốc |
| `fact_tra_hang.thoi_gian_key` | `tra_hang.ngay_tra` | Không trước ngày bán; trả lũy kế không vượt số lượng bán |
| `tien_hoan`, `gia_von_hoan` | Tiền hoàn nguồn, giá vốn bán phân bổ theo lượng trả | Tiền không âm; tổng hoàn không vượt doanh thu dòng; giá vốn hoàn không vượt giá vốn bán; làm tròn HALF_UP 2 chữ số và chặn giá vốn hoàn theo phần giá vốn còn lại |
| `stg_import` | Nguồn thô | Payload và khóa nguồn gắn `run_id` phục vụ truy vết |
| `etl_reject` | `raw_import_error` và dòng không hợp lệ | `source_id`, `reason`, payload, `run_id`; lỗi nhập thô không đi vào bảng 3NF có ràng buộc |
| `etl_log`, `etl_data_quality` | Mỗi lượt ETL | Dòng đọc/nạp/loại, trạng thái, cách xử lý, `run_id` |

Không sửa tiền sai thành 0 để làm cho kiểm thử PASS. Phải giải thích bằng reject hoặc quy tắc làm sạch xác định. Khóa nghiệp vụ UNIQUE và upsert bảo đảm chạy lặp; lịch sử log/reject được giữ theo từng lượt nên số dòng log có thể tăng dù fact không tăng.

## Công thức tổng hợp

Gọi `B` là các dòng bán hợp lệ sau lọc **ngày bán** và các chiều; `R(B)` là mọi dòng trả liên kết với B, kể cả trả ngoài khoảng ngày lọc.

| Chỉ số | Công thức |
|---|---|
| Doanh thu bán | `SUM(B.so_luong * B.don_gia - B.giam_gia)` |
| Doanh thu thuần | `SUM(B.doanh_thu) - SUM(R(B).tien_hoan)` |
| Giá vốn thuần | `SUM(B.gia_von) - SUM(R(B).gia_von_hoan)` |
| Lợi nhuận gộp | Doanh thu thuần − giá vốn thuần |
| Biên lợi nhuận | Lợi nhuận gộp / doanh thu thuần |
| Tỷ lệ trả theo lượng | `SUM(R(B).so_luong_tra) / SUM(B.so_luong)` |
| AOV | Doanh thu thuần / `COUNT(DISTINCT B.ma_don_hang)` |

Dùng `NULLIF(mau_so,0)`; tập rỗng hiển thị không có dữ liệu, không diễn giải tỷ lệ thiếu mẫu số là 0% thành công. Đơn đã trả hết vẫn là đơn bán hợp lệ trong mẫu số AOV; không đếm đơn hủy. Khi lọc SKU, AOV là doanh thu các dòng SKU được chọn trên số đơn chứa các dòng ấy.

Ví dụ bán 31/12/2026, trả 05/01/2027: dashboard lọc tháng 12/2026 đã trừ khoản hoàn đó. Báo cáo vận hành hoàn tiền tháng 01/2027 lọc ngày trả trên `fact_tra_hang` sẽ ghi nhận khoản này trong tháng 1. Hai báo cáo trả lời hai câu hỏi khác nhau.

## Năm câu hỏi OLAP

1. Thương hiệu, dòng máy/SKU nào có sản lượng, doanh thu thuần và lợi nhuận nổi bật? Drill-down thương hiệu → sản phẩm → SKU.
2. Doanh thu và lượng bán biến động thế nào theo mùa? Roll-up tháng → quý → năm, drill-down ngược lại.
3. Thương hiệu nào hiệu quả trên từng kênh? Slice/dice thương hiệu × kênh; CUBE mô phỏng bằng các grouping set tương ứng.
4. Giá bán bình quân và lượng tiêu thụ có liên hệ thế nào ở grain SKU × tháng có bán? Scatter và Pearson; giá bình quân = doanh thu sau giảm giá trước hoàn / lượng bán.
5. Khu vực/tỉnh/cửa hàng nào hiệu quả? Dùng phiên bản khu vực tại ngày bán, tránh chuyển toàn bộ doanh số cũ sang khu vực hiện tại.

Phân tích khuyến mại là lát cắt bổ sung và một grain benchmark, không thay thế câu hỏi giá–lượng. Năm grain benchmark là tháng, SKU, cửa hàng, kênh và khuyến mại; tệp mang tiền tố `benchmark_query_`. Năm câu hỏi quản lý xuất tiền tố `olap_business_`; không nhầm hai bộ này.

Các câu SQL nằm trong `sql/05_olap_queries.sql`; `vw_olap_cube` hỗ trợ tổng hợp nhiều chiều. Scatter plot mô tả liên hệ giữa giá bán trung bình sau giảm giá và số máy bán ở grain SKU × tháng có bán. Nếu tính Pearson r cần nêu số quan sát, grain, loại dữ liệu thiếu và trường hợp phương sai bằng 0. Tương quan không chứng minh khuyến mại gây tăng doanh số: mùa vụ, thương hiệu, lượng tồn, cửa hàng và cơ chế dữ liệu giả lập đều có thể gây nhiễu. Không coi chênh lệch nhóm hoặc đường xu hướng là kết quả kiểm định nhân quả.


Nguồn `nhan_vien` kiểm tra đơn có nhân viên thuộc đúng cửa hàng, nhưng không ánh xạ thành chiều thứ bảy. Đơn `PARTIALLY_RETURNED`/`RETURNED` vẫn được nạp; khoản hoàn chỉ trừ qua fact trả, tránh loại cả đơn rồi trừ thêm lần nữa. Nhãn phiếu trả `PARTIAL`/`FULL` không thay thế đối soát lượng và tiền. Sai ràng buộc của giao dịch nguồn hợp lệ (ví dụ khuyến mại ngoài hiệu lực hoặc lịch sử cửa hàng chồng lấn) làm ETL thất bại và rollback; lỗi envelope nhập thô được ghi reject riêng.
