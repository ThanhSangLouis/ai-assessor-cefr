"""Evidence validation and report composition for M06."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aicefr.contracts import (
    Assessment,
    AssessmentStatus,
    Criterion,
    FeatureSet,
    ReasonCode,
    ReviewDecision,
    Transcript,
)
from aicefr.report.contracts import (
    CommentRequest,
    CommentTemplate,
    DiagnosticComment,
    DiagnosticReport,
    EvidenceIssue,
    EvidenceRef,
    EvidenceSource,
    ReportStatus,
    TeacherFinalResult,
)
from aicefr.trust.contracts import TrustAssessment


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReportInput(_Frozen):
    response_id: str = Field(min_length=1)
    audio_duration_s: float = Field(ge=0)
    assessment: Assessment
    transcript: Transcript | None = None
    features: FeatureSet | None = None
    evidence_refs: tuple[EvidenceRef, ...] = ()
    comment_requests: tuple[CommentRequest, ...] = ()
    source_versions: dict[str, str] = Field(default_factory=dict)
    trust: TrustAssessment | None = None
    provenance: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _all_artifacts_match_response(self) -> ReportInput:
        response_ids = [self.assessment.response_id]
        if self.transcript is not None:
            response_ids.append(self.transcript.response_id)
        if self.features is not None:
            response_ids.append(self.features.response_id)
        if any(response_id != self.response_id for response_id in response_ids):
            raise ValueError("report artifacts must have the same response_id")
        return self


@dataclass(frozen=True)
class EvidenceValidation:
    valid: Mapping[str, EvidenceRef]
    issues: tuple[EvidenceIssue, ...]


class EvidenceValidator:
    """Fail closed: invalid, stale or foreign refs can never produce a comment."""

    def validate(self, report_input: ReportInput) -> EvidenceValidation:
        valid: dict[str, EvidenceRef] = {}
        issues: list[EvidenceIssue] = []
        for reference in report_input.evidence_refs:
            issue = self._validate_one(reference, report_input)
            if issue is None:
                valid[reference.evidence_id] = reference
            else:
                issues.append(EvidenceIssue(evidence_id=reference.evidence_id, reason=issue))
        return EvidenceValidation(valid=valid, issues=tuple(issues))

    def _validate_one(self, reference: EvidenceRef, report_input: ReportInput) -> str | None:
        if reference.response_id != report_input.response_id:
            return "EVIDENCE_RESPONSE_MISMATCH"
        expected_version = self._source_version(reference.source, report_input)
        if expected_version is None:
            return "EVIDENCE_SOURCE_UNAVAILABLE"
        if reference.source_version != expected_version:
            return "EVIDENCE_SOURCE_VERSION_MISMATCH"
        if reference.end_s is not None and reference.end_s > report_input.audio_duration_s:
            return "EVIDENCE_TIMESTAMP_OUT_OF_RANGE"
        if reference.start_s is not None and not math.isfinite(reference.start_s):
            return "EVIDENCE_TIMESTAMP_INVALID"
        if reference.end_s is not None and not math.isfinite(reference.end_s):
            return "EVIDENCE_TIMESTAMP_INVALID"
        if reference.word_index is not None:
            transcript = report_input.transcript
            if transcript is None or reference.source is not EvidenceSource.TRANSCRIPT:
                return "EVIDENCE_WORD_REFERENCE_INVALID"
            if reference.word_index >= len(transcript.words):
                return "EVIDENCE_WORD_REFERENCE_INVALID"
            word = transcript.words[reference.word_index]
            if reference.start_s != word.start_s or reference.end_s != word.end_s:
                return "EVIDENCE_WORD_TIMESTAMP_MISMATCH"
        if reference.source is EvidenceSource.FEATURE_SET:
            parts = reference.evidence_id.split(":", maxsplit=2)
            if len(parts) != 3 or parts[0] != "feature" or report_input.features is None:
                return "EVIDENCE_FEATURE_REFERENCE_INVALID"
            try:
                expected_value = float.fromhex(parts[2])
            except ValueError:
                return "EVIDENCE_FEATURE_REFERENCE_INVALID"
            actual_value = next(
                (value.value for value in report_input.features.values if value.name == parts[1]),
                None,
            )
            if (
                actual_value is None
                or not math.isfinite(actual_value)
                or actual_value != expected_value
            ):
                return "EVIDENCE_FEATURE_VALUE_MISMATCH"
        return None

    @staticmethod
    def _source_version(source: EvidenceSource, report_input: ReportInput) -> str | None:
        if source is EvidenceSource.TRANSCRIPT:
            return (
                report_input.transcript.decode_config_version
                if report_input.transcript is not None
                else None
            )
        return report_input.features.feature_version if report_input.features is not None else None


class ReportNotFound(LookupError):
    pass


class UnverifiedReviewDecision(PermissionError):
    """M06 received a decision that is not backed by a recorded M07 action."""


class ReviewDecisionVerifier(Protocol):
    def verify_decision(self, decision: ReviewDecision) -> bool: ...


class ReportRepository(Protocol):
    def put(self, report: DiagnosticReport) -> None: ...

    def get(self, response_id: str) -> DiagnosticReport | None: ...


class MemoryReportRepository:
    """In-memory report port for fixture-driven local runs and API tests."""

    def __init__(self) -> None:
        self._reports: dict[str, DiagnosticReport] = {}

    def put(self, report: DiagnosticReport) -> None:
        self._reports[report.response_id] = report

    def get(self, response_id: str) -> DiagnosticReport | None:
        return self._reports.get(response_id)


class DiagnosticReportBuilder:
    """Builds only observations grounded in checked EvidenceRef records."""

    MAX_INDICATOR_EVIDENCE_REFS = 8

    _TEMPLATE_TEXT: dict[CommentTemplate, str] = {
        CommentTemplate.WORD_TIMING_OBSERVED: "Có mốc từ được ghi nhận trong transcript.",
        CommentTemplate.PAUSE_MEASUREMENT_OBSERVED: "Có mốc dừng được ghi nhận trong dữ liệu.",
        CommentTemplate.FEATURE_VALUE_AVAILABLE: "Có dữ liệu đặc trưng có thể truy vết.",
    }
    _TEMPLATE_SOURCE: dict[CommentTemplate, EvidenceSource] = {
        CommentTemplate.WORD_TIMING_OBSERVED: EvidenceSource.TRANSCRIPT,
        CommentTemplate.PAUSE_MEASUREMENT_OBSERVED: EvidenceSource.FEATURE_SET,
        CommentTemplate.FEATURE_VALUE_AVAILABLE: EvidenceSource.FEATURE_SET,
    }

    def __init__(self, validator: EvidenceValidator | None = None) -> None:
        self._validator = validator or EvidenceValidator()

    def build(self, report_input: ReportInput) -> DiagnosticReport:
        evidence = self._validator.validate(report_input)
        comments, request_issues = self._comments(report_input.comment_requests, evidence.valid)
        issues = (*evidence.issues, *request_issues)
        assessment = report_input.assessment
        limitations = self._limitations(assessment.status, issues)
        trust = report_input.trust
        indicators = ()
        if trust is not None:
            evidence_by_criterion: dict[Criterion, list[str]] = {
                criterion: [] for criterion in Criterion
            }
            for reference in evidence.valid.values():
                evidence_by_criterion[reference.criterion].append(reference.evidence_id)
            indicators = tuple(
                indicator.model_copy(
                    update={
                        "evidence_refs": tuple(
                            evidence_by_criterion[indicator.name][
                                : self.MAX_INDICATOR_EVIDENCE_REFS
                            ]
                        )
                    }
                )
                for indicator in trust.criterion_indicators
            )
            trust = trust.model_copy(update={"criterion_indicators": indicators})
        if ReasonCode.SCORE_AGGREGATED in assessment.reasons:
            limitations += (
                "Bài dài dùng tổng hợp các cửa sổ, chưa được validation CEFR; "
                "phải có giảng viên duyệt trước khi sử dụng kết quả.",
            )
        return DiagnosticReport(
            response_id=report_input.response_id,
            status=ReportStatus.PROVISIONAL,
            assessment_status=assessment.status,
            overall_score=assessment.overall_score,
            overall_band=assessment.overall_band,
            criteria=assessment.criteria,
            interaction=assessment.interaction,
            reasons=assessment.reasons,
            comments=tuple(comments),
            evidence_refs=tuple(evidence.valid.values()),
            evidence_issues=tuple(issues),
            limitations=limitations,
            source_versions=self._source_versions(report_input) | report_input.source_versions,
            trust=trust,
            prediction_set=(trust.prediction_set if trust else None),
            criterion_indicators=indicators,
            provenance=report_input.provenance,
        )

    def apply_review(self, report: DiagnosticReport, decision: ReviewDecision) -> DiagnosticReport:
        if report.response_id != decision.response_id:
            raise ValueError("review decision belongs to another response")
        final = TeacherFinalResult(
            action=decision.action,
            overall_band=decision.final_band,
            reason=decision.reason,
            audit_id=decision.audit_id,
            recorded_at=decision.recorded_at.isoformat(),
        )
        return report.model_copy(
            update={
                "status": ReportStatus.TEACHER_VERIFIED,
                "teacher_verified": True,
                "teacher_final": final,
            }
        )

    def _comments(
        self,
        requests: tuple[CommentRequest, ...],
        references: Mapping[str, EvidenceRef],
    ) -> tuple[list[DiagnosticComment], list[EvidenceIssue]]:
        comments: list[DiagnosticComment] = []
        issues: list[EvidenceIssue] = []
        for request in requests:
            reference = references.get(request.evidence_id)
            if reference is None:
                issues.append(
                    EvidenceIssue(
                        evidence_id=request.evidence_id,
                        reason="COMMENT_EVIDENCE_MISSING",
                    )
                )
                continue
            if reference.criterion is not request.criterion:
                issues.append(
                    EvidenceIssue(
                        evidence_id=request.evidence_id,
                        reason="COMMENT_CRITERION_MISMATCH",
                    )
                )
                continue
            if self._TEMPLATE_SOURCE[request.template] is not reference.source:
                issues.append(
                    EvidenceIssue(
                        evidence_id=request.evidence_id,
                        reason="COMMENT_TEMPLATE_SOURCE_MISMATCH",
                    )
                )
                continue
            comments.append(
                DiagnosticComment(
                    criterion=request.criterion,
                    text=self._TEMPLATE_TEXT[request.template],
                    evidence_id=reference.evidence_id,
                    source=reference.source,
                )
            )
        return comments, issues

    @staticmethod
    def _limitations(
        status: AssessmentStatus, issues: tuple[EvidenceIssue, ...]
    ) -> tuple[str, ...]:
        values: list[str] = ["Kết quả chỉ hỗ trợ học tập, không phải chứng chỉ."]
        if status is AssessmentStatus.NOT_EVALUATED:
            values.append("Chưa đủ điều kiện để đưa ra ước lượng overall.")
        if issues:
            values.append("Một số nhận xét bị bỏ vì thiếu hoặc sai evidence.")
        return tuple(values)

    @staticmethod
    def _source_versions(report_input: ReportInput) -> dict[str, str]:
        values = {"assessment": report_input.assessment.provenance.model_version or "unavailable"}
        provenance = report_input.assessment.provenance
        for field in (
            "model_sha256",
            "band_map_version",
            "calibration_version",
            "unit_of_inference",
            "feature_version",
        ):
            value = getattr(provenance, field)
            if value is not None:
                values[field] = value
        if report_input.transcript is not None:
            values["transcript"] = report_input.transcript.decode_config_version
            values["asr_engine"] = (
                f"{report_input.transcript.engine}@{report_input.transcript.engine_version}"
            )
            values["asr_model"] = report_input.transcript.asr_model or "unavailable"
        if report_input.features is not None:
            values["feature_set"] = report_input.features.feature_version
        return values


class ReportService:
    """Repository facade used by M01 presentation and M07 decision integration."""

    def __init__(
        self,
        repository: ReportRepository,
        builder: DiagnosticReportBuilder | None = None,
        decision_verifier: ReviewDecisionVerifier | None = None,
    ) -> None:
        self._repository = repository
        self._builder = builder or DiagnosticReportBuilder()
        self._decision_verifier = decision_verifier

    def build_and_store(self, report_input: ReportInput) -> DiagnosticReport:
        report = self._builder.build(report_input)
        self._repository.put(report)
        return report

    def get(self, response_id: str) -> DiagnosticReport | None:
        return self._repository.get(response_id)

    def apply_review(self, decision: ReviewDecision) -> DiagnosticReport:
        if self._decision_verifier is None or not self._decision_verifier.verify_decision(decision):
            raise UnverifiedReviewDecision("teacher verification requires a recorded M07 decision")
        report = self._repository.get(decision.response_id)
        if report is None:
            raise ReportNotFound(decision.response_id)
        updated = self._builder.apply_review(report, decision)
        self._repository.put(updated)
        return updated
