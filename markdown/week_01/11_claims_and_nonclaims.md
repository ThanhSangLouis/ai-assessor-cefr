# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 11. Ma trận tuyên bố và giới hạn tuyên bố

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Quy tắc

Mỗi claim phải gắn với population, task, metric, uncertainty và human oversight. Không viết claim rộng hơn dữ liệu.

Hiện chưa có pilot, human rating hoặc model result. Mọi `N`, metric, CI, threshold hiệu quả và kết luận so sánh phải giữ ở dạng `[CẦN ĐO]`; không được dùng số mục tiêu quản trị như kết quả đo.

## 2. Claims được phép nếu có bằng chứng

| Claim dự kiến | Bằng chứng tối thiểu | Cách viết an toàn |
| --- | --- | --- |
| AI đồng thuận hữu ích với giảng viên | Human-human trước; AI-human QWK + CI; error rate | “Trên mẫu nghiên cứu..., hệ thống đạt...” |
| Fusion cải thiện baseline | Cùng speaker folds; paired cluster bootstrap; CI | “Có/không có bằng chứng cải thiện trong thiết kế này” |
| Confidence hỗ trợ teacher review | Calibration plot; error theo threshold; workload | “Threshold phát hiện một phần ca sai với trade-off...” |
| Feedback có evidence dễ hiểu hơn | Usability protocol và phản hồi người dùng | “Người tham gia đánh giá... trong thử nghiệm nhỏ” |
| WER/noise liên quan sai số | Manual transcript subset; stratified/error analysis | “Sai số tăng trong nhóm điều kiện..., chưa khẳng định nhân quả” |
| Điểm ổn định ở mức nhất định | Repeated runs/equivalent prompts/reliability analysis | “Mức ổn định quan sát được...” |

## 3. Non-claims

- “Hệ thống được CEFR chứng nhận.”
- “AI chấm chính xác hơn giảng viên.”
- “Kết quả áp dụng cho mọi người Việt hoặc mọi accent.”
- “Hệ thống cấp chứng chỉ/xếp lớp tự động.”
- “Không có bias” chỉ vì không phát hiện significance trong mẫu nhỏ.
- “Fusion không có tác dụng” khi CI còn rộng.
- “Phonology thấp vì accent Việt.”
- “LLM hiểu toàn bộ năng lực giao tiếp từ transcript.”
- “Mẫu 70-90 chắc chắn đủ” khi precision analysis chưa được tái tạo và duyệt.
- “G1/ethics/rater đã được duyệt” khi chưa có biên bản hoặc xác nhận thực tế.

## 4. Wording templates

### Kết quả dương

“Trên [N] sinh viên thuộc [population], với dữ liệu tách theo speaker và [protocol], mô hình [version] đạt [metric, CI] so với nhãn [human protocol]. Kết quả chỉ hỗ trợ đánh giá formative và các ca [threshold] cần giảng viên duyệt.”

### Không kết luận được

“Ước lượng chênh lệch là [value, CI]. Khoảng bất định còn bao gồm các hiệu ứng có ý nghĩa thực tế; vì vậy nghiên cứu chưa đủ bằng chứng để kết luận hai phương án tương đương hoặc khác nhau.”

### Giới hạn fairness

“Phân tích subgroup mang tính thăm dò vì kích thước nhóm nhỏ; không phát hiện chênh lệch không đồng nghĩa đã chứng minh không có sai lệch.”

## 5. Claim review checklist

- [ ] Có population và task context.
- [ ] Có metric và uncertainty.
- [ ] Có human-human reference.
- [ ] Có giới hạn intended use.
- [ ] Không dùng ngôn ngữ chứng nhận/đảm bảo tuyệt đối.
- [ ] Số liệu kết quả có artifact tái lập; placeholder chưa đo không bị xóa.
