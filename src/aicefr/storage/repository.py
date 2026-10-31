"""Persistence for assessment results. Implements FR-32 to FR-38.

One MongoDB database (D048); the collections follow the entity relationship
diagram in SDD section 5 closely, one document per former row.

Privacy rule: the speaker collection holds only pseudonym codes. Never store a
real name, a student ID, or any contact detail in this database.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from aicefr.contracts import (
    AppConfig,
    ReasonCode,
    Response,
    ResponseStatus,
    Review,
    ReviewLock,
    TaskPurpose,
)
from aicefr.infra.blobs import key_of
from aicefr.storage.audit_repository import prepare as prepare_audit
from aicefr.storage.audit_repository import recent_entries, write_audit
from aicefr.storage.db import (
    SYSTEM,
    IntegrityError,
    MongoStore,
    ensure_indexes,
    ensure_system,
    fields,
    next_id,
)
from aicefr.storage.db import now_iso as _now

# The collections of the assessment service and the indexes that stand for the
# former primary keys and UNIQUE constraints.
#
# response.purpose is 'practice' for a practice attempt (D023): never in the
# teacher queue, the research export, or the class scoring statistics.
# A response's document holds its parts (D060): `reviews` (each teacher
# decision), `review_lock` (who may decide right now), `review_visits` (when a
# teacher opened it and when they left, D041 -- the lock is cleared on decision,
# so its start is kept here) and `replay_labels` (guided listening, D056).
# The settings an administrator changes at run time live in `system` under
# `assessment.` (D060). When a person last looked at something that can change
# behind their back (D028) is on their account, asked of the identity part.
CONFIG = "assessment."
INDEXES = {
    "response": [
        (("response_id",), True),
        (("speaker_id",), False),
        (("status",), False),
        (("account_id", "created_at"), False),
        (("reviews.created_at",), False),
        (("replay_labels.account_id",), False),
    ],
}

LIST_FIELDS = (
    "response_id",
    "speaker_id",
    "task_id",
    "status",
    "overall_0_6",
    "overall_band",
    "teacher_verified",
    "created_at",
)


logger = logging.getLogger(__name__)


class InvalidStateError(Exception):
    """A transition the state machine does not allow was attempted."""


def _audit(
    db: Database, actor_id: str, action: str, target_id: str | None, detail: str | None
) -> None:
    """One entry of this service's audit log."""
    write_audit(db, "assessment", actor_id, action, target_id, detail)


def _record_decision(
    db: Database,
    response_id: str,
    reviewer_id: str,
    status: ResponseStatus,
    action: str,
    reason: str,
    scores: tuple[float | None, float | None, str | None, str | None] = (None, None, None, None),
) -> dict:
    """Claim a review decision, record it and audit it; return the response's owner.

    `scores` is (old score, new score, old band, new band). The caller saves the
    report afterwards with the owner returned here, never with placeholders.
    The claim comes first: a teacher who loses the race writes nothing.
    """
    _claim_decision(db, response_id, status)
    owner = db["response"].find_one(
        {"response_id": response_id},
        {"speaker_id": 1, "task_id": 1, "account_id": 1, "review_visits": 1},
    )
    old_score, new_score, old_band, new_band = scores
    visit = next(
        (
            v
            for v in (owner or {}).get("review_visits") or []
            if v["reviewer_id"] == reviewer_id and v.get("decided_at") is None
        ),
        None,
    )
    review = Review(
        review_id=next_id(db, "review"),
        reviewer_id=reviewer_id,
        old_score=old_score,
        new_score=new_score,
        old_band=old_band,
        new_band=new_band,
        reason=reason,
        created_at=_now(),
        opened_at=visit["opened_at"] if visit else None,
    )
    db["response"].update_one(
        {"response_id": response_id}, {"$push": {"reviews": review.model_dump(mode="json")}}
    )
    _audit(db, reviewer_id, action, response_id, reason)
    return fields(owner, ("speaker_id", "task_id", "account_id"))  # type: ignore[return-value]


