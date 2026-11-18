# XÂY DỰNG KHO DỮ LIỆU PHỤC VỤ PHÂN TÍCH HOẠT ĐỘNG BÁN ĐIỆN THOẠI DI ĐỘNG

Đồ án xây dựng kho dữ liệu để phân tích doanh thu, lợi nhuận, lượng điện thoại tiêu thụ, trả hàng và hiệu quả cửa hàng. Hệ thống sử dụng Python, MariaDB, ETL, Star Schema, OLAP và Dashboard Web theo kiến trúc MVC với Chart.js. Dữ liệu mô phỏng phục vụ học tập, không đại diện cho thị trường thực tế.

## Mục tiêu phân tích

1. Xác định thương hiệu và mẫu điện thoại có doanh thu, lượng bán và lợi nhuận cao nhất.
2. Phân tích biến động doanh thu, lợi nhuận theo năm, quý và tháng.
3. So sánh doanh thu giữa thương hiệu và kênh bán hàng.
4. Khảo sát tương quan giá bán và lượng tiêu thụ theo SKU, thời gian.
5. Đánh giá khu vực và cửa hàng theo doanh thu, lợi nhuận và tỷ lệ trả hàng.

## Kiến trúc hệ thống

```text
Sinh dữ liệu bán điện thoại → phone_source (OLTP, 3NF)
                           → Extract → Staging → Transform → Load
                           → phone_dw (Star Schema) → OLAP → API → Dashboard
```

Nguồn `phone_source` có 13 bảng nghiệp vụ chuẩn hóa 3NF cùng lịch sử cửa hàng và nhập lỗi thô (15 bảng); kho `phone_dw` có **6 dimension và 2 fact**. Nguồn có nhân viên, khuyến mại theo mùa với ngày hiệu lực, và trạng thái trả một phần/toàn bộ. Ngày bán thuộc 2024–2026; ngày trả có thể sang 2027. Chiều cửa hàng lưu lịch sử khu vực quản lý bằng SCD Type 2.

- Dimension: thời gian, sản phẩm, cửa hàng, khách hàng, kênh bán, khuyến mại.
- `fact_ban_hang`: một dòng chi tiết đơn hàng hợp lệ; loại đơn hủy.
- `fact_tra_hang`: một dòng chi tiết trả hàng, tham chiếu dòng bán gốc.
- ETL lưu `run_id`, nhật ký, thống kê chất lượng và bản ghi bị loại; chạy lặp không nhân đôi giao dịch hoặc mất lịch sử SCD2.

## Chức năng Dashboard

| Tab | Nội dung |
|---|---|
| Phân tích kinh doanh | Bộ lọc đa chiều, sáu KPI và sáu biểu đồ từ API/database |
| Lịch sử cửa hàng | Tìm cửa hàng, xem các phiên bản SCD2, so sánh doanh thu và mô phỏng chuyển khu vực |
| ETL & Data Quality | Nhật ký, lỗi dữ liệu, 10 bài kiểm thử và benchmark OLTP/DW |
| SQL Playground | Chạy SELECT có giới hạn trên `phone_source` hoặc `phone_dw` |

## Chạy trên Windows

Mở PowerShell tại thư mục dự án, bật MariaDB/MySQL rồi chạy:

```powershell
if (-not (Test-Path .venv\Scripts\python.exe)) { py -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Chỉ tạo .env khi chưa có; không ghi đè mật khẩu hiện tại.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m common.check_connection
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe web_app.py
```

Mở http://localhost:8050. Điền `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` theo máy trong `.env`. Tên database cố định thành `phone_source` và `phone_dw`; tên nguồn/kho cũ trong `.env` không chuyển truy vấn sang database cũ. Không đưa mật khẩu vào báo cáo hoặc Git.

Lệnh mặc định tái sử dụng dữ liệu nguồn đã có, chạy ETL, SCD2 demo, kiểm thử, OLAP và benchmark. Không tự reset database. Xem [hướng dẫn chạy](HUONG_DAN_CHAY_VA_SU_DUNG_WEB.md) cho cấu hình Windows và IntelliJ IDEA.

Các bước cũng có thể chạy riêng:

```powershell
.\.venv\Scripts\python.exe run_all.py init
.\.venv\Scripts\python.exe run_all.py generate
.\.venv\Scripts\python.exe run_all.py etl
.\.venv\Scripts\python.exe run_all.py scd2
.\.venv\Scripts\python.exe run_all.py tests
.\.venv\Scripts\python.exe run_all.py olap
.\.venv\Scripts\python.exe run_all.py benchmark
```

## Dữ liệu và kiểm thử

Bộ sinh mặc định dùng seed 2026, tạo 60.000 đơn, nhiều SKU, cửa hàng, kênh bán, khách mua lặp và khuyến mại theo mùa. CSV cùng manifest lỗi nằm trong `data/phone_sales/`. Lỗi được chèn có kiểm soát và loại khỏi Fact khi không hợp lệ.

Mười bài kiểm thử bao gồm đối soát số dòng, loại trùng, giá/lượng, khóa ngoại, doanh thu, lợi nhuận, giới hạn trả, khoảng SCD2, ETL idempotency và đối chiếu OLAP giữa OLTP/DW. Benchmark đo thời gian thực tế và kiểm tra kết quả tương đương; không giả định DW luôn nhanh hơn. Kết quả CSV/JSON, log và ảnh kiểm thử nằm trong `output/phone_sales/`.

## Chỉ số và cách đọc

- Doanh thu thuần = doanh thu bán sau giảm giá − tiền hoàn.
- Giá vốn thuần = tổng giá vốn bán − giá vốn hàng trả; lợi nhuận gộp = doanh thu thuần − giá vốn thuần.
- Tỷ lệ trả = tổng số lượng trả / tổng số lượng bán; AOV = doanh thu thuần / số đơn hợp lệ phân biệt.
- Bộ lọc ngày chọn **ngày bán gốc** (sale cohort), gồm các lượt trả của những dòng bán đó. Báo cáo theo ngày trả dùng thời gian của `fact_tra_hang`, có ý nghĩa khác.

Tiền dùng `DECIMAL(18,2)`/`Decimal`. Không lấy trung bình các tỷ lệ nhóm để tính tỷ lệ tổng.

## Tài liệu và mã nguồn

| Nội dung | Vị trí |
|---|---|
| Kiến trúc, ERD, star schema | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Mapping và KPI | [docs/mapping.md](docs/mapping.md) |
| Từ điển dữ liệu | [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) |
| Demo | [docs/KICH_BAN_DEMO_VA_THUYET_TRINH.md](docs/KICH_BAN_DEMO_VA_THUYET_TRINH.md) |
| Trạng thái | [PROJECT_STATE.md](PROJECT_STATE.md) |
| Báo cáo nghiệm thu và bằng chứng thực tế | [PHONE_SALES_IMPLEMENTATION_REPORT.md](PHONE_SALES_IMPLEMENTATION_REPORT.md) |
| Tạo dữ liệu / ETL / kiểm thử / benchmark | `generator/`, `etl/`, `tests/`, `analysis/` |
| Web MVC | `mvc/`, `web/`, `web_app.py` |
| Dữ liệu và kết quả hiện hành | `data/phone_sales/`, `output/phone_sales/` |

Hai database của đề tài này là `phone_source` và `phone_dw`. Hệ thống không phụ thuộc database của đề tài khác. Các kết quả chạy trước được lưu để tham khảo; khi cần đánh giá trạng thái hiện tại, hãy chạy kiểm thử và đọc báo cáo mới trong `output/phone_sales/`.
