"""Deterministic next-mission recommendations from eligible assessment evidence."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from aicefr.contracts import AssessmentStatus, Band, Criterion
from aicefr.practice.bank import PRACTICE_MISSIONS
from aicefr.practice.contracts import (
    Recommendation,
    RecommendationEvidence,
    RecommendationReasonCode,
)

CRITERION_ORDER = (
    Criterion.FLUENCY,
    Criterion.COHERENCE,
    Criterion.RANGE,
    Criterion.ACCURACY,
    Criterion.PHONOLOGY,
)
BAND_ORDER = (Band.A2, Band.B1, Band.B2)


def _nearest_band(band: Band | None) -> Band:
    return band if band in BAND_ORDER else Band.A2


def recommend_next(
    *,
    assessments: Sequence[RecommendationEvidence],
    completed_mission_ids: Collection[str] = (),
) -> Recommendation:
    """Recommend a mission; practice results are intentionally not accepted here."""
    eligible = [
        assessment
        for assessment in assessments
        if assessment.status in (AssessmentStatus.ESTIMATED, AssessmentStatus.REVIEW_REQUIRED)
        and assessment.overall_score is not None
        and assessment.overall_band is not None
    ]
    newest = max(eligible, key=lambda item: (item.created_at, item.response_id), default=None)
    if newest is None:
        criterion, band = Criterion.FLUENCY, Band.A2
        reason_code = RecommendationReasonCode.NO_ELIGIBLE_ASSESSMENT_FALLBACK_A2
        explanation = "Chưa có bài đánh giá đủ điều kiện; bắt đầu với nhiệm vụ A2 về độ trôi chảy."
    else:
        # Lower criterion coverage means weaker evidence, not a criterion score.
        coverage = {item.criterion: item.coverage for item in newest.criteria}
        criterion = min(
            CRITERION_ORDER,
            key=lambda item: (
                coverage.get(item) is not None,
                coverage.get(item) if coverage.get(item) is not None else 0.0,
                CRITERION_ORDER.index(item),
            ),
        )
        band = _nearest_band(newest.overall_band)
        reason_code = RecommendationReasonCode.WEAKEST_COVERAGE_NEAREST_BAND
        explanation = (
            f"Gợi ý luyện {criterion.value} ở band gần nhất {band.value}, "
            "dựa trên coverage thấp nhất."
        )
    candidates = [
        mission
        for mission in PRACTICE_MISSIONS
        if mission.criterion is criterion and mission.mission_id not in completed_mission_ids
    ]
    if not candidates:
        candidates = [mission for mission in PRACTICE_MISSIONS if mission.criterion is criterion]
    mission = min(
        candidates,
        key=lambda item: (
            abs(BAND_ORDER.index(item.target_band) - BAND_ORDER.index(band)),
            BAND_ORDER.index(item.target_band),
            item.mission_id,
        ),
    )
    return Recommendation(
        mission_id=mission.mission_id,
        criterion=mission.criterion,
        target_band=mission.target_band,
        reason_code=reason_code,
        explanation=explanation,
    )
