"""Application orchestration for durable, purpose-aware practice attempts."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from aicefr.auth.service import ResourceNotFound
from aicefr.contracts import BlobRef
from aicefr.practice.bank import get_mission, list_missions
from aicefr.practice.contracts import PracticePurpose
from aicefr.practice.recommend import recommend_next
from aicefr.practice.runner import PracticeRunner


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
