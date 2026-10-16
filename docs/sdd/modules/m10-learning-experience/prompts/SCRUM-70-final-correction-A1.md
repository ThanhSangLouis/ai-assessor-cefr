# SCRUM-70 — Final regression correction
Baseline lịch sử: 3b2d2b78ba5bb35bd162b8f3e5de21ade946d237. Tham chiếu: 40907cc35b3d04408f9a8713f16d9be99f4cd6c7. Parent: 51eff1f.
User đã yêu cầu Luna implement, Codex review và tạo PR; chỉ áp dụng quyền này cho task hiện tại, không tự duyệt SDD.

Sửa ba regression được full suite phát hiện trong tests/api/test_data_operations_api.py và tests/portal/test_w5_data_recovery.py. Đọc full-tests.log trong runtime/evidence/scrum-70-2026-10-15. Fixture phải ghi rõ column sau additive migration; tạo lesson rồi published version trước active_version; cung cấp idempotency key riêng cho các attempt độc lập. Giữ nguyên assertion bảo mật/backup/retention, không nới trigger sản phẩm chỉ để test xanh. Nếu là lỗi sản phẩm thực sự, báo Codex trước khi sửa. Chỉ sửa hai file test này, chạy targeted tests và Ruff; trả diff, lệnh, kết quả. Không commit/push.
