# SCRUM-84 — M14 sync với code đã merge

**Scope:** M14 · **Task:** SCRUM-84 / W6-T03 · **Ngày rà:** 25/10/2026
**Baseline:** `main` / task branch `f540cb88643214cd1d4444f2dd0d81f4463119fa`
**Result:** backend merge/evidence được nối với task; M14 acceptance vẫn `PENDING`.

## Code merge và evidence

| M14 task | Code/revision đã merge | Evidence được dẫn | Trạng thái sau đồng bộ |
| --- | --- | --- | --- |
| TASK-001–004 backend | SCRUM-67, PR #38 merge `d60e8a4`; final reviewed code `5c6397f` | [Verification](scrum-67/verification.md), [review record](scrum-67/review-record.md), API/data/control evidence trong `scrum-67/` | `IN_REVIEW`; historical verification recommends `READY_FOR_REVIEW`; user/Sang/Nguyên verdict PENDING |
| TASK-005 billing UI | Read surfaces được consumer PR #47 `cabcc44` | [M15 integration report](../../m15-product-web/evidence/scrum-74-76/integration-report.md), [SCRUM-67 UI handoff](scrum-67/ui-handoff.md) | `BLOCKED`; billing mutations/receipt journey chưa được chứng minh |
| TASK-006 full security/regression/evidence | Không có final integrated W5-T04 record trên baseline này | [M16 W5 task matrix](../../m16-monolith-runtime/06-tasks.md) | `BLOCKED` tới final integration gate |

## Current-base delta

PR #50 (`bfd1206`) thay billing-key ACL handling và một số data-operation/privacy compatibility paths khi tích hợp consent-v2. SCRUM-67's `600 passed` remains tied to reviewed code `5c6397f`, not to current `f540cb8`. TASK-001–004 therefore remain `IN_REVIEW`; SCRUM-84 did not rerun an M14-specific suite. PR #47 remains read-only billing UI evidence only; live merchant/payment still `NOT_RUN`.

## Historical checks và giới hạn

- SCRUM-67 ghi 600 passed, 0 failed, 0 skipped, 2 smoke deselected; coverage, clean wheel, browser integration/API, migration và populated synthetic-fixture roundtrip được ghi tại verification package.
- Global format có 22 legacy files ngoài diff chưa đạt; changed-file format PASS. Windows native, model inference, live merchant gateway/payment `NOT_RUN`.
- Report PR #47 chỉ chứng minh các màn hình xem billing overview/order; không suy ra TASK-005 hoàn tất.
- Không chạy test lại tại SCRUM-84; đây là đồng bộ traceability từ commit/evidence đã có.
- Requirement và global artifacts 02–06 vẫn `DRAFT/PENDING`; không ghi user/Sang/Nguyên acceptance hoặc Jira `DONE`.
