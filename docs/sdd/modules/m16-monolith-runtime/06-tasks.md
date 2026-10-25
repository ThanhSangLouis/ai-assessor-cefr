# M16 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT.

| Task | W5 | Deliverable | Tests | Status |
| --- | --- | --- | --- | --- |
| M16-TASK-001 | W5-T01 | baseline/backup/migration runner/schema groups | 001/002 | IN_REVIEW — SCRUM-65 technical checks PASS, Sang/G1 PENDING |
| M16-TASK-002 | W5-T01 | repository providers/composition contract | targeted module integration | IN_REVIEW — SCRUM-65 technical checks PASS, Sang/G1 PENDING |
| M16-TASK-003 | W5-T01 | durable worker/readiness/idempotency | 003/004/008 | IN_REVIEW — SCRUM-65 technical checks PASS, Sang/G1 PENDING |
| M16-TASK-004 | W5-T03 | data ops/cleanup/retention/backup hooks | 006/007 | IN_REVIEW — SCRUM-67 PR #38 evidence; PR #50 changes privacy/migration compatibility; cross-module/final integration review pending |
| M16-TASK-005 | W5-T04 | route/package/CI/docs integration | 005/009/010 | BLOCKED |
| M16-TASK-006 | W5-T04 + W5-N04 | final smoke/browser/evidence | 005/009/011 | BLOCKED |

M16-TASK-006 chỉ bắt đầu sau mọi module task cần thiết ở trạng thái IN_REVIEW/DONE trên cùng integration branch. Không dùng merge conflict resolution để thay review contract.

W6-T03 baseline: `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`. PR #50–#52 are integrated, but this does not satisfy TASK-005/006 final W5 gate or replace G1/Sang review.
