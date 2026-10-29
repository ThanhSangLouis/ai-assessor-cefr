# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 20. Chương 1 - Mở đầu (bản nháp tuần 1)

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | Cả nhóm; SV2 chủ biên |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

> Trạng thái bằng chứng: đây là draft lập luận, chưa có pilot/human/model result. Mọi mục tiêu kỹ thuật, quy mô và ngưỡng là đề xuất cần decision/validation; không được trình bày như kết quả đo.

## 1.1. Bối cảnh

Năng lực nói là một thành phần quan trọng của việc sử dụng ngoại ngữ trong học tập, công việc và giao tiếp xã hội. Tuy nhiên, đánh giá bài nói cần người chấm có chuyên môn, thời gian nghe lại, tiêu chí rõ và quy trình duy trì sự nhất quán. Trong lớp học đông, giảng viên khó cung cấp phản hồi chi tiết cho từng sinh viên sau mỗi hoạt động nói. Kết quả thường bị rút gọn thành một điểm tổng hoặc nhận xét chung, trong khi người học cần biết cụ thể mình đang gặp vấn đề ở phạm vi ngôn ngữ, độ chính xác, độ trôi chảy, tương tác, mạch lạc hay khả năng làm người nghe hiểu.

Sự phát triển của nhận dạng tiếng nói tự động, xử lý âm thanh, xử lý ngôn ngữ tự nhiên và mô hình ngôn ngữ tạo điều kiện xây dựng công cụ hỗ trợ phân tích bài nói. Tuy nhiên, việc một hệ thống có thể tạo transcript hoặc sinh nhận xét không có nghĩa hệ thống đã đánh giá đúng năng lực theo CEFR. Một hệ thống đánh giá có giá trị phải bắt đầu từ construct, nhiệm vụ tạo bằng chứng, rubric do chuyên gia ngôn ngữ sở hữu và dữ liệu được con người chấm theo quy trình độc lập.

[CEFR Companion Volume 2020](https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4) xem người học là tác nhân xã hội và mô tả năng lực thông qua các hoạt động giao tiếp và descriptor tích cực. CEFR không phải bài thi hay thuật toán. Appendix 3 trình bày sáu đặc trưng định tính của lời nói: Range, Accuracy, Fluency, Interaction, Coherence và Phonology. Các phương diện này tạo khung khái niệm cho đề tài, nhưng cần được vận hành hóa phù hợp sinh viên Việt Nam và kiểm định trong bối cảnh sử dụng cụ thể.

## 1.2. Vấn đề nghiên cứu

Đề tài giải quyết ba khoảng cách. Thứ nhất, giảng viên cần phản hồi nhanh nhưng không thể hy sinh tính nhất quán và quyền quyết định chuyên môn. Thứ hai, hệ thống AI có thể đo nhiều dấu hiệu nhưng các dấu hiệu như tốc độ nói, số pause, độ đa dạng từ vựng hoặc confidence của ASR chỉ là proxy cho một phần construct. Thứ ba, accent Việt, điều kiện thu âm và lỗi ASR có thể làm sai transcript và kéo theo sai số đánh giá nếu không có quality flags, manual audit và teacher review.

