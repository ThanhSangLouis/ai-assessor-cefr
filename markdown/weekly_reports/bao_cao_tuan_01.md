# BÁO CÁO TIẾN ĐỘ TUẦN 1

## Chốt bài toán và điều kiện nghiên cứu

| Thông tin | Nội dung |
| --- | --- |
| Tên đề tài | Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2 |
| Nhóm thực hiện | `[Điền họ tên và MSSV]` |
| Giảng viên hướng dẫn | `[Điền họ tên]` |
| Thời gian báo cáo | Tuần 1 theo kế hoạch; tổng hợp đến 12/09/2026 |
| Trạng thái tuần | **Hồ sơ đã chuẩn bị; hoạt động con người và phê duyệt còn chờ** |
| Cổng nghiệm thu | **G1 `NOT HELD` — chưa được phép ghi PASS/APPROVED** |
| Phiên bản minh chứng Git | `d9058bdc89951ad048c3d4008f3a45f8d0952f7e` |

## 1. Mục tiêu tuần

Tuần 1 nhằm xác định đúng đối tượng, construct đánh giá, phạm vi sử dụng, câu hỏi nghiên cứu, nhân sự chấm và điều kiện quản trị dữ liệu. Cổng G1 chỉ đạt khi giảng viên hướng dẫn phê duyệt phạm vi/RQ, giảng viên Ngoại ngữ xác nhận construct, có kế hoạch rater khả thi và các vấn đề dữ liệu–đạo đức có owner cùng thời hạn xử lý.

## 2. Tóm tắt kết quả

Nhóm đã xây dựng được nền tảng học thuật và hồ sơ quản trị tương đối đầy đủ để đưa vào buổi review G1. Đề tài được giữ đúng mục đích formative/diagnostic, low-stakes; AI chỉ hỗ trợ chấm sơ bộ, còn giảng viên giữ quyền kiểm duyệt và quyết định cuối cùng. Sáu tiêu chí mục tiêu là Range, Accuracy, Fluency, Interaction, Coherence và Phonology trong dải A2-B2.

Kết quả tiền thẩm định sư phạm của AI là **“READY FOR HUMAN REVIEW WITH REQUIRED REVISIONS”**. Đây là nhận xét chuẩn bị trước review, không phải phê duyệt của giảng viên. Tuần 1 chưa thể đóng vì các hoạt động familiarisation, workshop, chỉ định rater/adjudicator, ethics/storage review và cuộc họp G1 chưa diễn ra.

## 3. Công việc đã thực hiện

| Hạng mục | Kết quả | Trạng thái |
| --- | --- | --- |
| Phạm vi và intended use | Xác định population là sinh viên đại học Việt Nam từ 18 tuổi, A2-B2; loại trừ mục đích chứng chỉ, đậu/rớt, xếp lớp tự động và thay thế giảng viên | `READY FOR REVIEW` |
| Construct CEFR | Lập hệ sáu tiêu chí và nguyên tắc evidence; Interaction không được suy từ độc thoại; Phonology dựa trên intelligibility, không phạt accent Việt | `READY FOR REVIEW` |
| Câu hỏi nghiên cứu và validation | Soạn RQ, validation argument, nguyên tắc human-human trước AI-human, split theo speaker và truy vết version/evidence | `READY FOR REVIEW` |
| Thiết kế nhiệm vụ | Chuẩn bị task/evidence map và đặc tả ứng viên cho Task A, B, C | `READY FOR REVIEW` |
| Dữ liệu, riêng tư và đạo đức | Soạn DMP, consent, quyền rút dữ liệu, risk register, RACI và checklist tách identity khỏi research workspace | `READY FOR ETHICS REVIEW` |
| Kiểm tra DMP bằng synthetic data | Chạy lại sáu kiểm tra logic thành công; không đọc hoặc tạo dữ liệu người thật | `COMPLETED WITH LIMITATIONS` |
| Hồ sơ review | Chuẩn bị gói G1, agenda quyết định, runbook hoạt động con người và AI pedagogical pre-review | `READY TO EXECUTE/REVIEW` |
| Lane viết luận văn | Có bản nháp nội dung Chương 1 để GVHD kiểm tra claim và citation | `READY FOR REVIEW` |
| Khả năng truy vết | Phục hồi Git hợp lệ, tạo baseline và commit bộ hồ sơ W1-W3 | `COMPLETED` |

## 4. Minh chứng chính

- [Bản đồ hồ sơ tuần 1](../week_01/README.md).
- [Gói review G1 và ma trận hoàn thành](../week_01/25_G1_review_pack.md).
- [Báo cáo kiểm tra DMP bằng dữ liệu synthetic](../week_01/26_synthetic_dmp_test_report.md).
- [Runbook cho các hoạt động cần người thật](../week_01/27_human_activity_runbook.md).
- [Tiền thẩm định sư phạm của AI](../week_01/28_ai_pedagogical_pre_review.md).
- [Decision log tuần 1](../week_01/21_week1_decision_log.md).

## 5. Kết quả kiểm tra dữ liệu và riêng tư

