# M11 — Identity and Account Experience — Requirement

**SCOPE ID:** M11 · **TYPE:** module · **OWNER:** Thắng
**ROOT:** `docs/sdd/modules/m11-identity-account/` · **VERSION:** v0.1 · **STATUS:** DRAFT
**RELATED:** M01, M07, M08, M10, M12–M16
**RESEARCH MODE:** `RUN` đề xuất — security/OIDC và adaptation D028/D029/D036 cần evidence.
**USER VERDICT:** PENDING

M11 mở rộng trải nghiệm account trên contract M08 nhưng không sửa lịch sử nghiệm thu của M08. M08 vẫn là dependency lưu trữ/quyền W2; M11 sở hữu requirement W5 mới.

## Requirements

- **M11-FR-001:** profile chỉ có avatar icon/color và speaking goal 1/2/3/5/10 phút; không tên thật/ảnh/email.
- **M11-FR-002:** đổi password với current password, policy 8 ký tự/72 byte/khác alias/password cũ; revoke các session khác.
- **M11-FR-003:** temporary password chỉ mở được luồng đổi password; lockout 5 lần/15 phút; session tối đa 8 giờ.
- **M11-FR-004:** người dùng xem session/activity, revoke một session hoặc tất cả session khác; current session được nhận diện.
- **M11-FR-005:** admin tạo single/batch ≤200 atomic, reset/unlock/enable-disable/change role/revoke/unlink; không tự thao tác nguy hiểm.
- **M11-FR-006:** Google Authorization Code + PKCE S256/state/nonce/signed flow cookie; chỉ linked account, không auto-signup/role, chỉ lưu subject hash.
- **M11-FR-007:** admin thấy trạng thái cấu hình/redirect/scopes/domain/missing fields; secret chỉ có boolean đã đặt.
- **M11-FR-008:** consent version, research opt-in riêng và withdrawal propagation; audit không chứa credential/PII.

## Acceptance Criteria

- **M11-AC-001:** profile invalid bị 422; payload/database không có trường PII tự do.
- **M11-AC-002:** password/session/lockout/temp-password đúng policy và chống session fixation.
- **M11-AC-003:** batch lỗi một dòng rollback toàn bộ; password tạm hiện một lần; admin không tự hạ role/tắt/reset/revoke-all.
- **M11-AC-004:** forged/stale OAuth flow, state/nonce/issuer/audience/domain sai đều fail closed trước khi tạo session/link.
- **M11-AC-005:** duplicate Google subject không thể link hai alias; disabled account không đăng nhập Google.
- **M11-AC-006:** client secret/hash/token/password không xuất hiện trong API, DOM, log, export hoặc audit.
- **M11-AC-007:** withdraw research consent loại participant khỏi study/rating export theo dependency nhưng vẫn giữ quyền dữ liệu cá nhân.
- **M11-AC-008:** account journey bốn tab chạy desktop/mobile, keyboard/focus/error/recovery đầy đủ.

## Out of scope

Self-registration, password reset qua email/SMS, lưu email Google, SSO trường/LDAP, social profile, production OAuth setup/deploy.

## Open decisions

Xác nhận Google chỉ là optional; localhost HTTP được phép cho dev, HTTPS bắt buộc `__Host-`; theme/font lưu client còn profile/goal lưu server.
