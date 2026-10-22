# M13 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT. Code đã merge theo chỉ dẫn trực tiếp của user (xem [07-status](07-status.md)); cột Status ghi trạng thái code trên `main`, không phải verdict.

Chú giải: `CODE_MERGED` = code + test đã có trên `main`, review/acceptance PENDING. `PARTIAL` = mới có một phần hoặc test còn mỏng. `PENDING_OWNER` = phần của owner khác, chờ owner xác nhận.

| Task | W5 | Deliverable | Tests | Status (đồng bộ 21/10/2026) |
| --- | --- | --- | --- | --- |
| M13-TASK-001 | W5-T01 | study/session/SEM schema + repositories | 003/005/008/009/012 | PENDING_OWNER — `007_research.sql` (PR #36; Thắng xác nhận) |
| M13-TASK-002 | W5-S03 | vi-pron-v1 + profile/cohort | 001/002 | CODE_MERGED — PR #42 (`52e0bc9`): `pronunciation/vietnamese.py`, cohort ở `practice/service.py`; test `tests/test_pronunciation_unit.py` |
| M13-TASK-003 | W5-S04 | study assignment/gate/survey/analysis/export | 003–007/012 | CODE_MERGED — PR #43 (`829849b`): `research/study.py`, `research/service.py`; test `tests/portal/test_research_api.py` |
| M13-TASK-004 | W5-S04 | teacher-time/Wilson/reliable change/SEM | 008–010 | PARTIAL — PR #43: `research/teacher_time.py`, `research/reliable_change.py`; coverage `reliable_change.py` mới 25% (cần thêm unit test) |
| M13-TASK-005 | W5-N01/N02 | student progress/pronunciation/study UI | 004/011 | PENDING_OWNER — PR #44/#45 (Nguyên xác nhận) |
| M13-TASK-006 | W5-N03 | cohort pronunciation/KPI UI | 002/008/011 | PENDING_OWNER — PR #46 (Nguyên xác nhận) |
| M13-TASK-007 | W5-N04 | study/SEM admin UI | 003/005–011 | PENDING_OWNER — PR #47 (Nguyên xác nhận) |
| M13-TASK-008 | W5-T04 | privacy/full regression/evidence | all | PENDING — SCRUM-68 (W5-T04) đang In Review |

Bằng chứng chạy lại test trên `main` `cabcc44`: [evidence/w6-s02-sync.md](evidence/w6-s02-sync.md).
