# M11 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

1. Freeze actor/session/consent contracts with M08/M16 and UI payload with M15.
2. Add additive migration and repository tests using real SQLite file.
3. Implement password/session/admin services with injected clock/random/password hasher.
4. Implement Google flow as ports/adapters; network adapter disabled by default and fully mockable.
5. Implement endpoints, audit/redaction and downstream consent hooks.
6. Implement account/admin UI; run security/browser regression.

Code areas: `src/aicefr/auth/`, storage repository, portal/API handler, account/admin templates/static, tests. No auth rule may exist only in JS/template. Rollback disables Google/profile extensions but preserves existing auth; migration restore uses W5-T01 backup.
