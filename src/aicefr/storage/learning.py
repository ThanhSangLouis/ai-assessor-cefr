"""SQLite persistence for personal learning progress and pronunciation evidence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from aicefr.practice.achievements import Facts, Take, count
from aicefr.practice.progress import Effort


def _object(value: str | None) -> dict[str, Any]:
    try:
        result = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return result if isinstance(result, dict) else {}


def _number(value: Any) -> float:
    if type(value) not in {int, float}:
        return 0.0
    return max(0.0, float(value))


class LearningRepository:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection

    def attempts(self, owner_id: str) -> list[Take]:
        rows = self.connection.execute(
            "SELECT lesson_id,lesson_version,step_id,status,measurements,evidence,"
            "teacher_override,created_at "
            "FROM step_attempts WHERE owner_id=? ORDER BY julianday(created_at),attempt_id",
            (owner_id,),
        ).fetchall()
        result: list[Take] = []
        for (
            lesson_id,
            lesson_version,
            step_id,
            status,
            raw_measurements,
            raw_evidence,
            raw_override,
            created_at,
        ) in rows:
            measurements, evidence = _object(raw_measurements), _object(raw_evidence)
            override = _object(raw_override)
            seconds = _number(measurements.get("speaking_s"))
            if evidence.get("measured") is False:
                seconds = 0.0
            step = self.connection.execute(
                "SELECT kind,payload FROM lesson_steps WHERE lesson_id=? "
                "AND version=? AND step_id=?",
                (lesson_id, lesson_version, step_id),
            ).fetchone()
            kind = str(step[0]).lower() if step else ""
            payload = _object(step[1]) if step else {}
            is_free = bool(evidence.get("free") or payload.get("free")) or kind in {
                "free",
                "free_speaking",
                "free_multi_round",
            }
            result.append(
                Take(
                    lesson_id=str(lesson_id),
                    step_id=str(step_id),
                    created_at=str(created_at),
                    speaking_s=seconds,
                    passed=bool(override["passed"])
                    if type(override.get("passed")) is bool
                    else str(status).upper() in {"PASS", "PASSED", "COMPLETED"},
                    free=is_free,
                    review=bool(evidence.get("review")),
                )
            )

        missions = self.connection.execute(
            "SELECT mission_id,status,measurements,evidence,created_at FROM practice_attempts "
            "WHERE owner_id=? ORDER BY julianday(created_at),attempt_id",
            (owner_id,),
        ).fetchall()
        for mission_id, _status, raw_measurements, raw_evidence, created_at in missions:
            measurements, evidence = _object(raw_measurements), _object(raw_evidence)
            seconds = _number(measurements.get("speaking_s"))
            if evidence.get("measured") is False:
                seconds = 0.0
            result.append(
                Take(
                    lesson_id=f"mission:{mission_id}",
                    step_id="mission",
                    created_at=str(created_at),
                    speaking_s=seconds,
                    passed=False,
                    free=bool(evidence.get("free")),
                    review=bool(evidence.get("review")),
                )
            )
        return sorted(result, key=lambda item: item.created_at)

    def efforts(self, owner_id: str) -> list[Effort]:
        return [Effort(item.created_at, item.speaking_s) for item in self.attempts(owner_id)]

    def facts(self, owner_id: str) -> Facts:
        attempts = self.attempts(owner_id)
        profile = self.connection.execute(
            "SELECT goal FROM account_profiles WHERE account_id=?", (owner_id,)
        ).fetchone()
        goal_seconds = int(profile[0] or 3) * 60 if profile else 180
        completions = self.connection.execute(
            "SELECT lesson_id,evidence FROM step_attempts WHERE owner_id=?", (owner_id,)
        ).fetchall()
        lesson_ids: set[str] = set()
        unit_ids: set[str] = set()
        for lesson_id, raw_evidence in completions:
            evidence = _object(raw_evidence)
            if evidence.get("lesson_completed") is True:
                lesson_ids.add(str(lesson_id))
            if evidence.get("unit_completed") is True and isinstance(evidence.get("unit_id"), str):
                unit_ids.add(evidence["unit_id"])
        assessment_count = self.connection.execute(
            "SELECT COUNT(*) FROM responses r JOIN diagnostic_reports d "
            "ON d.response_id=r.response_id WHERE r.owner_id=? AND r.status='COMPLETED'",
            (owner_id,),
        ).fetchone()[0]
        facts = count(
            attempts,
            goal_seconds=goal_seconds,
            lessons_completed=len(lesson_ids),
            units_completed=len(unit_ids),
            assessments=int(assessment_count),
        )
        self._refresh_streak_days(owner_id, attempts)
        return facts

    def _refresh_streak_days(self, owner_id: str, attempts: list[Take]) -> None:
        from aicefr.practice.streak import local_day

        totals: dict[str, int] = {}
        for item in attempts:
            if item.speaking_s > 0:
                day = local_day(item.created_at).isoformat()
                totals[day] = totals.get(day, 0) + 1
        with self.store.transaction() as connection:
            connection.execute("DELETE FROM streak_days WHERE owner_id=?", (owner_id,))
            connection.executemany(
                "INSERT INTO streak_days(owner_id,local_date,effort_count) VALUES(?,?,?)",
                [(owner_id, day, amount) for day, amount in sorted(totals.items())],
            )

    def unlock(self, owner_id: str, codes: set[str], unlocked_at: datetime) -> None:
        if not codes:
            return
        with self.store.transaction() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO achievements(owner_id,code,unlocked_at) VALUES(?,?,?)",
                [(owner_id, code, unlocked_at.isoformat()) for code in sorted(codes)],
            )

    def unlocked(self, owner_id: str) -> dict[str, tuple[str, str | None]]:
        rows = self.connection.execute(
            "SELECT code,unlocked_at,seen_at FROM achievements WHERE owner_id=? ORDER BY code",
            (owner_id,),
        ).fetchall()
        return {str(code): (str(unlocked_at), seen_at) for code, unlocked_at, seen_at in rows}

    def mark_seen(self, owner_id: str, codes: list[str], seen_at: datetime) -> int:
        if not codes:
            return 0
        with self.store.transaction() as connection:
            changed = 0
            for code in codes:
                changed += connection.execute(
                    "UPDATE achievements SET seen_at=? "
                    "WHERE owner_id=? AND code=? AND seen_at IS NULL",
                    (seen_at.isoformat(), owner_id, code),
                ).rowcount
            return changed

    def pronunciation_attempts(self, owner_id: str, attempt_id: str | None = None) -> list[dict]:
        statement = (
            "SELECT attempt_id,lesson_id,lesson_version,step_id,measurements,evidence,"
            "teacher_override,created_at "
            "FROM step_attempts WHERE owner_id=?"
        )
        values: tuple[Any, ...] = (owner_id,)
        if attempt_id is not None:
            statement += " AND attempt_id=?"
            values += (attempt_id,)
        statement += " ORDER BY julianday(created_at),attempt_id"
        rows = self.connection.execute(statement, values).fetchall()
        return [
            {
                "attempt_id": str(row[0]),
                "lesson_id": str(row[1]),
                "lesson_version": int(row[2]),
                "step_id": str(row[3]),
                "measurements": _object(row[4]),
                "evidence": _object(row[5]),
                "teacher_override": _object(row[6]),
                "created_at": str(row[7]),
            }
            for row in rows
        ]

    def active_research_students(self) -> list[str]:
        return [
            str(row[0])
            for row in self.connection.execute(
                "SELECT a.actor_id FROM accounts a JOIN consents c "
                "ON c.participant_id=a.actor_id WHERE a.role='student' AND a.disabled=0 "
                "AND c.state='active' AND c.research_allowed=1 ORDER BY a.actor_id"
            )
        ]
