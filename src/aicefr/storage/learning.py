"""SQLite-backed learning persistence and read-only assessment projections.

`list_assessment_evidence` is an owner-scoped projection of durable reports,
not a second scoring path. It returns only recent reports with an eligible
assessment status and an actual overall score and band.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from aicefr.contracts import ActorRole, Band
from aicefr.lessons.model import (
    MAX_STEP_SPEAKING_SECONDS,
    LearningPath,
    LearningUnit,
    Lesson,
    LessonStep,
    PublishedLessonVersion,
    StepAttemptStatus,
    StepCompletion,
    StepKind,
    StepResult,
    StepResultStatus,
)
from aicefr.lessons.review import ReviewSchedule
from aicefr.practice.contracts import (
    PracticeMission,
    PracticePurpose,
    PracticeResult,
    RecommendationEvidence,
)
from aicefr.report.contracts import DiagnosticReport
from aicefr.storage.sqlite import SQLiteStore

MAX_ASSESSMENT_EVIDENCE = 100
MAX_ATTEMPT_LIST = 100
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_JSON_MAX_BYTES = 256_000


class LearningAttemptState(StrEnum):
    QUEUED = "QUEUED"
    COMPLETED = "COMPLETED"
    NOT_EVALUATED = "NOT_EVALUATED"
    LEGACY = "LEGACY"


class LearningConflict(RuntimeError):
    """A learning record changed or already completed with another payload."""


@dataclass(frozen=True)
class LearningAudioArtifact:
    artifact_id: str
    owner_id: str
    attempt_kind: str
    attempt_id: str
    blob_id: str
    content_type: str
    sha256: str
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True)
class LearningMediaArtifact:
    media_id: str
    lesson_id: str
    lesson_version: int
    step_id: str
    media_kind: str
    blob_id: str
    content_type: str
    sha256: str
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True)
class PracticeAttemptRecord:
    attempt_id: str
    owner_id: str
    purpose: PracticePurpose
    mission: PracticeMission | None
    state: LearningAttemptState
    result: PracticeResult | None
    reasons: tuple[str, ...]
    audio: LearningAudioArtifact | None
    revision: int
    created_at: datetime
    updated_at: datetime
    review_source_kind: str | None = None
    review_source_attempt_id: str | None = None
    review_content_key: str | None = None
    expected_review_revision: int | None = None
    review_box: int | None = None


@dataclass(frozen=True)
class StepAttemptRecord:
    attempt_id: str
    owner_id: str
    lesson_id: str
    lesson_version: int
    step_id: str
    rules_version: str
    state: LearningAttemptState
    result: StepResult | None
    reasons: tuple[str, ...]
    audio: LearningAudioArtifact | None
    revision: int
    round_index: int | None
    teacher_override: str | None
    created_at: datetime
    updated_at: datetime
    review_source_kind: str | None = None
    review_source_attempt_id: str | None = None
    review_content_key: str | None = None
    expected_review_revision: int | None = None
    review_box: int | None = None


@dataclass(frozen=True)
class ReviewItemRecord:
    review_id: str
    owner_id: str
    source_attempt_id: str
    content_key: str
    box: int
    due_at: datetime | None
    done: bool
    updated_at: datetime
    source_kind: str = "practice"
    revision: int = 0


@dataclass(frozen=True)
class TeacherOverrideEvent:
    event_id: str
    attempt_id: str
    owner_id: str
    actor_id: str
    old_value: str | None
    new_value: str
    reason: str
    recorded_at: datetime


@dataclass(frozen=True)
class LearningInsightsRecord:
    owner_id: str
    practice_completed: int
    practice_not_evaluated: int
    step_completed: int
    step_not_evaluated: int
    audio_artifacts: int
    due_reviews: int
    as_of: datetime


@dataclass(frozen=True)
class DraftLessonRecord:
    lesson: Lesson
    version: int


class LegacyPublishedLessonVersion(BaseModel):
    """Explicit projection for pre-v11 published versions lacking snapshot metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lesson_id: str
    version: int
    revision: int
    title: str
    summary: str | None
    band: Band | None
    rules_version: str
    published_at: datetime | None
    content_hash: str | None
    steps: tuple[LessonStep | dict[str, object], ...]
    legacy: bool = True
    provenance: str = "parent_lesson_title_and_preserved_legacy_steps"


_Model = TypeVar("_Model")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("learning timestamps must be timezone-aware")
    return value.isoformat()


def _parse_timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("stored learning timestamp must be timezone-aware")
    return result


def _dump_json(value: object) -> str:
    if hasattr(value, "model_dump_json"):
        payload = value.model_dump_json()
    else:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > _JSON_MAX_BYTES:
        raise ValueError("learning payload exceeds the storage limit")
    return payload


def _decode_json(payload: str | None, model: type[_Model]) -> _Model | None:
    if payload is None:
        return None
    if len(payload.encode("utf-8")) > _JSON_MAX_BYTES:
        raise ValueError("stored learning payload exceeds the storage limit")
    return model.model_validate_json(payload)  # type: ignore[attr-defined,no-any-return]


def _bounded_reasons(reasons: tuple[str, ...]) -> tuple[str, ...]:
    if len(reasons) > 8 or any(
        not isinstance(reason, str)
        or not reason
        or len(reason) > 80
        or not re.fullmatch(r"[A-Z0-9_]+", reason)
        for reason in reasons
    ):
        raise ValueError("learning reasons must be bounded stable reason codes")
    return reasons


