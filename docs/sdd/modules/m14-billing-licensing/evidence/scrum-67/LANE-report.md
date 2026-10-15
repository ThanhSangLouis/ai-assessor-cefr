# Báo cáo lane Gateway, License và Secrets — SCRUM-67

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; reference Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual implementation base `bab5f2513b1377013b2538143b50d30de650dc0f` (T01 + T02 `754ee9a`).

## Phạm vi đã thực hiện

Lane triển khai `GatewayRegistry` với sandbox nội bộ có chữ ký, adapter kiểm thử cho Stripe Checkout, MoMo captureWallet và VNPay 2.1.0; kho HMAC dùng chung cho chữ ký license/webhook; `LicenseService` để phát hành, cài đặt, kiểm tra license và ghi entitlement/audit trên transaction do caller quản lý. Các file được sở hữu trong lane gồm:

- `src/aicefr/billing/gateways.py`
- `src/aicefr/billing/licenses.py`
- `src/aicefr/billing/secrets.py`
- `tests/billing/test_gateways.py`
- `tests/billing/test_licenses.py`
- `tests/billing/test_payment_tampering.py`
- `tests/billing/conftest.py`
- `tests/api/test_billing_webhook_contract.py` (consumer contract tests only; no API implementation edits)

`KeyRing` lưu key versioned tại `data_dir/billing-hmac.key`, permission `0600`, từ chối symlink/hardlink, quyền file quá rộng, owner không hợp lệ và đường dẫn nằm trong repository. `GatewayRegistry` không còn mặc định `data_dir="."`; nếu không truyền keyring thì phải truyền data directory rõ ràng. HMAC tách domain license và gateway-event. Khóa live payment ở cấu hình; adapter provider chỉ hoạt động khi bật chế độ test, đủ test config và được inject transport. Các callback được giới hạn kích thước, timestamp, field/header và được xác minh chữ ký trước normalize.

License ký canonical payload có organization, plan, feature, giới hạn học viên, thời gian phát hành/hết hạn, nonce và key version. License đã ký phải có hạn dùng tương lai hữu hạn; thời điểm phát hành không được vượt quá clock quá 5 phút; feature và seat limit phải nằm trong plan. Nonce được ghi dạng hash vào `runtime_settings`. Exact retry khi cài đặt chỉ được chấp nhận sau kiểm tra hết hạn. ID organization chỉ nhận `local-demo` hoặc mã opaque `org_...`, được ghi qua helper binding dùng chung với billing core; cấu hình khác với binding đã lưu bị từ chối. `issue` nhận `idempotency_key` tùy chọn: key được hash và scope theo admin, cùng key/cùng request trả lại artifact đã phát hành (kể cả sau khi artifact hết hạn) mà không ghi entitlement/audit lần hai; cùng key/request khác trả 409. `apply_entitlement(connection, ...)` chỉ ghi entitlement và audit `billing_entitlement_applied`, không commit, để settlement giữ tính nguyên tử.

Fixture `tests/billing/conftest.py` tự động chặn `socket.connect`, `socket.connect_ex`, `socket.create_connection` và `urllib.request.urlopen` trong toàn bộ billing tests. Test redirect chỉ chấp nhận host checkout cố định của provider tương ứng; lỗi transport trả code an toàn và bỏ exception cause để không giữ credential trong traceback API.

Contract tests API chạy `BillingApi`, service, repository, registry và SQLite thật trong WSGI harness, với transport provider giả được inject. Có kiểm tra Stripe raw body whitespace đúng trong chữ ký, callback Stripe và sandbox lặp chỉ tạo một payment event/receipt, VNPAY form-urlencoded ký hợp lệ, sai chữ ký, sai `livemode` ở cả top event và Checkout Session, sai số tiền không áp entitlement, provider tắt trả 503, và license issue API replay cùng artifact/conflict khi thay payload. Các test parser/security bổ sung bao phủ VNPAY Unicode không hợp lệ, form trùng field, timestamp sai, thiếu status; Stripe metadata fallback và event chưa terminal; sandbox status/mode sai; chuỗi Unicode surrogate, timestamp tràn miền, header không đúng kiểu và key file quá dài. Trong khi tạo test phát hiện khối return của `BillingApi._signature_headers` bị đặt sau `return` của `_request_values`, khiến webhook mất signature header; data/API owner đã chuyển return về đúng hàm và thêm `X-Sandbox-Signature` vào allowlist. Đây là sửa của lane API khác, được ghi lại để reviewer theo dõi.

