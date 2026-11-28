# Bộ tài liệu thực nghiệm người dùng

**Trạng thái:** CHƯA THỰC HIỆN. Bộ tài liệu soạn ngày 28/11/2026 để chạy trong tuần 12 (30/11–06/12/2026). Kết quả sẽ ghi vào `ket-qua/`.

**Mục tiêu:** đo xem người dùng thật có tự làm được các việc chính trên https://speakup.fit không, mất bao lâu, vấp ở đâu, và hài lòng tới mức nào (SUS). Sau đó sửa theo phản hồi.

**Không đo ở đây:** độ chính xác của điểm CEFR. Phần đó thuộc kế hoạch thu dữ liệu riêng ([KE_HOACH_KHAO_SAT.md](../../plan/KE_HOACH_KHAO_SAT.md)).

## 1. Người tham gia

| Nhóm | Số người | Điều kiện |
| --- | --- | --- |
| Sinh viên | 6–8 | Sinh viên đại học, từ 18 tuổi, chưa từng dùng SpeakUp, không thuộc nhóm làm đồ án |
| Giảng viên hoặc trợ giảng tiếng Anh | 2 | Có dạy tiếng Anh |

Tổng 8–10 người. Mỗi người có một mã ẩn danh `P01`, `P02`…; bảng nối mã với họ tên chỉ giữ ở máy người phụ trách, **không đưa vào Git**.

**Chuẩn bị:**
- Một lớp mẫu, có mã vào lớp.
- Một đề nói đã giao cho lớp.
- Một tài khoản giảng viên cho người tham gia nhóm giảng viên.
- Mỗi sinh viên tự đăng ký tài khoản (đó là tác vụ S1).

## 2. Kịch bản tác vụ

Người hướng dẫn chỉ đọc đề tác vụ, không chỉ chỗ bấm. Người tham gia nghĩ thành lời trong lúc làm.

**Thời gian** tính từ lúc đọc xong đề đến lúc người tham gia nói "xong".

**Lỗi** là mỗi lần làm sai hướng mà phải quay lại: bấm nhầm trang, nộp sai đề, hỏi người hướng dẫn.

**Hoàn thành** là làm đúng mà không cần giúp. Cần gợi ý thì ghi "hoàn thành có trợ giúp". Bỏ cuộc hoặc quá 2 lần thời gian chuẩn thì ghi "không hoàn thành".

### Sinh viên

| Mã | Tác vụ (đọc cho người tham gia) | Đích | Thời gian chuẩn |
| --- | --- | --- | --- |
| S1 | "Hãy tạo tài khoản SpeakUp cho bạn." | `/signup`, vào được trang chủ | 2 phút |
| S2 | "Thầy cô gửi bạn mã lớp `<mã>`. Hãy vào lớp đó." | `/my-classes`, lớp hiện trong danh sách | 1 phút |
| S3 | "Hãy làm bài nói thầy cô đã giao và nộp bài." | Trang chủ hoặc `/my-assignments`, bài nộp thành công | 3 phút |
| S4 | "Hãy xem kết quả bài vừa nộp và cho biết bạn được band nào, cần cải thiện gì nhất." | `/report/{id}`, nói đúng band và một gợi ý | 2 phút |
| S5 | "Hãy luyện lại một lỗi mà hệ thống chỉ ra." | `/practice`, `/drill/{id}` hoặc bài học gợi ý | 3 phút |
| S6 | "Hãy tìm xem từ đầu tới giờ bạn đã tiến bộ thế nào." | `/my-progress` | 1 phút |

### Giảng viên

| Mã | Tác vụ | Đích | Thời gian chuẩn |
| --- | --- | --- | --- |
| G1 | "Hãy tạo một lớp mới và lấy mã để gửi sinh viên." | `/teach/classes` | 2 phút |
| G2 | "Hãy giao một đề nói cho lớp, hạn nộp tuần sau." | `/teach/tasks` hoặc trang lớp | 2 phút |
| G3 | "Hãy mở một bài trong hàng chờ, nghe lại, xác nhận hoặc sửa điểm và ghi lý do." | `/review`, `/review/{id}` | 4 phút |
| G4 | "Hãy cho biết lớp đang yếu nhất ở mặt nào." | `/teach/insights` hoặc `/review/stats` | 2 phút |

