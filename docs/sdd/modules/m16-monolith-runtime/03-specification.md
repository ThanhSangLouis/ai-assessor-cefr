# M16 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Runtime topology

One Python application exposes WSGI pages/API and owns a local worker lifecycle. Both use repository interfaces over one SQLite file; separate connections, WAL/busy timeout/short transactions as approved. Blob/model/config paths live outside repo. Domain services never import templates or open database directly.

## Job contract

```text
Job(job_id, response_id, kind, state, attempt, max_attempts,
    lease_owner, lease_until, idempotency_key, schema_version,
    created_at, updated_at, last_reason)
```

Claim is atomic; heartbeat/complete/fail uses owner+revision CAS. Retry only retryable reasons with bounded backoff. Final result uniqueness is enforced in database. Startup recovers expired leases, not active ones.

## Migration contract

Migration has version/name/precondition/apply/verify; runs under exclusive migration lock after backup manifest. No destructive drop in W5. App refuses to serve if schema newer/partial/verification failed. Test covers from current schema and fresh install.

## Data operations

Export manifest names schema/version/count/hash and excludes secrets/session/password hashes. Erasure is preview token → confirm → transactional rows + cleanup intent for blobs. Retention defaults dry-run. Backup includes SQLite snapshot, blobs/lesson media and checksummed manifest; restore smoke boots and reads old/new reports.

## Health/errors/packaging

`/live` no dependency detail; `/ready` returns component status codes without paths. Error body follows W5 plan. Setuptools package data explicitly includes templates/CSS/JS/SVG/WOFF2/license/migrations. Clean install uses no source-tree lookup.
