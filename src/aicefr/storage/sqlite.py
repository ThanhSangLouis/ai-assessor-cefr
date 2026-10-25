"""Versioned SQLite repositories with explicit transactions for synthetic data."""

from __future__ import annotations

import sqlite3
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from aicefr.auth.service import IDLE_TTL, AccountRecord
from aicefr.contracts import (
    Actor,
    ActorRole,
    AuditEvent,
    BlobRef,
    ConsentRecord,
    ConsentState,
    ReasonCode,
    ResponseRecord,
    ResponseStatus,
    SessionRecord,
)
from aicefr.storage.migrations import SCHEMA_VERSION, migration_lock
from aicefr.storage.migrations import migrate as migrate_w5
from aicefr.storage.paths import external_data_dir


class SQLiteStore:
    SCHEMA_VERSION = SCHEMA_VERSION

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = external_data_dir(data_dir)
        self.connection = sqlite3.connect(
            self.data_dir / "metadata.sqlite3", isolation_level=None, timeout=5.0
        )
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA foreign_keys=ON")
        try:
            self._migrate()
        except Exception:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self.connection.in_transaction:
            # Nested repositories join the caller-owned unit of work. The outer
            # owner alone decides commit or rollback.
            yield self.connection
            return
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _migrate(self) -> None:
        try:
            data_dir = getattr(self, "data_dir", None)
            if data_dir is None:
                self._migration_test_directory = tempfile.TemporaryDirectory()
                data_dir = Path(self._migration_test_directory.name)
            with migration_lock(Path(data_dir)):
                version = self.connection.execute("PRAGMA user_version").fetchone()[0]
                if version < 0 or version > self.SCHEMA_VERSION:
                    raise RuntimeError("unsupported SQLite schema version")
                if version == 0:
                    self._create_v1_schema()
                    version = 1
                if version == 1:
                    self._upgrade_v1_to_v2()
                    version = 2
                if version == 2:
                    self._upgrade_v2_to_v3()
                    version = 3
                if version == 3:
                    self._upgrade_v3_to_v4()
                    version = 4
                # W5 migration verifies the checksum ledger before extending an
                # already-upgraded schema (including the supported v10→v11 path).
                if version < 4 or version > self.SCHEMA_VERSION:
                    raise RuntimeError("unsupported SQLite schema version")
                migrate_w5(self.connection, Path(data_dir), lock_held=True)
        except Exception:
            self.connection.rollback()
            raise

    def _create_v1_schema(self) -> None:
        self.connection.executescript(
            """
            BEGIN IMMEDIATE;
            CREATE TABLE accounts (
                actor_id TEXT PRIMARY KEY, role TEXT NOT NULL, password_hash TEXT NOT NULL
            );
            CREATE TABLE sessions (
                token_digest TEXT PRIMARY KEY,
                actor_id TEXT NOT NULL REFERENCES accounts(actor_id),
                role TEXT NOT NULL, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
                idle_expires_at TEXT NOT NULL, absolute_expires_at TEXT NOT NULL
            );
            CREATE TABLE consents (
                participant_id TEXT PRIMARY KEY REFERENCES accounts(actor_id),
                consent_version TEXT NOT NULL, state TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE responses (
                response_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES accounts(actor_id),
                task_id TEXT NOT NULL, task_version TEXT NOT NULL,
                blob_id TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                status TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE audit (
                event_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, action TEXT NOT NULL,
                object_id TEXT NOT NULL, recorded_at TEXT NOT NULL, reason TEXT
            );
            CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit
                BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
            CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit
                BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
            PRAGMA user_version=1;
            COMMIT;
            """
        )

    def _upgrade_v1_to_v2(self) -> None:
        """Add M01 status reasons and durable M07 review records atomically."""
        self.connection.executescript(
            """
            BEGIN IMMEDIATE;
            ALTER TABLE responses ADD COLUMN status_reason TEXT;
            UPDATE responses SET status='QUEUED' WHERE status='submitted';
            CREATE TABLE review_candidates (
                response_id TEXT PRIMARY KEY REFERENCES responses(response_id),
                response_revision INTEGER NOT NULL,
                assessment_status TEXT NOT NULL,
                proposed_band TEXT,
                reasons_json TEXT NOT NULL,
                source_versions_json TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE review_decisions (
                decision_id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL REFERENCES review_candidates(response_id),
                teacher_id TEXT NOT NULL REFERENCES accounts(actor_id),
                action TEXT NOT NULL,
                old_state TEXT NOT NULL,
                new_state TEXT NOT NULL,
                candidate_revision INTEGER NOT NULL,
                proposed_band TEXT,
                final_band TEXT,
                reason TEXT,
                audit_id TEXT UNIQUE NOT NULL REFERENCES audit(event_id),
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX review_candidates_queue_idx
                ON review_candidates(state, updated_at);
            CREATE INDEX review_decisions_response_idx
                ON review_decisions(response_id, recorded_at);
            PRAGMA user_version=2;
            COMMIT;
            """
        )

    def _upgrade_v2_to_v3(self) -> None:
        self.connection.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE diagnostic_reports (
                response_id TEXT PRIMARY KEY REFERENCES responses(response_id),
                report_json TEXT NOT NULL
            );
            PRAGMA user_version=3;
            COMMIT;
        """)

    def _upgrade_v3_to_v4(self) -> None:
        self.connection.executescript("""
            BEGIN IMMEDIATE;
            ALTER TABLE accounts ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE accounts ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE accounts ADD COLUMN locked_until TEXT;
            ALTER TABLE consents ADD COLUMN research_allowed INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE responses ADD COLUMN audio_deleted_at TEXT;
            ALTER TABLE review_candidates ADD COLUMN claimed_by TEXT;
            UPDATE review_candidates SET claimed_by=(
                SELECT actor_id FROM audit WHERE action='review_claimed'
                AND object_id=review_candidates.response_id ORDER BY rowid DESC LIMIT 1
            ) WHERE state='IN_REVIEW';
            CREATE TABLE speaking_tasks (
                task_id TEXT NOT NULL, task_version TEXT NOT NULL,
                title TEXT NOT NULL, prompt_text TEXT NOT NULL,
                min_seconds REAL NOT NULL, max_seconds REAL NOT NULL,
                active INTEGER NOT NULL, revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(task_id, task_version)
            );
            CREATE TABLE runtime_settings (
                key TEXT PRIMARY KEY, payload TEXT NOT NULL,
                revision INTEGER NOT NULL, version TEXT NOT NULL,
                updated_by TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE blob_deletions (
                blob_id TEXT PRIMARY KEY, queued_at TEXT NOT NULL
            );
            CREATE INDEX responses_owner_created_idx ON responses(owner_id, created_at);
            PRAGMA user_version=4;
            COMMIT;
        """)

    def _audit(self, connection: sqlite3.Connection, event: AuditEvent) -> None:
        connection.execute(
            "INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.actor_id,
                event.action,
                event.object_id,
                event.recorded_at.isoformat(),
                event.reason,
            ),
        )

    def record_audit(self, connection: sqlite3.Connection, event: AuditEvent) -> None:
        """Append an audit event inside a caller-owned metadata transaction."""
        self._audit(connection, event)

    @staticmethod
    def _response_from_row(row: tuple[object, ...]) -> ResponseRecord:
        return ResponseRecord(
            response_id=str(row[0]),
            owner_id=str(row[1]),
            task_id=str(row[2]),
            task_version=str(row[3]),
            blob=BlobRef(blob_id=str(row[4]), sha256=str(row[5]), size_bytes=int(row[6])),
            status=ResponseStatus(str(row[7])),
            revision=int(row[8]),
            created_at=datetime.fromisoformat(str(row[9])),
            status_reason=ReasonCode(str(row[10])) if row[10] is not None else None,
            audio_available=row[11] is None,
        )

    def get_account(self, actor_id: str) -> AccountRecord | None:
        row = self.connection.execute(
            "SELECT actor_id, role, password_hash, disabled, failed_attempts, locked_until "
            "FROM accounts WHERE actor_id=?",
            (actor_id,),
        ).fetchone()
        if row is None:
            return None
        return AccountRecord(
            Actor(actor_id=row[0], role=ActorRole(row[1])),
            row[2],
            bool(row[3]),
            row[4],
            datetime.fromisoformat(row[5]) if row[5] else None,
        )

    def add_account(self, account: AccountRecord) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO accounts(actor_id, role, password_hash) VALUES (?, ?, ?)",
                (account.actor.actor_id, account.actor.role, account.password_hash),
            )

    def record_login(self, actor_id: str, *, success: bool, now: datetime) -> None:
        with self.transaction() as connection:
            account = self.get_account(actor_id)
            if account is None:
                return
            expired = account.locked_until is not None and now >= account.locked_until
            attempts = 0 if success or expired else account.failed_attempts
            if not success:
                attempts += 1
            locked = now + timedelta(minutes=15) if attempts >= 5 else None
            connection.execute(
                "UPDATE accounts SET failed_attempts=?, locked_until=? WHERE actor_id=?",
                (attempts, locked.isoformat() if locked else None, actor_id),
            )

    def get_session(self, digest: str) -> SessionRecord | None:
        row = self.connection.execute(
            "SELECT * FROM sessions WHERE token_digest=?", (digest,)
        ).fetchone()
        if row is None:
            return None
        return SessionRecord(
            token_digest=row[0],
            actor_id=row[1],
            role=ActorRole(row[2]),
            created_at=datetime.fromisoformat(row[3]),
            last_seen_at=datetime.fromisoformat(row[4]),
            idle_expires_at=datetime.fromisoformat(row[5]),
            absolute_expires_at=datetime.fromisoformat(row[6]),
        )

    def put_session(self, session: SessionRecord) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_digest) DO UPDATE SET
                last_seen_at=excluded.last_seen_at, idle_expires_at=excluded.idle_expires_at""",
                (
                    session.token_digest,
                    session.actor_id,
                    session.role,
                    session.created_at.isoformat(),
                    session.last_seen_at.isoformat(),
                    session.idle_expires_at.isoformat(),
                    session.absolute_expires_at.isoformat(),
                ),
            )

    def touch_session(self, session: SessionRecord, *, now: datetime) -> bool:
        """Refresh an existing live session without recreating a revoked row."""
        idle_expires = min(now + IDLE_TTL, session.absolute_expires_at)
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET last_seen_at=?,idle_expires_at=? "
                "WHERE token_digest=? AND actor_id=? AND role=? AND created_at=? "
                "AND absolute_expires_at=? AND idle_expires_at>? AND absolute_expires_at>?",
                (
                    now.isoformat(),
                    idle_expires.isoformat(),
                    session.token_digest,
                    session.actor_id,
                    session.role.value,
                    session.created_at.isoformat(),
                    session.absolute_expires_at.isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            return cursor.rowcount == 1

    def delete_session(self, digest: str) -> None:
        """Revoke a session by its stored token digest; missing sessions are harmless."""
        with self.transaction() as connection:
            connection.execute("DELETE FROM sessions WHERE token_digest=?", (digest,))

    def get_consent(self, participant_id: str) -> ConsentRecord | None:
        row = self.connection.execute(
            "SELECT * FROM consents WHERE participant_id=?", (participant_id,)
        ).fetchone()
        if row is None:
            return None
        return ConsentRecord(
            participant_id=row[0],
            consent_version=row[1],
            state=ConsentState(row[2]),
            recorded_at=datetime.fromisoformat(row[3]),
            research_allowed=bool(row[4]),
            audio_storage_allowed=bool(row[5]) if len(row) > 5 else False,
        )

    def put_consent(self, consent: ConsentRecord) -> None:
        event = AuditEvent(
            event_id=uuid.uuid4().hex,
            actor_id=consent.participant_id,
            action=f"consent_{consent.state}",
            object_id=consent.participant_id,
            recorded_at=consent.recorded_at,
        )
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO consents (
                participant_id, consent_version, state, recorded_at, research_allowed,
                audio_storage_allowed
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id) DO UPDATE SET
                consent_version=excluded.consent_version, state=excluded.state,
                recorded_at=excluded.recorded_at, research_allowed=excluded.research_allowed,
                audio_storage_allowed=excluded.audio_storage_allowed""",
                (
                    consent.participant_id,
                    consent.consent_version,
                    consent.state,
                    consent.recorded_at.isoformat(),
                    int(consent.research_allowed),
                    int(consent.audio_storage_allowed),
                ),
            )
            self._audit(connection, event)

    def get_response(self, response_id: str) -> ResponseRecord | None:
        row = self.connection.execute(
            "SELECT * FROM responses WHERE response_id=?", (response_id,)
        ).fetchone()
        if row is None:
            return None
        return self._response_from_row(row)

    def save_response(self, response: ResponseRecord, event: AuditEvent) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO responses (
                response_id, owner_id, task_id, task_version, blob_id, sha256,
                size_bytes, status, status_reason, revision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    response.response_id,
                    response.owner_id,
                    response.task_id,
                    response.task_version,
                    response.blob.blob_id,
                    response.blob.sha256,
                    response.blob.size_bytes,
                    response.status,
                    response.status_reason,
                    response.revision,
                    response.created_at.isoformat(),
                ),
            )
            self._audit(connection, event)

    def update_response_status(
        self,
        response_id: str,
        *,
        expected_revision: int,
        status: ResponseStatus,
        status_reason: ReasonCode | None,
        event: AuditEvent,
        expected_status: ResponseStatus | None = None,
    ) -> ResponseRecord:
        """Đổi trạng thái response với optimistic locking và audit cùng transaction.

        Đây là port nội bộ cho pipeline M01–M06, không phải API cho client.
        """
        with self.transaction() as connection:
            status_clause = " AND status=?" if expected_status is not None else ""
            parameters = (status, status_reason, response_id, expected_revision)
            if expected_status is not None:
                parameters += (expected_status,)
            cursor = connection.execute(
                """UPDATE responses SET status=?, status_reason=?, revision=revision+1
                WHERE response_id=? AND revision=?"""
                + status_clause,
                parameters,
            )
            if cursor.rowcount != 1:
                raise ConcurrentResponseUpdate("response missing or revision is stale")
            self._audit(connection, event)
            row = connection.execute(
                "SELECT * FROM responses WHERE response_id=?", (response_id,)
            ).fetchone()
        assert row is not None
        return self._response_from_row(row)

    def claim_queued_response(self, response: ResponseRecord) -> ResponseRecord:
        """CAS-claim a queued row only when the submitted provenance still matches."""
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE responses SET status=?, status_reason=NULL, revision=revision+1
                WHERE response_id=? AND owner_id=? AND task_id=? AND task_version=?
                AND blob_id=? AND sha256=? AND size_bytes=? AND revision=? AND status=?""",
                (
                    ResponseStatus.RUNNING,
                    response.response_id,
                    response.owner_id,
                    response.task_id,
                    response.task_version,
                    response.blob.blob_id,
                    response.blob.sha256,
                    response.blob.size_bytes,
                    response.revision,
                    ResponseStatus.QUEUED,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentResponseUpdate("response provenance or revision is stale")
            self._audit(
                connection,
                AuditEvent(
                    event_id=uuid.uuid4().hex,
                    actor_id="system-pipeline",
                    action="pipeline_started",
                    object_id=response.response_id,
                    recorded_at=datetime.now().astimezone(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM responses WHERE response_id=?", (response.response_id,)
            ).fetchone()
        assert row is not None
        return self._response_from_row(row)

    def list_audit(self) -> tuple[AuditEvent, ...]:
        rows = self.connection.execute("SELECT * FROM audit ORDER BY rowid").fetchall()
        return tuple(
            AuditEvent(
                event_id=row[0],
                actor_id=row[1],
                action=row[2],
                object_id=row[3],
                recorded_at=datetime.fromisoformat(row[4]),
                reason=row[5],
            )
            for row in rows
        )

    def referenced_blob_ids(self) -> set[str]:
        return {row[0] for row in self.connection.execute("SELECT blob_id FROM responses")}


class ConcurrentResponseUpdate(RuntimeError):
    """Response đã bị đổi bởi pipeline khác hoặc không còn tồn tại."""
