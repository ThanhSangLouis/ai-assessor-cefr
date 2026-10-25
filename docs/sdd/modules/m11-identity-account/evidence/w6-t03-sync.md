# SCRUM-84 — M11 sync với code đã merge

**Scope:** M11 · **Task:** SCRUM-84 / W6-T03 · **Ngày rà:** 25/10/2026
**Baseline:** `main` / task branch `f540cb88643214cd1d4444f2dd0d81f4463119fa`
**Result:** task/evidence mapping đã cập nhật; module approval và owner acceptance vẫn `PENDING`.

## Code merge và evidence

| M11 task | Code/revision đã merge | Evidence được dẫn | Trạng thái sau đồng bộ |
| --- | --- | --- | --- |
| TASK-001–005 backend | PR #36 `840efb9` và PR #37 `febf7f9`; SCRUM-66 product revision `311b029` | [SCRUM-66 review](scrum-66/review.md), test/coverage/wheel/API evidence trong `scrum-66/` | `IN_REVIEW`; review/owner verdict không được thay bằng trạng thái merge |
| TASK-006 account/public auth UI | Consumer code trong PR #44 `0fc428a` | [M15 integration report](../../m15-product-web/evidence/scrum-74-76/integration-report.md), [UI handoff](scrum-66/ui-handoff.md) | `IN_REVIEW`; owner review và UI AC còn PENDING |
| TASK-007 admin account/config UI | Consumer surfaces trong PR #47 `cabcc44` | [M15 integration report](../../m15-product-web/evidence/scrum-74-76/integration-report.md), [UI handoff](scrum-66/ui-handoff.md) | `IN_REVIEW`; role/action coverage và owner review còn PENDING |
| TASK-008 full regression/evidence | Không có final integrated SCRUM-84/W5-T04 record trên baseline này | [M16 W5 task matrix](../../m16-monolith-runtime/06-tasks.md) | `BLOCKED` tới final integration gate |

## Thay đổi tích hợp sau baseline 82fe708

- PR #50 / SCRUM-87 merge `bfd1206` thêm consent `consent-v2`, `audio_storage_allowed` tách khỏi research opt-in và migration `012`; cập nhật evidence cho TASK-005. Jira SCRUM-87 vẫn `Testing`; đây không phải approval M11.
- PR #51 / SCRUM-88 merge `7b56013` cập nhật prompt/rubric và màn hình đề/chấm; không đóng M11 auth acceptance.
- PR #52 / SCRUM-89 merge `f540cb8` chủ yếu bổ sung nguồn/tài liệu tập huấn; không chứng minh đã chạy hiệu chuẩn hai giám khảo.
- PR #50 cũng sửa shared storage/privacy/billing-key paths; đây là thay đổi sau evidence lịch sử SCRUM-66/67, không làm task cũ tự chuyển sang `DONE`.

## Historical checks và giới hạn

- SCRUM-66 record: 425 passed, 0 failed, 0 skipped, 2 smoke deselected; Ruff, changed-file format, Markdown/forbidden-file checks, clean wheel và backend browser checks PASS ở task-local revision. Global formatter vẫn có 22 legacy files ngoài diff; live OAuth/provider credentials `NOT_RUN`.
- PR #44/#47 merge evidence chứng minh source đã có trong `main`, không chứng minh mọi M11 UI Acceptance Criteria đã được kiểm chứng. M15 browser report chỉ cover supported routes/roles trên revision `0827b37`.
- Không chạy test lại tại SCRUM-84; đây là đồng bộ traceability từ commit/evidence đã có.
- Requirement, Research decision và artifacts 02–06 của M11 vẫn `DRAFT/PENDING`. Không ghi `APPROVED`, `DONE`, owner acceptance hoặc Jira status thay người có thẩm quyền.
