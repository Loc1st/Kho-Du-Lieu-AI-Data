# PHONE SALES DATA WAREHOUSE — Báo cáo triển khai và kiểm thử

Ngày kiểm chứng: **17/11/2026**, trên Windows, Python trong `.venv` và **MariaDB 10.4.32**. Triển khai trực tiếp tại `D:\HK1 nam 3\Kho_Du_Lieu\codepygit`.

**Kết quả:** `run_all.py` mặc định đã chạy hết với **exit code 0**, mất **296,94 giây**. Mười kiểm thử database đều PASS; chạy lại bộ kiểm thử qua HTTP cũng 10/10 PASS. Dashboard có bốn tab, sáu biểu đồ lấy dữ liệu thật, đã kiểm tra bằng Chrome headless trên desktop và mobile.

## 1. Bảo vệ trạng thái ban đầu và danh sách file

Working tree ban đầu ở nhánh `main`, HEAD `1cb623751b72f8a03166dfb452957eeb1cb73177`. Hai file đã có thay đổi của người dùng là `data/error_manifest.json` và `output/benchmark_result.csv`. Đã giữ nguyên byte của hai file này và `.env`, kiểm chứng bằng SHA-256 trước/sau; không ghi mật khẩu vào báo cáo.

Backup trước sửa: `backups/20261117_214730/workspace_before.zip`, gồm 77 file, có `sha256.json`, `git_status.txt`, `code_inventory.json`. Backup chứa cấu hình cục bộ nên được Git ignore. `.git` và `.venv` không nằm trong ZIP. Không tạo project hoặc clone mới, không tạo commit, không push; HEAD không đổi.

Danh sách dưới đây là thay đổi của đợt triển khai; **không** tính hai file người dùng đã sửa từ trước:

| Thao tác | File |
|---|---|
| Sửa | `.env.example` |
| Sửa | `.gitignore` |
| Sửa | `HUONG_DAN_CHAY_VA_SU_DUNG_WEB.md` |
| Sửa | `PROJECT_STATE.md` |
| Sửa | `README.md` |
| Sửa | `analysis/benchmark.py` |
| Sửa | `chay_web.bat` |
| Sửa | `common/check_connection.py` |
| Sửa | `common/db.py` |
| Sửa | `docs/KICH_BAN_DEMO_VA_THUYET_TRINH.md` |
| Sửa | `docs/mapping.md` |
| Sửa | `etl/demo_scd2.py` |
| Sửa | `etl/extract.py` |
| Sửa | `etl/load.py` |
| Sửa | `etl/pipeline.py` |
| Sửa | `etl/transform.py` |
| Sửa | `generator/generate_data.py` |
| Sửa | `mvc/controllers/etl_controller.py` |
| Sửa | `mvc/controllers/router.py` |
| Sửa | `mvc/controllers/scd2_controller.py` |
| Sửa | `mvc/controllers/sql_controller.py` |
| Sửa | `mvc/models/etl_model.py` |
| Sửa | `mvc/models/olap_model.py` |
| Sửa | `mvc/models/scd2_model.py` |
| Sửa | `mvc/models/sql_model.py` |
| Sửa | `requirements.txt` |
| Sửa | `run_all.py` |
| Sửa | `sql/01_create_source_db.sql` |
| Sửa | `sql/02_create_dw.sql` |
| Sửa | `sql/03_procedures.sql` |
| Sửa | `sql/04_olap_views.sql` |
| Sửa | `sql/05_olap_queries.sql` |
| Sửa | `tests/run_dq_tests.py` |
| Sửa | `web/build_standalone.py` |
| Sửa | `web/dashboard_standalone.html` |
| Sửa | `web/index.html` |
| Sửa | `web_app.py` |
| Thêm | `PHONE_SALES_IMPLEMENTATION_REPORT.md` |
| Thêm | `docs/ARCHITECTURE.md` |
| Thêm | `docs/DATA_DICTIONARY.md` |
| Thêm | `docs/DATA_IMPLEMENTATION_NOTES.md` |
| Thêm | `docs/PHONE_IMPLEMENTATION_PLAN.md` |
| Thêm | `docs/VERIFICATION_NOTES.md` |
| Thêm | `docs/WEB_REVIEW.md` |
| Thêm | `etl/test_scd2.py` |
| Thêm | `tests/api_smoke.py` |
| Thêm | `tests/browser_smoke.mjs` |
| Thêm | `tests/test_web.py` |
| Thêm | `web/app.js` |
| Thêm | `web/vendor/README.md` |
| Thêm | `web/vendor/chart.umd.min.js` |
| Xóa | `common/grading.py` |
| Xóa | `common/reference.py` |
| Xóa | `docs/update_proposal.py` |

