# SCRUM-66 — Phạm vi và quyền thực hiện

Ngày 15/10/2026. Người dùng giao SCRUM-66 cùng branch và các work package T02.1–T02.7, tiếp nối yêu cầu hoàn thành các task W5. Phân công đã được yêu cầu: Codex viết prompt và review; Luna triển khai; tạo PR sau khi kiểm tra kỹ thuật. Quyền này áp dụng cho task hiện tại, không thay thế nghiệm thu của Nguyên/Sang hoặc approval SDD cấp module.

Branch người dùng ban đầu ở `9968abc`, chưa có T01. Local branch được fast-forward đến `b2b573fce8da5ce679fbfc034c91b8f0aed3e7f0`, head PR #36 đang mở, để sử dụng schema v9 và providers. Không merge PR #36 hoặc main. Nếu PR #36 còn mở, PR T02 lấy branch T01 làm base để reviewer thấy riêng diff identity.

Hai revision tham chiếu W5: historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; bản Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`. Actual implementation base T02 là `b2b573f`, khác với historical target; không cập nhật bản Sang giữa tuần.

Google bị tắt mặc định. Optional dependency `cryptography` phục vụ xác minh RS256/JWKS, được cài cho dev để kiểm chữ ký thật bằng fixture offline. Không cấu hình OAuth production, gọi Google thật, lưu PII hoặc commit secret. Giữ nguyên checksum migration v9. Việc tạo PR đã được người dùng cho phép; không tự merge hoặc chuyển Jira DONE.

Cập nhật kiểm tra remote: PR #36 đã merge lúc `2026-10-15T04:42:50Z`, main `840efb9`. Tree main bằng tree baseline `b2b573f`; PR SCRUM-66 lấy `main` làm base trực tiếp.
