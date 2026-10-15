# Hợp đồng API dữ liệu — SCRUM-67

Các route dưới đây dùng session cookie và kiểm tra CSRF theo T02. Tất cả body ghi là JSON object có giới hạn kích thước; khóa JSON trùng, giá trị không hữu hạn, trường thừa hoặc sai kiểu bị từ chối. API không nhận đường dẫn filesystem từ client.

| Route | Quyền | Hành vi |
|---|---|---|
| `GET /api/v1/me/export` | Người dùng đã đăng nhập | Tải dữ liệu cá nhân đã chiếu qua allowlist |
| `POST /api/v1/admin/data/erasure/preview` | Admin | Nhận `actor_id`; trả số lượng và fingerprint, không trả nội dung riêng tư |
| `POST /api/v1/admin/data/erasure/confirm` | Admin | Nhận `actor_id`, `confirm_id`, `fingerprint`; từ chối preview cũ bằng 409 |
| `GET /api/v1/admin/data/retention?days=N` | Admin | Dry-run mặc định |
| `POST /api/v1/admin/data/retention` | Admin | Áp dụng retention rõ ràng; nhận `days` |
| `POST /api/v1/admin/data/backups` | Admin | Tạo snapshot; trả `backup_id` và manifest an toàn |
| `POST /api/v1/admin/data/restore` | Admin | Nhận `backup_id` đã cấp trong namespace của installation; restore sang staging mới |

Billing admin API dùng `/api/v1/admin/billing`, `/quotes`, `/orders`, `/orders/{id}/settle`, `/orders/{id}/cancel`, `/orders/{id}/receipt`, `/licenses`, `/gateways`. Webhook đi qua `POST /api/v1/billing/webhooks/{gateway}`; body bytes nguyên gốc được chuyển cho adapter để xác minh chữ ký, không parse rồi serialize lại. Webhook chỉ nhận chữ ký provider/sandbox, không dùng cookie.

Lỗi auth giữ phân biệt 401 (session), 403 (role hoặc đổi mật khẩu bắt buộc), 404 (tài nguyên không tồn tại), 409 (preview cũ hoặc xung đột), 422 (lỗi nghiệp vụ); lockout là 429. API không trả secret key, nonce, token digest, chữ ký license hay payload nhà cung cấp.