CSV nguồn và manifest mới nằm trong `data/phone_sales/`; tất cả bằng chứng chạy nằm trong `output/phone_sales/`. Hai thư mục được ignore để tránh đưa dữ liệu sinh lớn vào Git. File giáo dục `.docx` cũ được giữ làm tài liệu lịch sử, không còn được dùng để chạy hoặc hướng dẫn hệ thống mới. Ba module giáo dục không còn dùng đã được xóa khỏi working tree và có trong backup.

## 2. Database mới và độ hạt

`phone_source` có 13 bảng nghiệp vụ chuẩn hóa: `thuong_hieu`, `san_pham`, `phien_ban_san_pham`, `tinh_thanh`, `cua_hang`, `nhan_vien`, `khach_hang`, `kenh_ban`, `khuyen_mai`, `don_hang`, `chi_tiet_don_hang`, `tra_hang`, `chi_tiet_tra_hang`. Thêm `lich_su_cua_hang` và `raw_import_error`: tổng cộng 15 bảng. Dùng snake_case nhất quán trong SQL và Python; bảng tỉnh chuẩn hóa bổ sung để tránh lặp danh mục địa lý. Có PK, FK, UNIQUE, CHECK và chỉ mục cho liên kết. Không tắt kiểm tra FK để chèn lỗi.

Nguồn đã nạp **60.000 đơn**, **83.638 dòng bán**, **6.002 dòng trả**; 5 thương hiệu, 25 mẫu, 100 SKU, 18 cửa hàng, 12.000 khách hàng, 90 nhân viên và 4 kênh. Có tính mùa vụ, khuyến mại theo ngày, mua lặp và trả nhiều lần trên cùng dòng bán. Bộ sinh seed 2026 được chạy hai lần trong bộ nhớ: hash của mọi bảng giống nhau. Mã sản phẩm là danh mục mô phỏng cho đồ án, không đại diện dữ liệu thị trường hoặc lịch phát hành máy thực tế.

Đơn nguồn: 52.764 `COMPLETED`, 2.814 `PARTIALLY_RETURNED`, 2.306 `RETURNED`, 2.116 `CANCELLED`. Ba trạng thái đầu hợp lệ cho fact bán; đơn hủy bị loại. Có 16 mã khuyến mại mùa vụ/không khuyến mại được sử dụng; 4 mã danh mục không còn dùng từ lượt triển khai đầu được bảo toàn, nên nguồn và dimension có tổng 20 mã. Manifest mô tả chính xác 16 mã của fixture sinh hiện hành.

| Bảng kho | Số dòng kiểm chứng | Độ hạt / vai trò |
|---|---:|---|
| `dim_thoi_gian` | 1.461 | Một ngày, 2024–2027 để gồm cả ngày trả |
| `dim_san_pham` | 100 | Một SKU |
| `dim_cua_hang` | 26 | Một phiên bản hiệu lực của cửa hàng; 18 hiện hành, 8 lịch sử |
| `dim_khach_hang` | 12.000 | Một khách hàng |
| `dim_kenh_ban` | 4 | Một kênh bán |
| `dim_khuyen_mai` | 20 | Một mã khuyến mại |
| `fact_ban_hang` | 80.646 | Một dòng chi tiết đơn hợp lệ; business key `ma_chi_tiet` duy nhất |
| `fact_tra_hang` | 6.002 | Một dòng chi tiết trả; FK đến dòng bán gốc, business key `ma_chi_tiet_tra` duy nhất |

Tiền dùng `DECIMAL(18,2)` trong MariaDB và `Decimal` khi ETL. `giam_gia` và `gia_von` là **tổng dòng**, `don_gia` là giá mỗi chiếc. Fact giữ giá và giá vốn tại lúc bán. Return giữ số lượng, tiền hoàn, giá vốn hoàn và ngày trả. View `vw_sales_net` tổng hợp return theo khóa dòng bán **trước** khi nối, nên không nhân doanh thu khi một dòng có nhiều lượt trả.

