"""Fusion scorer: Ridge on the 18 measurements + DeBERTa-v3 LoRA on the transcript.

Chosen in the internal experiment report (chapter "Thực nghiệm", sections 6.4
and 6.8): out of fold it beats Ridge v4 alone, significantly under a paired
speaker bootstrap and for every seed tried, and the text model adds a small
fraction of the recogniser's CPU time. The figures are corpus statistics, so
they live in that report and in the artifact, never in this public repository
(W7-S01).

The score is a linear stack fitted on out-of-fold predictions:

    score = intercept + w_ridge * clip(ridge, 1, 6) + w_text * deberta

clipped to 1-6. When the transcript is missing or the text model fails, the
scorer returns Ridge v4 on its own and says so through `model_version`
(`ridge_resp_v4`, an artifact that exists on disk with the same coefficients),
so a stored report never claims a model that did not produce its number.

The 90 % interval is the score +/- the (1 - alpha) quantile of out-of-fold
absolute residuals, measured for the fusion and for Ridge alone (fallback).
A response goes to a teacher (SCORE_NEAR_BOUNDARY) whenever the interval
spans more than one band, exactly as with the CV+ interval of `RidgeScorer`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from aicefr.contracts import Assessment, FeatureSet, ReasonCode, ScoreInterval
from aicefr.scoring import artifacts
from aicefr.scoring.band_map import BAND_MAP_VERSION, bands_between, thresholds_of, to_band
from aicefr.scoring.conformal import reference_indicators, weakest
from aicefr.scoring.scorer import (
    CRITERION_FEATURES,
    SCORE_MAX,
    SCORE_MIN,
    IncompatibleModelError,
    RidgeScorer,
    criteria_coverage,
    load_model,
    out_of_distribution_detail,
    predict_overall,
)
from aicefr.scoring.text_model import DebertaTextModel

logger = logging.getLogger(__name__)

# The ridge half must be the very model the fallback artifact holds.
RIDGE_FIELDS = ("feature_order", "mean", "scale", "coef", "intercept", "feature_lo", "feature_hi")


def is_fusion_artifact(model: dict) -> bool:
    return "text_model" in model and "fusion" in model


class DebertaScorer:
    """The `Scorer` port over a fusion artifact (`tools/build_fusion_artifact.py`).

    `text_model` is injectable so tests, and a machine without torch, can run
    the full scoring logic with a stand-in.
    """

    def __init__(self, model_name: str, alpha: float | None = None, text_model=None) -> None:
        model = load_model(model_name)
        if not is_fusion_artifact(model):
            raise IncompatibleModelError(f"{model_name!r} không phải artifact mô hình ghép")
        RidgeScorer._refuse_if_wrong_unit(model_name, model)
        self._model = model
        self._fusion: dict = model["fusion"]
        self._interval: dict = model["interval"]
        self.ridge_model_version: str = model["ridge_model"]
        ridge = load_model(self.ridge_model_version)
        differs = [k for k in RIDGE_FIELDS if ridge.get(k) != model.get(k)]
        if differs:
            raise IncompatibleModelError(
                f"phần Ridge của {model_name!r} khác artifact dự phòng "
                f"{self.ridge_model_version!r} ở {differs}"
            )
        if alpha is not None and abs(alpha - self._interval["alpha"]) > 1e-9:
            raise ValueError(
                f"{model_name!r} chỉ có khoảng tin cậy cho alpha = {self._interval['alpha']}"
            )

        self.model_version: str = model["model_version"]
        self.feature_version = model.get("feature_version")
        self.band_map_version = BAND_MAP_VERSION
        self.calibration_version = model.get("calibration_version")
        self.band_thresholds: dict = thresholds_of(model["band_thresholds"])
        self.trained_with: dict = model.get("trained_with", {})
        self.calibrator = None  # the interval comes from `interval`, not a CV+ artifact
        self.text_model = text_model or DebertaTextModel(model["text_model"], artifacts.model_dir())

    def missing_files(self) -> list[str]:
        """Text-model files not on disk (cheap); for activation and readiness checks."""
        check = getattr(self.text_model, "missing_files", None)
        return check() if callable(check) else []

    def contributions(self, features: FeatureSet) -> dict[str, float]:
        """Per-feature points in the FUSED score: the ridge term `coef * z` times `w_ridge`.

        Only the measurement half can be split by feature; the text model's
        share is not attributed. When the text model was unavailable the
        response was scored by Ridge alone, and these figures understate each
        term by the factor `w_ridge`.
        """
        m, w = self._model, self._fusion["w_ridge"]
        out: dict[str, float] = {}
        for name, mean, scale, coef in zip(
            m["feature_order"], m["mean"], m["scale"], m["coef"], strict=True
        ):
            x = features.value_of(name)
            if x is None or not scale:
                continue
            out[name] = w * coef * ((x - mean) / scale)
        return out

    def _text_score(self, text: str | None) -> float | None:
        if not text or not text.strip():
            return None
        try:
            return self.text_model.predict(text)
        except Exception:  # noqa: BLE001 - fall back to Ridge alone, never lose the response
            logger.exception("text model failed; scoring with %s alone", self.ridge_model_version)
            return None

    def score(self, features: FeatureSet, text: str | None = None) -> Assessment:
        model = self._model
        th = self.band_thresholds
        ridge, reasons = predict_overall(features, model)

        overall, version, q, calibration = None, self.model_version, None, self.calibration_version
        if ridge is not None:
            text_score = self._text_score(text)
            if text_score is None:
                overall, version = ridge, self.ridge_model_version
                q, calibration = self._interval["q_ridge"], f"{self.calibration_version}-ridge"
            else:
                f = self._fusion
                raw = f["intercept"] + f["w_ridge"] * ridge + f["w_text"] * text_score
                overall = float(min(max(raw, SCORE_MIN), SCORE_MAX))
                q = self._interval["q_fusion"]

        interval = None
        indicators = []
        band = None
        if overall is not None:
            low = round(max(overall - q, SCORE_MIN), 2)
            high = round(min(overall + q, SCORE_MAX), 2)
            interval = ScoreInterval(
                low=low,
                high=high,
                band_set=bands_between(low, high, th),
                coverage=round(1 - self._interval["alpha"], 4),
                method=self._interval["method"],
                calibration_version=calibration,
            )
            indicators = reference_indicators(
                features, model.get("indicator_reference", {}), CRITERION_FEATURES
            )
            band = to_band(overall, th)
            if not interval.is_single_band or band not in interval.band_set:
                reasons.append(ReasonCode.SCORE_NEAR_BOUNDARY)

        return Assessment(
            overall_0_6=round(overall, 2) if overall is not None else None,
            overall_band=band,
            criteria=criteria_coverage(features, overall, reasons),
            model_version=version,
            feature_version=self.feature_version,
            band_map_version=self.band_map_version,
            calibration_version=calibration,
            scored_at=datetime.now(UTC).isoformat(timespec="seconds"),
            reasons=list(dict.fromkeys(reasons)),
            out_of_range=out_of_distribution_detail(features, model),
            teacher_verified=False,
            interval=interval,
            indicators=indicators,
            weakest_criteria=weakest(indicators),
        )
