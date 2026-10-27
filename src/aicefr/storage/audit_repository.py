"""The audit log of one service (D043).

Each service keeps its own `audit_log`, in its own store, and writes it in the
same transaction as the change it records -- a review decision and its audit row
commit together or not at all. The administrator's screen reads every
service's log through their facades and merges them by time
(`aicefr.services.core.identity`).

Rows say which service wrote them. When several services share one store -- one
SQLite file on one machine -- each still reads only its own rows. Rows written
before D043 have no service; they are assigned once, by the action's name.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from aicefr.contracts import AuditEntry
from aicefr.storage.db import Connection, SqlStore, add_columns

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    target_id       TEXT,
    detail          TEXT,
    created_at      TEXT NOT NULL
);
"""

SERVICES = ("identity", "assessment", "learning", "billing")

# How a row written before D043 is assigned: by the prefix of its action.
LEGACY_PREFIXES = {
    "identity": ("auth.", "account.", "consent."),
    "learning": ("lesson.", "ERASE_OWN_LESSON_ATTEMPT"),
    "billing": ("billing.",),
}


def prepare(c: Connection) -> None:
    """The table, its `service` column, and the assignment of rows from before D043."""
    c.executescript(SCHEMA)
    add_columns(c, "audit_log", (("service", "TEXT"),))
    for service, prefixes in LEGACY_PREFIXES.items():
        for prefix in prefixes:
            c.execute(
                "UPDATE audit_log SET service=? WHERE service IS NULL AND substr(action, 1, ?) = ?",
                (service, len(prefix), prefix),
            )
    c.execute("UPDATE audit_log SET service='assessment' WHERE service IS NULL")


def write_audit(
    c: Connection,
    service: str,
    actor_id: str,
    action: str,
    target_id: str | None,
    detail: str | None,
) -> None:
    """One audit row, inside the caller's transaction.

    Stamped to the microsecond, not the second: the logs of several services
    are merged by time, and two actions in the same second must keep their order.
    """
    stamp = datetime.now(UTC).isoformat(timespec="microseconds")
    c.execute(
        "INSERT INTO audit_log(service, actor_id, action, target_id, detail, created_at)"
        " VALUES(?,?,?,?,?,?)",
        (service, actor_id, action, target_id, detail, stamp),
    )


class AuditLog(SqlStore):
    """One service's audit log: write an entry, read the latest, read those about one target.

    Kept deliberately small: an actor, what they did, to what, and when. No
    transcript, no pseudonym of a third party, no free text unless the action
    needs one.
    """

    def __init__(self, db_path: str | Path, service: str) -> None:
        if service not in SERVICES:
            raise ValueError(f"unknown service {service}")
        self.db_path = str(db_path)
        self.service = service
        with self._conn() as c:
            prepare(c)

    def write(self, actor_id: str, action: str, target_id: str | None, detail: str | None) -> None:
        with self._conn() as c:
            write_audit(c, self.service, actor_id, action, target_id, detail)

    def recent(self, limit: int = 100) -> list[dict]:
        """The latest entries, newest first, with their order key for merging."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, actor_id, action, target_id, detail, created_at FROM audit_log"
                " WHERE service=? ORDER BY id DESC LIMIT ?",
                (self.service, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def about(self, target_id: str, actions: Sequence[str], limit: int = 40) -> list[dict]:
        """Entries about one target among `actions`, newest first (D029: an account's history)."""
        marks = ",".join("?" * len(actions))
        with self._conn() as c:
            rows = c.execute(
                f"SELECT actor_id, action, target_id, detail, created_at FROM audit_log"
                f" WHERE service=? AND target_id = ? AND action IN ({marks})"
                f" ORDER BY id DESC LIMIT ?",
                (self.service, target_id, *actions, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def merge(logs: Sequence[Sequence[dict]], limit: int) -> list[AuditEntry]:
    """Several services' latest entries as one list, newest first.

    By time, to the microsecond; rows from before that precision tie within a
    second and are ordered by row id, exactly when the services share a store.
    """
    rows = [r for log in logs for r in log]
    rows.sort(key=lambda r: (r["created_at"], r.get("id", 0)), reverse=True)
    return [
        AuditEntry(**{k: r[k] for k in ("actor_id", "action", "target_id", "detail", "created_at")})
        for r in rows[:limit]
    ]
