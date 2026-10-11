import logging

import pytest

from aicefr.contracts import (
    AsrStatus,
    AssessmentStatus,
    Band,
    Criterion,
    FeatureSet,
    FeatureValue,
    ReasonCode,
    Transcript,
)
from aicefr.scoring.coverage import criterion_coverage
from aicefr.scoring.scorer import RidgeScorer

FIXED_CLOCK = "2026-09-26T00:00:00+00:00"


def make_fs(order, values, **overrides):
    fields = {
        "response_id": "r1",
        "values": tuple(FeatureValue(name=n, value=values[n], unit="-") for n in order),
        "feature_version": "v3",
        "vad_name": "silero",
        "vad_version": "6.2.1",
        "vad_threshold": 0.5,
        "vad_min_silence_ms": 150,
        "asr_model": "whisper-small",
        "transcript_ref": "t1",
        "audio_sha256": "0" * 64,
    }
    fields.update(overrides)
    return FeatureSet(**fields)


def make_transcript(status=AsrStatus.OK, reasons=()):
    return Transcript(
        response_id="r1",
        status=status,
        engine="faster-whisper",
        engine_version="fixture",
        decode_config_version="asr-decode-v1",
        audio_sha256="0" * 64,
        reasons=reasons,
        test_only=True,
    )


def scorer_for(artifact):
    return RidgeScorer(artifact=artifact, clock=lambda: FIXED_CLOCK)


def vec(artifact, name):
    return dict(zip(artifact.feature_order, getattr(artifact, name), strict=True))


# --- M05-TEST-001 / 003: giá trị vàng trên artifact thật -------------------------


def expected_from_spec(art, values):
    """The M05 Spec formula restated, so the expectation is read from the artifact
    itself rather than from numbers copied into a public repository: the artifact's
    statistics come from S&I, whose licence forbids publishing them (W4-S4)."""
    raw = art.intercept + sum(
        coef * (values[name] - mean) / (scale or 1.0)
        for name, mean, scale, coef in zip(
            art.feature_order, art.mean, art.scale, art.coef, strict=True
        )
    )
    score = min(max(raw, 1.0), 6.0)
    t = art.band_thresholds
    band = Band.A2 if score < t["A2_B1"] else Band.B1 if score < t["B1_B2"] else Band.B2
    near = any(abs(score - x) <= art.boundary_margin for x in t.values())
    return score, band, AssessmentStatus.REVIEW_REQUIRED if near else AssessmentStatus.ESTIMATED


@pytest.mark.parametrize("vector", ["mean", "feature_lo", "feature_hi"])
def test_golden_vectors_on_real_artifact(real_artifact, vector):
    """M05-TEST-001."""
    art = real_artifact
    values = vec(art, vector)
    score, band, status = expected_from_spec(art, values)
    if vector == "mean":
        assert score == pytest.approx(art.intercept)  # every z = 0
    a = scorer_for(art).score(make_fs(art.feature_order, values), make_transcript())
    assert a.overall_score == pytest.approx(score, abs=1e-4)
    assert a.overall_band is band
    assert a.status is status
    p = a.provenance
    assert (p.model_version, p.model_sha256, p.feature_version) == (
        art.model_version,
        art.sha256,
        art.feature_version,
    )
    assert (p.band_map_version, p.calibration_version) == (
        art.band_map_version,
        art.calibration_version,
    )
    assert p.trained_with == art.trained_with and p.unit_of_inference == art.unit_of_inference


def test_full_features_give_full_coverage_without_scores(real_artifact):
    """M05-TEST-003: 5 dòng coverage = 1,0; fluency không còn bị filler_ratio kéo xuống."""
    art = real_artifact
    a = scorer_for(art).score(make_fs(art.feature_order, vec(art, "feature_hi")), make_transcript())
    assert [c.criterion for c in a.criteria] == list(Criterion)
    assert all(c.coverage == 1.0 and c.reasons == () for c in a.criteria)
    assert not {"score", "band"} & set(type(a.criteria[0]).model_fields)


