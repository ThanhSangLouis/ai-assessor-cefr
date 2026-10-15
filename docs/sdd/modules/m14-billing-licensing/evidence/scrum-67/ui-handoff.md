# Bàn giao UI quản trị — SCRUM-67

UI quản trị có thể gọi các hợp đồng trong `data-api-contract.md`. Billing overview trả kế hoạch, entitlement đã chiếu an toàn, trạng thái gateway và license metadata. Báo giá có `effective_at`, `ends_at`, `change_kind` để UI hiển thị thời điểm nâng/hạ gói hoặc gia hạn đã xếp hàng; payload snapshot entitlement nội bộ không được gửi ra.

Luồng sandbox cơ bản: đọc overview → tạo quote bằng khóa idempotency → tạo order bằng gateway sandbox/internal → settle sandbox có khóa idempotency → đọc receipt. UI cần trình bày rõ đây là sandbox; URL/metadata từ provider chỉ được hiện qua DTO allowlist. Việc webhook lặp là idempotent. Người không phải admin không được thấy thao tác quản trị.

Data controls: export cá nhân là thao tác người dùng; xóa tài khoản yêu cầu preview rồi xác nhận đúng fingerprint, với cảnh báo khi preview hết hạn; retention hiển thị dry-run trước khi áp dụng; backup trả ID và manifest tóm tắt; restore chỉ chọn backup có sẵn và tạo bản khôi phục kiểm tra riêng. UI không yêu cầu hay hiển thị đường dẫn máy chủ, khóa, nonce, token hoặc nội dung research bị làm mù.

Phần này bàn giao hợp đồng/backend cho lane UI; không xác nhận QA trình duyệt hoặc trải nghiệm giao diện.
