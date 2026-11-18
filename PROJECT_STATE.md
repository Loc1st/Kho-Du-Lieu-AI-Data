# Trạng thái dự án kho dữ liệu bán điện thoại

Cập nhật: 17/11/2026. Phạm vi đang dùng: `phone_source` → `phone_dw`, bán 2024–2026, trả có thể sang 2027; Web MVC cổng 8050.

## Thiết kế được chốt

- Nguồn: 13 bảng nghiệp vụ 3NF, lịch sử khu vực cửa hàng và vùng nhập thô chứa lỗi riêng biệt.
- Kho: 6 dimension, 2 fact theo dòng bán và dòng trả; tiền `DECIMAL(18,2)`.
- SCD2 cửa hàng dùng khoảng nửa mở `[ngay_hieu_luc, ngay_het_han)`; fact tra phiên bản theo ngày bán.
- Dashboard dùng ngày bán gốc; ngày trả lưu độc lập.
- ETL lưu reject, chất lượng và log theo `run_id`; chạy lặp không nhân đôi fact hoặc phiên bản chiều.
- Kiểm thử và benchmark chạy truy vấn thật; kết quả cũ không được dùng làm bằng chứng.

## Xác nhận trạng thái máy hiện tại

Chạy `run_all.py`, `python -m tests.run_dq_tests`, `python -m analysis.benchmark`, rồi mở dashboard. Đọc tệp trong `output/phone_sales/` cùng thời điểm chạy và `run_id`. Xem báo cáo triển khai cuối cùng để biết chính xác PASS, FAIL hoặc SKIP; tài liệu này không khẳng định máy đã nạp đủ dữ liệu hay 10/10 PASS.

Bằng chứng cần có: ít nhất 50.000 đơn; đối soát dòng và tiền; reject lỗi chủ đích; khóa ngoại; giới hạn trả lũy kế; ngày trả; SCD2 không chồng lấn và fact đúng lịch sử; ETL chạy lại; kết quả OLTP/DW tương đương; API và sáu biểu đồ thực tế.

## Bảo toàn tài sản

Giữ nguyên `.env` và mật khẩu, `data/error_manifest.json`, `output/benchmark_result.csv`. Bản sao: `backups/20261117_214730/workspace_before.zip`. Không xóa database cũ, không commit/push. Tài liệu giáo dục `.docx` được giữ để tham khảo lịch sử. Các file `*_NOTES.md` không thuộc phạm vi viết lại.

Tài liệu: [hướng dẫn](HUONG_DAN_CHAY_VA_SU_DUNG_WEB.md), [kiến trúc](docs/ARCHITECTURE.md), [mapping](docs/mapping.md), [từ điển](docs/DATA_DICTIONARY.md), [demo](docs/KICH_BAN_DEMO_VA_THUYET_TRINH.md).


## Đối chiếu thiết kế sau bổ sung nghiệp vụ

Nguồn có 13 bảng nghiệp vụ và 2 bảng hỗ trợ, tổng 15; có nhân viên và FK nhân viên ở đơn. Trạng thái đơn gồm `COMPLETED`, `PARTIALLY_RETURNED`, `RETURNED`, `CANCELLED`; chỉ hủy bị loại khỏi bán. Phiếu trả có `PARTIAL`/`FULL`. Khuyến mại có ngày hiệu lực: generator sinh 16 mã, database nâng cấp có thể giữ 4 mã cũ không dùng thành 20; giữ nguyên chúng theo yêu cầu bảo toàn.

Cùng ngày hiệu lực SCD2 và cùng khu vực là no-op; cùng ngày nhưng khu vực khác bị từ chối. Không reset, commit hoặc push trong lần tiếp tục này.

## Nghiệm thu thực tế cuối phiên

`run_all.py` mặc định đã hoàn tất với exit 0 trong 296,94 giây trên MariaDB 10.4.32. Có 60.000 đơn nguồn, 80.646 fact bán và 6.002 fact trả. Mười test PASS, gồm snapshot toàn bộ tám bảng trước/sau ETL thật. Năm câu hỏi nghiệp vụ và năm grain benchmark đều đối chiếu khớp OLTP/DW. Benchmark có năm lần đo mỗi truy vấn; DW chậm hơn OLTP ở grain tháng và nhanh hơn ở bốn grain còn lại.

Kiểm tra HTTP đạt 11/11 nhóm, gồm gọi bộ 10 test qua API. Chrome headless xác nhận bốn tab, sáu biểu đồ, đổi bộ lọc, thông báo khi API lỗi/phục hồi và mobile 390px. IntelliJ GUI chưa tự động kiểm thử. Xem [báo cáo triển khai](PHONE_SALES_IMPLEMENTATION_REPORT.md) để đọc log, số đo và giới hạn; thư mục bằng chứng là `output/phone_sales/`.

## Cập nhật 19/11/2026

Theo yêu cầu mới của người dùng, đã sao lưu rồi xóa `edu_source` và `edu_dw`. Backup SQL nằm tại `backups/remove_education_20261119_012403/education_databases.sql`. Hai database điện thoại được giữ nguyên; số dòng fact bán/trả và lịch sử cửa hàng trước/sau khớp. README đã được viết lại theo đề tài điện thoại. Các ghi nhận bảo toàn database cũ phía trên là lịch sử nghiệm thu ngày 17/11; trạng thái dọn mới được ghi trong `output/phone_sales/education_cleanup_result.json` và phụ lục báo cáo.
