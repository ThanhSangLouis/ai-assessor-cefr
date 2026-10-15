"""Immutable domain contracts for uns cored practice activities."""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aicefr.contracts import AssessmentStatus, Band, Criterion, CriterionCoverage


class FrozenModel(BaseModel):
    """Pydantic base that rejects accidental payload expansion and mutation."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class PracticePurpose(StrEnum):
    PRACTICE = "PRACTICE"
    LEARNING = "LEARNING"


class MissionKind(StrEnum):
    SPEAK_SECONDS = "speak_seconds"
    MAX_PAUSE = "max_pause"
    USE_WORDS = "use_words"
    UNIQUE_WORDS = "unique_words"
    PAST_VERBS = "past_verbs"
    CONDITIONALS = "conditionals"
    READ_ALOUD = "read_aloud"


class PracticeStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNSURE = "UNSURE"
    UNMEASURED = "UNMEASURED"


class PracticeReason(StrEnum):
    NO_SPEECH = "NO_SPEECH"
    LOW_ASR_CONFIDENCE = "LOW_ASR_CONFIDENCE"
    TRANSCRIPT_UNAVAILABLE = "TRANSCRIPT_UNAVAILABLE"
    REFERENCE_MISSING = "REFERENCE_MISSING"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    LANGUAGE_NOT_ENGLISH = "LANGUAGE_NOT_ENGLISH"
    LANGUAGE_UNCERTAIN = "LANGUAGE_UNCERTAIN"
    LEMMA_EQUIVALENT = "LEMMA_EQUIVALENT"


class TimeSpan(FrozenModel):
    """Half-open audio interval in seconds."""

    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)

    @model_validator(mode="after")
    def _valid_interval(self) -> TimeSpan:
        if not math.isfinite(self.start_s) or not math.isfinite(self.end_s):
            raise ValueError("time span bounds must be finite")
        if self.end_s <= self.start_s:
            raise ValueError("time span end must follow start")
        return self


class WordEvidence(FrozenModel):
    """Half-open range in the source Transcript.words tuple."""

    start_word_index: int = Field(ge=0)
    end_word_index: int = Field(gt=0)

    @model_validator(mode="after")
    def _nonempty(self) -> WordEvidence:
        if self.end_word_index <= self.start_word_index:
            raise ValueError("word evidence range must be non-empty")
        return self


class MissionGoal(FrozenModel):
    goal_id: str = Field(min_length=1)
    kind: MissionKind
    target: float = Field(gt=0)
    words: tuple[str, ...] = ()
    reference_text: str | None = None

    @field_validator("target")
    @classmethod
    def _finite_target(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("mission targets must be finite")
        return value

    @model_validator(mode="after")
    def _kind_payload(self) -> MissionGoal:
        if self.kind is MissionKind.USE_WORDS and not self.words:
            raise ValueError("use_words goals require a non-empty word list")
        if self.kind is MissionKind.READ_ALOUD and not self.reference_text:
            raise ValueError("read_aloud goals require reference text")
        if self.kind is not MissionKind.USE_WORDS and self.words:
            raise ValueError("only use_words goals may carry a word list")
        if self.kind is not MissionKind.READ_ALOUD and self.reference_text is not None:
            raise ValueError("only read_aloud goals may carry reference text")
        return self


class PracticeMission(FrozenModel):
    mission_id: str = Field(pattern=r"^PR-(FLU|COH|RAN|ACC|PHO)-(A2|B1|B2)$")
    criterion: Criterion
    target_band: Band
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    goals: tuple[MissionGoal, ...] = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    rules_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _id_metadata_consistent(self) -> PracticeMission:
        prefix, band = self.mission_id.removeprefix("PR-").split("-")
        expected = {
            "FLU": Criterion.FLUENCY,
            "COH": Criterion.COHERENCE,
            "RAN": Criterion.RANGE,
            "ACC": Criterion.ACCURACY,
            "PHO": Criterion.PHONOLOGY,
        }[prefix]
        if self.target_band.value != band or self.criterion is not expected:
            raise ValueError("mission id must agree with criterion and target band")
        if len({goal.goal_id for goal in self.goals}) != len(self.goals):
            raise ValueError("goal ids must be unique per mission")
        return self


class MissionMeasurement(FrozenModel):
    goal_id: str = Field(min_length=1)
    measured_value: float | None = None
    target: float = Field(gt=0)
    status: PracticeStatus
    evidence: tuple[WordEvidence, ...] = ()
    time_evidence: tuple[TimeSpan, ...] = ()
    reason: PracticeReason | None = None

    @model_validator(mode="after")
    def _finite_and_status(self) -> MissionMeasurement:
        if self.measured_value is not None and not math.isfinite(self.measured_value):
            raise ValueError("measured value must be finite")
        if (
            self.status in (PracticeStatus.PASS, PracticeStatus.FAIL)
            and self.measured_value is None
        ):
            raise ValueError("measured pass/fail requires a measured value")
        if (
            self.status in (PracticeStatus.UNSURE, PracticeStatus.UNMEASURED)
            and self.measured_value is not None
        ):
            raise ValueError("uncertain/unmeasured result cannot claim a value")
        return self


class PracticeResult(FrozenModel):
    mission_id: str = Field(pattern=r"^PR-(FLU|COH|RAN|ACC|PHO)-(A2|B1|B2)$")
    purpose: PracticePurpose
    status: PracticeStatus
    measurements: tuple[MissionMeasurement, ...] = Field(min_length=1)
    rules_version: str = Field(min_length=1)
    reasons: tuple[PracticeReason, ...] = ()
    word_count: int = Field(ge=0)
    audio_duration_s: float = Field(ge=0)
    speaking_s: float = Field(default=0.0, ge=0.0, le=3_600.0)

    @field_validator("audio_duration_s")
    @classmethod
    def _finite_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("audio duration must be finite")
        return value

    @field_validator("speaking_s")
    @classmethod
    def _finite_speaking_duration(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("speaking duration must be finite")
        return value

    @model_validator(mode="after")
    def _result_consistent(self) -> PracticeResult:
        ids = [item.goal_id for item in self.measurements]
        if len(ids) != len(set(ids)):
            raise ValueError("measurement goal ids must be unique")
        for item in self.measurements:
            if any(span.end_word_index > self.word_count for span in item.evidence):
                raise ValueError("word evidence exceeds transcript word count")
            if any(span.end_s > self.audio_duration_s for span in item.time_evidence):
                raise ValueError("time evidence exceeds audio duration")
        if self.speaking_s > self.audio_duration_s:
            raise ValueError("speaking duration exceeds audio duration")
        statuses = {item.status for item in self.measurements}
        if self.measurements:
            derived = (
                PracticeStatus.FAIL
                if PracticeStatus.FAIL in statuses
                else PracticeStatus.UNSURE
                if PracticeStatus.UNSURE in statuses
                else PracticeStatus.UNMEASURED
                if PracticeStatus.UNMEASURED in statuses
                else PracticeStatus.PASS
            )
            if self.status is not derived:
                raise ValueError("result status must match its measurements")
        return self


class RecommendationEvidence(FrozenModel):
    """Read-only projection of a persisted assessment; it is not an Assessment clone."""

    response_id: str = Field(min_length=1)
    created_at: datetime
    status: AssessmentStatus
    overall_score: float | None = Field(default=None, ge=1.0, le=6.0)
    overall_band: Band | None = None
    criteria: tuple[CriterionCoverage, ...]

    @field_validator("created_at")
    @classmethod
    def _aware_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessment timestamp must be timezone-aware")
        return value

    @field_validator("overall_score")
    @classmethod
    def _finite_score(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("overall score must be finite")
        return value


class RecommendationReasonCode(StrEnum):
    NO_ELIGIBLE_ASSESSMENT_FALLBACK_A2 = "NO_ELIGIBLE_ASSESSMENT_FALLBACK_A2"
    WEAKEST_COVERAGE_NEAREST_BAND = "WEAKEST_COVERAGE_NEAREST_BAND"


class Recommendation(FrozenModel):
    mission_id: str
    criterion: Criterion
    target_band: Band
    reason_code: RecommendationReasonCode
    explanation: str = Field(min_length=1)
