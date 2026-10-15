# Sáu task W5 của Thắng — readiness

Target baseline: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
Reference baseline: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.

Ngày 15/10/2026. Người dùng yêu cầu làm đầy đủ 6 task, gồm chuẩn bị commit/push/PR; chưa có verdict theo từng phase trong artifact. Không suy ra DONE từ yêu cầu này.

## Kết quả khảo sát và thứ tự

| Jira | Task | Hiện trạng đã xác minh | Việc còn lại / dependency |
| --- | --- | --- | --- |
| SCRUM-62 | G0 | baseline tests/build/boot/browser và backup/restore có evidence; branch triển khai đúng mốc đã tạo | Sang/Nguyên review ownership, nhánh và format FAIL |
| SCRUM-64 | G2 | [contract/runbook](W5-G2-migration-rollback.md) đã soạn, restore schema v4 PASS | review/chốt migration/rollback; chưa có W5 migration implementation |
| SCRUM-65 | T01 | SQLite v4, local worker và DI đã có; worker lấy response QUEUED trong một thread | cần migration registry/new schema/repositories, lease/CAS/retry/idempotency, readiness; G0–G2 và Phase 01/03/04/05 |
| SCRUM-66 | T02 | password hashing, lockout, TTL, consent và server auth M08 đã có | thiếu account/profile/password-change/temp-password/session-manager/admin atomic batch/Google flow/withdraw propagation W5; T01 + M11 |
| SCRUM-67 | T03 | DataControl có backup/export/erase/retention/cleanup cũ | chưa có package billing trong target; cần money rules, repositories, sandbox callbacks/license và data ops coverage; T01/T02 + M14/M16 |
| SCRUM-68 | T04 | entrypoint, wheel/CI và student/teacher baseline smoke đã có | cần các module W5, format gate, clean install, three-role journeys trên cùng final revision; T01–T03 + S01–S04 + N01–N04 |

G1 không thuộc sáu task nhưng vẫn là prerequisite T01. T04 không thể DONE khi phần Sang/Nguyên chưa tích hợp; không tự nhận hoàn thành task của họ.

## Gói Phase 01 để người dùng review

- [M11 Requirement v0.1](../m11-identity-account/01-requirement.md): profile không PII, password/session/admin controls, optional Google linked-account PKCE, consent. Đề xuất `RESEARCH MODE: RUN` để kiểm security/OIDC và adaptation.
- [M14 Requirement v0.1](../m14-billing-licensing/01-requirement.md): Free/Trial/Standard/Advanced, quote, sandbox signature/idempotency/license. Đề xuất `RUN`; **sandbox/test, không thu tiền thật**, không public callback/deploy.
- [M16 Requirement v0.1](01-requirement.md): một monolith/SQLite/worker, additive migration, data ops, wheel/CI/health. Đề xuất `RUN` cho gap analysis và contract adaptation.
- UI W5 vẫn thuộc Nguyên; Trust/learning/rating/research vẫn thuộc Sang. Chỉ sửa shared files sau owner coordination; báo cáo này không giả lập xác nhận của họ.

**Codex recommendation:** `RECOMMEND APPROVAL` Phase 01 cho ba Requirement trên với `RESEARCH MODE: RUN`, optional Google mặc định disabled khi thiếu config và sandbox billing. User verdict hiện **PENDING**.

Sau Phase 01 được duyệt: thực hiện Research → trình Specification cụ thể/schema/API → Test Plan → Plan/Task readiness đúng thứ tự. Không phát prompt implement từ draft hiện tại. Không tạo giả metrics, phase approval hoặc Jira Done.

## Git và review

- `feat/W5-product-parity`: nhánh người dùng tạo từ `5b477bd`, giữ nguyên, dùng cho PR hồ sơ G0/G2/readiness.
- `feat/W5-product-parity-baseline`: local branch tại `3b2d2b7`; tên khác để bảo toàn nhánh đã có. Chưa có implementation commit. Planning docs từ PR hồ sơ có thể đưa sang nhánh này sau khi review.
- Dữ liệu demo, database/blob/model và full local backup nằm ngoài Git; PR chỉ có báo cáo/evidence đã loại dữ liệu riêng tư và AI log.
- Jira connector chưa xuất hiện trong capability của phiên này, nên chưa đọc/chuyển trạng thái Jira trực tiếp. Không suy ra trạng thái remote từ screenshot cũ.
