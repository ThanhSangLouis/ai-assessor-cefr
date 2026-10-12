# M09 — Trust Layer — Requirement

**SCOPE ID:** M09
**SCOPE TYPE:** module
**SCOPE ROOT:** `docs/sdd/modules/m09-trust-layer/`
**OWNER:** Sang
**LIFECYCLE:** proposed
**RELATED SCOPES:** M03 ASR, M04 Features, M05 Scoring, M06 Diagnostic Report, M07 Teacher Review, M16 Monolith Runtime
**RESEARCH MODE:** `RUN` đề xuất — cần đối chiếu hành vi ở baseline Sang `40907cc`, artifact hiệu chuẩn và contract đang có trong repo dự án.
**VERSION:** v0.1 · 12/10/2026
**STATUS:** DRAFT · `USER VERDICT: PENDING`

## Mục tiêu

Bổ sung lớp kiểm soát độ tin cậy cho pipeline đánh giá để bài không đủ căn cứ không bị trình bày như kết quả chắc chắn; mọi quyết định từ chối hoặc chuyển giảng viên phải có reason code, evidence và provenance có thể kiểm tra.

## User Stories

- M09-US-001: Là sinh viên, tôi muốn biết vì sao bài cần giảng viên xem lại và tôi cần làm gì tiếp theo.
- M09-US-002: Là giảng viên, tôi muốn thấy evidence của LID, lạc đề, đọc lại đề và uncertainty để duyệt đúng trọng tâm.
- M09-US-003: Là quản trị viên/người nghiên cứu, tôi muốn tái tạo calibration và refusal benchmark từ manifest, seed và artifact hash.

## Functional Requirements

- **M09-FR-001 — Language identification:** xác định tiếng Anh/không phải tiếng Anh/không chắc chắn; lưu `method`, `version`, `confidence`, `reason_code`; không chắc chắn chuyển review, không tự trừ điểm.
- **M09-FR-002 — Validity shields:** phát hiện dấu hiệu lạc đề và đọc lại đề bằng evidence span có thể giải thích; chỉ thêm review reason.
- **M09-FR-003 — Conformal set:** dùng artifact CV+ có checksum, `alpha=0.10` mặc định; set nhiều band sinh `SCORE_NEAR_BOUNDARY`; artifact thiếu/sai hash trả `NOT_EVALUATED` hoặc readiness failure theo context.
- **M09-FR-004 — Criterion indicators:** Range, Accuracy, Fluency, Coherence, Phonology là chỉ báo có coverage/evidence, không phải năm điểm độc lập; `Interaction=null/insufficient_evidence` cho độc thoại.
- **M09-FR-005 — Provenance và compatibility:** report lưu model/feature/guard/calibration version và checksum; report cũ vẫn đọc được bằng default an toàn.
- **M09-FR-006 — Reproducible tools:** calibration và refusal benchmark nhận config, seed, input manifest; không dùng confirmation set để tune; output có hash và số mẫu.
- **M09-FR-007 — Long-response policy:** giữ policy cửa sổ hiện hành; chỉ aggregate khi mọi cửa sổ hợp lệ và luôn chuyển giảng viên.

## Acceptance Criteria

- **M09-AC-001:** non-English rõ ràng bị từ chối hoặc chuyển review theo policy; confidence sát ngưỡng không tạo điểm chắc chắn.
- **M09-AC-002:** off-topic/prompt-reading chỉ tạo reason/evidence; cùng feature đầu vào, bật/tắt guard không đổi điểm số trực tiếp.
- **M09-AC-003:** conformal artifact đúng hash tạo set deterministic; hash sai/thiếu không fallback sang set giả; set từ hai band trở lên có `SCORE_NEAR_BOUNDARY`.
- **M09-AC-004:** payload/UI không có `criterion_score`; chỉ có indicator, coverage, evidence và disclosure đúng nghĩa.
- **M09-AC-005:** report được tạo trước M09 vẫn render; field mới thiếu được hiểu là `not_available`, không suy diễn.
- **M09-AC-006:** benchmark chạy lại cùng manifest/seed/config cho cùng hash và summary; output ghi revision/artifact provenance.
- **M09-AC-007:** retry cùng `job_id/idempotency_key` không tạo report, reason hay audit trùng.

## In scope

LID, validity shields, conformal prediction set, criterion indicators, report provenance, calibration/refusal tools, reason-to-UI contract và regression cho pipeline/report cũ.

## Out of scope

Thay rubric/band threshold đã khóa; fine-tune foundation model; tuyên bố độ chính xác CEFR; tự động phạt điểm do lạc đề/đọc đề; D043 microservice.

## Ràng buộc và câu hỏi cần duyệt

- Model/artifact nằm ngoài Git, chỉ manifest/checksum/config được commit.
- Không log transcript, audio, actor ID hoặc path artifact.
- Cần user xác nhận `RESEARCH MODE: RUN`, `alpha=0.10` và policy `confidence thấp → REVIEW_REQUIRED` tại Phase 01.
