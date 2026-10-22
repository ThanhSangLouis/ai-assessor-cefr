# M10 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT. Code đã merge theo chỉ dẫn trực tiếp của user (xem [07-status](07-status.md)); cột Status ghi trạng thái code trên `main`, không phải verdict.

Chú giải: `CODE_MERGED` = code + test đã có trên `main`, review/acceptance PENDING. `PENDING_OWNER` = phần của owner khác, chờ owner xác nhận.

| Task ID | W5 task | Deliverable | Tests | Depends on | Status (đồng bộ 21/10/2026) |
| --- | --- | --- | --- | --- | --- |
| M10-TASK-001 | W5-T01 | migrations/repositories/seed transaction | 001/004/006/011 | M16 schema runner | PENDING_OWNER — migrations `006_learning.sql`, `011_learning_runtime.sql` (PR #36, #41; Thắng xác nhận phần runner) |
| M10-TASK-002 | W5-S02 | mission catalogue/rules/recommendation/no-score pipeline | 001–003/005 | TASK-001 interfaces | CODE_MERGED — PR #41 (`bf12f27`): `practice/`; test `tests/practice/`, `tests/api/test_learning_*.py` |
| M10-TASK-003 | W5-S02 | lesson domain/authoring/version/lint/import-export | 004–006/010 | TASK-001 | CODE_MERGED — PR #41: `lessons/authoring.py`, `lessons/service.py`; test `tests/lessons/` |
| M10-TASK-004 | W5-S02 | review schedule/teacher override | 007/010 | TASK-003 | CODE_MERGED — PR #41: lịch ôn + override trong `lessons/service.py`, `practice/service.py` |
| M10-TASK-005 | W5-S03 | achievement/streak/seen/export hooks | 008/011 | TASK-001/002 | CODE_MERGED — PR #42 (`52e0bc9`, `db172d2`): `practice/achievements.py`, `streak.py`, `progress.py`, `mark_seen`; test `tests/test_achievements_unit.py`, `tests/portal/test_learning_features.py` |
| M10-TASK-006 | W5-N02 | student roadmap/player/review/result/progress UI | 009 + DOM no-band | TASK-002–005 API freeze | PENDING_OWNER — PR #45 (Nguyên xác nhận) |
| M10-TASK-007 | W5-N03 | teacher authoring/insight/override UI | 004/009/010 | TASK-003/004 API freeze | PENDING_OWNER — PR #46 (Nguyên xác nhận) |
| M10-TASK-008 | W5-T04 | integrated regression/wheel/evidence | full module | TASK-001–007 | PENDING — SCRUM-68 (W5-T04) đang In Review |

Không task nào `DONE` nếu mới có màn hình không có persistence thật, hoặc domain pass unit test nhưng chưa chứng minh practice không lọt assessment/research paths.

Bằng chứng chạy lại test trên `main` `cabcc44`: [evidence/w6-s02-sync.md](evidence/w6-s02-sync.md).
