# W5-G2 — Migration và rollback

Target baseline: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
Reference baseline: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.

Task: SCRUM-64 / W5-G2 · Owner đề xuất từ vùng migration: Thắng · Review: Sang/Nguyên.
Version v0.1 · DRAFT / IN_REVIEW · User/reviewer verdict PENDING · 15/10/2026.

## Contract cần chốt

Migration chỉ additive, cùng một SQLite database và blob store hiện có. Không DROP/rename destructive, không copy database của bản Sang sang repo nhóm, không tạo PostgreSQL/broker/service riêng. Các schema của reference dùng để đối chiếu hành vi, không phải migration script có thể chạy trực tiếp lên target (target dùng `accounts`/`sessions`, reference dùng `account`/`auth_sessions`).

Thứ tự nhóm migration theo kế hoạch: identity/session/consent → learning/achievement → blind rating/study/measurement → billing → durable jobs/cleanup. Số schema version, DDL, constraint/index và mapping field chỉ khóa sau Specification liên quan được duyệt; không tự gán v5–v9 trước contract freeze.

| Nhóm | Dữ liệu giữ nguyên | Phần mở rộng / contract cần kiểm |
| --- | --- | --- |
| Account/session/consent | account ID/role/password hash, phiên chưa hết hạn, consent/version/research opt-in | profile allowlist, temp password, session metadata, Google subject hash và append-only consent event; M11 |
| Response/blob/report | ID/owner/task version/status/revision, blob byte hash, report JSON/provenance/evidence | không sửa score/rubric/band; media mới phải tham gia backup/export/erase; M10/M13/M16 |
| Review/audit | review candidates/decisions, teacher verification thực tế, audit ordering | blind/study rows không làm lộ identity/machine result; M12/M13 |
| Config/model/task | task/config history, model registry và artifact references | không tự bật model/gateway/Google; không đổi threshold; M11/M14/M16 |
| Billing/jobs/cleanup | các bảng cũ và cleanup intents | FK/unique/idempotency/lease/retry/CAS; M14/M16 |

## Preflight và migration runbook

1. Chốt reviewed revision, migration list/checksum và allowed files. Chỉ tiếp tục khi G0/G1/G2 và SDD module đã được duyệt đúng checkpoint.
2. Dừng app/worker đang dùng **data-dir cần migrate**, xác nhận không còn writer. Không dùng dữ liệu thật để test.
3. Kiểm `PRAGMA user_version=4`, `integrity_check=ok`, `foreign_key_check` không có lỗi; ghi row counts, schema dump, hash report/blob và config/model manifest.
4. Backup SQLite bằng backup API; copy blob/media và metadata cần restore. Kiểm checksum và private permissions. Restore thử vào vị trí mới trước migration.
5. Thử migration trên **bản sao**. Giữ exclusive migration lock xuyên suốt backup/verify/switch; dùng transaction đúng boundary, từ chối schema mới hơn/partial hoặc thiếu prerequisite.
6. Mỗi migration verify FK/index/unique và legacy data trước commit. Nếu fail, rollback transaction, không serve database partial.
7. Rerun migration phải không tạo row/event/index trùng. Test fresh install và v4→latest bằng SQLite file thật.
8. Smoke boot trên bản sao đã migrate; đọc report cũ, xác nhận session/consent hợp lệ. Chỉ đổi local runtime sau review; backup cũ giữ nguyên.

## Rollback runbook

1. Dừng app/worker; giữ database lỗi ở vị trí cách ly để kiểm tra, không overwrite hoặc xóa.
2. Kiểm checksum backup manifest; restore database + blob/media + config tương thích vào data-dir **mới**, không ghi đè nguồn.
3. Chạy code revision trước migration là `3b2d2b7`; trỏ vào data-dir đã restore. Không chạy code yêu cầu schema mới với database cũ.
4. Kiểm integrity/FK/count/hash, đọc report cũ và boot/login. Chỉ chuyển data-dir vận hành khi kiểm tra đạt.
5. Nếu rollback fail, giữ app dừng, giữ cả backup và bản lỗi; ghi evidence/reason, không đoán PASS.

## Test matrix cho T01

| ID | Scenario | Điều kiện đạt |
| --- | --- | --- |
| M16-TEST-001 | fresh + v4→new + rerun | legacy counts/content/blob hash giữ nguyên; không duplicate |
| M16-TEST-002 | failure injection giữa từng nhóm | không partial schema; old app đọc bản restore |
| M11-TEST-010 | account/session/consent | phiên hợp lệ và ownership giữ nguyên |
| M14-TEST-010 | billing constraints/transaction | FK/unique và rollback hợp lệ |
| M16-TEST-003/004 | concurrent claim/retry/restart | một terminal result/audit; không kẹt RUNNING |
| M16-TEST-006/007 | export/erase/retention/backup | không mất dữ liệu người khác; cleanup retry và restore đúng |

## Evidence đã có và giới hạn

[G0 backup/restore](evidence/w5-g0-2026-10-15/backup-restore-summary.json) PASS: schema v4, 11 bảng, 4 blob, table contents và hashes khớp, dữ liệu nguồn không đổi. [Báo cáo G0](evidence/w5-g0-2026-10-15/W5-G0.md) ghi toàn bộ kiểm tra baseline.

Đây là **restore của schema hiện tại**, chưa phải forward migration W5 hoặc failure-injection PASS. DDL runner mới và các test matrix ở trên **NOT_RUN/NOT_IMPLEMENTED**. G2 cần reviewer chốt contract này; T01 mới triển khai và đo kết quả.

**Codex recommendation:** review contract G2 cùng Requirement M11/M14/M16. **User/reviewer verdict:** PENDING. Chưa đề xuất Jira Done.
