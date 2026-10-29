"""SQLite store of the feedback study (D040): the study, who is in which arm, their survey."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from aicefr.research.study import STATUSES
from aicefr.storage.db import SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

SCHEMA = """
CREATE TABLE IF NOT EXISTS study (
    study_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    seed        INTEGER NOT NULL,
    min_days    INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',   -- running | survey | closed
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    closed_at   TEXT
);

CREATE TABLE IF NOT EXISTS study_participant (
    study_id     TEXT NOT NULL REFERENCES study(study_id),
    account_id   TEXT NOT NULL,
    arm          TEXT NOT NULL,                    -- feedback | score_only
    enrolled_at  TEXT NOT NULL,
    withdrawn_at TEXT,
    PRIMARY KEY (study_id, account_id)
);

CREATE TABLE IF NOT EXISTS study_survey (
    study_id      TEXT NOT NULL REFERENCES study(study_id),
    account_id    TEXT NOT NULL,
    answers_json  TEXT NOT NULL,
    submitted_at  TEXT NOT NULL,
    PRIMARY KEY (study_id, account_id)
);
"""


class StudyRepository(SqlStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)
            # The end of the measured phase: scores after it, when both arms see
            # feedback again, are not outcomes. A participant's code, fixed at
            # enrolment so exports of different days line up.
            add_columns(c, "study", (("measured_until", "TEXT"),))
            add_columns(c, "study_participant", (("code", "TEXT"),))

    def create(
        self, name: str, seed: int, min_days: int, created_by: str, arms: dict[str, str]
    ) -> str:
        study_id = "st-" + uuid.uuid4().hex[:10]
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO study(study_id, name, seed, min_days, created_by, created_at)"
                " VALUES(?,?,?,?,?,?)",
                (study_id, name, seed, min_days, created_by, now),
            )
            # Codes in the order of the random assignment: they say nothing of
            # who is who, and never change.
            c.executemany(
                "INSERT INTO study_participant(study_id, account_id, arm, enrolled_at, code)"
                " VALUES(?,?,?,?,?)",
                [
                    (study_id, account_id, arm, now, f"P{i:03d}")
                    for i, (account_id, arm) in enumerate(arms.items(), 1)
                ],
            )
        return study_id

    def get(self, study_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM study WHERE study_id=?", (study_id,)).fetchone()
        return dict(row) if row else None

    def active(self) -> dict | None:
        """The study still running or collecting surveys; at most one at a time."""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM study WHERE status IN ('running','survey')"
                " ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def all(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT s.*, (SELECT COUNT(*) FROM study_participant p"
                " WHERE p.study_id=s.study_id AND p.withdrawn_at IS NULL) AS participants,"
                " (SELECT COUNT(*) FROM study_survey v WHERE v.study_id=s.study_id) AS surveys"
                " FROM study s ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def set_status(self, study_id: str, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown study status {status}")
        now = _now()
        with self._conn() as c:
            c.execute(
                "UPDATE study SET status=?, closed_at=?,"
                " measured_until=COALESCE(measured_until, ?) WHERE study_id=?",
                (status, now if status == "closed" else None, now, study_id),
            )

    def participants(self, study_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id, arm, enrolled_at, withdrawn_at, code FROM study_participant"
                " WHERE study_id=? ORDER BY account_id",
                (study_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def membership(self, account_id: str) -> dict | None:
        """This learner's place in the active study, withdrawn or not."""
        with self._conn() as c:
            row = c.execute(
                "SELECT s.study_id, s.name, s.status, p.arm, p.withdrawn_at FROM study s"
                " JOIN study_participant p ON p.study_id=s.study_id"
                " WHERE p.account_id=? AND s.status IN ('running','survey')"
                " ORDER BY s.created_at DESC LIMIT 1",
                (account_id,),
            ).fetchone()
        return dict(row) if row else None

    def withdraw(self, account_id: str) -> int:
        """Leave every active study; from then on the learner sees full feedback again."""
        with self._conn() as c:
            cur = c.execute(
                "UPDATE study_participant SET withdrawn_at=? WHERE account_id=?"
                " AND withdrawn_at IS NULL AND study_id IN"
                " (SELECT study_id FROM study WHERE status IN ('running','survey'))",
                (_now(), account_id),
            )
        return cur.rowcount

    def save_survey(self, study_id: str, account_id: str, answers: dict) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO study_survey(study_id, account_id, answers_json, submitted_at)"
                " VALUES(?,?,?,?) ON CONFLICT(study_id, account_id) DO UPDATE SET"
                " answers_json=excluded.answers_json, submitted_at=excluded.submitted_at",
                (study_id, account_id, json.dumps(answers, ensure_ascii=False), _now()),
            )

    def surveys(self, study_id: str) -> dict[str, dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id, answers_json FROM study_survey WHERE study_id=?", (study_id,)
            ).fetchall()
        return {r["account_id"]: json.loads(r["answers_json"]) for r in rows}

    def has_survey(self, study_id: str, account_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM study_survey WHERE study_id=? AND account_id=?",
                (study_id, account_id),
            ).fetchone()
        return row is not None

    def erase_account(self, account_id: str) -> None:
        """Erasure (FR-35) takes the learner out of every study, past ones included."""
        with self._conn() as c:
            c.execute("DELETE FROM study_survey WHERE account_id=?", (account_id,))
            c.execute("DELETE FROM study_participant WHERE account_id=?", (account_id,))
