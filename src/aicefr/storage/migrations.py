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


def _drop_terms(db: Database, target: str) -> None:
    """D064: no terms-of-use step any more, so the account forgets when it accepted them.

    Run on a store without accounts (the learning or metering database), or a
    second time, it changes nothing.
    """
    if "account" in db.list_collection_names():
        db["account"].update_many(
            {"terms_accepted_at": {"$exists": True}}, {"$unset": {"terms_accepted_at": ""}}
        )


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


def _rename(db: Database, old: str, new: str) -> None:
    """Move every document of `old` into `new`, then drop `old`.

    Copy rather than `rename`: `new` may exist already, made by a repository
    of this release before the migration ran.
    """
    if not _has(db, old):
        return
    rows = list(db[old].find({}, {"_id": 0}))
    if rows:
        db[new].insert_many(rows)
    db.drop_collection(old)


def _settings(db: Database, old: str, prefix: str) -> None:
    """A part's settings collection into `system`, its keys prefixed with the part."""
    if not _has(db, old):
        return
    for r in db[old].find({}, {"_id": 0}):
        db["system"].update_one(
            {"key": prefix + r["key"]},
            {"$setOnInsert": {"value": r.get("value"), "updated_by": r.get("updated_by"),
                              "updated_at": r.get("updated_at")}},
            upsert=True,
        )  # fmt: skip
    db.drop_collection(old)


def _d060_billing(db: Database) -> None:
    """`billing_order` + `billing_event` become `order`; `billing_license` becomes `license`."""
    if _has(db, "billing_order"):
        for o in db["billing_order"].find({}, {"_id": 0}):
            events = [
                {
                    "kind": e["kind"],
                    "fingerprint": e["fingerprint"],
                    "detail": json.loads(e["detail_json"]),
                    "created_at": e["created_at"],
                    "repeats": e.get("repeats", 0),
                    "last_at": e.get("last_at"),
                }
                for e in db["billing_event"].find({"order_id": o["order_id"]}).sort("event_id", 1)
            ]
            db["order"].update_one(
                {"order_id": o["order_id"]}, {"$setOnInsert": {**o, "events": events}}, upsert=True
            )
        db.drop_collection("billing_order")
    db.drop_collection("billing_event")
    if _has(db, "order"):
        # A pack of runs named its kind where the plan goes; it buys no plan.
        db["order"].update_many({"plan": "credits"}, {"$set": {"plan": None}})
    _rename(db, "billing_license", "license")
    _settings(db, "billing_setting", "billing.")


def _d060_metering(db: Database) -> None:
    """`credit_wallet` + `free_quota` + `credit_grant` become `wallet`; `usage_ledger` `ledger`.

    The ledger keeps the response's purpose from now on: `assess` becomes
    `assessment`, as `TaskPurpose` says it. Of the free quota only the latest
    cycle of each account matters -- earlier cycles are over.
    """
    if _has(db, "credit_wallet") or _has(db, "free_quota") or _has(db, "credit_grant"):
        owners = {r["user_ref"] for r in db["credit_wallet"].find({}, {"user_ref": 1})}
        owners |= {r["user_ref"] for r in db["free_quota"].find({}, {"user_ref": 1})}
        owners |= {r["user_ref"] for r in db["credit_grant"].find({}, {"user_ref": 1})}
        for who in sorted(owners):
            w = db["credit_wallet"].find_one({"user_ref": who}) or {}
            q = db["free_quota"].find_one({"user_ref": who}, sort=[("period", -1)]) or {}
            grants = [
                {k: g.get(k) for k in ("grant_id", "units", "source", "ref", "by", "created_at")}
                for g in db["credit_grant"].find({"user_ref": who}).sort("created_at", 1)
            ]
            wallet = {
                "balance": int(w.get("balance", 0)),
                "period": q.get("period", ""),
                "free_used": int(q.get("used", 0)),
                "grants": grants,
            }
            db["wallet"].update_one({"user_ref": who}, {"$setOnInsert": wallet}, upsert=True)
        for old in ("credit_wallet", "free_quota", "credit_grant"):
            db.drop_collection(old)
    if _has(db, "usage_ledger"):
        for e in db["usage_ledger"].find({}, {"_id": 0}):
            if e.get("action") == "assess":
                e["action"] = "assessment"
            db["ledger"].update_one(
                {"key": e["key"], "action": e["action"]}, {"$setOnInsert": e}, upsert=True
            )
        db.drop_collection("usage_ledger")
    # The metering repository makes no indexes of its own: the migration does.
    ensure_indexes(db, D060_INDEXES["metering"], "migration-7-metering")


