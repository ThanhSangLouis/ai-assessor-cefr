# M12 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT. Code đã merge theo chỉ dẫn trực tiếp của user (xem [07-status](07-status.md)); cột Status ghi trạng thái code trên `main`, không phải verdict.

Chú giải: `CODE_MERGED` = code + test đã có trên `main`, review/acceptance PENDING. `PARTIAL` = mới có một phần deliverable. `PENDING_OWNER` = phần của owner khác, chờ owner xác nhận.

| Task | W5 | Deliverable | Tests | Status (đồng bộ 21/10/2026) |
| --- | --- | --- | --- | --- |
| M12-TASK-001 | W5-T01 | schema/repository/constraints/migration | 001/002/005/010 | PENDING_OWNER — `007_research.sql` (PR #36; Thắng xác nhận) |
| M12-TASK-002 | W5-S04 | assignment/adjudication/agreement logic | 001/006–008 | CODE_MERGED — PR #43 (`829849b`): `research/assign.py`, `research/agreement.py`; test `tests/test_assign_unit.py`, `tests/test_agreement.py` |
| M12-TASK-003 | W5-S04 | blind policy/API/report CLI | 002–008 | PARTIAL — PR #43: blind guard ở `api/review.py`, API `api/research.py` (test `tests/portal/test_research_api.py`); **report CLI chưa có** |
| M12-TASK-004 | W5-N03 | rater list/sheet/conflict/recovery UI | 003/005/009 | PENDING_OWNER — PR #46 (Nguyên xác nhận) |
| M12-TASK-005 | W5-N04 | batch/adjudication/report/export UI | 002/006–009 | PENDING_OWNER — PR #47 (Nguyên xác nhận) |
| M12-TASK-006 | W5-T04 | security/full regression/evidence | all | PENDING — SCRUM-68 (W5-T04) đang In Review |

Task Done requires browser Network/DOM leakage checklist in addition to functional screenshots.

Bằng chứng chạy lại test trên `main` `cabcc44`: [evidence/w6-s02-sync.md](evidence/w6-s02-sync.md).