Định nghĩa KPI: doanh thu bán = lượng × đơn giá − giảm giá; doanh thu thuần = doanh thu bán − hoàn tiền; giá vốn thuần = giá vốn bán − giá vốn hoàn; lợi nhuận gộp = doanh thu thuần − giá vốn thuần; biên = lợi nhuận/doanh thu thuần; số đơn đếm DISTINCT trên dân số hợp lệ; AOV = doanh thu thuần/số đơn; tỷ lệ trả = lượng trả/lượng bán. Chia cho 0 được xử lý rõ. Dashboard lọc **ngày bán gốc**, quy trả hàng về cohort bán; ngày trả vẫn có khóa thời gian riêng để truy vấn.

ERD, star schema, từ điển và mapping: [ARCHITECTURE](docs/ARCHITECTURE.md), [DATA_DICTIONARY](docs/DATA_DICTIONARY.md), [mapping](docs/mapping.md).

## 3. ETL, dữ liệu lỗi và SCD2

`etl.pipeline` điều phối `extract_sales` → `transform_sales` → `load_sales`. Extract đọc MariaDB và lưu envelope staging theo `run_id`; transform kiểm tra ngày, lượng, giá, giảm giá, giá vốn, hiệu lực khuyến mại, natural key và khoảng SCD2. Nạp dimension trước fact, tra surrogate key theo ngày giao dịch. Các thao tác DML, audit, staging và reject nằm trong transaction; lỗi rollback và ghi log FAILED riêng. Advisory lock `phone_dw_pipeline` tuần tự hóa ETL, generator và thay đổi SCD2.

Nguồn 3NF được ràng buộc; 90 envelope lỗi có kiểm soát nằm riêng trong `raw_import_error`, được ETL kiểm chứng payload rồi đưa vào `etl_reject`, không dựa vào nhãn lỗi để giả PASS. Có đúng 10 lỗi mỗi loại: trùng, thiếu bắt buộc, lượng âm, giá âm, vốn âm, SKU sai, ngày sai, tỉnh sai, trả vượt lượng bán. Manifest khớp từng envelope trong database. Các vi phạm logic nghiêm trọng ở nguồn chuẩn hóa làm ETL rollback thay vì âm thầm nạp sai.

Một lượt thành công đối soát: **83.638 = 80.646 dòng bán chấp nhận + 2.992 dòng hủy**; **6.002 = 6.002 dòng trả chấp nhận**; thêm 90 envelope lỗi. Tổng reject của lượt là **3.082**. `etl_log`, `etl_data_quality`, `etl_reject`, `stg_import` lưu lịch sử theo lượt; số dòng audit đọc = chấp nhận + loại. JSON mới nhất xuất trong `output/phone_sales/`.

SCD2 dùng khoảng nửa mở `[ngay_hieu_luc, ngay_het_han)`, mốc xa `9999-12-31`, đúng một phiên bản hiện hành. Chèn mốc mới đóng/tách khoảng cũ, giữ surrogate key của phiên bản đã có và cập nhật liên kết fact theo ngày bán. Cùng khu vực là no-op; đổi khu vực tại một mốc đã tồn tại bị từ chối để giữ lịch sử. CH00 đã có các phiên bản North → Metro → Metro demo → Integration region, có doanh thu theo từng phiên bản. Kiểm tra không chồng lấn, không fact lệch khoảng và chạy lại không tạo phiên bản đều PASS. Thuật toán Python giao dịch thay thế stored procedure; `sql/03_procedures.sql` ghi rõ lựa chọn này.

Idempotency được đo bằng số dòng và SHA-256 **toàn bộ giá trị, gồm surrogate key**, trên cả 6 dimension và 2 fact trước/sau một lượt ETL thật. Hai snapshot bằng nhau. Audit/staging được phép tăng theo lượt; không truncate fact. Generator mặc định bỏ qua nguồn đã có đơn trước khi đụng CSV; kiểm tra 16 file CSV/manifest trước/sau cũng không đổi.

## 4. API, Dashboard và OLAP

