"""Typed, immutable domain evidence for M09 Trust Layer."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from aicefr.contracts import Band, Criterion, ReasonCode, _Frozen

LANGUAGE_CONFIDENCE_THRESHOLD = 0.80


class LanguageDecision(StrEnum):
    ENGLISH = "ENGLISH"
    NON_ENGLISH = "NON_ENGLISH"
    UNCERTAIN = "UNCERTAIN"


class GuardKind(StrEnum):
    OFF_TOPIC = "off_topic"
    PROMPT_READING = "prompt_reading"


class GuardDecision(StrEnum):
    CLEAR = "clear"
    SUSPECTED = "suspected"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class TrustDisposition(StrEnum):
    CONTINUE = "CONTINUE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_EVALUATED = "NOT_EVALUATED"
    REJECTED = "REJECTED"


class LanguageEvidence(_Frozen):
    method: str = Field(min_length=1)
    version: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str | None = None
    decision: LanguageDecision
    reason_code: ReasonCode | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("confidence must be numeric, not bool")
        return value

    @model_validator(mode="after")
    def _decision_matches_evidence(self) -> LanguageEvidence:
        normalized = self.language.casefold() if self.language is not None else None
        confident = self.confidence is not None and self.confidence > LANGUAGE_CONFIDENCE_THRESHOLD
        if self.decision is LanguageDecision.ENGLISH and not (normalized == "en" and confident):
            raise ValueError("ENGLISH requires high-confidence language=en")
        if self.decision is LanguageDecision.NON_ENGLISH and not (
            normalized not in (None, "", "en") and confident
        ):
            raise ValueError("NON_ENGLISH requires high-confidence non-English language")
        return self


class EvidenceSpan(_Frozen):
    """Minimal word-index reference; never stores transcript text."""

    start_word: int = Field(ge=0, le=5000)
    end_word: int = Field(ge=1, le=5000)

    @model_validator(mode="after")
    def _nonempty(self) -> EvidenceSpan:
        if self.end_word <= self.start_word:
            raise ValueError("evidence span must be non-empty")
        return self


class GuardEvidence(_Frozen):
    kind: GuardKind
    value: float = Field(ge=0.0, le=1.0)
    threshold_version: str = Field(min_length=1)
    spans: tuple[EvidenceSpan, ...] = ()
    decision: GuardDecision

    @field_validator("value", mode="before")
    @classmethod
    def _value_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("guard value must be numeric, not bool")
        return value


class ConformalSet(_Frozen):
    """Prediction set computed from a verified calibration artifact."""

    alpha: float = Field(gt=0.0, lt=0.5)
    bands: tuple[Band, ...]
    calibration_id: str = Field(min_length=1)
    checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    low: float = Field(ge=1.0, le=6.0)
    high: float = Field(ge=1.0, le=6.0)

    @field_validator("alpha", "low", "high", mode="before")
    @classmethod
    def _finite_numeric_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("value must be numeric, not bool")
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError("value must be finite")
        return value

    @model_validator(mode="after")
    def _ordered_bounds(self) -> ConformalSet:
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        if len(set(self.bands)) != len(self.bands):
            raise ValueError("bands must be unique")
        if not self.bands:
            raise ValueError("conformal set must contain at least one band")
        canonical = tuple(band for band in Band if band in self.bands)
        if self.bands != canonical:
            raise ValueError("bands must use canonical A2/B1/B2 order")
        return self


class CriterionIndicator(_Frozen):
    name: Criterion
    coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    label: Literal["chỉ báo"] = "chỉ báo"
    evidence_refs: tuple[str, ...] = ()

    @field_validator("coverage", mode="before")
    @classmethod
    def _coverage_not_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("coverage must be numeric, not bool")
        return value


class TrustDecision(_Frozen):
    disposition: TrustDisposition
    reasons: tuple[ReasonCode, ...] = ()

    @field_validator("reasons")
    @classmethod
    def _unique_reasons(cls, values: tuple[ReasonCode, ...]) -> tuple[ReasonCode, ...]:
        return tuple(dict.fromkeys(values))


class TrustAssessment(_Frozen):
    language: LanguageEvidence | None = None
    relevance: tuple[GuardEvidence, ...] = ()
    prediction_set: ConformalSet | None = None
    criterion_indicators: tuple[CriterionIndicator, ...] = ()
    reasons: tuple[ReasonCode, ...] = ()
    disposition: TrustDisposition

    @field_validator("reasons")
    @classmethod
    def _unique_reasons(cls, values: tuple[ReasonCode, ...]) -> tuple[ReasonCode, ...]:
        return tuple(dict.fromkeys(values))