## Nguồn tài liệu provider

- Stripe Checkout Sessions API: [docs.stripe.com/api/checkout/sessions](https://docs.stripe.com/api/checkout/sessions)
- Stripe automated testing: [docs.stripe.com/automated-testing](https://docs.stripe.com/automated-testing)
- MoMo one-time captureWallet: [developers.momo.vn/v3/docs/payment/api/wallet/onetime](https://developers.momo.vn/v3/docs/payment/api/wallet/onetime/)
- MoMo notification handling: [developers.momo.vn/v3/docs/payment/api/result-handling/notification](https://developers.momo.vn/v3/docs/payment/api/result-handling/notification/)
- MoMo result codes: [developers.momo.vn/v3/docs/payment/api/result-handling/resultcode](https://developers.momo.vn/v3/docs/payment/api/result-handling/resultcode/)
- VNPay pay API: [sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html)

## Ranh giới kiểm chứng

Adapter provider được kiểm tra bằng mock transport được inject và fixture chữ ký hợp lệ/không hợp lệ. Đây là kiểm chứng chuẩn hóa payload, xác minh chữ ký, mode test, allowlist redirect và xử lý lỗi cục bộ; **không phải** kết nối thật tới Stripe/MoMo/VNPay. Không có merchant credential thật, gọi provider sandbox/dashboard, production transport hay outbound request nào được chạy. Live payment bị khóa cứng. Vì vậy test thật của provider được ghi là **NOT_RUN**.

## Kiểm tra và kết quả

Môi trường: Python 3.12.3; dùng `.venv` chung của dự án, `PYTHONPATH=src`, `AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models`, coverage tại `/tmp/.coverage-scrum67-LANE`.

Lint và format trên file lane:

```text
/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff format src/aicefr/billing/gateways.py src/aicefr/billing/licenses.py src/aicefr/billing/secrets.py tests/billing/test_gateways.py tests/billing/test_licenses.py tests/billing/test_payment_tampering.py tests/billing/conftest.py tests/api/test_billing_webhook_contract.py
8 files left unchanged

/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/billing/gateways.py src/aicefr/billing/licenses.py src/aicefr/billing/secrets.py tests/billing/test_gateways.py tests/billing/test_licenses.py tests/billing/test_payment_tampering.py tests/billing/conftest.py tests/api/test_billing_webhook_contract.py
All checks passed!
```

Scoped test và coverage:

```text
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models COVERAGE_FILE=/tmp/.coverage-scrum67-LANE /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest -q --cov=aicefr.billing.gateways --cov=aicefr.billing.licenses --cov=aicefr.billing.secrets --cov-branch --cov-report=term-missing tests/billing tests/api/test_billing_webhook_contract.py
95 passed
```

Coverage JSON phân biệt đúng số dòng và nhánh đã thực thi (không dùng phần trăm tổng hợp pytest làm line coverage):

```text
gateways.py: 382/421 lines; 159/180 branches (90.74% statements; 88.33% branches)
licenses.py: 263/284 lines; 89/102 branches (92.61% statements; 87.25% branches)
secrets.py: 103/111 lines; 24/28 branches (92.79% statements; 85.71% branches)
Combined: 748/816 lines; 272/310 branches (91.67% statements; 87.74% branches)
```

Coverage mục tiêu 90% statements/85% branches đã đạt cho từng module được đo, gồm parser gateway, license và keyring. Các nhánh chưa phủ còn lại chủ yếu là provider response/error phụ, nhánh corruption fallback và một số lỗi hiếm của filesystem/session.

## Trạng thái

Không tạo migration, không sửa schema, không commit/push. Billing suite và webhook consumer contract tests hiện đều xanh, coverage đạt ngưỡng theo module. Chờ root review và kiểm chứng độc lập toàn repository.