Giữ Python `ThreadingHTTPServer`, MVC và thiết kế responsive ban đầu; server bind localhost:8050. Giữ bốn tab, chuyển toàn bộ luồng hoạt động sang bán điện thoại. Chart.js 4.4.1 được vendored tại `web/vendor/` với thông tin giấy phép, không cần tải CDN khi demo.

| API | Hành vi đã kiểm tra |
|---|---|
| `GET /api/filters` | Thương hiệu, mẫu, năm/quý/tháng, khu vực, cửa hàng, kênh |
| `GET /api/overview` | KPI, sáu bộ dữ liệu biểu đồ và bảng hiệu quả cửa hàng; dùng cùng bộ lọc tham số hóa |
| `GET /api/store`, `/api/search_store` | Tìm cửa hàng và lịch sử/doanh thu từng phiên bản |
| `POST /api/scd2_change` | Giao dịch thay đổi vùng, trả phiên bản; lặp không thêm, xung đột báo 400 |
| `GET /api/etl` | Nhật ký, trước/sau làm sạch, reject, 10 kết quả test và benchmark mới |
| `POST /api/run_tests` | Thực thi bộ 10 test thật, gồm ETL rerun |
| `POST /api/sql` | SELECT trên một trong hai database mới, kết quả bảng và thời gian |

SQL Playground giới hạn một SELECT, bảng/view và hàm được cho phép, tối đa 500 dòng trả về, timeout 3 giây và transaction READ ONLY. Không phải SQL IDE đầy đủ: không hỗ trợ subquery, CTE, UNION, comment hoặc cú pháp bảng đặc biệt; CUBE dùng view được xây sẵn. Đã sửa các trường hợp cú pháp có thể bỏ qua kiểm tra bảng và có kiểm thử hồi quy. API kiểm tra input, trả JSON 400/404/503 rõ ràng; lỗi database không đưa chi tiết cấu hình kết nối ra trình duyệt.

Sáu biểu đồ: top 15 mẫu; doanh thu/lượng theo tháng; thương hiệu × kênh; giá–lượng SKU/tháng kèm Pearson; lượng theo thương hiệu; doanh thu/lợi nhuận theo khu vực. Không có số liệu demo hardcode trong API. Bỏ qua phản hồi overview cũ khi người dùng đổi lọc nhanh, giữ lựa chọn hợp lệ sau SCD, và xóa KPI/chart cũ khi API lỗi.

`sql/04_olap_views.sql` và `sql/05_olap_queries.sql` thực thi được: top thương hiệu/mẫu, năm→quý→tháng, thương hiệu×kênh, giá–lượng SKU/tháng, khu vực→tỉnh→cửa hàng. Có Slice/Dice, GROUP BY, aggregate, WITH ROLLUP và CUBE bốn grouping set qua UNION ALL. Pearson là tương quan mô tả trên SKU/tháng có bán, không kết luận quan hệ nhân quả. Năm câu hỏi được đối chiếu độc lập bằng truy vấn trên 3NF và Star Schema, không chỉ so các view với nhau.

## 5. Các lệnh đã chạy thực tế

Các lệnh chạy trong workspace với `.venv` hiện hữu; một số được bọc bằng Python/subprocess để lưu UTF-8 log trên Windows:

```powershell
git status --short
git diff --stat
git diff --check
.\.venv\Scripts\python.exe -m common.check_connection
.\.venv\Scripts\python.exe -m generator.generate_data
.\.venv\Scripts\python.exe -m etl.pipeline
.\.venv\Scripts\python.exe -m tests.run_dq_tests
.\.venv\Scripts\python.exe run_all.py
.\.venv\Scripts\python.exe -m unittest tests.test_web etl.test_scd2 -v
.\.venv\Scripts\python.exe -m compileall -q common etl generator mvc analysis tests run_all.py web_app.py
.\.venv\Scripts\python.exe web_app.py
.\.venv\Scripts\python.exe tests/api_smoke.py --run-tests
node --check web/app.js
node tests/browser_smoke.mjs
```

Ngoài ra đã gọi `change_store` trực tiếp để kiểm tra tách khoảng/no-op, chạy toàn bộ câu lệnh SQL05 bằng SQLAlchemy, tạo lại các view an toàn, sinh dữ liệu hai lần trong bộ nhớ để so hash, kiểm tra generator bảo toàn file và lấy EXPLAIN benchmark. Không chạy reset. Các chế độ `init/generate/etl/scd2/tests/olap/benchmark/all` có trong `run_all.py --help`; chạy mặc định là `all`.

