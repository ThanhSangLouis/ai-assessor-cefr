# M11 — Research và Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT.
Nguồn: Sang `40907cc` D028/D029/D036; target M08 auth/storage hiện hành.

| REF-ID | Pattern | Target decision |
| --- | --- | --- |
| M11-REF-01 | account/password/session repositories | ADAPT vào service/repository target, Argon2 hiện hành |
| M11-REF-02 | profile allowlist | ADOPT business invariant, đổi schema/API names theo target |
| M11-REF-03 | Google PKCE/signed cookie/subject hash | ADAPT; thêm issuer/audience/expiry/nonce verification rõ |
| M11-REF-04 | admin account operations | ADAPT với transaction/audit M08 |
| M11-REF-05 | account UI bốn tab | INSPIRE; M15 design system quyết định presentation |

Rủi ro: account enumeration, cookie injection/login CSRF, role escalation, secret exposure, partial batch, session còn sống sau security mutation. Mọi failure phải dùng thông báo chung và audit chỉ cho alias tồn tại.
