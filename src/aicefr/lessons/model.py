"""Frozen lesson hierarchy, typed step payloads, and publication validation."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from aicefr.contracts import Band
from aicefr.lessons.align import MAX_ALIGNMENT_TOKENS
from aicefr.lessons.rules import LESSON_RULES_VERSION
from aicefr.lessons.text import normalize_text
from aicefr.practice.contracts import FrozenModel, TimeSpan

MAX_CONTENT_TEXT_CHARS = 4_096
MAX_RESULT_TEXT_CHARS = 32_768
MAX_REFERENCE_CHARS = 2_048
MAX_REFERENCE_TOKENS = 512
MAX_CONTENT_ITEMS = 100
MAX_LESSON_STEPS = 40
MAX_STEP_SPEAKING_SECONDS = 3_600
MAX_CONTENT_REVISION = 2_147_483_647


def _validate_reference(value: str) -> str:
    if len(normalize_text(value)) > MAX_REFERENCE_TOKENS:
        raise ValueError(f"reference text is limited to {MAX_REFERENCE_TOKENS} tokens")
    return value


def _validate_items(values: tuple[str, ...]) -> tuple[str, ...]:
    if any(len(value) > MAX_REFERENCE_CHARS for value in values):
        raise ValueError(f"each content item is limited to {MAX_REFERENCE_CHARS} characters")
    if any(len(normalize_text(value)) > MAX_REFERENCE_TOKENS for value in values):
        raise ValueError(f"each reference item is limited to {MAX_REFERENCE_TOKENS} tokens")
    return values


class Topic(StrEnum):
    DAILY_LIFE = "daily_life"
    EDUCATION = "education"
    FOOD = "food"
    TRAVEL = "travel"
    CAREER = "career"
    HEALTH = "health"
    PEOPLE = "people"
    TECHNOLOGY = "technology"
    ENVIRONMENT = "environment"
    SOCIETY = "society"


class StepKind(StrEnum):
    READ_ALOUD = "read_aloud"
    REPEAT = "repeat"
    LOOK_UP = "look_up"
    GAP = "gap"
    KEYWORDS = "keywords"
    STARTER = "starter"
    PICTURE = "picture"
    OUTLINE = "outline"
    FREE = "free"


class LessonStage(StrEnum):
    MODEL = "model"
    CONTROLLED = "controlled"
    GUIDED = "guided"
    FREE = "free"


STAGE_ORDER = (LessonStage.MODEL, LessonStage.CONTROLLED, LessonStage.GUIDED, LessonStage.FREE)
STAGE_FOR_KIND = {
    StepKind.READ_ALOUD: LessonStage.MODEL,
    StepKind.REPEAT: LessonStage.MODEL,
    StepKind.LOOK_UP: LessonStage.CONTROLLED,
    StepKind.GAP: LessonStage.CONTROLLED,
    StepKind.KEYWORDS: LessonStage.GUIDED,
    StepKind.STARTER: LessonStage.GUIDED,
    StepKind.PICTURE: LessonStage.GUIDED,
    StepKind.OUTLINE: LessonStage.GUIDED,
    StepKind.FREE: LessonStage.FREE,
}


class ReadAloudPayload(FrozenModel):
    kind: Literal[StepKind.READ_ALOUD]
    text: str = Field(min_length=1, max_length=MAX_REFERENCE_CHARS)
    hint_words: tuple[str, ...] = Field(default=(), max_length=MAX_CONTENT_ITEMS)
    max_seconds: int = Field(gt=0)

    _reference_text = field_validator("text")(_validate_reference)
    _bounded_hints = field_validator("hint_words")(_validate_items)


class RepeatPayload(FrozenModel):
    kind: Literal[StepKind.REPEAT]
    text: str = Field(min_length=1, max_length=MAX_REFERENCE_CHARS)
    max_seconds: int = Field(gt=0)

    _reference_text = field_validator("text")(_validate_reference)


class LookUpPayload(FrozenModel):
    kind: Literal[StepKind.LOOK_UP]
    text: str = Field(min_length=1, max_length=MAX_REFERENCE_CHARS)
    show_seconds: int = Field(gt=0)
    max_seconds: int = Field(gt=0)

    _reference_text = field_validator("text")(_validate_reference)


class GapPayload(FrozenModel):
    kind: Literal[StepKind.GAP]
    text: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)
    answers: tuple[str, ...] = Field(min_length=1, max_length=MAX_CONTENT_ITEMS)
    hint_words: tuple[str, ...] = Field(default=(), max_length=MAX_CONTENT_ITEMS)
    max_seconds: int = Field(gt=0)

    _reference_answers = field_validator("answers")(_validate_items)
    _bounded_hints = field_validator("hint_words")(_validate_items)


class KeywordsPayload(FrozenModel):
    kind: Literal[StepKind.KEYWORDS]
    keywords: tuple[str, ...] = Field(min_length=1, max_length=MAX_CONTENT_ITEMS)
    min_words: int = Field(default=1, ge=1)
    max_seconds: int = Field(gt=0)

    _bounded_keywords = field_validator("keywords")(_validate_items)


class StarterPayload(FrozenModel):
    kind: Literal[StepKind.STARTER]
    text: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)
    starter: str = Field(min_length=1, max_length=MAX_REFERENCE_CHARS)
    min_words: int = Field(default=1, ge=1)
    max_seconds: int = Field(gt=0)

    _bounded_starter = field_validator("starter")(_validate_reference)


class PictureChoice(FrozenModel):
    choice_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)


class PicturePayload(FrozenModel):
    kind: Literal[StepKind.PICTURE]
    prompt: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)
    pictures: tuple[PictureChoice, ...] = Field(min_length=1, max_length=MAX_CONTENT_ITEMS)
    min_words: int = Field(default=1, ge=1)
    max_seconds: int = Field(gt=0)


class OutlinePayload(FrozenModel):
    kind: Literal[StepKind.OUTLINE]
    text: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)
    points: tuple[str, ...] = Field(min_length=1, max_length=MAX_CONTENT_ITEMS)
    markers: tuple[str, ...] = Field(default=(), max_length=MAX_CONTENT_ITEMS)
    prep_seconds: int = Field(default=0, ge=0)
    min_seconds: int = Field(default=0, ge=0)
    max_seconds: int = Field(gt=0)

    _bounded_points = field_validator("points")(_validate_items)
    _bounded_markers = field_validator("markers")(_validate_items)

    @model_validator(mode="after")
    def _time_bounds(self) -> OutlinePayload:
        if self.min_seconds > self.max_seconds:
            raise ValueError("min_seconds cannot exceed max_seconds")
        return self


class FreeRound(FrozenModel):
    duration_seconds: int = Field(gt=0)
    prompt: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)


class FreePayload(FrozenModel):
    kind: Literal[StepKind.FREE]
    rounds: tuple[FreeRound, ...] = Field(min_length=2, max_length=3)
    max_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def _decreasing_rounds(self) -> FreePayload:
        durations = [round_.duration_seconds for round_ in self.rounds]
        if any(right >= left for left, right in zip(durations, durations[1:], strict=False)):
            raise ValueError("free round budgets must strictly decrease")
        if durations[0] > self.max_seconds:
            raise ValueError("first free round cannot exceed max_seconds")
        return self


StepPayload = Annotated[
    ReadAloudPayload
    | RepeatPayload
    | LookUpPayload
    | GapPayload
    | KeywordsPayload
    | StarterPayload
    | PicturePayload
    | OutlinePayload
    | FreePayload,
    Field(discriminator="kind"),
]


class LessonStep(FrozenModel):
    step_id: str = Field(min_length=1, max_length=128)
    ordinal: int = Field(ge=1)
    stage: LessonStage
    kind: StepKind
    instruction: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)
    payload: StepPayload
    rules_version: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _matching_kind_stage(self) -> LessonStep:
        if self.payload.kind is not self.kind:
            raise ValueError("step kind must match its typed payload")
        if self.stage is not STAGE_FOR_KIND[self.kind]:
            raise ValueError("step stage does not match its kind")
        return self


class LearningUnit(FrozenModel):
    unit_id: str = Field(min_length=1, max_length=128)
    path_id: str = Field(min_length=1, max_length=128)
    ordinal: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=256)
    band: Band
    topic: Topic | None = None
    learning_function: str | None = None
    lesson_ids: tuple[str, ...] = Field(default=(), max_length=MAX_CONTENT_ITEMS)
    revision: int = Field(default=0, ge=0, le=MAX_CONTENT_REVISION, strict=True)

    @model_validator(mode="after")
    def _unique_lessons(self) -> LearningUnit:
        if len(set(self.lesson_ids)) != len(self.lesson_ids):
            raise ValueError("lesson_ids must be unique within a unit")
        return self


class LearningPath(FrozenModel):
    path_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=MAX_CONTENT_TEXT_CHARS)
    band_from: Band
    band_to: Band
    units: tuple[LearningUnit, ...] = Field(default=(), max_length=MAX_CONTENT_ITEMS)
    content_version: str = Field(min_length=1, max_length=128)
    revision: int = Field(default=0, ge=0, le=MAX_CONTENT_REVISION, strict=True)

    @model_validator(mode="after")
    def _hierarchy(self) -> LearningPath:
        if len({unit.unit_id for unit in self.units}) != len(self.units):
            raise ValueError("unit ids must be unique within a path")
        if any(unit.path_id != self.path_id for unit in self.units):
            raise ValueError("all units must refer to their containing path")
        if [unit.ordinal for unit in self.units] != sorted(unit.ordinal for unit in self.units):
            raise ValueError("units must be ordered by ordinal")
        return self


class Lesson(FrozenModel):
    lesson_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    summary: str = Field(default="", max_length=MAX_CONTENT_TEXT_CHARS)
    band: Band
    steps: tuple[LessonStep, ...] = Field(default=(), max_length=MAX_LESSON_STEPS)
    revision: int = Field(default=1, ge=1)
    content_version: str = Field(default="v1", min_length=1, max_length=128)

    @model_validator(mode="after")
    def _steps_unique_ordered(self) -> Lesson:
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("step ids must be unique within a lesson")
        if len({step.ordinal for step in self.steps}) != len(self.steps):
            raise ValueError("step ordinals must be unique within a lesson")
        if [step.ordinal for step in self.steps] != sorted(step.ordinal for step in self.steps):
            raise ValueError("steps must be ordered by ordinal")
        return self


class PublishedLessonVersion(FrozenModel):
    lesson_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=256)
    summary: str = Field(default="", max_length=MAX_CONTENT_TEXT_CHARS)
    band: Band
    rules_version: str = Field(min_length=1, max_length=128)
    published_at: datetime
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    steps: tuple[LessonStep, ...] = Field(min_length=1, max_length=MAX_LESSON_STEPS)

    @field_validator("published_at")
    @classmethod
    def _aware_published_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        return value

    @classmethod
    def from_lesson(
        cls, lesson: Lesson, *, version: int, published_at: datetime
    ) -> PublishedLessonVersion:
        from aicefr.lessons.lint import lint_lesson

        validation = lint_lesson(lesson, for_publish=True)
        if not validation.valid:
            raise ValueError("lesson must pass publication lint")
        payload = lesson.model_dump(mode="json")
        content_hash = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rules_versions = {step.rules_version for step in lesson.steps}
        if len(rules_versions) != 1:
            raise ValueError("published lesson steps must share one rules version")
        return cls(
            lesson_id=lesson.lesson_id,
            version=version,
            revision=lesson.revision,
            title=lesson.title,
            summary=lesson.summary,
            band=lesson.band,
            rules_version=next(iter(rules_versions)),
            published_at=published_at,
            content_hash=content_hash,
            steps=lesson.steps,
        )


class LessonLintIssue(FrozenModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    step_id: str | None = None


class LessonValidation(FrozenModel):
    valid: bool
    errors: tuple[LessonLintIssue, ...] = ()
    warnings: tuple[LessonLintIssue, ...] = ()


class StepResultStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNSURE = "UNSURE"
    UNMEASURED = "UNMEASURED"


class StepEvidenceState(StrEnum):
    HEARD = "HEARD"
    UNSURE = "UNSURE"
    MISSED = "MISSED"


class StepEvidenceOperation(StrEnum):
    MATCH = "MATCH"
    SUBSTITUTE = "SUBSTITUTE"
    DELETE = "DELETE"
    INSERT = "INSERT"


class StepTokenEvidence(FrozenModel):
    reference_index: int = Field(ge=0)
    source_word_index: int | None = Field(default=None, ge=0)
    expected_token: str = Field(max_length=MAX_REFERENCE_CHARS)
    heard_token: str | None = Field(default=None, max_length=MAX_REFERENCE_CHARS)
    operation: StepEvidenceOperation
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    state: StepEvidenceState

    @field_validator("confidence")
    @classmethod
    def _finite_confidence(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("confidence must be finite")
        return value


class StepResult(FrozenModel):
    step_id: str = Field(min_length=1, max_length=128)
    kind: StepKind
    status: StepResultStatus
    rules_version: str = Field(default=LESSON_RULES_VERSION, min_length=1, max_length=128)
    heard_text: str = Field(default="", max_length=MAX_RESULT_TEXT_CHARS)
    matched_count: int | None = Field(default=None, ge=0)
    target_count: int | None = Field(default=None, ge=0)
    evidence: tuple[StepTokenEvidence, ...] = Field(default=(), max_length=MAX_ALIGNMENT_TOKENS * 2)
    round_index: int | None = Field(default=None, ge=0)
    round_count: int | None = Field(default=None, ge=1)
    elapsed_seconds: float | None = Field(default=None, ge=0.0)
    speaking_s: float = Field(default=0.0, ge=0.0, le=MAX_STEP_SPEAKING_SECONDS)
    time_evidence: tuple[TimeSpan, ...] = Field(default=(), max_length=MAX_ALIGNMENT_TOKENS)
    word_count: int = Field(default=0, ge=0)
    feedback: str = Field(min_length=1, max_length=MAX_CONTENT_TEXT_CHARS)

    @model_validator(mode="after")
    def _evidence_bounds(self) -> StepResult:
        if any(
            item.source_word_index is not None and item.source_word_index >= self.word_count
            for item in self.evidence
        ):
            raise ValueError("step evidence index exceeds source transcript word count")
        if self.elapsed_seconds is not None and not math.isfinite(self.elapsed_seconds):
            raise ValueError("elapsed_seconds must be finite")
        if not math.isfinite(self.speaking_s):
            raise ValueError("speaking_s must be finite")
        return self


class StepAttemptStatus(StrEnum):
    COMPLETE = "COMPLETE"
    RETRY = "RETRY"
    SKIPPED = "SKIPPED"


class StepCompletion(FrozenModel):
    attempt_id: str = Field(min_length=1, max_length=128)
    step_id: str = Field(min_length=1, max_length=128)
    kind: StepKind
    status: StepAttemptStatus
    attempted_at: datetime
    round_index: int | None = Field(default=None, ge=0)
    speaking_s: float = Field(default=0.0, ge=0.0, le=MAX_STEP_SPEAKING_SECONDS)

    @field_validator("attempted_at")
    @classmethod
    def _aware_attempted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("attempted_at must be timezone-aware")
        return value

    @field_validator("speaking_s")
    @classmethod
    def _finite_speaking_time(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("speaking_s must be finite")
        return value

    @model_validator(mode="after")
    def _round_shape(self) -> StepCompletion:
        if (self.kind is StepKind.FREE) != (self.round_index is not None):
            raise ValueError("only FREE attempts require a round index")
        return self


class LessonProgress(FrozenModel):
    completed_step_ids: tuple[str, ...] = Field(max_length=MAX_LESSON_STEPS)
    required_step_count: int = Field(ge=0)
    completion_fraction: float = Field(ge=0.0, le=1.0)
    completed_free_rounds: int = Field(ge=0)
    required_free_rounds: int = Field(ge=0)
    complete: bool

    @field_validator("completion_fraction")
    @classmethod
    def _finite_fraction(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("completion_fraction must be finite")
        return value