## 6. Kết quả PASS / FAIL / SKIP có bằng chứng

| Kiểm tra | Kết quả cuối | Bằng chứng trong `output/phone_sales/` |
|---|---|---|
| `run_all.py` mặc định | PASS, exit 0, 296,94 giây | `run_all_result.json`, `run_all_final.log` |
| TC01 nguồn / nạp / loại / audit cân bằng | PASS | `test_cases_result.json` |
| TC02 business key bán/trả không trùng | PASS | Cùng file, 0 vi phạm |
| TC03 lượng, giá, giảm giá, vốn hợp lệ | PASS | Cùng file, 0 vi phạm |
| TC04 FK của hai fact hợp lệ | PASS | Cùng file, 0 vi phạm |
| TC05 doanh thu bán/thuần chính xác | PASS | Cùng file, 0 vi phạm |
| TC06 giá vốn thuần/lợi nhuận chính xác | PASS | Cùng file, 0 vi phạm |
| TC07 trả lũy kế không vượt lượng/tiền/vốn | PASS | Cùng file, 0 vi phạm |
| TC08 SCD2 khoảng/current/fact theo ngày | PASS | Cùng file, 8 phiên bản lịch sử, 0 vi phạm |
| TC09 ETL thật giữ đủ khóa và giá trị | PASS | Snapshot/hash before=after của cả 8 bảng |
| TC10 đối chiếu OLTP/DW | PASS | 5 benchmark grain + 5 câu nghiệp vụ bằng nhau |
| API, assets, bộ lọc, SQL, SCD2, chạy test qua HTTP | PASS, 11/11 nhóm | `api_smoke.json`, `api_smoke_console.log` |
| Chrome desktop, 6 canvas có dữ liệu, đổi lọc, 4 tab | PASS | `browser_smoke.json`, `dashboard.png` |
| Chrome mobile 390px | PASS, không tràn ngang | Cùng browser JSON |
| API mất kết nối mô phỏng ở trình duyệt / phục hồi | PASS, xóa dữ liệu cũ rồi nạp lại | `apiErrorState` trong browser JSON |
| Python unit regression | PASS, 5 test methods | Lệnh unittest, hai test SCD và ba test Web với nhiều subcase |
| Python compile / JS syntax / git whitespace | PASS | `final_static_checks.json` |
| 7 SELECT trong SQL05 + USE | PASS | `sql05_execution.json` |
| Bộ sinh seed cố định | PASS, mọi bảng cùng hash | `generator_reproducibility.json` |
| Sinh lại bảo toàn nguồn và CSV/manifest | PASS | `generator_preservation.json` |
| Manifest khớp raw DB; bảo toàn file người dùng | PASS | `preservation_check.json` |
| IntelliJ IDEA thao tác GUI trực tiếp | SKIP | Đã chạy interpreter và working directory bằng terminal; hướng dẫn GUI để người dùng kiểm tra |
| Reset phá hủy dữ liệu | SKIP có chủ đích | Không thực thi, không cần cho nghiệm thu |

Năm câu nghiệp vụ đối chiếu có số dòng tương ứng **31 / 52 / 26 / 3.600 / 73**, gồm các tổng ROLLUP. Đây là số dòng đúng tại snapshot kiểm thử sau SCD demo; không phải số giao dịch. File `olap_reconciliation.json` và `olap_business_*.csv` lưu kết quả. Mười test cũng được gọi qua `/api/run_tests`: HTTP 200, 10 PASS, khoảng 99,78 giây gồm ETL và đối chiếu thật.

KPI toàn bộ dữ liệu tại lượt HTTP kiểm chứng: doanh thu bán **1.123.324.052.000 VND**; hoàn **63.041.004.000 VND**; thuần **1.060.283.048.000 VND**; **57.884 đơn**, **109.727 máy**; giá vốn thuần **816.716.116.000 VND**; lợi nhuận **243.566.932.000 VND**; biên **22,971878%**, tỷ lệ trả **5,6012%**. Giá trị lấy từ API/database; không được chèn cố định vào giao diện.

