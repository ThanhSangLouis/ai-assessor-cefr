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

## W7 — Nền kiến trúc ba dịch vụ (W7-T01, SCRUM-98)

| Task | Deliverable | Tests | Status |
| --- | --- | --- | --- |
| W7-T01 | `contracts.py`, `ports.py`, `config.py`, `encoding.py`, `formatting.py`, `observability.py`, `cli.py`; `storage/db.py`, `storage/migrations.py` (MongoDB, D048); `platform/` (bus, RedisBus, RPC, gateway, D050); `infra/` (blob store kể cả S3, hàng đợi, giới hạn tần suất, D051); `services/runtime.py`, `services/core/app.py`; compose, `deploy/`, `Dockerfile`, CI | `test_contracts`, `test_ports`, `test_schema`, `test_services_split`, `test_bus_redis`, `test_blobs`, `test_observability_unit`, `test_platform_unit`, `test_deploy_config` | IN_REVIEW — PR vào `migrate/w7-repo-goc`; chờ Thắng review |

Chuyển từ `ThanhSangLouis/ai-assessor-cefr@059fa28` (bản `0853c95` đã gỡ artifact S&I, W7-S01). Sang làm thay theo chỉ dẫn của chủ dự án ngày 25/10/2026 để gỡ chặn đợt 2; Thắng là người review và vẫn là chủ M16. Runtime cũ được gỡ cùng PR: `local/`, `limits.py`, `storage/{sqlite,paths,providers,blob,jobs}.py`, `storage/migrations/*.sql` và test của chúng. Kho theo module (`storage/identity.py`, `billing.py`, `learning.py`, ...) do chủ module gỡ khi chuyển phần của mình.
