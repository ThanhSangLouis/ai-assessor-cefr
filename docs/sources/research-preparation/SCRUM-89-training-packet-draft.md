# SCRUM-89 — Gói tập huấn hai người chấm (bản nháp)

**Trạng thái:** `DRAFT — NOT APPROVED — NOT RUN`  
**Task:** SCRUM-89 — Tập huấn hai người chấm  
**Nguồn tham khảo:** `KE_HOACH_KHAO_SAT.md` §6; `06_cefr_A2_B1_B2_descriptor_map.md`; `07_construct_evidence_matrix.md`; `14_ALTE_speaking_grid_draft.md`; `27_human_activity_runbook.md`; `28_ai_pedagogical_pre_review.md`. Tất cả là `REFERENCE_ONLY` trong branch này.  
**Phạm vi tài liệu:** chuẩn bị quy trình và mẫu bằng chứng. Tài liệu này không xác nhận đã có rater, buổi tập huấn, calibration result hoặc phê duyệt.

## 1. Mục tiêu

Chuẩn bị hai người chấm sử dụng cùng một rubric/version, chấm độc lập và không thấy identity, điểm AI hoặc điểm người chấm còn lại. Trước khi bắt đầu chấm dữ liệu nghiên cứu, phải có bằng chứng người chấm hiểu rubric và đạt ngưỡng calibration do owner/GVHD phê duyệt.

## 2. Gate trước khi đặt lịch

Chỉ tổ chức khi các điều kiện dưới đây đã được xác nhận. Nếu thiếu điều kiện, giữ `NOT_RUN` và không phát audio cho người chấm.

| Gate | Điều kiện cần | Trạng thái hiện tại |
|---|---|---|
| Rubric | Có rubric, scoring sheet, decision rules và version đã được M05 owner/GVHD duyệt; thống nhất 5 tiêu chí cho độc thoại và cách xử lý `Interaction=null`. | `PENDING` — nguồn đang có bản 5 tiêu chí và tài liệu draft 6 tiêu chí. |
| Samples | Có danh sách mẫu giả danh, quyền sử dụng audio và consent phù hợp; giữ identity map tách riêng. | `PENDING` — chưa có sample set được xác nhận. |
| Answer key | Mỗi calibration sample có điểm tham chiếu/consensus được người có chuyên môn xác nhận trước buổi chấm. | `PENDING` — chưa có anchor hoặc answer key được duyệt. |
| Raters | Hai người thật đủ chuyên môn, không xung đột lợi ích, đã xác nhận lịch; dùng role ID trong repo. | `NOT_VERIFIED`. |
| Blind workflow | Có kênh phân phối ẩn AI output, identity và rating của người còn lại; xác nhận bằng test/checklist trước khi gửi. | `PENDING` — M12 vẫn `DRAFT/PENDING`; M07 không được claim là blind UI. |
| Calibration rule | Chốt trước phép đo, unit, weighting, target/threshold và remediation rule. | `PENDING` — nguồn đề xuất weighted kappa ≥ 0,70, chưa được duyệt cho task này. |
| Governance | Có approval reference, approved storage/access, retention và evidence location. | `PENDING` — DMP/consent nguồn `DRAFT`; encryption/access còn thiếu test. |

## 3. Hai hoạt động riêng

Không gộp dry run vận hành và calibration thành một kết quả.

### A. Dry run vận hành — đề xuất 4–6 mẫu

Nguồn AI pre-review đề xuất 4–6 mẫu để đo độ rõ của hướng dẫn, thời gian chấm, bất đồng, tải nhận thức và fatigue. Đây là usability/workload check, **không phải** phép chứng nhận độ tin cậy, không dùng để tuyên bố đạt kappa, và không thay bộ calibration.

1. Chỉ dùng mẫu có quyền/consent phù hợp và đã giả danh.
2. Mỗi rater đọc hướng dẫn rồi chấm độc lập theo cùng rubric/version.
3. Ghi thời gian thực tế, câu hỏi về rubric, điểm khó hiểu và nguyên nhân bất đồng; không mở answer key trước khi khóa hai lượt chấm.
4. Sau khi khóa lượt độc lập, facilitator mới điều phối debrief. Ghi đề xuất sửa thành action item, không âm thầm đổi rubric giữa phiên.
5. Nếu đổi rubric hoặc scoring sheet, tăng version và chuẩn bị lại toàn bộ tài liệu cho calibration.

### B. Calibration — đề xuất 10 mẫu

Kế hoạch khảo sát nguồn đề xuất 10 mẫu có điểm đồng thuận từ trước và weighted kappa ≥ 0,70 trước khi bắt đầu chấm thật. Đây vẫn là **đề xuất**, cần owner/GVHD phê duyệt cả sample set, metric, cách tính và ngưỡng.

