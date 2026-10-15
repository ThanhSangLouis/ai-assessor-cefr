"""Deterministic reason-to-review routing for the W2 M07 interface pack."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from aicefr.contracts import (
    Assessment,
    AssessmentStatus,
    ReasonCode,
    ReviewCandidate,
    ReviewState,
)

REVIEW_REASONS = frozenset(
    {
        ReasonCode.QC_SILENCE_REVIEW,
        ReasonCode.QC_CLIPPING_REVIEW,
        ReasonCode.ASR_FAILED,
        ReasonCode.ASR_EMPTY_TRANSCRIPT,
        ReasonCode.ASR_HALLUCINATION,
        ReasonCode.ASR_VERSION_MISMATCH,
        ReasonCode.VAD_VERSION_MISMATCH,
        ReasonCode.FEATURE_NOT_COMPUTABLE,
        ReasonCode.TOO_FEW_WORDS,
        ReasonCode.FEATURE_VERSION_MISMATCH,
        ReasonCode.OUT_OF_DISTRIBUTION,
        ReasonCode.SCORE_NEAR_BOUNDARY,
        ReasonCode.SCORE_AGGREGATED,
        ReasonCode.MANUAL_REVIEW_REQUESTED,
        ReasonCode.MODEL_VERSION_MISSING,
        ReasonCode.MODEL_ARTIFACT_INVALID,
        ReasonCode.LANGUAGE_NOT_ENGLISH,
        ReasonCode.LANGUAGE_UNCERTAIN,
        ReasonCode.OFF_TOPIC_SUSPECTED,
        ReasonCode.PROMPT_READING_SUSPECTED,
        ReasonCode.CALIBRATION_MISSING,
        ReasonCode.CALIBRATION_HASH_MISMATCH,
        ReasonCode.CALIBRATION_INVALID,
        ReasonCode.LONG_RESPONSE_REVIEW,
    }
)


class NoReviewNeeded(ValueError):
    """The response has no approved reason route into the teacher queue."""


def routed_reasons(assessment: Assessment) -> tuple[ReasonCode, ...]:
    """Return only reasons that intentionally route to a teacher.

    Input/upload rejects remain visible to the student as rejected submissions;
    they are not silently converted into a teacher scoring candidate.
    """
    return tuple(reason for reason in assessment.reasons if reason in REVIEW_REASONS)


def review_candidate_from_assessment(
    assessment: Assessment,
    *,
    response_revision: int,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ReviewCandidate:
    reasons = routed_reasons(assessment)
    if not reasons:
        raise NoReviewNeeded("assessment has no routed review reason")
    if assessment.status not in {
        AssessmentStatus.REVIEW_REQUIRED,
        AssessmentStatus.NOT_EVALUATED,
    }:
        raise NoReviewNeeded("estimated assessment does not require a review candidate")
    now = clock()
    return ReviewCandidate(
        response_id=assessment.response_id,
        response_revision=response_revision,
        assessment_status=assessment.status,
        proposed_band=assessment.overall_band,
        reasons=reasons,
        source_versions={
            "model": assessment.provenance.model_version or "unavailable",
            "feature": assessment.provenance.feature_version or "unavailable",
            "band_map": assessment.provenance.band_map_version or "unavailable",
        },
        state=ReviewState.PENDING,
        created_at=now,
        updated_at=now,
    )
