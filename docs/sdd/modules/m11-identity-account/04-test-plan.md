# M11 — Test Plan

**Version:** v0.1 · **STATUS:** DRAFT · **UT REQUIRED:** YES.

| Test ID | AC | Scenario | Expected | Level |
| --- | --- | --- | --- | --- |
| M11-TEST-001 | 001 | profile allowlist/boundary | 200/422, no free-text PII | Unit/API |
| M11-TEST-002 | 002 | password rules/wrong current/lockout/temp gate | policy, 429, only password route | Unit/integration |
| M11-TEST-003 | 002 | list/revoke/change password/disable | đúng current/other revocation, token rotation | Integration |
| M11-TEST-004 | 003 | single/batch max, duplicate/invalid middle row | atomic and one-time password | Repository/API |
| M11-TEST-005 | 003 | self admin actions/role escalation | 409/403 and audit | Security |
| M11-TEST-006 | 004/005 | PKCE/state/nonce/cookie mutation/stale/issuer/audience/domain/duplicate | fail closed, no session/link | Unit/integration |
| M11-TEST-007 | 006 | secret scan API/DOM/log/export | no credential/hash/token leakage | Security/browser |
| M11-TEST-008 | 007 | consent sign/version/withdraw propagation | effective state and downstream removal | Integration |
| M11-TEST-009 | 008 | four-tab journey desktop/mobile/keyboard | complete states/focus/recovery | Browser |
| M11-TEST-010 | Migration | pre-W5 account/session/consent | preserved and readable | Migration |

Critical auth/security branches require direct tests regardless of global coverage; pure services target line ≥90%, branch ≥85%.