class Repository(MongoStore):
    """The repository. pymongo's client is shared between threads; no method
    keeps state of its own between calls."""

    def __init__(self, db_path: str | Path = "aicefr.db", blobs=None) -> None:
        self.db_path = str(db_path)
        # D051: where the recordings are (disk or object storage); unset, the
        # settings' upload folder, read when first needed.
        self._blobs = blobs
        db = self.db
        ensure_indexes(db, INDEXES, "assessment")
        ensure_system(db)
        prepare_audit(db)

    @property
    def blobs(self):
        if self._blobs is None:
            from aicefr.config import get_settings
            from aicefr.infra.blobs import blob_store

            self._blobs = blob_store(get_settings())
        return self._blobs

    def _has_audio(self, audio_path: str | None) -> bool:
        if audio_path and Path(audio_path).is_absolute() and Path(audio_path).is_file():
            return True  # a file a response saved before D051 names by its path
        key = key_of(audio_path)
        return key is not None and self.blobs.exists(key)

    def _drop_audio(self, audio_path: str | None) -> None:
        """Delete a recording: the object, and a file a response saved before
        D051 pointed at by its full path."""
        key = key_of(audio_path)
        if key is None:
            return
        self.blobs.delete(key)
        if Path(audio_path).is_absolute():
            Path(audio_path).unlink(missing_ok=True)

    def save(
        self,
        report: Response,
        speaker_id: str,
        task_id: str,
        account_id: str | None = None,
        audio_path: str | None = None,
        must_exist: bool = False,
        purpose: TaskPurpose | None = None,
    ) -> bool:
        """Ghi mot bao cao. Tra False khi tu choi ghi.

        `must_exist=True` la duong cua WORKER ghi ket qua cham: chi cap nhat mot
        bai CON TON TAI va CON DANG CHO (QUEUED/RUNNING). Truoc day duong nay la
        `INSERT OR REPLACE` vo dieu kien, nen sinh vien xoa bai trong luc Whisper
        dang chay thi luc cham xong dong bi xoa duoc TAO LAI kem transcript --
        quyen xoa du lieu bi vo hieu. Bai da cham xong roi cung khong bi worker
        thu hai de len.
        """
        a = report.assessment
        responses = self.col("response")
        existing = responses.find_one({"response_id": report.response_id})

        if must_exist and (
            existing is None
            or existing.get("status")
            not in (ResponseStatus.QUEUED.value, ResponseStatus.RUNNING.value)
        ):
            logger.warning(
                "bo ket qua cham cua %s: bai da bi xoa hoac khong con dang cho",
                report.response_id,
            )
            return False

        # A teacher's decision outranks anything the machine produces later.
        #
        # This used to be an unconditional overwrite, so a late background
        # job -- after a reload, a second worker, or a rescoring run -- could
        # replace a verified result with a fresh estimate and clear
        # teacher_verified, leaving no trace that a human had ever decided.
        if (
            existing is not None
            and existing.get("teacher_verified")
            and not (a and a.teacher_verified)
        ):
            logger.warning(
                "refusing to overwrite a teacher-verified result for %s", report.response_id
            )
            return False

        # Preserve, rather than overwrite, anything the caller did not pass.
        # Dropping speaker_id or account_id here is what orphaned reports once
        # before; created_at is the submission time and must not drift to
        # "time of last write", or the queue reorders itself and the stuck-job
        # sweep measures from the wrong moment.
        def keep(name: str, value):
            """Keep what is already stored when the caller passes nothing."""
            if value is not None:
                return value
            return existing.get(name) if existing is not None else None

        values = {
            "speaker_id": keep("speaker_id", speaker_id or None),
            "task_id": keep("task_id", task_id or None),
            "status": report.status.value,
            "overall_0_6": a.overall_0_6 if a else None,
            "overall_band": a.overall_band.value if a and a.overall_band else None,
            "teacher_verified": int(a.teacher_verified) if a else 0,
            "model_version": a.model_version if a else None,
            "config_version": report.config_version,
            # The reviews are kept beside the report, not inside it (`get`).
            "report_json": json.dumps(
                report.model_dump(mode="json", exclude={"reviews"}), ensure_ascii=False
            ),
            "account_id": keep("account_id", account_id),
            "audio_path": keep("audio_path", audio_path),
            "purpose": keep("purpose", purpose.value if purpose else None)
            or TaskPurpose.ASSESSMENT.value,
        }
        if must_exist:
            # The worker's path updates, and only a response that still waits:
            # checked by the update itself, not by the read above, so an
            # erasure in between leaves nothing to write to -- never an insert
            # that would bring the transcript back.
            done = responses.update_one(
                {
                    "response_id": report.response_id,
                    "status": {"$in": [ResponseStatus.QUEUED.value, ResponseStatus.RUNNING.value]},
                    "teacher_verified": 0,
                },
                {"$set": values},
            )
            return done.modified_count == 1

        # An upsert of the one document: its _id, and with it everything that
        # points at the response (blind-rating assignments, "saw the machine"
        # records), stays as it was.
        try:
            responses.update_one(
                {"response_id": report.response_id},
                {
                    "$set": values,
                    "$setOnInsert": {"created_at": _now(), "started_at": None},
                },
                upsert=True,
            )
        except IntegrityError:
            # Two first saves of one response at once: the other created it.
            responses.update_one({"response_id": report.response_id}, {"$set": values})
        return True

    def set_status(
        self,
        response_id: str,
        status: ResponseStatus,
        reasons: list[ReasonCode] | None = None,
        only_from: tuple[ResponseStatus, ...] | None = None,
    ) -> bool:
        """Change the status of a response being processed; True when it changed.

        Both the status field and the JSON report are updated so the two cannot
        drift apart. List queries read the field while the report page reads the
        JSON; if they diverge, one of the two places would be lying.

        `only_from`: change it only while it is in one of these states, checked
        by the update itself -- a result that lands between the caller's look
        and this write is not overwritten (D043: the overdue sweep, a worker's
        failure report).
        """
        responses = self.col("response")
        row = responses.find_one({"response_id": response_id}, {"report_json": 1, "status": 1})
        if row is None or (only_from and row["status"] not in {s.value for s in only_from}):
            return False
        report = json.loads(row["report_json"])
        report["status"] = status.value
        if reasons is not None:
            report["reasons"] = [r.value for r in reasons]
        done = responses.update_one(
            {"response_id": response_id, "status": row["status"]},
            {
                "$set": {
                    "status": status.value,
                    "report_json": json.dumps(report, ensure_ascii=False),
                }
            },
        )
        return done.modified_count == 1

    def mark_running(self, response_id: str) -> bool:
        """QUEUED becomes RUNNING, stamped with the time; anything else stays as it is.

        The speech service says it started and, later, what it found. Between
        services the two messages can arrive the other way round; a "started"
        arriving after the result must not put a finished response back to
        RUNNING, so only a QUEUED response moves.
        """
        responses = self.col("response")
        row = responses.find_one(
            {"response_id": response_id, "status": ResponseStatus.QUEUED.value}, {"report_json": 1}
        )
        if row is None:
            return False
        report = json.loads(row["report_json"])
        report["status"] = ResponseStatus.RUNNING.value
        responses.update_one(
            {"response_id": response_id, "status": ResponseStatus.QUEUED.value},
            {
                "$set": {
                    "status": ResponseStatus.RUNNING.value,
                    "report_json": json.dumps(report, ensure_ascii=False),
                    "started_at": _now(),
                }
            },
        )
        return True

    def running_since(self, cutoff: str) -> list[str]:
        """Responses RUNNING since before `cutoff`: the speech service never finished them."""
        rows = self.col("response").find(
            {"status": ResponseStatus.RUNNING.value, "started_at": {"$ne": None, "$lte": cutoff}},
            {"response_id": 1},
        )
        return [r["response_id"] for r in rows]

    def queued_since(self, cutoff: str) -> list[str]:
        """Responses still QUEUED, submitted before `cutoff`: no worker ever took them."""
        rows = self.col("response").find(
            {"status": ResponseStatus.QUEUED.value, "created_at": {"$lte": cutoff}},
            {"response_id": 1},
        )
        return [r["response_id"] for r in rows]

    def fail_stuck(self, minutes: int = 10) -> list[str]:
        """Mark responses stuck in QUEUED or RUNNING for too long as FAILED.

        Runs at startup. If the process dies mid-run, whatever was being
        processed stays in RUNNING forever; left alone, the submitter waits
        indefinitely and NFR-11, on the share of jobs reaching a definite final
        state, is never met.
        """
        cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
        rows = self.col("response").find(
            {
                "status": {"$in": [ResponseStatus.QUEUED.value, ResponseStatus.RUNNING.value]},
                "created_at": {"$lte": cutoff},
            },
            {"response_id": 1},
        )
        ids = [r["response_id"] for r in rows]
        for rid in ids:
            self.set_status(rid, ResponseStatus.FAILED, [ReasonCode.PROCESSING_INTERRUPTED])
        return ids

    def status_of(self, response_id: str) -> dict | None:
        """Lightweight status information for periodic polling. Serves FR-05."""
        row = self.col("response").find_one({"response_id": response_id})
        return fields(
            row,
            (
                "response_id",
                "task_id",
                "status",
                "overall_0_6",
                "overall_band",
                "teacher_verified",
                "created_at",
                "purpose",
            ),
        )

    # ---------- review locking (FR-29) ----------

    def lock_response(
        self, response_id: str, reviewer_id: str, reviewer_name: str, minutes: int = 15
    ) -> tuple[bool, str | None]:
        """Claim the right to review a response for `minutes` minutes.

        Returns (claimed, name of the current holder). Without this step, two
        teachers opening the same response would overwrite each other's decision
        and neither would know.

        An expired lock can be claimed again automatically, so a teacher who
        closes the browser mid-review does not leave the response locked forever.
        """
        until = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat(timespec="seconds")
        claim = {"reviewer_id": reviewer_id, "reviewer_name": reviewer_name, "locked_until": until}
        # One conditional write on the response, so the check and the claim
        # cannot be interleaved. Reading the lock and then writing it left a
        # window in which two teachers both read "nobody holds this" and both
        # wrote their own claim. Here the update takes the response only when
        # nobody holds it, the lock has run out, or it is one's own.
        self.col("response").update_one(
            {
                "response_id": response_id,
                "$or": [
                    {"review_lock": None},
                    {"review_lock.locked_until": {"$lte": _now()}},
                    {"review_lock.reviewer_id": reviewer_id},
                ],
            },
            {"$set": {"review_lock": claim}},
        )
        lock = self._lock(response_id)
        if lock is not None and not lock.is_held_by(reviewer_id):
            return False, lock.reviewer_name
        return True, None

    def _lock(self, response_id: str) -> ReviewLock | None:
        row = self.col("response").find_one({"response_id": response_id}, {"review_lock": 1})
        held = (row or {}).get("review_lock")
        return ReviewLock(response_id=response_id, **held) if held else None

    def unlock_response(self, response_id: str, reviewer_id: str) -> None:
        """Release the lock. Only the current holder can release it."""
        self.col("response").update_one(
            {"response_id": response_id, "review_lock.reviewer_id": reviewer_id},
            {"$set": {"review_lock": None}},
        )

    def locked_by(self, response_id: str) -> str | None:
        """Name of whoever holds a still-valid lock, or None."""
        lock = self._lock(response_id)
        if lock is None or lock.locked_until <= _now():
            return None
        return lock.reviewer_name

    def review_history(self, response_id: str) -> list[Review]:
        """History of result edits for one response. FR-31."""
        row = self.col("response").find_one({"response_id": response_id}, {"reviews": 1})
        return [Review(**r) for r in (row or {}).get("reviews") or []]

    # ---------- personal data: export and erasure (FR-34, FR-35, FR-38) ----------

    def speaking_profile(self, account_id: str) -> list[dict]:
        """Verified results for one learner, for the exported profile.

        Only responses a teacher has confirmed. An unverified machine score is
        an estimate; putting it in an exportable profile would let it travel as
        though it were a finding, which is exactly what FR-21 forbids.
        """
        rows = (
            self.col("response")
            .find({"account_id": account_id, "teacher_verified": 1})
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        names = (
            "response_id",
            "task_id",
            "overall_0_6",
            "overall_band",
            "created_at",
            "report_json",
        )
        return [_profile_row(fields(r, names)) for r in rows]  # type: ignore[arg-type]

    def open_review_session(self, response_id: str, reviewer_id: str) -> None:
        """Note that a teacher opened a response for review; once per open visit."""
        self.col("response").update_one(
            {
                "response_id": response_id,
                "review_visits": {
                    "$not": {"$elemMatch": {"reviewer_id": reviewer_id, "decided_at": None}}
                },
            },
            {
                "$push": {
                    "review_visits": {
                        "reviewer_id": reviewer_id,
                        "opened_at": _now(),
                        "decided_at": None,
                        "action": None,
                    }
                }
            },
        )

    def close_review_session(self, response_id: str, reviewer_id: str, action: str) -> None:
        now = _now()
        # One open visit per reviewer at a time; the loop closes a stray second.
        for _ in range(4):
            done = self.col("response").update_one(
                {
                    "response_id": response_id,
                    "review_visits": {
                        "$elemMatch": {"reviewer_id": reviewer_id, "decided_at": None}
                    },
                },
                {
                    "$set": {
                        "review_visits.$.decided_at": now,
                        "review_visits.$.action": action,
                    }
                },
            )
            if not done.modified_count:
                return

    def review_sessions(self, limit: int = 5000) -> list[dict]:
        rows = self.col("response").find(
            {"review_visits.decided_at": {"$ne": None}}, {"review_visits": 1}
        )
        visits = [
            {"opened_at": v["opened_at"], "decided_at": v["decided_at"], "action": v["action"]}
            for r in rows
            for v in r.get("review_visits") or []
            if v.get("decided_at") is not None
        ]
        visits.sort(key=lambda v: v["decided_at"], reverse=True)
        return visits[:limit]

    def settled_counts(self) -> tuple[int, int]:
        """(scored assessments the machine settled alone, scored assessments that reached a result).

        Alone: COMPLETED with no teacher confirmation. Reached a result:
        COMPLETED or REVIEW_REQUIRED, with a machine score.
        """
        rows = self.col("response").find(
            {
                "purpose": "assessment",
                "overall_0_6": {"$ne": None},
                "status": {"$in": ["COMPLETED", "REVIEW_REQUIRED"]},
            },
            {"status": 1, "teacher_verified": 1},
        )
        alone = total = 0
        for r in rows:
            total += 1
            alone += int(r["status"] == "COMPLETED" and not r.get("teacher_verified"))
        return alone, total

    def scored_assessments(
        self,
        accounts: Collection[str] | None = None,
        machine_only: bool = False,
        limit: int = 20000,
    ) -> list[dict]:
        """Scored assessments, oldest first; the latest `limit` when there are more.

        The test-retest pairs of D042 and the outcomes of the feedback study
        (D040) come from here. `accounts` narrows to those learners;
        `machine_only` keeps the machine's own scores, leaving out the responses
        a teacher's decision overwrote -- a test-retest pair compares the
        instrument with itself.
        """
        query: dict = {
            "overall_0_6": {"$ne": None},
            "purpose": "assessment",
            "account_id": {"$ne": None},
        }
        if accounts is not None:
            ids = list(accounts)
            if not ids:
                return []
            query["account_id"] = {"$in": ids}
        if machine_only:
            query["teacher_verified"] = 0
        rows = (
            self.col("response")
            .find(query)
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        names = ("account_id", "task_id", "overall_0_6", "model_version", "created_at")
        return [fields(r, names) for r in reversed(list(rows))]  # type: ignore[misc]

    def progress_series(self, account_id: str, limit: int = 100) -> list[dict]:
        """One learner's results over time, machine estimate and verified alike.

        Deliberately wider than `speaking_profile`, which exports only what a
        teacher confirmed. A profile is a claim about someone and must not carry
        an unverified number out of the system; a progress view is the learner
        looking at their own practice, where hiding every unconfirmed attempt
        would leave most students with an empty chart and no reason to come
        back. The distinction is carried per row in `teacher_verified`, so the
        screen can draw the two differently instead of blurring them together.
        """
        rows = (
            self.col("response")
            .find({"account_id": account_id, "overall_0_6": {"$ne": None}})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        names = (
            "response_id",
            "task_id",
            "status",
            "overall_0_6",
            "overall_band",
            "teacher_verified",
            "model_version",
            "created_at",
        )
        # The latest `limit`, in time order: "the last three results" must be.
        return [fields(r, names) for r in reversed(list(rows))]  # type: ignore[misc]

    def cohort_stats(self, limit: int = 5000) -> dict:
        """What a teacher needs to see about a class rather than one student. FR-29.

        Two of these numbers are about the students and the rest are about the
        machine, which is the point. `agreement` counts how often a teacher left
        the band as the model set it, and `changed` how often they did not: a
        class where teachers overturn a third of the bands is telling you
        something about the model, and no per-response screen would ever show
        it. Nothing here is a grade for anybody -- there is no ranking of
        students and no teacher leaderboard, because a screen that ranks people
        gets used to rank people.
        """
        # The numbers about the SCORING MACHINE count assessment responses only
        # (D023): practice is never scored, and counting it would make "responses"
        # and "scored responses" drift apart for no reason anyone could explain.
        responses = self.col("response")
        assessed = list(
            responses.find(
                {"purpose": "assessment"},
                {"overall_band": 1, "task_id": 1, "overall_0_6": 1, "status": 1, "account_id": 1},
            )
        )
        by_band: dict[str, int] = {}
        tasks: dict[str, dict] = {}
        for r in assessed:
            if r.get("overall_band") is not None:
                by_band[r["overall_band"]] = by_band.get(r["overall_band"], 0) + 1
            cell = tasks.setdefault(r["task_id"], {"n": 0, "scores": [], "waiting": 0})
            cell["n"] += 1
            if r.get("overall_0_6") is not None:
                cell["scores"].append(r["overall_0_6"])
            cell["waiting"] += int(r["status"] == "REVIEW_REQUIRED")
        speakers = len({r["account_id"] for r in assessed if r.get("account_id") is not None})
        waiting = sum(1 for r in assessed if r["status"] == "REVIEW_REQUIRED")
        verified = responses.count_documents({"teacher_verified": 1})

        # Only decisions where the machine had proposed a band at all.
        # A review of a response the model refused to score is a teacher doing
        # the work from scratch, not a teacher agreeing or disagreeing with
        # anything, and counting it as agreement would flatter the model with
        # cases it never answered.
        decisions = sorted(
            (
                r
                for row in self.col("response").find(
                    {"reviews.old_band": {"$ne": None}}, {"reviews": 1}
                )
                for r in row.get("reviews") or []
                if r.get("old_band") is not None
            ),
            key=lambda r: r.get("review_id") or 0,
        )[:limit]

        kept = sum(1 for r in decisions if r.get("new_band") == r["old_band"])
        changed = len(decisions) - kept
        return {
            # Two different counts, and the screen shows both. `responses` alone
            # read as a contradiction next to the review backlog: 7 scored
            # responses beside 13 waiting for review looks like an error until
            # you know that a response the model refused to score is also
            # waiting -- and is in fact the kind most in need of a teacher.
            "responses": len(assessed),
            "scored": sum(by_band.values()),
            "speakers": speakers,
            "waiting_for_review": waiting,
            "teacher_verified": verified,
            "by_band": by_band,
            "by_task": [
                {
                    "task_id": task_id,
                    "n": cell["n"],
                    "avg_score": round(sum(cell["scores"]) / len(cell["scores"]), 2)
                    if cell["scores"]
                    else None,
                    "waiting": cell["waiting"],
                }
                for task_id, cell in sorted(tasks.items(), key=lambda kv: str(kv[0]))
            ],
            "agreement": {
                "decisions": len(decisions),
                "band_kept": kept,
                "band_changed": changed,
                # None, not 0.0, when nobody has reviewed anything yet: a rate
                # of zero would read as "teachers never agree with the model".
                "rate": round(kept / len(decisions), 3) if decisions else None,
            },
            "practice": self.practice_summary(),
        }

    def practice_summary(self) -> dict:
        """How far the class has got with practice, per criterion. D023, outline 1.7.

        Totals only, no row per learner: this screen tells a teacher which criterion
        the class is stumbling on so they can pick work for the whole class, not who
        practises more than whom.
        """
        from aicefr.practice.bank import PRACTICE_TASKS

        criterion_of = {t.task_id: t.criterion.value for t in PRACTICE_TASKS}
        rows = list(
            self.col("response").find(
                {"purpose": "practice", "status": ResponseStatus.COMPLETED.value},
                {"account_id": 1, "task_id": 1, "report_json": 1},
            )
        )
        by_criterion: dict[str, dict[str, int]] = {}
        done = 0
        for r in rows:
            cell = by_criterion.setdefault(
                criterion_of.get(r["task_id"], "khac"), {"attempts": 0, "completed": 0}
            )
            cell["attempts"] += 1
            if _practice_completed(r.get("report_json")):
                cell["completed"] += 1
                done += 1
        return {
            "attempts": len(rows),
            "learners": len({r["account_id"] for r in rows if r.get("account_id")}),
            "completed": done,
            "by_criterion": by_criterion,
        }

    # ---------- practice (D023) ----------

    def practice_attempts(self, account_id: str, task_id: str | None = None) -> list[dict]:
        """One learner's practice attempts, oldest first, with the outcome of each.

        Rejected attempts (REJECTED, FAILED) are included: the task page has to say
        "your last attempt was rejected for too much silence" rather than act as if it
        never happened. The streak and the learning path count processed attempts only.
        """
        query = {"account_id": account_id, "purpose": "practice"}
        if task_id is not None:
            query["task_id"] = task_id
        # _id keeps submission order when two attempts share a second
        # (created_at only has second precision).
        rows = (
            self.col("response").find(query).sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        out = []
        for r in rows:
            result = (json.loads(r.get("report_json") or "{}").get("practice")) or {}
            out.append(
                {
                    "response_id": r["response_id"],
                    "task_id": r["task_id"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "completed": result.get("completed"),
                    "met_count": result.get("met_count"),
                    "total": len(result.get("checks") or []) or None,
                }
            )
        return out

    def assessments_by_account(self, since: str, until: str) -> dict[str, int]:
        """Assessments submitted in [since, until), per account (D033: the monthly figure).

        Per account rather than one total, so the caller can leave out research
        participants, who do not count towards a plan (BR-30).
        """
        rows = self.col("response").find(
            {
                "purpose": "assessment",
                "account_id": {"$ne": None},
                "created_at": {"$gte": since, "$lt": until},
            },
            {"account_id": 1},
        )
        out: dict[str, int] = {}
        for r in rows:
            out[r["account_id"]] = out.get(r["account_id"], 0) + 1
        return out

    def latest_assessment(self, account_id: str) -> dict | None:
        """The latest scored assessment: the basis for suggesting practice.

        The band is the one stored on the response, i.e. the teacher's band if
        the response was reviewed. `weakest_criteria` is empty for responses
        scored before D022 or without per-criterion indicators -- the suggestion
        then does not rely on a weakest criterion rather than guess one.
        """
        row = self.col("response").find_one(
            {"account_id": account_id, "purpose": "assessment", "overall_band": {"$ne": None}},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        if row is None:
            return None
        assessment = json.loads(row.get("report_json") or "{}").get("assessment") or {}
        return {
            "response_id": row["response_id"],
            "band": row["overall_band"],
            "teacher_verified": bool(row.get("teacher_verified")),
            "created_at": row["created_at"],
            "weakest_criteria": list(assessment.get("weakest_criteria") or []),
        }

    def erasure_preview(self, speaker_id: str) -> dict:
        """What an erasure would remove, without removing anything.

        FR-35 requires showing the artifacts first and asking for the id a
        second time. Deleting a participant's recordings is irreversible, so
        the interface must make the operator look at the list before acting.
        """
        rows = list(
            self.col("response").find(
                {"speaker_id": speaker_id}, {"response_id": 1, "audio_path": 1, "reviews": 1}
            )
        )
        ids = [r["response_id"] for r in rows]
        reviews = sum(len(r.get("reviews") or []) for r in rows)
        audio_files = sum(1 for r in rows if self._has_audio(r.get("audio_path")))
        return {
            "speaker_id": speaker_id,
            "responses": len(rows),
            "audio_files": audio_files,
            "review_actions": reviews,
            "response_ids": ids,
        }

    def _forget_responses(self, ids: list[str]) -> None:
        """Everything that hangs off these responses, then the responses.

        What a foreign key's ON DELETE CASCADE did in SQL: the blind-rating
        sheets and their ratings go with the response they are about; the
        review history, the lock and who saw the machine's result are part of
        the response's own document (D060).
        """
        if not ids:
            return
        db = self.db
        within = {"response_id": {"$in": ids}}
        # The blind-rating sheets about them, from whichever batch holds them.
        db["rating_batch"].update_many(
            {"ratings.response_id": {"$in": ids}},
            {"$pull": {"ratings": {"response_id": {"$in": ids}}}},
        )
        # The reviews, the lock, the visits and the replay labels are part of
        # the response document and go with it.
        db["response"].delete_many(within)

    def erase_speaker(self, speaker_id: str, actor_id: str) -> dict:
        """Delete one participant's recordings and reports. Irreversible.

        Removes the audio from disk as well as the documents. Leaving the files
        behind would make the deletion a lie: a recording of someone's voice is
        personal data whether or not a document still points at it.

        Writes an audit entry that records the erasure itself. The entry keeps
        the pseudonym and the counts, not the content.
        """
        preview = self.erasure_preview(speaker_id)
        rows = list(
            self.col("response").find(
                {"speaker_id": speaker_id}, {"response_id": 1, "audio_path": 1}
            )
        )
        for r in rows:
            self._drop_audio(r.get("audio_path"))
        self._forget_responses([r["response_id"] for r in rows])
        _audit(
            self.db,
            actor_id,
            "ERASE_PARTICIPANT",
            speaker_id,
            f"{preview['responses']} responses, {preview['audio_files']} audio files",
        )
        return preview

    def erase_one_response(self, response_id: str, actor_id: str) -> bool:
        """Delete a single response: its document, its review history, its audio file.

        Separate from `erase_speaker` because the two answer different requests.
        `erase_speaker` is an administrator acting on a request to erase and
        removes everything a person ever submitted. This is a person deleting one
        recording of their own -- "I mumbled through that one, take it off" --
        and it must not require asking anybody. A right that needs someone else
        to act on your behalf is a queue, not a right.

        A response a teacher has already verified is refused, and the caller is
        told why. The verified result is a record of a decision somebody made,
        and the audit trail behind it has to keep pointing at something real.

        Returns False when there is nothing to delete, so the caller can answer
        404 rather than claim success for a response that never existed.
        """
        row = self.col("response").find_one(
            {"response_id": response_id}, {"audio_path": 1, "teacher_verified": 1}
        )
        if row is None:
            return False
        if row.get("teacher_verified"):
            raise InvalidStateError(
                "bài đã được giảng viên xác nhận nên không tự xoá được;"
                " hãy liên hệ giảng viên phụ trách"
            )

        # The recording, not only the document. A recording of someone's voice
        # is personal data whether or not a document still points at it.
        self._drop_audio(row.get("audio_path"))
        self._forget_responses([response_id])
        # The entry records that a deletion happened and who asked for it. It
        # carries no transcript and no score: an audit log that keeps a copy of
        # what was deleted has not deleted it.
        _audit(
            self.db, actor_id, "ERASE_OWN_RESPONSE", response_id, "người học tự xoá bài của mình"
        )
        return True

    def audio_path_of(self, response_id: str) -> str | None:
        """Filesystem path of a response's audio file.

        Internal use only. Never return this path through the API: leaking the
        server's directory layout is one step towards leaking more.
        """
        row = self.col("response").find_one({"response_id": response_id}, {"audio_path": 1})
        return row.get("audio_path") if row else None

    # ---------- the upgraded answer (D069) ----------
    def upgrade_of(self, response_id: str) -> dict | None:
        """The learner's answer rewritten one band higher, if one was made."""
        row = self.col("response").find_one({"response_id": response_id}, {"coach_upgrade": 1})
        return (row or {}).get("coach_upgrade")

    def save_upgrade(self, response_id: str, upgrade: dict) -> None:
        """Kept with the response, so it is erased with it and paid for once."""
        self.col("response").update_one(
            {"response_id": response_id}, {"$set": {"coach_upgrade": upgrade}}
        )

    def upgrades_since(self, account_id: str, since: str) -> int:
        """How many upgrades this account asked for since `since` (ISO time)."""
        return self.col("response").count_documents(
            {"account_id": account_id, "coach_upgrade.created_at": {"$gte": since}}
        )

    def owner_of(self, response_id: str) -> str | None:
        """Return the submitter's account_id, or None if the response has no owner."""
        row = self.col("response").find_one({"response_id": response_id}, {"account_id": 1})
        return row.get("account_id") if row else None

    def list_by_account(self, account_id: str, limit: int = 200) -> list[dict]:
        """List one person's responses. Serves FR-04.

        `reviewed_at` is the time of the latest teacher decision, so the list
        can mark a result a teacher confirmed since the owner last looked (D028).
        """
        rows = list(
            self.col("response")
            .find({"account_id": account_id})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        latest = {
            r["response_id"]: max(x["created_at"] for x in r["reviews"])
            for r in rows
            if r.get("reviews")
        }
        out = []
        for r in rows:
            item = fields(r, (*LIST_FIELDS, "purpose"))
            item["reviewed_at"] = latest.get(r["response_id"])  # type: ignore[index]
            out.append(item)
        return out  # type: ignore[return-value]

    # ---------- what is new for a person (D028) ----------

    def count_reviewed_since(self, account_id: str, since: str | None) -> int:
        """The owner's assessed responses a teacher decided on after `since`.

        Never-looked (`since` None) counts every decided response: a student who
        has not opened their list yet has not seen any of those decisions.
        """
        rows = self.col("response").find(
            {"account_id": account_id, "purpose": "assessment", "reviews.0": {"$exists": True}},
            {"reviews": 1},
        )
        return sum(
            1 for r in rows if since is None or any(x["created_at"] > since for x in r["reviews"])
        )

    def count_waiting_review(self, exclude: Collection[str] = ()) -> int:
        """How many assessed responses wait in the teacher queue, less the ones in `exclude`."""
        rows = self.col("response").find(
            {"status": ResponseStatus.REVIEW_REQUIRED.value, "purpose": "assessment"},
            {"response_id": 1},
        )
        hidden = set(exclude)
        return sum(r["response_id"] not in hidden for r in rows)

    def get(self, response_id: str) -> Response | None:
        row = self.col("response").find_one(
            {"response_id": response_id}, {"report_json": 1, "reviews": 1}
        )
        if row is None:
            return None
        report = Response.model_validate_json(row["report_json"])
        return report.model_copy(
            update={"reviews": [Review(**r) for r in row.get("reviews") or []]}
        )

    def queue_with_locks(self, status: ResponseStatus, limit: int = 50) -> list[dict]:
        """The review queue plus, for each response, who currently holds it.

        Two reads rather than one read per queued response: the caller used to
        loop over the responses calling `locked_by` on each, which costs one
        round trip per response -- fine with three in a test, linear in the size
        of the queue in a real term.
        """
        rows = list(
            self.col("response")
            .find({"status": status.value, "purpose": "assessment"})
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
            .limit(limit)
        )
        now = _now()
        out = []
        for r in rows:
            item = fields(r, LIST_FIELDS)
            lock = r.get("review_lock")
            held = lock is not None and lock["locked_until"] > now
            item["locked_by"] = lock["reviewer_name"] if held else None  # type: ignore[index]
            out.append(item)
        return out  # type: ignore[return-value]

    def assessments_since(self, account_ids: list[str], task_id: str, since: str) -> list[dict]:
        """Assessment responses of `task_id` by these accounts from `since` on, oldest first.

        What a class assignment counts as handed in (D054).
        """
        rows = (
            self.col("response")
            .find(
                {
                    "account_id": {"$in": account_ids},
                    "task_id": task_id,
                    "purpose": {"$ne": "practice"},
                    "created_at": {"$gte": since},
                }
            )
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [fields(r, (*LIST_FIELDS, "account_id")) for r in rows]  # type: ignore[misc]

    def list_all(self, limit: int = 200) -> list[dict]:
        rows = (
            self.col("response")
            .find()
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [fields(r, LIST_FIELDS) for r in rows]  # type: ignore[misc]

    def apply_review(
        self,
        response_id: str,
        reviewer_id: str,
        new_score: float | None,
        new_band: str | None,
        reason: str,
    ) -> Response | None:
        """A teacher approves or edits a score. This is the only place where
        teacher_verified may be turned on."""
        report = self.get(response_id)
        if report is None:
            return None

        # Only a response that is actually waiting for a decision may receive one.
        #
        # Without this, a recording the quality check had REJECTED -- too long,
        # too noisy, clipped -- could be "approved" into teacher_verified=1 and
        # travel into the exported profile, which is exactly what FR-21 forbids.
        # A response still QUEUED or RUNNING could be decided before it had been
        # scored at all, and an already decided one could be quietly changed again.
        if report.status is not ResponseStatus.REVIEW_REQUIRED:
            raise InvalidStateError(
                f"bài đang ở trạng thái {report.status.value}, chỉ duyệt được bài "
                "đang chờ giảng viên"
            )

        if report.assessment is None:
            # May khong cham duoc (khong phai tieng Anh, ban chep rong, thieu
            # model). Truoc day bai nay KHONG duyet duoc va nam mai trong hang
            # doi. Gio giang vien tu cham -- ket qua ghi ro la cua giang vien --
            # hoac dong bai bang `close_unscorable`.
            if new_score is None and new_band is None:
                raise InvalidStateError(
                    "máy không chấm được bài này: hãy nhập điểm hoặc band của giảng viên, "
                    "hoặc đóng bài"
                )
            from aicefr.contracts import Assessment

            report.assessment = Assessment(
                overall_0_6=None,
                overall_band=None,
                model_version="teacher",
                reasons=list(report.reasons),
            )
        a = report.assessment
        old_score, old_band = a.overall_0_6, a.overall_band
        thresholds = _band_thresholds(a.model_version)

        # Diem va band khong duoc mau thuan (5,5 kem A2 tung duoc luu la "da xac
        # nhan"). Gui ca hai thi chung phai khop nguong cua chinh mo hinh da cham.
        if new_score is not None and new_band is not None:
            from aicefr.scoring.band_map import to_band

            if to_band(new_score, thresholds).value != new_band:
                raise InvalidStateError(
                    f"điểm {new_score} ứng với band {to_band(new_score, thresholds).value}, "
                    f"không phải {new_band}"
                )

        if new_score is not None:
            a.overall_0_6 = new_score
        if new_band is not None:
            from aicefr.contracts import Band

            a.overall_band = Band(new_band)
        # A score and its band must never disagree.
        #
        # The two were updated independently, so a teacher who corrected the
        # score and left the band alone produced rows like 5.5 paired with A2 --
        # verified, exported, and meaningless. When only the score moves, the
        # band follows it.
        if new_score is not None and new_band is None:
            from aicefr.scoring.band_map import to_band

            a.overall_band = to_band(new_score, thresholds)

        # Khong con vong lap chep diem moi xuong tung tieu chi: tu khi
        # CriterionScore thanh CriterionCoverage, cac dong do chi mang do phu
        # phep do, va viec giang vien sua diem khong lam doi so phep do da tinh
        # duoc tren ban ghi.

        a.teacher_verified = True
        report.status = ResponseStatus.COMPLETED

        owner = _record_decision(
            self.db,
            response_id,
            reviewer_id,
            ResponseStatus.COMPLETED,
            "REVIEW_DECISION",
            reason,
            (
                old_score,
                new_score,
                old_band.value if old_band else None,
                # Band SAU quyet dinh, ke ca khi no duoc suy tu diem. Ghi tham
                # so dau vao (None khi chi sua diem) lam thong ke dong thuan
                # dem nham "sua band" thanh "giu band".
                a.overall_band.value if a.overall_band else None,
            ),
        )
        # Write the report back WITHOUT losing who it belongs to.
        #
        # This line used to read `self.save(report, report.response_id, "")`,
        # which passed the response id in the speaker_id slot, an empty task id,
        # and no account id. Approving a review therefore erased the owner: the
        # student lost access to their own report, it vanished from "my
        # responses", and it never reached the exported profile. Nothing failed
        # loudly — the document was still there, just orphaned.
        self.save(report, owner["speaker_id"], owner["task_id"], account_id=owner["account_id"])
        return report

    def close_unscorable(self, response_id: str, reviewer_id: str, reason: str) -> Response | None:
        """Giang vien dong mot bai may khong cham duoc ma khong cho diem.

        Chi cho bai dang cho duyet VA khong co ket qua cham. Bai chuyen sang
        REJECTED: sinh vien thay "ban ghi chua dung duoc" va duoc moi nop lai.
        Co ban ghi review_action (khong co band, nen khong tinh vao ty le dong
        thuan) va ban ghi audit, nhu moi quyet dinh khac.
        """
        report = self.get(response_id)
        if report is None:
            return None
        if report.status is not ResponseStatus.REVIEW_REQUIRED or report.assessment is not None:
            raise InvalidStateError("chỉ đóng được bài đang chờ duyệt mà máy không chấm được")
        report.status = ResponseStatus.REJECTED
        owner = _record_decision(
            self.db, response_id, reviewer_id, ResponseStatus.REJECTED, "REVIEW_CLOSED", reason
        )
        self.save(report, owner["speaker_id"], owner["task_id"], account_id=owner["account_id"])
        return report

    def research_rows(self, allowed_account_ids: set[str], limit: int = 5000) -> list[dict]:
        """Rows for the research export, restricted to accounts that allow it.

        The caller passes the allowed set rather than this method reading the
        accounts itself. Two reasons: the scoring store and the accounts are
        separate concerns, and a caller holding an explicit
        set is auditable -- you can print it, count it, and show it to an ethics
        reviewer. A join hidden inside the query cannot be shown to anybody.

        Never returns the transcript. The export exists to analyse scores
        against human ratings; shipping the words of a recording around is a
        risk with no matching benefit.
        """
        if not allowed_account_ids:
            return []
        # Filtered in the query, then limited: limiting first and filtering
        # after would silently drop the newer responses of allowed learners
        # once there were more than `limit` in all.
        rows = self.col("response").find(
            {
                "account_id": {"$in": sorted(allowed_account_ids)},
                # D023: practice attempts are constrained exercises (given
                # words, reading aloud), not free speech to compare with
                # teacher ratings.
                "purpose": "assessment",
            }
        )
        names = (
            "response_id",
            "speaker_id",
            "task_id",
            "status",
            "overall_0_6",
            "overall_band",
            "teacher_verified",
            "model_version",
            "config_version",
            "created_at",
            "account_id",
        )
        out = [fields(r, names) for r in rows]
        out.sort(key=lambda r: r["created_at"])  # type: ignore[index]
        return out[:limit]  # type: ignore[return-value]

    # ---------- runtime configuration (FR-08, FR-36) ----------
    #
    # Settings that an administrator may change while the system is running live
    # here rather than in environment variables, for one reason: a change has to
    # be attributable. The document carries who changed it, when, and under which
    # version label -- an env var carries none of that, and "who raised the
    # silence threshold the week the results went strange" is a question that
    # will be asked.

    def set_config(self, key: str, value: str, version: str, actor_id: str) -> None:
        self.col(SYSTEM).update_one(
            {"key": CONFIG + key},
            {
                "$set": {
                    "value": value,
                    "version": version,
                    "updated_by": actor_id,
                    "updated_at": _now(),
                }
            },
            upsert=True,
        )

    def get_config(self, key: str) -> AppConfig | None:
        row = self.col(SYSTEM).find_one({"key": CONFIG + key})
        names = ("value", "version", "updated_by", "updated_at")
        return AppConfig(key=key, **fields(row, names)) if row else None

    def write_audit(
        self, actor_id: str, action: str, target_id: str | None, detail: str | None
    ) -> None:
        """Record one accountable action.

        Kept deliberately small: an actor, what they did, to what, and when.
        No transcript, no pseudonym of a third party, no free text unless the
        caller passes it -- the log itself must not become a second copy of the
        personal data it is meant to protect.
        """
        _audit(self.db, actor_id, action, target_id, detail)

    def audit(self, limit: int = 100) -> list[dict]:
        """This service's latest audit entries, newest first, as `AuditLog.recent` gives them."""
        return recent_entries(self.db, "assessment", limit)

    def stats(self) -> dict:
        rows = list(self.col("response").find({}, {"status": 1, "overall_band": 1}))
        by_status: dict[str, int] = {}
        by_band: dict[str, int] = {}
        for r in rows:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
            if r.get("overall_band") is not None:
                by_band[r["overall_band"]] = by_band.get(r["overall_band"], 0) + 1
        return {
            "total": len(rows),
            "by_status": by_status,
            "by_band": by_band,
            "teacher_verified": self.col("response").count_documents({"teacher_verified": 1}),
        }


def _practice_completed(report_json: str | None) -> bool:
    return bool((json.loads(report_json or "{}").get("practice") or {}).get("completed"))


def _profile_row(row: dict) -> dict:
    """One profile row: a verified result plus the criterion to practise first (D022).

    `weakest_criteria` is a position RELATIVE TO THE REFERENCE RESPONSES, not a
    criterion score; the hint comes from the fixed rule table `NEXT_TASK_HINTS`.
    Responses saved before D022 carry no indicators, so both fields stay empty
    rather than guessed.

    D023 ADDS `next_task_id`: the practice task for the weakest criterion at the
    verified band, so another system reading the profile (topics 3, 5 and 8 of
    ALDM-L) can open the right practice task. `next_task_hint` keeps its meaning.
    """
    from aicefr.contracts import Band, Criterion
    from aicefr.practice.bank import practice_task_id
    from aicefr.report.comments import NEXT_TASK_HINTS

    report = json.loads(row.pop("report_json") or "{}")
    weak = [Criterion(c) for c in ((report.get("assessment") or {}).get("weakest_criteria") or [])]
    row["weakest_criteria"] = [c.value for c in weak]
    row["next_task_hint"] = NEXT_TASK_HINTS[weak[0]] if weak else None
    band = row.get("overall_band")
    row["next_task_id"] = practice_task_id(weak[0], Band(band)) if weak and band else None
    return row


def _claim_decision(db: Database, response_id: str, new_status: ResponseStatus) -> None:
    """Chuyen REVIEW_REQUIRED -> new_status NGUYEN TU, truoc moi ghi khac cua quyet dinh.

    Kiem trang thai bang mot lan doc truoc do khong du: hai giang vien cung doc
    REVIEW_REQUIRED thi ca hai quyet dinh deu duoc chap nhan va cai sau de cai
    truoc. Cap nhat co dieu kien chi thanh cong cho mot nguoi; nguoi con lai nhan
    loi truoc khi kip ghi review_action nao.
    """
    claimed = (
        db["response"]
        .update_one(
            {"response_id": response_id, "status": ResponseStatus.REVIEW_REQUIRED.value},
            {"$set": {"status": new_status.value}},
        )
        .modified_count
    )
    if claimed == 0:
        raise InvalidStateError("bài vừa được giảng viên khác quyết định")


def _band_thresholds(model_version: str | None) -> dict[str, float]:
    """Nguong band cua CHINH mo hinh da cham bai (muc 13 review).

    Dung mo hinh mac dinh cho moi bai sai khi admin da kich hoat mo hinh khac.
    Bai do giang vien tu cham ("teacher") hoac mo hinh khong con tren dia thi
    dung mo hinh mac dinh.
    """
    from aicefr.scoring.band_map import thresholds_of
    from aicefr.scoring.scorer import ModelNotFoundError, load_model

    if model_version:
        try:
            return thresholds_of(load_model(model_version)["band_thresholds"])
        except (ModelNotFoundError, KeyError):
            pass
    return thresholds_of(load_model()["band_thresholds"])
