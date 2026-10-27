"""The calibrated artifact (D052): variance restoration plus refitted band thresholds."""

import pytest
from conftest import feature_set

from aicefr.contracts import Band
from aicefr.scoring.scorer import RidgeScorer, load_model

BASE, CAL = "ridge_resp_v2", "ridge_resp_v2_cal"


@pytest.fixture(scope="module")
def cal() -> dict:
    return load_model(CAL)


def test_the_calibrated_score_is_the_base_score_stretched_around_mu(cal) -> None:
    import numpy as np

    base, calibrated = RidgeScorer(BASE), RidgeScorer(CAL)
    mu, lam = cal["calibration"]["mu"], cal["calibration"]["lambda"]
    rng = np.random.default_rng(20261024)
    for _ in range(40):
        fs = feature_set(
            {
                n: float(rng.uniform(lo, hi))
                for n, lo, hi in zip(
                    cal["feature_order"], cal["feature_lo"], cal["feature_hi"], strict=True
                )
            }
        )
        b, c = base.score(fs).overall_0_6, calibrated.score(fs).overall_0_6
        if 1.0 < b < 6.0:
            expected = min(max(mu + lam * (b - mu), 1.0), 6.0)
            assert c == pytest.approx(expected, abs=0.02)


def test_it_stretches_and_never_shrinks(cal) -> None:
    assert 1.0 <= cal["calibration"]["lambda"] <= 1.436


def test_its_own_thresholds_band_its_own_scores(cal) -> None:
    th = cal["band_thresholds"]
    assert th["A2_B1"] < th["B1_B2"]
    scorer = RidgeScorer(CAL)
    assert scorer.band_thresholds == th


def test_it_says_where_it_came_from(cal) -> None:
    import hashlib

    from aicefr.scoring import artifacts

    assert cal["derived_from"] == BASE
    digest = hashlib.sha256(artifacts.artifact_path(BASE).read_bytes()).hexdigest()
    assert cal["derived_from_sha256"] == digest
    assert "nested_evaluation" in cal["calibration"]


def test_the_report_keeps_its_not_calibrated_warning(cal) -> None:
    """Fitted on S&I learners, not Vietnamese students: SRS 11.3 keeps the warning."""
    from aicefr.contracts import Assessment

    a = Assessment(
        overall_0_6=3.0,
        overall_band=Band.B1,
        model_version=CAL,
        calibration_version=cal["calibration_version"],
    )
    assert a.is_calibrated is False


def test_it_has_its_own_intervals() -> None:
    scorer = RidgeScorer(CAL)
    assert scorer.calibrator is not None
    assert "cal" in scorer.calibrator.version


def test_the_default_model_is_unchanged() -> None:
    """Activation is an administrator's choice (FR-36), never a silent default."""
    from aicefr.scoring.scorer import DEFAULT_MODEL

    assert DEFAULT_MODEL == BASE
