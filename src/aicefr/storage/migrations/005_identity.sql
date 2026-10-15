CREATE TABLE account_profiles (
 account_id TEXT PRIMARY KEY REFERENCES accounts(actor_id) ON DELETE CASCADE,
 goal INTEGER CHECK(goal IS NULL OR goal IN (1,2,3,5,10)),
 icon TEXT CHECK(icon IS NULL OR (length(icon)<=32 AND icon NOT GLOB '*[^a-z0-9_-]*')),
 color TEXT CHECK(color IS NULL OR (length(color)<=32 AND color NOT GLOB '*[^a-z0-9_-]*')),
 revision INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
);
CREATE TABLE temporary_passwords (
 account_id TEXT PRIMARY KEY REFERENCES accounts(actor_id) ON DELETE CASCADE,
 password_hash TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES accounts(actor_id)
);
CREATE TABLE session_metadata (
 token_digest TEXT PRIMARY KEY REFERENCES sessions(token_digest) ON DELETE CASCADE,
 device TEXT NOT NULL DEFAULT '', method TEXT NOT NULL DEFAULT 'password',
 expires_at TEXT, revoked_at TEXT
);
CREATE TABLE account_identities (
 identity_id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(actor_id) ON DELETE CASCADE,
 provider TEXT NOT NULL, subject_hash TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(provider, subject_hash), UNIQUE(account_id, provider)
);
CREATE TABLE consent_events (
 event_id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(actor_id),
 consent_version TEXT NOT NULL, state TEXT NOT NULL, research_allowed INTEGER NOT NULL CHECK(research_allowed IN (0,1)),
 recorded_at TEXT NOT NULL, source TEXT NOT NULL
);
CREATE INDEX consent_events_account_idx ON consent_events(account_id, recorded_at);
CREATE TRIGGER consent_events_no_update BEFORE UPDATE ON consent_events BEGIN SELECT RAISE(ABORT,'consent events are append-only'); END;
CREATE TRIGGER consent_events_no_delete BEFORE DELETE ON consent_events BEGIN SELECT RAISE(ABORT,'consent events are append-only'); END;
CREATE TABLE activity_events (
 event_id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(actor_id),
 kind TEXT NOT NULL, object_id TEXT, recorded_at TEXT NOT NULL, detail_code TEXT
);
CREATE INDEX activity_events_account_idx ON activity_events(account_id, recorded_at);
