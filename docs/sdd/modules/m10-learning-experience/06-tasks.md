# M10 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT.

| Task ID | W5 task | Deliverable | Tests | Depends on | Status |
| --- | --- | --- | --- | --- | --- |
| M10-TASK-001 | W5-T01 | migrations/repositories/seed transaction | 001/004/006/011 | M16 schema runner | BLOCKED |
| M10-TASK-002 | W5-S02 | mission catalogue/rules/recommendation/no-score pipeline | 001–003/005 | TASK-001 interfaces | BLOCKED |
| M10-TASK-003 | W5-S02 | lesson domain/authoring/version/lint/import-export | 004–006/010 | TASK-001 | BLOCKED |
| M10-TASK-004 | W5-S02 | review schedule/teacher override | 007/010 | TASK-003 | BLOCKED |
| M10-TASK-005 | W5-S03 | achievement/streak/seen/export hooks | 008/011 | TASK-001/002 | BLOCKED |
| M10-TASK-006 | W5-N02 | student roadmap/player/review/result/progress UI | 009 + DOM no-band | TASK-002–005 API freeze | BLOCKED |
| M10-TASK-007 | W5-N03 | teacher authoring/insight/override UI | 004/009/010 | TASK-003/004 API freeze | BLOCKED |
| M10-TASK-008 | W5-T04 | integrated regression/wheel/evidence | full module | TASK-001–007 | BLOCKED |

Không task nào `DONE` nếu mới có màn hình không có persistence thật, hoặc domain pass unit test nhưng chưa chứng minh practice không lọt assessment/research paths.
