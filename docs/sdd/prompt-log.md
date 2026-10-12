# Prompt Log — chỉ mục

Prompt và evidence chính thức thuộc scope root của từng module/feature. File này chỉ dẫn đường, không thay log/Status local. Trạng thái phát hành đọc từ log của từng scope; W3 dùng subagents Luna theo chỉ dẫn trực tiếp của Thắng.

| Module | Prompt Log | Evidence Manifest | Status |
| --- | --- | --- | --- |
| M01 | [prompts/M01](modules/m01-intake-student/prompts/prompt-log.md) | [evidence/M01](modules/m01-intake-student/evidence/evidence-manifest.md) | [status/M01](modules/m01-intake-student/07-status.md) |
| M02 | [prompts/M02](modules/m02-audio-qc/prompts/prompt-log.md) | [evidence/M02](modules/m02-audio-qc/evidence/evidence-manifest.md) | [status/M02](modules/m02-audio-qc/07-status.md) |
| M03 | [prompts/M03](modules/m03-asr/prompts/prompt-log.md) | [evidence/M03](modules/m03-asr/evidence/evidence-manifest.md) | [status/M03](modules/m03-asr/07-status.md) |
| M04 | [prompts/M04](modules/m04-features/prompts/prompt-log.md) | [evidence/M04](modules/m04-features/evidence/evidence-manifest.md) | [status/M04](modules/m04-features/07-status.md) |
| M05 | [prompts/M05](modules/m05-scoring/prompts/prompt-log.md) | [evidence/M05](modules/m05-scoring/evidence/evidence-manifest.md) | [status/M05](modules/m05-scoring/07-status.md) |
| M06 | [prompts/M06](modules/m06-diagnostic-report/prompts/prompt-log.md) | [evidence/M06](modules/m06-diagnostic-report/evidence/evidence-manifest.md) | [status/M06](modules/m06-diagnostic-report/07-status.md) |
| M07 | [prompts/M07](modules/m07-teacher-review/prompts/prompt-log.md) | [evidence/M07](modules/m07-teacher-review/evidence/evidence-manifest.md) | [status/M07](modules/m07-teacher-review/07-status.md) |
| M08 | [prompts/M08](modules/m08-identity-storage-admin/prompts/prompt-log.md) | [evidence/M08](modules/m08-identity-storage-admin/evidence/evidence-manifest.md) | [status/M08](modules/m08-identity-storage-admin/07-status.md) |
| M09 | NONE ISSUED | chưa tạo | [status/M09](modules/m09-trust-layer/07-status.md) |
| M10 | NONE ISSUED | chưa tạo | [status/M10](modules/m10-learning-experience/07-status.md) |
| M11 | NONE ISSUED | chưa tạo | [status/M11](modules/m11-identity-account/07-status.md) |
| M12 | NONE ISSUED | chưa tạo | [status/M12](modules/m12-blind-evaluation/07-status.md) |
| M13 | NONE ISSUED | chưa tạo | [status/M13](modules/m13-learning-evidence/07-status.md) |
| M14 | NONE ISSUED | chưa tạo | [status/M14](modules/m14-billing-licensing/07-status.md) |
| M15 | NONE ISSUED | chưa tạo | [status/M15](modules/m15-product-web/07-status.md) |
| M16 | NONE ISSUED | chưa tạo | [status/M16](modules/m16-monolith-runtime/07-status.md) |
| W3 integration | [prompts/W3](features/w3-local-integration/prompts/prompt-log.md) | [evidence/W3](features/w3-local-integration/evidence/evidence-manifest.md) | [status/W3](features/w3-local-integration/07-status.md) |

Quy trình: Phase 05 APPROVED → lưu prompt file và log trong module → xác minh fingerprint → bàn giao Antigravity → lưu raw report và evidence trong module → Codex review actual diff → cập nhật Status. Bản chat đơn thuần không tự tạo file prompt hoặc evidence.

Ngoại lệ W3 02/10/2026: Thắng trực tiếp authorize triển khai/ủy nhiệm ba Luna, Codex review và branch local. Formal verdict chưa có không được ghi APPROVED. Prompt gốc, amendments và corrections đã lưu file/Excel trước dispatch; workbook sheet Thắng là log AI chính của lượt này.
