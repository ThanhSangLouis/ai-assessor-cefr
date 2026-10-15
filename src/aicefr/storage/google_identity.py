"""Google subject lookup and durable OAuth-flow replay reservations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime

from aicefr.storage.sqlite import SQLiteStore


def google_subject_hash(subject: str) -> str:
    """Return the only Google subject representation allowed in storage."""
    return hashlib.sha256(b"aicefr:google-subject:v1\0" + subject.encode("utf-8")).hexdigest()


class GoogleIdentityRepository:
    """Google-owned adapter over the frozen v9 identity and runtime tables."""

    FLOW_PREFIX = "google_flow_v1:"

    def __init__(self, storage: SQLiteStore) -> None:
        self.storage = storage

    def reserve_flow(self, state_hash: str, expires_at: datetime, *, now: datetime) -> None:
        key = self.FLOW_PREFIX + state_hash
        with self.storage.transaction() as connection:
            rows = connection.execute(
                "SELECT key,payload FROM runtime_settings WHERE substr(key,1,?)=?",
                (len(self.FLOW_PREFIX), self.FLOW_PREFIX),
            ).fetchall()
            for stale_key, stale_payload in rows:
                try:
                    expires = datetime.fromisoformat(json.loads(stale_payload)["expires_at"])
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    expires = now
                if now >= expires:
                    connection.execute("DELETE FROM runtime_settings WHERE key=?", (stale_key,))
            connection.execute(
                "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
                "VALUES(?,?,1,'google-flow-v1','system-google',?)",
                (key, json.dumps({"expires_at": expires_at.isoformat()}), now.isoformat()),
            )

    def consume_flow(self, state_hash: str, now: datetime) -> bool:
        """Delete one unexpired flow exactly once, serialized across SQLite connections."""
        key = self.FLOW_PREFIX + state_hash
        with self.storage.transaction() as connection:
            row = connection.execute(
                "SELECT payload FROM runtime_settings WHERE key=?", (key,)
            ).fetchone()
            if row is None:
                return False
            try:
                payload = json.loads(row[0])
                expires = datetime.fromisoformat(payload["expires_at"])
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                connection.execute("DELETE FROM runtime_settings WHERE key=?", (key,))
                return False
            if now >= expires:
                connection.execute("DELETE FROM runtime_settings WHERE key=?", (key,))
                return False
            connection.execute("DELETE FROM runtime_settings WHERE key=?", (key,))
            return True

    def account_for_subject(self, subject_hash: str) -> str | None:
        row = self.storage.connection.execute(
            "SELECT account_id FROM account_identities WHERE provider='google' AND subject_hash=?",
            (subject_hash,),
        ).fetchone()
        return str(row[0]) if row else None

    def account_is_linked(self, actor_id: str) -> bool:
        return bool(
            self.storage.connection.execute(
                "SELECT 1 FROM account_identities WHERE account_id=? AND provider='google'",
                (actor_id,),
            ).fetchone()
        )

    def link_subject(self, actor_id: str, subject_hash: str, now: datetime) -> None:
        """Attach one unique subject and record a non-sensitive audit event atomically."""
        with self.storage.transaction() as connection:
            connection.execute(
                "INSERT INTO account_identities(identity_id,account_id,provider,"
                "subject_hash,created_at) "
                "VALUES(?,?,'google',?,?)",
                (uuid.uuid4().hex, actor_id, subject_hash, now.isoformat()),
            )
            self._event(connection, actor_id, "google_linked", now)

    def unlink_subject(self, actor_id: str, now: datetime) -> bool:
        with self.storage.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM account_identities WHERE account_id=? AND provider='google'",
                (actor_id,),
            )
            if cursor.rowcount:
                self._event(connection, actor_id, "google_unlinked", now)
            return cursor.rowcount > 0

    @staticmethod
    def _event(connection: sqlite3.Connection, actor_id: str, action: str, now: datetime) -> None:
        connection.execute(
            "INSERT INTO audit(event_id,actor_id,action,object_id,recorded_at,reason) "
            "VALUES(?,?,?,?,?,NULL)",
            (uuid.uuid4().hex, actor_id, action, actor_id, now.isoformat()),
        )
        connection.execute(
            "INSERT INTO activity_events(event_id,account_id,kind,object_id,recorded_at,"
            "detail_code) "
            "VALUES(?,?,?,NULL,?,NULL)",
            (uuid.uuid4().hex, actor_id, action, now.isoformat()),
        )
