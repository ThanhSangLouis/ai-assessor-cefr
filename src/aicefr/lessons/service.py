"""Repository-backed lesson reading and audio step-attempt orchestration."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from aicefr.auth.service import ResourceNotFound
from aicefr.contracts import BlobRef
from aicefr.lessons.lint import lint_lesson
from aicefr.lessons.model import (
    LearningPath,
    LearningUnit,
    Lesson,
    StepKind,
)
from aicefr.lessons.progress import lesson_completion


def _now() -> datetime:
    return datetime.now(UTC)


class LessonService:
    def __init__(
        self,
        repository: Any,
        blobs: Any,
        runner: Any,
        *,
        qc_config: Any | None = None,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._repository = repository
        self._blobs = blobs
        self._runner = runner
        self._qc_config = qc_config
        self._id_factory = id_factory
        self._clock = clock

    def paths(self):
        return self._repository.list_paths(published_only=True)

    def path_by_id(self, path_id: str, *, published_only: bool = True):
        return self._repository.get_path(path_id, published_only=published_only)

    def path_revision(self, path_id: str) -> int | None:
        return self._repository.path_revision(path_id)

    def unit_revision(self, unit_id: str) -> int | None:
        return self._repository.unit_revision(unit_id)

    def save_path(self, actor_id: str, path: LearningPath, *, expected_revision: int):
        return self._resource_call(
            self._repository.save_draft_path,
            actor_id,
            path,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def import_path(self, actor_id: str, data: bytes):
        from aicefr.lessons.authoring import import_path

        imported = import_path(data, id_factory=lambda kind: f"{kind}-{self._id_factory()}")
        return self._resource_call(
            self._repository.import_draft_path_bundle,
            actor_id,
            imported,
            expected_revision=0,
            now=self._clock(),
        )

    def export_path(self, path_id: str, *, published_only: bool = False) -> bytes:
        from aicefr.lessons.authoring import export_path

        bundle = self._repository.export_path_bundle(path_id, published_only=published_only)
        if bundle is None:
            raise ResourceNotFound("learning path unavailable")
        return export_path(bundle)

    def save_unit(self, actor_id: str, path_id: str, unit: LearningUnit, *, expected_revision: int):
        return self._resource_call(
            self._repository.save_draft_unit,
            actor_id,
            path_id,
            unit,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def delete_path(self, actor_id: str, path_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.delete_draft_path,
            actor_id,
            path_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def publish_path(self, actor_id: str, path_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.publish_path,
            actor_id,
            path_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def delete_unit(self, actor_id: str, path_id: str, unit_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.delete_draft_unit,
            actor_id,
            path_id,
            unit_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def delete_lesson(self, actor_id: str, lesson_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.delete_draft_lesson,
            actor_id,
            lesson_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def delete_step(self, actor_id: str, lesson_id: str, step_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.delete_draft_step,
            actor_id,
            lesson_id,
            step_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def reorder_steps(
        self,
        actor_id: str,
        lesson_id: str,
        ordered_step_ids: Sequence[str],
        *,
        expected_revision: int,
    ):
        return self._resource_call(
            self._repository.reorder_draft_steps,
            actor_id,
            lesson_id,
            tuple(ordered_step_ids),
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def import_lesson(self, actor_id: str, unit_id: str, data: bytes, *, expected_revision: int):
        from aicefr.lessons.authoring import import_lesson

        lesson = import_lesson(data, lesson_id=self._id_factory())
        return self.save_draft(actor_id, unit_id, lesson, expected_revision=expected_revision)

    @staticmethod
    def export_lesson(lesson: Any) -> bytes:
        from aicefr.lessons.authoring import export_lesson

        return export_lesson(lesson)

    def path(self):
        paths = self.paths()
        return paths[0] if paths else None

    def lesson(self, lesson_id: str, version: int | None = None):
        return self._repository.get_lesson(lesson_id, version=version, published_only=True)

    def draft(self, lesson_id: str):
        return self._repository.get_lesson(lesson_id, published_only=False)

    def draft_record(self, lesson_id: str):
        return self._repository.get_draft_lesson(lesson_id)

    def save_draft(self, actor_id: str, unit_id: str, lesson: Lesson, *, expected_revision: int):
        return self._resource_call(
            self._repository.save_draft_lesson,
            actor_id,
            unit_id,
            lesson,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def publish(self, actor_id: str, lesson_id: str, *, expected_revision: int):
        return self._resource_call(
            self._repository.publish_lesson,
            actor_id,
            lesson_id,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def reorder(
        self, actor_id: str, path_id: str, unit_ids: Sequence[str], *, expected_revision: int
    ):
        return self._resource_call(
            self._repository.reorder_units,
            actor_id,
            path_id,
            unit_ids,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    @staticmethod
    def _resource_call(operation: Callable[..., Any], *args: Any, **kwargs: Any):
        """Translate the repository's documented missing-row KeyError at resource boundaries."""
        try:
            return operation(*args, **kwargs)
        except KeyError:
            raise ResourceNotFound("learning resource unavailable") from None

    @staticmethod
    def lint(lesson: Lesson, *, for_publish: bool = False):
        return lint_lesson(lesson, for_publish=for_publish)

    def upload_media(
        self,
        actor_id: str,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        data: bytes,
        extension: str,
        content_type: str,
        *,
        media_kind: str = "sample_audio",
    ):
        from aicefr.audio.decoder import decode_and_measure

        if self._qc_config is None:
            raise RuntimeError("audio media validation is unavailable")
        lesson = self._repository.get_lesson(
            lesson_id, version=lesson_version, published_only=False
        )
        if lesson is None or not any(step.step_id == step_id for step in lesson.steps):
            return None
        decoded = decode_and_measure(data, extension, self._qc_config)
        if decoded.audio is None:
            raise ValueError("sample audio failed bounded decoding")
        blob = self._blobs.store(data)
        try:
            return self._resource_call(
                self._repository.create_lesson_media,
                actor_id,
                lesson_id=lesson_id,
                lesson_version=lesson_version,
                step_id=step_id,
                media_kind=media_kind,
                blob_id=blob.blob_id,
                content_type=content_type,
                sha256=blob.sha256,
                size_bytes=blob.size_bytes,
                now=self._clock(),
            )
        except Exception:
            self._blobs.compensate(blob)
            raise

    def media(
        self,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        *,
        include_draft: bool = False,
        actor_id: str | None = None,
    ):
        return self._repository.get_lesson_media(
            lesson_id,
            lesson_version,
            step_id,
            include_draft=include_draft,
            actor_id=actor_id,
        )

    def read_media(self, artifact: Any) -> bytes:
        from aicefr.contracts import BlobRef

        return self._blobs.read(
            BlobRef(
                blob_id=artifact.blob_id, sha256=artifact.sha256, size_bytes=artifact.size_bytes
            )
        )

    def public_media(
        self,
        lesson: Any,
        *,
        include_draft: bool = False,
        actor_id: str | None = None,
        lesson_version: int | None = None,
    ) -> list[dict[str, Any]]:
        version = lesson_version if lesson_version is not None else getattr(lesson, "version", None)
        if version is None:
            return []
        result = []
        for step in lesson.steps:
            rows = self.media(
                lesson.lesson_id,
                version,
                step.step_id,
                include_draft=include_draft,
                actor_id=actor_id,
            )
            result.extend(
                {
                    "media_id": row.media_id,
                    "lesson_id": row.lesson_id,
                    "lesson_version": row.lesson_version,
                    "step_id": row.step_id,
                    "media_kind": row.media_kind,
                    "content_type": row.content_type,
                    "sha256": row.sha256,
                    "size_bytes": row.size_bytes,
                    "url": (
                        f"/api/v1/teacher/learn/lessons/{row.lesson_id}/versions/"
                        f"{row.lesson_version}/steps/{row.step_id}/media/{row.media_id}"
                        if include_draft
                        else f"/api/v1/learn/lessons/{row.lesson_id}/versions/"
                        f"{row.lesson_version}/steps/{row.step_id}/media/{row.media_id}"
                    ),
                }
                for row in rows
            )
        return result

    def due_reviews(self, owner_id: str, *, limit: int = 50):
        return self._repository.list_due_reviews(owner_id, as_of=self._clock(), limit=limit)

    def learning_insights(self, owner_id: str, *, limit: int = 100):
        return self._repository.get_learning_insights(owner_id, as_of=self._clock(), limit=limit)

    def override_attempt(
        self,
        actor_id: str,
        owner_id: str,
        attempt_id: str,
        *,
        new_value: str,
        reason: str,
        expected_revision: int,
    ):
        return self._resource_call(
            self._repository.append_step_override,
            actor_id,
            owner_id,
            attempt_id,
            new_value=new_value,
            reason=reason,
            expected_revision=expected_revision,
            now=self._clock(),
        )

    def attempt(self, owner_id: str, attempt_id: str):
        return self._repository.get_step_attempt(owner_id, attempt_id)

    def attempts(self, owner_id: str, *, lesson_id: str | None = None, limit: int = 50):
        return self._repository.list_step_attempts(owner_id, lesson_id=lesson_id, limit=limit)

    def review_replay(self, owner_id: str, idempotency_key: str):
        return self._repository.get_step_attempt_by_idempotency(owner_id, idempotency_key)

    def delete_attempt(self, owner_id: str, attempt_id: str, *, expected_revision: int):
        return self._repository.delete_step_attempt(
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
        existing = self._repository.get_step_attempt_by_idempotency(owner_id, idempotency_key)
        if existing is not None:
            if not existing.review_source_attempt_id or not existing.review_content_key:
                raise ValueError("review replay is not bound to a source review")
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
            return self.submit_step(
                owner_id,
                existing.lesson_id,
                existing.lesson_version,
                existing.step_id,
                data,
                extension,
                idempotency_key,
                round_index=existing.round_index,
                content_type=content_type,
                _review_item=binding,
            )
        due = self._repository.get_due_review_item(owner_id, review_id, as_of=self._clock())
        if due is None or due.source_kind != "step":
            return None
        source = self._repository.get_step_attempt(owner_id, due.source_attempt_id)
        if source is None or source.result is None:
            return None
        return self.submit_step(
            owner_id,
            source.lesson_id,
            source.lesson_version,
            source.step_id,
            data,
            extension,
            idempotency_key,
            round_index=source.round_index,
            content_type=content_type,
            _review_item=due,
        )

    def submit_step(
        self,
        owner_id: str,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        data: bytes,
        extension: str,
        idempotency_key: str,
        *,
        round_index: int | None = None,
        content_type: str | None = None,
        _review_item: Any | None = None,
    ):
        if (
            isinstance(lesson_version, bool)
            or not isinstance(lesson_version, int)
            or lesson_version < 1
        ):
            raise ValueError("lesson_version is invalid")
        lesson = self._repository.get_lesson(lesson_id, version=lesson_version, published_only=True)
        if lesson is None:
            return None
        step = next((item for item in lesson.steps if item.step_id == step_id), None)
        if step is None:
            return None
        if step.kind is StepKind.FREE:
            rounds = getattr(step.payload, "rounds", ())
            if (
                isinstance(round_index, bool)
                or not isinstance(round_index, int)
                or not 0 <= round_index < len(rounds)
            ):
                raise ValueError("free step requires a valid round index")
        elif round_index is not None:
            raise ValueError("only free steps accept a round index")
        blob = self._blobs.store(data)
        now = self._clock()
        try:
            record = self._repository.create_step_attempt(
                owner_id,
                lesson_id=lesson.lesson_id,
                lesson_version=lesson.version,
                step_id=step.step_id,
                rules_version=step.rules_version,
                idempotency_key=idempotency_key,
                blob_id=blob.blob_id,
                sha256=blob.sha256,
                size_bytes=blob.size_bytes,
                audio_content_type=content_type or _MIME_BY_EXTENSION.get(extension, ""),
                round_index=round_index,
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
        replay = record.audio is not None and record.audio.blob_id != blob.blob_id
        if replay:
            self._blobs.compensate(blob)
        if record.state.value != "QUEUED":
            return record
        if record.audio is None:
            raise RuntimeError("queued step attempt is missing its immutable audio artifact")
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
        saved_lesson = self._repository.get_lesson(
            record.lesson_id, version=record.lesson_version, published_only=False
        )
        if saved_lesson is None:
            raise RuntimeError("queued step attempt has no immutable lesson snapshot")
        step = next((item for item in saved_lesson.steps if item.step_id == record.step_id), None)
        if step is None:
            raise RuntimeError("queued step attempt has no immutable step snapshot")
        run = self._runner.run_step(
            step,
            run_data,
            run_extension,
            attempt_id=record.attempt_id,
            round_index=record.round_index,
        )
        from aicefr.storage.learning import LearningAttemptState

        result = run.result
        if result is None:
            return self._repository.complete_step_attempt(
                owner_id,
                record.attempt_id,
                None,
                state=LearningAttemptState.NOT_EVALUATED,
                reasons=(run.reason or "STEP_NOT_EVALUATED",),
                expected_revision=record.revision,
                now=self._clock(),
            )
        schedule = None
        source_id = None
        content_key = None
        source_revision = None
        source_kind = _review_item.source_kind if _review_item is not None else None
        if _review_item is not None and result.status.value in {"PASS", "FAIL"}:
            from aicefr.lessons.review import review_again

            schedule = review_again(
                box=_review_item.box,
                passed=result.status.value == "PASS",
                reviewed_at=self._clock(),
            )
            source_id = _review_item.source_attempt_id
            content_key = _review_item.content_key
            source_revision = _review_item.revision
        elif result.status.value in {"PASS", "FAIL"}:
            from aicefr.lessons.review import first_review

            schedule = first_review(due_from=self._clock())
            source_kind = "step"
        if result.status.value in {"PASS", "FAIL"}:
            content_key = content_key or (
                f"{record.lesson_id}:{record.lesson_version}:{record.step_id}:{record.round_index}"
            )
        return self._repository.complete_step_attempt(
            owner_id,
            record.attempt_id,
            result,
            expected_revision=record.revision,
            now=self._clock(),
            review_source_kind=source_kind if schedule else None,
            review_source_attempt_id=source_id if schedule else None,
            review_content_key=content_key if schedule else None,
            review_schedule=schedule,
            expected_review_revision=source_revision,
        )

    def progress(self, owner_id: str, lesson_id: str, version: int | None = None):
        lesson = self.lesson(lesson_id, version)
        if lesson is None:
            return None
        completions = self._repository.list_lesson_progress_completions(
            owner_id, lesson_id, lesson.version
        )
        return lesson_completion(steps=lesson.steps, attempts=completions)


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
