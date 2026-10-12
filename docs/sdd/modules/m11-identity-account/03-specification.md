# M11 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Services

- `AccountService`: profile/password/activity/data summary.
- `SessionService`: issue/rotate/list/revoke/touch; cookie HttpOnly/SameSite, Secure theo TLS.
- `AdminAccountService`: atomic create/batch/security/role actions với self-action guard.
- `GoogleIdentityService`: create signed flow, exchange/validate ID token, link/login/unlink.
- `ConsentService`: append-only consent event và effective state.

## Storage

Mở rộng account/profile, `auth_session(device, method, created_at, last_seen_at, expires_at, revoked_at)`, `account_identity(provider, subject_hash)`, `server_secret(name, value_encrypted_or_local_protected)`, consent event và audit. Unique provider+subject; session token chỉ lưu hash; migration không làm mất session/consent M08.

## API

- `/api/v1/me`, `/profile`, `/password`, `/sessions`, `/activity`, `/google`, `/consent`.
- `/api/v1/admin/accounts` single/batch/list/detail và action subroutes.
- `/auth/google/start`, `/callback`; browser cookie flow không được đưa verifier/token vào URL/log.

Error semantics: foreign session 404; self-prohibited admin action/stale role 409; policy validation 422; lockout 429; Google disabled/config error 503 hoặc user-safe disabled state.

## Google validation order

Verify signed flow + max age → state → exchange HTTPS adapter → signature/JWKS policy or injected verifier → issuer/audience/expiry/nonce/domain → subject hash lookup → account active → rotate session. Link additionally requires current session and flow account ID match.

## UI

Tab Hồ sơ, Bảo mật, Hoạt động, Dữ liệu; staff không thấy student-only goal nếu không áp dụng. Sensitive confirm dialog; password/temp-password print không còn trong DOM sau close/refresh. Google disabled state nêu missing setup nhưng không secret.
