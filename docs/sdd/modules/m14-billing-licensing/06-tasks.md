# M14 — Tasks

**Version:** v0.1 · **STATUS:** DRAFT.

| Task | W5 | Deliverable | Tests | Status |
| --- | --- | --- | --- | --- |
| M14-TASK-001 | W5-T01/T03 | billing schema/repository/migration | 004/010 | IN_REVIEW — SCRUM-67 evidence; PR #38 merged; user/reviewer verdict PENDING |
| M14-TASK-002 | W5-T03 | plan/quote/entitlement/license rules | 001/002/007 | IN_REVIEW — SCRUM-67 evidence; PR #38 merged; user/reviewer verdict PENDING |
| M14-TASK-003 | W5-T03 | sandbox settlement/signature/idempotency | 003–006/008 | IN_REVIEW — SCRUM-67 evidence; PR #38 merged; live gateway NOT_RUN |
| M14-TASK-004 | W5-T03 | optional gateway adapters/config status | 003/006/008 | IN_REVIEW — SCRUM-67 evidence; PR #38 merged; live gateway NOT_RUN |
| M14-TASK-005 | W5-N04 | billing admin/payment/result/receipt UI | 005/008/009 | BLOCKED — PR #47 has read-only surfaces; mutation/UI acceptance incomplete |
| M14-TASK-006 | W5-T04 | full security/regression/evidence | all | BLOCKED — final integrated W5-T04 gate not complete |

Không task nào được ghi DONE bằng giao dịch sandbox thủ công nếu tampering/replay/rollback tests chưa có.

W6-T03 baseline: `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`. PR #50 chạm billing-key/private-file paths sau SCRUM-67; giữ TASK-001–004 `IN_REVIEW` cho tới khi evidence/reviewer scope đó được đối chiếu. TASK-005/006 vẫn `BLOCKED`; không suy ra billing mutation/live payment đã được nghiệm thu.

Trạng thái task-local phản ánh code/evidence đã merge; module vẫn `DRAFT/PENDING`. Các dòng này không phê duyệt phase SDD hoặc đóng Jira.

## Local execution SCRUM-67

User giao trực tiếp W5-T03 và cho phép Luna implement/Codex review/tạo PR. Global packet vẫn DRAFT; không biến các dòng BLOCKED planning ở trên thành approval. Backend tương ứng TASK001–004 đã được triển khai trên base `bab5f25`, final local verification PASS, sẵn sàng PR review. Handoff cho TASK005/N04 nằm trong evidence; full UI và TASK006/T04 không được ghi hoàn thành từ task này. Historical target `3b2d2b7`; Sang `40907cc`.

- [Authority](evidence/scrum-67/authority.md)
- [Review record](evidence/scrum-67/review-record.md)
- [Verification và mapping](evidence/scrum-67/verification.md)

## W7 — Chuyển M14 và kênh tính lượt từ repo gốc (W7-T03, SCRUM-100)

| Task | Deliverable | Tests | Status |
| --- | --- | --- | --- |
| W7-T03 (M14) | `src/aicefr/billing/` (plans, licenses, quotes, gateways, payments, service, keys), kho `storage/billing_repository.py`, dịch vụ `services/core/billing/`, module tính lượt `src/aicefr/metering/` và kho `storage/metering_repository.py`, dịch vụ `services/core/metering/` | `test_billing.py`, `test_billing_unit.py`, `test_gateways.py`, `test_gateways_unit.py` | IN_REVIEW — Chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95 vào nhánh tích hợp |

