"""Data-contract tests. The Interaction criterion must be excluded per QD-04."""

import pytest
from pydantic import ValidationError

from aicefr.contracts import (
    Band,
    Criterion,
    Feature,
    FeatureSet,
    ReasonCode,
    Response,
    ResponseStatus,
)


def test_exactly_five_criteria():
    assert len(list(Criterion)) == 5
    assert "interaction" not in {c.value for c in Criterion}


def test_six_bands_within_scope():
    """D059: the whole CEFR scale, A1 to C2, in order."""
    assert [b.value for b in Band] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert [b.rank for b in Band] == list(range(6))


def test_minimal_report_is_valid():
    r = Response(response_id="r1", status=ResponseStatus.FAILED, config_version="v1")
    assert r.assessment is None
    assert r.reasons == []


def test_every_reason_code_is_uppercase():
    for code in ReasonCode:
        assert code.value.isupper()


# ------------------------------------------------------- Feature: mot so HOAC mot ly do


def test_a_feature_with_no_value_must_carry_a_reason():
    """Day chinh la lo hong cua thiet ke cu, dung bang mot kieu.

    Truoc day `FeatureSet` giu hai bang song song: `values` va `invalid`. Mot
    dac trung co the nam trong `values` voi gia tri None ma khong co dong nao
    trong `invalid` -- va that su da xay ra voi `asr_conf_mean`. Nguoi doc bao
    cao thay mot phep do trong, khong biet vi sao.
    """
    with pytest.raises(ValidationError):
        Feature(name="asr_conf_mean", value=None, reason=None)


def test_a_feature_with_a_value_must_not_carry_a_reason():
    """Chieu nguoc lai cung la mot mau thuan: co so do roi thi khong con ly do vang."""
    with pytest.raises(ValidationError):
        Feature(name="n_words", value=42.0, reason=ReasonCode.TOO_FEW_WORDS)


def test_a_feature_set_refuses_the_same_name_twice():
    """Hai phep do cung ten thi `value_of` tra ve cai nao? Cau hoi khong duoc phep ton tai."""
    with pytest.raises(ValidationError):
        FeatureSet(
            items=[
                Feature(name="ttr", value=0.5),
                Feature(name="ttr", value=0.6),
            ],
            feature_version="v3",
        )


def test_scoring_vector_refuses_a_hole_instead_of_filling_it():
    """Mot vector cham diem thieu mot o phai bao loi, khong duoc lang le thay bang 0.

    Neu thay bang 0 thi ket qua tra ve la mot con so trong khoang 0-6, nhin
    khong khac gi moi con so hop le khac -- khong ai phat hien duoc.
    """
    fs = FeatureSet(
        items=[
            Feature(name="n_words", value=42.0),
            Feature(name="ttr", value=None, reason=ReasonCode.TOO_FEW_WORDS),
        ],
        feature_version="v3",
    )
    assert fs.vector(["n_words"]) == [42.0]
    with pytest.raises(ValueError, match="khong tinh duoc"):
        fs.vector(["n_words", "ttr"])
