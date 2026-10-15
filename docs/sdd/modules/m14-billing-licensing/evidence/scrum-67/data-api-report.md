# Báo cáo lane Data Operations và API — SCRUM-67

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; reference Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual implementation base `bab5f2513b1377013b2538143b50d30de650dc0f` (T01 + T02 `754ee9a`).

## Kết quả

Đã nối API admin billing/license vào router/runtime, giữ body webhook nguyên bản để adapter xác minh chữ ký, allowlist DTO nhạy cảm và giữ quyền/CSRF/status lỗi của T02. Admin license issue hỗ trợ idempotency tùy chọn; quote chỉ lộ các mốc `effective_at`, `ends_at`, `change_kind` đã chọn. Export cá nhân dùng allowlist, giữ lịch sử đồng ý và kết quả học tập của chủ tài khoản nhưng loại token/digest, runtime license nonce/payload/signature, khóa và metadata nhà cung cấp.

Data controls có preview/fingerprint bao phủ hồ sơ, session, consent, hoạt động, phản hồi/báo cáo, attempt, nghiên cứu/khảo sát, billing và liên kết audit; xác nhận recheck admin và fingerprint trong transaction. Erasure giữ event xóa cuối cùng gắn với admin đã xác thực, xóa định danh tự do, thay các mutable FK còn lại bằng tombstone opaque, gỡ assignment/rating/consent theo thứ tự và giữ audit tối thiểu. Migration v10 là additive, chỉ mở ngoại lệ DELETE theo cleanup intent khớp; trigger update immutable và audit no-delete vẫn bật. Seat limit FREE được kiểm tra trong transaction ngay trước insert cho cả modern và legacy account APIs; re-enable tài khoản cũ không bị chặn.

Retention dry-run là mặc định và apply recheck điều kiện dưới write lock; đang chạy/xếp hàng hoặc trạng thái chưa biết được giữ lại. Cleanup là retryable qua intent bền vững, kiểm tra lại tham chiếu response và media bài học trước unlink. Backup/restore gồm snapshot SQLite, media response và media bài học đã tham chiếu, manifest hash, cùng key cần thiết được bảo vệ; restore kiểm tra integrity/FK/schema/blob/key và mở store ở thư mục mới. API chọn backup bằng ID server phát, không nhận đường dẫn.

## Kiểm thử

Môi trường offline: Python 3.12.3, `.venv` dự án, `PYTHONPATH=src`, fixture model tại `AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models`. Không gọi payment provider thật, không đổi dữ liệu runtime thật, không commit/push.

Lệnh lint scoped:

```text
/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/auth/accounts.py src/aicefr/local/app.py src/aicefr/portal/data.py src/aicefr/portal/router.py src/aicefr/portal/service.py src/aicefr/storage/identity.py src/aicefr/storage/migrations.py src/aicefr/api/billing.py src/aicefr/api/data_operations.py tests/portal/test_portal.py tests/api/test_data_operations_api.py tests/api/test_billing_api.py tests/storage/test_privacy_migration.py
All checks passed!
git diff --check
PASS
```

Lệnh pytest scoped:

```text
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest -q tests/portal/test_portal.py tests/api/test_billing_api.py tests/api/test_data_operations_api.py tests/storage/test_privacy_migration.py tests/storage/test_w5_storage_foundation.py tests/storage/test_identity_compatibility.py tests/storage/test_sqlite_memory_migration.py tests/storage/test_sqlite_blob_store.py
82 passed in 32.42s
```

Bộ kiểm thử gồm HTTP auth/CSRF/export/redaction, stale preview do profile hoặc survey mới, rollback giữa chừng khi audit thất bại, xóa research rating có dữ liệu thật, audit shared lesson không đổi, race retention với response chuyển sang RUNNING, giới hạn seat modern/legacy/batch rollback, backup/restore media bài học + key usable, file backup bị sửa, và migration v9→v10 / rollback lỗi migration / reopen idempotent.

Coverage lần đầu của lane (pytest-cov + branch, 49 test trong tập portal/API):

```text
portal/data.py: 80.7% lines; 156/218 branches
portal/service.py: 82.7% lines; 57/80 branches
api/billing.py: 69.1% lines; 32/52 branches
api/data_operations.py: 69.4% lines; 23/42 branches
```

Coverage ban đầu dưới ngưỡng mục tiêu. Sau đó đã bổ sung kiểm thử an toàn đầu vào API, fingerprint tác vụ/cleanup, manifest sai cấu trúc, file media bị thiếu, lỗi audit khi restore, retry cleanup và migration khi nền tảng không có `os.getuid`.

## Bổ sung xác minh SCRUM-67

Lệnh coverage cuối cùng, gồm API billing, webhook, data operations, portal và migration privacy:

```text
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest -q --cov=aicefr.portal.data --cov-branch --cov-report=term-missing tests/api/test_data_operations_api.py tests/portal/test_portal.py tests/portal/test_w5_data_recovery.py
85 passed in 48.96s
```

Coverage đo được ở lượt API ban đầu: `api/billing.py` 91% line / 46 trên 52 branch đã đi qua; `api/data_operations.py` 92% line / 40 trên 46 branch; `portal/service.py` 83% line / 61 trên 80 branch. Lượt coverage cuối tập trung vào `portal/data.py`: **93% line** và **210 trên 246 branch (85.4%)**, đạt mục tiêu ≥90% line / ≥85% branch. Không loại trừ nhánh để làm đẹp số liệu.

Đã thêm `scripts/qa/w5_billing_browser.py`, harness Chromium chỉ cho URL loopback, khóa request ra ngoài, đăng nhập admin/student, kiểm quote/order, callback sandbox có chữ ký và phát lại, receipt, retention preview, backup/restore mới, erasure preview, student 403, CSRF cross-origin và lỗi console/page. Root đã chạy một lượt trên wheel sạch trước patch cuối về session/audit của backup: lượt đó PASS, không có page/console error và SHA-256 wheel là `d60bc7e05bfeec7c1216d3aa61d5c11d62a9c72f23e2cbe6f9e861a58661d31b`, khớp nguồn tại thời điểm chạy. Cần rebuild và chạy lại journey để xác nhận patch cuối. Harness không gọi provider thật.

Lệnh kiểm tra cuối lane: Ruff scoped và `git diff --check` đều PASS; `py_compile` và `--help` của browser harness PASS. Bộ coverage cuối gồm test retry cleanup, bảo vệ media được chia sẻ, retention cho practice/step attempts và jobs/intents, orphan cleanup, backup conflict/FK, key không an toàn, cùng restore manifest/database/media/key/audit lỗi. Không tạo commit hoặc push.

## Giới hạn

Provider live và production payment **NOT_RUN**; chỉ sandbox/mock và callback ký bằng fixture. Browser harness cần server wheel sạch, database disposable đã khởi tạo cùng fixture admin/student và Chromium/Playwright; không chạy với dữ liệu production hoặc DB đang dùng.

## Codex final verification

Source cuối đã được build/cài wheel offline và chạy lại Chromium sau backup authorization/audit fix: PASS, zero page/console errors. Wheel/source byte match và SHA256 cuối nằm trong `wheel-browser.json`. Full suite độc lập của Codex: 600 PASS; coverage final riêng portal/data95,97%/85,37%, API billing92,68%/88,46%, data API94,26%/86,96%. Báo cáo scoped phía trên giữ kết quả từng lane đúng thời điểm, không thay thế số liệu full cuối.
