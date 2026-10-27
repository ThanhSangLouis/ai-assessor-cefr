# M08 — 06 Tasks

> W2 v0.3 · 28/09/2026. Thắng approved implementing and pushing the four task branches on 28/09/2026; M01/M07 owner review remains PENDING.

| Task | Branch | Owner | Dependency | Test IDs |
| --- | --- | --- | --- | --- |
| M08-TASK-001 / SCRUM-48 | `feat/SCRUM-48-M08-TASK-001-Auth-consent-va-kiểm-tra-owner` | Thắng | Phase 01/03/04/05 approved | M08-TEST-001, 002, 004, 005 |
| M08-TASK-002 / SCRUM-49 | `feat/SCRUM-49-M08-TASK-002-SQLite-BlobStore-persistence-va-audit` | Thắng | SCRUM-48 typed interfaces | M08-TEST-001, 002, 003, 005 |

## SCRUM-48 — Auth, consent and owner

Implement typed Actor, SessionRecord and ConsentRecord; Argon2id fixture account bootstrap; opaque session token with digest-only repository, 30-minute idle and 8-hour absolute expiry; consent activate/withdraw/require-active; and generic owner authorization error. Scope: `src/aicefr/auth/**`, M08 auth additions to `src/aicefr/contracts.py`, `pyproject.toml`, `tests/auth/**` and `tests/storage/test_authorization.py`.

## SCRUM-49 — SQLite, BlobStore and audit

Implement versioned SQLite schema/repositories, persistent sessions/consent/response/audit, bounded immutable blobs, same-filesystem staging, SHA-256 verification, compensation after DB failure, and report-only orphan reconciliation. Scope: `src/aicefr/storage/**`, `src/aicefr/infra/**`, M08 storage additions to `src/aicefr/contracts.py`, `tests/storage/**`, M08 contract assertions in `tests/test_contracts.py`.

## Definition of Done

- All listed Test IDs run with actual PASS; SKIPPED count stated.
- Pure M08 Python logic reaches line ≥ 90% and branch ≥ 85% where measured.
- Branch/PR title includes Jira key; checks green and PR reviewed before merge.
- Only task-scoped source and synthetic fixture data; no secrets, real audio, transcript, real PII or generated DB/blob committed.
- Evidence includes commands, exit codes, coverage and revision under M08 `evidence/`.
- Cross-owner M01/M07 contract review is recorded before merge. It is currently PENDING.

## W7 — Chuyển M08 từ repo gốc (W7-T02, SCRUM-99)

| Task | Deliverable | Tests | Status |
| --- | --- | --- | --- |
| W7-T02 (M08) | `src/aicefr/auth/` (`passwords.py`, `sessions.py`, `google.py`, `pseudonyms.py`), `services/core/identity/` | `test_auth.py`, `test_consent.py`, `test_google_flow.py`, `test_security.py` | IN_REVIEW — Chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95 vào nhánh tích hợp |

