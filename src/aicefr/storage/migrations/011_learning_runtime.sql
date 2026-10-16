-- Additive runtime metadata for versioned learning content and attempts.
-- Migrations 005-010 are intentionally left byte-for-byte unchanged.

ALTER TABLE learning_paths ADD COLUMN seed_version TEXT;
ALTER TABLE learning_paths ADD COLUMN seed_hash TEXT;
ALTER TABLE learning_paths ADD COLUMN seed_owned INTEGER NOT NULL DEFAULT 0 CHECK(seed_owned IN (0,1));
ALTER TABLE learning_paths ADD COLUMN content_hash TEXT;
ALTER TABLE learning_paths ADD COLUMN band_from TEXT;
ALTER TABLE learning_paths ADD COLUMN band_to TEXT;
ALTER TABLE learning_paths ADD COLUMN content_version TEXT;

ALTER TABLE learning_units ADD COLUMN band TEXT;
ALTER TABLE learning_units ADD COLUMN topic TEXT;
ALTER TABLE learning_units ADD COLUMN learning_function TEXT;
ALTER TABLE learning_units ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0);
ALTER TABLE learning_units ADD COLUMN seed_version TEXT;
ALTER TABLE learning_units ADD COLUMN seed_hash TEXT;
ALTER TABLE learning_units ADD COLUMN seed_owned INTEGER NOT NULL DEFAULT 0 CHECK(seed_owned IN (0,1));
ALTER TABLE learning_units ADD COLUMN content_hash TEXT;

ALTER TABLE learning_lessons ADD COLUMN summary TEXT NOT NULL DEFAULT '';
ALTER TABLE learning_lessons ADD COLUMN band TEXT;
ALTER TABLE learning_lessons ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1);
ALTER TABLE learning_lessons ADD COLUMN seed_version TEXT;
ALTER TABLE learning_lessons ADD COLUMN seed_hash TEXT;
ALTER TABLE learning_lessons ADD COLUMN seed_owned INTEGER NOT NULL DEFAULT 0 CHECK(seed_owned IN (0,1));
ALTER TABLE learning_lessons ADD COLUMN content_hash TEXT;
ALTER TABLE learning_lessons ADD COLUMN content_version TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE learning_lessons ADD COLUMN ordinal INTEGER NOT NULL DEFAULT 0;

ALTER TABLE lesson_steps ADD COLUMN stage TEXT;
ALTER TABLE lesson_steps ADD COLUMN instruction TEXT;
ALTER TABLE lesson_steps ADD COLUMN rules_version TEXT;

ALTER TABLE lesson_versions ADD COLUMN title TEXT NOT NULL DEFAULT '';
ALTER TABLE lesson_versions ADD COLUMN summary TEXT NOT NULL DEFAULT '';
ALTER TABLE lesson_versions ADD COLUMN band TEXT;
ALTER TABLE lesson_versions ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1);
ALTER TABLE lesson_versions ADD COLUMN content_hash TEXT;

CREATE TRIGGER lesson_active_version_insert_valid
BEFORE INSERT ON learning_lessons
WHEN NEW.active_version IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM lesson_versions v
    WHERE v.lesson_id=NEW.lesson_id AND v.version=NEW.active_version AND v.state='published'
)
BEGIN SELECT RAISE(ABORT,'active version must be a published version of this lesson'); END;

CREATE TRIGGER lesson_active_version_update_valid
BEFORE UPDATE OF active_version ON learning_lessons
WHEN NEW.active_version IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM lesson_versions v
    WHERE v.lesson_id=NEW.lesson_id AND v.version=NEW.active_version AND v.state='published'
)
BEGIN SELECT RAISE(ABORT,'active version must be a published version of this lesson'); END;

CREATE TRIGGER lesson_publish_snapshot_valid
BEFORE UPDATE OF state ON lesson_versions
WHEN OLD.state='draft' AND NEW.state='published' AND (
    NEW.title='' OR NEW.band IS NULL OR NEW.content_hash IS NULL
    OR length(NEW.content_hash)<>64
    OR NOT EXISTS (
        SELECT 1 FROM lesson_steps s
        WHERE s.lesson_id=NEW.lesson_id AND s.version=NEW.version
    )
)
BEGIN SELECT RAISE(ABORT,'published lesson version requires complete immutable snapshot metadata'); END;

ALTER TABLE practice_attempts ADD COLUMN purpose TEXT NOT NULL DEFAULT 'PRACTICE'
    CHECK(purpose IN ('PRACTICE','LEARNING'));
ALTER TABLE practice_attempts ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT '';
ALTER TABLE practice_attempts ADD COLUMN rules_version TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE practice_attempts ADD COLUMN mission_snapshot TEXT NOT NULL DEFAULT '{}';
ALTER TABLE practice_attempts ADD COLUMN attempt_state TEXT NOT NULL DEFAULT 'COMPLETED'
    CHECK(attempt_state IN ('QUEUED','COMPLETED','NOT_EVALUATED','LEGACY'));
