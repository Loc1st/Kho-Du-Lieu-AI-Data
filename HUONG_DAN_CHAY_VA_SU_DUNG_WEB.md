# Hướng dẫn chạy và sử dụng Web

## Chuẩn bị Windows

Cần Python, MariaDB/MySQL đang lắng nghe và quyền tạo `phone_source`, `phone_dw`. Với XAMPP, mở Control Panel và Start MySQL. Không mặc định mật khẩu rỗng; dùng thông tin kết nối của máy. Mở PowerShell ở thư mục chứa `run_all.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m common.check_connection
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe web_app.py
```

Giữ `.env` hiện có và mật khẩu; chỉ sửa host/port/user/password khi cần. Các tên database cũ trong `.env` được ứng dụng thay bằng `phone_source`, `phone_dw`. Không đổi tên hoặc xóa database cũ để chạy dự án.

Truy cập http://localhost:8050 bằng Chrome/Edge/Firefox. Giữ cửa sổ server mở; Ctrl+C để dừng. File HTML không có server không thay thế được kết nối dữ liệu thật; các bản snapshot giáo dục cũ không phải dashboard hiện hành.

## Chạy từng bước và chạy lại an toàn

`run_all.py` nhận mode `init`, `generate`, `etl`, `scd2`, `tests`, `olap`, `benchmark`, `all` (mặc định). `all` tái sử dụng nguồn đã có từ 50.000 đơn trở lên, mặc định sinh 60.000 đơn với seed 2026 khi cần. Generator từ chối ghi lại khi nguồn đã có đơn để giữ dữ liệu hiện hữu; nếu nguồn có dưới ngưỡng, cần xem trạng thái thay vì mặc định cho rằng lệnh đã bổ sung đủ đơn.

```powershell
.\.venv\Scripts\python.exe run_all.py init
.\.venv\Scripts\python.exe run_all.py generate --orders 60000 --seed 2026
.\.venv\Scripts\python.exe run_all.py etl
.\.venv\Scripts\python.exe run_all.py scd2
.\.venv\Scripts\python.exe run_all.py tests
.\.venv\Scripts\python.exe run_all.py olap
.\.venv\Scripts\python.exe run_all.py benchmark
# Kiểm chứng chạy lặp trên nguồn không thay đổi:
.\.venv\Scripts\python.exe run_all.py etl
```

Ưu tiên `all` hoặc `etl` cho lần chạy lại thường ngày. `--orders` tối thiểu 50.000. Trong đợt tiếp tục hiện tại, **không reset**: giữ nguyên dữ liệu và thay đổi SCD2. CLI vẫn có cơ chế reset bảo vệ bằng hai cờ `--reset` và `--confirm-reset phone-sales`, chỉ cho phép hai tên database điện thoại cố định; đây không phải bước vận hành được yêu cầu trong đợt này. Không có cờ `--force-generate`.

## IntelliJ IDEA

1. Open thư mục dự án; chọn Python interpreter là `.venv\Scripts\python.exe` trong cấu hình Python/plugin tương ứng. Nếu chưa có Python runner, dùng Terminal tích hợp với các lệnh trên.
2. Run Configuration cho `run_all.py`: working directory là thư mục gốc, parameters `all`. Chạy và đọc exit code, các lỗi kết nối hoặc kiểm thử.
3. Tạo configuration riêng cho `web_app.py`, cùng interpreter và working directory. Chạy sau pipeline, mở localhost:8050.
4. Để thử ETL lặp, tạo configuration `run_all.py` parameters `etl`; không thêm reset vào cấu hình mặc định.

## Thao tác trên Web

- Dashboard: chọn thời gian bán, thương hiệu/sản phẩm, cửa hàng/khu vực và kênh theo bộ lọc hiện có. Đối chiếu KPI và cả sáu biểu đồ sau mỗi thay đổi; đặt lại bộ lọc để về toàn bộ dữ liệu. Lát cắt trống phải hiển thị không có dữ liệu.
- SCD2: tìm mã cửa hàng có thật, xem lịch sử; chọn khu vực mới và ngày hiệu lực hợp lệ rồi thực hiện thay đổi. Kiểm tra phiên bản cũ kết thúc đúng ngày phiên bản mới bắt đầu. Giao dịch bán trước/sau mốc thuộc đúng khu vực. Lặp cùng khu vực trả no-op; khu vực khác tại đúng mốc đã có bị từ chối, cần chọn ngày khác.
- ETL/kiểm thử: chạy ETL rồi đọc run_id, log, DQ và reject; chạy kiểm thử thật và đọc từng PASS/FAIL. Không xem số lượng lỗi giảm là bằng chứng đủ nếu chưa đối soát.
- SQL: thử SELECT trên bảng/view kho cho phép; kết quả bị giới hạn. Đây không phải console quản trị; DDL/DML, nhiều câu lệnh và tham chiếu database khác bị từ chối.

