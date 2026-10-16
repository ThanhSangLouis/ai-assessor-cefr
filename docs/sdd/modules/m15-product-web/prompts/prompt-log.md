# M15 — Prompt Log

| Prompt ID | Task | Base revision | State | File |
| --- | --- | --- | --- | --- |
| `M15-W5-N01-001A-A1` | `M15-TASK-001A` / W5-N01.1 một phần | `61455024f1544a92e4313030067f72c29cf80d49` | RETURNED — Phase 07 A1 `CHANGES_REQUIRED`; head `6baf720f173b440eb961676b09ea290058a39b35` | [Prompt](M15-W5-N01-001A-A1.md) |
| `M15-W5-N01-001A-A2` | `M15-TASK-001A` / correction F01–F05 | `6baf720f173b440eb961676b09ea290058a39b35` | `SUPERSEDED_BEFORE_EXECUTION` — baseline/Phase 05 scope đổi; không gửi Antigravity | [Prompt](M15-W5-N01-001A-A2.md) |
| `M15-W5-N01-001A-A2R1` | `M15-TASK-001A` / bundled correction F01–F06 | `6baf720f173b440eb961676b09ea290058a39b35` | `RETURNED_FOR_REWORK` — Phase 07 Codex `CHANGES_REQUIRED`; xem [review A2R1](../reviews/phase-07-review-a2-2026-10-15.md) | [Prompt](M15-W5-N01-001A-A2R1.md) |
| `M15-W5-N01-001A-A2R2` | `M15-TASK-001A` / bundled correction R01–R04 | `6baf720f173b440eb961676b09ea290058a39b35` | `RETURNED_FOR_REWORK` — Codex Phase 07 `CHANGES_REQUIRED`, R01–R03 còn mở. Correction bundle đã dùng; R02 traceability tái diễn. Chờ chủ dự án quyết định hướng tiếp theo; chưa có prompt mới | [Prompt](M15-W5-N01-001A-A2R2.md) |

WORKSPACE FINGERPRINT: 1ae115f3a33d0d76baa28de634654eec31311d60ebaeb8392748478011e56b37
FINGERPRINT ALGORITHM: `sdd-workspace-v2`
FINGERPRINT METADATA FILES: `docs/sdd/modules/m15-product-web/07-status.md`; `docs/sdd/modules/m15-product-web/prompts/M15-W5-N01-001A-A2R2.md`; `docs/sdd/modules/m15-product-web/prompts/prompt-log.md`
FINGERPRINT EXCLUSIONS: `EDUZ/**`; `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r2/**` (A2R2 preflight options)

Log A1 đã lưu trước handoff. A2 cũ chưa thực thi và bị supersede; A2R1 là bản reissue cho cùng attempt A2 sau khi Phase 05 v0.2a được user duyệt. Chủ dự án báo A2R2 đã được Antigravity hoàn tất và chuyển Codex review; Review A2R2 `CHANGES_REQUIRED`, R01–R03 còn mở (xem `../reviews/phase-07-review-a2r2-2026-10-15.md`). A2R2 là bundled correction hiện tại; correction budget mặc định đã dùng và R02 traceability tiếp tục tái diễn, nên chưa phát correction prompt tiếp theo, chờ chủ dự án quyết định đánh giá lại task/Plan. Kiểm tra runner ngày 15/10/2026 chỉ liệt kê Gemini 3.8 Flash (High), trong khi skill Antigravity đang áp dụng bắt buộc Gemini 3.6 Flash (High) và cấm fallback; không chạy implementer. Fingerprint A2R2 vẫn là dữ liệu mâu thuẫn đã ghi trong Review Record, không sửa hồi tố. 001B/002–006 chưa có prompt. Antigravity là implementer; subagent Codex chỉ Research/review đọc-only.
