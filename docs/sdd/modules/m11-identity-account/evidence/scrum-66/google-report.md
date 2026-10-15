# SCRUM-66 Google identity lane — raw implementation report

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

**Prompt:** `SCRUM-66-google-A1`  
**Workspace fingerprint:** `d66d2836052ce56f8067c635e3e2f4021eb9aa545bcb6b1f83664310ecb8f4e1`  
**Base:** `b2b573f` (SCRUM-65 / PR #36 branch)  
**Scope:** Google identity service, fixed HTTPS transport, v9 storage adapter, offline security tests.

## Changes

- Added `GoogleConfig`, `GoogleIdentityService`, safe result/error types, and `GoogleIdentityService.is_linked(token)`. Configuration is disabled by default. Status exposes only readiness, redirect, openid scope, optional domain, missing fields, and whether a client secret is set.
- Added Authorization Code + PKCE S256 with state, nonce, a 10-minute HMAC-signed flow cookie, and a one-time hashed state reservation in `runtime_settings`. Link flows bind to the original actor and session; the session is checked again after provider exchange. State is consumed before the token request to serialize concurrent callbacks.
- Added fixed Google token and JWKS HTTPS endpoints, TLS certificate verification, redirect refusal, five-second timeout, 256 KiB JWKS and bounded token-response reads. RS256 signature verification uses `cryptography`; the optional dependency is checked at runtime so a base installation with Google disabled does not require it. JWKS are cached for five minutes and refreshed once for an unknown key ID.
- Validates the signed JWT header and signature, issuer, single trusted audience, optional authorized party, expiry, issue time, nonce, subject, and configured hosted domain. Login requires an existing subject link and creates the session via `AuthService.issue_session`; no account creation or role claim is accepted. Auth lockout exceptions remain lockout responses.
- Added `GoogleIdentityRepository` on the existing v9 tables. It stores only a domain-separated SHA-256 subject hash, creates audit/activity records on link changes, and removes expired flow reservations. HMAC key material lives in an external data directory file with mode `0600`, checked for regular-file type, owner, link count, and symlink refusal.
- Added offline tests with locally generated RSA keys, valid signed synthetic JWTs, and injected transport. No call to Google or other network service was made.

## Verification

Command:

```text
PYTHONPATH=src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check src/aicefr/auth/google.py src/aicefr/auth/google_transport.py src/aicefr/storage/google_identity.py tests/auth/test_google_identity.py tests/auth/test_google_transport.py
```

Result: **PASS**, all checks passed.

Command:

```text
PYTHONPATH=src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/python -m pytest tests/auth/test_google_identity.py tests/auth/test_google_transport.py --cov=aicefr.auth.google --cov=aicefr.auth.google_transport --cov=aicefr.storage.google_identity --cov-branch --cov-report=term-missing -q
```

Result: **PASS**, 36 passed. Coverage: Google service 91.2% lines / 86.2% branches; HTTPS transport 97.4% / 94.4%; Google storage adapter 100% / 100%. The combined report was 93% line-plus-branch coverage.

The cases cover successful linked login and link/unlink; PKCE S256 and `openid` scope; invalid state, code, cookie, stale/replayed flow; cross-connection single-consume behavior; actor/session link binding and post-exchange recheck; duplicate subject; disabled account; lockout; malformed and tampered JWTs; issuer/audience/`azp`/expiry/`iat`/nonce/domain rejection; missing linked identity; client-secret and subject-hash storage scans; unsafe/missing key files; fixed endpoint, redirect, timeout, body-size, and duplicate-JSON transport behavior; and provider exception redaction.

## Boundaries and limitations

- Real Google OAuth, live JWKS retrieval, browser navigation, configured production credentials, and deploy were **NOT_RUN**.
- The focused lane tests use synthetic local RSA signing keys and fake HTTPS transport. The root/API lane owns route cookie attributes, CSRF/origin checks, and adapter wiring; root is running the full independent suite.
- Schema remains v9; no migration or checksum was changed. No real user/account data or provider credentials were used.