# --- chạy được trên CI với ART-FAKE18 -----------------------------------------


@pytest.fixture
def mid(fake18):
    """Mọi đặc trưng 0,5 → điểm 3,0 (B1, cách 2 ngưỡng 0,25 → near-boundary)."""
    return {n: 0.5 for n in fake18.feature_order}


def test_score_is_deterministic_apart_from_timestamp(fake18, mid):
    """M05-TEST-002."""
    fs, tr = make_fs(fake18.feature_order, mid), make_transcript()
    first = RidgeScorer(artifact=fake18).score(fs, tr)
    second = RidgeScorer(artifact=fake18).score(fs, tr)
    strip = {"provenance": {"scored_at"}}
    assert first.model_dump(exclude=strip) == second.model_dump(exclude=strip)


def test_estimated_and_review_statuses(fake18, mid):
    s = scorer_for(fake18)
    near = s.score(make_fs(fake18.feature_order, mid), make_transcript())
    assert near.status is AssessmentStatus.REVIEW_REQUIRED
    assert near.reasons == (ReasonCode.SCORE_NEAR_BOUNDARY,)
    assert near.overall_band is Band.B1
    high = {n: 1.0 for n in fake18.feature_order[:4]}  # 4 × (+0,5) → 5,0, vẫn trong khoảng
    far = s.score(make_fs(fake18.feature_order, mid | high), make_transcript())
    assert far.status is AssessmentStatus.ESTIMATED and far.reasons == ()
    assert far.overall_score == pytest.approx(5.0) and far.overall_band is Band.B2


def test_transcript_not_ok_is_not_evaluated_and_keeps_m03_reason(fake18, mid):
    """M05-TEST-008."""
    tr = make_transcript(AsrStatus.UNRELIABLE, (ReasonCode.ASR_HALLUCINATION,))
    a = scorer_for(fake18).score(make_fs(fake18.feature_order, mid), tr)
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.ASR_HALLUCINATION,)
    assert a.overall_score is None and a.overall_band is None


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"asr_model": "whisper-medium"}, (ReasonCode.ASR_VERSION_MISMATCH,)),  # 009
        ({"vad_name": "energy"}, (ReasonCode.VAD_VERSION_MISMATCH,)),  # 010
        ({"vad_threshold": 0.6}, (ReasonCode.VAD_VERSION_MISMATCH,)),
        ({"vad_min_silence_ms": 200}, (ReasonCode.VAD_VERSION_MISMATCH,)),
        ({"feature_version": "v4"}, (ReasonCode.FEATURE_VERSION_MISMATCH,)),
        (
            {"asr_model": "whisper-medium", "vad_name": "energy"},  # 012
            (ReasonCode.ASR_VERSION_MISMATCH, ReasonCode.VAD_VERSION_MISMATCH),
        ),
        ({"asr_model": "whisper-small.en"}, (ReasonCode.ASR_VERSION_MISMATCH,)),  # 013
    ],
)
def test_provenance_mismatch_is_not_evaluated(fake18, mid, overrides, expected):
    """M05-TEST-009, 010, 012, 013."""
    a = scorer_for(fake18).score(make_fs(fake18.feature_order, mid, **overrides), make_transcript())
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == expected
    assert a.overall_score is None


def test_swapped_feature_order_is_not_evaluated(fake18, mid):
    """M05-TEST-011."""
    order = list(fake18.feature_order)
    order[0], order[1] = order[1], order[0]
    a = scorer_for(fake18).score(make_fs(order, mid), make_transcript())
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.FEATURE_VERSION_MISMATCH,)


def test_missing_feature_is_not_evaluated_with_null_coverage(fake18, mid):
    """M05-TEST-014."""
    fs = make_fs(fake18.feature_order, mid | {"vad_pause_sd": None})
    a = scorer_for(fake18).score(fs, make_transcript())
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.FEATURE_NOT_COMPUTABLE,)
    assert all(c.coverage is None for c in a.criteria)


