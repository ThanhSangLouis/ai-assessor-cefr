# Hợp đồng API identity/account — SCRUM-66

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

Tài liệu này mô tả adapter hiện tại trong `aicefr.api.identity.IdentityApi`. API dùng JSON UTF-8, cookie phiên opaque; lỗi không trả nội dung exception, password, token, Google code hay input đã gửi. JSON có key trùng bị từ chối. Body không nhận field lạ.

## Phiên và CSRF

Client web gửi cookie phiên. Với HTTP local cookie là `aicefr_session`; khi HTTPS dùng `__Host-aicefr_session; Secure; HttpOnly; SameSite=Lax; Path=/`, không có Domain. Không nhận cookie HTTP tên thường trên HTTPS. Session token không xuất hiện trong JSON. API client có thể dùng `Authorization: Bearer <opaque-session>`; các mutation từ cookie yêu cầu `Origin` cùng origin. API bearer không cần Origin.

Tài khoản mới vào được `/api/v1/me` và GET `/api/v1/me/profile` để xem trạng thái an toàn, nhưng các API cần phiên bình thường trả `403 PASSWORD_CHANGE_REQUIRED` đến khi đổi mật khẩu. Đăng nhập tài khoản mật khẩu tạm chuyển đến `/password-change`. Đổi mật khẩu thành công xoay phiên và đặt cookie mới.

## Endpoint

| Method và đường dẫn | Quyền / tác dụng |
|---|---|
| `GET /api/v1/me` | Phiên hợp lệ, kể cả đang bị yêu cầu đổi mật khẩu. Trả `profile` và `catalog`. |
| `GET /api/v1/me/profile` | Xem hồ sơ an toàn. |
| `PATCH /api/v1/me/profile` | Cập nhật `goal`, `icon`, `color`; field phải nằm trong catalog. |
| `POST /api/v1/me/password` | Body `{ "current_password": "...", "new_password": "..." }`; xoay phiên, token chỉ ở Set-Cookie. |
| `GET /api/v1/me/sessions` | Liệt kê phiên của chính tài khoản; `session_id` là ID opaque, không phải token. |
| `DELETE /api/v1/me/sessions/{session_id}` | Thu hồi phiên của chính tài khoản; ID của người khác trả 404. Thu hồi phiên hiện tại xóa cookie. |
| `POST /api/v1/me/sessions/revoke-others` | Thu hồi các phiên khác, giữ phiên hiện tại. |
| `GET /api/v1/me/activity?limit=50&offset=0` | Hoạt động của chính tài khoản; `limit` 1–100, `offset` 0–100000. |
| `GET /api/v1/me/consent` | Đọc trạng thái consent của học sinh. |
| `POST /api/v1/me/consent` | `{ "version": "...", "research_allowed": true, "active": true }`; đặt `active:false` để rút consent. |
| `GET /api/v1/me/google` | Trả `{ "linked": boolean, "enabled": boolean }`. |
| `POST /api/v1/me/google` | Hủy liên kết Google của chính tài khoản. |
| `GET /api/v1/admin/accounts` | Admin: danh sách tài khoản an toàn, gồm disabled/locked/temp-required. |
| `POST /api/v1/admin/accounts` | Admin: `{ "accounts": [{"actor_id":"...","role":"student","goal":3}] }`, tối đa 200. Trả mật khẩu tạm đúng một lần trong response. |
| `POST /api/v1/admin/accounts/{actor_id}/{action}` | Admin action: `unlock`, `disable`, `enable`, `reset`, `role`, `revoke_all`, `unlink`. `role` nhận `{ "role":"student|teacher|admin" }`. Reset trả mật khẩu tạm một lần. Self-disable/reset/role/revoke/unlink bị chặn. |
| `GET /api/v1/admin/google` | Admin: trạng thái cấu hình đã lọc bí mật; không trả client secret hay HMAC key. |
| `GET /auth/google/start` | Bắt đầu login OAuth; redirect tới provider, flow cookie HttpOnly. |
| `POST /auth/google/start?intent=link` | Bắt đầu liên kết, cùng origin và phiên đăng nhập bắt buộc. |
| `GET /auth/google/callback?state=…&code=…` | Callback chỉ nhận GET, query trùng/không hợp lệ bị từ chối; luôn xóa flow cookie. |
| `GET /password-change`, `POST /password-change` | Form đổi mật khẩu cho luồng HTML legacy; POST cùng origin, cần current/new/confirm. |

Ví dụ response profile state (catalog thực tế 15 icon, 10 màu):

```json
{
  "profile": {"actor_id":"student-42","goal":3,"icon":"book","color":"blue","temporary_password_required":false},
  "catalog": {
    "goals":[1,2,3,5,10],
    "icons":["bird","book","cat","cloud","flower","fox","leaf","mountain","moon","owl","pencil","rocket","star","sun","wave"],
    "colors":["blue","gray","green","indigo","orange","pink","purple","red","teal","yellow"]
  }
}
```

## Status và mã lỗi ổn định

| HTTP | `error` | Ý nghĩa |
|---:|---|---|
| 400 | `INVALID_REQUEST` | JSON/query sai cú pháp, trùng key hoặc query parameter. |
| 401 | `SESSION_REQUIRED` | Thiếu/hết hạn phiên. |
| 403 | `ACCESS_DENIED` | Sai vai trò; `PASSWORD_CHANGE_REQUIRED` cho tài khoản tạm. |
| 404 | `RESOURCE_UNAVAILABLE` | Không tìm thấy tài nguyên hoặc phiên không thuộc người gọi. |
| 409 | `DUPLICATE_ACCOUNT`, `SELF_ACTION_PROHIBITED`, ... | Trùng, tự khóa tài khoản hoặc xung đột nghiệp vụ. |
| 422 | `INVALID_REQUEST`, mã validation an toàn | Payload không hợp lệ/field không cho phép. |
| 429 | `LOGIN_LOCKED` | Thử lại sau; có header `Retry-After` khi lockout ở API identity. |
| 503 | `GOOGLE_UNAVAILABLE` | Google OAuth chưa sẵn sàng hoặc bị tắt. |

Mật khẩu tạm có thời hạn và chỉ trả khi admin tạo/reset. Không có route nào trả cleartext credential sau response đó. API legacy `/admin/accounts` cũng dùng cùng AccountService; tạo tài khoản từ route legacy vẫn được đánh dấu cần đổi mật khẩu, còn init fixture/CLI giữ cơ chế synthetic hiện có.

## Lưu ý lưu trữ và erasure

Erasure xóa phiên, hồ sơ, provider identity, activity và temporary-password gate. Nếu khóa ngoại lịch sử yêu cầu giữ account stub, bản ghi bị disable và `password_hash` được thay bằng chuỗi rỗng không thể xác thực; login bị từ chối. Consent event append-only và alias pseudonymous được giữ để bảo toàn lịch sử. Enrollment nghiên cứu được đánh dấu withdrawn. Google callback access log chỉ ghi method/status/size, không log path/query/code/state.
