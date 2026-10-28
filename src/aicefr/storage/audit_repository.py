"""The audit log of one service (D043).

Each service keeps its own `audit_log`, in its own store, and writes it right
after the change it records. The administrator's screen reads every service's
log through their facades and merges them by time
(`aicefr.services.core.identity`).

Entries say which service wrote them. When several services share one store
each still reads only its own entries.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pymongo import DESCENDING
from pymongo.database import Database

from aicefr.contracts import AuditEntry
from aicefr.storage.db import MongoStore, ensure_indexes, fields, next_id

SERVICES = ("identity", "assessment", "learning", "billing", "metering")

INDEXES = {"audit_log": [(("id",), True), (("service", "id"), False)]}

_FIELDS = ("id", "actor_id", "action", "target_id", "detail", "created_at")


def prepare(db: Database) -> None:
    """The collection and its indexes."""
    ensure_indexes(db, INDEXES, "audit")


def write_audit(
    db: Database,
    service: str,
    actor_id: str,
    action: str,
    target_id: str | None,
    detail: str | None,
) -> None:
    """One audit entry.

    Stamped to the microsecond, not the second: the logs of several services
    are merged by time, and two actions in the same second must keep their order.
    """
    stamp = datetime.now(UTC).isoformat(timespec="microseconds")
    db["audit_log"].insert_one(
        {
            "id": next_id(db, "audit_log"),
            "service": service,
            "actor_id": actor_id,
            "action": action,
            "target_id": target_id,
            "detail": detail,
            "created_at": stamp,
        }
    )


def recent_entries(db: Database, service: str, limit: int) -> list[dict]:
    rows = db["audit_log"].find({"service": service}).sort("id", DESCENDING).limit(limit)
    return [fields(r, _FIELDS) for r in rows]  # type: ignore[misc]


class AuditLog(MongoStore):
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
        prepare(self.db)

    def write(self, actor_id: str, action: str, target_id: str | None, detail: str | None) -> None:
        write_audit(self.db, self.service, actor_id, action, target_id, detail)

    def recent(self, limit: int = 100) -> list[dict]:
        """The latest entries, newest first, with their order key for merging."""
        return recent_entries(self.db, self.service, limit)

    def about(self, target_id: str, actions: Sequence[str], limit: int = 40) -> list[dict]:
        """Entries about one target among `actions`, newest first (D029: an account's history)."""
        rows = (
            self.col("audit_log")
            .find(
                {"service": self.service, "target_id": target_id, "action": {"$in": list(actions)}}
            )
            .sort("id", DESCENDING)
            .limit(limit)
        )
        return [fields(r, _FIELDS[1:]) for r in rows]  # type: ignore[misc]


def merge(logs: Sequence[Sequence[dict]], limit: int) -> list[AuditEntry]:
    """Several services' latest entries as one list, newest first.

    By time, to the microsecond; entries that tie are ordered by their number.
    """
    rows = [r for log in logs for r in log]
    rows.sort(key=lambda r: (r["created_at"], r.get("id", 0)), reverse=True)
    return [
        AuditEntry(**{k: r[k] for k in ("actor_id", "action", "target_id", "detail", "created_at")})
        for r in rows[:limit]
    ]
