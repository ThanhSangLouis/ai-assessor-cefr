"""Versioned structure of the core store (D045, on MongoDB since D048).

A MongoDB collection has no columns to migrate; what the store's structure
consists of is its collections and their indexes -- the unique ones carry what
primary keys and UNIQUE constraints carried in SQL. Version 1, the baseline,
is every collection and index the repositories create; from then on a change is
a numbered migration below, never a silent edit of a repository's `INDEXES`:
`tests/test_schema.py` compares a fresh store with the committed snapshot
`docs/db/schema_core.json` and fails on any difference.

Applied versions are recorded in `schema_migrations`, one document per
version under a unique index. Every migration must be idempotent -- creating an
index that exists is a no-op, a data change guards itself with a condition --
so two processes upgrading at once both run it and exactly one records it.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pymongo.database import Database

from aicefr.storage.db import IntegrityError, database, ensure_indexes, now_iso

COLLECTION = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Database, str], None]


def _baseline(db: Database, target: str) -> None:
    """Every collection and index up to D044, as the repositories create them."""
    from aicefr.storage.audit_repository import AuditLog
    from aicefr.storage.auth_repository import AuthRepository
    from aicefr.storage.billing_repository import BillingRepository
    from aicefr.storage.consent_repository import ConsentRepository
    from aicefr.storage.lesson_repository import LessonRepository
    from aicefr.storage.rating_repository import RatingRepository
    from aicefr.storage.repository import Repository
    from aicefr.storage.study_repository import StudyRepository
    from aicefr.storage.task_repository import TaskRepository

    Repository(target)
    AuthRepository(target)
    ConsentRepository(target)
    TaskRepository(target)
    RatingRepository(target)
    StudyRepository(target)
    BillingRepository(target)
    LessonRepository(target, seed=False)
    AuditLog(target, "identity")


# audience: student | teacher; path_id: the draft path a teacher saved it as.
PLAN_INDEXES = {"learning_plan": [(("plan_id",), True), (("account_id", "active"), False)]}


def _learning_plan(db: Database, target: str) -> None:
    ensure_indexes(db, PLAN_INDEXES, "migration-2")


def _metering(db: Database, target: str) -> None:
    # usage_ledger is unique on (key, action): one charge per response and action.
    # credit_grant is unique on (source, ref): one credit per top-up.
    ensure_indexes(
        db,
        {
            "usage_ledger": [
                (("entry_id",), True),
                (("key", "action"), True),
                (("user_ref", "created_at"), False),
                (("state", "created_at"), False),
            ],
            "credit_wallet": [(("user_ref",), True)],
            "free_quota": [(("user_ref", "period"), True)],
            "credit_grant": [(("grant_id",), True), (("source", "ref"), True)],
        },
        "migration-3",
    )


def _classrooms(db: Database, target: str) -> None:
    # classroom.code is unique: a join code names one class.
    ensure_indexes(
        db,
        {
            "classroom": [(("class_id",), True), (("code",), True), (("teacher_id",), False)],
            "class_member": [(("class_id", "account_id"), True), (("account_id",), False)],
            "assignment": [(("assignment_id",), True), (("class_id", "due_at"), False)],
        },
        "migration-4",
    )


def _replay(db: Database, target: str) -> None:
    # One answer per moment of a response; read back per learner.
    ensure_indexes(
        db,
        {"replay_label": [(("response_id", "moment_id"), True), (("account_id",), False)]},
        "migration-5",
    )


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "baseline: the collections of D044", _baseline),
    Migration(
        2,
        "learning_plan: personal and teacher-drafted paths composed by the path model (D046)",
        _learning_plan,
    ),
    Migration(3, "metering: usage ledger, wallets, free quota, top-ups (D049)", _metering),
    Migration(4, "classrooms: classes, members, assignments (D054)", _classrooms),
    Migration(5, "replay_label: guided listening with control moments (D056)", _replay),
)

LATEST = MIGRATIONS[-1].version


def _ledger(db: Database):
    ledger = db[COLLECTION]
    ledger.create_index("version", unique=True, name="u_version")
    return ledger


def applied(target: str | Path) -> dict[int, str]:
    """The versions recorded in the store, with when each was applied."""
    rows = _ledger(database(target)).find({}, {"version": 1, "applied_at": 1})
    return {int(r["version"]): r["applied_at"] for r in rows}


def pending(target: str | Path) -> list[Migration]:
    done = applied(target)
    return [m for m in MIGRATIONS if m.version not in done]


def migrate(target: str | Path) -> list[int]:
    """Bring the store at `target` to LATEST; the versions this call recorded."""
    db = database(target)
    ledger = _ledger(db)
    done = applied(target)
    ran: list[int] = []
    for m in MIGRATIONS:
        if m.version in done:
            continue
        m.apply(db, str(target))
        try:
            ledger.insert_one({"version": m.version, "name": m.name, "applied_at": now_iso()})
        except IntegrityError:
            continue  # another process recorded it first, after running it too
        ran.append(m.version)
    return ran


_current: set[str] = set()
_current_lock = threading.Lock()


def ensure_current(target: str | Path) -> None:
    """`migrate` once per store per process, for repositories of collections added after D044."""
    key = str(target)
    if key in _current:
        return
    with _current_lock:
        if key not in _current:
            migrate(key)
            _current.add(key)


def forget_current() -> None:
    """Make the next `ensure_current` migrate again: for tests that drop a database."""
    with _current_lock:
        _current.clear()


def snapshot(target: str | Path) -> str:
    """The structure of a store: each collection and its indexes, as sorted JSON.

    Internal collections (the counters, the ledger) are left out; what a
    reader of the data dictionary needs is the data's own collections.
    """
    db = database(target)
    out = {}
    for name in sorted(db.list_collection_names()):
        if name.startswith("_") or name == COLLECTION:
            continue
        indexes = []
        for spec in db[name].list_indexes():
            if spec["name"] == "_id_":
                continue
            indexes.append(
                {
                    "name": spec["name"],
                    "keys": [k for k, _ in spec["key"].items()],
                    "unique": bool(spec.get("unique", False)),
                }
            )
        out[name] = sorted(indexes, key=lambda i: i["name"])
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"