def _d060_identity(db: Database) -> None:
    """Outside identities and seen markers into `account`; sessions, secrets, settings move.

    `account_identity` -> `account.identities`, `seen_marker` ->
    `account.seen_markers`, `auth_sessions` -> `session`, `server_secret` and
    `app_config` -> `system` (under `identity.secret.` and `assessment.`).
    """
    if _has(db, "account_identity"):
        for link in db["account_identity"].find().sort("linked_at", 1):
            item = {k: link[k] for k in ("provider", "subject_hash", "linked_at")}
            db["account"].update_one(
                {"account_id": link["account_id"],
                 "identities.provider": {"$ne": link["provider"]}},
                {"$push": {"identities": item}},
            )  # fmt: skip
        db.drop_collection("account_identity")
    if _has(db, "seen_marker"):
        for m in db["seen_marker"].find():
            db["account"].update_one(
                {"account_id": m["account_id"]},
                {"$set": {f"seen_markers.{m['marker']}": m["seen_at"]}},
            )
        db.drop_collection("seen_marker")
    if _has(db, "account"):
        db["account"].update_many({"identities": {"$exists": False}}, {"$set": {"identities": []}})
        db["account"].update_many(
            {"seen_markers": {"$exists": False}}, {"$set": {"seen_markers": {}}}
        )
    _rename(db, "auth_sessions", "session")
    if _has(db, "server_secret"):
        for r in db["server_secret"].find():
            db["system"].update_one(
                {"key": "identity.secret." + r["name"]},
                {"$setOnInsert": {"value": r["value_hex"], "updated_by": None,
                                  "updated_at": r.get("created_at")}},
                upsert=True,
            )  # fmt: skip
        db.drop_collection("server_secret")
    if _has(db, "app_config"):
        for r in db["app_config"].find({}, {"_id": 0}):
            key = r.pop("key")
            db["system"].update_one({"key": "assessment." + key}, {"$setOnInsert": r}, upsert=True)
        db.drop_collection("app_config")


def _d060_response(db: Database) -> None:
    """Reviews, the lock, review visits and replay labels into `response`.

    `review_action` -> `response.reviews` (numbered by the old id, stamped with
    the opening of the visit it closed), `review_lock` -> `response.review_lock`,
    `review_session` -> `response.review_visits`, `replay_label` ->
    `response.replay_labels`.
    """
    if not _has(db, "response"):
        return
    if _has(db, "review_session"):
        for v in db["review_session"].find().sort("id", 1):
            visit = {k: v.get(k) for k in ("reviewer_id", "opened_at", "decided_at", "action")}
            db["response"].update_one(
                {"response_id": v["response_id"], "review_visits": {"$ne": visit}},
                {"$push": {"review_visits": visit}},
            )
    if _has(db, "review_action"):
        for r in db["review_action"].find().sort("id", 1):
            visit = (
                db["review_session"].find_one(
                    {"response_id": r["response_id"], "reviewer_id": r["reviewer_id"],
                     "decided_at": {"$gte": r["created_at"]}},
                    sort=[("decided_at", 1)],
                )
                if _has(db, "review_session")
                else None
            )  # fmt: skip
            review = {
                "review_id": r["id"],
                "reviewer_id": r["reviewer_id"],
                "old_score": r.get("old_score"),
                "new_score": r.get("new_score"),
                "old_band": r.get("old_band"),
                "new_band": r.get("new_band"),
                "reason": r.get("reason") or "",
                "created_at": r["created_at"],
                "opened_at": visit["opened_at"] if visit else None,
            }
            db["response"].update_one(
                {"response_id": r["response_id"], "reviews.review_id": {"$ne": r["id"]}},
                {"$push": {"reviews": review}},
            )
        # Reviews are numbered on from where the old series stopped.
        last = db["_counters"].find_one({"_id": "review_action"})
        if last:
            db["_counters"].update_one(
                {"_id": "review"}, {"$max": {"seq": last["seq"]}}, upsert=True
            )
    if _has(db, "review_lock"):
        for lock in db["review_lock"].find():
            held = {k: lock[k] for k in ("reviewer_id", "reviewer_name", "locked_until")}
            db["response"].update_one(
                {"response_id": lock["response_id"]}, {"$set": {"review_lock": held}}
            )
    if _has(db, "replay_label"):
        for x in db["replay_label"].find({}, {"_id": 0}).sort("moment_id", 1):
            db["response"].update_one(
                {
                    "response_id": x["response_id"],
                    "replay_labels.moment_id": {"$ne": x["moment_id"]},
                },
                {"$push": {"replay_labels": x}},
            )
    for old in ("review_session", "review_action", "review_lock", "replay_label"):
        db.drop_collection(old)


