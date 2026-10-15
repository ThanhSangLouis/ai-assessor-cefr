# SCRUM-66 account/session/consent lane report

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

**Scope:** W5-T02.1–T02.7 account, profile, password, session, admin and consent behavior. The migration schema remains v9; SQL migrations and checksums were not changed.

## Implemented contract

- `AccountService(auth, repository)` exposes `get_profile(token)`, `update_profile(token, ProfileUpdate | None, **fields)`, `change_password(token, current_password, new_password)`, `list_sessions(token)`, `revoke_session(token, session_id)`, `revoke_other_sessions(token)`, `activity(token, limit=50, offset=0)`, `create_accounts(token, list[AccountCreate])`, `create_legacy_account(token, actor_id, role, password)`, `change_legacy_account(token, target_id, disabled, unlock)`, `admin_action(token, target_id, action, role=None)`, `consent(token)`, and `set_consent(token, version, research_allowed, active=True)`.
- DTOs live in `aicefr.auth.contracts`: `AccountCreate(actor_id, role, goal=None)`, `ProfileUpdate(goal, icon, color)` with omission tracking, `AccountProfile`, `AdminAccount`, `PublicSession`, `ActivityItem`, and `CreatedAccount`. `CreatedAccount.temporary_password` is omitted from `repr`.
- Exported errors live in `aicefr.auth.errors`; every error has a stable `.code`, and lockout errors expose `retry_after`.
- `IdentityRepository(store)` owns v9-backed account/profile/session/activity/consent operations. Auth receives it as `identity_repository=` and exposes `resolve(token, allow_temporary=False)` and `issue_session(actor_id, method="google")` for integration.

## Security and persistence behavior

Profile accepts only goal, icon and color. Goals are exact integers in `{1, 2, 3, 5, 10}`; the boolean-as-integer case is rejected. Icon and color values must belong to explicit safe catalogs. No alias/name/email/photo/free-text profile field is accepted. Updates distinguish omitted fields from explicit null clearing and write a fixed `profile_updated` audit/activity record.

Passwords require at least 8 characters and at most 72 UTF-8 bytes; current-password and actor-ID reuse are denied. Rotation checks the old password in service code, then repository transactionally rechecks active account, current session and expected hash (CAS) before replacing the hash, removing the temp gate, revoking old sessions and issuing a new opaque token. Temporary passwords are one-time responses; expiry does not clear the permanent password-change gate. Expired temporary credentials require admin reset. Temp accounts are restricted to safe profile read, password rotation and logout paths.

Admin password reset, single/batch create, and admin state mutations carry the authorizing token digest into their repository transaction and recheck that the session is still active, unexpired, role-matched, and belongs to an enabled admin after expensive hashing. `AuthService.resolve` refreshes an existing live session with an UPDATE-only `touch_session`; a concurrent revocation causes authorization failure instead of an UPSERT recreating the row. Login stores only a coarse device value (`desktop`, `mobile`, `tablet`, or `unknown`); unknown/raw user-agent input is normalized to `unknown`, and password rotation preserves only that enum.

Login lockout counters commit before a failed-login exception is raised. Existing aliases get success/failure activity, including known disabled/locked aliases; unknown aliases are not recorded. Admin bulk create is bounded to 1–200 rows and inserts accounts, profiles, temp hashes, audit and activity in one transaction. Passwords are stored only as hashes. Role changes, disable and reset revoke sessions; self disable/reset/role/revoke-all/unlink are prohibited. Admin-only listings include disabled and lockout state without hashes.

Session identifiers are domain-separated opaque public identifiers, never token digests. Listings filter on the minimum of idle, absolute and metadata expiry. Individual foreign/expired IDs return not-found. Security mutations write fixed-safe audit/activity values. Consent updates append `consent_events`; withdrawal and research opt-out mark study enrollments withdrawn and void OPEN/SUBMITTED rating assignments transactionally. Immutable `research_ratings` rows are retained. Re-opt-in changes current consent/export eligibility but does not restore withdrawn enrollment or void assignments.

## Verification

Executed from the SCRUM-66 worktree with the configured project virtualenv:

```text
ruff format tests/auth/test_w5_accounts.py tests/auth/test_w5_consent.py tests/storage/test_identity_repository.py
ruff check src/aicefr/auth/accounts.py src/aicefr/auth/contracts.py src/aicefr/auth/errors.py src/aicefr/auth/service.py src/aicefr/storage/identity.py tests/auth/test_w5_accounts.py tests/auth/test_w5_consent.py tests/storage/test_identity_repository.py
PYTHONPATH=src python -m pytest -q tests/auth/test_w5_accounts.py tests/auth/test_w5_consent.py tests/storage/test_identity_repository.py
```

Results: formatting left all three test files unchanged; Ruff passed; focused tests passed (**9 passed**). Coverage was measured using isolated `/tmp/.coverage-scrum66-final` and `--cov-branch` on those focused tests only:

| Module | Line coverage | Branch coverage |
| --- | ---: | ---: |
| `auth/accounts.py` | 88.3% (128/145 statements) | 66.7% (24/36 branches covered) |
| `auth/service.py` | 70.7% (118/167 statements) | 85.7% (48/56 branches covered) |
| `storage/identity.py` | 74.2% (222/299 statements) | 76.6% (98/128 branches covered) |

These earlier lane-only figures were superseded by the final AccountService coverage run below. Root's broader pre-final run reported `AuthService` 94.0% line / 89.3% branch, `AccountService` 90.34% line / 69.44% branch, and `IdentityRepository` 79.26% line / 58.59% branch. The added direct security tests bring AccountService above its 90% line / 85% branch targets.

The focused batch rollback test triggers a real SQLite failure on the second profile insert and confirms no account, profile, temporary-password, audit or activity row from either new account survives. Consent tests similarly inject a mid-transaction event-insert failure and verify effective consent, event, audit and activity counts remain unchanged. Other focused tests cover profile allowlists and omitted/null updates, temp password expiry/gating/reset, session ownership and lockout, password-rotation CAS against an intervening revoke, reset authorization after an intervening admin-session revoke, resolve touch after a second SQLite connection revokes the session, coarse device metadata/redaction, admin self-guards/role revocation/disabled-login activity, research opt-out export exclusion, immutable ratings, and re-opt-in non-restoration.

Final AccountService-only coverage was run using separate `/tmp/.coverage-scrum66-account-security-final` across `tests/auth` and `tests/storage/test_identity_repository.py`: **57 passed**, AccountService **97.2% line (141/145 statements), 88.9% branch (32/36 branches)**. Both pure AccountService targets were met.

## Limits

The API and Google lanes provide their own route and OAuth tests. Google compatibility tests cover v4-to-v9 preservation. A focused coverage run leaves a few defensive AccountService branches, unusual session-expiry/metadata combinations, repository admin edge cases, and legacy `ConsentService` memory paths uncovered. No production OAuth configuration, UI redesign, deployment, commit or push was performed.
