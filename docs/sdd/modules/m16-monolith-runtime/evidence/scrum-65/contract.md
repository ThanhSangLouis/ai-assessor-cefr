# SCRUM-65 — Contract triển khai và verification

Historical target: `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.
Reference: `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`.
Actual branch base: `9968abcac29efdf81e2c9eb57302a842b396f409`.

Ngày 15/10/2026; phạm vi người dùng yêu cầu trực tiếp: W5-T01.1–T01.6, Codex lead/review, Luna implement. Xem [authority](authority.md). Đây là contract task cụ thể, không đổi verdict các module M09–M16 hay nhận nghiệm thu thay Sang.

## Kiến trúc và ranh giới

Một entrypoint WSGI, SQLite file hiện có và local worker thread. Các connection của request/worker/heartbeat đều trỏ cùng database; không chia sẻ connection SQLite giữa thread. Không thêm dependency sản phẩm, DB thứ hai, broker hoặc HTTP nội bộ.

Migration groups v5 identity, v6 learning, v7 research/rating, v8 billing, v9 jobs/cleanup. Không sửa shape legacy `accounts`, `sessions`, `responses`, report/review/audit/task/config; phần mới dùng side tables và FK. Tất cả W5 group chạy trong một transaction, có ledger checksum và schema signature; lỗi phải rollback về version ban đầu. Fresh install chạy legacy v1–v4 rồi W5. Preflight backup gồm SQLite snapshot, blobs và checksums/private permissions; restore chỉ vào path mới.

RepositoryProviders có profiles/learning/rating/research/billing/cleanup, được inject vào LocalRuntime. Repository mở transaction qua store; service consume typed record/port, không tự mở DB. Business rules account/OAuth/payment/learning/rating vẫn thuộc task tương ứng; T01 chỉ cung cấp persistence foundation.

Durable job có unique response/idempotency key, state queued/running/succeeded/failed, bounded attempts, available_at/backoff, owner/revision/lease fencing. Claim/recovery/finalization có CAS; expired recovery bump response revision trước retry. Commit guard chạy trong transaction ghi report/status/review/audit để stale worker không ghi kết quả của successor. Không giữ transaction trong suốt inference. Worker periodically phát hiện submit/enqueue crash gap, heartbeat dùng connection riêng, mất lease không tiếp tục ghi final state. Không sửa score/rubric hoặc tạo output giả.

Readiness `/ready` và `/readyz` kiểm config/schema/SQLite/blob/worker/model, chỉ boolean/fixed reason codes; liveness `/live` và health aliases không phụ thuộc model. Thiếu model là readiness 503 trung thực, không tải model. Wheel phải chứa SQL migration và static assets thực có.

## Kiểm tra trước PR

- M16-TEST-001/002: fresh + populated v4 preserve + idempotent rerun + injected failure ở mỗi group + restore boot; schema newer/partial/ledger/index/trigger tamper từ chối.
- M16-TEST-003/004: atomic two-connection claim, wrong/stale/expired owner, heartbeat, retry/backoff/max-attempts, restart và duplicate; stale coordinator không ghi report/terminal audit.
- M16-TEST-005/008/010: wheel build/install trong venv sạch offline bằng wheelhouse core/transitive; CLI/login/liveness/readiness missing-model, SQL/static included; không D043/dependency mới.
- Repository contracts: FK/unique/transaction, typed round-trip, immutable publication/ratings, profiles không PII/goal allowlist; no app import cycles/global mutable singleton.
- Full non-smoke suite + coverage no regression so với baseline thực `9968abc`, targeted tests, lint changed scope, format changed files; lỗi global baseline có sẵn ghi rõ.
- Runtime/browser smoke trên final source; dữ liệu thử/backup/model giữ ngoài Git.

## Nguồn kỹ thuật đã đối chiếu

Đã đọc tài liệu chính thức ngày 15/10/2026, dùng để thiết kế transaction và backup (không thay requirement dự án):

- [SQLite transaction](https://www.sqlite.org/lang_transaction.html): transaction ghi có một writer, BEGIN IMMEDIATE đặt write lock; nested operations dùng transaction outer hiện có hoặc savepoint.
- [SQLite Backup API](https://www.sqlite.org/backup.html): snapshot qua backup API; không copy file database đang ghi như cách backup mặc định.
- [SQLite foreign_keys](https://www.sqlite.org/pragma.html#pragma_foreign_keys): bật/kiểm FK trên từng connection ngoài transaction.

## Done/acceptance

Codex chỉ đưa technical review/recommendation. PR chỉ sau kiểm tra/review code đạt; Sang review và dependency G1 vẫn phải được nêu rõ. Không tự merge hoặc chuyển Jira Done. Không tuyên bố T02/T03/T04, Google hoặc payment business flow hoàn tất từ schema foundation.