Bộ lọc ngày là **ngày bán gốc**, không phải ngày hoàn tiền. Trả hàng năm 2027 cho đơn 2026 vẫn giảm doanh thu cohort 2026. [Mapping](docs/mapping.md) có công thức chi tiết.

## Kiểm thử, benchmark và kết quả

`tests/run_dq_tests.py` thực thi 10 ca thật:

| Ca | Nội dung |
|---|---|
| TC01 | Đối soát dòng nguồn đã xử lý với nạp và loại |
| TC02 | Không trùng khóa nghiệp vụ hai fact |
| TC03 | Giá/số lượng hợp lệ, giảm giá không vượt giá trị bán |
| TC04 | Không có FK mồ côi |
| TC05 | Công thức doanh thu bán và thuần |
| TC06 | Công thức giá vốn thuần và lợi nhuận |
| TC07 | Lượng trả, tiền hoàn, giá vốn hoàn không vượt dòng bán |
| TC08 | Khoảng SCD2, một current và khóa fact đúng lịch sử |
| TC09 | Chạy lại ETL thật, so toàn bộ khóa/giá trị bằng snapshot/hash |
| TC10 | Năm câu hỏi quản lý và năm grain benchmark được đối soát nguồn/kho |

Kết quả: `output/phone_sales/test_cases_result.json` và `.csv`. Benchmark chạy truy vấn tương đương trên hai database, warm-up, đo nhiều lần gồm fetch kết quả và so equality. Đọc `benchmark_result.csv`, `olap_reconciliation.json` cùng các file `olap_business_Q1_brand_model.csv`, `olap_business_Q2_year_quarter_month.csv`, `olap_business_Q3_brand_channel.csv`, `olap_business_Q4_sku_month_price_quantity.csv`, `olap_business_Q5_region_store.csv` và `benchmark_query_Q1_month.csv`, `benchmark_query_Q2_sku.csv`, `benchmark_query_Q3_store.csv`, `benchmark_query_Q4_channel.csv`, `benchmark_query_Q5_promotion.csv` trong thư mục này. Không mặc định DW nhanh hơn: tỷ lệ thời gian có thể nhỏ hơn 1, tùy cache, dữ liệu, index và máy.

## Xử lý lỗi thường gặp

- Không kết nối: kiểm tra MySQL đã chạy, host/port và credentials; không ghi mật khẩu ra log.
- Thiếu bảng: chạy `run_all.py init`, sau đó `all`; không dùng reset như bước sửa lỗi đầu tiên.
- Cổng 8050 đã dùng: dừng server cũ do mình chạy rồi khởi động lại; không mở nhiều server cùng cổng.
- Web báo lỗi hoặc biểu đồ trống: xem thông báo API, terminal server, bộ lọc và kết quả ETL; không dùng dữ liệu cũ để che lỗi.
- Kiểm thử FAIL/benchmark không khớp: giữ báo cáo và run_id, sửa nguyên nhân rồi chạy lại. Không đổi FAIL thành PASS trong tệp báo cáo.

## Sinh CSV khi chưa có database

```powershell
.\.venv\Scripts\python.exe -m generator.generate_data --csv-only --orders 60000 --seed 2026
```

Lệnh này chỉ sinh dữ liệu dưới `data/phone_sales/`, gồm manifest mới; không chứng minh ETL, SQL hay Web đã chạy được. Log ETL mới xuất dưới dạng `etl_log_latest.json`, `etl_data_quality_latest.json`, `etl_reject_latest.json` trong `output/phone_sales/`. Benchmark mặc định một warm-up không tính giờ và 5 lần đo cho mỗi truy vấn/mỗi hệ; `source_over_dw` là median nguồn chia median kho, lớn hơn 1 mới có nghĩa kho nhanh hơn trong phép đo đó.
