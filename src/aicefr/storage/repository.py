"""Persistence for assessment results. Implements FR-32 to FR-38.

SQLite is used during development; switching to PostgreSQL on deployment is a
matter of changing the connection string. The schema follows the entity
relationship diagram in SDD section 5 closely.

Privacy rule: the speaker table holds only pseudonym codes. Never store a real
name, a student ID, or any contact detail in this database.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aicefr.contracts import (
    AppConfig,
    ReasonCode,
    Response,
    Review,
    ReviewLock,
    Status,
    TaskPurpose,
)
from aicefr.storage.audit_repository import prepare as prepare_audit
from aicefr.storage.audit_repository import write_audit
from aicefr.storage.db import Connection, DbRow, SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

SCHEMA = """
CREATE TABLE IF NOT EXISTS response (
    response_id     TEXT PRIMARY KEY,
    speaker_id      TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    status          TEXT NOT NULL,
    overall_0_6     REAL,
    overall_band    TEXT,
    teacher_verified INTEGER NOT NULL DEFAULT 0,
    model_version   TEXT,
    config_version  TEXT NOT NULL,
    report_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    account_id      TEXT,
    audio_path      TEXT,
    -- D023. 'practice' for a practice attempt: never in the teacher queue, the
    -- research export, or the class scoring statistics.
    purpose         TEXT NOT NULL DEFAULT 'assessment'
);
CREATE INDEX IF NOT EXISTS idx_response_speaker ON response(speaker_id);
CREATE INDEX IF NOT EXISTS idx_response_status  ON response(status);

