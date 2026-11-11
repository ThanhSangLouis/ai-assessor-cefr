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
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pymongo.database import Database

from aicefr.storage.db import IntegrityError, database, ensure_indexes, now_iso

COLLECTION = "schema_migrations"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[Database, str], None]


def _baseline(db: Database, target: str) -> None:
    """Every collection and index up to D044, as the repositories create them.

    D078: the blind rating and the feedback study are gone, so a new store no
    longer gets their collections (migration 11 drops them from an older one)."""
    from aicefr.storage.audit_repository import AuditLog
    from aicefr.storage.auth_repository import AuthRepository
    from aicefr.storage.billing_repository import BillingRepository
    from aicefr.storage.lesson_repository import LessonRepository
    from aicefr.storage.repository import Repository
    from aicefr.storage.task_repository import TaskRepository

    Repository(target)
    AuthRepository(target)
    TaskRepository(target)
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


def _d078_research_data(db: Database, target: str) -> None:
    """The data of what D078 removed goes with it: blind rating, feedback study, exam part.

    `rating_batch` and `study` are dropped; `response.machine_seen` (who saw the
    machine's result, for the blind rating), `task.part` (P3/P4/P5) and the
    measurement error an administrator set (D042) are removed, and the shipped
    path loses its "sample, waiting for review" wording. Approved by the project
    owner on 01/11/2026. It cannot be undone.
    """
    for name in ("rating_batch", "study"):
        if _has(db, name):
            db.drop_collection(name)
    if _has(db, "response"):
        db["response"].update_many(
            {"machine_seen": {"$exists": True}}, {"$unset": {"machine_seen": ""}}
        )
    if _has(db, "task"):
        db["task"].update_many({"part": {"$exists": True}}, {"$unset": {"part": ""}})
    if _has(db, "system"):
        db["system"].delete_many({"key": "assessment.measurement_error"})
    # The path shipped with the system is approved content now: its "sample,
    # waiting for review" title and note go -- unless a teacher already changed them.
    if _has(db, "path"):
        db["path"].update_one(
            {"path_id": "path-sample", "title": "Lộ trình mẫu: Nói tiếng Anh A1 → C2"},
            {"$set": {"title": "Nói tiếng Anh A1 → C2"}},
        )
        row = db["path"].find_one({"path_id": "path-sample"}, {"description": 1}) or {}
        note = " Nội dung mẫu, chờ giảng viên Khoa Ngoại ngữ duyệt."
        if note in (row.get("description") or ""):
            db["path"].update_one(
                {"path_id": "path-sample"},
                {"$set": {"description": row["description"].replace(note, "")}},
            )


def _d081_recovery_code(db: Database, target: str) -> None:
    """The recovery codes of D065 go: a forgotten password is replaced by email (D079).

    Only the bcrypt hash of each code and when it was made were kept; both are
    removed from every account. Approved by the project owner on 01/11/2026.
    """
    if _has(db, "account"):
        db["account"].update_many(
            {
                "$or": [
                    {"recovery_hash": {"$exists": True}},
                    {"recovery_issued_at": {"$exists": True}},
                ]
            },
            {"$unset": {"recovery_hash": "", "recovery_issued_at": ""}},
        )


def _d082_review_session(db: Database, target: str) -> None:
    """Reviewing a response becomes its own `review_session` (D082).

    `response.review_lock` (who may decide now) and `response.review_visits`
    (when each teacher opened it and left, D041) move into one session per
    response, `lock` and `visits`; the response keeps the submission, the
    result and the decisions. Nothing is lost: a response with neither gets no
    session, which is what a response nobody has opened has.
    """
    ensure_indexes(db, {"review_session": [(("response_id",), True)]}, "migration-13")
    if not _has(db, "response"):
        return
    moved = {"review_lock": 1, "review_visits": 1, "response_id": 1}
    held = {"$or": [{"review_lock": {"$ne": None}}, {"review_visits.0": {"$exists": True}}]}
    for r in db["response"].find(held, moved):
        db["review_session"].update_one(
            {"response_id": r["response_id"]},
            {
                "$setOnInsert": {
                    "lock": r.get("review_lock"),
                    "visits": r.get("review_visits") or [],
                }
            },
            upsert=True,
        )
    db["response"].update_many(
        {"$or": [{"review_lock": {"$exists": True}}, {"review_visits": {"$exists": True}}]},
        {"$unset": {"review_lock": "", "review_visits": ""}},
    )