ALTER TABLE practice_attempts ADD COLUMN result_json TEXT;
ALTER TABLE practice_attempts ADD COLUMN reasons_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE practice_attempts ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0);
ALTER TABLE practice_attempts ADD COLUMN review_source_kind TEXT CHECK(review_source_kind IS NULL OR review_source_kind IN ('practice','step'));
ALTER TABLE practice_attempts ADD COLUMN review_source_attempt_id TEXT;
ALTER TABLE practice_attempts ADD COLUMN review_content_key TEXT;
ALTER TABLE practice_attempts ADD COLUMN expected_review_revision INTEGER CHECK(expected_review_revision IS NULL OR expected_review_revision>=0);
ALTER TABLE practice_attempts ADD COLUMN review_box INTEGER CHECK(review_box IS NULL OR review_box BETWEEN 1 AND 4);
UPDATE practice_attempts SET attempt_state='LEGACY',reasons_json='["LEGACY_RESULT_NOT_TYPED"]';
UPDATE practice_attempts SET idempotency_key='legacy:'||attempt_id WHERE idempotency_key='';
CREATE UNIQUE INDEX practice_attempt_idempotency_idx
    ON practice_attempts(owner_id,purpose,idempotency_key);

ALTER TABLE step_attempts ADD COLUMN idempotency_key TEXT NOT NULL DEFAULT '';
ALTER TABLE step_attempts ADD COLUMN attempt_state TEXT NOT NULL DEFAULT 'COMPLETED'
    CHECK(attempt_state IN ('QUEUED','COMPLETED','NOT_EVALUATED','LEGACY'));
ALTER TABLE step_attempts ADD COLUMN result_json TEXT;
ALTER TABLE step_attempts ADD COLUMN reasons_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE step_attempts ADD COLUMN round_index INTEGER CHECK(round_index IS NULL OR round_index>=0);
ALTER TABLE step_attempts ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE step_attempts ADD COLUMN review_source_kind TEXT CHECK(review_source_kind IS NULL OR review_source_kind IN ('practice','step'));
ALTER TABLE step_attempts ADD COLUMN review_source_attempt_id TEXT;
ALTER TABLE step_attempts ADD COLUMN review_content_key TEXT;
ALTER TABLE step_attempts ADD COLUMN expected_review_revision INTEGER CHECK(expected_review_revision IS NULL OR expected_review_revision>=0);
ALTER TABLE step_attempts ADD COLUMN review_box INTEGER CHECK(review_box IS NULL OR review_box BETWEEN 1 AND 4);
UPDATE step_attempts SET updated_at=created_at WHERE updated_at='';
UPDATE step_attempts SET idempotency_key='legacy:'||attempt_id WHERE idempotency_key='';
UPDATE step_attempts SET attempt_state='LEGACY',reasons_json='["LEGACY_RESULT_NOT_TYPED"]';
CREATE UNIQUE INDEX step_attempt_idempotency_idx
    ON step_attempts(owner_id,idempotency_key);

ALTER TABLE review_items ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0);
CREATE TABLE step_review_items (
    review_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES accounts(actor_id),
    source_step_attempt TEXT NOT NULL REFERENCES step_attempts(attempt_id) ON DELETE CASCADE,
    content_key TEXT NOT NULL,
    box INTEGER NOT NULL DEFAULT 0,
    due_at TEXT NOT NULL,
    state TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
    updated_at TEXT NOT NULL,
    UNIQUE(owner_id,source_step_attempt,content_key)
);
CREATE INDEX step_review_items_due_idx ON step_review_items(owner_id,state,due_at);

