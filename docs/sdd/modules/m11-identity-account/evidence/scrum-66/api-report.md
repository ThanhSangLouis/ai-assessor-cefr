# Báo cáo lane API/DI/handoff — SCRUM-66

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

## Thay đổi đã tích hợp

- Thêm `IdentityApi` adapter cho self-service account, session, activity, consent, admin account và Google; body JSON từ chối field lạ/key trùng, lỗi được chuẩn hóa và không echo secret.
- Runtime chia sẻ cùng `SQLiteStore`, `IdentityRepository`, `AccountService`, `GoogleIdentityService`. Google config chỉ trả trạng thái đã lọc.
- Cookie phiên/Google flow HTTPS dùng tên `__Host-…`, Secure, HttpOnly, SameSite=Lax, Path=/; HTTP local dùng cookie tên/path riêng. HTTPS parser không fallback qua cookie HTTP cũ.
- Login giảm User-Agent thành enum `desktop|mobile|tablet|unknown` trước khi truyền cho AuthService; raw header không được lưu trong session metadata hoặc DTO.
- Google callback chỉ nhận GET, kiểm tra query đơn, luôn xóa flow cookie sau callback thành công/lỗi. Access log chỉ ghi method/status/size để code/state/query không lọt vào log.
- Legacy admin account create/change delegate qua AccountService. Account mới qua legacy route cũng bắt buộc đổi mật khẩu. Legacy login redirect tới form đổi mật khẩu và cấp phiên xoay sau khi đổi.
- Form `/password-change` trả HTML status 200 cho session tạm, có đủ current/new/confirm fields; thông báo lỗi được HTML-escape. Browser harness kiểm tra response cuối là 200 và các field có mặt.
- Erasure xóa thông tin credential/session/profile/provider/activity mutable, rút enrollment. Khi lịch sử bất biến còn FK, giữ alias pseudonymous dưới dạng account disabled với `password_hash` rỗng; preview nói rõ dữ liệu nào được giữ. Quét đầy đủ mọi FK column cùng tham chiếu tới `accounts(actor_id)` trước khi xóa stub.
- Tạo tài liệu consumer: [API contract](api-contract.md) và [UI handoff](ui-handoff.md). Handoff giữ phần thiết kế tab N01/N04 cho lane UI.

## Kiểm tra đã chạy

Lệnh test (offline, fixture model):

```sh
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/python -m pytest -q \
  tests/api/test_identity_api.py tests/api/test_google_identity_api.py \
  tests/portal/test_portal.py tests/local/test_foundation_runtime.py \
  tests/api/test_local_sessions.py
```

Kết quả sau khi thêm form `/password-change`, kiểm tra catalog/admin listing, coarse device category, và session refresh revocation race fix: `58 passed in 25.89s`.

`ruff check` trên adapter, WSGI/runtime, portal route/service/data, API tests, portal tests và Playwright harness: `All checks passed!`.

Adapter coverage gồm auth matrix (401 thiếu phiên, 403 role/temp gate, 404 foreign session, 409 self guard, 422 profile PII field), lockout 429, password rotation/cookie, consent withdraw, callback log redaction, HTTPS cookie parser, coarse UA categories + session metadata redaction, và Google real-service dispatch tests. Portal regressions xác nhận legacy self-disable 409 và erasure scrub/history behavior.

## Handoff và giới hạn xác minh

`scripts/qa/w5_identity_browser.py` cung cấp Playwright journey để chạy local. Clean-wheel browser run ban đầu phát hiện `/password-change` GET lỗi 500 vì renderer form còn thiếu; renderer và assertion response-status đã được sửa trong source. Root cần đóng gói/chạy lại clean-wheel browser journey trên build mới để xác nhận artifact mới. Google provider network/configuration thật, deployment TLS proxy behavior, và full repository suite thuộc root’s final QA. Không cấu hình provider thật, deploy, commit hay push.