def _d083_practice_tasks(db: Database, target: str) -> None:
    """The practice tasks of D023 go, with every attempt at them (D083).

    The path's lessons are what a learner practises with (D025, D068); nobody
    could start a practice task since D078. Their tasks, the responses made on
    them and those recordings are deleted; `response.purpose` and the practice
    fields of a task go, and the task index on (`purpose`, `active`) becomes one
    on `active`. The ledger keeps its entries: what was charged stays charged.
    Approved by the project owner on 01/11/2026. It cannot be undone.
    """
    if _has(db, "response"):
        practice = {"purpose": "practice"}
        recordings = [r.get("audio_path") for r in db["response"].find(practice, {"audio_path": 1})]
        ids = [r["response_id"] for r in db["response"].find(practice, {"response_id": 1})]
        db["response"].delete_many(practice)
        if _has(db, "review_session"):
            db["review_session"].delete_many({"response_id": {"$in": ids}})
        db["response"].update_many({"purpose": {"$exists": True}}, {"$unset": {"purpose": ""}})
        _drop_recordings(recordings)
    if _has(db, "task"):
        db["task"].delete_many({"purpose": "practice"})
        db["task"].update_many(
            {},
            {
                "$unset": {
                    "purpose": "",
                    "criterion": "",
                    "missions_json": "",
                    "tips_json": "",
                    "reference_text": "",
                }
            },
        )
        present = {ix["name"] for ix in db["task"].list_indexes()}
        if "i_purpose_active" in present:
            db["task"].drop_index("i_purpose_active")
    ensure_indexes(db, {"task": [(("active",), False)]}, "migration-14")


