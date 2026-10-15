# Handoff cho giao diện identity/account — SCRUM-66

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

Adapter backend đã có thể được UI gọi trực tiếp. Phạm vi này cung cấp hợp đồng, không thay đổi bố cục/luồng bốn tab theo N01/N04; phần giao diện thuộc lane Nguyên. Không đưa tên/email vào hồ sơ: `actor_id` hiện là mã giả danh và payload profile từ chối field lạ.

## Cách dựng trạng thái trang

Gọi `GET /api/v1/me` sau khi phiên được tạo. Response có `profile` và `catalog`; dùng catalog này để dựng dropdown/icon/color thay vì hard-code danh sách. Profile hiện có `actor_id`, `goal`, `icon`, `color`, `temporary_password_required`, `revision`. Có 15 icon: `bird`, `book`, `cat`, `cloud`, `flower`, `fox`, `leaf`, `mountain`, `moon`, `owl`, `pencil`, `rocket`, `star`, `sun`, `wave`. Có 10 màu: `blue`, `gray`, `green`, `indigo`, `orange`, `pink`, `purple`, `red`, `teal`, `yellow`. Goal hợp lệ: `1, 2, 3, 5, 10`.

Khi `temporary_password_required=true`, hiển thị luồng bắt buộc `/password-change` hoặc form dùng `POST /api/v1/me/password`, sau đó tải lại `/api/v1/me`. Business API trả `403 PASSWORD_CHANGE_REQUIRED` trong thời gian này. Mật khẩu mới phải được gửi qua TLS; client không lưu mật khẩu hay session token vào local storage.

## Các thao tác UI

- Hồ sơ: GET `/api/v1/me/profile`; PATCH cùng endpoint với một phần `{goal?, icon?, color?}`. Gửi Origin cùng origin.
- Phiên: GET `/api/v1/me/sessions`, DELETE `/api/v1/me/sessions/{session_id}`, POST `/api/v1/me/sessions/revoke-others`. Hiển thị thiết bị/ngày từ DTO; session ID chỉ dùng để revoke.
- Hoạt động: GET `/api/v1/me/activity?limit=50&offset=0`.
- Consent: GET/POST `/api/v1/me/consent`; rút consent bằng POST `{version, research_allowed:false, active:false}`.
- Google: GET `/api/v1/me/google`; nối bằng POST `/auth/google/start?intent=link`; unlink bằng POST `/api/v1/me/google`. Nếu API trả `503 GOOGLE_UNAVAILABLE`, hiển thị trạng thái chưa cấu hình, không chặn trang tài khoản.
- Admin: GET/POST `/api/v1/admin/accounts`; admin actions POST `/api/v1/admin/accounts/{actor_id}/{action}`. Tạo/reset trả mật khẩu tạm một lần để admin chuyển an toàn cho người dùng; không render lại sau điều hướng và không log.

## Xử lý lỗi cho UI

`401 SESSION_REQUIRED` chuyển về đăng nhập. `403 ACCESS_DENIED` ẩn/báo quyền không đủ; `403 PASSWORD_CHANGE_REQUIRED` điều hướng đổi mật khẩu. `404 RESOURCE_UNAVAILABLE` cho tài nguyên/phiên không thuộc người gọi, không tiết lộ chủ sở hữu. `409 SELF_ACTION_PROHIBITED` hoặc duplicate hiển thị hành động không thực hiện được. `422 INVALID_REQUEST` giữ form và chỉ hiển thị lỗi chung/trường an toàn. `429 LOGIN_LOCKED` dùng `Retry-After`. `503 GOOGLE_UNAVAILABLE` hiển thị Google chưa khả dụng.

Không cần Bearer token trong browser: cookie HttpOnly được trình duyệt gửi tự động. Với mutation cookie, Origin phải khớp origin hiện tại; không bỏ qua lỗi CSRF bằng cách retry GET. Session HTTPS dùng `__Host-aicefr_session` Secure/HttpOnly/SameSite=Lax/Path=/; Google flow tương tự dùng `__Host-aicefr_google_flow` trong HTTPS. Môi trường HTTP loopback chỉ dành cho phát triển.
