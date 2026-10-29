"""Scores from features and maps to a CEFR band. Implements FR-18 to FR-23.

The model is a calibrated linear regression, stored as human-readable JSON
instead of a pickle. Reason: a pickle is tightly coupled to library versions and
cannot be inspected by eye during review.

UNIT OF INFERENCE: one spoken response, that is, one audio file. This is the
unit the project works with. The model was trained on parts P3 and P4 of Speak &
Improve because in those parts each exam response is a single file.

Cross-validated with GroupKFold, 5 folds grouped by speaker; the figures are
in the artifact (`cv_pcc`, `cv_rmse`), which lives outside the repository
because it is corpus statistics (W7-S01). They are LOWER than at whole-exam
level, which is exactly what to expect: a 60-second response carries less
information than a five-minute whole exam. The two numbers must not be
compared as though they came from the same problem.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from aicefr.contracts import (
    Assessment,
    Criterion,
    CriterionCoverage,
    FeatureSet,
    ReasonCode,
)
from aicefr.scoring import artifacts
from aicefr.scoring.band_map import BAND_MAP_VERSION, near_boundary, thresholds_of, to_band
from aicefr.scoring.conformal import ConformalCalibrator, weakest

# ridge_resp_v2 is ridge_resp_v1 with one term removed: `filler_ratio`, whose
# coefficient was fitted on a column that is constant zero in the training data
# and therefore carries no information. Scores are identical on every input the
# current recogniser can produce -- `tools/derive_model_v2.py` explains the
# reasoning, `tests/test_scorer.py` checks the equality.
DEFAULT_MODEL = "ridge_resp_v2"
SCORE_MIN, SCORE_MAX = 1.0, 6.0

# Which features back which criterion. Used to explain the scores.
#
# `filler_ratio` is still extracted (FR-11) but backs nothing here: the model no
# longer uses it (ridge_resp_v2), and the recogniser drops "uh"/"um", so it is
# zero on every recording. Listing it under Fluency told the student that
# hesitation words were measured when they never are (HUONG_PHAT_TRIEN_TIEP W6).
CRITERION_FEATURES: dict[Criterion, tuple[str, ...]] = {
    Criterion.RANGE: ("log_uniq", "ttr", "mean_word_len"),
    Criterion.ACCURACY: ("asr_conf_mean", "asr_conf_geo"),
    Criterion.FLUENCY: (
        "words_per_sec",
        "vad_articulation_rate",
        "vad_mean_pause",
        "vad_pause_per_min",
        "vad_long_pause_ratio",
    ),
    Criterion.COHERENCE: ("n_words", "vad_mean_seg_len", "total_dur"),
    Criterion.PHONOLOGY: ("asr_conf_mean", "vad_silence_ratio"),
}


class IncompatibleModelError(ValueError):
    """The artifact was trained on a different unit of inference.

    This is the guard against repeating the worst bug this project has had. An
    earlier model was fitted on whole exam sittings -- four parts concatenated,
    several minutes of speech per sample. This system scores ONE response:
    about a minute. Feeding a single response to that
    model produced 1.00 (A2) for a submission an expert had marked 4.00 (B2),
    and reported success while doing it.

    That artifact is still on disk, and it reports a HIGHER cross-validated
    correlation than the model actually in use. The two
    numbers describe different tasks and must never be compared. An
    administrator reading a table of models would reasonably pick the higher
    one, so the refusal has to live in the code, not in a caption.
    """


class ModelNotFoundError(FileNotFoundError):
    """The model artifact is missing. The pipeline must return MODEL_VERSION_MISSING."""


def load_model(name: str = DEFAULT_MODEL) -> dict:
    """The artifact `name` from AICEFR_MODEL_DIR, checked against its pinned SHA-256 (W7-S01)."""
    try:
        return _load_model(name, str(artifacts.model_dir()))
    except artifacts.ArtifactError as e:
        raise ModelNotFoundError(str(e)) from e


@lru_cache(maxsize=8)
def _load_model(name: str, folder: str) -> dict:
    # Keyed by the folder too: tests point AICEFR_MODEL_DIR somewhere else.
    return artifacts.read_json(name)


def out_of_distribution(features: FeatureSet, model: dict) -> list[str]:
    """List the features that fall far outside the range seen during training.

    Why this function exists: a linear regression still returns a number for ANY
    input, including a meaningless one. Without this guard the system would
    silently hand out wrong scores. A case we actually hit: a model trained at
    whole-exam level was given a one-minute response and
    returned the floor score of 1.0 for a response that was really a 4.0.
    """
    return [item["feature"] for item in out_of_distribution_detail(features, model)]


def out_of_distribution_detail(features: FeatureSet, model: dict) -> list[dict]:
    """The same check, but keeping the numbers so a person can be told why.

    Returning only feature names meant the student saw "not enough reliable
    evidence" and nothing else. For the most common cause -- a recording longer
    than anything the model was trained on -- that is the difference between a
    dead end and "your recording is 95 seconds; keep it under 75".
    """
    tol = model.get("ood_tolerance", 0.5)
    out: list[dict] = []
    for name, lo, hi in zip(
        model["feature_order"], model["feature_lo"], model["feature_hi"], strict=True
    ):
        value = features.value_of(name)
        if value is None:
            continue
        span = hi - lo
        if span <= 0:
            continue
        low_limit, high_limit = lo - tol * span, hi + tol * span
        if value < low_limit or value > high_limit:
            out.append(
                {
                    "feature": name,
                    "value": round(float(value), 3),
                    "trained_low": round(float(lo), 3),
                    "trained_high": round(float(hi), 3),
                    "accepted_low": round(float(low_limit), 3),
                    "accepted_high": round(float(high_limit), 3),
                    "too": "low" if value < low_limit else "high",
                }
            )
    return out


def predict_overall(features: FeatureSet, model: dict) -> tuple[float | None, list[ReasonCode]]:
    """Predict the overall 0-6 score. Missing features or out-of-distribution input
    means no score is produced."""
    missing = [n for n in model["feature_order"] if features.value_of(n) is None]
    if missing:
        return None, [ReasonCode.FEATURE_NOT_COMPUTABLE]
    if out_of_distribution(features, model):
        return None, [ReasonCode.OUT_OF_DISTRIBUTION]

    z = [
        (x - m) / (s or 1.0)
        for x, m, s in zip(
            features.vector(model["feature_order"]), model["mean"], model["scale"], strict=True
        )
    ]
    raw = sum(a * b for a, b in zip(z, model["coef"], strict=True)) + model["intercept"]
    return float(min(max(raw, SCORE_MIN), SCORE_MAX)), []


class RidgeScorer:
    """Scores a response with the calibrated linear (ridge) model.

    An adapter: it implements the `Scorer` port declared in `aicefr.ports`. The
    dependency only ever points one way -- this module imports the port, the
    port knows nothing about this module. That is the dependency inversion
    principle in practice: the business layer talks to `Scorer` and never names
    `RidgeScorer` or `Ridge` at all, so replacing the model with another
    implementation, or with a fake in tests, touches no business code.

    A class rather than a bare function for two reasons:

    1. The model artifact is expensive state. It is loaded once, at
       construction, and kept, instead of being fetched on every call.
    2. More importantly, every piece of provenance information (FR-27) --
       `model_version`, `feature_version`, `band_map_version`,
       `calibration_version` -- is read from that artifact rather than
       hard-coded in the source. Those values therefore describe the loaded
       artifact, which is to say they belong to the object, not to the module.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, alpha: float | None = None) -> None:
        self._model = load_model(model_name)
        self._refuse_if_wrong_unit(model_name, self._model)
        self.model_version: str = self._model["model_version"]
        self.feature_version = self._model.get("feature_version")
        # D059: the band map lives in the code (six bands, five boundaries); the
        # artifact contributes its own boundaries, not the version.
        self.band_map_version = BAND_MAP_VERSION
        self.calibration_version = self._model.get("calibration_version")
        # Exposed so the window aggregation maps its median to a band with the
        # same thresholds the artifact declares, instead of a second copy.
        self.band_thresholds: dict = thresholds_of(self._model["band_thresholds"])
        # Which recogniser and detector produced the features this model was
        # fitted on. The pipeline compares them with what is actually running.
        self.trained_with: dict = self._model.get("trained_with", {})
        # Trust Layer (D022). None khi mo hinh chua co artifact hieu chinh: khi
        # do luat bien +-boundary_margin cu van chay va `interval` de trong.
        self.calibrator = ConformalCalibrator.for_model(model_name, alpha)

    @staticmethod
    def _refuse_if_wrong_unit(model_name: str, model: dict) -> None:
        """Refuse an artifact that was not fitted on single responses.

        Loud failure at construction beats a plausible wrong number at scoring
        time. See IncompatibleModelError for what happened when this guard did
        not exist.
        """
        unit = model.get("unit_of_inference")
        if not unit:
            raise IncompatibleModelError(
                f"mô hình {model_name!r} không khai báo đơn vị suy luận nên không dùng được. "
                "Hệ thống chấm MỘT bài nói; mô hình huấn luyện ở mức cả bài thi sẽ trả về "
                "điểm sai mà vẫn báo thành công."
            )
        if "mot bai noi" not in unit and "một bài nói" not in unit:
            raise IncompatibleModelError(
                f"mô hình {model_name!r} khai báo đơn vị suy luận {unit!r}, không phải một bài nói."
            )

    def contributions(self, features: FeatureSet) -> dict[str, float]:
        """Per-feature contribution in points, for the practice priorities (FR-26).

        The model is linear, so a contribution is exactly `coef * z`. Negative
        means this measurement cost the speaker points. No feature value, no
        entry -- an absent measurement must not look like a neutral one.
        """
        m = self._model
        out: dict[str, float] = {}
        for name, mean, scale, coef in zip(
            m["feature_order"], m["mean"], m["scale"], m["coef"], strict=True
        ):
            x = features.value_of(name)
            if x is None or not scale:
                continue
            out[name] = coef * ((x - mean) / scale)
        return out

    def score(self, features: FeatureSet) -> Assessment:
        """Score the overall response and each criterion.

        Declared limitations, which must be stated whenever results are reported:
        1. The model was trained on the OVERALL score label of a response, not on
           per-criterion labels. Per-criterion scores are derived from the overall
           score plus the related features; they are not separate models.
        2. A criterion's confidence only reflects the fraction of its features that
           could be computed; it is not the probability that the score is correct.
        """
        model = self._model
        overall, reasons = predict_overall(features, model)
        th = self.band_thresholds

        criteria: list[CriterionCoverage] = []
        for crit, feats in CRITERION_FEATURES.items():
            usable = [f for f in feats if features.value_of(f) is not None]
            if overall is None or not usable:
                criteria.append(
                    CriterionCoverage(
                        criterion=crit,
                        reasons=reasons or [ReasonCode.FEATURE_NOT_COMPUTABLE],
                    )
                )
                continue
            conf = len(usable) / len(feats)
            criteria.append(
                # Khong con score_0_6 va band o day. Mo hinh co MOT dau ra;
                # ghi dung con so do vao ca nam dong tao ra nam ban sao doc
                # nhu nam phan xet doc lap. Thu that su rieng cho tung tieu chi
                # la ty le phep do tinh duoc, va do la thu duy nhat con lai.
                CriterionCoverage(
                    criterion=crit,
                    coverage=round(conf, 2),
                    reasons=[] if conf == 1.0 else [ReasonCode.FEATURE_NOT_COMPUTABLE],
                )
            )

        interval = None
        indicators = []
        if overall is not None and self.calibrator is not None:
            interval = self.calibrator.interval(features, th)
            indicators = self.calibrator.indicators(features, CRITERION_FEATURES)
        band = to_band(overall, th) if overall is not None else None

        # SCORE_NEAR_BOUNDARY giu ten cu, doi nghia (D022): khoang tin cay cham
        # hon mot band, hoac band cua diem diem khong nam trong khoang. Chi khi
        # chua co hieu chinh moi dung luat +-boundary_margin dat tay.
        if overall is not None:
            if interval is not None:
                ambiguous = not interval.is_single_band or band not in interval.band_set
            else:
                ambiguous = near_boundary(overall, th, model["boundary_margin"])
            if ambiguous:
                reasons.append(ReasonCode.SCORE_NEAR_BOUNDARY)

        return Assessment(
            overall_0_6=round(overall, 2) if overall is not None else None,
            overall_band=band,
            criteria=criteria,
            model_version=self.model_version,
            # FR-27: read from the model artifact, never hard-coded. Hard-coding it
            # means that swapping the model and forgetting to update the source would
            # declare the wrong provenance.
            feature_version=self.feature_version,
            band_map_version=self.band_map_version,
            calibration_version=self.calibration_version,
            scored_at=datetime.now(UTC).isoformat(timespec="seconds"),
            # Carried on the assessment itself, not on a local variable.
            #
            # SCORE_NEAR_BOUNDARY used to be appended to a list that was then
            # discarded: `Assessment` had no field for it, and the per-criterion
            # lists had already been built. The router looked for the flag on
            # those criteria, where it could never appear, so every response
            # sitting exactly on a band boundary went straight to COMPLETED --
            # precisely the responses the model is least sure about, and
            # precisely the case a teacher is supposed to see.
            reasons=list(dict.fromkeys(reasons)),
            out_of_range=out_of_distribution_detail(features, model),
            teacher_verified=False,
            interval=interval,
            indicators=indicators,
            weakest_criteria=weakest(indicators),
        )
