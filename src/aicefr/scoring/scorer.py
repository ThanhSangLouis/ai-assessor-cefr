"""Scorer M05: thứ tự kiểm fail-closed 8 bước (M05 Spec v0.2).

Dừng ở bước đầu tiên thất bại và trả `NOT_EVALUATED` không có điểm. Có điểm
nhưng gần ranh giới band thì `REVIEW_REQUIRED`. Mọi kết quả là ước lượng thử
nghiệm, `teacher_verified=False` cho đến khi giảng viên xác nhận (M07).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from aicefr.contracts import (
    AsrStatus,
    Assessment,
    AssessmentStatus,
    FeatureSet,
    OutOfRangeFeature,
    Provenance,
    ReasonCode,
    Transcript,
)
from aicefr.scoring.artifact import (
    RIDGE_RESP_V2_SHA256,
    ModelArtifact,
    ModelArtifactError,
    default_artifact_path,
    load_artifact,
)
from aicefr.scoring.coverage import criterion_coverage, not_evaluated_coverage
from aicefr.scoring.ridge import near_boundary, ood_detail, predict, to_band

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def provenance_mismatches(features: FeatureSet, artifact: ModelArtifact) -> tuple[ReasonCode, ...]:
    """Bước 4 (M05-FR-003): so bằng `==`, gộp mọi mục lệch."""
    trained = artifact.trained_with
    reasons: list[ReasonCode] = []
    if "asr_model" in trained and features.asr_model != trained["asr_model"]:
        reasons.append(ReasonCode.ASR_VERSION_MISMATCH)
    vad_pairs = (
        ("vad_name", features.vad_name),
        ("vad_threshold", features.vad_threshold),
        ("vad_min_silence_ms", features.vad_min_silence_ms),
    )
    if any(key in trained and value != trained[key] for key, value in vad_pairs):
        reasons.append(ReasonCode.VAD_VERSION_MISMATCH)
    if (
        features.names() != artifact.feature_order
        or features.feature_version != artifact.feature_version
    ):
        reasons.append(ReasonCode.FEATURE_VERSION_MISMATCH)
    return tuple(reasons)


class RidgeScorer:
    """Chấm một bài nói bằng artifact Ridge đã kiểm hash.

    Nạp artifact một lần khi khởi tạo. Nạp lỗi không ném ra ngoài: mọi lần chấm
    sau đó trả `NOT_EVALUATED` với reason của lỗi (bước 1–2).
    """

    def __init__(
        self,
        artifact: ModelArtifact | None = None,
        load_error: ModelArtifactError | None = None,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        if (artifact is None) == (load_error is None):
            raise ValueError("cần đúng một trong artifact hoặc load_error")
        self._artifact = artifact
        self._load_error = load_error
        self._clock = clock

    @property
    def artifact(self) -> ModelArtifact | None:
        """The loaded artifact, or None when loading failed (W4-S3).

        The coordinator needs it to build the M04 extractor from the same
        `feature_order` (`FeatureExtractor.from_artifact`) and to read the window
        policy; reaching into `_artifact` for that couples it to a private name.
        """
        return self._artifact

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        expected_sha256: str = RIDGE_RESP_V2_SHA256,
        clock: Callable[[], str] = _utc_now,
    ) -> RidgeScorer:
        try:
            artifact = load_artifact(path or default_artifact_path(), expected_sha256)
        except ModelArtifactError as err:
            return cls(load_error=err, clock=clock)
        return cls(artifact=artifact, clock=clock)

    def score(self, features: FeatureSet, transcript: Transcript) -> Assessment:
        assessment = self._evaluate(features, transcript)
        log.info(
            "scored response_id=%s status=%s reasons=%s model_version=%s",
            assessment.response_id,
            assessment.status.value,
            ",".join(r.value for r in assessment.reasons) or "-",
            assessment.provenance.model_version or "-",
        )
        return assessment

    def _evaluate(self, features: FeatureSet, transcript: Transcript) -> Assessment:
        art = self._artifact
        # Bước 1–2: artifact. __init__ bảo đảm có đúng một trong artifact / load_error.
        if art is None:
            reason = (
                self._load_error.reason if self._load_error else ReasonCode.MODEL_VERSION_MISSING
            )
            return self._not_evaluated(features, (reason,))
        # Bước 3: transcript phải OK.
        if transcript.status is not AsrStatus.OK:
            return self._not_evaluated(features, tuple(transcript.reasons))
        if (len(art.scale) != len(art.feature_order)
                or any(not math.isfinite(value) or value <= 0 for value in art.scale)):
            return self._not_evaluated(features, (ReasonCode.MODEL_ARTIFACT_INVALID,))
        # Bước 4: provenance.
        mismatches = provenance_mismatches(features, art)
        if mismatches:
            return self._not_evaluated(features, mismatches)
        names = features.names()
        if names != art.feature_order or len(set(names)) != len(names):
            return self._not_evaluated(features, (ReasonCode.FEATURE_VERSION_MISMATCH,))
        values = {v.name: v.value for v in features.values}
        if any(value is not None and not math.isfinite(value) for value in values.values()):
            return self._not_evaluated(features, (ReasonCode.FEATURE_NOT_COMPUTABLE,))
        # Bước 5: không đặc trưng nào None.
        if any(values[name] is None for name in art.feature_order):
            return self._not_evaluated(features, (ReasonCode.FEATURE_NOT_COMPUTABLE,))
        # Bước 6: OOD.
        findings = ood_detail(values, art)
        if findings:
            detail = tuple(
                OutOfRangeFeature(
                    feature=f.feature,
                    value=f.value,
                    accepted_low=f.accepted_low,
                    accepted_high=f.accepted_high,
                    too=f.too,
                )
                for f in findings
            )
            return self._not_evaluated(
                features, (ReasonCode.OUT_OF_DISTRIBUTION,), out_of_range=detail
            )
        # Bước 7–8: điểm, band, near-boundary.
        score = predict(values, art)
        if not math.isfinite(score):
            return self._not_evaluated(features, (ReasonCode.MODEL_ARTIFACT_INVALID,))
        near = near_boundary(score, art.band_thresholds, art.boundary_margin)
        return Assessment(
            response_id=features.response_id,
            status=AssessmentStatus.REVIEW_REQUIRED if near else AssessmentStatus.ESTIMATED,
            overall_score=score,
            overall_band=to_band(score, art.band_thresholds),
            criteria=criterion_coverage(values, art.feature_order),
            reasons=(ReasonCode.SCORE_NEAR_BOUNDARY,) if near else (),
            provenance=self._provenance(),
        )

    def _not_evaluated(
        self,
        features: FeatureSet,
        reasons: tuple[ReasonCode, ...],
        out_of_range: tuple[OutOfRangeFeature, ...] = (),
    ) -> Assessment:
        return Assessment(
            response_id=features.response_id,
            status=AssessmentStatus.NOT_EVALUATED,
            criteria=not_evaluated_coverage(reasons),
            reasons=reasons,
            out_of_range=out_of_range,
            provenance=self._provenance(),
        )

    def _provenance(self) -> Provenance:
        art = self._artifact
        if art is None:
            return Provenance(
                model_version=None,
                model_sha256=None,
                feature_version=None,
                band_map_version=None,
                calibration_version=None,
                unit_of_inference=None,
                scored_at=self._clock(),
            )
        return Provenance(
            model_version=art.model_version,
            model_sha256=art.sha256,
            feature_version=art.feature_version,
            band_map_version=art.band_map_version,
            calibration_version=art.calibration_version,
            trained_with=dict(art.trained_with),
            unit_of_inference=art.unit_of_inference,
            scored_at=self._clock(),
        )
