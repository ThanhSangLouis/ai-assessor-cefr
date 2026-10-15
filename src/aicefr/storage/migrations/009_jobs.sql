CREATE TABLE durable_jobs (
 job_id TEXT PRIMARY KEY,
 response_id TEXT NOT NULL UNIQUE REFERENCES responses(response_id) ON DELETE CASCADE,
 kind TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','failed')),
 attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt>=0),
 max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts>0),
 lease_owner TEXT,
 lease_until REAL,
 idempotency_key TEXT NOT NULL UNIQUE,
 schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version>0),
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 available_at REAL NOT NULL,
 last_reason TEXT,
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
 CHECK(attempt<=max_attempts),
 CHECK((state='running' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR (state!='running' AND lease_owner IS NULL AND lease_until IS NULL)),
 CHECK(state NOT IN ('succeeded','failed') OR attempt>0)
);
CREATE INDEX durable_jobs_queue_idx ON durable_jobs(state,available_at,created_at) WHERE state='queued';
CREATE INDEX durable_jobs_lease_idx ON durable_jobs(lease_until) WHERE state='running';
CREATE TABLE cleanup_intents (
 intent_id TEXT PRIMARY KEY, owner_id TEXT REFERENCES accounts(actor_id) ON DELETE SET NULL,
 resource_kind TEXT NOT NULL, resource_id TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','running','complete','failed')),
 attempt INTEGER NOT NULL DEFAULT 0 CHECK(attempt>=0), available_at REAL NOT NULL,
 created_at REAL NOT NULL, updated_at REAL NOT NULL, last_reason TEXT,
 UNIQUE(resource_kind,resource_id)
);
CREATE INDEX cleanup_intents_queue_idx ON cleanup_intents(state,available_at,created_at) WHERE state IN ('pending','failed');
