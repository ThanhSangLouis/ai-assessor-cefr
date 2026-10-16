from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from aicefr.auth.errors import ResourceNotFound
from aicefr.contracts import BlobRef
from aicefr.practice.achievements import BY_CODE, CATALOG, nearest, reached, standings
from aicefr.practice.bank import get_mission, list_missions
from aicefr.practice.contracts import PracticePurpose
from aicefr.practice.progress import summarize
from aicefr.practice.recommend import recommend_next
from aicefr.practice.runner import PracticeRunner
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


def _now() -> datetime:
    return datetime.now(UTC)


class PracticeService:
    """Coordinates BlobStore, typed repository and an uns cored audio runner."""

    def __init__(
        self,
        repository: Any,
        blobs: Any,
        runner: PracticeRunner,
        *,
        evidence_provider: Any,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._repository = repository
        self._blobs = blobs
        self._runner = runner
        self._evidence = evidence_provider
        self._id_factory = id_factory
        self._clock = clock

    def catalogue(self) -> tuple[Any, ...]:
        return list_missions()

    def mission(self, mission_id: str):
        return get_mission(mission_id)

    def attempt(self, owner_id: str, attempt_id: str):
        return self._repository.get_practice_attempt(owner_id, attempt_id)

    def attempts(self, owner_id: str, *, limit: int = 20):
        return self._repository.list_practice_attempts(owner_id, limit=limit)

    def submit(
        self,
        owner_id: str,
        mission_id: str,
        data: bytes,
        extension: str,
        idempotency_key: str,
        *,
        prompt_version: str,
        purpose: PracticePurpose = PracticePurpose.PRACTICE,
        content_type: str | None = None,
        _mission_snapshot: Any | None = None,
        _review_item: Any | None = None,
    ):
        if not isinstance(prompt_version, str) or not prompt_version:
            raise ValueError("prompt_version is required")
        if purpose not in (PracticePurpose.PRACTICE, PracticePurpose.LEARNING):
            raise ValueError("unsupported learning purpose")
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
            raise ValueError("invalid idempotency key")
        blob = self._blobs.store(data)
        now = self._clock()
        existing = self._repository.get_practice_attempt_by_idempotency(
            owner_id, purpose, idempotency_key
        )
        mission = (
            existing.mission
            if existing is not None and existing.mission is not None
            else _mission_snapshot
        )
        if mission is None:
            try:
                mission = get_mission(mission_id)
            except KeyError:
                self._blobs.compensate(blob)
                raise ResourceNotFound("mission unavailable") from None
        if mission.mission_id != mission_id or mission.prompt_version != prompt_version:
            self._blobs.compensate(blob)
            if existing is not None:
                from aicefr.storage.learning import LearningConflict

                raise LearningConflict("idempotency key was reused for a different request")
            raise ValueError("mission version does not match the requested catalogue snapshot")
        try:
            record = self._repository.create_practice_attempt(
                owner_id,
                mission,
                purpose,
                idempotency_key,
                blob_id=blob.blob_id,
                sha256=blob.sha256,
                size_bytes=blob.size_bytes,
                audio_content_type=content_type or _MIME_BY_EXTENSION.get(extension, ""),
                prompt_version=prompt_version,
                review_source_kind=(_review_item.source_kind if _review_item is not None else None),
                review_source_attempt_id=(
                    _review_item.source_attempt_id if _review_item is not None else None
                ),
                review_content_key=_review_item.content_key if _review_item is not None else None,
                expected_review_revision=(
                    _review_item.revision if _review_item is not None else None
                ),
                review_box=_review_item.box if _review_item is not None else None,
                now=now,
            )
        except Exception:
            self._blobs.compensate(blob)
            raise
        # An idempotent replay returns the original artifact. Remove the newly
        # staged duplicate before running or returning that existing attempt.
        replay = record.audio is not None and record.audio.blob_id != blob.blob_id
        if replay:
            self._blobs.compensate(blob)
        if record.state.value != "QUEUED":
            return record
        if record.audio is None:
            raise RuntimeError("queued practice attempt is missing its immutable audio artifact")
        run_data = (
            self._blobs.read(
                BlobRef(
                    blob_id=record.audio.blob_id,
                    sha256=record.audio.sha256,
                    size_bytes=record.audio.size_bytes,
                )
            )
            if replay
            else data
        )
        run_extension = _extension_from_mime(record.audio.content_type)
        run = self._runner.run(
            record.mission,
            run_data,
            run_extension,
            attempt_id=record.attempt_id,
            purpose=record.purpose,
        )
        if run.result is not None:
            schedule = None
            source_id = None
            content_key = None
            source_revision = None
            source_kind = _review_item.source_kind if _review_item is not None else None
            if _review_item is not None and run.result.status.value in {"PASS", "FAIL"}:
                from aicefr.lessons.review import review_again

                schedule = review_again(
                    box=_review_item.box,
                    passed=run.result.status.value == "PASS",
                    reviewed_at=self._clock(),
                )
                source_id = _review_item.source_attempt_id
                content_key = _review_item.content_key
                source_revision = _review_item.revision
            elif purpose is PracticePurpose.PRACTICE and run.result.status.value in {
                "PASS",
                "FAIL",
            }:
                from aicefr.lessons.review import first_review

                schedule = first_review(due_from=self._clock())
                source_kind = "practice"
            return self._repository.complete_practice_attempt(
                owner_id,
                record.attempt_id,
                run.result,
                expected_revision=record.revision,
                now=self._clock(),
                review_source_kind=source_kind if schedule else None,
                review_source_attempt_id=source_id if schedule else None,
                review_content_key=(content_key or mission.mission_id) if schedule else None,
                review_schedule=schedule,
                expected_review_revision=source_revision,
            )
        from aicefr.storage.learning import LearningAttemptState

        return self._repository.complete_practice_attempt(
            owner_id,
            record.attempt_id,
            None,
            state=LearningAttemptState.NOT_EVALUATED,
            reasons=(run.reason or "PRACTICE_NOT_EVALUATED",),
            expected_revision=record.revision,
            now=self._clock(),
        )

    def delete_attempt(self, owner_id: str, attempt_id: str, *, expected_revision: int):
        return self._repository.delete_practice_attempt(
            owner_id, attempt_id, expected_revision=expected_revision, now=self._clock()
        )

    def submit_review(
        self,
        owner_id: str,
        review_id: str,
        data: bytes,
        extension: str,
        idempotency_key: str,
        *,
        content_type: str,
    ):
        existing = self._repository.get_practice_attempt_by_idempotency(
            owner_id, PracticePurpose.LEARNING, idempotency_key
        )
        if existing is not None:
            if existing.purpose is not PracticePurpose.LEARNING or existing.mission is None:
                raise ValueError("review replay is not a typed learning attempt")
            review = self._repository.get_review_item(owner_id, review_id)
            if review is None:
                return None
            if (
                review.source_kind != existing.review_source_kind
                or review.source_attempt_id != existing.review_source_attempt_id
                or review.content_key != existing.review_content_key
            ):
                from aicefr.storage.learning import LearningConflict

                raise LearningConflict("idempotency key belongs to a different review")
            binding = _saved_review_binding(existing)
            return self.submit(
                owner_id,
                existing.mission.mission_id,
                data,
                extension,
                idempotency_key,
                prompt_version=existing.mission.prompt_version,
                purpose=PracticePurpose.LEARNING,
                content_type=content_type,
                _mission_snapshot=existing.mission,
                _review_item=binding,
            )
        due = self._repository.get_due_review_item(owner_id, review_id, as_of=self._clock())
        if due is None or due.source_kind != "practice":
            return None
        source = self._repository.get_practice_attempt(owner_id, due.source_attempt_id)
        if source is None or source.mission is None or source.result is None:
            return None
        return self.submit(
            owner_id,
            source.mission.mission_id,
            data,
            extension,
            idempotency_key,
            prompt_version=source.mission.prompt_version,
            purpose=PracticePurpose.LEARNING,
            content_type=content_type,
            _mission_snapshot=source.mission,
            _review_item=due,
        )

    def review_replay(self, owner_id: str, idempotency_key: str):
        return self._repository.get_practice_attempt_by_idempotency(
            owner_id, PracticePurpose.LEARNING, idempotency_key
        )

    def recommendation(self, owner_id: str):
        assessments = self._evidence.list_assessment_evidence(owner_id, limit=20)
        attempts = self._repository.list_practice_attempts(owner_id, limit=100)
        completed = {
            item.mission.mission_id
            for item in attempts
            if item.state.value == "COMPLETED"
            and item.result is not None
            and item.mission is not None
        }
        return recommend_next(assessments=assessments, completed_mission_ids=completed)

    def evidence_digest(self, data: bytes) -> str:
        """Stable helper for audit adapters; audio bytes never enter reports."""
        return hashlib.sha256(data).hexdigest()


_MIME_BY_EXTENSION = {
    "wav": "audio/wav",
    "flac": "audio/flac",
    "ogg": "audio/ogg",
    "mp3": "audio/mpeg",
    "webm": "audio/webm",
    "mp4": "audio/mp4",
}


def _extension_from_mime(content_type: str) -> str:
    for extension, mime in _MIME_BY_EXTENSION.items():
        if content_type == mime:
            return extension
    raise ValueError("stored audio type is unsupported")


def _saved_review_binding(record: Any) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        source_kind=record.review_source_kind,
        source_attempt_id=record.review_source_attempt_id,
        content_key=record.review_content_key,
        revision=record.expected_review_revision,
        box=record.review_box,
    )