def _d060_rating(db: Database) -> None:
    """Sheets and ratings into `rating_batch.ratings`; `machine_seen` into the response.

    `rating_assignment` + `research_rating` -> `rating_batch.ratings` (a sheet
    and its rating are one `Rating`), `rating_batch.status` -> `closed`,
    `machine_seen` -> `response.machine_seen`.
    """
    if _has(db, "machine_seen"):
        for m in db["machine_seen"].find().sort("first_seen", 1):
            item = {"account_id": m["account_id"], "first_seen": m.get("first_seen"),
                    "via": m.get("via")}  # fmt: skip
            db["response"].update_one(
                {
                    "response_id": m["response_id"],
                    "machine_seen.account_id": {"$ne": m["account_id"]},
                },
                {"$push": {"machine_seen": item}},
            )
        db.drop_collection("machine_seen")
    if _has(db, "rating_assignment"):
        given = (
            {r["assignment_id"]: r for r in db["research_rating"].find({}, {"_id": 0})}
            if _has(db, "research_rating")
            else {}
        )
        for b in db["rating_batch"].find({}, {"batch_id": 1}):
            sheets = []
            for x in db["rating_assignment"].find({"batch_id": b["batch_id"]}).sort("position", 1):
                rating = given.get(x["assignment_id"], {})
                sheets.append(
                    {
                        "assignment_id": x["assignment_id"],
                        "response_id": x["response_id"],
                        "rater_id": x["rater_id"],
                        "slot": x["slot"],
                        "position": x["position"],
                        "opened_at": x.get("opened_at"),
                        **{k: rating.get(k) for k in _RATING_KEYS},
                        "unscorable": rating.get("unscorable", 0),
                    }
                )
            db["rating_batch"].update_one({"_id": b["_id"]}, {"$set": {"ratings": sheets}})
        db.drop_collection("rating_assignment")
        db.drop_collection("research_rating")
    if _has(db, "rating_batch"):
        for b in db["rating_batch"].find({"closed": {"$exists": False}}, {"status": 1}):
            db["rating_batch"].update_one(
                {"_id": b["_id"]},
                {"$set": {"closed": b.get("status") == "closed"}, "$unset": {"status": ""}},
            )
        db["rating_batch"].update_many({"ratings": {"$exists": False}}, {"$set": {"ratings": []}})


