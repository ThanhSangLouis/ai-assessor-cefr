# SCRUM-84 — M16 sync với code đã merge

**Scope:** M16 · **Task:** SCRUM-84 / W6-T03 · **Ngày rà:** 25/10/2026
**Baseline:** `main` / task branch `f540cb88643214cd1d4444f2dd0d81f4463119fa`
**Result:** TASK-001–004 có mapping code/evidence; final gate TASK-005/006 còn `BLOCKED`.

## Code merge và evidence

| M16 task | Code/revision đã merge | Evidence được dẫn | Trạng thái sau đồng bộ |
| --- | --- | --- | --- |
| TASK-001–003 | SCRUM-65, PR #35 merge `9968abc`; reviewed code `61a5353` | [SCRUM-65 review](scrum-65/review.md), [integration report](scrum-65/integration-report.md), G0/G2 evidence | `IN_REVIEW`; technical checks PASS, Sang/G1 verdict PENDING |
| TASK-004 | Data operations trong SCRUM-67, PR #38 merge `d60e8a4` | [SCRUM-67 verification](../../m14-billing-licensing/evidence/scrum-67/verification.md), gồm M16-TEST-006/007 và roundtrip với fixture tổng hợp | `IN_REVIEW`; review liên module và tích hợp cuối còn chờ |
| TASK-005 | Tích hợp route/package/CI/docs cho W5-T04 | Baseline chưa có evidence W5-T04 tích hợp cuối | `BLOCKED` |
| TASK-006 | Smoke/browser/evidence cuối cho W5-T04 + N04 | M15 report chạy trên revision `0827b37`, không phải package W5-T04 cuối | `BLOCKED` |

## Current-base delta

PR #50 (`bfd1206`) updates consent/storage migration and data-operation compatibility after SCRUM-65/67. PR #51 (`7b56013`) and #52 (`f540cb8`) add W6 protocol and rater-training materials but do not run the integrated W5-T04 gate. Historical SCRUM-65/67 test numbers remain attached to their recorded revisions; SCRUM-84 did not relabel them as current-head results.

## Historical checks và giới hạn

- Code được review trong SCRUM-65 tại `61a5353`: 358 passed, 0 failed/skipped, 2 smoke deselected; lint/format file thay đổi, clean wheel/CLI/HTTP, 11 browser checks và migration/restore v4→v9 có evidence PASS trên revision task-local.
- Review SCRUM-65 ghi 23 file legacy chưa đạt global format; ASR/VAD inference và Windows native `NOT_RUN`; verdict Sang/G1 `PENDING`.
- SCRUM-67 có verification data operations và roundtrip với fixture tổng hợp; không đóng gate tích hợp cuối của M16 TASK-005/006.
- Không chạy test lại tại SCRUM-84; đây là đồng bộ traceability từ commit/evidence đã có.
- Requirement và Artifacts 02–06 toàn M16 vẫn `DRAFT/PENDING`; không tuyên bố module đã được nghiệm thu hoặc Jira `DONE`.