CREATE TABLE learning_seed_manifest (
    seed_name TEXT PRIMARY KEY,
    seed_version TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL CHECK(length(manifest_sha256)=64),
    layout INTEGER NOT NULL CHECK(layout>0),
    applied_at TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE learning_audio_artifacts (
    artifact_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES accounts(actor_id),
    attempt_kind TEXT NOT NULL CHECK(attempt_kind IN ('practice','step')),
    practice_attempt_id TEXT REFERENCES practice_attempts(attempt_id) ON DELETE CASCADE,
    step_attempt_id TEXT REFERENCES step_attempts(attempt_id) ON DELETE CASCADE,
    blob_id TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL CHECK(length(content_type) BETWEEN 3 AND 128),
    sha256 TEXT NOT NULL CHECK(length(sha256)=64),
    size_bytes INTEGER NOT NULL CHECK(size_bytes>0),
    created_at TEXT NOT NULL,
    CHECK((attempt_kind='practice' AND practice_attempt_id IS NOT NULL AND step_attempt_id IS NULL)
       OR (attempt_kind='step' AND practice_attempt_id IS NULL AND step_attempt_id IS NOT NULL))
);
CREATE INDEX learning_audio_owner_idx ON learning_audio_artifacts(owner_id,created_at);

CREATE TRIGGER learning_audio_owner_valid_insert
BEFORE INSERT ON learning_audio_artifacts
WHEN NOT EXISTS (
    SELECT 1 FROM practice_attempts p
    WHERE NEW.attempt_kind='practice' AND p.attempt_id=NEW.practice_attempt_id
      AND p.owner_id=NEW.owner_id
) AND NOT EXISTS (
    SELECT 1 FROM step_attempts s
    WHERE NEW.attempt_kind='step' AND s.attempt_id=NEW.step_attempt_id
      AND s.owner_id=NEW.owner_id
)
BEGIN SELECT RAISE(ABORT,'audio owner must match its attempt'); END;

CREATE TRIGGER learning_audio_immutable_update
BEFORE UPDATE ON learning_audio_artifacts
BEGIN SELECT RAISE(ABORT,'learning audio artifact references are immutable'); END;

CREATE TRIGGER learning_audio_cleanup_required
BEFORE DELETE ON learning_audio_artifacts
WHEN NOT EXISTS (
    SELECT 1 FROM cleanup_intents i
    WHERE i.resource_kind='blob' AND i.resource_id=OLD.blob_id
)
BEGIN SELECT RAISE(ABORT,'learning audio deletion requires a cleanup intent'); END;

CREATE TABLE teacher_override_events (
    event_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    owner_id TEXT NOT NULL REFERENCES accounts(actor_id),
    actor_id TEXT NOT NULL REFERENCES accounts(actor_id),
    old_value TEXT,
    new_value TEXT NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX teacher_override_owner_idx ON teacher_override_events(owner_id,recorded_at);
CREATE TRIGGER teacher_override_events_no_update
BEFORE UPDATE ON teacher_override_events
BEGIN SELECT RAISE(ABORT,'teacher override events are append-only'); END;
CREATE TRIGGER teacher_override_events_no_delete
BEFORE DELETE ON teacher_override_events
WHEN NOT EXISTS (
    SELECT 1 FROM cleanup_intents i
    WHERE i.resource_kind='privacy_erasure' AND i.owner_id=OLD.owner_id AND i.state='running'
)
BEGIN SELECT RAISE(ABORT,'teacher override events require authorized erasure'); END;

ALTER TABLE learning_media ADD COLUMN lesson_version INTEGER;
ALTER TABLE learning_media ADD COLUMN step_id TEXT;
ALTER TABLE learning_media ADD COLUMN content_type TEXT;
CREATE UNIQUE INDEX learning_media_version_step_idx
    ON learning_media(lesson_id,lesson_version,step_id,media_kind)
    WHERE lesson_version IS NOT NULL AND step_id IS NOT NULL;
CREATE TRIGGER learning_media_version_valid_insert
BEFORE INSERT ON learning_media
WHEN NEW.lesson_version IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM lesson_versions v
    WHERE v.lesson_id=NEW.lesson_id AND v.version=NEW.lesson_version AND v.state='draft'
) OR NEW.step_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM lesson_steps s
    WHERE s.lesson_id=NEW.lesson_id AND s.version=NEW.lesson_version AND s.step_id=NEW.step_id
)
BEGIN SELECT RAISE(ABORT,'media must reference a draft lesson version and its step'); END;

CREATE TRIGGER learning_media_version_valid_update
BEFORE UPDATE ON learning_media
WHEN OLD.lesson_version IS NOT NULL AND EXISTS (
    SELECT 1 FROM lesson_versions v
    WHERE v.lesson_id=OLD.lesson_id AND v.version=OLD.lesson_version AND v.state='published'
)
BEGIN SELECT RAISE(ABORT,'published lesson media references are immutable'); END;

CREATE TRIGGER learning_media_published_delete
BEFORE DELETE ON learning_media
WHEN OLD.lesson_version IS NOT NULL AND EXISTS (
    SELECT 1 FROM lesson_versions v
    WHERE v.lesson_id=OLD.lesson_id AND v.version=OLD.lesson_version AND v.state='published'
) AND NOT EXISTS (
    SELECT 1 FROM cleanup_intents i
    WHERE i.resource_kind='privacy_erasure' AND i.state='running'
)
BEGIN SELECT RAISE(ABORT,'published lesson media requires authorized erasure'); END;

CREATE TRIGGER learning_media_cleanup_required
BEFORE DELETE ON learning_media
WHEN OLD.blob_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM cleanup_intents i
    WHERE i.resource_kind='blob' AND i.resource_id=OLD.blob_id
)
BEGIN SELECT RAISE(ABORT,'lesson media deletion requires a cleanup intent'); END;
