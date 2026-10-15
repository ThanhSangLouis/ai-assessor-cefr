# Báo cáo lane Billing Core — SCRUM-67

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; reference Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`; actual implementation base `bab5f2513b1377013b2538143b50d30de650dc0f` (T01 + T02 `754ee9a`).

## Phạm vi

Đã triển khai hợp đồng DTO/lỗi, bảng giá và quy tắc gói, phép tính quote/proration, service điều phối billing và repository SQLite trong transaction dùng chung với ứng dụng. Các luồng gồm overview theo organization cài đặt, tạo quote/order, sandbox settlement, xử lý normalized payment event, receipt, hủy order, danh sách order và capacity check cho student mới. Một ID organization pseudonymous được ghi một lần vào runtime settings và dùng chung entitlement cho mọi admin trong installation; quota assessment chỉ phát cảnh báo 80%/100%, không chặn việc học hay assessment. Feature tăng theo tier chỉ gồm capability hiện có; billing không cấp quyền quản lý tài khoản, quyền dữ liệu cá nhân hay quyền nghiên cứu.

Quote lưu snapshot bất biến gồm entitlement/source order, thời điểm hiệu lực/hết hạn, giá, giảm giá và credit. API-safe metadata `effective_at`, `ends_at`, `change_kind` được tính một lần tại quote, gồm ngày kết thúc theo lịch cho kỳ trả phí, 30 ngày cho Trial và không có ngày kết thúc cho Free; entitlement snapshot vẫn private. Proration dùng integer minor units, giá trị paid order trước đó và phần thời gian thực còn lại; credit không vượt giá mới. Quote/order idempotency key bị ràng buộc với input gốc. Repository kiểm tra lại entitlement trong write transaction khi tạo order. Settlement ghi event, chuyển state, receipt, entitlement và audit trong cùng transaction; callback trễ sau hạn checkout không cấp receipt/entitlement, callback success sau state terminal không đảo ngược state. Event replay được kiểm soát theo event ID và payload hash. Checkout còn pending sau timeout có thể retry an toàn.

## Kiểm chứng

Môi trường Python 3.12.3; test chạy offline, `tests/billing/conftest.py` chặn outbound socket/urllib. Không gọi payment provider thật, không sửa SQL/schema trong lane này, không commit/push.

```text
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models COVERAGE_FILE=/tmp/.coverage-scrum67-final-lane /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest -q tests/billing tests/api/test_billing_webhook_contract.py --disable-warnings --cov=aicefr.billing --cov=aicefr.storage.billing --cov-branch --cov-report=term-missing
123 passed in 23.25s

/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/billing/contracts.py src/aicefr/billing/errors.py src/aicefr/billing/plans.py src/aicefr/billing/quotes.py src/aicefr/billing/service.py src/aicefr/storage/billing.py tests/billing/test_plans.py tests/billing/test_quotes.py tests/billing/test_billing_service.py tests/billing/test_billing_repository.py --output-format concise
All checks passed!
```

Coverage chạy tập trung đạt 93.9% statements (1439/1532) và 91.0% branches (515/566), vượt mục tiêu tổng 90%/85%. `service.py` đạt 95.6% statements (260/272) và 90.4% branches (103/114); `storage/billing.py` đạt 97.3% statements (323/332) và 95.2% branches (120/126). `plans.py`, `quotes.py`, contracts và errors đạt 100% line/branch. Coverage review được biên soạn lại thành các invariant persistence cụ thể: retry idempotent, xung đột key, timestamp/payment binding, settlement rollback, trạng thái terminal, entitlement/grace và kiểm tra capacity; test chỉ bổ sung các nhánh hành vi có ý nghĩa, không thêm test để chạy qua dòng code một cách máy móc.

Các kiểm thử lane bao gồm transaction rollback, idempotency với input đổi và exact retry, stale quote trước và trong lúc tạo order, retry sau timeout, thất bại/hủy/hết hạn, callback sai hoặc trễ, event replay, hai SQLite connection settlement cạnh tranh, proration trên kỳ annual, entitlement tie/grace/scheduled boundary, seat scope theo organization và quota warning. Riêng `storage/billing.py`, 117 test trong `tests/billing` đạt 97% statements và 95% branches. Provider thật, merchant credentials, live mode và kiểm thử nhiều tiến trình triển khai được ghi nhận **NOT_RUN**.

## Ranh giới còn lại

Đây là kết quả lane tập trung, chưa thay thế full-project test, integration review, migration review hay đánh giá bảo mật của root. API/data adapter và migration v10 thuộc lane khác. Pull request, merge và triển khai chưa thực hiện.
