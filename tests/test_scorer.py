"""Scoring tests. The focus: never score at random when the input is abnormal."""

import pytest
from conftest import feature_set

from aicefr.contracts import Band, FeatureSet, ReasonCode
from aicefr.ports import Scorer
from aicefr.scoring.scorer import (
    DEFAULT_MODEL,
    RidgeScorer,
    load_model,
    out_of_distribution,
    to_band,
)


@pytest.fixture
def model() -> dict:
    return load_model(DEFAULT_MODEL)


@pytest.fixture
def typical(model) -> FeatureSet:
    """Features sitting in the middle of the training range."""
    mid = {
        n: (lo + hi) / 2
        for n, lo, hi in zip(
            model["feature_order"], model["feature_lo"], model["feature_hi"], strict=True
        )
    }
    return feature_set(mid)


def test_model_operates_at_single_response_level(model):
    assert "mot bai noi" in model["unit_of_inference"]
    assert model["cv_scheme"].startswith("GroupKFold")


def test_normal_input_is_scored(typical):
    a = RidgeScorer().score(typical)
    assert a.overall_0_6 is not None
    assert 1.0 <= a.overall_0_6 <= 6.0
    assert a.overall_band in set(Band)
    assert len(a.criteria) == 5


def test_band_mapping_by_threshold():
    th = {"A2_B1": 2.75, "B1_B2": 3.75}
    assert to_band(2.0, th) is Band.A2
    assert to_band(3.0, th) is Band.B1
    assert to_band(5.0, th) is Band.B2


def test_missing_features_prevent_scoring(typical):
    typical = feature_set({**{f.name: f.value for f in typical.items}, "n_words": None})
    a = RidgeScorer().score(typical)
    assert a.overall_0_6 is None
    assert ReasonCode.FEATURE_NOT_COMPUTABLE in a.criteria[0].reasons


def test_out_of_distribution_input_refuses_scoring(typical, model):
    """A bug seen for real: a whole-corpus-level model would take any single response and
    hand back a score regardless."""
    typical = feature_set(
        {**{f.name: f.value for f in typical.items}, "n_words": model["feature_hi"][0] * 10}
    )
    assert out_of_distribution(typical, model)
    a = RidgeScorer().score(typical)
    assert a.overall_0_6 is None
    assert ReasonCode.OUT_OF_DISTRIBUTION in a.criteria[0].reasons


def test_in_range_features_not_flagged_out_of_distribution(typical, model):
    assert out_of_distribution(typical, model) == []


def test_never_sets_teacher_verified_by_itself(typical):
    assert RidgeScorer().score(typical).teacher_verified is False


def test_ridge_scorer_satisfies_scorer_port():
    assert isinstance(RidgeScorer(), Scorer)


def test_v2_cho_diem_y_het_v1_tren_moi_dau_vao_thuc_te() -> None:
    """Bỏ `filler_ratio` không được làm điểm đổi. FR-11.

    `filler_ratio` bằng 0 trong toàn bộ tập huấn luyện và cũng bằng 0 với bộ
    nhận dạng đang chạy, nên hệ số của nó không xác định được. Bỏ một số hạng
    luôn bằng không khác hẳn với sửa một hệ số đã khớp dữ liệu — và đây là chỗ
    chứng minh điều đó.
    """
    import numpy as np

    from aicefr.scoring.scorer import RidgeScorer, load_model

    v1, v2 = RidgeScorer("ridge_resp_v1"), RidgeScorer("ridge_resp_v2")
    m = load_model("ridge_resp_v1")
    rng = np.random.default_rng(20260913)

    for _ in range(50):
        values = {
            name: float(rng.uniform(lo, hi))
            for name, lo, hi in zip(
                m["feature_order"], m["feature_lo"], m["feature_hi"], strict=True
            )
        }
        values["filler_ratio"] = 0.0  # điều bộ nhận dạng hiện tại luôn sinh ra
        fs = feature_set(values)
        assert v1.score(fs).overall_0_6 == v2.score(fs).overall_0_6


def test_v2_khong_con_dac_trung_filler_ratio() -> None:
    from aicefr.scoring.scorer import load_model

    assert "filler_ratio" not in load_model("ridge_resp_v2")["feature_order"]
    assert len(load_model("ridge_resp_v2")["feature_order"]) == 18


def test_v2_ghi_ro_no_duoc_dan_xuat_tu_dau() -> None:
    """Một artifact không nói được nó từ đâu ra thì không bảo vệ được."""
    from aicefr.scoring.scorer import load_model

    m = load_model("ridge_resp_v2")
    assert m["derived_from"] == "ridge_resp_v1"
    assert "hằng số" in m["derivation"]