### Benchmark thực tế

Một warm-up không tính giờ, sau đó **5 lần đo**, gồm fetch toàn bộ kết quả, dùng median. Cả năm kết quả OLTP và DW đều khớp. Các lần đo phản ánh máy/cấu hình và cache trong phiên này, không phải cam kết hiệu năng phổ quát.

| Grain | OLTP median (ms) | DW median (ms) | OLTP / DW |
|---|---:|---:|---:|
| Tháng | 1.001,02 | 5.669,12 | 0,177× |
| SKU | 1.345,10 | 389,56 | 3,453× |
| Cửa hàng | 3.038,46 | 676,39 | 4,492× |
| Kênh | 1.721,24 | 755,85 | 2,277× |
| Khuyến mại | 1.219,37 | 659,23 | 1,850× |

Truy vấn tháng DW chậm hơn. EXPLAIN cho thấy DW bắt đầu từ `dim_san_pham`, tra fact qua index sản phẩm, rồi nối nhiều dimension và tổng hợp bảng trả; có temporary/filesort. Buffer pool thực tế chỉ **16 MiB**. Suy luận hợp lý là thứ tự join, truy cập trang và cache nhỏ làm tăng chi phí cho grain thời gian. Chưa cô lập từng nguyên nhân bằng thí nghiệm cấu hình, nên không khẳng định nguyên nhân duy nhất. Không thay đổi cấu hình MariaDB toàn máy để làm đẹp số đo. Bằng chứng: `benchmark_result.csv` chứa từng sample và median, `benchmark_explain.json` chứa kế hoạch hai phía.

## 7. Lỗi đã sửa, tồn tại và giới hạn

Đã sửa: schema/API giáo dục; hardcoded dashboard cũ; đường dẫn test/benchmark đọc nhầm báo cáo cũ; mã cửa hàng mặc định không tồn tại; chữ tiếng Việt bị hỏng; JS thiếu dấu ngoặc; Windows console encoding; ETL tạo lại surrogate key return; kế hoạch upsert SQL quá chậm; loại nhầm đơn trả khỏi doanh thu; xung đột cùng mốc SCD ghi đè lịch sử; lựa chọn lọc mất sau SCD; kiểm tra SELECT bỏ sót cú pháp bảng không hỗ trợ.

Một lượt `run_all.py` trước đã FAIL vì import trong lúc module SCD đang được ghi lại, xuất hiện ký tự BOM sai. File đã được ghi UTF-8 sạch, compile/unit PASS và lượt cuối exit 0. Hai lượt ETL thử nghiệm trước có kế hoạch SQL chậm đã được dừng/rollback; log FAILED lịch sử được giữ. Các file log lỗi cũ không bị sửa thành PASS. Trạng thái hiện tại dựa vào lượt cuối và bộ bằng chứng nêu trên.

Không còn lỗi chặn trong các luồng đã kiểm thử. Các giới hạn còn lại: server là dashboard đồ án cục bộ, không có xác thực hay thiết kế triển khai Internet; SQL Playground là tập con SELECT có chủ đích; bộ lịch/sale validation dành cho fixture 2024–2026; hiệu năng thay đổi theo cache/cấu hình. Không có kiểm thử GUI IntelliJ tự động. Khi khởi động XAMPP đã thấy cảnh báo InnoDB LSN sẵn có; không sửa file dữ liệu hay recovery của database cũ trong nhiệm vụ này. Hai database cũ vẫn có 11 và 18 bảng; không có snapshot dòng ban đầu để tuyên bố đã đối chiếu toàn bộ dữ liệu cũ.

## 8. Hướng dẫn kiểm thử thủ công

