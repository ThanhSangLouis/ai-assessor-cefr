# SCRUM-66 — v4 identity compatibility test report

Revision W5: target `3b2d2b7`, Sang `40907cc`; implementation base `b2b573f`.

**Scope:** one integration test for legacy account, session, and consent rows carried from SQLite schema v4 through the v9 migration, then reopened and used by current identity services.

The test uses the existing T01 `_make_v4` fixture in `tests/storage/test_w5_storage_foundation.py`. Before opening the v4 database through `SQLiteStore`, it replaces the fixture session with a known opaque token digest and active idle/absolute expiries. The migration upgrades the database to v9. Assertions verify the legacy password hash, role, session digest and metadata, and effective consent remain present. The current `AuthService` and `AccountService` then resolve that session, list it as current without exposing its digest, create an allowlisted profile, and append a consent event. A synthetic Google subject is linked using its SHA-256 subject hash. After close and reopen, the test verifies the profile, effective consent, event, subject hash, session, and schema version remain stable.

No source, migration SQL, or checksum was changed. No real user data was used.

## Verification

Command:

```text
PYTHONPATH=.:src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/python -m pytest tests/storage/test_identity_compatibility.py -q
```

Result: **PASS**, 1 passed.

Command:

```text
PYTHONPATH=.:src /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/ruff check tests/storage/test_identity_compatibility.py
```

Result: **PASS**.
