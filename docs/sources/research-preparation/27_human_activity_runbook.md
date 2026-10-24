# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 27. Runbook hoàn tất các hoạt động con người tuần 1

| Thuộc tính | Giá trị |
| --- | --- |
| Mục đích | Chạy phần W1 không thể được AI thực hiện hoặc tự phê duyệt |
| Trạng thái tài liệu | READY TO EXECUTE |
| Trạng thái hoạt động | NOT STARTED |
| Ngày chuẩn bị/cập nhật | 02/09/2026 / 12/09/2026 |

Không ghi hồi tố, không dùng điểm/kết quả do AI tạo và không đổi `PROPOSED` thành `APPROVED` nếu thiếu xác nhận thực tế.

## 1. Quy tắc lưu bằng chứng

- Trong repository chỉ lưu kết quả đã giả danh, decision ID, ngày, role và `approval_ref` không chứa PII.
- Danh bạ có tên/liên hệ, phiếu cá nhân, chữ ký và biên bản có danh tính lưu tại governance/ethics storage được duyệt, không commit.
- `approval_ref` phải trỏ được tới bản gốc có kiểm soát nhưng không nhúng tên, email, chữ ký hoặc đường dẫn nhận dạng vào log công khai.
- Mỗi hoạt động có facilitator, người tham gia thật, thời gian, input version và kết luận/deviation.

## 2. Phiên familiarisation 1: đọc nguồn

| Trường | Giá trị |
| --- | --- |
| Thành phần tối thiểu | SV1, SV2, SV3; GV Ngoại ngữ kiểm tra chéo |
| Thời lượng | 90 phút tự đọc + 30 phút đối chiếu |
| Input | `02_source_reading_log.md`, sáu nguồn chính thức |
| Output | Một log/người/nguồn được giao; ba kết luận, một rủi ro, một câu hỏi |
| Điều kiện đạt | Không chỉ ghi “đã đọc”; điểm bất đồng được đưa vào `08`/`21` |

Trình tự:

1. SV2 phân nguồn và ghi version.
2. Từng người đọc độc lập, điền log trước thảo luận.
3. GV Ngoại ngữ kiểm tra các kết luận về construct/descriptor.
4. SV2 tổng hợp nhưng giữ lại khác biệt, không sửa thành đồng thuận giả.

## 3. Phiên familiarisation 2: descriptor sorting

| Trường | Giá trị |
| --- | --- |
| Thời lượng | 20 phút cá nhân + 15 phút cặp + 20 phút nhóm + 10 phút debrief |
| Input | Bộ 18 thẻ trong `03_descriptor_sorting_result.md`; bản làm phải ẩn cột đáp án |
| Output | Phiếu trước/sau thảo luận, tổng điểm và loại lỗi hiểu |
| Điều kiện đạt | Mỗi người ít nhất 15/18 sau thảo luận; không phạt accent; không chấm Interaction từ độc thoại |

Facilitator phải lưu phiếu trước khi mở answer key. Nếu ai đã xem đáp án, gắn `INVALID_PRIOR_EXPOSURE` và dùng bộ thẻ tương đương khác sau khi được GV Ngoại ngữ duyệt.

## 4. Phiên familiarisation 3: quiz

| Trường | Giá trị |
| --- | --- |
| Thời lượng | 25 phút cá nhân + 20 phút chấm/debrief |
| Input | 20 câu và answer key trong `04_cefr_familiarisation_check.md` |
| Output | Điểm lần 1, nội dung đọc lại, điểm kiểm tra lại nếu có |
| Điều kiện đạt | 18-20 đạt; 15-17 đọc lại/test lại; dưới 15 chưa tham gia chốt rubric |

Người làm không được mở answer key. Kết quả phải do người kiểm tra thật xác nhận; Codex/AI không được đứng tên người làm hoặc người chấm.

## 5. Pedagogy workshop

| Phần | Phút | Quyết định/evidence |
| --- | ---: | --- |
| Nhắc intended use và non-claims | 10 | D002 |
| Review construct/sáu criteria | 30 | D003, D006 |
| Production-Interaction-Mediation boundary | 25 | D004, D005 |
| Task C/interlocutor và missing rule | 25 | D013, Q14/Q27 |
| Rating workload/two-pass/adjudication | 20 | D007, D012 |
| Kết luận và action items | 10 | approval/ref, owner, deadline |

