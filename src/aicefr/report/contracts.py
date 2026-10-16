"""Typed report-side contracts for evidence-bound diagnostic feedback."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aicefr.contracts import (
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Interaction,
    ReasonCode,
    ReviewAction,
)
from aicefr.trust.contracts import ConformalSet, CriterionIndicator, TrustAssessment


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceSource(StrEnum):
    TRANSCRIPT = "transcript"
    FEATURE_SET = "feature_set"


class CommentTemplate(StrEnum):
    WORD_TIMING_OBSERVED = "WORD_TIMING_OBSERVED"
    PAUSE_MEASUREMENT_OBSERVED = "PAUSE_MEASUREMENT_OBSERVED"
    FEATURE_VALUE_AVAILABLE = "FEATURE_VALUE_AVAILABLE"


class ReportStatus(StrEnum):
    PROVISIONAL = "PROVISIONAL"
    TEACHER_VERIFIED = "TEACHER_VERIFIED"


class EvidenceRef(_Frozen):
    """A report reference that can be checked against source response/version."""

    evidence_id: str = Field(min_length=1)
    response_id: str = Field(min_length=1)
    source: EvidenceSource
    source_version: str = Field(min_length=1)
    criterion: Criterion
    start_s: float | None = Field(default=None, ge=0)
    end_s: float | None = Field(default=None, ge=0)
    word_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _time_range_is_complete(self) -> EvidenceRef:
        if (self.start_s is None) != (self.end_s is None):
            raise ValueError("time evidence needs both start_s and end_s")
        if self.start_s is not None and self.end_s is not None and self.end_s < self.start_s:
            raise ValueError("end_s must not precede start_s")
        return self


class CommentRequest(_Frozen):
    """A bounded, non-generative comment request tied to exactly one evidence ref."""

    criterion: Criterion
    template: CommentTemplate
    evidence_id: str = Field(min_length=1)


class DiagnosticComment(_Frozen):
    criterion: Criterion
    text: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    source: EvidenceSource


class EvidenceIssue(_Frozen):
    evidence_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class TeacherFinalResult(_Frozen):
    action: ReviewAction
    overall_band: Band | None = None
    reason: str | None = None
    audit_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    recorded_at: str = Field(min_length=1)


class DiagnosticReport(_Frozen):
    """Presentation data: one overall estimate and five coverage rows, never five scores."""

    response_id: str = Field(min_length=1)
    status: ReportStatus
    assessment_status: AssessmentStatus
    overall_score: float | None = Field(default=None, ge=1.0, le=6.0)
    overall_band: Band | None = None
    criteria: tuple[CriterionCoverage, ...]
    interaction: Interaction
    reasons: tuple[ReasonCode, ...] = ()
    comments: tuple[DiagnosticComment, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    evidence_issues: tuple[EvidenceIssue, ...] = ()
    limitations: tuple[str, ...] = ()
    source_versions: dict[str, str] = Field(default_factory=dict)
    # Optional M09 extension. Defaults preserve read compatibility with reports
    # written before Trust was introduced.
    trust: TrustAssessment | None = None
    prediction_set: ConformalSet | None = None
    criterion_indicators: tuple[CriterionIndicator, ...] = ()
    provenance: dict[str, str] = Field(default_factory=dict)
    teacher_verified: bool = False
    teacher_final: TeacherFinalResult | None = None

    @model_validator(mode="after")
    def _report_shape_is_safe(self) -> DiagnosticReport:
        criteria = tuple(row.criterion for row in self.criteria)
        if criteria != tuple(Criterion):
            raise ValueError("criteria must contain the five CEFR coverage rows in canonical order")
        if self.assessment_status is AssessmentStatus.NOT_EVALUATED and (
            self.overall_score is not None or self.overall_band is not None
        ):
            raise ValueError("NOT_EVALUATED must not expose an overall estimate")
        if self.teacher_verified != (self.teacher_final is not None):
            raise ValueError("teacher_verified requires exactly one teacher_final audit result")
        if self.teacher_verified and self.status is not ReportStatus.TEACHER_VERIFIED:
            raise ValueError("verified report must use TEACHER_VERIFIED status")
        if self.trust is not None:
            indicators = self.trust.criterion_indicators
            if tuple(row.name for row in indicators) != tuple(Criterion):
                raise ValueError("trust must provide exactly five canonical criterion indicators")
            if any(row.label != "chỉ báo" for row in indicators):
                raise ValueError("criterion indicator label must remain 'chỉ báo'")
            if self.prediction_set != self.trust.prediction_set:
                raise ValueError("report prediction_set must match trust assessment")
            if self.criterion_indicators != self.trust.criterion_indicators:
                raise ValueError("report criterion indicators must match trust assessment")
        return self

    @field_validator("provenance")
    @classmethod
    def _bounded_metadata(cls, values: dict[str, str]) -> dict[str, str]:
        if len(values) > 16 or any(
            not isinstance(key, str)
            or not isinstance(value, str)
            or len(key) > 64
            or len(value) > 160
            for key, value in values.items()
        ):
            raise ValueError("report metadata is too large")
        return values
