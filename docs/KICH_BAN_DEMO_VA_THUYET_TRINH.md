# Kịch bản demo và thuyết trình: kho dữ liệu bán điện thoại

Thời lượng gợi ý 12–15 phút. Chỉ công bố số liệu lấy từ lần chạy thật hiện tại; không đọc lại kết quả của bản giáo dục hoặc khẳng định sẵn 10/10 PASS.

## Chuẩn bị trước buổi demo

Bật MariaDB; chạy `run_all.py`, lưu exit code và `output/phone_sales/`. Mở `web_app.py`, truy cập localhost:8050; kiểm tra cả sáu biểu đồ. Chọn một mã cửa hàng có thật, một mốc SCD2 hợp lệ và ghi số dòng/tiền trước thao tác. Không reset trong buổi trình bày. Nếu database chưa chạy hoặc kiểm thử chưa xong, nói rõ phần chưa kiểm chứng.

## 1. Bài toán và thiết kế (3 phút)

Giới thiệu nhu cầu xem doanh thu thuần, lợi nhuận và trả hàng theo thời gian, SKU, cửa hàng, kênh và khuyến mại. Nguồn 13 bảng nghiệp vụ chuẩn hóa tránh lặp nhãn; lịch sử cửa hàng và lỗi nhập thô là hai bảng hỗ trợ. Mở ERD và star ở [ARCHITECTURE.md](ARCHITECTURE.md).

Giải thích grain: một dòng bán khác một đơn; một dòng bán có thể trả nhiều lần. Kho có sáu dimension, hai fact. Trình bày tại sao view phải gom trả trước khi nối bán. Tiền dùng DECIMAL; giảm giá và giá vốn là tổng dòng.

## 2. Dashboard và năm câu hỏi (4 phút)

1. Drill-down hãng → sản phẩm/SKU; so doanh thu, sản lượng với tỷ lệ trả.
2. Roll-up tháng → quý/năm; đọc mùa vụ doanh thu thuần và lượng bán.
3. Dice thương hiệu × kênh; đọc cùng chỉ số trên cùng lát cắt.
4. Scatter giá bán bình quân sau giảm giá và lượng bán theo SKU × tháng; đọc Pearson và cỡ mẫu, không suy diễn nhân quả.
5. Chọn khu vực/tỉnh/cửa hàng; giải thích khu vực tại ngày bán.

Có thể minh họa thêm bộ lọc khuyến mại, nhưng đây không thay thế một trong năm câu hỏi trên.

Chọn một bộ lọc và chỉ ra mọi KPI/biểu đồ cùng đổi; thử lát cắt rỗng rồi đặt lại. Scatter giá bán trung bình và số máy ở grain SKU × tháng chỉ thể hiện quan hệ trong dữ liệu mô phỏng; r nếu có là tương quan ở grain đã công bố, phụ thuộc cỡ mẫu, phương sai và yếu tố gây nhiễu.

Nêu ví dụ bán 31/12/2026, trả 05/01/2027: cohort tháng 12 giảm doanh thu; báo cáo ngày hoàn tiền ghi nhận vào tháng 1. Không dùng hai số này như hai cách tính có thể hoán đổi.

## 3. SCD2 trực tiếp (3 phút)

Tìm cửa hàng đã chọn; đọc lịch sử và current. Thực hiện đổi khu vực với ngày hợp lệ; đọc phản hồi. Mốc cũ hết hạn bằng mốc mới hiệu lực, khoảng `[start,end)` nên không trùng ngày. Dùng ngày bán trước và đúng mốc để chứng minh lookup; fact cũ vẫn giữ khu vực cũ. Thực hiện lại cùng yêu cầu, kiểm tra no-op và không có phiên bản trùng. Thử khu vực khác tại đúng mốc đã tồn tại phải nhận lỗi bảo vệ lịch sử; chọn mốc khác nếu cần thay đổi; chạy lại ETL và đối chiếu số dòng/tiền.

SQL minh họa trên playground:

```sql
SELECT ma_cua_hang, khu_vuc_quan_ly, ngay_hieu_luc, ngay_het_han, is_current
FROM dim_cua_hang
ORDER BY ma_cua_hang, ngay_hieu_luc
LIMIT 30
```

## 4. ETL, kiểm thử và benchmark (3 phút)

Mở log theo run_id: chỉ một lỗi thô và lý do reject; đối chiếu dòng đọc = dòng xử lý hợp lệ + dòng loại theo phạm vi của lượt. Giải thích transaction, rollback DML và khóa tuần tự hóa ETL/SCD2. Log mỗi lượt tăng là bình thường; idempotence yêu cầu fact và dimension không bị nhân đôi khi nguồn không đổi.

Chạy 10 test, đọc kết quả thật và chi tiết ca lỗi nếu có. TC09 thực sự chạy ETL lại và đối chiếu snapshot; TC10 so năm tập kết quả nguồn/kho. Mở benchmark: nêu warm-up, số lần lặp, thời gian đo gồm fetch, equality và môi trường. Nếu DW chậm hơn ở một truy vấn, trình bày đúng kết quả; star schema không bảo đảm mọi truy vấn nhanh hơn.

## Câu hỏi phản biện

| Câu hỏi | Trả lời |
|---|---|
| Vì sao SCD2? | Giữ khu vực cửa hàng tại thời điểm bán; ghi đè SCD1 sẽ đổi phân loại lịch sử. |
| Vì sao không dùng BETWEEN? | BETWEEN gồm cả hai cận; tại mốc thay đổi có thể khớp hai phiên bản. Dùng `>= start AND < end`. |
| Vì sao không join trực tiếp hai fact? | Nhiều lượt trả nhân dòng bán, làm SUM doanh thu sai. Gom trả theo dòng bán trước. |
| Tỷ lệ trả có phải trung bình tỷ lệ SKU? | Không; phải chia tổng lượng trả cho tổng lượng bán sau cùng bộ lọc. |
| Đơn trả hết có trong AOV? | Có, nếu đơn bán hợp lệ; tử số đã trừ tiền hoàn. |
| Vì sao giữ raw lỗi riêng? | Giữ FK nguồn 3NF có hiệu lực và vẫn có dữ liệu sai để chứng minh reject. |
| Có chứng minh khuyến mại làm tăng doanh số? | Chưa; đây là mô tả dữ liệu mô phỏng, cần thiết kế nghiên cứu khác để kết luận nhân quả. |
| Đã hoàn thành chưa? | Trả lời theo báo cáo chạy hiện tại: phần PASS, FAIL, SKIP và giới hạn, không theo con số định trước. |