1. Khóa danh sách 10 mẫu, rubric/version, answer key và metric trước khi mở lượt chấm.
2. Xáo thứ tự riêng cho mỗi rater; không đưa identity, baseline level, transcript nếu protocol không cho phép, machine result hoặc rating còn lại.
3. Hai rater chấm độc lập; ghi raw rating và thời gian vào evidence storage được duyệt. Không thảo luận mẫu cho tới khi hai lượt đã khóa.
4. Tính metric theo cách đã được chốt trên **các lượt độc lập trước debrief**. Ghi actual value hoặc `NOT_RUN`; không nhập kết quả ước tính.
5. Nếu chưa đạt threshold đã duyệt, không bắt đầu chấm thật. Lập remediation plan, cập nhật training material nếu được duyệt, rồi đánh giá lại trên bộ mẫu tương đương khác đã có quyền sử dụng. Không xóa lượt đầu hoặc thay điểm để biến kết quả thành đạt.
6. Chỉ sau khi người có thẩm quyền xem evidence mới ghi readiness; tài liệu này không đưa verdict thay họ.

## 4. Agenda cho facilitator

Thời lượng từng phần phải được thống nhất sau dry run; không đặt thời lượng cam kết trong bản nháp này.

| Bước | Hoạt động | Điều kiện/ghi chú |
|---|---|---|
| 1 | Xác nhận version rubric, prompt, scoring sheet và sample-set ID. | Nếu version không khớp, dừng. |
| 2 | Đọc mục đích sử dụng, giới hạn claim, quy tắc accent/intelligibility và `insufficient_evidence`. | Không dạy rater suy band từ accent hoặc độ dài một cách máy móc. |
| 3 | Ôn từng tiêu chí và decision rules bằng anchor đã được duyệt. | Hiện chưa có anchor thật; không tự tạo gold answer. |
| 4 | Thực hành dry run độc lập, ghi câu hỏi và thời gian. | Không xem AI score/report. |
| 5 | Khóa phiếu; sau đó mới thảo luận điểm khác biệt. | Giữ nguyên raw ratings. |
| 6 | Thực hiện calibration riêng nếu đã được phê duyệt. | Dùng bộ 10 mẫu riêng; tính metric trước khi debrief. |
| 7 | Ghi outcome, remediation và sign-off. | Facilitator không tự ký thay rater/GVHD. |

## 5. Quy tắc blind và lưu bằng chứng

- Dùng `RATER-01`, `RATER-02`, `FACILITATOR` và `ADJ-01` nếu có adjudicator. Không ghi tên, email, lớp hoặc thông tin liên hệ trong repo.
- Không dùng trang M07 hiện tại để khẳng định chấm mù: M07 ghi UI có thể hiển thị AI result cho teacher. Chỉ dùng một quy trình đã được M12/owner duyệt và đã kiểm tra leakage.
- Không đưa audio, transcript có PII, identity map, chữ ký hoặc raw restricted score sheet lên Git. Lưu chúng trong vị trí được ethics/GVHD phê duyệt; repo chỉ lưu pseudonymous activity ID, trạng thái, version và `approval_ref` không nhận dạng.
- Chỉ điền ngày và kết quả sau hoạt động thực tế. Trước đó dùng `NOT_RUN`, `NOT_VERIFIED`, `NOT_EVALUATED`.

## 6. Quyết định cần owner/GVHD chốt

| ID | Câu hỏi | Hệ quả nếu chưa chốt |
|---|---|---|
| S89-D01 | Rubric/version nào được dùng; sheet có 5 tiêu chí + overall nào; band/score mapping và `Interaction` cho độc thoại ra sao? | Chưa thể hoàn thiện nội dung tập huấn. |
| S89-D02 | 4–6 mẫu dry run và 10 mẫu calibration là hai bộ riêng hay cùng sample pool nhưng tách use? Ai xác nhận đáp án chuẩn? | Chưa thể phát audio hoặc tính readiness. |
| S89-D03 | Metric nào là gate: weighted kappa trên band, điểm 0–6 hay cả hai; cách xử lý unrateable/missing; threshold có thực sự là 0,70? | Chưa thể tính/diễn giải calibration. |
| S89-D04 | Quy trình offline hay app; nếu app, ai sở hữu M12 blind policy và leakage verification? | M07 không đáp ứng tuyên bố blind rating. |
| S89-D05 | Ai là hai rater thật, xác nhận chuyên môn, conflict, lịch và commitment ở đâu được giữ? | Roster hiện `NOT_VERIFIED`; không thể ghi attendance/readiness. |
| S89-D06 | Sample audio nào được phép dùng, consent/retention/storage nào áp dụng và ai giữ restricted evidence? | Không được dùng audio thật cho buổi tập huấn. |

## 7. Trạng thái hiện tại

- Buổi dry run: `NOT_RUN`.
- Calibration 10 mẫu: `NOT_RUN`.
- Hai rater đã xác nhận: `NOT_VERIFIED`.
- Agreement/reliability result: `NOT_EVALUATED`.
- Task readiness: `PENDING` các quyết định và evidence ở trên.

