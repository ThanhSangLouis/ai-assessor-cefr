# M14 — Billing and Licensing Sandbox — Requirement

**SCOPE ID:** M14 · **TYPE:** module · **OWNER:** Thắng
**ROOT:** `docs/sdd/modules/m14-billing-licensing/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M08, M10–M12, M15, M16
**RESEARCH MODE:** `RUN` đề xuất — payment signature/replay/config từ D034–D035 cần review.
**USER VERDICT:** PENDING

## Requirements

- **M14-FR-001:** plan ladder Free, Trial 30 ngày, Standard, Advanced; entitlement tăng dần và không khóa learning/data rights của sinh viên.
- **M14-FR-002:** seat limit chỉ chặn account student mới; assessment quota chỉ cảnh báo 80/100%; research-consented assessment không tính nếu policy được duyệt.
- **M14-FR-003:** quote có 12-month discount 15%, prorated upgrade, queued renewal/downgrade, paid grace 14 ngày.
- **M14-FR-004:** order/payment/receipt lifecycle idempotent; gateway sandbox nội bộ mặc định.
- **M14-FR-005:** VNPay/Stripe/MoMo chỉ load khi config test hợp lệ; live mode khóa bởi explicit config và ngoài QA W5.
- **M14-FR-006:** verify signature, amount, currency, order, gateway, checkout/session và live/test mode; replay/duplicate callback không settle hai lần.
- **M14-FR-007:** signed license HMAC có organization, expiry, features, student limit, nonce/key version; install/renew audit.
- **M14-FR-008:** admin UI hiển thị plan/quote/order/receipt/gateway status/missing config và nhãn sandbox; không secret/payment instrument.

## Acceptance Criteria

- **M14-AC-001:** mọi plan giữ student learning; hết hạn/grace không xóa dữ liệu hoặc đóng hành động đã tạo.
- **M14-AC-002:** quote/proration/discount dùng integer minor units, rounding deterministic và currency thống nhất.
- **M14-AC-003:** tampered/wrong-gateway/wrong-mode/amount/currency/signature bị từ chối; duplicate/reordered messages settle một lần.
- **M14-AC-004:** timeout/pending/cancel/fail/late success có transition hợp lệ và receipt chỉ khi paid.
- **M14-AC-005:** unit/integration CI không gọi mạng thật; live credential/mode không bật trong W5.
- **M14-AC-006:** license forged/expired/wrong key/version/replay bị từ chối và không đổi entitlement.
- **M14-AC-007:** secret/card/bank/name/email không có trong API/DOM/log/database/export.

## Out of scope

Thu tiền thật, deploy callback public, refund/chargeback production, invoice thuế, student purchase, lưu payment instrument.
