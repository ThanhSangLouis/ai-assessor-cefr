# M15 — Prompt Log

| Prompt ID | Task | Base revision | State | File |
| --- | --- | --- | --- | --- |
| `M15-W5-N01-001A-A1` | `M15-TASK-001A` / W5-N01.1 một phần | `61455024f1544a92e4313030067f72c29cf80d49` | RETURNED — Phase 07 A1 `CHANGES_REQUIRED`; head `6baf720f173b440eb961676b09ea290058a39b35` | [Prompt](M15-W5-N01-001A-A1.md) |
| `M15-W5-N01-001A-A2` | `M15-TASK-001A` / correction F01–F05 | `6baf720f173b440eb961676b09ea290058a39b35` | `SUPERSEDED_BEFORE_EXECUTION` — baseline/Phase 05 scope đổi; không gửi Antigravity | [Prompt](M15-W5-N01-001A-A2.md) |
| `M15-W5-N01-001A-A2R1` | `M15-TASK-001A` / bundled correction F01–F06 | `6baf720f173b440eb961676b09ea290058a39b35` | `RETURNED_FOR_REWORK` — Phase 07 Codex `CHANGES_REQUIRED`; xem [review A2R1](../reviews/phase-07-review-a2-2026-10-15.md) | [Prompt](M15-W5-N01-001A-A2R1.md) |
| `M15-W5-N01-001A-A2R2` | `M15-TASK-001A` / R01 evidence còn thiếu, R02–R04 | `6baf720f173b440eb961676b09ea290058a39b35` | `RETURNED_FOR_REWORK` — chủ dự án báo Antigravity đã hoàn thành; Codex Phase 07 `CHANGES_REQUIRED`, R01–R03 còn mở. Fingerprint provenance đang mâu thuẫn; xem Review A2R2 | [Prompt](M15-W5-N01-001A-A2R2.md) |

WORKSPACE FINGERPRINT: 1ae115f3a33d0d76baa28de634654eec31311d60ebaeb8392748478011e56b37
FINGERPRINT ALGORITHM: `sdd-workspace-v2`
FINGERPRINT METADATA FILES: `docs/sdd/modules/m15-product-web/07-status.md`; `docs/sdd/modules/m15-product-web/prompts/M15-W5-N01-001A-A2R2.md`; `docs/sdd/modules/m15-product-web/prompts/prompt-log.md`
FINGERPRINT EXCLUSIONS: `EDUZ/**`; `docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r2/**` (A2R2 preflight options)

Log A1 đã lưu trước handoff. A2 cũ chưa thực thi và bị supersede; A2R1 là bản reissue cho cùng attempt A2 sau khi Phase 05 v0.2a được user duyệt. A2R2 ban đầu ở trạng thái `BLOCKED_MODEL_UNAVAILABLE`; sau đó chủ dự án trực tiếp báo Antigravity đã hoàn tất và gửi handoff cho Codex review. Review A2R2 hiện `CHANGES_REQUIRED`; xem `../reviews/phase-07-review-a2r2-2026-10-15.md`. Fingerprint khởi đầu trong prompt là `1ae115f3…`, khác starting value trong report (`3a4bd112…`); final value trong report/log (`6687a1a1…`) cũng không khớp lần Codex tính lại workspace theo đúng options (`1ae115f3…`). Không ghi trạng thái model-blocked cũ như trạng thái hiện hành; đó là lịch sử trước handoff. 001B/002–006 chưa có prompt. Antigravity là implementer; subagent Codex chỉ Research/review đọc-only.
