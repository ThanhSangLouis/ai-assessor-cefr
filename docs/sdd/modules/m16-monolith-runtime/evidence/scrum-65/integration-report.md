# SCRUM-65 integration lane report

**Prompt:** `SCRUM-65-integration-A1`
**Scope:** runtime DI, readiness and aliases, package data, offline clean-wheel QA harness.
**Status:** implementation and lane regression evidence recorded; final review/build remains with root.

## Changes

- `LocalRuntime` exposes `RepositoryProviders`; `create_runtime(..., repository_factory=...)` injects the provider builder. Its default is `build_providers(store)` over the existing store.
- Startup recovery excludes responses referenced by any durable job. The durable worker owns recovery for those rows, including expired leases.
- Public readiness checks expose booleans only for configuration, schema/ledger, SQLite write access, blob storage, models, and worker health. Schema ledger verification uses the packaged migration files. Blob probing does not recreate missing roots or follow a symlink. A savepoint protects any transaction already owned by the caller.
- `/live` and `/ready` are aliases; `/health`, `/healthz`, and `/readyz` remain. Readiness returns 503 when required local artifacts are missing or invalid.
- The wheel includes the SQL migration assets alongside the existing JavaScript assets. The QA harness installs a supplied wheel into a fresh venv, checks the import path, boots the actual CLI on loopback, tests login/liveness/readiness/static assets, creates a NOT_EVALUATED report without model inference, and checks that report after backup/restore.

## Validation

- `ruff check src/aicefr/local/app.py src/aicefr/portal/control.py src/aicefr/portal/router.py tests/local/test_foundation_runtime.py scripts/qa/w5_foundation_smoke.py` — PASS.
- `pytest tests/local/test_foundation_runtime.py tests/local/test_factory_integration.py -q` with the repository Python and `PYTHONPATH=src` — 7 passed.
- `pytest tests/local tests/portal -q` with `PYTHONPATH=src` — 71 passed.
- `git diff --check` on lane-owned files — PASS.
- `pip wheel --no-deps --no-build-isolation` built `aicefr-0.1.0-py3-none-any.whl` successfully. The final real CLI/HTTP harness could not complete under this lane's socket-restricted shell: `socket.socket()` returned `PermissionError: [Errno 1] Operation not permitted`. Root reported an independent clean-wheel smoke pass and will rerun the harness against the final wheel in its elevated QA environment.

Model inference was `NOT_RUN`; the wheel smoke intentionally omits ASR and scoring artifacts and verifies the no-score response path. No model weights or network access were used.
