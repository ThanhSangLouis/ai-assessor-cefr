# SCRUM-65 migration and provider lane report

**Prompt:** `SCRUM-65-migrations-A1`
**Branch:** `feat/SCRUM-65-W5-T01-Monolith-foundation-SQLite-migration-va-worker`
**Base:** `9968abcac29efdf81e2c9eb57302a842b396f409`
**Result:** implementation submitted for root review; no task completion or user acceptance claimed.

## Changed files

- `src/aicefr/storage/sqlite.py`
- `src/aicefr/storage/migrations.py`
- `src/aicefr/storage/migrations/005_identity.sql`
- `src/aicefr/storage/migrations/006_learning.sql`
- `src/aicefr/storage/migrations/007_research.sql`
- `src/aicefr/storage/migrations/008_billing.sql`
- `src/aicefr/storage/migrations/009_jobs.sql`
- `src/aicefr/storage/providers.py`
- `tests/storage/test_w5_storage_foundation.py`
- Existing schema version assertions updated in `test_report_migration.py`, `test_sqlite_blob_store.py`, and `test_sqlite_memory_migration.py`.

## Implementation

`SQLiteStore` now reaches schema v9 and revalidates the migration ledger and complete W5 table/index/trigger shape on each open. The v4-to-v9 migration runs five additive SQL groups under one OS migration lock and transaction. The lock also serializes legacy v1-to-v4 initialization, uses a bounded 5-second wait, and selects `fcntl` or `msvcrt` by platform. SQLite foreign keys and a 5-second busy timeout are enabled at the store boundary.

The v4 pre-migration backup contains a SQLite snapshot, copied blobs, and a SHA-256 manifest under private filesystem permissions. Backup creation rejects symlinks and does not replace existing snapshots. `restore_backup` verifies manifest paths and file inventory, requires the database entry, rejects symlinks and destinations inside/overlapping the source, verifies checksums, and restores to a private new directory.

The five schema groups add identity profiles and side tables; learning paths, immutable lesson versions/steps and effort attempts; blind ratings, studies and research records; billing quotes/orders/receipts/licenses/entitlements; and the durable job/cleanup-intent contract. Existing `sessions` and `responses` shapes are retained. Profile goals are constrained to the allowlist and icon/color fields to bounded identifiers. Consent events, published lesson content, and research ratings have append-only/immutability guards. Schema verification normalizes whitespace while preserving the exact case and spacing inside quoted SQL literals.

`build_providers(store)` returns typed repositories for profiles, learning, ratings, research, billing, and cleanup. Repository methods use parameterized SQL, bounded list limits, and the injected store connection.

## Checks run

Environment: Python and Ruff from `/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv`; `PYTHONPATH=src`; model directory configured outside the repository. Tests use temporary SQLite files and fixture data.

- `python -m pytest -q tests/storage/test_w5_storage_foundation.py` — **16 passed**.
- `python -m pytest -q tests/storage` — **41 passed**.
- `ruff check src/aicefr/storage tests/storage` — **passed**.
- `ruff format --check src/aicefr/storage tests/storage` — **passed**.

Covered cases include all five injected migration group failures and v4 rollback, v4-to-v9 preservation of account/session/consent/response/report/audit/config and blob bytes, backup restore smoke, rerun stability, schema table/index/trigger/column/ledger and case-sensitive CHECK literal tampering, foreign keys and uniqueness, immutable/append-only constraints, bounded providers, symlink/path traversal rejection, and concurrent fresh initializers.

## Limits

No real database, audio, model, external service, network, or payment gateway was used. The full project suite, package build, and application/browser checks were not run by this lane. Root integration and review remain outstanding; provider API and SQL asset packaging must be checked on the integrated revision.