Mỗi decision ghi một trong `APPROVE`, `REVISE`, `REJECT`, `DEFER`. `DEFER` phải có owner/deadline và vẫn là blocker nếu ảnh hưởng construct.

## 6. Chỉ định rater và adjudicator

Trước khi collection/rating, GVHD xác nhận ngoài repository:

| Trường cần xác nhận | Rater 1 | Rater 2 | Adjudicator |
| --- | --- | --- | --- |
| Đủ chuyên môn Speaking/CEFR | [ ] | [ ] | [ ] |
| Không xem AI output trước independent rating | [ ] | [ ] | N/A |
| Cam kết lịch training/rating | [ ] | [ ] | [ ] |
| Hiểu two-pass và listening limit | [ ] | [ ] | [ ] |
| Hiểu accent/intelligibility rule | [ ] | [ ] | [ ] |
| Conflict of interest đã khai báo | [ ] | [ ] | [ ] |

Repository chỉ ghi role IDs `RATER-01`, `RATER-02`, `ADJ-01`, trạng thái và approval reference; không ghi tên/liên hệ.

## 7. Data/ethics review

Reviewer phải chốt bằng văn bản:

- mẫu/đơn vị ethics áp dụng;
- nơi lưu identity và research data;
- cơ chế encryption cụ thể, key owner và recovery;
- role access matrix và backup target;
- retention, withdrawal cutoff và deletion limits;
- kênh liên hệ/khiếu nại;
- có cấm cloud/external API hay cho phép opt-in nào.

Sau khi cấu hình approved storage, chạy lại `tools/week1_dmp_synthetic_check.py` và bổ sung test thực cho encryption/access. Không tuyển người trước bước này.

## 8. G1 review

Pre-read: `25_G1_review_pack.md`; biên bản: `22_G1_review_minutes.md`.

1. Thư ký ghi attendance và `approval_ref` tại thời điểm họp.
2. Chủ trì xử lý D002-D016 theo agenda; D019 chỉ được ghi nhận là quyết định repository của người dùng.
3. Mọi mục `REVISE/DEFER` có owner/deadline.
4. Gate chỉ là `PASS`, `CONDITIONAL PASS` hoặc `FAIL`; không dùng từ “DONE” thay gate status.
5. Sau họp, SV3 cập nhật decision log và các file bị ảnh hưởng; một reviewer khác đối chiếu consistency.

## 9. Form handoff không chứa PII

| Activity ID | Ngày | Input version | Kết quả | Approval ref | Owner follow-up | Deadline |
| --- | --- | --- | --- | --- | --- | --- |
| W1-FAM-READ | [Điền] | [Điền] | [PASS/REVISE] | [Mã tham chiếu] | [Role] | [Ngày] |
| W1-FAM-SORT | [Điền] | [Điền] | [PASS/REVISE] | [Mã tham chiếu] | [Role] | [Ngày] |
| W1-FAM-QUIZ | [Điền] | [Điền] | [PASS/REVISE] | [Mã tham chiếu] | [Role] | [Ngày] |
| W1-PED-LAB | [Điền] | [Điền] | [PASS/REVISE] | [Mã tham chiếu] | [Role] | [Ngày] |
| W1-DATA-ETHICS | [Điền] | [Điền] | [PASS/REVISE] | [Mã tham chiếu] | [Role] | [Ngày] |
| W1-G1 | [Điền] | [Điền] | [PASS/CONDITIONAL PASS/FAIL] | [Mã tham chiếu] | [Role] | [Ngày] |

## 10. Stop conditions

Dừng và không đánh dấu hoàn tất nếu:

- người làm sorting/quiz đã xem đáp án trước;
- không có GV Ngoại ngữ cho quyết định construct;
- chưa có hai rater độc lập và adjudicator cho reference rating;
- storage/consent/ethics chưa duyệt nhưng chuẩn bị thu dữ liệu thật;
- approval chỉ được truyền miệng và không có reference có thể audit;
- G1 còn blocker không có owner/deadline.
