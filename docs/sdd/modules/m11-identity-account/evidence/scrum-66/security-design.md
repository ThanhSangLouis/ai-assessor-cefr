# SCRUM-66 — Quyết định security

Hai revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

Google dùng authorization code với PKCE S256, state, nonce và flow cookie có HMAC. Flow link bị ràng buộc với account và session ban đầu; callback kiểm lại phiên sau round trip. Reservation hash trong SQLite chặn replay qua restart; không lưu code, verifier, ID token hoặc thông tin Google nhận dạng cá nhân. Identity chỉ lưu subject hash.

ID token phải được kiểm chữ ký RS256 bằng JWKS từ endpoint Google cố định, sau đó kiểm issuer, audience, azp, expiry, issued-at và nonce. Không chấp nhận alg none/HS256, URL khóa do token cung cấp hoặc JSON trùng key. Transport có timeout, giới hạn response và chặn redirect. Test dùng RSA key và provider fixture offline. OAuth Google thực tế: **NOT_RUN**, cần credential môi trường riêng và review user flow của Nguyên.

Nguồn thiết kế: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect), [OpenID Core ID token validation](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation), [RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636), [cryptography RSA](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/). `cryptography` dùng license Apache-2.0 hoặc BSD theo [tài liệu license](https://cryptography.io/en/latest/faq/#what-license-is-cryptography-distributed-under); không có D043 dependency được thêm.

Profile chỉ nhận các field allowlist. API session chỉ trả opaque public ID được domain-separate từ digest; không trả token/digest. Password mới quay session và thu hồi các phiên khác; password tạm chỉ được dùng cho journey bắt buộc đổi. Batch admin tối đa 200 account trong transaction, chặn self-action nguy hiểm. Route admin cũ phải đi qua cùng policy; fixture bootstrap CLI không trở thành đường public signup.

Withdraw consent và research opt-out giữ event/version, cập nhật quyền nghiên cứu, study enrollment và rating assignment trong cùng transaction. Export tiếp tục kiểm consent hiện hành, không coi lịch sử nghiên cứu là quyền truy cập còn hiệu lực.