CREATE TABLE IF NOT EXISTS review_action (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     TEXT NOT NULL REFERENCES response(response_id),
    reviewer_id     TEXT NOT NULL,
    old_score       REAL,
    new_score       REAL,
    old_band        TEXT,
    new_band        TEXT,
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_response ON review_action(response_id);

CREATE TABLE IF NOT EXISTS review_lock (
    response_id     TEXT PRIMARY KEY REFERENCES response(response_id),
    reviewer_id     TEXT NOT NULL,
    reviewer_name   TEXT NOT NULL,
    locked_until    TEXT NOT NULL
);

-- D041. When a teacher opened a response for review and when they decided:
-- the lock itself is deleted on decision, so its start is kept here.
CREATE TABLE IF NOT EXISTS review_session (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     TEXT NOT NULL,
    reviewer_id     TEXT NOT NULL,
    opened_at       TEXT NOT NULL,
    decided_at      TEXT,
    action          TEXT
);
CREATE INDEX IF NOT EXISTS idx_review_session_open
    ON review_session(response_id, reviewer_id, decided_at);

CREATE TABLE IF NOT EXISTS app_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    version     TEXT NOT NULL,
    updated_by  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- D028. When a person last looked at something that can change behind their
-- back (a teacher's decision on their response), so the sidebar can count
-- what is new since then.
CREATE TABLE IF NOT EXISTS seen_marker (
    account_id  TEXT NOT NULL,
    marker      TEXT NOT NULL,
    seen_at     TEXT NOT NULL,
    PRIMARY KEY (account_id, marker)
);
"""


logger = logging.getLogger(__name__)


class InvalidStateError(Exception):
    """A transition the state machine does not allow was attempted."""


def _audit(
    c: Connection, actor_id: str, action: str, target_id: str | None, detail: str | None
) -> None:
    """One row of this service's audit log, inside the caller's transaction."""
    write_audit(c, "assessment", actor_id, action, target_id, detail)


def _record_decision(
    c: Connection,
    response_id: str,
    reviewer_id: str,
    status: Status,
    action: str,
    reason: str,
    scores: tuple[float | None, float | None, str | None, str | None] = (None, None, None, None),
) -> DbRow:
    """Claim a review decision, record it and audit it; return the response's owner.

    `scores` is (old score, new score, old band, new band). The caller saves the
    report afterwards with the owner returned here, never with placeholders.
    """
    _claim_decision(c, response_id, status)
    owner = c.execute(
        "SELECT speaker_id, task_id, account_id FROM response WHERE response_id=?",
        (response_id,),
    ).fetchone()
    c.execute(
        """INSERT INTO review_action
           (response_id, reviewer_id, old_score, new_score, old_band, new_band,
            reason, created_at) VALUES (?,?,?,?,?,?,?,?)""",
        (response_id, reviewer_id, *scores, reason, _now()),
    )
    _audit(c, reviewer_id, action, response_id, reason)
    return owner


class Repository(SqlStore):
    """The repository. Each method opens and closes its own connection so that it
    stays safe under multiple threads."""

    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)
            prepare_audit(c)
            self._upgrade_schema(c)

    @staticmethod
    def _upgrade_schema(c: Connection) -> None:
        """Add the columns a database from an older build lacks (see `add_columns`)."""
        add_columns(
            c,
            "response",
            (
                ("account_id", "TEXT"),
                ("audio_path", "TEXT"),
                ("purpose", "TEXT NOT NULL DEFAULT 'assessment'"),
                # D043: when the speech service started on it, for the overdue sweep.
                ("started_at", "TEXT"),
            ),
        )
        Repository._backfill_review_bands(c)

    @staticmethod
    def _backfill_review_bands(c: Connection) -> None:
        """Dien `new_band` cho cac quyet dinh cu chi ghi tham so dau vao (D022 review).

        Truoc day giang vien chi sua diem thi band duoc suy lai nhung `new_band`
        luu None, va thong ke dong thuan coi None la "giu nguyen band": sua 3,2
        (B1) thanh 2,0 (A2) van tinh la dong y voi may. Chay lai vo hai: chi cham
        toi dong con thieu.
        """
        c.execute(
            "UPDATE review_action SET new_band = old_band"
            " WHERE new_band IS NULL AND new_score IS NULL AND old_band IS NOT NULL"
        )
        rows = c.execute(
            "SELECT id, new_score FROM review_action"
            " WHERE new_band IS NULL AND new_score IS NOT NULL"
        ).fetchall()
        if rows:
            from aicefr.scoring.scorer import load_model, to_band

            th = load_model()["band_thresholds"]
            c.executemany(
                "UPDATE review_action SET new_band=? WHERE id=?",
                [(to_band(r["new_score"], th).value, r["id"]) for r in rows],
            )

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
        with self._conn() as c:
            existing = c.execute(
                "SELECT teacher_verified, created_at, speaker_id, task_id, account_id,"
                " audio_path, status, purpose FROM response WHERE response_id=?",
                (report.response_id,),
            ).fetchone()

            if must_exist and (
                existing is None
                or existing["status"] not in (Status.QUEUED.value, Status.RUNNING.value)
            ):
                logger.warning(
                    "bo ket qua cham cua %s: bai da bi xoa hoac khong con dang cho",
                    report.response_id,
                )
                return False

            # A teacher's decision outranks anything the machine produces later.
            #
            # This used to be an unconditional overwrite, so a late background
            # job -- after a reload, a second worker, or a rescoring run --
            # could replace a verified result with a fresh estimate and clear
            # teacher_verified, leaving no trace that a human had ever decided.
            if (
                existing is not None
                and existing["teacher_verified"]
                and not (a and a.teacher_verified)
            ):
                logger.warning(
                    "refusing to overwrite a teacher-verified result for %s",
                    report.response_id,
                )
                return False

            # Preserve, rather than overwrite, anything the caller did not pass.
            # Dropping speaker_id or account_id here is what orphaned reports
            # once before; created_at is the submission time and must not drift
            # to "time of last write", or the queue reorders itself and the
            # stuck-job sweep measures from the wrong moment.
            def keep(column: str, value):
                """Keep what is already stored when the caller passes nothing."""
                if value is not None:
                    return value
                return existing[column] if existing is not None else None

            values = (
                keep("speaker_id", speaker_id or None),
                keep("task_id", task_id or None),
                report.status.value,
                a.overall_0_6 if a else None,
                a.overall_band.value if a and a.overall_band else None,
                int(a.teacher_verified) if a else 0,
                a.model_version if a else None,
                report.config_version,
                json.dumps(report.model_dump(mode="json"), ensure_ascii=False),
                keep("account_id", account_id),
                keep("audio_path", audio_path),
                keep("purpose", purpose.value if purpose else None) or TaskPurpose.ASSESSMENT.value,
            )
            if must_exist:
                # The worker's path updates, and only a response that still
                # waits: checked by the UPDATE itself, not by the SELECT above,
                # so an erasure committed in between leaves nothing to write to
                # -- never an INSERT that would bring the transcript back.
                cur = c.execute(
                    """UPDATE response SET speaker_id=?, task_id=?, status=?, overall_0_6=?,
                       overall_band=?, teacher_verified=?, model_version=?, config_version=?,
                       report_json=?, account_id=?, audio_path=?, purpose=?
                       WHERE response_id=? AND status IN (?,?) AND teacher_verified=0""",
                    (*values, report.response_id, Status.QUEUED.value, Status.RUNNING.value),
                )
                return cur.rowcount == 1

            # An upsert, not INSERT OR REPLACE: REPLACE deletes the old row
            # first, and with foreign keys on that delete cascades -- every
            # blind-rating assignment and "saw the machine" record of the
            # response went with a teacher's decision.
            c.execute(
                """INSERT INTO response
                   (response_id, speaker_id, task_id, status, overall_0_6, overall_band,
                    teacher_verified, model_version, config_version, report_json, created_at,
                    account_id, audio_path, purpose)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(response_id) DO UPDATE SET
                    speaker_id=excluded.speaker_id, task_id=excluded.task_id,
                    status=excluded.status, overall_0_6=excluded.overall_0_6,
                    overall_band=excluded.overall_band,
                    teacher_verified=excluded.teacher_verified,
                    model_version=excluded.model_version,
                    config_version=excluded.config_version,
                    report_json=excluded.report_json, created_at=excluded.created_at,
                    account_id=excluded.account_id, audio_path=excluded.audio_path,
                    purpose=excluded.purpose""",
                (
                    report.response_id,
                    *values[:9],
                    existing["created_at"] if existing is not None else _now(),
                    *values[9:],
                ),
            )
        return True

    def set_status(
        self,
        response_id: str,
        status: Status,
        reasons: list[ReasonCode] | None = None,
        only_from: tuple[Status, ...] | None = None,
    ) -> bool:
        """Change the status of a response being processed; True when it changed.

        Both the status column and the JSON blob are updated so the two cannot
        drift apart. List queries read the column while the report page reads the
        JSON; if they diverge, one of the two places would be lying.

        `only_from`: change it only while it is in one of these states, checked
        by the UPDATE itself -- a result that lands between the caller's look
        and this write is not overwritten (D043: the overdue sweep, a worker's
        failure report).
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT report_json, status FROM response WHERE response_id=?", (response_id,)
            ).fetchone()
            if row is None or (only_from and row["status"] not in {s.value for s in only_from}):
                return False
            report = json.loads(row["report_json"])
            report["status"] = status.value
            if reasons is not None:
                report["reasons"] = [r.value for r in reasons]
            cur = c.execute(
                "UPDATE response SET status=?, report_json=? WHERE response_id=? AND status=?",
                (status.value, json.dumps(report, ensure_ascii=False), response_id, row["status"]),
            )
            return cur.rowcount == 1

    def mark_running(self, response_id: str) -> bool:
        """QUEUED becomes RUNNING, stamped with the time; anything else stays as it is.

        The speech service says it started and, later, what it found. Between
        services the two messages can arrive the other way round; a "started"
        arriving after the result must not put a finished response back to
        RUNNING, so only a QUEUED response moves.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT report_json FROM response WHERE response_id=? AND status=?",
                (response_id, Status.QUEUED.value),
            ).fetchone()
            if row is None:
                return False
            report = json.loads(row["report_json"])
            report["status"] = Status.RUNNING.value
            c.execute(
                "UPDATE response SET status=?, report_json=?, started_at=?"
                " WHERE response_id=? AND status=?",
                (
                    Status.RUNNING.value,
                    json.dumps(report, ensure_ascii=False),
                    _now(),
                    response_id,
                    Status.QUEUED.value,
                ),
            )
        return True

    def running_since(self, cutoff: str) -> list[str]:
        """Responses RUNNING since before `cutoff`: the speech service never finished them."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id FROM response WHERE status=? AND started_at <= ?",
                (Status.RUNNING.value, cutoff),
            ).fetchall()
        return [r["response_id"] for r in rows]

    def queued_since(self, cutoff: str) -> list[str]:
        """Responses still QUEUED, submitted before `cutoff`: no worker ever took them."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id FROM response WHERE status=? AND created_at <= ?",
                (Status.QUEUED.value, cutoff),
            ).fetchall()
        return [r["response_id"] for r in rows]

    def fail_stuck(self, minutes: int = 10) -> list[str]:
        """Mark responses stuck in QUEUED or RUNNING for too long as FAILED.

        Runs at startup. If the process dies mid-run, whatever was being
        processed stays in RUNNING forever; left alone, the submitter waits
        indefinitely and NFR-11, on the share of jobs reaching a definite final
        state, is never met.
        """
        cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id FROM response WHERE status IN (?,?) AND created_at <= ?",
                (Status.QUEUED.value, Status.RUNNING.value, cutoff),
            ).fetchall()
        ids = [r["response_id"] for r in rows]
        for rid in ids:
            self.set_status(rid, Status.FAILED, [ReasonCode.PROCESSING_INTERRUPTED])
        return ids

    def status_of(self, response_id: str) -> dict | None:
        """Lightweight status information for periodic polling. Serves FR-05."""
        with self._conn() as c:
            row = c.execute(
                "SELECT response_id, task_id, status, overall_0_6, overall_band,"
                " teacher_verified, created_at, purpose FROM response WHERE response_id=?",
                (response_id,),
            ).fetchone()
        return dict(row) if row else None

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
        with self._conn() as c:
            # One statement, so the check and the claim cannot be interleaved.
            #
            # Reading the row and then writing it left a window in which two
            # teachers both read "nobody holds this" and both wrote their own
            # claim: the lock reported success to both, which is the one thing
            # it exists to prevent. The conflict clause is evaluated atomically,
            # so exactly one writer wins.
            c.execute(
                """INSERT INTO review_lock(response_id, reviewer_id, reviewer_name, locked_until)
                   VALUES(?,?,?,?)
                   ON CONFLICT(response_id) DO UPDATE SET
                       reviewer_id = excluded.reviewer_id,
                       reviewer_name = excluded.reviewer_name,
                       locked_until = excluded.locked_until
                   WHERE review_lock.locked_until <= ?
                      OR review_lock.reviewer_id = excluded.reviewer_id""",
                (response_id, reviewer_id, reviewer_name, until, _now()),
            )
            row = c.execute(
                "SELECT response_id, reviewer_id, reviewer_name, locked_until"
                " FROM review_lock WHERE response_id=?",
                (response_id,),
            ).fetchone()
        lock = ReviewLock(**dict(row)) if row else None
        if lock is not None and not lock.is_held_by(reviewer_id):
            return False, lock.reviewer_name
        return True, None

    def unlock_response(self, response_id: str, reviewer_id: str) -> None:
        """Release the lock. Only the current holder can release it."""
        with self._conn() as c:
            c.execute(
                "DELETE FROM review_lock WHERE response_id=? AND reviewer_id=?",
                (response_id, reviewer_id),
            )

    def locked_by(self, response_id: str) -> str | None:
        """Name of whoever holds a still-valid lock, or None."""
        with self._conn() as c:
            row = c.execute(
                "SELECT reviewer_name, locked_until FROM review_lock WHERE response_id=?",
                (response_id,),
            ).fetchone()
        if row is None or row["locked_until"] <= _now():
            return None
        return row["reviewer_name"]

    def review_history(self, response_id: str) -> list[Review]:
        """History of result edits for one response. FR-31."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT reviewer_id, old_score, new_score, old_band, new_band, reason,"
                " created_at FROM review_action WHERE response_id=? ORDER BY created_at",
                (response_id,),
            ).fetchall()
        return [Review(**dict(r)) for r in rows]

    # ---------- personal data: export and erasure (FR-34, FR-35, FR-38) ----------

    def speaking_profile(self, account_id: str) -> list[dict]:
        """Verified results for one learner, for the exported profile.

        Only rows a teacher has confirmed. An unverified machine score is an
        estimate; putting it in an exportable profile would let it travel as
        though it were a finding, which is exactly what FR-21 forbids.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id, task_id, overall_0_6, overall_band, created_at, report_json"
                " FROM response WHERE account_id=? AND teacher_verified=1"
                " ORDER BY created_at",
                (account_id,),
            ).fetchall()
        return [_profile_row(dict(r)) for r in rows]

    def open_review_session(self, response_id: str, reviewer_id: str) -> None:
        """Note that a teacher opened a response for review; once per open session."""
        with self._conn() as c:
            open_row = c.execute(
                "SELECT 1 FROM review_session WHERE response_id=? AND reviewer_id=?"
                " AND decided_at IS NULL",
                (response_id, reviewer_id),
            ).fetchone()
            if not open_row:
                c.execute(
                    "INSERT INTO review_session(response_id, reviewer_id, opened_at) VALUES(?,?,?)",
                    (response_id, reviewer_id, _now()),
                )

    def close_review_session(self, response_id: str, reviewer_id: str, action: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE review_session SET decided_at=?, action=? WHERE response_id=?"
                " AND reviewer_id=? AND decided_at IS NULL",
                (_now(), action, response_id, reviewer_id),
            )

    def review_sessions(self, limit: int = 5000) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT opened_at, decided_at, action FROM review_session"
                " WHERE decided_at IS NOT NULL ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def settled_counts(self) -> tuple[int, int]:
        """(scored assessments the machine settled alone, scored assessments that reached a result).

        Alone: COMPLETED with no teacher confirmation. Reached a result:
        COMPLETED or REVIEW_REQUIRED, with a machine score.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT SUM(CASE WHEN status='COMPLETED' AND teacher_verified=0 THEN 1 ELSE 0 END),"
                " COUNT(*) FROM response WHERE purpose='assessment' AND overall_0_6 IS NOT NULL"
                " AND status IN ('COMPLETED','REVIEW_REQUIRED')"
            ).fetchone()
        return int(row[0] or 0), int(row[1] or 0)

    def scored_assessments(
        self,
        accounts: Collection[str] | None = None,
        machine_only: bool = False,
        limit: int = 20000,
    ) -> list[dict]:
        """Scored assessments, oldest first; the latest `limit` when there are more.

        The test-retest pairs of D042 and the outcomes of the feedback study
        (D040) come from here. `accounts` narrows to those learners;
        `machine_only` keeps the machine's own scores, leaving out the rows a
        teacher's decision overwrote -- a test-retest pair compares the
        instrument with itself.
        """
        where = ["overall_0_6 IS NOT NULL", "purpose='assessment'", "account_id IS NOT NULL"]
        args: list = []
        if accounts is not None:
            ids = list(accounts)
            if not ids:
                return []
            where.append(f"account_id IN ({','.join('?' * len(ids))})")
            args += ids
        if machine_only:
            where.append("teacher_verified=0")
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id, task_id, overall_0_6, model_version, created_at FROM response"
                f" WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT ?",
                (*args, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

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
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id, task_id, status, overall_0_6, overall_band,"
                " teacher_verified, model_version, created_at"
                " FROM response WHERE account_id=? AND overall_0_6 IS NOT NULL"
                " ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (account_id, limit),
            ).fetchall()
        # The latest `limit`, in time order: "the last three results" must be.
        return [dict(r) for r in reversed(rows)]

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
        with self._conn() as c:
            by_band = {
                r["overall_band"]: r["n"]
                for r in c.execute(
                    "SELECT overall_band, COUNT(*) n FROM response"
                    " WHERE overall_band IS NOT NULL AND purpose='assessment'"
                    " GROUP BY overall_band"
                ).fetchall()
            }
            by_task = [
                dict(r)
                for r in c.execute(
                    "SELECT task_id, COUNT(*) n,"
                    " AVG(overall_0_6) avg_score,"
                    " SUM(CASE WHEN status='REVIEW_REQUIRED' THEN 1 ELSE 0 END) waiting"
                    " FROM response WHERE purpose='assessment' GROUP BY task_id ORDER BY task_id"
                ).fetchall()
            ]
            total = c.execute(
                "SELECT COUNT(*) n FROM response WHERE purpose='assessment'"
            ).fetchone()["n"]
            speakers = c.execute(
                "SELECT COUNT(DISTINCT account_id) n FROM response"
                " WHERE account_id IS NOT NULL AND purpose='assessment'"
            ).fetchone()["n"]
            waiting = c.execute(
                "SELECT COUNT(*) n FROM response"
                " WHERE status='REVIEW_REQUIRED' AND purpose='assessment'"
            ).fetchone()["n"]
            verified = c.execute(
                "SELECT COUNT(*) n FROM response WHERE teacher_verified=1"
            ).fetchone()["n"]

            # Only decisions where the machine had proposed a band at all.
            # A review of a response the model refused to score is a teacher
            # doing the work from scratch, not a teacher agreeing or
            # disagreeing with anything, and counting it as agreement would
            # flatter the model with cases it never answered.
            decisions = c.execute(
                "SELECT old_band, new_band FROM review_action WHERE old_band IS NOT NULL LIMIT ?",
                (limit,),
            ).fetchall()

        kept = sum(1 for r in decisions if r["new_band"] == r["old_band"])
        changed = len(decisions) - kept
        return {
            # Two different counts, and the screen shows both. `responses` alone
            # read as a contradiction next to the review backlog: 7 scored
            # responses beside 13 waiting for review looks like an error until
            # you know that a response the model refused to score is also
            # waiting -- and is in fact the kind most in need of a teacher.
            "responses": total,
            "scored": sum(by_band.values()),
            "speakers": speakers,
            "waiting_for_review": waiting,
            "teacher_verified": verified,
            "by_band": by_band,
            "by_task": [
                {
                    "task_id": r["task_id"],
                    "n": r["n"],
                    "avg_score": round(r["avg_score"], 2) if r["avg_score"] is not None else None,
                    "waiting": r["waiting"],
                }
                for r in by_task
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
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id, task_id, report_json FROM response"
                " WHERE purpose='practice' AND status=?",
                (Status.COMPLETED.value,),
            ).fetchall()
        by_criterion: dict[str, dict[str, int]] = {}
        done = 0
        for r in rows:
            cell = by_criterion.setdefault(
                criterion_of.get(r["task_id"], "khac"), {"attempts": 0, "completed": 0}
            )
            cell["attempts"] += 1
            if _practice_completed(r["report_json"]):
                cell["completed"] += 1
                done += 1
        return {
            "attempts": len(rows),
            "learners": len({r["account_id"] for r in rows if r["account_id"]}),
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
        sql = (
            "SELECT response_id, task_id, status, created_at, report_json FROM response"
            " WHERE account_id=? AND purpose='practice'"
        )
        args: tuple = (account_id,)
        if task_id is not None:
            sql += " AND task_id=?"
            args += (task_id,)
        with self._conn() as c:
            # rowid keeps submission order when two attempts share a second
            # (created_at only has second precision).
            rows = c.execute(sql + " ORDER BY created_at, rowid", args).fetchall()
        out = []
        for r in rows:
            result = (json.loads(r["report_json"] or "{}").get("practice")) or {}
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
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id, COUNT(*) AS n FROM response"
                " WHERE purpose='assessment' AND account_id IS NOT NULL"
                " AND created_at >= ? AND created_at < ? GROUP BY account_id",
                (since, until),
            ).fetchall()
        return {r["account_id"]: r["n"] for r in rows}

    def latest_assessment(self, account_id: str) -> dict | None:
        """The latest scored assessment: the basis for suggesting practice.

        The band is the one stored on the row, i.e. the teacher's band if the response
        was reviewed. `weakest_criteria` is empty for responses scored before D022 or
        without per-criterion indicators -- the suggestion then does not rely on a
        weakest criterion rather than guess one.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT response_id, overall_band, teacher_verified, created_at, report_json"
                " FROM response WHERE account_id=? AND purpose='assessment'"
                " AND overall_band IS NOT NULL ORDER BY created_at DESC LIMIT 1",
                (account_id,),
            ).fetchone()
        if row is None:
            return None
        assessment = json.loads(row["report_json"] or "{}").get("assessment") or {}
        return {
            "response_id": row["response_id"],
            "band": row["overall_band"],
            "teacher_verified": bool(row["teacher_verified"]),
            "created_at": row["created_at"],
            "weakest_criteria": list(assessment.get("weakest_criteria") or []),
        }

    def erasure_preview(self, speaker_id: str) -> dict:
        """What an erasure would remove, without removing anything.

        FR-35 requires showing the artifacts first and asking for the id a
        second time. Deleting a participant's recordings is irreversible, so
        the interface must make the operator look at the list before acting.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id, audio_path FROM response WHERE speaker_id=?",
                (speaker_id,),
            ).fetchall()
            reviews = c.execute(
                "SELECT COUNT(*) AS n FROM review_action WHERE response_id IN"
                " (SELECT response_id FROM response WHERE speaker_id=?)",
                (speaker_id,),
            ).fetchone()["n"]
        audio_files = sum(1 for r in rows if r["audio_path"] and Path(r["audio_path"]).is_file())
        return {
            "speaker_id": speaker_id,
            "responses": len(rows),
            "audio_files": audio_files,
            "review_actions": reviews,
            "response_ids": [r["response_id"] for r in rows],
        }

    def erase_speaker(self, speaker_id: str, actor_id: str) -> dict:
        """Delete one participant's recordings and reports. Irreversible.

        Removes the audio from disk as well as the rows. Leaving the files
        behind would make the deletion a lie: a recording of someone's voice is
        personal data whether or not a database row still points at it.

        Writes an audit entry that records the erasure itself. The entry keeps
        the pseudonym and the counts, not the content.
        """
        preview = self.erasure_preview(speaker_id)
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id, audio_path FROM response WHERE speaker_id=?",
                (speaker_id,),
            ).fetchall()
            for r in rows:
                if r["audio_path"]:
                    Path(r["audio_path"]).unlink(missing_ok=True)
            ids = [r["response_id"] for r in rows]
            marks = ",".join("?" * len(ids)) or "NULL"
            if ids:
                c.execute(f"DELETE FROM review_action WHERE response_id IN ({marks})", ids)
                c.execute(f"DELETE FROM review_lock WHERE response_id IN ({marks})", ids)
            c.execute("DELETE FROM response WHERE speaker_id=?", (speaker_id,))
            _audit(
                c,
                actor_id,
                "ERASE_PARTICIPANT",
                speaker_id,
                f"{preview['responses']} responses, {preview['audio_files']} audio files",
            )
        return preview

    def erase_one_response(self, response_id: str, actor_id: str) -> bool:
        """Delete a single response: its row, its review history, its audio file.

        Separate from `erase_speaker` because the two answer different requests.
        `erase_speaker` is an administrator acting on a withdrawal of consent and
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
        with self._conn() as c:
            row = c.execute(
                "SELECT audio_path, teacher_verified FROM response WHERE response_id=?",
                (response_id,),
            ).fetchone()
            if row is None:
                return False
            if row["teacher_verified"]:
                raise InvalidStateError(
                    "bài đã được giảng viên xác nhận nên không tự xoá được;"
                    " hãy liên hệ giảng viên phụ trách"
                )

            if row["audio_path"]:
                # The file, not only the row. A recording of someone's voice is
                # personal data whether or not a row still points at it.
                Path(row["audio_path"]).unlink(missing_ok=True)
            c.execute("DELETE FROM review_action WHERE response_id=?", (response_id,))
            c.execute("DELETE FROM review_lock WHERE response_id=?", (response_id,))
            c.execute("DELETE FROM response WHERE response_id=?", (response_id,))
            # The entry records that a deletion happened and who asked for it.
            # It carries no transcript and no score: an audit log that keeps a
            # copy of what was deleted has not deleted it.
            _audit(c, actor_id, "ERASE_OWN_RESPONSE", response_id, "người học tự xoá bài của mình")
        return True

    def audio_path_of(self, response_id: str) -> str | None:
        """Filesystem path of a response's audio file.

        Internal use only. Never return this path through the API: leaking the
        server's directory layout is one step towards leaking more.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT audio_path FROM response WHERE response_id=?", (response_id,)
            ).fetchone()
        return row["audio_path"] if row else None

    def owner_of(self, response_id: str) -> str | None:
        """Return the submitter's account_id, or None if the response has no owner."""
        with self._conn() as c:
            row = c.execute(
                "SELECT account_id FROM response WHERE response_id=?", (response_id,)
            ).fetchone()
        return row["account_id"] if row else None

    def list_by_account(self, account_id: str, limit: int = 200) -> list[dict]:
        """List one person's responses. Serves FR-04.

        `reviewed_at` is the time of the latest teacher decision, so the list
        can mark a result a teacher confirmed since the owner last looked (D028).
        """
        with self._conn() as c:
            rows = c.execute(
                """SELECT r.response_id, r.speaker_id, r.task_id, r.status, r.overall_0_6,
                          r.overall_band, r.teacher_verified, r.created_at, r.purpose,
                          (SELECT MAX(a.created_at) FROM review_action a
                            WHERE a.response_id = r.response_id) AS reviewed_at
                   FROM response r WHERE r.account_id=? ORDER BY r.created_at DESC LIMIT ?""",
                (account_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---------- what is new for a person (D028) ----------

    def seen_at(self, account_id: str, marker: str) -> str | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT seen_at FROM seen_marker WHERE account_id=? AND marker=?",
                (account_id, marker),
            ).fetchone()
        return row["seen_at"] if row else None

    def mark_seen(self, account_id: str, marker: str) -> str:
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO seen_marker(account_id, marker, seen_at) VALUES(?,?,?)"
                " ON CONFLICT(account_id, marker) DO UPDATE SET seen_at=excluded.seen_at",
                (account_id, marker, now),
            )
        return now

    def count_reviewed_since(self, account_id: str, since: str | None) -> int:
        """The owner's assessed responses a teacher decided on after `since`.

        Never-looked (`since` None) counts every decided response: a student who
        has not opened their list yet has not seen any of those decisions.
        """
        # Two statements rather than "(? IS NULL OR ...)": PostgreSQL cannot tell
        # the type of a parameter that is only ever compared with NULL.
        sql = """SELECT COUNT(DISTINCT r.response_id) FROM response r
                 JOIN review_action a ON a.response_id = r.response_id
                 WHERE r.account_id = ? AND r.purpose = 'assessment'"""
        args: tuple = (account_id,)
        if since is not None:
            sql += " AND a.created_at > ?"
            args += (since,)
        with self._conn() as c:
            return c.execute(sql, args).fetchone()[0]

    def count_waiting_review(self, exclude: Collection[str] = ()) -> int:
        """How many assessed responses wait in the teacher queue, less the ones in `exclude`."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id FROM response WHERE status=? AND purpose='assessment'",
                (Status.REVIEW_REQUIRED.value,),
            ).fetchall()
        hidden = set(exclude)
        return sum(r["response_id"] not in hidden for r in rows)

    def get(self, response_id: str) -> Response | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT report_json FROM response WHERE response_id=?", (response_id,)
            ).fetchone()
        return Response.model_validate_json(row["report_json"]) if row else None

    def queue_with_locks(self, status: Status, limit: int = 50) -> list[dict]:
        """The review queue plus, for each row, who currently holds it.

        One query with a LEFT JOIN rather than a query per row. The caller used
        to loop over the rows calling `locked_by` on each, which costs one round
        trip per queued response: fine with three rows in a test, linear in the
        size of the queue in a real term.
        """
        with self._conn() as c:
            rows = c.execute(
                """SELECT r.response_id, r.speaker_id, r.task_id, r.status,
                          r.overall_0_6, r.overall_band, r.teacher_verified, r.created_at,
                          CASE WHEN l.locked_until > ? THEN l.reviewer_name END AS locked_by
                   FROM response r
                   LEFT JOIN review_lock l ON l.response_id = r.response_id
                   WHERE r.status = ? AND r.purpose = 'assessment'
                   ORDER BY r.created_at
                   LIMIT ?""",
                (_now(), status.value, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_all(self, limit: int = 200) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT response_id, speaker_id, task_id, status, overall_0_6,
                          overall_band, teacher_verified, created_at
                   FROM response ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

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
        if report.status is not Status.REVIEW_REQUIRED:
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
            from aicefr.scoring.scorer import to_band

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
            from aicefr.scoring.scorer import to_band

            a.overall_band = to_band(new_score, thresholds)

        # Khong con vong lap chep diem moi xuong tung tieu chi: tu khi
        # CriterionScore thanh CriterionCoverage, cac dong do chi mang do phu
        # phep do, va viec giang vien sua diem khong lam doi so phep do da tinh
        # duoc tren ban ghi.

        a.teacher_verified = True
        report.status = Status.COMPLETED

        with self._conn() as c:
            owner = _record_decision(
                c,
                response_id,
                reviewer_id,
                Status.COMPLETED,
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
        # loudly — the row was still there, just orphaned.
        self.save(report, owner["speaker_id"], owner["task_id"], account_id=owner["account_id"])
        return report

    def close_unscorable(self, response_id: str, reviewer_id: str, reason: str) -> Response | None:
        """Giang vien dong mot bai may khong cham duoc ma khong cho diem.

        Chi cho bai dang cho duyet VA khong co ket qua cham. Bai chuyen sang
        REJECTED: sinh vien thay "ban ghi chua dung duoc" va duoc moi nop lai.
        Co dong review_action (khong co band, nen khong tinh vao ty le dong thuan)
        va dong audit, nhu moi quyet dinh khac.
        """
        report = self.get(response_id)
        if report is None:
            return None
        if report.status is not Status.REVIEW_REQUIRED or report.assessment is not None:
            raise InvalidStateError("chỉ đóng được bài đang chờ duyệt mà máy không chấm được")
        report.status = Status.REJECTED
        with self._conn() as c:
            owner = _record_decision(
                c, response_id, reviewer_id, Status.REJECTED, "REVIEW_CLOSED", reason
            )
        self.save(report, owner["speaker_id"], owner["task_id"], account_id=owner["account_id"])
        return report

    def research_rows(self, allowed_account_ids: set[str], limit: int = 5000) -> list[dict]:
        """Rows for the research export, restricted to accounts that allow it.

        The caller passes the allowed set rather than this method reading the
        consent table itself. Two reasons: the scoring database and the consent
        table are separate concerns, and a caller holding an explicit set is
        auditable -- you can print it, count it, and show it to an ethics
        reviewer. A join hidden inside the query cannot be shown to anybody.

        Never returns the transcript. The export exists to analyse scores
        against human ratings; shipping the words of a recording around is a
        risk with no matching benefit.
        """
        if not allowed_account_ids:
            return []
        # Loc TRONG SQL roi moi LIMIT. Truoc day LIMIT 5000 dong dau tien roi
        # moi loc trong Python: khi co hon 5000 dong, bai moi hon cua nguoi da
        # dong y roi mat im lang ma row_count van trong hop le. Chia ID thanh
        # tung lo de khong vuot gioi han so tham so cua SQLite.
        ids = sorted(allowed_account_ids)
        out: list[dict] = []
        with self._conn() as c:
            for i in range(0, len(ids), 500):
                chunk = ids[i : i + 500]
                marks = ",".join("?" * len(chunk))
                out += [
                    dict(r)
                    for r in c.execute(
                        "SELECT response_id, speaker_id, task_id, status, overall_0_6,"
                        " overall_band, teacher_verified, model_version, config_version,"
                        f" created_at, account_id FROM response WHERE account_id IN ({marks})"
                        # D023: practice attempts are constrained exercises (given
                        # words, reading aloud), not free speech to compare with
                        # teacher ratings.
                        " AND purpose='assessment'",
                        chunk,
                    )
                ]
        out.sort(key=lambda r: r["created_at"])
        return out[:limit]

    # ---------- runtime configuration (FR-08, FR-36) ----------
    #
    # Settings that an administrator may change while the system is running live
    # here rather than in environment variables, for one reason: a change has to
    # be attributable. The row carries who changed it, when, and under which
    # version label -- an env var carries none of that, and "who raised the
    # silence threshold the week the results went strange" is a question that
    # will be asked.

    def set_config(self, key: str, value: str, version: str, actor_id: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO app_config(key, value, version, updated_by, updated_at)"
                " VALUES(?,?,?,?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                " version=excluded.version, updated_by=excluded.updated_by,"
                " updated_at=excluded.updated_at",
                (key, value, version, actor_id, _now()),
            )

    def get_config(self, key: str) -> AppConfig | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT key, value, version, updated_by, updated_at FROM app_config WHERE key=?",
                (key,),
            ).fetchone()
        return AppConfig(**dict(row)) if row else None

    def write_audit(
        self, actor_id: str, action: str, target_id: str | None, detail: str | None
    ) -> None:
        """Record one accountable action.

        Kept deliberately small: an actor, what they did, to what, and when.
        No transcript, no pseudonym of a third party, no free text unless the
        caller passes it -- the log itself must not become a second copy of the
        personal data it is meant to protect.
        """
        with self._conn() as c:
            _audit(c, actor_id, action, target_id, detail)

    def audit(self, limit: int = 100) -> list[dict]:
        """This service's latest audit entries, newest first, as `AuditLog.recent` gives them."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, actor_id, action, target_id, detail, created_at FROM audit_log"
                " WHERE service='assessment' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) n FROM response").fetchone()["n"]
            by_status = {
                r["status"]: r["n"]
                for r in c.execute(
                    "SELECT status, COUNT(*) n FROM response GROUP BY status"
                ).fetchall()
            }
            by_band = {
                r["overall_band"]: r["n"]
                for r in c.execute(
                    "SELECT overall_band, COUNT(*) n FROM response"
                    " WHERE overall_band IS NOT NULL GROUP BY overall_band"
                ).fetchall()
            }
            verified = c.execute(
                "SELECT COUNT(*) n FROM response WHERE teacher_verified=1"
            ).fetchone()["n"]
        return {
            "total": total,
            "by_status": by_status,
            "by_band": by_band,
            "teacher_verified": verified,
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


def _claim_decision(c: Connection, response_id: str, new_status: Status) -> None:
    """Chuyen REVIEW_REQUIRED -> new_status NGUYEN TU, trong transaction cua quyet dinh.

    Kiem trang thai bang mot lan doc truoc do khong du: hai giang vien cung doc
    REVIEW_REQUIRED thi ca hai quyet dinh deu duoc chap nhan va cai sau de cai
    truoc. UPDATE co dieu kien chi thanh cong cho mot nguoi; nguoi con lai nhan
    loi va transaction cua ho bi huy, khong de lai dong review_action nao.
    """
    claimed = c.execute(
        "UPDATE response SET status=? WHERE response_id=? AND status=?",
        (new_status.value, response_id, Status.REVIEW_REQUIRED.value),
    ).rowcount
    if claimed == 0:
        raise InvalidStateError("bài vừa được giảng viên khác quyết định")


def _band_thresholds(model_version: str | None) -> dict[str, float]:
    """Nguong band cua CHINH mo hinh da cham bai (muc 13 review).

    Dung mo hinh mac dinh cho moi bai sai khi admin da kich hoat mo hinh khac.
    Bai do giang vien tu cham ("teacher") hoac mo hinh khong con tren dia thi
    dung mo hinh mac dinh.
    """
    from aicefr.scoring.scorer import ModelNotFoundError, load_model

    if model_version:
        try:
            return load_model(model_version)["band_thresholds"]
        except (ModelNotFoundError, KeyError):
            pass
    return load_model()["band_thresholds"]