1. Bật MySQL trong XAMPP. Mở terminal ở đúng thư mục dự án, chọn `.venv\Scripts\python.exe` làm interpreter trong IntelliJ, Working directory là thư mục dự án, encoding UTF-8.
2. Chạy `.\.venv\Scripts\python.exe run_all.py`. Lần lặp dùng nguồn hiện có; chờ test và benchmark thật hoàn tất, xem exit code và `output/phone_sales/`.
3. Chạy `.\.venv\Scripts\python.exe web_app.py`, mở **http://localhost:8050**. Nếu phiên server kiểm thử còn chạy thì chỉ mở trang, không khởi động thêm server cùng cổng.
4. Dashboard: thấy sáu KPI/sáu biểu đồ; chọn 2025, quý 1, Apple, WEB và kiểm tra đồng bộ; thử tổ hợp không có giao dịch.
5. SCD2: tìm CH00, xem bốn phiên bản và doanh thu. Chọn mốc mới chưa tồn tại, nhập khu vực mới, áp dụng; chạy lặp cùng payload phải không thêm phiên bản. Cố đổi khu vực khác tại mốc đã có phải báo lỗi, lịch sử không đổi. Thao tác này sẽ thay đổi dữ liệu demo nên kết quả tổng hợp theo khu vực có thể khác snapshot báo cáo.
6. ETL: xem run_id, số dòng/loại và nguyên nhân; bấm chạy 10 test, đợi hoàn thành. Benchmark lấy từ file đo thật mới, không phải file cũ ở `output/`.
7. SQL: chọn mỗi database và chạy mẫu. SELECT cho kết quả và thời gian; câu ghi dữ liệu bị từ chối. Xem [hướng dẫn Windows/IntelliJ](HUONG_DAN_CHAY_VA_SU_DUNG_WEB.md) và [kịch bản demo](docs/KICH_BAN_DEMO_VA_THUYET_TRINH.md).

## 9. Xác nhận phạm vi và bảo toàn

- **Không reset database trong quá trình tiếp tục/kiểm chứng; không xóa `edu_source` hoặc `edu_dw`.** Mọi DML triển khai chỉ hướng tới hai database điện thoại.
- **Không sửa `.env` hoặc mật khẩu**; hai file thay đổi chưa commit ban đầu giữ nguyên byte, đã kiểm chứng hash.
- **Không commit, không push GitHub**, HEAD và nhánh giữ nguyên; chỉ sửa working tree.
- Không dùng dữ liệu giáo dục trong API/Dashboard mới. Dữ liệu giả lập được lưu thật ở MariaDB rồi tính qua ETL/SQL, không giả response trực tuyến.

Các JSON/CSV/log và ảnh kiểm chứng được giữ cục bộ trong `output/phone_sales/`; danh mục database và run_id mới nhất ở `database_inventory.json`. Lượt kiểm thử qua API có ETL run_id `b816ecfb50524aef9dcafcccaa613a4c`. `acceptance_summary.json` tổng hợp các điều kiện từ bằng chứng đã chạy: tất cả điều kiện đạt PASS, hai mục SKIP có chủ đích được ghi riêng. README và tài liệu hiện hành đã được chuyển sang đề tài điện thoại.

## Cập nhật ngày 19/11/2026 — dọn database theo yêu cầu mới

Các xác nhận giữ database cũ ở trên mô tả lần nghiệm thu ngày 17/11. Ngày 19/11, người dùng yêu cầu rõ ràng xóa database của đề tài cũ, thay thế chỉ dẫn bảo toàn hai database này trước đó.

- Đã viết lại README theo tên đề tài, kiến trúc, năm câu hỏi phân tích, bốn tab Dashboard và các chế độ chạy của kho bán điện thoại.
- Sao lưu đầy đủ `edu_source`, `edu_dw` bằng mysqldump (gồm dữ liệu, view, routines, events và triggers) vào `backups/remove_education_20261119_012403/education_databases.sql`, dung lượng 64.287.074 byte. Đã kiểm tra dump kết thúc thành công, DDL/USE và SHA-256 trước khi xóa; manifest lưu cùng thư mục backup.
- Đã thực thi DROP đúng hai database `edu_dw`, `edu_source`; kiểm tra sau đó xác nhận cả hai không còn tồn tại. Không có FK từ database khác tham chiếu hai database này lúc xóa.
- `phone_source`, `phone_dw` vẫn tồn tại. Số dòng trước/sau giữ nguyên: 80.646 fact bán, 6.002 fact trả, 26 phiên bản cửa hàng. Không reset dữ liệu điện thoại, không sửa mật khẩu, không commit/push.
- Bằng chứng mới: `output/phone_sales/education_cleanup_result.json` (PASS). Các bản kiểm kê và bảo toàn cũ là snapshot ngày 17/11, không mô tả trạng thái database sau lần dọn này.