Thời gian chuẩn là thời gian nhóm làm thử cộng thêm khoảng 100 %. Đo lại với 1 người thử trước buổi chính và chỉnh nếu lệch quá xa.

## 3. Số liệu thu

| Chỉ số | Cách tính | Ngưỡng mục tiêu (bản cam kết, KPI-5) |
| --- | --- | --- |
| Tỷ lệ hoàn thành | Số tác vụ hoàn thành không trợ giúp / tổng tác vụ | ≥ 90 % |
| Thời gian hoàn thành | Trung vị theo từng tác vụ | So với thời gian chuẩn |
| Số lỗi | Trung bình mỗi tác vụ | Càng thấp càng tốt; liệt kê chỗ vấp |
| SUS | Thang 0–100 (mục 4) | ≥ 68 (trung bình ngành); ≥ 80 là tốt |

Ghi vào [`mau-ghi-chep.csv`](mau-ghi-chep.csv), mỗi tác vụ một dòng.

## 4. Phiếu SUS (System Usability Scale)

Sau khi làm xong các tác vụ, người tham gia chấm mỗi câu từ 1 (rất không đồng ý) đến 5 (rất đồng ý). Bản dịch tiếng Việt của bộ 10 câu chuẩn (Brooke, 1996):

1. Tôi nghĩ tôi sẽ muốn dùng hệ thống này thường xuyên.
2. Tôi thấy hệ thống phức tạp không cần thiết.
3. Tôi thấy hệ thống dễ dùng.
4. Tôi nghĩ tôi cần người kỹ thuật giúp mới dùng được hệ thống này.
5. Tôi thấy các chức năng của hệ thống được gắn kết tốt với nhau.
6. Tôi thấy hệ thống có quá nhiều chỗ không nhất quán.
7. Tôi nghĩ đa số mọi người sẽ học dùng hệ thống này rất nhanh.
8. Tôi thấy hệ thống rất rườm rà, khó dùng.
9. Tôi thấy tự tin khi dùng hệ thống.
10. Tôi phải học nhiều thứ trước khi dùng được hệ thống này.

**Cách tính:**
- Câu lẻ: lấy điểm − 1.
- Câu chẵn: lấy 5 − điểm.
- Cộng cả 10 câu rồi nhân 2,5, ra thang 0–100.

Thêm hai câu mở:
- "Điều gì khiến bạn khó chịu nhất?"
- "Bạn muốn sửa gì đầu tiên?"

## 5. Đồng thuận

Đọc cho người tham gia trước khi bắt đầu, và ghi nhận đồng ý (giấy hoặc biểu mẫu, lưu ngoài Git):

> Buổi thử này đánh giá **phần mềm**, không đánh giá bạn. Bạn có thể dừng bất cứ lúc nào. Chúng tôi ghi thời gian, các lần bấm nhầm và câu trả lời phiếu, gắn với mã ẩn danh. Bản ghi âm bài nói bạn nộp nằm trên hệ thống như mọi người dùng khác; bạn có thể xoá bài hoặc xoá tài khoản sau buổi thử.

## 6. Sau buổi thử: danh sách cải tiến

Mỗi phản hồi dẫn tới thay đổi được ghi vào [`cai-tien.md`](cai-tien.md):
- vấn đề, do ai nêu (mã ẩn danh), số người gặp;
- mức độ;
- thay đổi đã làm và PR;
- đo lại (nếu có).

Phản hồi không sửa cũng ghi, kèm lý do.

## 7. Lịch đề xuất

| Ngày | Việc |
| --- | --- |
| 30/11 | Chạy thử với 1 người, chỉnh thời gian chuẩn và lời đọc tác vụ |
| 01–03/12 | Buổi chính, 8–10 người, mỗi người khoảng 25 phút |
| 04/12 | Tổng hợp số liệu, SUS, danh sách vấn đề |
| 05–08/12 | Sửa các vấn đề ưu tiên, ghi `cai-tien.md`, đo lại nếu kịp |
