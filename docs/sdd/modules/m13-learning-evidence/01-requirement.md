# M13 — Learning Evidence and Study Metrics — Requirement

**SCOPE ID:** M13 · **TYPE:** module · **OWNER:** Sang
**ROOT:** `docs/sdd/modules/m13-learning-evidence/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M05–M08, M10–M12, M15, M16
**RESEARCH MODE:** `RUN` đề xuất — D039–D042 có quyết định thống kê/privacy cần đối chiếu.
**USER VERDICT:** PENDING

## Requirements

- **M13-FR-001:** `vi-pron-v1` phân loại năm pattern từ word evidence của lesson; teacher-corrected-as-heard và unmeasured step không tính lỗi.
- **M13-FR-002:** student profile có error/opportunity, tỷ lệ chỉ khi exposure ≥8, tối đa 5 ví dụ; cohort chỉ aggregate, không identity/link.
- **M13-FR-003:** feedback study một active study, consenting active students, balanced seeded assignment, tối thiểu 4; withholding server-side chỉ trên own assessment report.
- **M13-FR-004:** participant withdraw bất cứ lúc nào; consent withdrawal/erasure/phase close khôi phục feedback và loại khỏi analysis.
- **M13-FR-005:** survey năm Likert 1–5; analysis pre/post theo `min_days`, bootstrap 95% CI 2000 lần trong từng arm, Hedges g; insufficient state rõ.
- **M13-FR-006:** teacher-time từ review session; bỏ >30 phút; median chỉ khi n≥5; auto-complete/kept-band có Wilson 95% CI.
- **M13-FR-007:** reliable change dùng tối đa ba bài đầu/cuối và SEM; retest pair ≤48 giờ, mỗi bài một pair, n≥10; manual SEM phải có source; cấm RMSE thay SEM.
- **M13-FR-008:** export dùng P001…, không alias/account ID; metric/report luôn ghi n, source, seed/config/version.

## Acceptance Criteria

- **M13-AC-001:** năm pronunciation pattern đúng priority; no-match im lặng; boundary exposure 7/8 và cap 5 đúng.
- **M13-AC-002:** cohort payload không thể truy ngược cá nhân, student không đọc cohort, foreign example không mở được.
- **M13-AC-003:** study assignment reproducible/balanced; withholding không thể bypass bằng API/HTML; teacher/admin không bị withholding.
- **M13-AC-004:** withdraw/consent/erasure/close có hiệu lực ngay và deterministic.
- **M13-AC-005:** survey/analysis/CSV đúng validation, sample, CI/effect-size và privacy; n nhỏ trả null + reason.
- **M13-AC-006:** review session start/end/release/timeout và KPI median/Wilson đúng; n<5 không nêu median/time saved.
- **M13-AC-007:** reliable-change states `insufficient_assessments`, `sem_unavailable`, `improved`, `declined`, `within_measurement_error` đúng công thức/source.
- **M13-AC-008:** UI không gọi pronunciation là điểm hoặc fixture là hiệu quả thật; exploratory disclaimer luôn hiện.

## Out of scope

Khẳng định causal effect/accuracy từ fixture; tự chọn SEM không nguồn; individualized clinical/speech diagnosis; public cohort dashboard.