def _drop_recordings(paths: list[str | None]) -> None:
    """Delete recordings where the speech service keeps them; a miss is logged, not fatal."""
    from aicefr.config import get_settings
    from aicefr.infra.blobs import blob_store, key_of

    found = [(p, key_of(p)) for p in paths if key_of(p)]
    if not found:
        return
    blobs = blob_store(get_settings())
    for path, key in found:
        try:
            blobs.delete(key)
            if path and Path(path).is_absolute():
                Path(path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - the documents are gone; a stray file is not
            logger.warning("could not delete recording %s", key)


PAYMENT_FIELDS = (
    "gateway", "live", "checkout_ref", "reference", "result_code", "settled_at", "events"
)  # fmt: skip


def _d084_payment(db: Database, target: str) -> None:
    """How the gateway took the money leaves the order for its `payment` (D084).

    Each order keeps what was bought -- runs, money, status, buyer, deadline,
    when the runs reached the wallet -- and gets one payment holding the
    gateway, real money or not, the checkout and transaction numbers, the
    result code, when it was settled and the gateway's messages. The order's
    index on (`gateway`, `checkout_ref`) moves with them. Nothing is lost.
    """
    ensure_indexes(
        db,
        {"payment": [(("order_id",), True), (("gateway", "checkout_ref"), False)]},
        "migration-15",
    )
    if not _has(db, "order"):
        return
    for o in db["order"].find({"gateway": {"$exists": True}}):
        paid = {f: o.get(f) for f in PAYMENT_FIELDS}
        paid["gateway"] = paid["gateway"] or "none"
        paid["live"] = bool(paid["live"])
        paid["events"] = paid["events"] or []
        db["payment"].update_one({"order_id": o["order_id"]}, {"$setOnInsert": paid}, upsert=True)
    db["order"].update_many(
        {"gateway": {"$exists": True}}, {"$unset": {f: "" for f in PAYMENT_FIELDS}}
    )
    present = {ix["name"] for ix in db["order"].list_indexes()}
    if "i_gateway_checkout_ref" in present:
        db["order"].drop_index("i_gateway_checkout_ref")


def _d085_built_in(db: Database, target: str) -> None:
    """A path shipped with the system is `built_in`, no longer `sample` (D085).

    Only the name changes: the path is approved content since D078. A lesson
    keeps `sample` inside the versions already saved, which read it either way.
    """
    if _has(db, "path"):
        db["path"].update_many({"sample": {"$exists": True}}, {"$rename": {"sample": "built_in"}})


def _d088_push_subscription(db: Database, target: str) -> None:
    """Where to send a browser's notifications: `push_subscription` (D088).

    One document per browser that allowed SpeakUp's notifications, keyed by
    the push service's endpoint; an account may have several (a phone and a
    laptop). Nothing to move: the collection is new.
    """
    ensure_indexes(
        db,
        {"push_subscription": [(("endpoint",), True), (("account_id",), False)]},
        "migration-17",
    )


def _d089_word_drill(db: Database, target: str) -> None:
    """The words a learner says again from one of their recordings: `word_drill` (D089).

    One document per learner, response and word, holding its takes. Nothing to
    move: the collection is new, and a `review_item` keeps its own shape (a
    word sent to review from a drill points back with `drill_id`).
    """
    ensure_indexes(
        db,
        {
            "word_drill": [
                (("drill_id",), True),
                (("account_id", "response_id", "word"), True),
                (("account_id", "passed", "updated_at"), False),
            ]
        },
        "migration-18",
    )


def _d090_drill_passage(db: Database, target: str) -> None:
    """Reading passages written around a learner's unclear words: `drill_passage` (D090).

    One document per passage, holding the words it was written for and its
    takes. New collection, nothing to move.
    """
    ensure_indexes(
        db,
        {
            "drill_passage": [
                (("passage_id",), True),
                (("account_id", "created_at"), False),
            ]
        },
        "migration-19",
    )


# Where an account made before D103 without an email gets one: a subdomain
# that receives no mail, so nothing is ever sent to it.
D103_EMAIL_DOMAIN = "demo.speakup.fit"


def _drop_index(db: Database, collection: str, name: str) -> None:
    if _has(db, collection) and name in {ix["name"] for ix in db[collection].list_indexes()}:
        db[collection].drop_index(name)


def _d103_account_email(db: Database) -> dict[str, str]:
    """Every account signs in with an email; the pseudonym goes. Returns pseudonym -> id."""
    if not _has(db, "account"):
        return {}
    accounts = db["account"]
    ids = {
        a["pseudonym"]: a["account_id"]
        for a in accounts.find(
            {"pseudonym": {"$type": "string"}}, {"pseudonym": 1, "account_id": 1}
        )
    }
    taken = set(accounts.distinct("email"))
    for a in accounts.find(
        {"email": {"$not": {"$type": "string"}}}, {"account_id": 1, "pseudonym": 1}
    ):
        base = (a.get("pseudonym") or a["account_id"]).lower()
        email, n = f"{base}@{D103_EMAIL_DOMAIN}", 1
        while email in taken:
            n += 1
            email = f"{base}-{n}@{D103_EMAIL_DOMAIN}"
        taken.add(email)
        # An administrator made it, so it keeps its free runs (verified, as
        # D103 counts such accounts) and gets no reminders at a domain without mail.
        accounts.update_one(
            {"account_id": a["account_id"]},
            {"$set": {"email": email, "email_verified": 1, "email_reminders": 0}},
        )
        logger.info("account %s signs in as %s from now on", a["account_id"], email)
    _drop_index(db, "account", "u_pseudonym")
    _drop_index(db, "account", "i_pseudonym_lower")
    # Partial before (accounts without an email), whole from now on.
    old = {ix["name"]: ix for ix in accounts.list_indexes()}.get("u_email")
    if old is not None and "partialFilterExpression" in old:
        accounts.drop_index("u_email")
    accounts.create_index([("email", 1)], unique=True, name="u_email")
    accounts.update_many(
        {},
        {"$unset": {"pseudonym": "", "pseudonym_lower": "", "seen_markers": ""}},
    )
    return ids


def _d103_fields(db: Database, target: str) -> None:
    """The pseudonym and the fields nothing reads go (D103).

    An account is its email from now on: one without becomes
    `<pseudonym>@demo.speakup.fit`. Where a pseudonym named a person -- the
    audit log's actor, who changed a setting, who overrode a lesson step -- the
    account id takes its place, as far as this store knows the accounts.
    Removed for good: `response.speaker_id` (the account id says whose it is),
    the review lock's copied name, a path's "built in" mark, the "seen" markers (D028's new-results
    badge goes with them), who made a task or a path and who edited or
    published a lesson or a price list (the audit log keeps who did what), the
    model name and token counts on an upgrade and a passage (the ledger keeps
    the tokens), a plan's model version, a payment's result code, gateway and
    money mode (a deployment runs one gateway), an order's kind (every order
    is a run pack; the plan orders of D033 are deleted), the review visits and
    a decision's opening time (D041), the path a plan was saved as, the price
    version on a ledger entry, a phrase card's review count and when an
    achievement was seen (its "new" mark goes with it). Two fields that other
    fields already give go too: a ledger entry's `held` (free runs plus wallet
    runs) and a unit's `position` (its place in the path's list, put in that
    order here); a passage's band, used to write it and never read after. Approved
    by the project owner on 10/11/2026; the data was test data.
    """
    ids = _d103_account_email(db)
    for name in ids:  # an actor or an author recorded by pseudonym
        aid = ids[name]
        if _has(db, "audit_log"):
            db["audit_log"].update_many({"actor_id": name}, {"$set": {"actor_id": aid}})
        if _has(db, "system"):
            db["system"].update_many({"updated_by": name}, {"$set": {"updated_by": aid}})
        if _has(db, "attempt"):
            db["attempt"].update_many({"overridden_by": name}, {"$set": {"overridden_by": aid}})
    unset = {
        "response": ("speaker_id", "coach_upgrade.provider", "coach_upgrade.model",
                     "coach_upgrade.prompt_version"),
        "task": ("created_by",),
        "path": ("created_by", "built_in"),
        "lesson": ("updated_by",),
        "payment": ("result_code", "gateway", "live"),
        "drill_passage": ("provider", "model", "prompt_version", "input_tokens", "output_tokens",
                          "band"),
        "price_list": ("changed_by",),
        "review_session": ("visits",),
        "learning_plan": ("model_version", "path_id"),
        "ledger": ("price_version", "held"),
        "achievement": ("seen_at",),
    }  # fmt: skip
    for collection, names in unset.items():
        if _has(db, collection):
            db[collection].update_many({}, {"$unset": {n: "" for n in names}})
    _drop_index(db, "response", "i_speaker_id")
    _drop_index(db, "payment", "i_gateway_checkout_ref")
    _drop_index(db, "order", "i_created_by_kind")
    if _has(db, "payment"):
        db["payment"].create_index([("checkout_ref", 1)], name="i_checkout_ref")
    if _has(db, "order"):
        db["order"].create_index([("created_by", 1)], name="i_created_by")
    if _has(db, "order"):
        # Only run packs are orders now: the plan orders of D033 go, with their payments.
        gone = [o["order_id"] for o in db["order"].find({"kind": {"$nin": [None, "credits"]}})]
        if gone:
            db["order"].delete_many({"order_id": {"$in": gone}})
            if _has(db, "payment"):
                db["payment"].delete_many({"order_id": {"$in": gone}})
        db["order"].update_many(
            {"runs": {"$exists": False}, "seats": {"$exists": True}}, {"$rename": {"seats": "runs"}}
        )
        db["order"].update_many({}, {"$unset": {"kind": ""}})
    if _has(db, "review_session"):
        db["review_session"].update_many(
            {"lock.reviewer_name": {"$exists": True}}, {"$unset": {"lock.reviewer_name": ""}}
        )
    if _has(db, "lesson"):
        for row in db["lesson"].find(
            {"$or": [{"versions.published_by": {"$exists": True}},
                     {"media.created_by": {"$exists": True}}]},
            {"lesson_id": 1, "versions": 1, "media": 1},
        ):  # fmt: skip
            db["lesson"].update_one(
                {"lesson_id": row["lesson_id"]},
                {
                    "$set": {
                        "versions": [
                            {k: v for k, v in x.items() if k != "published_by"}
                            for x in row.get("versions") or []
                        ],
                        "media": [
                            {k: v for k, v in x.items() if k != "created_by"}
                            for x in row.get("media") or []
                        ],
                    }
                },
            )
    if _has(db, "response"):
        for row in db["response"].find(
            {"$or": [{"reviews.opened_at": {"$exists": True}},
                     {"coach_upgrade.phrases.reviews": {"$exists": True}}]},
            {"response_id": 1, "reviews": 1, "coach_upgrade.phrases": 1},
        ):  # fmt: skip
            reviews = row.get("reviews") or []
            kept = [{k: v for k, v in r.items() if k != "opened_at"} for r in reviews]
            sets: dict = {"reviews": kept}
            phrases = (row.get("coach_upgrade") or {}).get("phrases")
            if phrases is not None:
                sets["coach_upgrade.phrases"] = [
                    {k: v for k, v in x.items() if k != "reviews"} for x in phrases
                ]
            db["response"].update_one({"response_id": row["response_id"]}, {"$set": sets})
    if _has(db, "path"):
        placed = db["path"].find({"units.position": {"$exists": True}}, {"path_id": 1, "units": 1})
        for row in placed:
            units = sorted(row.get("units") or [], key=lambda u: u.get("position") or 0)
            kept = [{k: v for k, v in u.items() if k != "position"} for u in units]
            db["path"].update_one({"path_id": row["path_id"]}, {"$set": {"units": kept}})
    if _has(db, "price_list"):
        for row in db["price_list"].find({"history.changed_by": {"$exists": True}}):
            history = [{k: v for k, v in h.items() if k != "changed_by"} for h in row["history"]]
            db["price_list"].update_one({"_id": row["_id"]}, {"$set": {"history": history}})


# ---------------------------------------------------------------- D104
# Fewer collections and no JSON in strings: the review lock back into the
# response, the payment into its order, a phrase's review state into the
# learning store's review items, and every stored report, lesson, attempt and
# plan as a document instead of a string holding JSON.

D104_SCORE_COPIES = ("overall_0_6", "overall_band", "teacher_verified", "model_version")


def _parsed(value):
    """A stored JSON string as the document it holds; anything else as it is."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def _d104_response(db: Database) -> None:
    """The report becomes the response's own fields; the copied scores and review_session go."""
    if not _has(db, "response"):
        return
    for row in db["response"].find(
        {"$or": [{"report_json": {"$exists": True}},
                 {"coach_upgrade.phrases.box": {"$exists": True}}]},
        {"response_id": 1, "report_json": 1, "coach_upgrade": 1},
    ):  # fmt: skip
        sets: dict = {}
        report = _parsed(row.get("report_json")) or {}
        for key, value in report.items():
            if key not in ("reviews", "upgrade"):
                sets[key] = value
        upgrade = row.get("coach_upgrade") or {}
        if upgrade.get("phrases"):
            # The words stay with the upgrade; a phrase's box starts again in the
            # learning store (the data held then was test data).
            sets["coach_upgrade.phrases"] = [
                {k: v for k, v in p.items() if k in ("phrase", "meaning_vi")}
                for p in upgrade["phrases"]
            ]
        update: dict = {"$unset": {k: "" for k in ("report_json", *D104_SCORE_COPIES)}}
        if sets:
            update["$set"] = sets
        db["response"].update_one({"response_id": row["response_id"]}, update)
    if _has(db, "review_session"):
        for session in db["review_session"].find({"lock": {"$ne": None}}):
            lock = {
                k: v for k, v in session["lock"].items() if k in ("reviewer_id", "locked_until")
            }
            db["response"].update_one(
                {"response_id": session["response_id"]}, {"$set": {"review_lock": lock}}
            )
        db.drop_collection("review_session")


def _d104_order(db: Database) -> None:
    """Each payment's fields join its order; the payment collection goes."""
    if not _has(db, "payment"):
        return
    for paid in db["payment"].find({}):
        fields = {k: paid.get(k) for k in ("checkout_ref", "reference", "settled_at")}
        db["order"].update_one(
            {"order_id": paid["order_id"]},
            {"$set": {**fields, "events": paid.get("events") or []}},
        )
    db.drop_collection("payment")
    db["order"].create_index([("checkout_ref", 1)], name="i_checkout_ref")


def _d104_learning(db: Database) -> None:
    """Lessons, attempts and plans hold documents, not JSON strings."""
    if _has(db, "lesson"):
        for row in db["lesson"].find(
            {"$or": [{"draft_json": {"$exists": True}},
                     {"versions.lesson_json": {"$exists": True}}]},
            {"lesson_id": 1, "draft_json": 1, "versions": 1},
        ):  # fmt: skip
            versions = [
                {**{k: v for k, v in x.items() if k != "lesson_json"},
                 "lesson": _parsed(x.get("lesson_json", x.get("lesson")))}
                for x in row.get("versions") or []
            ]  # fmt: skip
            sets: dict = {"versions": versions}
            if "draft_json" in row:
                sets["draft"] = _parsed(row["draft_json"])
            db["lesson"].update_one(
                {"lesson_id": row["lesson_id"]}, {"$set": sets, "$unset": {"draft_json": ""}}
            )
    if _has(db, "attempt"):
        for row in db["attempt"].find(
            {"$or": [{"result_json": {"$exists": True}}, {"override_json": {"$exists": True}}]},
            {"attempt_id": 1, "result_json": 1, "override_json": 1},
        ):
            db["attempt"].update_one(
                {"attempt_id": row["attempt_id"]},
                {
                    "$set": {
                        "result": _parsed(row.get("result_json")),
                        "override": _parsed(row.get("override_json")),
                    },
                    "$unset": {"result_json": "", "override_json": ""},
                },
            )
    if _has(db, "learning_plan"):
        for row in db["learning_plan"].find(
            {"$or": [{"goal_json": {"$exists": True}}, {"plan_json": {"$exists": True}}]},
            {"plan_id": 1, "goal_json": 1, "plan_json": 1},
        ):
            db["learning_plan"].update_one(
                {"plan_id": row["plan_id"]},
                {
                    "$set": {"goal": _parsed(row.get("goal_json")),
                             "plan": _parsed(row.get("plan_json"))},
                    "$unset": {"goal_json": "", "plan_json": ""},
                },
            )  # fmt: skip


def _d104_documents(db: Database, target: str) -> None:
    """Fewer collections and no JSON strings (D104).

    `review_session` (D082) folds back into `response.review_lock`, `payment`
    (D084) into its `order`; the response's report is stored as the response's
    own fields, without the score, band, verification and model copied out of
    it; a phrase card's box leaves the upgrade (the learning store's review
    items keep it from now on, starting again); lessons, attempts and plans
    keep documents where they kept JSON strings. Approved by the project owner
    on 11/11/2026; the data was test data.
    """
    _d104_response(db)
    _d104_order(db)
    _d104_learning(db)


# ---------------------------------------------------------------- D105


def _d105_copies(db: Database, target: str) -> None:
    """Fields another field already gives go (D105).

    An attempt's step, round, speaking time, rules and verdict (its `result`
    and `override` give them) and the index on its step nothing queried; a
    lesson's "changed since published" mark (the draft compared with the
    version shown); the price list's copies of earlier versions and its counter
    (the audit log keeps every change, the version carries the number); a
    plan's copy of its goal and the path model's version inside it; a reading
    passage's words (its drills hold them). And the times written and never
    read: when a task was made, a path last changed, a unit made, a review item
    last moved, a lesson version published, a medium uploaded. The token counts
    kept with each charge and the recogniser's output count behind them go
    too: nothing read them (the coach's daily counters keep the model's). Approved by the
    project owner on 11/11/2026.
    """
    unset = {
        "attempt": ("step_id", "round", "passed", "speaking_s", "rules_version"),
        "lesson": ("draft_changed",),
        "price_list": ("history", "number"),
        "learning_plan": ("plan.goal", "plan.model_version"),
        "drill_passage": ("words",),
        "word_drill": ("word_index",),
        "ledger": ("input_tokens", "output_tokens", "usage_estimated"),
        "response": ("asr.output_tokens",),
        "task": ("created_at",),
        "path": ("updated_at",),
        "review_item": ("updated_at",),
    }
    for collection, names in unset.items():
        if _has(db, collection):
            db[collection].update_many({}, {"$unset": {n: "" for n in names}})
    _drop_index(db, "attempt", "i_lesson_id_step_id")
    if _has(db, "path"):
        for row in db["path"].find(
            {"units.created_at": {"$exists": True}}, {"path_id": 1, "units": 1}
        ):
            units = [{k: v for k, v in u.items() if k != "created_at"} for u in row["units"]]
            db["path"].update_one({"path_id": row["path_id"]}, {"$set": {"units": units}})
    if _has(db, "lesson"):
        stamped = {"$or": [{"versions.published_at": {"$exists": True}},
                           {"media.created_at": {"$exists": True}}]}  # fmt: skip
        for row in db["lesson"].find(stamped, {"lesson_id": 1, "versions": 1, "media": 1}):
            db["lesson"].update_one(
                {"lesson_id": row["lesson_id"]},
                {
                    "$set": {
                        "versions": [{k: v for k, v in x.items() if k != "published_at"}
                                     for x in row.get("versions") or []],
                        "media": [{k: v for k, v in x.items() if k != "created_at"}
                                  for x in row.get("media") or []],
                    }
                },
            )  # fmt: skip


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
    Migration(
        11,
        "blind rating, feedback study and exam part removed with their data (D078)",
        _d078_research_data,
    ),
    Migration(12, "account: the recovery code of D065 removed (D081)", _d081_recovery_code),
    Migration(
        13, "review_session: lock and visits leave the response (D082)", _d082_review_session
    ),
    Migration(14, "practice tasks and their attempts removed (D083)", _d083_practice_tasks),
    Migration(15, "payment: the gateway's part of an order on its own (D084)", _d084_payment),
    Migration(16, "path: sample renamed built_in (D085)", _d085_built_in),
    Migration(
        17, "push_subscription: a browser's Web Push endpoint (D088)", _d088_push_subscription
    ),
    Migration(18, "word_drill: words said again from a recording (D089)", _d089_word_drill),
    Migration(19, "drill_passage: passages read around unclear words (D090)", _d090_drill_passage),
    Migration(20, "account by email, pseudonym and unread fields removed (D103)", _d103_fields),
    Migration(
        21,
        "review lock, payment and phrase state folded in; no JSON strings (D104)",
        _d104_documents,
    ),
    Migration(22, "copies of other fields removed (D105)", _d105_copies),
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


_migrate_lock = threading.Lock()


def migrate(target: str | Path) -> list[int]:
    """Bring the store at `target` to LATEST; the versions this call recorded."""
    # One at a time within a process: the in-memory store of development and
    # the tests does not enforce a unique index atomically, so two threads could
    # both record a version. Processes on a real server still meet at the ledger.
    with _migrate_lock:
        return _migrate(target)


def _migrate(target: str | Path) -> list[int]:
    db = database(target)
    ledger = _ledger(db)
    done = applied(target)
    ran: list[int] = []
    for m in MIGRATIONS:
        if m.version in done:
            continue
        try:
            m.apply(db, str(target))
        except IntegrityError:
            # Another process starting at the same time inserted the same row
            # first; every step is idempotent, so running it again finishes it.
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
