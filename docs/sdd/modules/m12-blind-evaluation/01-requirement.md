# M12 — Blind Rating and Agreement — Requirement

**SCOPE ID:** M12 · **TYPE:** module · **OWNER:** Sang
**ROOT:** `docs/sdd/modules/m12-blind-evaluation/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M05–M08, M11, M13, M15, M16
**RESEARCH MODE:** `RUN` đề xuất — privacy/blinding/statistical contract và D030 cần đối chiếu.
**USER VERDICT:** PENDING

## Requirements

- **M12-FR-001:** admin tạo batch từ assessment có audio, trạng thái phù hợp và active research consent; seed lưu; đúng hai rater khác nhau/response, thứ tự riêng.
- **M12-FR-002:** rater blind không thấy identity, response ID public, machine output, reviewer khác hoặc metadata suy danh tính qua mọi route.
- **M12-FR-003:** ai đã xem machine result không được giao/tiếp tục blind assignment của response đó; void sheet được giao lại an toàn.
- **M12-FR-004:** sheet gồm năm tiêu chí + overall 0–6 bước 0.5 + band + rationale, hoặc unrateable reason; submit một lần.
- **M12-FR-005:** adjudication khi lệch overall ≥1.0, lệch band hoặc một bên unrateable; adjudicator không phải rater cũ và vẫn blind.
- **M12-FR-006:** report human-human trước machine-human, reference = mean hai rater hoặc median ba khi adjudicated; bootstrap theo speaker.
- **M12-FR-007:** CSV dùng pseudonym nghiên cứu, re-check consent khi report/export; erasure xóa rating link cá nhân theo policy.
- **M12-FR-008:** CLI/tool tái tạo report từ batch/seed/config và kết quả UI/API thống nhất.

## Acceptance Criteria

- **M12-AC-001:** assignment deterministic, balanced và không collision; <2 rater hoặc không có eligible response trả 422.
- **M12-AC-002:** blind leakage test trên queue/report/history/admin/export/direct URL đều không lộ forbidden fields.
- **M12-AC-003:** seen-machine assignment bị loại/void; replacement không trùng rater cũ và giữ audit.
- **M12-AC-004:** sheet validation và one-time submit chống replay/concurrent submit.
- **M12-AC-005:** adjudication đúng boundary và conflict; batch closed không nhận submission mới.
- **M12-AC-006:** report ghi n/sample/CI/seed; insufficient sample không bịa metric; withdrawn participant biến mất khỏi analysis/export.
- **M12-AC-007:** teacher/admin browser journeys có conflict/error/recovery, keyboard và mobile state.

## Out of scope

Thay rubric chính thức, tuyển rater ngoài hệ thống, email notification, payment rater, claim machine accuracy từ fixture.