class LearningRepository:
    """Learning-specific persistence adapter over the injected metadata store."""

    def __init__(self, store: SQLiteStore, *, id_factory=uuid.uuid4) -> None:
        self._store = store
        self._id_factory = id_factory

    def seed_sample_catalogue(
        self,
        path: LearningPath,
        units: tuple[LearningUnit, ...],
        lessons: tuple[tuple[str, Lesson], ...],
        *,
        layout: int,
        seed_version: str,
        now: datetime,
    ) -> str:
        """Insert sample rows without replacing an existing teacher-owned row."""
        if layout < 1 or not seed_version or len(seed_version) > 40:
            raise ValueError("sample seed version and layout must be bounded")
        if any(unit.path_id != path.path_id for unit in units):
            raise ValueError("sample units must belong to the sample path")
        if len({unit.unit_id for unit in units}) != len(units):
            raise ValueError("sample unit ids must be unique")
        lesson_ids = {lesson.lesson_id for _, lesson in lessons}
        if len(lesson_ids) != len(lessons):
            raise ValueError("sample lesson ids must be unique")
        manifest = {
            "path": path.model_dump(mode="json"),
            "units": [unit.model_dump(mode="json") for unit in units],
            "lessons": [lesson.model_dump(mode="json") for _, lesson in lessons],
            "layout": layout,
            "seed_version": seed_version,
        }
        manifest_json = json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
        stamp = _timestamp(now)
        lesson_ordinals: dict[str, int] = {}
        per_unit: dict[str, int] = {}
        for unit_id, lesson in lessons:
            per_unit[unit_id] = per_unit.get(unit_id, 0) + 1
            lesson_ordinals[lesson.lesson_id] = per_unit[unit_id]
        outcome = {"inserted": 0, "updated": 0, "skipped": 0}
        with self._store.transaction() as connection:
            prior_manifest = connection.execute(
                "SELECT seed_version,manifest_sha256,layout,result_json "
                "FROM learning_seed_manifest "
                "WHERE seed_name=?",
                (path.path_id,),
            ).fetchone()
            if (
                prior_manifest
                and prior_manifest[1] == manifest_hash
                and prior_manifest[2] == layout
            ):
                return manifest_hash
            path_hash = hashlib.sha256(_dump_json(path).encode("utf-8")).hexdigest()
            existing_path = connection.execute(
                "SELECT seed_owned,seed_hash,content_hash FROM learning_paths WHERE path_id=?",
                (path.path_id,),
            ).fetchone()
            if existing_path is None:
                connection.execute(
                    """INSERT INTO learning_paths(
                        path_id,title,description,state,revision,created_at,updated_at,seed_version,
                        seed_hash,seed_owned,content_hash,band_from,band_to,content_version
                    ) VALUES(?,?,?,'published',1,?,?,?,?,1,?,?,?,?)""",
                    (
                        path.path_id,
                        path.title,
                        path.description,
                        stamp,
                        stamp,
                        seed_version,
                        path_hash,
                        path_hash,
                        path.band_from.value,
                        path.band_to.value,
                        path.content_version,
                    ),
                )
                outcome["inserted"] += 1
            elif existing_path[0] == 1 and existing_path[1] == existing_path[2]:
                connection.execute(
                    """UPDATE learning_paths SET title=?,description=?,band_from=?,band_to=?,
                       content_version=?,seed_version=?,seed_hash=?,content_hash=?,
                       revision=revision+1,
                       updated_at=? WHERE path_id=? AND seed_owned=1 AND content_hash=seed_hash""",
                    (
                        path.title,
                        path.description,
                        path.band_from.value,
                        path.band_to.value,
                        path.content_version,
                        seed_version,
                        path_hash,
                        path_hash,
                        stamp,
                        path.path_id,
                    ),
                )
                outcome["updated"] += 1
            else:
                outcome["skipped"] += 1
            for unit in units:
                unit_json = _dump_json(unit)
                unit_hash = hashlib.sha256(unit_json.encode("utf-8")).hexdigest()
                exists = connection.execute(
                    "SELECT path_id,seed_owned,seed_hash,content_hash "
                    "FROM learning_units WHERE unit_id=?",
                    (unit.unit_id,),
                ).fetchone()
                if exists:
                    if exists[0] == path.path_id and exists[1] == 1 and exists[2] == exists[3]:
                        connection.execute(
                            """UPDATE learning_units SET title=?,ordinal=?,band=?,topic=?,
                               learning_function=?,revision=revision+1,seed_version=?,seed_hash=?,
                               content_hash=? WHERE unit_id=? AND path_id=? AND seed_owned=1
                               AND content_hash=seed_hash""",
                            (
                                unit.title,
                                unit.ordinal,
                                unit.band.value,
                                unit.topic.value if unit.topic else None,
                                unit.learning_function,
                                seed_version,
                                unit_hash,
                                unit_hash,
                                unit.unit_id,
                                path.path_id,
                            ),
                        )
                        outcome["updated"] += 1
                    else:
                        outcome["skipped"] += 1
                    continue
                connection.execute(
                    """INSERT INTO learning_units(
                        unit_id,path_id,title,ordinal,band,topic,learning_function,revision,
                        seed_version,seed_hash,seed_owned,content_hash
                    ) VALUES(?,?,?,?,?,?,?,1,?,?,1,?)""",
                    (
                        unit.unit_id,
                        path.path_id,
                        unit.title,
                        unit.ordinal,
                        unit.band.value,
                        unit.topic.value if unit.topic else None,
                        unit.learning_function,
                        seed_version,
                        unit_hash,
                        unit_hash,
                    ),
                )
                outcome["inserted"] += 1
            for unit_id, lesson in lessons:
                if unit_id not in {unit.unit_id for unit in units}:
                    raise ValueError("sample lesson references an unknown unit")
                lesson_json = _dump_json(lesson)
                lesson_hash = hashlib.sha256(lesson_json.encode("utf-8")).hexdigest()
                exists = connection.execute(
                    """SELECT unit_id,seed_owned,seed_hash,content_hash,revision
                       FROM learning_lessons WHERE lesson_id=?""",
                    (lesson.lesson_id,),
                ).fetchone()
                if exists:
                    if exists[0] == unit_id and exists[1] == 1 and exists[2] == exists[3]:
                        if exists[3] != lesson_hash:
                            updated_lesson = lesson.model_copy(update={"revision": exists[4] + 1})
                            updated_hash = hashlib.sha256(
                                _dump_json(updated_lesson).encode("utf-8")
                            ).hexdigest()
                            connection.execute(
                                """UPDATE learning_lessons SET title=?,summary=?,band=?,revision=?,
                                   seed_version=?,seed_hash=?,content_hash=?,content_version=?,
                                   ordinal=?
                                   WHERE lesson_id=? AND seed_owned=1 AND content_hash=seed_hash""",
                                (
                                    updated_lesson.title,
                                    updated_lesson.summary,
                                    updated_lesson.band.value,
                                    updated_lesson.revision,
                                    seed_version,
                                    updated_hash,
                                    updated_hash,
                                    updated_lesson.content_version,
                                    lesson_ordinals[lesson.lesson_id],
                                    lesson.lesson_id,
                                ),
                            )
                            next_version = connection.execute(
                                "SELECT COALESCE(MAX(version),0)+1 FROM lesson_versions "
                                "WHERE lesson_id=?",
                                (lesson.lesson_id,),
                            ).fetchone()[0]
                            self._insert_published_seed_version(
                                updated_lesson, version=next_version, now=now
                            )
                            outcome["updated"] += 1
                        else:
                            connection.execute(
                                "UPDATE learning_lessons SET seed_version=? WHERE lesson_id=?",
                                (seed_version, lesson.lesson_id),
                            )
                            outcome["skipped"] += 1
                    else:
                        outcome["skipped"] += 1
                    continue
                connection.execute(
                    """INSERT INTO learning_lessons(
                        lesson_id,unit_id,title,active_version,created_at,summary,band,revision,
                        seed_version,seed_hash,seed_owned,content_hash,content_version,ordinal
                    ) VALUES(?,?,?,NULL,?,?,?,?,?,?,1,?,?,?)""",
                    (
                        lesson.lesson_id,
                        unit_id,
                        lesson.title,
                        stamp,
                        lesson.summary,
                        lesson.band.value,
                        lesson.revision,
                        seed_version,
                        lesson_hash,
                        lesson_hash,
                        lesson.content_version,
                        lesson_ordinals[lesson.lesson_id],
                    ),
                )
                self._insert_published_seed_version(lesson, version=1, now=now)
                outcome["inserted"] += 1
            connection.execute(
                """INSERT INTO learning_seed_manifest(
                       seed_name,seed_version,manifest_sha256,layout,applied_at,result_json
                   ) VALUES(?,?,?,?,?,?) ON CONFLICT(seed_name) DO UPDATE SET
                   seed_version=excluded.seed_version,manifest_sha256=excluded.manifest_sha256,
                   layout=excluded.layout,applied_at=excluded.applied_at,
                   result_json=excluded.result_json""",
                (path.path_id, seed_version, manifest_hash, layout, stamp, _dump_json(outcome)),
            )
        return manifest_hash

    def _insert_published_seed_version(
        self, lesson: Lesson, *, version: int, now: datetime
    ) -> None:
        stamp = _timestamp(now)
        snapshot = PublishedLessonVersion.from_lesson(lesson, version=version, published_at=now)
        self._store.connection.execute(
            """INSERT INTO lesson_versions(
                lesson_id,version,state,rules_version,published_at,created_at,title,summary,
                band,revision,content_hash
            ) VALUES(?,?,'draft',?,NULL,?,?,?,?,?,NULL)""",
            (
                lesson.lesson_id,
                version,
                snapshot.rules_version,
                stamp,
                snapshot.title,
                snapshot.summary,
                snapshot.band.value,
                snapshot.revision,
            ),
        )
        for step in snapshot.steps:
            self._store.connection.execute(
                """INSERT INTO lesson_steps(
                    lesson_id,version,step_id,kind,ordinal,payload,stage,instruction,rules_version
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    lesson.lesson_id,
                    version,
                    step.step_id,
                    step.kind.value,
                    step.ordinal,
                    _dump_json(step.payload),
                    step.stage.value,
                    step.instruction,
                    step.rules_version,
                ),
            )
        self._store.connection.execute(
            """UPDATE lesson_versions SET state='published',published_at=?,content_hash=?
               WHERE lesson_id=? AND version=?""",
            (stamp, snapshot.content_hash, lesson.lesson_id, version),
        )
        self._store.connection.execute(
            "UPDATE learning_lessons SET active_version=? WHERE lesson_id=?",
            (version, lesson.lesson_id),
        )

    def create_practice_attempt(
        self,
        owner_id: str,
        mission: PracticeMission,
        purpose: PracticePurpose,
        idempotency_key: str,
        *,
        prompt_version: str,
        blob_id: str,
        audio_content_type: str,
        sha256: str,
        size_bytes: int,
        now: datetime,
        review_source_kind: str | None = None,
        review_source_attempt_id: str | None = None,
        review_content_key: str | None = None,
        expected_review_revision: int | None = None,
        review_box: int | None = None,
    ) -> PracticeAttemptRecord:
        _validate_attempt_input(
            owner_id, idempotency_key, blob_id, audio_content_type, sha256, size_bytes
        )
        if prompt_version != mission.prompt_version:
            raise ValueError("declared prompt version does not match the selected mission")
        _validate_review_binding(
            review_source_kind,
            review_source_attempt_id,
            review_content_key,
            expected_review_revision,
            review_box,
        )
        created = _timestamp(now)
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT attempt_id FROM practice_attempts "
                "WHERE owner_id=? AND purpose=? AND idempotency_key=?",
                (owner_id, purpose.value, idempotency_key),
            ).fetchone()
            if existing:
                record = self.get_practice_attempt(owner_id, existing[0])
                if record is None:
                    raise LearningConflict("idempotent attempt reference is missing")
                if (
                    record.purpose is not purpose
                    or record.mission is None
                    or record.mission.prompt_version != prompt_version
                    or record.audio is None
                    or record.audio.sha256 != sha256
                    or record.audio.content_type != audio_content_type
                    or record.review_source_kind != review_source_kind
                    or record.review_source_attempt_id != review_source_attempt_id
                    or record.review_content_key != review_content_key
                    or record.expected_review_revision != expected_review_revision
                    or record.review_box != review_box
                ):
                    raise LearningConflict("idempotency key was reused for a different request")
                return record
            attempt_id = self._new_id()
            connection.execute(
                """INSERT INTO practice_attempts(
                    attempt_id,owner_id,mission_id,prompt_version,status,measurements,evidence,
                    created_at,updated_at,purpose,idempotency_key,rules_version,
                    mission_snapshot,attempt_state,result_json,reasons_json,revision,
                    review_source_kind,review_source_attempt_id,review_content_key,
                    expected_review_revision,review_box
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'QUEUED',NULL,'[]',0,?,?,?,?,?)""",
                (
                    attempt_id,
                    owner_id,
                    mission.mission_id,
                    mission.prompt_version,
                    "QUEUED",
                    "{}",
                    "{}",
                    created,
                    created,
                    purpose.value,
                    idempotency_key,
                    mission.rules_version,
                    _dump_json(mission),
                    review_source_kind,
                    review_source_attempt_id,
                    review_content_key,
                    expected_review_revision,
                    review_box,
                ),
            )
            self._insert_audio(
                owner_id,
                "practice",
                attempt_id,
                blob_id,
                audio_content_type,
                sha256,
                size_bytes,
                created,
            )
        record = self.get_practice_attempt(owner_id, attempt_id)
        assert record is not None
        return record

    def get_practice_attempt_by_idempotency(
        self, owner_id: str, purpose: PracticePurpose, idempotency_key: str
    ) -> PracticeAttemptRecord | None:
        row = self._store.connection.execute(
            "SELECT attempt_id FROM practice_attempts "
            "WHERE owner_id=? AND purpose=? AND idempotency_key=?",
            (owner_id, purpose.value, idempotency_key),
        ).fetchone()
        return self.get_practice_attempt(owner_id, row[0]) if row else None

    def get_path(self, path_id: str, *, published_only: bool = True) -> LearningPath | None:
        row = self._store.connection.execute(
            "SELECT path_id,title,description,state,band_from,band_to,content_version,revision "
            "FROM learning_paths WHERE path_id=?",
            (path_id,),
        ).fetchone()
        if row is None or (published_only and row[3] != "published"):
            return None
        if row[4] is None or row[5] is None or row[6] is None:
            return None
        unit_rows = self._store.connection.execute(
            """SELECT unit_id,path_id,ordinal,title,band,topic,learning_function,revision
               FROM learning_units WHERE path_id=? ORDER BY ordinal,unit_id""",
            (path_id,),
        ).fetchall()
        units: list[LearningUnit] = []
        for unit in unit_rows:
            if published_only:
                lessons = self._store.connection.execute(
                    """SELECT l.lesson_id FROM learning_lessons l
                       JOIN lesson_versions v ON v.lesson_id=l.lesson_id
                         AND v.version=l.active_version AND v.state='published'
                       WHERE l.unit_id=? ORDER BY l.ordinal,l.lesson_id""",
                    (unit[0],),
                ).fetchall()
            else:
                lessons = self._store.connection.execute(
                    "SELECT lesson_id FROM learning_lessons WHERE unit_id=? "
                    "ORDER BY ordinal,lesson_id",
                    (unit[0],),
                ).fetchall()
            from aicefr.lessons.model import Topic

            units.append(
                LearningUnit(
                    unit_id=unit[0],
                    path_id=unit[1],
                    ordinal=unit[2],
                    title=unit[3],
                    band=Band(unit[4]),
                    topic=Topic(unit[5]) if unit[5] else None,
                    learning_function=unit[6],
                    lesson_ids=tuple(item[0] for item in lessons),
                    revision=unit[7],
                )
            )
        return LearningPath(
            path_id=row[0],
            title=row[1],
            description=row[2],
            band_from=Band(row[4]),
            band_to=Band(row[5]),
            units=tuple(units),
            content_version=row[6],
            revision=row[7],
        )

    def path_revision(self, path_id: str) -> int | None:
        """Return the current CAS revision for a teacher's path projection."""
        row = self._store.connection.execute(
            "SELECT revision FROM learning_paths WHERE path_id=?", (path_id,)
        ).fetchone()
        return int(row[0]) if row is not None else None

    def unit_revision(self, unit_id: str) -> int | None:
        """Return the current CAS revision for a teacher's unit projection."""
        row = self._store.connection.execute(
            "SELECT revision FROM learning_units WHERE unit_id=?", (unit_id,)
        ).fetchone()
        return int(row[0]) if row is not None else None

    def list_paths(self, *, published_only: bool = True) -> tuple[LearningPath, ...]:
        where = "WHERE state='published'" if published_only else ""
        ids = self._store.connection.execute(
            f"SELECT path_id FROM learning_paths {where} ORDER BY path_id"
        ).fetchall()
        return tuple(
            path
            for item in ids
            if (path := self.get_path(item[0], published_only=published_only)) is not None
        )

    def get_lesson(
        self,
        lesson_id: str,
        *,
        version: int | None = None,
        published_only: bool = True,
    ) -> Lesson | PublishedLessonVersion | LegacyPublishedLessonVersion | None:
        lesson = self._store.connection.execute(
            """SELECT l.lesson_id,l.title,l.summary,l.band,l.revision,l.content_version,
                      l.active_version,u.path_id,p.state
               FROM learning_lessons l JOIN learning_units u ON u.unit_id=l.unit_id
               JOIN learning_paths p ON p.path_id=u.path_id WHERE l.lesson_id=?""",
            (lesson_id,),
        ).fetchone()
        if lesson is None or (published_only and lesson[8] != "published"):
            return None
        if version is None and not published_only:
            draft = self._store.connection.execute(
                "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
                "ORDER BY version DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if draft is not None:
                return self._draft_lesson_from_rows(lesson_id, draft[0])
            if lesson[6] is not None:
                published = self.get_lesson(lesson_id, version=lesson[6], published_only=True)
                if isinstance(published, PublishedLessonVersion):
                    return Lesson(
                        lesson_id=published.lesson_id,
                        title=published.title,
                        summary=published.summary,
                        band=published.band,
                        steps=published.steps,
                        revision=lesson[4],
                        content_version=lesson[5],
                    )
                return None
        selected_version = version if version is not None else lesson[6]
        if selected_version is None:
            if published_only:
                return None
            steps = self._read_draft_steps(lesson_id)
            if lesson[3] is None:
                return None
            return Lesson(
                lesson_id=lesson[0],
                title=lesson[1],
                summary=lesson[2],
                band=Band(lesson[3]),
                revision=lesson[4],
                content_version=lesson[5],
                steps=steps,
            )
        version_row = self._store.connection.execute(
            """SELECT state,rules_version,published_at,title,summary,band,revision,content_hash
               FROM lesson_versions WHERE lesson_id=? AND version=?""",
            (lesson_id, selected_version),
        ).fetchone()
        if version_row is None or (published_only and version_row[0] != "published"):
            return None
        steps = self._read_version_steps(lesson_id, selected_version)
        published_at = _parse_timestamp(version_row[2]) if version_row[2] else None
        if (
            version_row[5] is None
            or not version_row[7]
            or not steps
            or any(not isinstance(step, LessonStep) for step in steps)
        ):
            return LegacyPublishedLessonVersion(
                lesson_id=lesson_id,
                version=selected_version,
                revision=version_row[6],
                title=version_row[3] or lesson[1],
                summary=version_row[4] if version_row[4] else None,
                band=Band(version_row[5]) if version_row[5] else None,
                rules_version=version_row[1],
                published_at=published_at,
                content_hash=version_row[7],
                steps=tuple(
                    step
                    if isinstance(step, LessonStep)
                    else self._legacy_step_dict(lesson_id, selected_version, step)
                    for step in steps
                ),
            )
        return PublishedLessonVersion(
            lesson_id=lesson_id,
            version=selected_version,
            revision=version_row[6],
            title=version_row[3],
            summary=version_row[4],
            band=Band(version_row[5]),
            rules_version=version_row[1],
            published_at=published_at,
            content_hash=version_row[7],
            steps=tuple(steps),
        )

    def save_draft_lesson(
        self,
        actor_id: str,
        unit_id: str,
        lesson: Lesson,
        expected_revision: int,
        now: datetime,
    ) -> Lesson:
        stamp = _timestamp(now)
        lesson_id = lesson.lesson_id
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            unit = connection.execute(
                "SELECT path_id FROM learning_units WHERE unit_id=?", (unit_id,)
            ).fetchone()
            if unit is None:
                raise KeyError("learning unit not found")
            current = connection.execute(
                "SELECT unit_id,revision FROM learning_lessons WHERE lesson_id=?", (lesson_id,)
            ).fetchone()
            if current is None:
                if expected_revision != 0:
                    raise LearningConflict("new lesson expected revision must be zero")
                next_revision = 1
                connection.execute(
                    """INSERT INTO learning_lessons(
                        lesson_id,unit_id,title,active_version,created_at,summary,band,revision,
                        content_version
                    ) VALUES(?,?,?,NULL,?,?,?,?,?)""",
                    (
                        lesson_id,
                        unit_id,
                        lesson.title,
                        stamp,
                        lesson.summary,
                        lesson.band.value,
                        next_revision,
                        lesson.content_version,
                    ),
                )
            else:
                if current[0] != unit_id:
                    raise LearningConflict("lesson cannot be moved by a draft edit")
                if current[1] != expected_revision:
                    raise LearningConflict("lesson revision is stale")
                next_revision = current[1] + 1
                changed = connection.execute(
                    """UPDATE learning_lessons SET title=?,summary=?,band=?,revision=?,
                       content_version=?,
                       seed_owned=0,content_hash=NULL
                       WHERE lesson_id=? AND revision=?""",
                    (
                        lesson.title,
                        lesson.summary,
                        lesson.band.value,
                        next_revision,
                        lesson.content_version,
                        lesson_id,
                        expected_revision,
                    ),
                ).rowcount
                if changed != 1:
                    raise LearningConflict("lesson revision is stale")
            versions = connection.execute(
                "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
                "ORDER BY version DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if versions:
                version = versions[0]
                connection.execute(
                    "DELETE FROM lesson_steps WHERE lesson_id=? AND version=?",
                    (lesson_id, version),
                )
                connection.execute(
                    """UPDATE lesson_versions SET rules_version=?,title=?,summary=?,band=?,
                       revision=?,content_hash=NULL WHERE lesson_id=? AND version=?""",
                    (
                        lesson.steps[0].rules_version if lesson.steps else "pending",
                        lesson.title,
                        lesson.summary,
                        lesson.band.value,
                        next_revision,
                        lesson_id,
                        version,
                    ),
                )
            else:
                version = connection.execute(
                    "SELECT COALESCE(MAX(version),0)+1 FROM lesson_versions WHERE lesson_id=?",
                    (lesson_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO lesson_versions(
                        lesson_id,version,state,rules_version,published_at,created_at,title,
                        summary,band,revision,content_hash
                    ) VALUES(?,?,'draft',?,NULL,?,?,?,?,?,NULL)""",
                    (
                        lesson_id,
                        version,
                        lesson.steps[0].rules_version if lesson.steps else "pending",
                        stamp,
                        lesson.title,
                        lesson.summary,
                        lesson.band.value,
                        next_revision,
                    ),
                )
            for step in lesson.steps:
                connection.execute(
                    """INSERT INTO lesson_steps(
                        lesson_id,version,step_id,kind,ordinal,payload,stage,instruction,rules_version
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        lesson_id,
                        version,
                        step.step_id,
                        step.kind.value,
                        step.ordinal,
                        _dump_json(step.payload),
                        step.stage.value,
                        step.instruction,
                        step.rules_version,
                    ),
                )
            self._audit(actor_id, "lesson_draft_saved", lesson_id, stamp)
        return lesson.model_copy(update={"revision": next_revision})

    def save_draft_path(
        self, actor_id: str, path: LearningPath, *, expected_revision: int, now: datetime
    ) -> LearningPath:
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            current = connection.execute(
                "SELECT revision,state FROM learning_paths WHERE path_id=?", (path.path_id,)
            ).fetchone()
            if current is None:
                if expected_revision != 0:
                    raise LearningConflict("new path expected revision must be zero")
                revision = 1
                connection.execute(
                    """INSERT INTO learning_paths(
                        path_id,title,description,state,revision,created_at,updated_at,band_from,
                        band_to,content_version,seed_owned
                    ) VALUES(?,?,?,'draft',?,?,?,?,?,?,0)""",
                    (
                        path.path_id,
                        path.title,
                        path.description,
                        revision,
                        stamp,
                        stamp,
                        path.band_from.value,
                        path.band_to.value,
                        path.content_version,
                    ),
                )
            else:
                if current[1] != "draft":
                    raise LearningConflict("published path metadata is immutable")
                if current[0] != expected_revision:
                    raise LearningConflict("path revision is stale")
                revision = expected_revision + 1
                changed = connection.execute(
                    """UPDATE learning_paths SET title=?,description=?,band_from=?,band_to=?,
                       content_version=?,revision=?,updated_at=?,seed_owned=0,content_hash=NULL
                       WHERE path_id=? AND revision=? AND state='draft'""",
                    (
                        path.title,
                        path.description,
                        path.band_from.value,
                        path.band_to.value,
                        path.content_version,
                        revision,
                        stamp,
                        path.path_id,
                        expected_revision,
                    ),
                ).rowcount
                if changed != 1:
                    raise LearningConflict("path revision is stale")
            self._audit(actor_id, "learning_path_saved", path.path_id, stamp)
        return path.model_copy(update={"revision": revision})

    def publish_path(
        self,
        actor_id: str,
        path_id: str,
        *,
        expected_revision: int,
        now: datetime,
    ) -> LearningPath:
        """Publish a complete draft hierarchy after every lesson has a snapshot."""
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            path_row = connection.execute(
                """SELECT title,description,state,revision,band_from,band_to,content_version
                   FROM learning_paths WHERE path_id=?""",
                (path_id,),
            ).fetchone()
            if path_row is None:
                raise KeyError("learning path not found")
            if path_row[3] != expected_revision:
                raise LearningConflict("path revision is stale")
            if path_row[2] != "draft":
                raise LearningConflict("only a draft path can be published")
            unit_rows = connection.execute(
                """SELECT unit_id,path_id,ordinal,title,band,topic,learning_function,revision
                   FROM learning_units WHERE path_id=? ORDER BY ordinal,unit_id""",
                (path_id,),
            ).fetchall()
            if not unit_rows or [row[2] for row in unit_rows] != list(range(1, len(unit_rows) + 1)):
                raise ValueError("a published path needs ordered units starting at one")
            units: list[LearningUnit] = []
            snapshots: list[tuple[str, int, str]] = []
            for unit in unit_rows:
                lesson_rows = connection.execute(
                    """SELECT l.lesson_id,l.active_version,v.state,v.content_hash
                       FROM learning_lessons l LEFT JOIN lesson_versions v
                         ON v.lesson_id=l.lesson_id AND v.version=l.active_version
                       WHERE l.unit_id=? ORDER BY l.ordinal,l.lesson_id""",
                    (unit[0],),
                ).fetchall()
                if not lesson_rows:
                    raise ValueError("every published unit must contain a lesson")
                for lesson_id, version, state, content_hash in lesson_rows:
                    if version is None or state != "published" or not content_hash:
                        raise ValueError("every path lesson needs a published snapshot")
                    published = self.get_lesson(lesson_id, version=version, published_only=False)
                    if not isinstance(published, PublishedLessonVersion):
                        raise ValueError("legacy or invalid lessons cannot publish a path")
                    snapshots.append((lesson_id, version, content_hash))
                from aicefr.lessons.model import Topic

                units.append(
                    LearningUnit(
                        unit_id=unit[0],
                        path_id=unit[1],
                        ordinal=unit[2],
                        title=unit[3],
                        band=Band(unit[4]),
                        topic=Topic(unit[5]) if unit[5] else None,
                        learning_function=unit[6],
                        lesson_ids=tuple(row[0] for row in lesson_rows),
                        revision=unit[7],
                    )
                )
            path = LearningPath(
                path_id=path_id,
                title=path_row[0],
                description=path_row[1],
                band_from=Band(path_row[4]),
                band_to=Band(path_row[5]),
                units=tuple(units),
                content_version=path_row[6],
                revision=expected_revision,
            )
            content_hash = hashlib.sha256(
                _dump_json({"path": path.model_dump(mode="json"), "lessons": snapshots}).encode(
                    "utf-8"
                )
            ).hexdigest()
            changed = connection.execute(
                """UPDATE learning_paths SET state='published',revision=revision+1,
                   updated_at=?,content_hash=?,seed_owned=0
                   WHERE path_id=? AND state='draft' AND revision=?""",
                (stamp, content_hash, path_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("path revision is stale")
            self._audit(actor_id, "learning_path_published", path_id, stamp)
        return path.model_copy(update={"revision": expected_revision + 1})

    def save_draft_unit(
        self,
        actor_id: str,
        path_id: str,
        unit: LearningUnit,
        *,
        expected_revision: int,
        now: datetime,
    ) -> LearningUnit:
        if unit.path_id != path_id:
            raise ValueError("unit path id does not match its authoring path")
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            path = connection.execute(
                "SELECT state FROM learning_paths WHERE path_id=?", (path_id,)
            ).fetchone()
            if path is None:
                raise KeyError("learning path not found")
            if path[0] != "draft":
                raise LearningConflict("units can only be changed in a draft path")
            current = connection.execute(
                "SELECT revision,path_id FROM learning_units WHERE unit_id=?", (unit.unit_id,)
            ).fetchone()
            if current is None:
                if expected_revision != 0:
                    raise LearningConflict("new unit expected revision must be zero")
                revision = 1
                connection.execute(
                    """INSERT INTO learning_units(
                        unit_id,path_id,title,ordinal,band,topic,learning_function,revision,seed_owned
                    ) VALUES(?,?,?,?,?,?,?,?,0)""",
                    (
                        unit.unit_id,
                        path_id,
                        unit.title,
                        unit.ordinal,
                        unit.band.value,
                        unit.topic.value if unit.topic else None,
                        unit.learning_function,
                        revision,
                    ),
                )
            else:
                if current[1] != path_id:
                    raise LearningConflict("unit cannot be moved between paths")
                if current[0] != expected_revision:
                    raise LearningConflict("unit revision is stale")
                revision = expected_revision + 1
                changed = connection.execute(
                    """UPDATE learning_units SET title=?,ordinal=?,band=?,topic=?,
                       learning_function=?,
                       revision=?,seed_owned=0,content_hash=NULL
                       WHERE unit_id=? AND path_id=? AND revision=?""",
                    (
                        unit.title,
                        unit.ordinal,
                        unit.band.value,
                        unit.topic.value if unit.topic else None,
                        unit.learning_function,
                        revision,
                        unit.unit_id,
                        path_id,
                        expected_revision,
                    ),
                ).rowcount
                if changed != 1:
                    raise LearningConflict("unit revision is stale")
            self._audit(actor_id, "learning_unit_saved", unit.unit_id, stamp)
        return unit.model_copy(update={"revision": revision}) if hasattr(unit, "revision") else unit

    def delete_draft_path(
        self, actor_id: str, path_id: str, *, expected_revision: int, now: datetime
    ) -> bool:
        """Delete a draft path and its draft descendants with audio cleanup queued."""
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            row = connection.execute(
                "SELECT state,revision FROM learning_paths WHERE path_id=?", (path_id,)
            ).fetchone()
            if row is None:
                return False
            if row[0] != "draft":
                raise LearningConflict("only draft paths can be deleted")
            if row[1] != expected_revision:
                raise LearningConflict("path revision is stale")
            published = connection.execute(
                """SELECT 1 FROM learning_lessons l JOIN learning_units u ON u.unit_id=l.unit_id
                   JOIN lesson_versions v ON v.lesson_id=l.lesson_id
                   WHERE u.path_id=? AND v.state='published' LIMIT 1""",
                (path_id,),
            ).fetchone()
            if published:
                raise LearningConflict("path contains published lesson versions")
            self._queue_path_media_cleanup(connection, actor_id, path_id, now)
            changed = connection.execute(
                "DELETE FROM learning_paths WHERE path_id=? AND state='draft' AND revision=?",
                (path_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("path revision is stale")
            self._audit(actor_id, "learning_path_deleted", path_id, _timestamp(now))
        return True

    def delete_draft_unit(
        self,
        actor_id: str,
        path_id: str,
        unit_id: str,
        *,
        expected_revision: int,
        now: datetime,
    ) -> bool:
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            path = connection.execute(
                "SELECT state FROM learning_paths WHERE path_id=?", (path_id,)
            ).fetchone()
            unit = connection.execute(
                "SELECT path_id,revision FROM learning_units WHERE unit_id=?", (unit_id,)
            ).fetchone()
            if unit is None or path is None or unit[0] != path_id:
                return False
            if path[0] != "draft":
                raise LearningConflict("units can only be deleted from a draft path")
            if unit[1] != expected_revision:
                raise LearningConflict("unit revision is stale")
            published = connection.execute(
                """SELECT 1 FROM learning_lessons l JOIN lesson_versions v
                   ON v.lesson_id=l.lesson_id WHERE l.unit_id=? AND v.state='published' LIMIT 1""",
                (unit_id,),
            ).fetchone()
            if published:
                raise LearningConflict("unit contains published lesson versions")
            self._queue_unit_media_cleanup(connection, actor_id, unit_id, now)
            changed = connection.execute(
                "DELETE FROM learning_units WHERE unit_id=? AND path_id=? AND revision=?",
                (unit_id, path_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("unit revision is stale")
            self._audit(actor_id, "learning_unit_deleted", unit_id, _timestamp(now))
        return True

    def delete_draft_lesson(
        self,
        actor_id: str,
        lesson_id: str,
        *,
        expected_revision: int,
        now: datetime,
    ) -> bool:
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            row = connection.execute(
                "SELECT revision FROM learning_lessons WHERE lesson_id=?", (lesson_id,)
            ).fetchone()
            if row is None:
                return False
            if row[0] != expected_revision:
                raise LearningConflict("lesson revision is stale")
            published = connection.execute(
                "SELECT 1 FROM lesson_versions WHERE lesson_id=? AND state='published' LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if published:
                raise LearningConflict("published lesson versions are immutable")
            self._queue_lesson_media_cleanup(connection, actor_id, lesson_id, now)
            changed = connection.execute(
                "DELETE FROM learning_lessons WHERE lesson_id=? AND revision=?",
                (lesson_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("lesson revision is stale")
            self._audit(actor_id, "lesson_draft_deleted", lesson_id, _timestamp(now))
        return True

    def delete_draft_step(
        self,
        actor_id: str,
        lesson_id: str,
        step_id: str,
        *,
        expected_revision: int,
        now: datetime,
    ) -> Lesson:
        return self._mutate_draft_steps(
            actor_id,
            lesson_id,
            expected_revision=expected_revision,
            now=now,
            action="lesson_step_deleted",
            mutate=lambda steps: tuple(step for step in steps if step.step_id != step_id),
            required_step_id=step_id,
        )

    def reorder_draft_steps(
        self,
        actor_id: str,
        lesson_id: str,
        ordered_step_ids: tuple[str, ...],
        *,
        expected_revision: int,
        now: datetime,
    ) -> Lesson:
        def reorder(steps: tuple[LessonStep, ...]) -> tuple[LessonStep, ...]:
            if set(ordered_step_ids) != {step.step_id for step in steps} or len(steps) != len(
                ordered_step_ids
            ):
                raise ValueError("reorder must name every draft step exactly once")
            by_id = {step.step_id: step for step in steps}
            return tuple(
                by_id[step_id].model_copy(update={"ordinal": ordinal})
                for ordinal, step_id in enumerate(ordered_step_ids, start=1)
            )

        return self._mutate_draft_steps(
            actor_id,
            lesson_id,
            expected_revision=expected_revision,
            now=now,
            action="lesson_steps_reordered",
            mutate=reorder,
        )

    def _mutate_draft_steps(
        self,
        actor_id: str,
        lesson_id: str,
        *,
        expected_revision: int,
        now: datetime,
        action: str,
        mutate,
        required_step_id: str | None = None,
    ) -> Lesson:
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            current = connection.execute(
                "SELECT revision FROM learning_lessons WHERE lesson_id=?", (lesson_id,)
            ).fetchone()
            draft = connection.execute(
                "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
                "ORDER BY version DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if current is None or draft is None:
                raise KeyError("draft lesson not found")
            if current[0] != expected_revision:
                raise LearningConflict("lesson revision is stale")
            steps = self._read_version_steps(lesson_id, draft[0])
            if any(not isinstance(step, LessonStep) for step in steps):
                raise ValueError("draft lesson contains invalid typed steps")
            if required_step_id is not None and not any(
                step.step_id == required_step_id for step in steps
            ):
                raise KeyError("draft lesson step not found")
            changed_steps = mutate(steps)
            version = draft[0]
            removed_ids = {step.step_id for step in steps} - {
                step.step_id for step in changed_steps
            }
            for removed_id in removed_ids:
                self._queue_step_media_cleanup(
                    connection, actor_id, lesson_id, version, removed_id, now
                )
            if removed_ids:
                placeholders = ",".join("?" for _ in removed_ids)
                connection.execute(
                    f"DELETE FROM learning_media WHERE lesson_id=? AND lesson_version=? "
                    f"AND step_id IN ({placeholders})",
                    (lesson_id, version, *sorted(removed_ids)),
                )
            connection.execute(
                "DELETE FROM lesson_steps WHERE lesson_id=? AND version=?", (lesson_id, version)
            )
            revision = expected_revision + 1
            for step in changed_steps:
                connection.execute(
                    """INSERT INTO lesson_steps(lesson_id,version,step_id,kind,ordinal,
                       payload,stage,
                       instruction,rules_version)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        lesson_id,
                        version,
                        step.step_id,
                        step.kind.value,
                        step.ordinal,
                        _dump_json(step.payload),
                        step.stage.value,
                        step.instruction,
                        step.rules_version,
                    ),
                )
            connection.execute(
                "UPDATE learning_lessons SET revision=?,seed_owned=0,content_hash=NULL "
                "WHERE lesson_id=? AND revision=?",
                (revision, lesson_id, expected_revision),
            )
            connection.execute(
                "UPDATE lesson_versions SET revision=?,content_hash=NULL "
                "WHERE lesson_id=? AND version=?",
                (revision, lesson_id, version),
            )
            self._audit(actor_id, action, lesson_id, _timestamp(now))
        result = self.get_draft_lesson(lesson_id)
        assert result is not None
        return result.lesson

    def move_draft_lesson(
        self,
        actor_id: str,
        lesson_id: str,
        target_unit_id: str,
        *,
        expected_revision: int,
        now: datetime,
    ) -> int:
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            target = connection.execute(
                """SELECT p.state FROM learning_units u JOIN learning_paths p ON p.path_id=u.path_id
                   WHERE u.unit_id=?""",
                (target_unit_id,),
            ).fetchone()
            lesson = connection.execute(
                "SELECT unit_id,active_version,revision FROM learning_lessons WHERE lesson_id=?",
                (lesson_id,),
            ).fetchone()
            if target is None or target[0] != "draft":
                raise ValueError("target unit must belong to a draft path")
            if lesson is None:
                raise KeyError("lesson not found")
            if lesson[1] is not None:
                raise LearningConflict("published lessons cannot be moved")
            if lesson[2] != expected_revision:
                raise LearningConflict("lesson revision is stale")
            changed = connection.execute(
                "UPDATE learning_lessons SET unit_id=?,revision=revision+1,seed_owned=0,"
                "content_hash=NULL "
                "WHERE lesson_id=? AND revision=? AND active_version IS NULL",
                (target_unit_id, lesson_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("lesson revision is stale")
            self._audit(actor_id, "draft_lesson_moved", lesson_id, stamp)
        return expected_revision + 1

    def reorder_units(
        self,
        actor_id: str,
        path_id: str,
        ordered_unit_ids: tuple[str, ...],
        expected_revision: int,
        now: datetime,
    ) -> int:
        stamp = _timestamp(now)
        if len(set(ordered_unit_ids)) != len(ordered_unit_ids):
            raise ValueError("unit order cannot contain duplicates")
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            path = connection.execute(
                "SELECT revision,state FROM learning_paths WHERE path_id=?", (path_id,)
            ).fetchone()
            if path is None:
                raise KeyError("learning path not found")
            if path[0] != expected_revision:
                raise LearningConflict("path revision is stale")
            if path[1] != "draft":
                raise LearningConflict("published path order cannot be changed")
            actual = tuple(
                row[0]
                for row in connection.execute(
                    "SELECT unit_id FROM learning_units WHERE path_id=? ORDER BY ordinal,unit_id",
                    (path_id,),
                )
            )
            if set(actual) != set(ordered_unit_ids) or len(actual) != len(ordered_unit_ids):
                raise ValueError("reorder must name every unit in the path exactly once")
            connection.execute(
                "UPDATE learning_units SET ordinal=ordinal+100000,seed_owned=0,content_hash=NULL "
                "WHERE path_id=?",
                (path_id,),
            )
            for ordinal, unit_id in enumerate(ordered_unit_ids, start=1):
                connection.execute(
                    "UPDATE learning_units SET ordinal=?,revision=revision+1 "
                    "WHERE path_id=? AND unit_id=?",
                    (ordinal, path_id, unit_id),
                )
            changed = connection.execute(
                "UPDATE learning_paths SET revision=revision+1,updated_at=?,seed_owned=0,"
                "content_hash=NULL "
                "WHERE path_id=? AND revision=?",
                (stamp, path_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("path revision is stale")
            self._audit(actor_id, "learning_units_reordered", path_id, stamp)
        return expected_revision + 1

    def publish_lesson(
        self,
        actor_id: str,
        lesson_id: str,
        expected_revision: int,
        now: datetime,
    ) -> PublishedLessonVersion:
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            current = connection.execute(
                "SELECT unit_id,revision FROM learning_lessons WHERE lesson_id=?", (lesson_id,)
            ).fetchone()
            if current is None:
                raise KeyError("lesson not found")
            if current[1] != expected_revision:
                raise LearningConflict("lesson revision is stale")
            draft = connection.execute(
                "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
                "ORDER BY version DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if draft is None:
                raise ValueError("lesson has no draft version to publish")
            lesson = self._draft_lesson_from_rows(lesson_id, draft[0])
            snapshot = PublishedLessonVersion.from_lesson(
                lesson, version=draft[0], published_at=now
            )
            connection.execute(
                """UPDATE lesson_versions SET title=?,summary=?,band=?,revision=?,content_hash=?,
                   rules_version=?,published_at=?,state='published'
                   WHERE lesson_id=? AND version=? AND state='draft'""",
                (
                    snapshot.title,
                    snapshot.summary,
                    snapshot.band.value,
                    snapshot.revision,
                    snapshot.content_hash,
                    snapshot.rules_version,
                    _timestamp(now),
                    lesson_id,
                    draft[0],
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise LearningConflict("lesson draft changed while publishing")
            connection.execute(
                "UPDATE learning_lessons SET active_version=? WHERE lesson_id=?",
                (draft[0], lesson_id),
            )
            self._audit(actor_id, "lesson_published", lesson_id, _timestamp(now))
            return snapshot

    def create_lesson_media(
        self,
        actor_id: str,
        *,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        media_kind: str,
        blob_id: str,
        content_type: str,
        sha256: str,
        size_bytes: int,
        now: datetime,
    ) -> LearningMediaArtifact:
        _validate_media(blob_id, content_type, sha256, size_bytes, media_kind)
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            version = connection.execute(
                "SELECT state FROM lesson_versions WHERE lesson_id=? AND version=?",
                (lesson_id, lesson_version),
            ).fetchone()
            step = connection.execute(
                "SELECT 1 FROM lesson_steps WHERE lesson_id=? AND version=? AND step_id=?",
                (lesson_id, lesson_version, step_id),
            ).fetchone()
            if version is None or version[0] != "draft" or step is None:
                raise ValueError("lesson media must attach to a draft version and existing step")
            media_id = self._new_id()
            connection.execute(
                """INSERT INTO learning_media(
                    media_id,lesson_id,media_kind,blob_id,sha256,size_bytes,created_at,
                    lesson_version,step_id,content_type
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    media_id,
                    lesson_id,
                    media_kind,
                    blob_id,
                    sha256,
                    size_bytes,
                    stamp,
                    lesson_version,
                    step_id,
                    content_type,
                ),
            )
            self._audit(actor_id, "lesson_media_attached", media_id, stamp)
        return LearningMediaArtifact(
            media_id,
            lesson_id,
            lesson_version,
            step_id,
            media_kind,
            blob_id,
            content_type,
            sha256,
            size_bytes,
            now,
        )

    def get_lesson_media(
        self,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        *,
        include_draft: bool = False,
        actor_id: str | None = None,
    ) -> tuple[LearningMediaArtifact, ...]:
        if include_draft:
            if actor_id is None:
                raise PermissionError("draft media preview requires an authenticated author")
            self._require_author(actor_id)
        rows = self._store.connection.execute(
            """SELECT m.media_id,m.lesson_id,m.lesson_version,m.step_id,m.media_kind,
                      m.blob_id,m.content_type,m.sha256,m.size_bytes,m.created_at,v.state,p.state
               FROM learning_media m JOIN lesson_versions v
                 ON v.lesson_id=m.lesson_id AND v.version=m.lesson_version
               JOIN learning_lessons l ON l.lesson_id=m.lesson_id
               JOIN learning_units u ON u.unit_id=l.unit_id
               JOIN learning_paths p ON p.path_id=u.path_id
               WHERE m.lesson_id=? AND m.lesson_version=? AND m.step_id=?
               ORDER BY m.media_kind,m.media_id""",
            (lesson_id, lesson_version, step_id),
        ).fetchall()
        return tuple(
            LearningMediaArtifact(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                _parse_timestamp(row[9]),
            )
            for row in rows
            if (row[10] == "published" and row[11] == "published") or include_draft
        )

    def _draft_lesson_from_rows(self, lesson_id: str, version: int) -> Lesson:
        row = self._store.connection.execute(
            "SELECT title,summary,band,revision,content_version "
            "FROM learning_lessons WHERE lesson_id=?",
            (lesson_id,),
        ).fetchone()
        if row is None or row[2] is None:
            raise ValueError("draft lesson is missing required metadata")
        steps = self._read_version_steps(lesson_id, version)
        if any(not isinstance(step, LessonStep) for step in steps):
            raise ValueError("draft lesson contains invalid typed steps")
        return Lesson(
            lesson_id=lesson_id,
            title=row[0],
            summary=row[1],
            band=Band(row[2]),
            revision=row[3],
            content_version=row[4],
            steps=tuple(steps),
        )

    def get_draft_lesson(self, lesson_id: str) -> DraftLessonRecord | None:
        row = self._store.connection.execute(
            "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
            "ORDER BY version DESC LIMIT 1",
            (lesson_id,),
        ).fetchone()
        if row is None:
            return None
        return DraftLessonRecord(
            lesson=self._draft_lesson_from_rows(lesson_id, row[0]),
            version=row[0],
        )

    def _require_author(self, actor_id: str) -> ActorRole:
        row = self._store.connection.execute(
            "SELECT role,disabled FROM accounts WHERE actor_id=?", (actor_id,)
        ).fetchone()
        if row is None or row[1] or row[0] not in {ActorRole.TEACHER.value, ActorRole.ADMIN.value}:
            raise PermissionError("teacher or admin role is required")
        return ActorRole(row[0])

    def _audit(self, actor_id: str, action: str, object_id: str, recorded_at: str) -> None:
        self._store.connection.execute(
            "INSERT INTO audit(event_id,actor_id,action,object_id,recorded_at,reason) "
            "VALUES(?,?,?,?,?,NULL)",
            (self._new_id(), actor_id, action, object_id, recorded_at),
        )

    def _read_draft_steps(self, lesson_id: str) -> tuple[LessonStep, ...]:
        row = self._store.connection.execute(
            "SELECT version FROM lesson_versions WHERE lesson_id=? AND state='draft' "
            "ORDER BY version DESC LIMIT 1",
            (lesson_id,),
        ).fetchone()
        return self._read_version_steps(lesson_id, row[0]) if row else ()

    def _read_version_steps(
        self, lesson_id: str, version: int
    ) -> tuple[LessonStep | dict[str, object], ...]:
        rows = self._store.connection.execute(
            """SELECT step_id,kind,ordinal,payload,stage,instruction,rules_version
               FROM lesson_steps WHERE lesson_id=? AND version=? ORDER BY ordinal,step_id""",
            (lesson_id, version),
        ).fetchall()
        result: list[LessonStep | dict[str, object]] = []
        for step_id, kind, ordinal, payload_json, stage, instruction, rules_version in rows:
            payload = json.loads(payload_json)
            if stage is None or instruction is None or rules_version is None:
                result.append(
                    {"step_id": step_id, "kind": kind, "ordinal": ordinal, "payload": payload}
                )
                continue
            try:
                result.append(
                    LessonStep(
                        step_id=step_id,
                        ordinal=ordinal,
                        stage=stage,
                        kind=kind,
                        instruction=instruction,
                        payload=payload,
                        rules_version=rules_version,
                    )
                )
            except ValidationError:
                result.append(
                    {"step_id": step_id, "kind": kind, "ordinal": ordinal, "payload": payload}
                )
        return tuple(result)

    @staticmethod
    def _legacy_step_dict(
        lesson_id: str, version: int, step: dict[str, object]
    ) -> dict[str, object]:
        # The serialized legacy step remains a raw, version-addressed projection.
        return {"lesson_id": lesson_id, "version": version, **step}

    def get_practice_attempt(self, owner_id: str, attempt_id: str) -> PracticeAttemptRecord | None:
        rows = _dict_rows(
            self._store.connection,
            """SELECT p.*, a.artifact_id,a.attempt_kind,a.blob_id AS audio_blob_id,
                      a.content_type AS audio_content_type,
                      a.sha256 AS audio_sha256,a.size_bytes AS audio_size_bytes,
                      a.created_at AS audio_created_at
               FROM practice_attempts p LEFT JOIN learning_audio_artifacts a
               ON a.attempt_kind='practice' AND a.practice_attempt_id=p.attempt_id
               WHERE p.owner_id=? AND p.attempt_id=?""",
            (owner_id, attempt_id),
        )
        return _practice_record(rows[0]) if rows else None

    def list_practice_attempts(
        self, owner_id: str, *, limit: int = 50, before: str | None = None
    ) -> tuple[PracticeAttemptRecord, ...]:
        _validate_limit(limit)
        query = """SELECT p.*, a.artifact_id,a.attempt_kind,a.blob_id AS audio_blob_id,
                   a.content_type AS audio_content_type,
                   a.sha256 AS audio_sha256,a.size_bytes AS audio_size_bytes,
                   a.created_at AS audio_created_at
                   FROM practice_attempts p LEFT JOIN learning_audio_artifacts a
                   ON a.attempt_kind='practice' AND a.practice_attempt_id=p.attempt_id
                   WHERE p.owner_id=?"""
        values: list[object] = [owner_id]
        if before is not None:
            query += " AND p.created_at<?"
            values.append(before)
        query += " ORDER BY p.created_at DESC,p.attempt_id DESC LIMIT ?"
        values.append(limit)
        rows = _dict_rows(self._store.connection, query, tuple(values))
        return tuple(_practice_record(row) for row in rows)

    def complete_practice_attempt(
        self,
        owner_id: str,
        attempt_id: str,
        result: PracticeResult | None,
        *,
        state: LearningAttemptState = LearningAttemptState.COMPLETED,
        reasons: tuple[str, ...] = (),
        expected_revision: int,
        now: datetime,
        review_source_kind: str | None = None,
        review_source_attempt_id: str | None = None,
        review_content_key: str | None = None,
        review_schedule: ReviewSchedule | None = None,
        expected_review_revision: int | None = None,
    ) -> PracticeAttemptRecord:
        reasons = _bounded_reasons(reasons)
        if state is LearningAttemptState.COMPLETED and result is None:
            raise ValueError("completed practice attempts require a typed result")
        if state is LearningAttemptState.NOT_EVALUATED and result is not None:
            raise ValueError("not-evaluated attempts cannot contain a result")
        if state is LearningAttemptState.NOT_EVALUATED and not reasons:
            raise ValueError("not-evaluated attempts require at least one reason")
        if state is LearningAttemptState.QUEUED:
            raise ValueError("an attempt cannot be completed back to queued")
        _validate_review_completion_args(
            review_source_kind,
            review_source_attempt_id,
            review_content_key,
            review_schedule,
            expected_review_revision,
        )
        if review_schedule is not None and (
            state is not LearningAttemptState.COMPLETED or result is None
        ):
            raise ValueError("review scheduling requires a completed typed practice result")
        with self._store.transaction() as connection:
            current = self.get_practice_attempt(owner_id, attempt_id)
            if current is None:
                raise KeyError("practice attempt not found")
            if current.state is not LearningAttemptState.QUEUED:
                if (
                    current.state is state
                    and current.result == result
                    and current.reasons == reasons
                ):
                    return current
                raise LearningConflict("practice attempt already completed differently")
            if current.revision != expected_revision:
                raise LearningConflict("practice attempt revision is stale")
            review_binding = _resolve_attempt_review_binding(
                attempt_id=attempt_id,
                attempt_kind="practice",
                stored=(
                    current.review_source_kind,
                    current.review_source_attempt_id,
                    current.review_content_key,
                    current.expected_review_revision,
                ),
                supplied=(
                    review_source_kind,
                    review_source_attempt_id,
                    review_content_key,
                    expected_review_revision,
                ),
                schedule=review_schedule,
            )
            if current.mission is None:
                raise LearningConflict("legacy attempt has no verified mission snapshot")
            if result is not None and (
                result.mission_id != current.mission.mission_id
                or result.purpose is not current.purpose
                or result.rules_version != current.mission.rules_version
            ):
                raise ValueError("practice result does not match its attempt snapshot")
            connection.execute(
                """UPDATE practice_attempts SET attempt_state=?,status=?,result_json=?,
                   reasons_json=?,updated_at=?,revision=revision+1
                   WHERE attempt_id=? AND owner_id=? AND revision=? AND attempt_state='QUEUED'""",
                (
                    state.value,
                    state.value,
                    _dump_json(result) if result is not None else None,
                    _dump_json(reasons),
                    _timestamp(now),
                    attempt_id,
                    owner_id,
                    expected_revision,
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise LearningConflict("practice attempt revision is stale")
            if review_schedule is not None:
                self._apply_review_schedule(
                    connection,
                    source_kind=review_binding[0],
                    attempt_id=attempt_id,
                    owner_id=owner_id,
                    source_attempt_id=review_binding[1],
                    content_key=review_binding[2],
                    schedule=review_schedule,
                    expected_revision=review_binding[3],
                    as_of=now,
                )
        record = self.get_practice_attempt(owner_id, attempt_id)
        assert record is not None
        return record

    def create_step_attempt(
        self,
        owner_id: str,
        *,
        lesson_id: str,
        lesson_version: int,
        step_id: str,
        rules_version: str,
        idempotency_key: str,
        blob_id: str,
        sha256: str,
        size_bytes: int,
        audio_content_type: str,
        round_index: int | None,
        now: datetime,
        review_source_kind: str | None = None,
        review_source_attempt_id: str | None = None,
        review_content_key: str | None = None,
        expected_review_revision: int | None = None,
        review_box: int | None = None,
    ) -> StepAttemptRecord:
        _validate_attempt_input(
            owner_id, idempotency_key, blob_id, audio_content_type, sha256, size_bytes
        )
        _validate_review_binding(
            review_source_kind,
            review_source_attempt_id,
            review_content_key,
            expected_review_revision,
            review_box,
        )
        if lesson_version < 1 or not lesson_id or not step_id or not rules_version:
            raise ValueError("step attempt must reference a complete lesson snapshot")
        created = _timestamp(now)
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT attempt_id FROM step_attempts WHERE owner_id=? AND idempotency_key=?",
                (owner_id, idempotency_key),
            ).fetchone()
            if existing:
                record = self.get_step_attempt(owner_id, existing[0])
                if record is None:
                    raise LearningConflict("idempotent step attempt reference is missing")
                if (
                    record.lesson_id != lesson_id
                    or record.lesson_version != lesson_version
                    or record.step_id != step_id
                    or record.rules_version != rules_version
                    or record.round_index != round_index
                    or record.audio is None
                    or record.audio.sha256 != sha256
                    or record.audio.content_type != audio_content_type
                    or record.review_source_kind != review_source_kind
                    or record.review_source_attempt_id != review_source_attempt_id
                    or record.review_content_key != review_content_key
                    or record.expected_review_revision != expected_review_revision
                    or record.review_box != review_box
                ):
                    raise LearningConflict("idempotency key was reused for a different request")
                return record
            step = connection.execute(
                """SELECT v.state,v.rules_version,s.kind,s.payload FROM lesson_versions v
                   JOIN lesson_steps s ON s.lesson_id=v.lesson_id AND s.version=v.version
                   WHERE v.lesson_id=? AND v.version=? AND s.step_id=?""",
                (lesson_id, lesson_version, step_id),
            ).fetchone()
            if step is None or step[0] != "published":
                raise ValueError("step attempts must reference an immutable published version")
            if step[1] != rules_version:
                raise ValueError("step rules version does not match published snapshot")
            is_free = step[2] == "free"
            if is_free != (round_index is not None):
                raise ValueError("FREE attempts require a round index; other attempts forbid it")
            if round_index is not None and (isinstance(round_index, bool) or round_index < 0):
                raise ValueError("round_index must be a nonnegative integer")
            if is_free:
                payload = json.loads(step[3])
                rounds = payload.get("rounds", []) if isinstance(payload, dict) else []
                if not isinstance(rounds, list | tuple) or round_index >= len(rounds):
                    raise ValueError("FREE attempt round index exceeds published round count")
            attempt_id = self._new_id()
            connection.execute(
                """INSERT INTO step_attempts(
                    attempt_id,owner_id,lesson_id,lesson_version,step_id,rules_version,status,
                    measurements,evidence,teacher_override,revision,created_at,idempotency_key,
                    attempt_state,result_json,reasons_json,round_index,updated_at,
                    review_source_kind,review_source_attempt_id,review_content_key,
                    expected_review_revision,review_box
                ) VALUES(?,?,?,?,?,?, 'QUEUED','{}','{}',NULL,0,?,?,'QUEUED',NULL,'[]',
                         ?,?,?,?,?,?,?)""",
                (
                    attempt_id,
                    owner_id,
                    lesson_id,
                    lesson_version,
                    step_id,
                    rules_version,
                    created,
                    idempotency_key,
                    round_index,
                    created,
                    review_source_kind,
                    review_source_attempt_id,
                    review_content_key,
                    expected_review_revision,
                    review_box,
                ),
            )
            self._insert_audio(
                owner_id,
                "step",
                attempt_id,
                blob_id,
                audio_content_type,
                sha256,
                size_bytes,
                created,
            )
        record = self.get_step_attempt(owner_id, attempt_id)
        assert record is not None
        return record

    def get_step_attempt(self, owner_id: str, attempt_id: str) -> StepAttemptRecord | None:
        rows = _dict_rows(
            self._store.connection,
            """SELECT s.*,
                      (SELECT e.new_value FROM teacher_override_events e WHERE e.owner_id=s.owner_id
                       AND e.attempt_id=s.attempt_id
                       ORDER BY e.recorded_at DESC,e.event_id DESC LIMIT 1)
                        AS latest_teacher_override,
                      a.artifact_id,a.attempt_kind,a.blob_id AS audio_blob_id,
                      a.content_type AS audio_content_type,
                      a.sha256 AS audio_sha256,a.size_bytes AS audio_size_bytes,
                      a.created_at AS audio_created_at
               FROM step_attempts s LEFT JOIN learning_audio_artifacts a
               ON a.attempt_kind='step' AND a.step_attempt_id=s.attempt_id
               WHERE s.owner_id=? AND s.attempt_id=?""",
            (owner_id, attempt_id),
        )
        return _step_record(rows[0]) if rows else None

    def get_step_attempt_by_idempotency(
        self, owner_id: str, idempotency_key: str
    ) -> StepAttemptRecord | None:
        row = self._store.connection.execute(
            "SELECT attempt_id FROM step_attempts WHERE owner_id=? AND idempotency_key=?",
            (owner_id, idempotency_key),
        ).fetchone()
        return self.get_step_attempt(owner_id, row[0]) if row else None

    def list_step_attempts(
        self,
        owner_id: str,
        *,
        lesson_id: str | None = None,
        limit: int = 50,
        before: tuple[str, str] | None = None,
    ) -> tuple[StepAttemptRecord, ...]:
        _validate_limit(limit)
        query = """SELECT s.*,
                   (SELECT e.new_value FROM teacher_override_events e WHERE e.owner_id=s.owner_id
                    AND e.attempt_id=s.attempt_id
                    ORDER BY e.recorded_at DESC,e.event_id DESC LIMIT 1)
                     AS latest_teacher_override,
                   a.artifact_id,a.attempt_kind,a.blob_id AS audio_blob_id,
                   a.content_type AS audio_content_type,
                   a.sha256 AS audio_sha256,a.size_bytes AS audio_size_bytes,
                   a.created_at AS audio_created_at
                   FROM step_attempts s LEFT JOIN learning_audio_artifacts a
                   ON a.attempt_kind='step' AND a.step_attempt_id=s.attempt_id
                   WHERE s.owner_id=?"""
        values: list[object] = [owner_id]
        if lesson_id is not None:
            query += " AND s.lesson_id=?"
            values.append(lesson_id)
        if before is not None:
            cursor_time, cursor_id = before
            _parse_timestamp(cursor_time)
            query += " AND (s.created_at<? OR (s.created_at=? AND s.attempt_id<?))"
            values.extend((cursor_time, cursor_time, cursor_id))
        query += " ORDER BY s.created_at DESC,s.attempt_id DESC LIMIT ?"
        values.append(limit)
        rows = _dict_rows(self._store.connection, query, tuple(values))
        return tuple(_step_record(row) for row in rows)

    def list_latest_step_attempts(
        self,
        owner_id: str,
        lesson_id: str,
        lesson_version: int,
        *,
        limit: int = 100,
    ) -> tuple[StepAttemptRecord, ...]:
        """Return latest attempt per step, or per step/round for FREE steps."""
        _validate_limit(limit)
        rows = _dict_rows(
            self._store.connection,
            """WITH ranked AS (
                 SELECT s.*,
                        (SELECT e.new_value FROM teacher_override_events e
                         WHERE e.owner_id=s.owner_id
                         AND e.attempt_id=s.attempt_id
                         ORDER BY e.recorded_at DESC,e.event_id DESC LIMIT 1)
                          AS latest_teacher_override,
                        a.artifact_id,a.attempt_kind,a.blob_id AS audio_blob_id,
                        a.content_type AS audio_content_type,a.sha256 AS audio_sha256,
                        a.size_bytes AS audio_size_bytes,a.created_at AS audio_created_at,
                        ROW_NUMBER() OVER (
                          PARTITION BY s.step_id,
                            CASE WHEN ls.kind='free' THEN s.round_index ELSE -1 END
                          ORDER BY s.created_at DESC,s.attempt_id DESC
                        ) AS pick
                 FROM step_attempts s
                 JOIN lesson_steps ls ON ls.lesson_id=s.lesson_id AND ls.version=s.lesson_version
                 LEFT JOIN learning_audio_artifacts a
                   ON a.attempt_kind='step' AND a.step_attempt_id=s.attempt_id
                 WHERE s.owner_id=? AND s.lesson_id=? AND s.lesson_version=?
               ) SELECT * FROM ranked WHERE pick=1
                 ORDER BY created_at DESC,attempt_id DESC LIMIT ?""",
            (owner_id, lesson_id, lesson_version, limit),
        )
        return tuple(_step_record(row) for row in rows)

    def list_lesson_progress_completions(
        self, owner_id: str, lesson_id: str, lesson_version: int
    ) -> tuple[StepCompletion, ...]:
        """Return bounded best progress per step/round across all prior attempts.

        A later failed retry does not revoke an earlier ordinary-step PASS.
        FREE progress records any positive measured voiced effort,
        regardless of the authored timing rule outcome.
        """
        if lesson_version < 1:
            raise ValueError("lesson version must be positive")
        cursor = self._store.connection.execute(
            """SELECT s.attempt_id,s.step_id,s.round_index,s.created_at,s.attempt_state,
                      s.result_json,ls.kind
               FROM step_attempts s JOIN lesson_steps ls
                 ON ls.lesson_id=s.lesson_id AND ls.version=s.lesson_version
                 AND ls.step_id=s.step_id
               WHERE s.owner_id=? AND s.lesson_id=? AND s.lesson_version=?
               ORDER BY s.created_at DESC,s.attempt_id DESC""",
            (owner_id, lesson_id, lesson_version),
        )
        best: dict[tuple[str, int | None], tuple[bool, str, StepCompletion]] = {}
        for row in cursor:
            attempt_id, step_id, round_index, created_at, state, raw, kind_value = row
            kind = StepKind(kind_value)
            status = StepAttemptStatus.RETRY
            qualifies = False
            result = None
            spoken_seconds = 0.0
            if state == LearningAttemptState.COMPLETED.value and raw:
                try:
                    result = StepResult.model_validate_json(raw)
                except (ValueError, TypeError):
                    result = None
                if result is not None and kind is not StepKind.FREE:
                    qualifies = result.status is StepResultStatus.PASS
                elif result is not None and kind is StepKind.FREE:
                    spoken_seconds = result.speaking_s
                    qualifies = spoken_seconds > 0.0
            if qualifies:
                status = StepAttemptStatus.COMPLETE
            key = (step_id, int(round_index) if round_index is not None else None)
            existing = best.get(key)
            if existing is None or (qualifies, created_at, attempt_id) > (
                existing[0],
                existing[1],
                existing[2].attempt_id,
            ):
                best[key] = (
                    qualifies,
                    created_at,
                    StepCompletion(
                        attempt_id=attempt_id,
                        step_id=step_id,
                        kind=kind,
                        status=status,
                        attempted_at=_parse_timestamp(created_at),
                        round_index=key[1],
                        speaking_s=min(spoken_seconds, MAX_STEP_SPEAKING_SECONDS)
                        if kind is StepKind.FREE and result is not None
                        else 0.0,
                    ),
                )
        return tuple(value[2] for value in best.values())

    def complete_step_attempt(
        self,
        owner_id: str,
        attempt_id: str,
        result: StepResult | None,
        *,
        state: LearningAttemptState = LearningAttemptState.COMPLETED,
        reasons: tuple[str, ...] = (),
        expected_revision: int,
        now: datetime,
        review_source_kind: str | None = None,
        review_source_attempt_id: str | None = None,
        review_content_key: str | None = None,
        review_schedule: ReviewSchedule | None = None,
        expected_review_revision: int | None = None,
    ) -> StepAttemptRecord:
        reasons = _bounded_reasons(reasons)
        if state is LearningAttemptState.COMPLETED and result is None:
            raise ValueError("completed step attempts require a typed result")
        if state is LearningAttemptState.NOT_EVALUATED and result is not None:
            raise ValueError("not-evaluated attempts cannot contain a result")
        if state is LearningAttemptState.NOT_EVALUATED and not reasons:
            raise ValueError("not-evaluated attempts require at least one reason")
        if state is LearningAttemptState.QUEUED:
            raise ValueError("an attempt cannot be completed back to queued")
        _validate_review_completion_args(
            review_source_kind,
            review_source_attempt_id,
            review_content_key,
            review_schedule,
            expected_review_revision,
        )
        if review_schedule is not None and (
            state is not LearningAttemptState.COMPLETED or result is None
        ):
            raise ValueError("review scheduling requires a completed typed step result")
        with self._store.transaction() as connection:
            current = self.get_step_attempt(owner_id, attempt_id)
            if current is None:
                raise KeyError("step attempt not found")
            if current.state is not LearningAttemptState.QUEUED:
                if (
                    current.state is state
                    and current.result == result
                    and current.reasons == reasons
                ):
                    return current
                raise LearningConflict("step attempt already completed differently")
            if current.revision != expected_revision:
                raise LearningConflict("step attempt revision is stale")
            review_binding = _resolve_attempt_review_binding(
                attempt_id=attempt_id,
                attempt_kind="step",
                stored=(
                    current.review_source_kind,
                    current.review_source_attempt_id,
                    current.review_content_key,
                    current.expected_review_revision,
                ),
                supplied=(
                    review_source_kind,
                    review_source_attempt_id,
                    review_content_key,
                    expected_review_revision,
                ),
                schedule=review_schedule,
            )
            if result is not None and (
                result.step_id != current.step_id
                or result.kind.value
                != self._step_kind(current.lesson_id, current.lesson_version, current.step_id)
                or result.round_index != current.round_index
            ):
                raise ValueError("step result does not match its immutable step snapshot")
            connection.execute(
                """UPDATE step_attempts SET attempt_state=?,status=?,result_json=?,
                   reasons_json=?,updated_at=?,revision=revision+1
                   WHERE attempt_id=? AND owner_id=? AND revision=? AND attempt_state='QUEUED'""",
                (
                    state.value,
                    state.value,
                    _dump_json(result) if result is not None else None,
                    _dump_json(reasons),
                    _timestamp(now),
                    attempt_id,
                    owner_id,
                    expected_revision,
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise LearningConflict("step attempt revision is stale")
            if review_schedule is not None:
                self._apply_review_schedule(
                    connection,
                    source_kind=review_binding[0],
                    attempt_id=attempt_id,
                    owner_id=owner_id,
                    source_attempt_id=review_binding[1],
                    content_key=review_binding[2],
                    schedule=review_schedule,
                    expected_revision=review_binding[3],
                    as_of=now,
                )
        record = self.get_step_attempt(owner_id, attempt_id)
        assert record is not None
        return record

    def append_step_override(
        self,
        actor_id: str,
        owner_id: str,
        attempt_id: str,
        *,
        new_value: str,
        reason: str,
        expected_revision: int,
        now: datetime,
    ) -> StepAttemptRecord:
        from aicefr.lessons.model import StepResultStatus

        try:
            normalized = StepResultStatus(new_value).value
        except ValueError as exc:
            raise ValueError("teacher override must be a typed step result status") from exc
        if not reason or len(reason) > 500 or any(ord(char) < 32 for char in reason):
            raise ValueError("teacher override reason must be bounded printable text")
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            record = self.get_step_attempt(owner_id, attempt_id)
            if record is None:
                raise KeyError("step attempt not found")
            if record.state is not LearningAttemptState.COMPLETED or record.result is None:
                raise LearningConflict("only completed typed results can receive an override")
            if record.revision != expected_revision:
                raise LearningConflict("step attempt revision is stale")
            event = TeacherOverrideEvent(
                event_id=self._new_id(),
                attempt_id=attempt_id,
                owner_id=owner_id,
                actor_id=actor_id,
                old_value=record.teacher_override,
                new_value=normalized,
                reason=reason,
                recorded_at=now,
            )
            connection.execute(
                """INSERT INTO teacher_override_events(
                    event_id,attempt_id,owner_id,actor_id,old_value,new_value,reason,recorded_at
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    event.event_id,
                    attempt_id,
                    owner_id,
                    actor_id,
                    event.old_value,
                    event.new_value,
                    event.reason,
                    stamp,
                ),
            )
            changed = connection.execute(
                "UPDATE step_attempts SET revision=revision+1,teacher_override=? "
                "WHERE owner_id=? AND attempt_id=? AND revision=? AND attempt_state='COMPLETED'",
                (normalized, owner_id, attempt_id, expected_revision),
            ).rowcount
            if changed != 1:
                raise LearningConflict("step attempt revision is stale")
            self._audit(actor_id, "step_attempt_overridden", attempt_id, stamp)
        updated = self.get_step_attempt(owner_id, attempt_id)
        assert updated is not None
        return updated

    def list_step_override_events(
        self, owner_id: str, attempt_id: str, *, limit: int = 20
    ) -> tuple[TeacherOverrideEvent, ...]:
        _validate_limit(limit)
        rows = self._store.connection.execute(
            """SELECT event_id,attempt_id,owner_id,actor_id,old_value,new_value,reason,recorded_at
               FROM teacher_override_events WHERE owner_id=? AND attempt_id=?
               ORDER BY recorded_at,event_id LIMIT ?""",
            (owner_id, attempt_id, limit),
        ).fetchall()
        return tuple(
            TeacherOverrideEvent(
                event_id=row[0],
                attempt_id=row[1],
                owner_id=row[2],
                actor_id=row[3],
                old_value=row[4],
                new_value=row[5],
                reason=row[6],
                recorded_at=_parse_timestamp(row[7]),
            )
            for row in rows
        )

    def get_learning_insights(
        self, owner_id: str, *, as_of: datetime, limit: int = MAX_ATTEMPT_LIST
    ) -> LearningInsightsRecord:
        _validate_limit(limit)
        stamp = _timestamp(as_of)
        practice = self._store.connection.execute(
            """SELECT SUM(attempt_state='COMPLETED'),SUM(attempt_state='NOT_EVALUATED')
               FROM (SELECT attempt_state FROM practice_attempts WHERE owner_id=?
               ORDER BY created_at DESC,attempt_id DESC LIMIT ?)""",
            (owner_id, limit),
        ).fetchone()
        steps = self._store.connection.execute(
            """SELECT SUM(attempt_state='COMPLETED'),SUM(attempt_state='NOT_EVALUATED')
               FROM (SELECT attempt_state FROM step_attempts WHERE owner_id=?
               ORDER BY created_at DESC,attempt_id DESC LIMIT ?)""",
            (owner_id, limit),
        ).fetchone()
        audio_count = self._store.connection.execute(
            """SELECT COUNT(*) FROM (SELECT artifact_id FROM learning_audio_artifacts
               WHERE owner_id=? ORDER BY created_at DESC,artifact_id DESC LIMIT ?)""",
            (owner_id, limit),
        ).fetchone()[0]
        due_count = self._store.connection.execute(
            """SELECT COUNT(*) FROM (
                 SELECT review_id FROM review_items WHERE owner_id=? AND state='due' AND
                 julianday(due_at)<=julianday(?)
                 UNION ALL
                 SELECT review_id FROM step_review_items WHERE owner_id=? AND state='due' AND
                 julianday(due_at)<=julianday(?)
                 LIMIT ?
               )""",
            (owner_id, stamp, owner_id, stamp, limit),
        ).fetchone()[0]
        return LearningInsightsRecord(
            owner_id=owner_id,
            practice_completed=int(practice[0] or 0),
            practice_not_evaluated=int(practice[1] or 0),
            step_completed=int(steps[0] or 0),
            step_not_evaluated=int(steps[1] or 0),
            audio_artifacts=int(audio_count),
            due_reviews=int(due_count),
            as_of=as_of,
        )

    def import_draft_path_bundle(
        self, actor_id: str, imported, *, expected_revision: int = 0, now: datetime
    ) -> LearningPath:
        """Atomically import a fully validated, media-free path draft bundle."""
        if expected_revision != 0:
            raise LearningConflict("new path bundle imports require revision zero")
        path = imported.path
        lessons = tuple(imported.lessons)
        unit_ids = {unit.unit_id for unit in path.units}
        lesson_by_id = {lesson.lesson_id: lesson for lesson in lessons}
        expected_lessons = [lesson_id for unit in path.units for lesson_id in unit.lesson_ids]
        if len(unit_ids) != len(path.units) or len(lesson_by_id) != len(lessons):
            raise ValueError("import bundle contains duplicate unit or lesson ids")
        if len(set(expected_lessons)) != len(expected_lessons) or set(expected_lessons) != set(
            lesson_by_id
        ):
            raise ValueError("every imported lesson must belong to exactly one ordered unit")
        if any(not lesson.steps for lesson in lessons):
            raise ValueError("imported draft lesson must contain at least one typed step")
        stamp = _timestamp(now)
        with self._store.transaction() as connection:
            self._require_author(actor_id)
            identifiers = [path.path_id, *[unit.unit_id for unit in path.units], *lesson_by_id]
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("imported path, unit, and lesson identifiers must be unique")
            for identifier in identifiers:
                if connection.execute(
                    """SELECT 1 FROM learning_paths WHERE path_id=? UNION ALL
                       SELECT 1 FROM learning_units WHERE unit_id=? UNION ALL
                       SELECT 1 FROM learning_lessons WHERE lesson_id=? LIMIT 1""",
                    (identifier, identifier, identifier),
                ).fetchone():
                    raise LearningConflict("imported identifier already exists")
            connection.execute(
                """INSERT INTO learning_paths(
                    path_id,title,description,state,revision,created_at,updated_at,
                    band_from,band_to,content_version,seed_owned
                ) VALUES(?,?,?,'draft',1,?,?,?,?,?,0)""",
                (
                    path.path_id,
                    path.title,
                    path.description,
                    stamp,
                    stamp,
                    path.band_from.value,
                    path.band_to.value,
                    path.content_version,
                ),
            )
            for unit in path.units:
                connection.execute(
                    """INSERT INTO learning_units(
                        unit_id,path_id,title,ordinal,band,topic,learning_function,revision,seed_owned
                    ) VALUES(?,?,?,?,?,?,?,?,0)""",
                    (
                        unit.unit_id,
                        path.path_id,
                        unit.title,
                        unit.ordinal,
                        unit.band.value,
                        unit.topic.value if unit.topic else None,
                        unit.learning_function,
                        1,
                    ),
                )
                for lesson_id in unit.lesson_ids:
                    lesson = lesson_by_id[lesson_id]
                    connection.execute(
                        """INSERT INTO learning_lessons(
                            lesson_id,unit_id,title,active_version,created_at,summary,band,revision,
                            content_version,ordinal,seed_owned
                        ) VALUES(?,?,?,NULL,?,?,?,?,?, ?,0)""",
                        (
                            lesson.lesson_id,
                            unit.unit_id,
                            lesson.title,
                            stamp,
                            lesson.summary,
                            lesson.band.value,
                            1,
                            lesson.content_version,
                            unit.lesson_ids.index(lesson_id) + 1,
                        ),
                    )
                    rules_version = lesson.steps[0].rules_version
                    connection.execute(
                        """INSERT INTO lesson_versions(
                            lesson_id,version,state,rules_version,published_at,created_at,title,
                            summary,band,revision,content_hash
                        ) VALUES(?,1,'draft',?,NULL,?,?,?,?,1,NULL)""",
                        (
                            lesson.lesson_id,
                            rules_version,
                            stamp,
                            lesson.title,
                            lesson.summary,
                            lesson.band.value,
                        ),
                    )
                    for step in lesson.steps:
                        connection.execute(
                            """INSERT INTO lesson_steps(
                                lesson_id,version,step_id,kind,ordinal,payload,stage,instruction,rules_version
                            ) VALUES(?,1,?,?,?,?,?,?,?)""",
                            (
                                lesson.lesson_id,
                                step.step_id,
                                step.kind.value,
                                step.ordinal,
                                _dump_json(step.payload),
                                step.stage.value,
                                step.instruction,
                                step.rules_version,
                            ),
                        )
            self._audit(actor_id, "path_bundle_imported", path.path_id, stamp)
        result = self.get_path(path.path_id, published_only=False)
        assert result is not None
        return result

    def export_path_bundle(self, path_id: str, *, published_only: bool = False):
        """Project a media-free ordered bundle; legacy untyped snapshots are refused."""
        from aicefr.lessons.authoring import LearningPathBundle, LessonBundleEntry

        path = self.get_path(path_id, published_only=published_only)
        if path is None:
            return None
        entries: list[LessonBundleEntry] = []
        for unit in path.units:
            for lesson_id in unit.lesson_ids:
                if published_only:
                    active = self._store.connection.execute(
                        "SELECT active_version FROM learning_lessons WHERE lesson_id=?",
                        (lesson_id,),
                    ).fetchone()
                    value = (
                        self.get_lesson(lesson_id, version=active[0], published_only=True)
                        if active and active[0] is not None
                        else None
                    )
                else:
                    value = self.get_lesson(lesson_id, published_only=False)
                if not isinstance(value, (Lesson, PublishedLessonVersion)):
                    raise ValueError("path bundle contains a legacy or missing lesson snapshot")
                entries.append(LessonBundleEntry(unit_id=unit.unit_id, lesson=value))
        return LearningPathBundle(path=path, lessons=tuple(entries))

    def upsert_review_item(
        self,
        owner_id: str,
        source_attempt_id: str,
        content_key: str,
        schedule: ReviewSchedule,
        *,
        now: datetime,
    ) -> ReviewItemRecord:
        if not owner_id or not content_key or len(content_key) > 160:
            raise ValueError("review identity must be bounded and non-empty")
        if not 1 <= schedule.box <= 4:
            raise ValueError("review box must be between 1 and 4")
        updated_at = _timestamp(now)
        with self._store.transaction() as connection:
            source = connection.execute(
                "SELECT 1 FROM practice_attempts WHERE owner_id=? AND attempt_id=?",
                (owner_id, source_attempt_id),
            ).fetchone()
            if source is None:
                raise KeyError("review source attempt not found")
            self._write_review_schedule(
                connection,
                "practice",
                owner_id,
                source_attempt_id,
                content_key,
                schedule,
                updated_at,
            )
        row = self._store.connection.execute(
            "SELECT review_id,owner_id,source_attempt,content_key,box,due_at,state,updated_at,"
            "'practice',revision "
            "FROM review_items WHERE owner_id=? AND source_attempt=? AND content_key=?",
            (owner_id, source_attempt_id, content_key),
        ).fetchone()
        assert row is not None
        return _review_record(row)

    def upsert_step_review_item(
        self,
        owner_id: str,
        source_attempt_id: str,
        content_key: str,
        schedule: ReviewSchedule,
        *,
        now: datetime,
    ) -> ReviewItemRecord:
        _validate_review_key(owner_id, content_key, schedule)
        updated_at = _timestamp(now)
        with self._store.transaction() as connection:
            source = connection.execute(
                "SELECT 1 FROM step_attempts WHERE owner_id=? AND attempt_id=?",
                (owner_id, source_attempt_id),
            ).fetchone()
            if source is None:
                raise KeyError("step review source attempt not found")
            self._write_review_schedule(
                connection, "step", owner_id, source_attempt_id, content_key, schedule, updated_at
            )
        row = self._store.connection.execute(
            """SELECT review_id,owner_id,source_step_attempt,content_key,box,due_at,state,
               updated_at,revision FROM step_review_items
               WHERE owner_id=? AND source_step_attempt=? AND content_key=?""",
            (owner_id, source_attempt_id, content_key),
        ).fetchone()
        assert row is not None
        return _review_record((*row[:8], "step", row[8]))

    def _write_review_schedule(
        self,
        connection,
        source_kind: str,
        owner_id: str,
        source_attempt_id: str,
        content_key: str,
        schedule: ReviewSchedule,
        updated_at: str,
    ) -> None:
        table, source_column = (
            ("review_items", "source_attempt")
            if source_kind == "practice"
            else ("step_review_items", "source_step_attempt")
        )
        due_at = _timestamp(schedule.due_at) if schedule.due_at else ""
        connection.execute(
            f"""INSERT INTO {table}(
                review_id,owner_id,{source_column},content_key,box,due_at,state,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(owner_id,{source_column},content_key) DO UPDATE SET
                box=excluded.box,due_at=excluded.due_at,state=excluded.state,
                revision={table}.revision+1,updated_at=excluded.updated_at""",
            (
                self._new_id(),
                owner_id,
                source_attempt_id,
                content_key,
                schedule.box,
                due_at,
                "done" if schedule.done else "due",
                updated_at,
            ),
        )

    def _apply_review_schedule(
        self,
        connection,
        *,
        source_kind: str,
        attempt_id: str,
        owner_id: str,
        source_attempt_id: str,
        content_key: str | None,
        schedule: ReviewSchedule,
        expected_revision: int | None,
        as_of: datetime,
    ) -> None:
        assert content_key is not None
        table, source_column = (
            ("review_items", "source_attempt")
            if source_kind == "practice"
            else ("step_review_items", "source_step_attempt")
        )
        current_attempt_id = connection.execute(
            "SELECT attempt_id FROM practice_attempts WHERE owner_id=? AND attempt_id=?"
            if source_kind == "practice"
            else "SELECT attempt_id FROM step_attempts WHERE owner_id=? AND attempt_id=?",
            (owner_id, source_attempt_id),
        ).fetchone()
        if current_attempt_id is None:
            raise LearningConflict("review source attempt does not belong to learner")
        row = connection.execute(
            f"SELECT review_id,box,due_at,state,revision FROM {table} "
            f"WHERE owner_id=? AND {source_column}=? AND content_key=?",
            (owner_id, source_attempt_id, content_key),
        ).fetchone()
        if row is None:
            # First review schedules the just-completed result. A retry/review
            # must match a durable due occurrence and its revision.
            if expected_revision is not None or source_attempt_id != attempt_id:
                raise LearningConflict("review schedule changed before completion")
            self._write_review_schedule(
                connection,
                source_kind,
                owner_id,
                source_attempt_id,
                content_key,
                schedule,
                _timestamp(as_of),
            )
            return
        if expected_revision is None or row[4] != expected_revision:
            raise LearningConflict("review schedule revision is stale")
        if row[3] != "due" or not row[2] or _parse_timestamp(row[2]) > as_of:
            raise LearningConflict("review item is not currently due")
        due_at = _timestamp(schedule.due_at) if schedule.due_at else ""
        changed = connection.execute(
            f"UPDATE {table} SET box=?,due_at=?,state=?,revision=revision+1,updated_at=? "
            f"WHERE review_id=? AND revision=? AND state='due' AND due_at=?",
            (
                schedule.box,
                due_at,
                "done" if schedule.done else "due",
                _timestamp(as_of),
                row[0],
                expected_revision,
                row[2],
            ),
        ).rowcount
        if changed != 1:
            raise LearningConflict("review schedule was completed concurrently")

    def list_due_reviews(
        self, owner_id: str, *, as_of: datetime, limit: int = 50
    ) -> tuple[ReviewItemRecord, ...]:
        _validate_limit(limit)
        now = _timestamp(as_of)
        rows = self._store.connection.execute(
            """SELECT review_id,owner_id,source_attempt,content_key,box,due_at,state,updated_at,
                      'practice' AS source_kind,revision
               FROM review_items
               WHERE owner_id=? AND state='due' AND julianday(due_at)<=julianday(?)
               UNION ALL
               SELECT review_id,owner_id,source_step_attempt,content_key,box,due_at,state,
                      updated_at,
                      'step' AS source_kind,revision
               FROM step_review_items
               WHERE owner_id=? AND state='due' AND julianday(due_at)<=julianday(?)
               ORDER BY due_at,review_id LIMIT ?""",
            (owner_id, now, owner_id, now, limit),
        ).fetchall()
        return tuple(_review_record(row) for row in rows)

    def get_review_item(self, owner_id: str, review_id: str) -> ReviewItemRecord | None:
        """Look up one owned review by stable ID, including advanced or done items."""
        row = self._store.connection.execute(
            """SELECT review_id,owner_id,source_attempt,content_key,box,due_at,state,updated_at,
                      'practice' AS source_kind,revision
               FROM review_items WHERE owner_id=? AND review_id=?
               UNION ALL
               SELECT review_id,owner_id,source_step_attempt,content_key,box,due_at,state,
                      updated_at,'step' AS source_kind,revision
               FROM step_review_items WHERE owner_id=? AND review_id=?
               LIMIT 1""",
            (owner_id, review_id, owner_id, review_id),
        ).fetchone()
        return _review_record(row) if row else None

    def get_due_review_item(
        self, owner_id: str, review_id: str, *, as_of: datetime
    ) -> ReviewItemRecord | None:
        """Look up one exact owned review if it is due, without paging through others."""
        now = _timestamp(as_of)
        row = self._store.connection.execute(
            """SELECT review_id,owner_id,source_attempt,content_key,box,due_at,state,updated_at,
                      'practice' AS source_kind,revision
               FROM review_items WHERE owner_id=? AND review_id=? AND state='due'
                 AND julianday(due_at)<=julianday(?)
               UNION ALL
               SELECT review_id,owner_id,source_step_attempt,content_key,box,due_at,state,
                      updated_at,'step' AS source_kind,revision
               FROM step_review_items WHERE owner_id=? AND review_id=? AND state='due'
                 AND julianday(due_at)<=julianday(?)
               LIMIT 1""",
            (owner_id, review_id, now, owner_id, review_id, now),
        ).fetchone()
        return _review_record(row) if row else None

    def delete_practice_attempt(
        self, owner_id: str, attempt_id: str, *, expected_revision: int, now: datetime
    ) -> bool:
        with self._store.transaction() as connection:
            record = self.get_practice_attempt(owner_id, attempt_id)
            if record is None:
                return False
            if record.revision != expected_revision:
                raise LearningConflict("practice attempt revision is stale")
            self._enqueue_blob_cleanup(record.audio, owner_id, now)
            connection.execute(
                "DELETE FROM practice_attempts WHERE owner_id=? AND attempt_id=? AND revision=?",
                (owner_id, attempt_id, expected_revision),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise LearningConflict("practice attempt revision is stale")
        return True

    def delete_step_attempt(
        self, owner_id: str, attempt_id: str, *, expected_revision: int, now: datetime
    ) -> bool:
        with self._store.transaction() as connection:
            record = self.get_step_attempt(owner_id, attempt_id)
            if record is None:
                return False
            if record.revision != expected_revision:
                raise LearningConflict("step attempt revision is stale")
            self._enqueue_blob_cleanup(record.audio, owner_id, now)
            connection.execute(
                "DELETE FROM step_attempts WHERE owner_id=? AND attempt_id=? AND revision=?",
                (owner_id, attempt_id, expected_revision),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise LearningConflict("step attempt revision is stale")
        return True

    def delete_owner_learning_data(self, owner_id: str, *, now: datetime) -> None:
        """Delete owner attempts/reviews and audit events under an erasure intent."""
        created = _timestamp(now)
        with self._store.transaction() as connection:
            connection.execute(
                """INSERT INTO cleanup_intents(
                    intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,
                    created_at,updated_at,last_reason
                ) VALUES(?,?, 'privacy_erasure',?,'running',0,?,?,?,NULL)
                ON CONFLICT(resource_kind,resource_id) DO UPDATE SET
                state='running',updated_at=excluded.updated_at""",
                (
                    self._new_id(),
                    owner_id,
                    f"learning:{owner_id}",
                    now.timestamp(),
                    created,
                    created,
                ),
            )
            practice_rows = _dict_rows(
                connection,
                "SELECT attempt_id FROM practice_attempts WHERE owner_id=?",
                (owner_id,),
            )
            step_rows = _dict_rows(
                connection,
                "SELECT attempt_id FROM step_attempts WHERE owner_id=?",
                (owner_id,),
            )
            for row in connection.execute(
                "SELECT blob_id FROM learning_audio_artifacts WHERE owner_id=?", (owner_id,)
            ).fetchall():
                self._enqueue_blob_cleanup_by_id(owner_id, row[0], now)
            connection.execute("DELETE FROM review_items WHERE owner_id=?", (owner_id,))
            for row in practice_rows:
                connection.execute(
                    "DELETE FROM practice_attempts WHERE owner_id=? AND attempt_id=?",
                    (owner_id, row["attempt_id"]),
                )
            for row in step_rows:
                connection.execute(
                    "DELETE FROM step_attempts WHERE owner_id=? AND attempt_id=?",
                    (owner_id, row["attempt_id"]),
                )
            connection.execute("DELETE FROM teacher_override_events WHERE owner_id=?", (owner_id,))

    def export_owner_learning_data(self, owner_id: str) -> dict[str, object]:
        """Return a bounded, owner-only learning export with typed round history."""
        return {
            "practice_attempts": [
                _practice_export(record)
                for record in self.list_practice_attempts(owner_id, limit=MAX_ATTEMPT_LIST)
            ],
            "step_attempts": [
                _step_export(record)
                for record in self.list_step_attempts(owner_id, limit=MAX_ATTEMPT_LIST)
            ],
            "review_items": [
                _review_record(row)
                for row in self._store.connection.execute(
                    """SELECT review_id,owner_id,source_attempt,content_key,box,due_at,state,
                              updated_at,'practice',revision
                       FROM review_items WHERE owner_id=? ORDER BY updated_at,review_id LIMIT ?""",
                    (owner_id, MAX_ATTEMPT_LIST),
                ).fetchall()
            ]
            + [
                _review_record((*row[:8], "step", row[8]))
                for row in self._store.connection.execute(
                    """SELECT review_id,owner_id,source_step_attempt,content_key,box,due_at,state,
                              updated_at,revision FROM step_review_items WHERE owner_id=?
                       ORDER BY updated_at,review_id LIMIT ?""",
                    (owner_id, MAX_ATTEMPT_LIST),
                ).fetchall()
            ],
        }

    def _queue_step_media_cleanup(
        self, connection, owner_id: str, lesson_id: str, version: int, step_id: str, now: datetime
    ) -> None:
        for row in connection.execute(
            "SELECT blob_id FROM learning_media "
            "WHERE lesson_id=? AND lesson_version=? AND step_id=?",
            (lesson_id, version, step_id),
        ).fetchall():
            self._enqueue_blob_cleanup_by_id(owner_id, row[0], now)

    def _queue_lesson_media_cleanup(
        self, connection, owner_id: str, lesson_id: str, now: datetime
    ) -> None:
        for row in connection.execute(
            "SELECT blob_id FROM learning_media WHERE lesson_id=?", (lesson_id,)
        ).fetchall():
            self._enqueue_blob_cleanup_by_id(owner_id, row[0], now)
        connection.execute("DELETE FROM learning_media WHERE lesson_id=?", (lesson_id,))

    def _queue_unit_media_cleanup(
        self, connection, owner_id: str, unit_id: str, now: datetime
    ) -> None:
        for row in connection.execute(
            """SELECT m.blob_id FROM learning_media m JOIN learning_lessons l
               ON l.lesson_id=m.lesson_id WHERE l.unit_id=?""",
            (unit_id,),
        ).fetchall():
            self._enqueue_blob_cleanup_by_id(owner_id, row[0], now)
        connection.execute(
            "DELETE FROM learning_media WHERE lesson_id IN "
            "(SELECT lesson_id FROM learning_lessons WHERE unit_id=?)",
            (unit_id,),
        )

    def _queue_path_media_cleanup(
        self, connection, owner_id: str, path_id: str, now: datetime
    ) -> None:
        for row in connection.execute(
            """SELECT m.blob_id FROM learning_media m JOIN learning_lessons l
               ON l.lesson_id=m.lesson_id JOIN learning_units u ON u.unit_id=l.unit_id
               WHERE u.path_id=?""",
            (path_id,),
        ).fetchall():
            self._enqueue_blob_cleanup_by_id(owner_id, row[0], now)
        connection.execute(
            "DELETE FROM learning_media WHERE lesson_id IN "
            "(SELECT l.lesson_id FROM learning_lessons l "
            "JOIN learning_units u ON u.unit_id=l.unit_id WHERE u.path_id=?)",
            (path_id,),
        )

    def _enqueue_blob_cleanup(
        self, audio: LearningAudioArtifact | None, owner_id: str, now: datetime
    ) -> None:
        if audio is not None:
            self._enqueue_blob_cleanup_by_id(owner_id, audio.blob_id, now)

    def _enqueue_blob_cleanup_by_id(self, owner_id: str, blob_id: str, now: datetime) -> None:
        stamp = _timestamp(now)
        epoch = now.timestamp()
        self._store.connection.execute(
            """INSERT INTO cleanup_intents(
                intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,
                created_at,updated_at,last_reason
            ) VALUES(?,?, 'blob',?,'pending',0,?,?,?,NULL)
            ON CONFLICT(resource_kind,resource_id) DO NOTHING""",
            (self._new_id(), owner_id, blob_id, epoch, stamp, stamp),
        )

    def list_assessment_evidence(
        self, owner_id: str, *, limit: int = 20
    ) -> tuple[RecommendationEvidence, ...]:
        """Return a bounded recent projection of eligible persisted reports.

        The SQL join scopes before loading report JSON, so a caller cannot use
        this port to enumerate another learner's response identifiers.
        Malformed or legacy reports without the required estimate are omitted.
        """
        if not owner_id or len(owner_id) > 160:
            raise ValueError("owner_id must be a bounded non-empty identifier")
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_ASSESSMENT_EVIDENCE
        ):
            raise ValueError(f"limit must be between 1 and {MAX_ASSESSMENT_EVIDENCE}")

        rows = self._store.connection.execute(
            """SELECT r.response_id, r.created_at, d.report_json
               FROM responses AS r
               JOIN diagnostic_reports AS d ON d.response_id = r.response_id
               WHERE r.owner_id = ?
               ORDER BY r.created_at DESC, r.response_id DESC
               LIMIT ?""",
            (owner_id, limit),
        ).fetchall()
        result: list[RecommendationEvidence] = []
        for response_id, created_at_raw, report_json in rows:
            try:
                report = DiagnosticReport.model_validate_json(report_json)
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                if report.response_id != response_id:
                    continue
                if report.assessment_status.value not in {"ESTIMATED", "REVIEW_REQUIRED"}:
                    continue
                if report.overall_score is None or report.overall_band is None:
                    continue
                result.append(
                    RecommendationEvidence(
                        response_id=response_id,
                        created_at=created_at,
                        status=report.assessment_status,
                        overall_score=report.overall_score,
                        overall_band=report.overall_band,
                        criteria=report.criteria,
                    )
                )
            except (AttributeError, TypeError, ValueError, ValidationError, RecursionError):
                # Historical or corrupt reports are not recommendation evidence.
                continue
        return tuple(result)

    def _insert_audio(
        self,
        owner_id: str,
        attempt_kind: str,
        attempt_id: str,
        blob_id: str,
        audio_content_type: str,
        sha256: str,
        size_bytes: int,
        created_at: str,
    ) -> None:
        self._store.connection.execute(
            """INSERT INTO learning_audio_artifacts(
                artifact_id,owner_id,attempt_kind,practice_attempt_id,step_attempt_id,
                blob_id,content_type,sha256,size_bytes,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                self._new_id(),
                owner_id,
                attempt_kind,
                attempt_id if attempt_kind == "practice" else None,
                attempt_id if attempt_kind == "step" else None,
                blob_id,
                audio_content_type,
                sha256,
                size_bytes,
                created_at,
            ),
        )

    def _new_id(self) -> str:
        value = self._id_factory()
        return value.hex if hasattr(value, "hex") else str(value)

    def _step_kind(self, lesson_id: str, version: int, step_id: str) -> str:
        row = self._store.connection.execute(
            "SELECT kind FROM lesson_steps WHERE lesson_id=? AND version=? AND step_id=?",
            (lesson_id, version, step_id),
        ).fetchone()
        if row is None:
            raise KeyError("published step not found")
        return row[0]


def _validate_attempt_input(
    owner_id: str,
    idempotency_key: str,
    blob_id: str,
    content_type: str,
    sha256: str,
    size_bytes: int,
) -> None:
    if not owner_id or len(owner_id) > 160:
        raise ValueError("owner_id must be a bounded non-empty identifier")
    if (
        not idempotency_key
        or len(idempotency_key) > 128
        or any(ord(c) < 32 for c in idempotency_key)
    ):
        raise ValueError("idempotency key must be bounded printable text")
    if not blob_id or len(blob_id) > 256 or any(ord(c) < 32 for c in blob_id):
        raise ValueError("blob_id must be bounded printable text")
    if not _SHA256.fullmatch(sha256):
        raise ValueError("audio SHA-256 must be lowercase hexadecimal")
    if (
        not isinstance(content_type, str)
        or not 3 <= len(content_type) <= 128
        or any(ord(c) < 32 for c in content_type)
    ):
        raise ValueError("audio content type must be bounded printable text")
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or not 0 < size_bytes <= 50_000_000
    ):
        raise ValueError("audio size is outside the storage limit")


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ATTEMPT_LIST:
        raise ValueError(f"limit must be between 1 and {MAX_ATTEMPT_LIST}")


def _validate_media(
    blob_id: str,
    content_type: str,
    sha256: str,
    size_bytes: int,
    media_kind: str,
) -> None:
    if not blob_id or len(blob_id) > 256 or any(ord(char) < 32 for char in blob_id):
        raise ValueError("media blob id must be bounded printable text")
    if (
        not isinstance(content_type, str)
        or not 3 <= len(content_type) <= 128
        or any(ord(char) < 32 for char in content_type)
    ):
        raise ValueError("media content type must be bounded printable text")
    if not _SHA256.fullmatch(sha256):
        raise ValueError("media SHA-256 must be lowercase hexadecimal")
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or not 0 < size_bytes <= 50_000_000
    ):
        raise ValueError("media size is outside the storage limit")
    if not media_kind or len(media_kind) > 40 or not re.fullmatch(r"[a-z][a-z0-9_]*", media_kind):
        raise ValueError("media kind must be a bounded stable identifier")


def _dict_rows(connection, sql: str, params: tuple[object, ...]) -> list[dict[str, object]]:
    cursor = connection.execute(sql, params)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def _audio_record(row: dict[str, object]) -> LearningAudioArtifact | None:
    if row.get("artifact_id") is None:
        return None
    return LearningAudioArtifact(
        artifact_id=str(row["artifact_id"]),
        owner_id=str(row["owner_id"]),
        attempt_kind=str(row["attempt_kind"]),
        attempt_id=str(row["attempt_id"]),
        blob_id=str(row["audio_blob_id"]),
        content_type=str(row["audio_content_type"]),
        sha256=str(row["audio_sha256"]),
        size_bytes=int(row["audio_size_bytes"]),
        created_at=_parse_timestamp(str(row["audio_created_at"])),
    )


def _practice_record(row: dict[str, object]) -> PracticeAttemptRecord:
    snapshot = str(row["mission_snapshot"])
    mission = None if snapshot == "{}" else PracticeMission.model_validate_json(snapshot)
    return PracticeAttemptRecord(
        attempt_id=str(row["attempt_id"]),
        owner_id=str(row["owner_id"]),
        purpose=PracticePurpose(str(row["purpose"])),
        mission=mission,
        state=LearningAttemptState(str(row["attempt_state"])),
        result=_decode_json(row["result_json"], PracticeResult),  # type: ignore[arg-type]
        reasons=tuple(json.loads(str(row["reasons_json"]))),
        audio=_audio_record(row),
        revision=int(row["revision"]),
        created_at=_parse_timestamp(str(row["created_at"])),
        updated_at=_parse_timestamp(str(row["updated_at"])),
        review_source_kind=str(row["review_source_kind"]) if row["review_source_kind"] else None,
        review_source_attempt_id=(
            str(row["review_source_attempt_id"]) if row["review_source_attempt_id"] else None
        ),
        review_content_key=str(row["review_content_key"]) if row["review_content_key"] else None,
        expected_review_revision=(
            int(row["expected_review_revision"])
            if row["expected_review_revision"] is not None
            else None
        ),
        review_box=int(row["review_box"]) if row["review_box"] is not None else None,
    )


def _step_record(row: dict[str, object]) -> StepAttemptRecord:
    return StepAttemptRecord(
        attempt_id=str(row["attempt_id"]),
        owner_id=str(row["owner_id"]),
        lesson_id=str(row["lesson_id"]),
        lesson_version=int(row["lesson_version"]),
        step_id=str(row["step_id"]),
        rules_version=str(row["rules_version"]),
        state=LearningAttemptState(str(row["attempt_state"])),
        result=_decode_json(row["result_json"], StepResult),  # type: ignore[arg-type]
        reasons=tuple(json.loads(str(row["reasons_json"]))),
        audio=_audio_record(row),
        revision=int(row["revision"]),
        round_index=int(row["round_index"]) if row["round_index"] is not None else None,
        teacher_override=(
            str(row["latest_teacher_override"])
            if row.get("latest_teacher_override") is not None
            else str(row["teacher_override"])
            if row.get("teacher_override") is not None
            else None
        ),
        created_at=_parse_timestamp(str(row["created_at"])),
        updated_at=_parse_timestamp(str(row["updated_at"])),
        review_source_kind=str(row["review_source_kind"]) if row["review_source_kind"] else None,
        review_source_attempt_id=(
            str(row["review_source_attempt_id"]) if row["review_source_attempt_id"] else None
        ),
        review_content_key=str(row["review_content_key"]) if row["review_content_key"] else None,
        expected_review_revision=(
            int(row["expected_review_revision"])
            if row["expected_review_revision"] is not None
            else None
        ),
        review_box=int(row["review_box"]) if row["review_box"] is not None else None,
    )


def _review_record(row: tuple[object, ...]) -> ReviewItemRecord:
    review_id, owner_id, source_attempt, content_key, box, due_at, state, updated_at = row[:8]
    source_kind = str(row[8]) if len(row) > 8 else "practice"
    return ReviewItemRecord(
        review_id=str(review_id),
        owner_id=str(owner_id),
        source_attempt_id=str(source_attempt),
        content_key=str(content_key),
        box=int(box),
        due_at=_parse_timestamp(str(due_at)) if due_at else None,
        done=str(state) == "done",
        updated_at=_parse_timestamp(str(updated_at)),
        source_kind=source_kind,
        revision=int(row[9]) if len(row) > 9 else 0,
    )


def _validate_review_key(owner_id: str, content_key: str, schedule: ReviewSchedule) -> None:
    if not owner_id or len(owner_id) > 160 or not content_key or len(content_key) > 160:
        raise ValueError("review identity must be bounded and non-empty")
    if isinstance(schedule.box, bool) or not 1 <= schedule.box <= 4:
        raise ValueError("review box must be between 1 and 4")
    if schedule.due_at is not None:
        _timestamp(schedule.due_at)


def _validate_review_completion_args(
    source_kind: str | None,
    source_attempt_id: str | None,
    content_key: str | None,
    schedule: ReviewSchedule | None,
    expected_revision: int | None,
) -> None:
    if schedule is None:
        if any(
            value is not None
            for value in (source_kind, source_attempt_id, content_key, expected_revision)
        ):
            raise ValueError("review source and revision require a review schedule")
        return
    if source_kind is not None and source_kind not in {"practice", "step"}:
        raise ValueError("review source kind is invalid")
    if source_attempt_id is not None and len(source_attempt_id) > 128:
        raise ValueError("review source attempt id is invalid")
    if expected_revision is not None and (
        isinstance(expected_revision, bool) or expected_revision < 0
    ):
        raise ValueError("review expected revision must be nonnegative")
    if content_key is not None:
        _validate_review_key("owner", content_key, schedule)


def _validate_review_binding(
    source_kind: str | None,
    source_attempt_id: str | None,
    content_key: str | None,
    expected_revision: int | None,
    review_box: int | None,
) -> None:
    provided = (source_kind, source_attempt_id, content_key, expected_revision, review_box)
    if all(value is None for value in provided):
        return
    if (
        source_kind not in {"practice", "step"}
        or not source_attempt_id
        or not content_key
        or expected_revision is None
        or review_box is None
    ):
        raise ValueError("review request binding requires source kind, attempt id, and content key")
    if len(source_attempt_id) > 128 or len(content_key) > 160:
        raise ValueError("review request binding exceeds its limit")
    if expected_revision is not None and (
        isinstance(expected_revision, bool) or expected_revision < 0
    ):
        raise ValueError("expected review revision must be nonnegative")
    if isinstance(review_box, bool) or not 1 <= review_box <= 4:
        raise ValueError("review box must be between 1 and 4")


def _resolve_attempt_review_binding(
    *,
    attempt_id: str,
    attempt_kind: str,
    stored: tuple[str | None, str | None, str | None, int | None],
    supplied: tuple[str | None, str | None, str | None, int | None],
    schedule: ReviewSchedule | None,
) -> tuple[str, str, str, int | None] | None:
    stored_kind, stored_source_id, stored_content_key, stored_expected_revision = stored
    passed_kind, passed_source_id, passed_content_key, passed_expected_revision = supplied
    if schedule is None:
        if any(
            value is not None
            for value in (
                passed_kind,
                passed_source_id,
                passed_content_key,
                passed_expected_revision,
            )
        ):
            raise LearningConflict("review completion does not match its queued request")
        return None
    if stored_kind is None and stored_source_id is None and stored_content_key is None:
        if passed_kind not in {None, attempt_kind} or passed_source_id not in {None, attempt_id}:
            raise LearningConflict("first review must be scheduled against its own attempt")
        if passed_expected_revision is not None or not passed_content_key:
            raise LearningConflict("first review requires its content key and no prior revision")
        return attempt_kind, attempt_id, passed_content_key, None
    resolved = (
        stored_kind,
        stored_source_id,
        stored_content_key,
        stored_expected_revision,
    )
    supplied = (passed_kind, passed_source_id, passed_content_key, passed_expected_revision)
    if any(
        value is not None and value != target
        for value, target in zip(supplied, resolved, strict=True)
    ):
        raise LearningConflict("review completion does not match its queued request fingerprint")
    if not all(resolved[:3]):
        raise LearningConflict("queued review request has incomplete binding")
    return resolved  # type: ignore[return-value]


def _practice_export(record: PracticeAttemptRecord) -> dict[str, object]:
    return {
        "attempt_id": record.attempt_id,
        "purpose": record.purpose.value,
        "mission": record.mission.model_dump(mode="json") if record.mission else None,
        "state": record.state.value,
        "result": record.result.model_dump(mode="json") if record.result else None,
        "reasons": list(record.reasons),
        "audio": record.audio.__dict__ if record.audio else None,
        "revision": record.revision,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "review_source_kind": record.review_source_kind,
        "review_source_attempt_id": record.review_source_attempt_id,
        "review_content_key": record.review_content_key,
        "expected_review_revision": record.expected_review_revision,
        "review_box": record.review_box,
    }


def _step_export(record: StepAttemptRecord) -> dict[str, object]:
    return {
        "attempt_id": record.attempt_id,
        "lesson_id": record.lesson_id,
        "lesson_version": record.lesson_version,
        "step_id": record.step_id,
        "rules_version": record.rules_version,
        "round_index": record.round_index,
        "state": record.state.value,
        "result": record.result.model_dump(mode="json") if record.result else None,
        "reasons": list(record.reasons),
        "audio": record.audio.__dict__ if record.audio else None,
        "revision": record.revision,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "review_source_kind": record.review_source_kind,
        "review_source_attempt_id": record.review_source_attempt_id,
        "review_content_key": record.review_content_key,
        "expected_review_revision": record.expected_review_revision,
        "review_box": record.review_box,
        "teacher_override": record.teacher_override,
    }
