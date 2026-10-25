"""Trust Layer (D022): khoang diem CV+, tap band, chi bao theo tieu chi."""

from __future__ import annotations

import pytest
from conftest import feature_set

from aicefr.contracts import Band, Criterion, CriterionIndicator, ReasonCode
from aicefr.scoring import artifacts
from aicefr.scoring.conformal import (
    CalibrationMismatchError,
    ConformalCalibrator,
    bands_between,
    weakest,
)
from aicefr.scoring.scorer import CRITERION_FEATURES, RidgeScorer, load_model

TH = {"A2_B1": 2.75, "B1_B2": 3.75}


def _artifact() -> dict:
    return artifacts.read_json("conformal_resp_v2")


def _typical() -> dict[str, float]:
    """Moi dac trung o giua khoang huan luyen: mot bai noi 'binh thuong'."""
    m = load_model()
    return {
        n: (lo + hi) / 2
        for n, lo, hi in zip(m["feature_order"], m["feature_lo"], m["feature_hi"], strict=True)
    }


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [
        (2.0, 2.5, [Band.A2]),
        (2.75, 3.5, [Band.B1]),  # 2,75 la can duoi cua B1, khong thuoc A2
        (2.74, 2.75, [Band.A2, Band.B1]),
        (3.0, 3.75, [Band.B1, Band.B2]),
        (1.0, 6.0, [Band.A2, Band.B1, Band.B2]),
    ],
)
def test_band_set_is_every_band_the_interval_touches(low, high, expected) -> None:
    assert bands_between(low, high, TH) == expected


def test_calibration_is_bound_to_the_exact_model() -> None:
    """Hieu chinh cua mo hinh khac thi khoang van tron tria ma sai: phai tu choi."""
    art = _artifact()
    art["model_sha256"] = "0" * 64
    with pytest.raises(CalibrationMismatchError):
        ConformalCalibrator(art, artifacts.artifact_path("ridge_resp_v2"))


def test_interval_is_ordered_and_contains_the_point_estimate() -> None:
    fs = feature_set(_typical())
    a = RidgeScorer().score(fs)
    iv = a.interval
    assert iv is not None and iv.method == "cv+"
    assert iv.low <= a.overall_0_6 <= iv.high
    assert iv.coverage == pytest.approx(0.90)
    assert iv.band_set == bands_between(iv.low, iv.high, TH)


def test_a_larger_alpha_gives_a_narrower_interval() -> None:
    fs = feature_set(_typical())
    widths = []
    for alpha in (0.05, 0.10, 0.20, 0.30):
        iv = ConformalCalibrator.for_model("ridge_resp_v2", alpha).interval(fs, TH)
        widths.append(iv.high - iv.low)
    assert widths == sorted(widths, reverse=True)


def test_alpha_outside_the_sane_range_is_refused() -> None:
    with pytest.raises(ValueError):
        ConformalCalibrator(_artifact(), artifacts.artifact_path("ridge_resp_v2"), alpha=0.6)


def test_an_interval_touching_two_bands_goes_to_a_teacher() -> None:
    a = RidgeScorer().score(feature_set(_typical()))
    assert len(a.interval.band_set) >= 2
    assert ReasonCode.SCORE_NEAR_BOUNDARY in a.reasons


def _strong(frac: float) -> dict[str, float]:
    """Moi dac trung dat `frac` khoang huan luyen theo chieu lam diem tang."""
    m = load_model()
    return {
        n: lo + (hi - lo) * (frac if c > 0 else 1 - frac)
        for n, c, lo, hi in zip(
            m["feature_order"], m["coef"], m["feature_lo"], m["feature_hi"], strict=True
        )
    }


def test_a_clearly_strong_response_gets_its_band_without_a_teacher() -> None:
    """Khoang 90% nam gon trong B2 thi may duoc phat band, khong co co bien."""
    a = RidgeScorer().score(feature_set(_strong(0.9)))
    assert a.interval.band_set == [Band.B2] and a.overall_band is Band.B2
    assert ReasonCode.SCORE_NEAR_BOUNDARY not in a.reasons


def test_the_same_response_at_a_looser_alpha_can_be_auto_banded() -> None:
    """Cung bai: alpha 0,10 cham B1 va B2, alpha 0,30 chi con B2.

    Doi alpha la doi tai giang vien -- day la nut dieu chinh, khong phai mot hang so.
    """
    fs = feature_set(_strong(0.75))
    strict, loose = RidgeScorer(alpha=0.10).score(fs), RidgeScorer(alpha=0.30).score(fs)
    assert strict.interval.band_set == [Band.B1, Band.B2]
    assert ReasonCode.SCORE_NEAR_BOUNDARY in strict.reasons
    assert loose.interval.band_set == [Band.B2]
    assert ReasonCode.SCORE_NEAR_BOUNDARY not in loose.reasons


def test_without_a_calibration_the_old_margin_rule_still_runs() -> None:
    scorer = RidgeScorer()
    scorer.calibrator = None
    a = scorer.score(feature_set(_typical()))
    assert a.interval is None and a.indicators == []
    m = load_model()
    near = any(abs(a.overall_0_6 - t) <= m["boundary_margin"] for t in TH.values())
    assert (ReasonCode.SCORE_NEAR_BOUNDARY in a.reasons) == near


def test_no_score_means_no_interval_and_no_indicators() -> None:
    values = _typical()
    values["n_words"] = None
    a = RidgeScorer().score(feature_set(values))
    assert a.overall_0_6 is None
    assert a.interval is None and a.indicators == [] and a.weakest_criteria == []


def test_measured_coverage_matches_the_nominal_level() -> None:
    """Muc phu DO DUOC (CV long nhau, S&I) phai sat 1 - alpha.

    Ghim lai de mot artifact hong hoac mot lan hieu chinh sai khong lot qua im
    lang.
    """
    curve = {row["alpha"]: row for row in _artifact()["alpha_curve"]}
    for alpha, row in curve.items():
        assert abs(row["coverage"] - (1 - alpha)) <= 0.03, row
    assert curve[0.10]["gross_error_rate_in_auto"] <= 0.05


def test_indicators_are_positions_not_scores() -> None:
    a = RidgeScorer().score(feature_set(_typical()))
    assert a.indicators
    for ind in a.indicators:
        assert 0.0 <= ind.percentile <= 1.0
        assert ind.feature in CRITERION_FEATURES[ind.criterion]
    # filler_ratio la hang so trong luc chay nen khong co phan bo tham chieu
    assert all(ind.feature != "filler_ratio" for ind in a.indicators)


def test_a_missing_measurement_has_no_indicator() -> None:
    cal = ConformalCalibrator.for_model("ridge_resp_v2")
    values = _typical()
    values["ttr"] = None
    inds = cal.indicators(feature_set(values), CRITERION_FEATURES)
    assert "ttr" not in {i.feature for i in inds}


def test_weakest_is_the_lowest_average_standing() -> None:
    def ind(crit, pct, higher=True):
        return CriterionIndicator(
            criterion=crit, feature="x", value=1.0, percentile=pct, higher_is_better=higher
        )

    rows = [
        ind(Criterion.FLUENCY, 0.8),
        ind(Criterion.RANGE, 0.3),
        ind(Criterion.ACCURACY, 0.9, higher=False),  # standing 0,1 -> yeu nhat
    ]
    assert weakest(rows) == [Criterion.ACCURACY]
    assert weakest([]) == []
