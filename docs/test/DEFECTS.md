# Danh sách defect

Cập nhật 28/11/2026, đối chiếu `main` `2dfa4fc`.

**Nguồn:** dự án không dùng GitHub Issues. Lỗi được phát hiện qua review, test, rà bảo mật và thực nghiệm, rồi sửa trong commit hoặc PR. Danh sách dựng lại từ lịch sử `main`, mỗi dòng có commit hoặc PR để truy được. Lỗi phát sinh và được sửa ngay trong cùng một PR chưa merge không được tính.

**Mức độ:**
- **Cao:** lộ dữ liệu, sai quyền, mất tiền/lượt, dịch vụ ngừng.
- **Trung bình:** sai chức năng, có cách tránh.
- **Thấp:** hiển thị, tài liệu, công cụ.

**Trạng thái:** *Đã sửa* (đã có trên `main`) · *Đã sửa, chờ merge* · *Mở*.

## 1. Đã sửa

| Mã | Ngày | Mức | Mô tả lỗi | Cách sửa | Minh chứng | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| DF-01 | 04/11 | Cao | SEC-01: mã gửi qua email không gắn với địa chỉ nhận. Đổi email xong, mã cũ vẫn dùng được; Google có thể tự liên kết vào tài khoản chưa xác minh địa chỉ | Kiểm mã, hạn, số lần thử và email hiện tại trong một lệnh cập nhật có điều kiện; đổi email thì huỷ mọi mã cũ | `8da9ed1`, `0bd8447` (sửa thêm 2 tình huống tranh chấp sau review) | Đã sửa |
| DF-02 | 04/11 | Cao | SEC-02: tệp audio nén nhỏ nhưng giải mã ra rất lớn, có thể làm hết bộ nhớ máy chủ | Trần bộ nhớ PCM sau giải mã (`AICEFR_MAX_DECODED_BYTES`), kiểm từ header trước khi cấp phát; trả 413 / `AUDIO_TOO_LARGE` | `8da9ed1` | Đã sửa |
| DF-03 | 04/11 | Cao | SEC-03: bước xác thực lại khi đổi email/mật khẩu không dùng chung bộ đếm khoá với đăng nhập, nên thử mật khẩu không giới hạn được | Dùng chung bộ đếm và khoá; đang khoá thì trả 429 | `8da9ed1` | Đã sửa |
| DF-04 | 04/11 | Cao | SEC-04: tham số `next` sau đăng nhập cho chuyển hướng ra trang ngoài (`//`, gạch chéo ngược, ký tự điều khiển) | Phân giải theo origin hiện tại ở `login.js` và `auth/google.py`, chặn các dạng trên | `8da9ed1` | Đã sửa |
| DF-05 | 04/11 | Cao | SEC-05: luồng thông báo trực tiếp (SSE) vẫn chạy sau khi đăng xuất, khoá tài khoản hay đổi vai trò | Kiểm lại phiên mỗi 30 giây và trước mỗi sự kiện | `8da9ed1` | Đã sửa |
| DF-06 | 30/10 | Cao | Trang quản trị mở được với tài khoản không phải admin | Chặn theo vai trò; thêm test ma trận quyền trên mọi route | [#90](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/90) | Đã sửa |
| DF-07 | 29/10 | Cao | Một commit đồng bộ (`ff683cc`) ghi đè `main`, mất thay đổi | Khôi phục `main` về bản #79 (`378ba47`) | [#80](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/80) | Đã sửa |
| DF-08 | 29/10 | Cao | Còn sót số đo trên Speak & Improve trong tài liệu công khai (dữ liệu phi thương mại) | Gỡ số đo, chuyển tài liệu vận hành | [#73](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/73) | Đã sửa |
| DF-09 | 16/10 | Trung bình | Quản trị viên bấm hai lần tạo hai thay đổi trùng | Chặn thao tác trùng | `8b7770d` | Đã sửa |
| DF-10 | 07/11 | Trung bình | Khối band tràn ngang trên điện thoại; chữ cam dưới mức tương phản AA | Co khối dưới 640 px; đổi sang màu `--brand-strong` | [#134](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/134) | Đã sửa |
| DF-11 | 06/11 | Trung bình | Ảnh lộ trình, icon và favicon không được đóng gói vào bản build | Đưa vào gói build | [#131](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/131) | Đã sửa |
| DF-12 | 30/10 | Trung bình | Bật Whisper khi chưa cài nhóm `asr` thì lỗi khó hiểu; sai backend trên Mac Intel | Báo rõ lỗi; chọn đúng backend | [#89](https://github.com/ThanhSangLouis/ai-assessor-cefr/pull/89) | Đã sửa |
| DF-13 | 30/10 | Trung bình | Dịch vụ speech chạy không có Silero VAD | Bật Silero VAD | `8674b21` | Đã sửa |
| DF-14 | 27/10 | Trung bình | Sau khi chuyển sang MongoDB, thiếu `db_cli` và repository, kho cũ/mới không tương thích | Bổ sung `db_cli`, repository; tương thích hai kho | `95208e7` | Đã sửa |
| DF-15 | 16/10 | Trung bình | Bộ soạn bài lưu tự động cả bản nháp chưa hợp lệ; xem trước bài học cho ghi âm và sửa được | Hoãn tự lưu tới khi hợp lệ; xem trước chỉ đọc, tắt ghi âm | `ba0d703`, `05c6a61`, `470d14e`, `04382e1` | Đã sửa |
| DF-16 | 16/10 | Trung bình | Trang tiến độ và luyện tập gọi API đã đổi | Khớp với API hiện hành | `0827b37`, `faa1d8e` | Đã sửa |
| DF-17 | 16/10 | Thấp | Trang của giảng viên, quản trị viên vẫn gọi API huy hiệu chỉ dành cho sinh viên | Bỏ lời gọi với tài khoản giảng viên | `e584a2b` | Đã sửa |
| DF-18 | 16/10 | Trung bình | Mốc thời gian không múi giờ bị hiểu sai giờ | Coi là UTC | `636c020` | Đã sửa |
| DF-19 | 16/10 | Thấp | Báo cáo chỉ có điểm bị lặp tiêu đề; trang mất cấp tiêu đề cho trình đọc màn hình | Bỏ tiêu đề lặp; khôi phục cấp tiêu đề | `62a5d8d`, `d113d56` | Đã sửa |
| DF-20 | 12/10 | Trung bình | Tệp lưu trên Windows bị hỏng đường dẫn | Giữ đúng tệp trên Windows | `1f14f7f` | Đã sửa |
| DF-21 | 03/10 | Trung bình | QC từ chối nhưng lý do không chép sang Transcript, báo cáo thiếu lý do | Chép lý do QC sang Transcript | `c06e997` | Đã sửa |
| DF-22 | 02/10 | Trung bình | Vòng đời pipeline trên SQLite không nguyên tử, có thể kẹt bài | Giao dịch nguyên tử, phục hồi | `d1f10ae` | Đã sửa |
| DF-23 | 02/10 | Trung bình | Mô hình tải về không được kiểm nguồn gốc | Kiểm SHA-256 từng tệp mô hình | `98e70da` | Đã sửa |
| DF-24 | 02/10 | Trung bình | Ứng dụng chạy cục bộ: đồng thuận, đăng xuất và màn duyệt trên điện thoại lỗi | Sửa ba luồng | `ffb325c` | Đã sửa |
| DF-25 | 28/11 | Thấp | `teach_insights.js` khai biến toàn cục `open`, che `window.open` của trình duyệt cho mọi tệp nạp sau; `credits.js` khai `when` trùng biến có sẵn; 3 biến thừa | Đổi tên (`dialogAttempt`, `fmtWhen`), bỏ biến thừa. Phát hiện bằng ESLint | nhánh `docs/sang/submission-evidence`, [báo cáo ESLint trước khi sửa](../evidence/tc2-4-code-quality/reports/eslint-before-2026-11-28.txt) | Đã sửa, chờ merge |

## 2. Còn mở hoặc giới hạn đã biết

| Mã | Mức | Mô tả | Lý do chưa sửa | Hướng xử lý, thời hạn |
| --- | --- | --- | --- | --- |
| DF-O1 | Trung bình | Bộ đoán ngôn ngữ của Whisper small gắn nhầm "không phải tiếng Anh" cho khoảng 6,6 % bài tiếng Anh giọng người học (đo trên tập dev, chương thực nghiệm mục 6.1). Bài không bị chấm sai mà bị chuyển giảng viên | Cần dữ liệu để chọn lại ngưỡng xác suất mà vẫn bắt được bài nói tiếng Việt | Hiệu chỉnh ngưỡng `min_probability` trên dev, trước 06/12/2026 |
| DF-O2 | Thấp | `GET` và `POST /api/v1/billing/notify/{gateway}` dùng chung một hàm, nên OpenAPI báo trùng operation id | Không ảnh hưởng chạy thật | Đặt `operation_id` riêng cho hai route, trước 06/12/2026 |
| DF-O3 | Giới hạn | Khoảng dự đoán 90 % rộng hơn một band, nên mọi bài vẫn chuyển giảng viên; máy chưa tự phát band | Giới hạn của độ chính xác mô hình, không phải lỗi mã | Ghi trong luận văn; xét lại sau khi có dữ liệu sinh viên Việt Nam |
| DF-O4 | Giới hạn | Mô hình chấm bài A2 cao hơn thật và bài C1 thấp hơn thật (co về giữa) | Dữ liệu huấn luyện ít bài ở hai đầu | Ghi trong luận văn; thu thêm dữ liệu band thấp |
