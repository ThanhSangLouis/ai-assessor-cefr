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
    from aicefr.storage.lesson_repository import LessonRepository
    from aicefr.storage.rating_repository import RatingRepository
    from aicefr.storage.repository import Repository
    from aicefr.storage.study_repository import StudyRepository
    from aicefr.storage.task_repository import TaskRepository

    Repository(target)
    AuthRepository(target)
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


def _terms(db: Database, target: str) -> None:
    """D058: the research consent form is gone; accepting the terms replaces it.

    A standing signature that allowed keeping recordings becomes the account's
    `terms_accepted_at`, dated when it was signed, so nobody who could submit
    before has to accept again. Then the consent collection is dropped. Run on
    a store with no consent collection (the learning or metering database), it
    does nothing.
    """
    if "consent" not in db.list_collection_names():
        return
    for row in db["consent"].find({"withdrawn_at": None, "audio_storage_allowed": 1}):
        db["account"].update_one(
            {"account_id": row["account_id"], "terms_accepted_at": None},
            {"$set": {"terms_accepted_at": row["signed_at"]}},
        )
    db.drop_collection("consent")


# ---------------------------------------------------------------- D060
# One collection per aggregate root of the class diagram: the parts of an
# aggregate move into its document. Each step copies first and drops the old
# collection only after, and finds nothing to do the second time.


def _has(db: Database, name: str) -> bool:
    return name in db.list_collection_names()


def _d060_classroom(db: Database) -> None:
    """`class_member` and `assignment` become `classroom.members` / `.assignments`."""
    if _has(db, "class_member") or _has(db, "assignment"):
        for c in db["classroom"].find({}, {"class_id": 1}):
            cid = c["class_id"]
            members = [
                m["account_id"]
                for m in db["class_member"].find({"class_id": cid}).sort("joined_at", 1)
            ]
            assignments = [
                {k: a.get(k) for k in _ASSIGNMENT_KEYS}
                for a in db["assignment"].find({"class_id": cid}).sort("created_at", 1)
            ]
            db["classroom"].update_one(
                {"_id": c["_id"]}, {"$set": {"members": members, "assignments": assignments}}
            )
        db.drop_collection("class_member")
        db.drop_collection("assignment")
    if _has(db, "classroom"):
        for key in ("members", "assignments"):
            db["classroom"].update_many({key: {"$exists": False}}, {"$set": {key: []}})
    ensure_indexes(db, D060_INDEXES["classroom"], "migration-7-classroom")


def _d060_study(db: Database) -> None:
    """`study_participant` and `study_survey` become `study.participants`."""
    if _has(db, "study_participant") or _has(db, "study_survey"):
        for st in db["study"].find({}, {"study_id": 1}):
            sid = st["study_id"]
            surveys = {r["account_id"]: r for r in db["study_survey"].find({"study_id": sid})}
            participants = []
            for p in db["study_participant"].find({"study_id": sid}).sort("code", 1):
                survey = surveys.get(p["account_id"])
                participants.append(
                    {
                        "code": p["code"],
                        "account_id": p["account_id"],
                        "arm": p["arm"],
                        "enrolled_at": p["enrolled_at"],
                        "withdrawn_at": p.get("withdrawn_at"),
                        "survey_answers": json.loads(survey["answers_json"]) if survey else None,
                        "surveyed_at": survey.get("submitted_at") if survey else None,
                    }
                )
            db["study"].update_one({"_id": st["_id"]}, {"$set": {"participants": participants}})
        db.drop_collection("study_participant")
        db.drop_collection("study_survey")
    if _has(db, "study"):
        db["study"].update_many(
            {"participants": {"$exists": False}}, {"$set": {"participants": []}}
        )


_ASSIGNMENT_KEYS = (
    "assignment_id", "task_id", "note", "due_on", "due_at", "created_by", "created_at",
)  # fmt: skip

# The indexes of the D060 collections, by the aggregate that owns them.
D060_INDEXES: dict[str, dict] = {
    "classroom": {
        "classroom": [
            (("class_id",), True),
            (("code",), True),
            (("teacher_id",), False),
            (("members",), False),
            (("assignments.assignment_id",), False),
        ]
    },
}

D060_STEPS: tuple[Callable[[Database], None], ...] = (_d060_classroom, _d060_study)


def _d060(db: Database, target: str) -> None:
    """D060: the collections follow the class diagram (one per aggregate root)."""
    for step in D060_STEPS:
        step(db)


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
    Migration(6, "terms: research consent replaced by account.terms_accepted_at (D058)", _terms),
    Migration(7, "one collection per aggregate root of the class diagram (D060)", _d060),
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