| Kiểm tra synthetic | Kết quả | Phạm vi diễn giải |
| --- | --- | --- |
| Tách identity khỏi research workspace | `PASS` | Chỉ chứng minh trên fixture synthetic |
| Boundary schema | `PASS` | Phát hiện thiếu trường bắt buộc theo test hiện tại |
| Log privacy | `PASS` | Log test không chứa identity/audio/transcript |
| Snapshot checksum và raw artifact bất biến | `PASS` | Khớp SHA-256 trong phiên test |
| Withdrawal/deletion | `PASS` | Workflow synthetic hoạt động và có deletion log không chứa identity trực tiếp |
| Cleanup workspace tạm | `PASS` | Phiên chạy cuối tự dọn dữ liệu tạm |
| Mã hóa dữ liệu lưu trữ | `NOT TESTED` | Chưa có storage, key owner và cấu hình được duyệt |
| Phân quyền theo vai trò | `NOT TESTED` | Chưa có tài khoản/role thật |

Các kết quả `PASS` trên không chứng minh môi trường production đã an toàn và không thay thế ethics approval.

## 6. Đánh giá chuyên môn dưới góc nhìn giáo viên

### Điểm mạnh

- Định vị đề tài đúng: AI hỗ trợ đánh giá quá trình, không tự nhận vai trò chứng nhận CEFR.
- Construct được bảo vệ tốt: không dùng một vài proxy kỹ thuật như tốc độ nói hoặc ASR confidence để thay toàn bộ năng lực nói.
- Quy tắc xử lý thiếu bằng chứng hợp lý: độc thoại không tạo điểm Interaction; dữ liệu lỗi không bị đổi thành điểm mặc định.
- Hướng đánh giá Phonology công bằng hơn khi tập trung vào intelligibility và listener effort, không coi accent Việt là thiếu hụt.
- Hồ sơ có decision log, reason code và kế hoạch truy vết, phù hợp cho nghiên cứu cần audit.

### Điểm còn yếu

- Descriptor mới là nền cho workshop, chưa có anchor thật và chưa chứng minh hai rater hiểu ranh giới A2/B1/B2 giống nhau.
- Task C chưa được pilot nên chưa biết mức độ chuẩn hóa, contingency, ảnh hưởng của interlocutor và tính hợp lệ của latency.
- Chưa có quy tắc overall band đã standardise; không được tự trung bình sáu tiêu chí hoặc sinh overall tự động.
- Chưa có bằng chứng hoạt động học thuật của từng thành viên qua reading log, descriptor sorting và quiz.
- DMP mới kiểm tra logic synthetic; encryption, access control, retention và incident workflow vẫn mở.

### Nhận định tổng hợp

Nếu đánh giá như một giáo viên, bộ hồ sơ tuần 1 **đạt mức khá về chuẩn bị học thuật và quản trị**, nhưng **chưa đạt điều kiện nghiệm thu tuần** do thiếu xác nhận con người và bằng chứng vận hành. Không nên bắt đầu thu dữ liệu thật hoặc chấm CEFR trước khi đóng các mục bắt buộc của G1.

## 7. Phần chưa hoàn tất và hành động cần làm

| Việc còn thiếu | Người/nhóm cần thực hiện | Minh chứng cần tạo | Điều kiện hoàn tất |
| --- | --- | --- | --- |
| CEFR familiarisation: đọc nguồn, descriptor sorting, quiz | Ba thành viên | Log và kết quả ẩn danh theo runbook | Có kết quả thật; không tự điền điểm |
| Pedagogy workshop | Nhóm + GV Ngoại ngữ/GVHD | Biên bản, quyết định và action items | Wording construct/task được xác nhận hoặc yêu cầu sửa |
| Chỉ định 2 rater + 1 adjudicator | Chủ dự án/GVHD | Roster và cam kết lịch thực tế, lưu ngoài repo nếu có PII | Có role, availability và quy trình blind rating |
| Chốt Task C, overall rule và precision assumptions | Người duyệt có thẩm quyền | Decision log D011-D015 cập nhật | Có trạng thái, approver, ngày và điều kiện rõ |
| Storage/retention/encryption/access | Owner dữ liệu + reviewer ethics | Cấu hình được duyệt và test report | Hai test còn thiếu được chạy trên môi trường duyệt |
| Họp G1 | GVHD và các vai trò liên quan | `22_G1_review_minutes.md` | Ghi `PASS`, `CONDITIONAL PASS` hoặc `FAIL` thật |

## 8. Kế hoạch chuyển tiếp

1. Tổ chức các phiên familiarisation và pedagogy workshop theo runbook.
2. Chỉ định rater/adjudicator và chốt owner cho dữ liệu–đạo đức.
3. Họp G1 theo agenda; cập nhật D002-D016 bằng quyết định thực tế.
4. Nếu G1 đạt hoặc đạt có điều kiện, mới khóa phạm vi rubric, task và protocol cho tuần 2.
5. Nếu G1 chưa đạt, sửa hồ sơ theo finding trước khi mở hoạt động pilot hoặc thu dữ liệu.

## 9. Kết luận tuần

Tuần 1 đã tạo được một bộ nền tảng có chất lượng để hội đồng xem xét: scope rõ, construct phù hợp, privacy được coi là yêu cầu thiết kế và các rủi ro đo lường quan trọng đã được nhận diện. Tuy nhiên, kết luận chính thức vẫn là:

> **Deliverables prepared; human activities and G1 approval pending; W1 NOT DONE.**

| Xác nhận | Nội dung |
| --- | --- |
| Đại diện nhóm | `[Ký/ghi họ tên sau khi kiểm tra nội dung]` |
| Giảng viên hướng dẫn | `[Ý kiến và chữ ký thực tế]` |
| Ngày trình | `[Điền ngày]` |