def _d060_learning(db: Database) -> None:
    """Units into `path`, versions and media into `lesson`, attempts into `attempt`.

    `lesson_path` + `lesson_unit` -> `path` (units embedded, in their order),
    `lesson_version` -> `lesson.versions`, `lesson_media` -> the media of the
    lesson whose step points at it (by the key the upload put in its file
    name), `step_attempt` -> `attempt`, `lesson_meta` -> `system` (`learning.`).
    """
    if _has(db, "lesson_path"):
        for p in db["lesson_path"].find({}, {"_id": 0}):
            units = [
                {k: v for k, v in u.items() if k not in ("_id", "path_id")}
                for u in db["lesson_unit"].find({"path_id": p["path_id"]}).sort("position", 1)
            ]
            db["path"].update_one(
                {"path_id": p["path_id"]}, {"$setOnInsert": {**p, "units": units}}, upsert=True
            )
        db.drop_collection("lesson_path")
        db.drop_collection("lesson_unit")
    if _has(db, "lesson_version"):
        for v in db["lesson_version"].find({}, {"_id": 0}).sort("version", 1):
            lid = v.pop("lesson_id")
            db["lesson"].update_one(
                {"lesson_id": lid, "versions.version": {"$ne": v["version"]}},
                {"$push": {"versions": v}},
            )
        db.drop_collection("lesson_version")
    if _has(db, "lesson_media"):
        for m in db["lesson_media"].find({}, {"_id": 0}):
            # Uploads are named `lesson-media-<lesson>-<step>-...`: the lesson
            # they were made for. A file of another name is kept with no lesson
            # rather than lost.
            owner = None
            blob = str(m.get("blob_key") or "")
            if blob.startswith("lesson-media-"):
                for row in db["lesson"].find({}, {"lesson_id": 1}):
                    if blob.startswith(f"lesson-media-{row['lesson_id']}-"):
                        owner = row["lesson_id"]
                        break
            if owner is None:
                hit = db["lesson"].find_one({"draft_json": {"$regex": m["media_key"]}})
                owner = hit["lesson_id"] if hit else None
            if owner is not None:
                db["lesson"].update_one(
                    {"lesson_id": owner, "media.media_key": {"$ne": m["media_key"]}},
                    {"$push": {"media": m}},
                )
        db.drop_collection("lesson_media")
    if _has(db, "lesson"):
        for key in ("versions", "media"):
            db["lesson"].update_many({key: {"$exists": False}}, {"$set": {key: []}})
    _rename(db, "step_attempt", "attempt")
    _settings(db, "lesson_meta", "learning.")


_RATING_KEYS = (
    "score_range", "score_accuracy", "score_fluency", "score_coherence", "score_phonology",
    "score_overall", "band", "unscorable_reason", "reason", "submitted_at",
)  # fmt: skip

_ASSIGNMENT_KEYS = (
    "assignment_id", "task_id", "note", "due_on", "due_at", "created_by", "created_at",
)  # fmt: skip

# The indexes of the D060 collections, by the aggregate that owns them.
D060_INDEXES: dict[str, dict] = {
    # usage: one entry per (response, purpose), so a charge is never taken twice.
    "metering": {
        "wallet": [(("user_ref",), True)],
        "ledger": [
            (("entry_id",), True),
            (("key", "action"), True),
            (("user_ref", "created_at"), False),
            (("state", "created_at"), False),
        ],
    },
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

D060_STEPS: tuple[Callable[[Database], None], ...] = (
    _d060_classroom,
    _d060_study,
    _d060_billing,
    _d060_metering,
    _d060_identity,
    _d060_response,
    _d060_rating,
    _d060_learning,
)


def _d060(db: Database, target: str) -> None:
    """D060: the collections follow the class diagram (one per aggregate root)."""
    for step in D060_STEPS:
        step(db)


def _d071_class_teachers(db: Database, target: str) -> None:
    """A class has teachers, not a teacher (D071): `teacher_id` becomes `teacher_ids`."""
    if not _has(db, "classroom"):
        return
    for c in db["classroom"].find({"teacher_ids": {"$exists": False}}, {"teacher_id": 1}):
        owner = c.get("teacher_id")
        db["classroom"].update_one(
            {"_id": c["_id"]},
            {"$set": {"teacher_ids": [owner] if owner else []}, "$unset": {"teacher_id": ""}},
        )
    ensure_indexes(db, {"classroom": [(("teacher_ids",), False)]}, "migration-9")


def _d075_classroom_code(db: Database, target: str) -> None:
    """Classes set no assessments and nobody joins with a code (D075).

    The unique index on `code`, the index on the `teacher_id` replaced by
    `teacher_ids` in D071 and the index on the assignments go. Only indexes:
    what a class document already holds stays as it is, unread.
    """
    if not _has(db, "classroom"):
        return
    present = {ix["name"] for ix in db["classroom"].list_indexes()}
    for name in ("u_code", "i_teacher_id", "i_assignments.assignment_id"):
        if name in present:
            db["classroom"].drop_index(name)


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
    Migration(8, "terms: account.terms_accepted_at dropped, no terms step (D064)", _drop_terms),
    Migration(
        9, "classroom.teacher_ids: a class has one or more teachers (D071)", _d071_class_teachers
    ),
    Migration(
        10, "classroom: no join code, assignment or teacher_id index (D075)", _d075_classroom_code
    ),
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