def test_out_of_distribution_carries_detail(fake18, mid):
    a = scorer_for(fake18).score(
        make_fs(fake18.feature_order, mid | {"total_dur": 9.0}), make_transcript()
    )
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.OUT_OF_DISTRIBUTION,)
    [detail] = a.out_of_range
    assert (detail.feature, detail.too, detail.accepted_high) == ("total_dur", "high", 1.5)


def test_missing_artifact_gives_not_evaluated_assessment(tmp_path, fake18, mid):
    """M05-TEST-005 ở cấp Assessment: không có điểm, không fallback band."""
    s = RidgeScorer.load(tmp_path / "ridge_resp_v2.json", clock=lambda: FIXED_CLOCK)
    a = s.score(make_fs(fake18.feature_order, mid), make_transcript())
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.MODEL_VERSION_MISSING,)
    assert a.overall_score is None and a.provenance.model_version is None


def test_load_valid_artifact_scores(write_fake):
    path, sha = write_fake()
    s = RidgeScorer.load(path, expected_sha256=sha)
    fs = make_fs(("a", "b"), {"a": 0.5, "b": 0.5}, feature_version="v3")
    assert s.score(fs, make_transcript()).overall_score == pytest.approx(4.0)


def test_scorer_requires_exactly_one_of_artifact_or_error(fake18):
    with pytest.raises(ValueError):
        RidgeScorer()


def test_every_assessment_has_insufficient_evidence_interaction(fake18, mid):
    """M05-TEST-004: độc thoại luôn Interaction null / insufficient_evidence."""
    s = scorer_for(fake18)
    tr_bad = make_transcript(AsrStatus.ASR_FAILED, (ReasonCode.ASR_FAILED,))
    for a in (
        s.score(make_fs(fake18.feature_order, mid), make_transcript()),
        s.score(make_fs(fake18.feature_order, mid), tr_bad),
    ):
        assert a.interaction.level is None
        assert a.interaction.score_status == "insufficient_evidence"
        assert a.teacher_verified is False


def test_coverage_with_one_missing_fluency_feature(fake18):
    """M05-TEST-020: gọi hàm coverage trực tiếp."""
    order = fake18.feature_order
    values = {n: 1.0 for n in order} | {"vad_mean_pause": None}
    rows = {c.criterion: c for c in criterion_coverage(values, order)}
    assert rows[Criterion.FLUENCY].coverage == 0.8
    assert rows[Criterion.FLUENCY].reasons == (ReasonCode.FEATURE_NOT_COMPUTABLE,)
    assert rows[Criterion.RANGE].coverage == 1.0 and rows[Criterion.RANGE].reasons == ()


def test_coverage_criterion_without_any_model_feature_is_null():
    rows = criterion_coverage({"a": 1.0}, ["a"])
    assert all(c.coverage is None for c in rows)
    assert all(c.reasons == (ReasonCode.FEATURE_NOT_COMPUTABLE,) for c in rows)


def test_log_has_ids_and_status_but_no_feature_values(fake18, mid, caplog):
    """M05-TEST-021."""
    values = mid | {"n_words": 0.123456}
    with caplog.at_level(logging.INFO, logger="aicefr.scoring.scorer"):
        scorer_for(fake18).score(make_fs(fake18.feature_order, values), make_transcript())
    text = caplog.text
    assert "response_id=r1" in text and "status=" in text and "model_version=fake_v1" in text
    assert "0.123456" not in text and "n_words" not in text


def test_artifact_is_exposed_for_the_m04_extractor(fake18, tmp_path):
    """W4-S3: the coordinator joins M04 to M05 through a public name, not `_artifact`."""
    assert RidgeScorer(artifact=fake18).artifact is fake18
    assert RidgeScorer.load(tmp_path / "missing.json").artifact is None
