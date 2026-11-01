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
    CoachUpgrade,
    ReasonCode,
    Response,
    ResponseStatus,
    Review,
    ReviewLock,
    ReviewSession,
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
# Every response is an assessment since D083: the practice attempts of D023
# and their `purpose` are gone (migration 14).
# A response's document holds its parts (D060): `reviews` (each teacher
# decision) and `replay_labels` (guided listening, D056). Reviewing it is a
# `review_session` of its own (D082), at most one per response: `lock` (who may
# decide right now) and `visits` (when a teacher opened it and when they left,
# D041 -- the lock is cleared on decision, so its start is kept there).
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
    "review_session": [(("response_id",), True)],
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
        {"response_id": response_id}, {"speaker_id": 1, "task_id": 1, "account_id": 1}
    )
    session = _review_session(db, response_id)
    old_score, new_score, old_band, new_band = scores
    visit = next(
        (
            v
            for v in (session.visits if session else [])
            if v.reviewer_id == reviewer_id and v.decided_at is None
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
        opened_at=visit.opened_at if visit else None,
    )
    db["response"].update_one(
        {"response_id": response_id}, {"$push": {"reviews": review.model_dump(mode="json")}}
    )
    _audit(db, reviewer_id, action, response_id, reason)
    return fields(owner, ("speaker_id", "task_id", "account_id"))  # type: ignore[return-value]


def _review_session(db: Database, response_id: str) -> ReviewSession | None:
    row = db["review_session"].find_one({"response_id": response_id}, {"_id": 0})
    if row is None:
        return None
    if row.get("lock"):
        row["lock"] = {"response_id": response_id, **row["lock"]}
    return ReviewSession.model_validate(row)


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
                report.model_dump(mode="json", exclude={"reviews", "upgrade"}), ensure_ascii=False
            ),
            "account_id": keep("account_id", account_id),
            "audio_path": keep("audio_path", audio_path),
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
        # One conditional write, so the check and the claim cannot be
        # interleaved. Reading the lock and then writing it left a window in
        # which two teachers both read "nobody holds this" and both wrote their
        # own claim. Here the update takes the session only when nobody holds
        # it, the lock has run out, or it is one's own; with no session yet it
        # makes one, and the unique index on `response_id` lets only one of two
        # racing teachers make it.
        try:
            self.col("review_session").update_one(
                {
                    "response_id": response_id,
                    "$or": [
                        {"lock": None},
                        {"lock.locked_until": {"$lte": _now()}},
                        {"lock.reviewer_id": reviewer_id},
                    ],
                },
                {"$set": {"lock": claim}, "$setOnInsert": {"visits": []}},
                upsert=True,
            )
        except IntegrityError:
            pass  # somebody else holds the session; read below who
        lock = self._lock(response_id)
        if lock is not None and not lock.is_held_by(reviewer_id):
            return False, lock.reviewer_name
        return True, None

    def _lock(self, response_id: str) -> ReviewLock | None:
        session = _review_session(self.db, response_id)
        return session.lock if session else None

    def unlock_response(self, response_id: str, reviewer_id: str) -> None:
        """Release the lock. Only the current holder can release it."""
        self.col("review_session").update_one(
            {"response_id": response_id, "lock.reviewer_id": reviewer_id},
            {"$set": {"lock": None}},
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
        """Note that a teacher opened a response for review; once per open visit.

        Called after `lock_response`, which made the session.
        """
        self.col("review_session").update_one(
            {
                "response_id": response_id,
                "visits": {
                    "$not": {"$elemMatch": {"reviewer_id": reviewer_id, "decided_at": None}}
                },
            },
            {
                "$push": {
                    "visits": {
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
            done = self.col("review_session").update_one(
                {
                    "response_id": response_id,
                    "visits": {"$elemMatch": {"reviewer_id": reviewer_id, "decided_at": None}},
                },
                {"$set": {"visits.$.decided_at": now, "visits.$.action": action}},
            )
            if not done.modified_count:
                return

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

    def cohort_stats(self, limit: int = 5000, owners: set[str] | None = None) -> dict:
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
        responses = self.col("response")
        # D071: a teacher's statistics are their classes' students; None, everyone's.
        scope: dict = {} if owners is None else {"account_id": {"$in": sorted(owners)}}
        assessed = list(
            responses.find(
                scope,
                {"overall_band": 1, "task_id": 1, "status": 1, "account_id": 1},
            )
        )
        by_band: dict[str, int] = {}
        # D078: by the band of the prompt answered -- did learners answering a
        # band's prompts land at that band, under it or above it?
        prompt_band = {
            t["task_id"]: t.get("band") for t in self.db["task"].find({}, {"task_id": 1, "band": 1})
        }
        order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        bands: dict[str, dict] = {}
        for r in assessed:
            got = r.get("overall_band")
            if got is not None:
                by_band[got] = by_band.get(got, 0) + 1
            asked = prompt_band.get(r["task_id"])
            if asked not in order:
                continue
            cell = bands.setdefault(
                asked,
                {"n": 0, "learners": set(), "at": 0, "below": 0, "above": 0, "waiting": 0},
            )
            cell["n"] += 1
            cell["learners"].add(r.get("account_id"))
            cell["waiting"] += int(r["status"] == "REVIEW_REQUIRED")
            if got in order:
                gap = order.index(got) - order.index(asked)
                cell["at" if gap == 0 else "below" if gap < 0 else "above"] += 1
        speakers = len({r["account_id"] for r in assessed if r.get("account_id") is not None})
        waiting = sum(1 for r in assessed if r["status"] == "REVIEW_REQUIRED")
        verified = responses.count_documents({"teacher_verified": 1, **scope})

        # Only decisions where the machine had proposed a band at all.
        # A review of a response the model refused to score is a teacher doing
        # the work from scratch, not a teacher agreeing or disagreeing with
        # anything, and counting it as agreement would flatter the model with
        # cases it never answered.
        decisions = sorted(
            (
                r
                for row in self.col("response").find(
                    {"reviews.old_band": {"$ne": None}, **scope}, {"reviews": 1}
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
            "by_prompt_band": [
                {**cell, "band": b, "learners": len(cell["learners"] - {None})}
                for b in order
                if (cell := bands.get(b))
            ],
            "agreement": {
                "decisions": len(decisions),
                "band_kept": kept,
                "band_changed": changed,
                # None, not 0.0, when nobody has reviewed anything yet: a rate
                # of zero would read as "teachers never agree with the model".
                "rate": round(kept / len(decisions), 3) if decisions else None,
            },
        }

    def assessments_by_account(self, since: str, until: str) -> dict[str, int]:
        """Assessments submitted in [since, until), per account (D033: the monthly figure).

        Per account rather than one total, so the caller can leave out research
        participants, who do not count towards a plan (BR-30).
        """
        rows = self.col("response").find(
            {
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
        """The latest scored assessment: the basis for suggesting what to learn next.

        The band is the one stored on the response, i.e. the teacher's band if
        the response was reviewed. `weakest_criteria` is empty for responses
        scored before D022 or without per-criterion indicators -- the suggestion
        then does not rely on a weakest criterion rather than guess one.
        """
        row = self.col("response").find_one(
            {"account_id": account_id, "overall_band": {"$ne": None}},
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
        """The responses, with everything their documents hold.

        The review history and the replay labels are part of the response's
        own document (D060) and go with it; its review session (D082) is
        removed beside it.
        """
        if not ids:
            return
        db = self.db
        within = {"response_id": {"$in": ids}}
        db["response"].delete_many(within)
        db["review_session"].delete_many(within)

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

    def upgrades_of_account(self, account_id: str, limit: int = 500) -> list[dict]:
        """Every upgrade this account made, oldest first: the phrase book's source (D070)."""
        rows = (
            self.col("response")
            .find(
                {"account_id": account_id, "coach_upgrade.phrases": {"$exists": True}},
                {"response_id": 1, "created_at": 1, "coach_upgrade": 1},
            )
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
            .limit(limit)
        )
        return [
            {
                "response_id": r["response_id"],
                "created_at": r.get("created_at"),
                **r["coach_upgrade"],
            }
            for r in rows
        ]

    def save_upgrade_phrases(self, response_id: str, phrases: list[dict]) -> None:
        """The phrases of one upgrade with their review state (D070), written back whole."""
        self.col("response").update_one(
            {"response_id": response_id}, {"$set": {"coach_upgrade.phrases": phrases}}
        )

    def feature_series(
        self, account_id: str, names: tuple[str, ...], limit: int = 100
    ) -> list[dict]:
        """The named measurements of one learner's scored assessments, in time order (D070).

        Read from the report each response keeps, so nothing new is stored. A
        name the recording did not yield is absent from that row's `values`.
        """
        rows = (
            self.col("response")
            .find(
                {"account_id": account_id, "overall_0_6": {"$ne": None}},
                {"response_id": 1, "task_id": 1, "created_at": 1, "report_json": 1},
            )
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        out = []
        for r in reversed(list(rows)):
            try:
                items = (json.loads(r.get("report_json") or "{}").get("features") or {}).get(
                    "items"
                )
            except (TypeError, ValueError):
                items = None
            values = {
                f["name"]: f["value"]
                for f in items or []
                if f.get("name") in names and isinstance(f.get("value"), int | float)
            }
            if values:
                out.append(
                    {
                        "response_id": r["response_id"],
                        "task_id": r.get("task_id"),
                        "created_at": r.get("created_at"),
                        "values": values,
                    }
                )
        return out

    # ---------- the language model's use per provider day (D072) ----------
    #
    # One document a day in `system`, `coach_usage.<YYYY-MM-DD>`, counted up as
    # requests go out: the global cap reads it, the administrator's dashboard
    # reads the last days of it. Counters, not a log: nothing about what was said.

    COACH_DAY_FIELDS = (
        "requests",
        "free_requests",
        "paid_requests",
        "paid_cost_usd",
        "upgrades",
        "drafts",
        "failed",
        "refused_user",
        "refused_global",
        "input_tokens",
        "output_tokens",
        "cost_usd",
    )

    def record_coach(
        self,
        day: str,
        *,
        account_id: str | None = None,
        error: str | None = None,
        **counts: float,
    ) -> None:
        """Add `counts` (names from COACH_DAY_FIELDS) to the provider day `day`."""
        unknown = set(counts) - set(self.COACH_DAY_FIELDS)
        if unknown:
            raise ValueError(f"unknown counters: {sorted(unknown)}")
        inc = {k: v for k, v in counts.items() if v}
        if error:
            # A field name may not hold a dot or start with a dollar sign.
            inc["errors." + error.replace(".", "·").lstrip("$")[:120]] = 1
        update: dict = {"$set": {"day": day, "updated_at": _now()}}
        if inc:
            update["$inc"] = inc
        if account_id and counts.get("requests"):
            update["$addToSet"] = {"accounts": account_id}
        self.col(SYSTEM).update_one({"key": "coach_usage." + day}, update, upsert=True)

    def coach_days(self, days: list[str]) -> list[dict]:
        """The counters of each of `days`, zeros for a day nothing happened; in order."""
        keys = ["coach_usage." + d for d in days]
        rows = {r["day"]: r for r in self.col(SYSTEM).find({"key": {"$in": keys}})}
        out = []
        for d in days:
            row = rows.get(d, {})
            item = {"day": d, **{k: row.get(k, 0) for k in self.COACH_DAY_FIELDS}}
            for money in ("cost_usd", "paid_cost_usd"):
                item[money] = round(float(item[money]), 6)
            item["accounts"] = len(row.get("accounts") or [])
            item["errors"] = dict(row.get("errors") or {})
            out.append(item)
        return out

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
            item = fields(r, LIST_FIELDS)
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
            {"account_id": account_id, "reviews.0": {"$exists": True}},
            {"reviews": 1},
        )
        return sum(
            1 for r in rows if since is None or any(x["created_at"] > since for x in r["reviews"])
        )

    def count_waiting_review(
        self, exclude: Collection[str] = (), owners: set[str] | None = None
    ) -> int:
        """Assessed responses waiting in the queue, less `exclude`; `owners` only (D071)."""
        query: dict = {"status": ResponseStatus.REVIEW_REQUIRED.value}
        if owners is not None:
            query["account_id"] = {"$in": sorted(owners)}
        rows = self.col("response").find(query, {"response_id": 1})
        hidden = set(exclude)
        return sum(r["response_id"] not in hidden for r in rows)

    def get(self, response_id: str) -> Response | None:
        row = self.col("response").find_one(
            {"response_id": response_id}, {"report_json": 1, "reviews": 1, "coach_upgrade": 1}
        )
        if row is None:
            return None
        report = Response.model_validate_json(row["report_json"])
        return report.model_copy(
            update={
                "reviews": [Review(**r) for r in row.get("reviews") or []],
                "upgrade": _upgrade(row.get("coach_upgrade")),
            }
        )

    def queue_with_locks(
        self, status: ResponseStatus, limit: int = 50, owners: set[str] | None = None
    ) -> list[dict]:
        """The review queue plus, for each response, who currently holds it.

        Two reads rather than one read per queued response: the caller used to
        loop over the responses calling `locked_by` on each, which costs one
        round trip per response -- fine with three in a test, linear in the size
        of the queue in a real term. `owners` keeps a teacher's queue to the
        students of their classes (D071); None is everyone's.
        """
        query: dict = {"status": status.value}
        if owners is not None:
            query["account_id"] = {"$in": sorted(owners)}
        rows = list(
            self.col("response")
            .find(query)
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
            .limit(limit)
        )
        now = _now()
        locks = {
            x["response_id"]: x.get("lock")
            for x in self.col("review_session").find(
                {"response_id": {"$in": [r["response_id"] for r in rows]}},
                {"response_id": 1, "lock": 1},
            )
        }
        out = []
        for r in rows:
            item = fields(r, LIST_FIELDS)
            lock = locks.get(r["response_id"])
            held = lock is not None and lock["locked_until"] > now
            item["locked_by"] = lock["reviewer_name"] if held else None  # type: ignore[index]
            item["account_id"] = r.get("account_id")
            out.append(item)
        return out  # type: ignore[return-value]

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


def _upgrade(stored: dict | None) -> CoachUpgrade | None:
    """The kept upgrade as its contract, or None; one that no longer reads is left out."""
    if not stored:
        return None
    try:
        return CoachUpgrade.model_validate(stored)
    except ValueError:
        logger.warning("coach upgrade does not match its contract; left out of the report")
        return None


def _profile_row(row: dict) -> dict:
    """One profile row: a verified result plus the criterion to practise first (D022).

    `weakest_criteria` is a position RELATIVE TO THE REFERENCE RESPONSES, not a
    criterion score; the hint comes from the fixed rule table `NEXT_TASK_HINTS`.
    Responses saved before D022 carry no indicators, so both fields stay empty
    rather than guessed.

    The `next_task_id` of D023, a practice task, went with the practice tasks (D083).
    """
    from aicefr.contracts import Criterion
    from aicefr.report.comments import NEXT_TASK_HINTS

    report = json.loads(row.pop("report_json") or "{}")
    weak = [Criterion(c) for c in ((report.get("assessment") or {}).get("weakest_criteria") or [])]
    row["weakest_criteria"] = [c.value for c in weak]
    row["next_task_hint"] = NEXT_TASK_HINTS[weak[0]] if weak else None
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
