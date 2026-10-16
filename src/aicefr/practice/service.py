"""Application services for achievements, streaks and pronunciation evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from aicefr.practice.achievements import BY_CODE, CATALOG, nearest, reached, standings
from aicefr.practice.progress import summarize
from aicefr.pronunciation.vietnamese import Pattern, profile

MIN_COHORT_SPEAKERS = 5


def _status(value: Any) -> SimpleNamespace:
    return SimpleNamespace(value=str(value or "unmeasured").lower())


def _pronunciation_rows(rows: list[dict]) -> list[dict]:
    converted = []
    for row in rows:
        evidence = row["evidence"]
        raw_words = evidence.get("words")
        words = []
        override = row.get("teacher_override", {})
        override_words = override.get("words", {}) if isinstance(override, dict) else {}
        if isinstance(raw_words, list):
            for position, raw in enumerate(raw_words):
                if not isinstance(raw, dict):
                    continue
                expected = raw.get("text", raw.get("expected"))
                said = raw.get("said", raw.get("heard"))
                if not isinstance(expected, str) or (
                    said is not None and not isinstance(said, str)
                ):
                    continue
                index = raw.get("index", position)
                correction = override_words.get(str(index), override_words.get(index))
                if isinstance(correction, dict):
                    correction = correction.get("status")
                teacher = correction if correction in {"heard", "missed", "unsure"} else None
                if teacher is None:
                    raw_teacher = raw.get("teacher")
                    if isinstance(raw_teacher, dict):
                        raw_teacher = raw_teacher.get("status")
                    if raw_teacher in {"heard", "missed", "unsure"}:
                        teacher = raw_teacher
                if teacher is None and (
                    raw.get("teacher_corrected") or raw.get("corrected_by_teacher")
                ):
                    teacher = "heard"
                words.append(
                    SimpleNamespace(
                        text=expected,
                        said=said,
                        status=_status(raw.get("status")),
                        teacher=_status(teacher) if teacher else None,
                        start_s=raw.get("start_s")
                        if type(raw.get("start_s")) in {int, float}
                        else None,
                    )
                )
        measured = _number(row["measurements"].get("speaking_s")) > 0
        if evidence.get("measured") is False:
            measured = False
        result = SimpleNamespace(measured=measured, words=words, step_id=row["step_id"])
        converted.append(
            {
                "result": result,
                "lesson_id": row["lesson_id"],
                "attempt_id": row["attempt_id"],
                "created_at": row["created_at"],
            }
        )
    return converted


def _number(value: Any) -> float:
    return float(value) if type(value) in {int, float} and value > 0 else 0.0


class LearningService:
    def __init__(self, repository, *, clock=lambda: datetime.now(UTC)) -> None:
        self.repository = repository
        self.clock = clock

    def achievements(self, owner_id: str) -> dict:
        facts = self.repository.facts(owner_id)
        self.repository.unlock(owner_id, reached(facts), self.clock())
        unlocked = self.repository.unlocked(owner_id)
        progress = []
        by_code = {item.achievement.code: item for item in standings(facts)}
        for achievement in CATALOG:
            standing = by_code[achievement.code]
            unlocked_at, seen_at = unlocked.get(achievement.code, (None, None))
            progress.append(
                {
                    "code": achievement.code,
                    "group": achievement.group,
                    "title": achievement.title,
                    "description": achievement.description,
                    "icon": achievement.icon,
                    "target": achievement.target,
                    "unit": achievement.unit,
                    "value": standing.value,
                    "unlocked_at": unlocked_at,
                    "seen_at": seen_at,
                    "is_new": bool(unlocked_at and seen_at is None),
                }
            )
        next_item = nearest(facts, unlocked)
        return {
            "catalogue_version": "achievement-v1",
            "total": len(CATALOG),
            "unlocked": len(unlocked),
            "items": progress,
            "next": (
                {
                    "code": next_item.achievement.code,
                    "value": next_item.value,
                    "target": next_item.achievement.target,
                }
                if next_item
                else None
            ),
        }

    def mark_seen(self, owner_id: str, codes: list[str]) -> dict:
        if len(codes) > len(CATALOG) or len(set(codes)) != len(codes):
            raise ValueError("invalid achievement codes")
        if any(code not in BY_CODE for code in codes):
            raise ValueError("invalid achievement codes")
        return {"seen": self.repository.mark_seen(owner_id, codes, self.clock())}

    def progress(self, owner_id: str) -> dict:
        profile = self.repository.connection.execute(
            "SELECT goal FROM account_profiles WHERE account_id=?", (owner_id,)
        ).fetchone()
        goal_seconds = int(profile[0] or 3) * 60 if profile else 180
        return summarize(self.repository.efforts(owner_id), self.clock(), goal_seconds).as_dict()

    def pronunciation(self, owner_id: str) -> dict:
        return profile(_pronunciation_rows(self.repository.pronunciation_attempts(owner_id)))

    def pronunciation_example(self, owner_id: str, attempt_id: str) -> dict | None:
        row = self.repository.pronunciation_attempts(owner_id, attempt_id)
        if not row:
            return None
        return profile(_pronunciation_rows(row))

    def cohort_pronunciation(self) -> dict:
        students = self.repository.active_research_students()
        profiles = [
            profile(_pronunciation_rows(self.repository.pronunciation_attempts(owner_id)))
            for owner_id in students
        ]
        by_pattern: dict[str, dict[str, int]] = {
            item.value: {"speakers": 0, "opportunities": 0, "errors": 0} for item in Pattern
        }
        for item in profiles:
            for pattern in item["patterns"]:
                aggregate = by_pattern[pattern["pattern"]]
                if pattern["opportunities"]:
                    aggregate["speakers"] += 1
                    aggregate["opportunities"] += pattern["opportunities"]
                    aggregate["errors"] += pattern["errors"]
        patterns = []
        for pattern in Pattern:
            item = by_pattern[pattern.value]
            reportable = item["speakers"] >= MIN_COHORT_SPEAKERS
            enough = reportable and item["opportunities"] >= 8
            patterns.append(
                {
                    "pattern": pattern.value,
                    "name": self._pattern_name(pattern),
                    "speakers": item["speakers"] if reportable else None,
                    "opportunities": item["opportunities"] if reportable else None,
                    "errors": item["errors"] if reportable else None,
                    "enough": enough,
                    "rate": round(item["errors"] / item["opportunities"], 4) if enough else None,
                    "examples": [],
                }
            )
        return {
            "version": "vi-pron-v1",
            "minimum_speakers": MIN_COHORT_SPEAKERS,
            "participants": len(students) if len(students) >= MIN_COHORT_SPEAKERS else None,
            "patterns": patterns,
        }

    @staticmethod
    def _pattern_name(pattern: Pattern) -> str:
        from aicefr.pronunciation.vietnamese import PATTERN_NAMES

        return PATTERN_NAMES[pattern]