[Manual for Language Test Development and Examining sửa đổi 2026](https://rm.coe.int/new-revised-manual-for-language-test-development-and-examining-joint-p/48802cc30d) yêu cầu automated rating được đánh giá về accuracy, reliability, robustness và explainability, đồng thời duy trì quality monitoring. Vì vậy, khả năng tạo transcript hoặc gọi LLM chưa đủ để khẳng định CEFR alignment nếu thiếu task specification, speaker-level split, human-human agreement, calibration, uncertainty và error analysis. Đặc biệt, Interaction không thể được suy luận hợp lệ từ bài độc thoại, và Phonology không nên phạt accent nếu thông điệp vẫn intelligible.

## 1.3. Phát biểu bài toán

Làm thế nào xây dựng một hệ thống AI có thể hỗ trợ ước lượng mức Speaking A2-B2 của sinh viên đại học Việt Nam theo sáu tiêu chí CEFR, cung cấp confidence và bằng chứng truy vết được, đồng thời đạt mức đồng thuận hữu ích so với giảng viên trên dữ liệu tách theo người nói và có cơ chế chuyển ca bất định cho con người?

## 1.4. Mục tiêu

### Mục tiêu tổng quát

Xây dựng và kiểm định một proof-of-concept AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam A2-B2 trong bối cảnh formative/low-stakes.

### Mục tiêu cụ thể

1. Xây task blueprint bao phủ spoken production và spoken interaction.
2. Vận hành hóa sáu tiêu chí CEFR thành rubric và evidence map.
3. Thu bộ dữ liệu người Việt có consent, double-rating và adjudication.
4. Xây các baseline được phê duyệt, tối thiểu audio-only và transcript-only; local LLM chỉ giữ nếu privacy/license/compute được duyệt.
5. Xây late-fusion model có calibration và teacher-review threshold.
6. Đánh giá agreement, error, reliability, robustness và usability.
7. Xuất speaking profile có evidence, limitation và model/rubric version.

## 1.5. Câu hỏi nghiên cứu

- RQ1: AI-human agreement ở mức nào so với human-human reference, với uncertainty nào?
- RQ2: Fusion có cải thiện các baseline đơn kênh không?
- RQ3: WER, noise, duration, device và prompt liên quan sai số thế nào?
- RQ4: Confidence/calibration có phát hiện ca cần teacher review không?
- RQ5: Grounded feedback có rõ và hành động được không?
- RQ6: Kết quả ổn định giữa prompt, lần chạy và nhiễu ở mức nào?

## 1.6. Phạm vi

Đối tượng là sinh viên đại học Việt Nam từ 18 tuổi, A2-B2. Hệ thống dự kiến dùng Task A kể/mô tả, Task B trình bày quan điểm và Task C hội thoại bán cấu trúc nếu thiết kế/pilot tạo đủ evidence. Kết quả chỉ phục vụ formative/diagnostic use. Hệ thống không cấp chứng chỉ, không tự quyết định học vụ, không đánh giá A1/C1/C2 và không suy luận thuộc tính nhạy cảm.

Mediation không thuộc MVP vì cần nhiệm vụ riêng để tạo bằng chứng về xử lý/truyền đạt nội dung hoặc vai trò trung gian. Interaction chỉ được chấm từ task có hội thoại. Phonology tập trung vào intelligibility, sound articulation và prosody; accent không bị coi là lỗi tự thân.

## 1.7. Vai trò AI và con người

Theo protocol `PROPOSED`, giảng viên Ngoại ngữ thiết lập/sở hữu rubric, chọn anchor, tham gia hiệu chuẩn và xử lý ca khó; hai rater chấm độc lập để ước lượng human-human agreement và adjudicator phân xử theo rule được duyệt. AI phân tích audio, transcript và turn log, tạo probability, confidence và evidence. Giảng viên giữ quyền xác nhận/sửa kết quả. Sinh viên được xem phản hồi, hiểu giới hạn và thực hiện nhiệm vụ luyện tiếp. Danh tính/cam kết của rater và adjudicator hiện chưa được xác nhận.

## 1.8. Đóng góp dự kiến

- Một task/rubric/evidence design minh bạch cho A2-B2.
- Một bộ dữ liệu thí điểm người Việt có nhãn nhiều người chấm.
- Một pipeline multimodal có baseline, fusion và calibration.
- Một khung đánh giá báo uncertainty, human ceiling và error conditions.
- Một hồ sơ `speaking_profile` có thể kết nối với module học tập khác nhưng không xây toàn hệ sinh thái.

## 1.9. Cấu trúc phần còn lại

Chương 2 trình bày nền tảng và nghiên cứu liên quan. Chương 3 mô tả phương pháp, task, rubric, dữ liệu và thống kê. Chương 4 trình bày hệ thống. Chương 5 báo cáo kết quả. Chương 6 thảo luận validity, fairness, usability và giới hạn. Chương 7 kết luận và hướng phát triển.

## Tài liệu nền cần trích dẫn chính thức

- Council of Europe (2001), CEFR.
- Council of Europe (2020), CEFR Companion Volume.
- Council of Europe, Manual for Relating Language Examinations to the CEFR.
- ALTE CEFR SIG (2014), CEFR Grid for Speaking Tests.
- North và Piccardo (2016), mediation descriptors.
- Council of Europe & ALTE (2026), *New revised Manual for Language Test Development and Examining*.
- Quốc hội (2025), Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15; Chính phủ (2025), Nghị định 356/2025/NĐ-CP.
