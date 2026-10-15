# SCRUM-65 jobs/worker lane report

**Prompt:** SCRUM-65-jobs-A1
**Scope:** M16-TASK-001–003 jobs/worker fencing portion
**Baseline:** branch base `9968abcac29efdf81e2c9eb57302a842b396f409`
**Status:** implementation evidence for independent review; no approval or completion verdict.

## Changes

- Added `SQLiteJobRepository` and typed `Job` records over the shared `durable_jobs` schema. Enqueue is idempotent and capacity checking is atomic; claims use `BEGIN IMMEDIATE` plus revision CAS. Heartbeat, complete, and fail require owner, revision, and an unexpired lease. Retry limits and exponential delay are bounded.
- Recovery only touches expired leases. It reconciles a committed terminal response to a succeeded job, requeues expired `RUNNING` responses with a revision bump, retries a crash before response claim while the response stays `QUEUED`, and marks exhausted work failed once. Startup and polling discover queued responses with no job.
- Reworked `BackgroundPipeline` to own a runtime/SQLite connection in its worker thread, renew leases on a separately created connection, reload runtime configuration between jobs, expose sanitized `health()`/`ready`, and join worker/heartbeat threads during shutdown. Initialization and heartbeat logs expose bounded exception types only.
- Added `PipelineCoordinator.set_commit_guard()`. Durable claims are fenced in the same transaction as the response claim, and guards run before report, status, candidate, reject, and failure writes. A stale or expired worker cannot follow a newer response revision to mark it failed. The no-guard synchronous path still marks its own pipeline failures and no longer retries a stale CAS against a newer revision.
- Adapted the existing worker-window tests to durable queue semantics and changed the prior stale-CAS regression to assert the successor revision remains untouched.

## Changed files

- `src/aicefr/storage/jobs.py`
- `src/aicefr/local/worker.py`
- `src/aicefr/pipeline/coordinator.py`
- `tests/storage/test_jobs.py`
- `tests/local/test_durable_worker.py`
- `tests/portal/test_windows_worker.py`
- `tests/pipeline/test_coordinator.py` (specific regression authorized by root)

## Verification

Command:

```text
PYTHONPATH=src AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models /home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/pytest -q tests/storage/test_jobs.py tests/local/test_durable_worker.py tests/portal/test_windows_worker.py tests/pipeline/test_coordinator.py
```

Result after heartbeat, retry, stale-owner, restart, and durable-exception coverage was added: **44 passed**. Ruff check passed for all lane source and test files.

Coverage includes duplicate enqueue, owner/revision/lease checks, an active-lease no-claim case, two SQLite connections racing to claim, stale heartbeat/completion/failure refusal, lease renewal during a blocked pipeline, transient retry after backoff, max-attempt terminal failure, lease expiry after worker startup, crash before response claim, bounded attempts, recovery after terminal persistence across SQLite restart, startup health failure without traceback/path disclosure, and real `PipelineCoordinator` stale takeover and late-exception paths proving one report and one terminal audit.

## Contract and limitations

`BackgroundPipeline(store, factory, capacity=...)` remains compatible; optional `lease_seconds`, `max_attempts`, and `backoff_seconds` tune durable work. The worker exposes a boolean `health()` method and `ready` property. The runtime control must not reset durable-linked `RUNNING` rows before lease recovery. The migration lane owns schema creation and currently provides `durable_jobs` with the shared fields/checks/indexes.

Tests use synthetic data and temporary SQLite files. Full repository suite/coverage and final cross-lane integration review remain with root. No real model, external service, commit, or push was used.
