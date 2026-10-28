"""Tests for evidence building and the hand-off-to-teacher rules."""

from conftest import feature_set

from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    CriterionCoverage,
    FeatureSet,
    QcResult,
    QcStatus,
    ReasonCode,
    Status,
    Transcript,
    Word,
)
from aicefr.report.evidence import EvidenceBuilder
from aicefr.review.router import ReviewRouter


def _asr(verbatim: bool = False) -> Transcript:
    words = [Word(text="hello", start_s=0.0, end_s=0.4, prob=0.95)]
    words += [Word(text="um", start_s=0.5, end_s=0.8, prob=0.9)]
    words += [Word(text="world", start_s=2.0, end_s=2.4, prob=0.2)]
    return Transcript(
        text="hello um world",
        words=words,
        engine="fake",
        model_version="v1",
        has_word_timestamps=True,
        is_verbatim=verbatim,
    )


def _features() -> FeatureSet:
    return feature_set({"log_uniq": 3.0, "n_words": 20.0})


def _qc(passed: bool = True, reasons=None, status: QcStatus | None = None) -> QcResult:
    if status is None:
        status = QcStatus.PASS if passed else QcStatus.REJECT
    return QcResult(
        duration_ms=40_000,
        sample_rate_hz=16_000,
        channels=1,
        silence_ratio=0.2,
        clipping_ratio=0.0,
        qc_status=status,
        reasons=reasons or [],
    )


def test_evidence_carries_real_timestamps():
    ev = EvidenceBuilder().build(_asr(), _features(), [(0.0, 1.0), (3.0, 5.0)])
    pauses = [e for e in ev if e.kind == "pause"]
    assert pauses and pauses[0].start_s == 1.0


def test_low_confidence_word_becomes_phonology_evidence():
    ev = EvidenceBuilder().build(_asr(), _features(), [])
    low = [e for e in ev if e.kind == "low_confidence_word"]
    assert low and low[0].criterion is Criterion.PHONOLOGY


def test_no_filler_reported_when_model_not_verbatim():
    assert not [
        e for e in EvidenceBuilder().build(_asr(False), _features(), []) if e.kind == "filler"
    ]


def test_fillers_reported_when_model_is_verbatim():
    assert [e for e in EvidenceBuilder().build(_asr(True), _features(), []) if e.kind == "filler"]


def _assessment(score: float | None, reasons=None) -> Assessment:
    return Assessment(
        overall_0_6=score,
        overall_band=Band.B1 if score else None,
        criteria=[
            CriterionCoverage(criterion=c, score_0_6=score, band=None, reasons=list(reasons or []))
            for c in Criterion
        ],
        model_version="v1",
    )


def test_failed_qc_rejects():
    d = ReviewRouter().route(_qc(False, [ReasonCode.AUDIO_TOO_LONG]), None, None)
    assert d.status is Status.REJECTED


def test_score_near_boundary_goes_to_teacher():
    d = ReviewRouter().route(_qc(), _assessment(3.7, [ReasonCode.SCORE_NEAR_BOUNDARY]), None)
    assert d.needs_teacher


def test_low_asr_confidence_goes_to_teacher():
    fs = feature_set({"asr_conf_mean": 0.3})
    d = ReviewRouter().route(_qc(), _assessment(4.0), fs)
    assert ReasonCode.ASR_LOW_CONFIDENCE in d.reasons
    assert d.needs_teacher


def test_normal_case_completes():
    fs = feature_set({"asr_conf_mean": 0.9})
    assert ReviewRouter().route(_qc(), _assessment(4.0), fs).status is Status.COMPLETED


def test_unscorable_response_keeps_its_reasons():
    d = ReviewRouter().route(_qc(), _assessment(None, [ReasonCode.OUT_OF_DISTRIBUTION]), None)
    assert d.status is Status.REVIEW_REQUIRED
    assert d.reasons.count(ReasonCode.OUT_OF_DISTRIBUTION) == 1


def test_qc_review_level_goes_to_teacher():
    """A 20-29 second recording is scorable, but the result must not be treated as certain.

    Before QcResult had three levels, this zone was folded into PASS, so such responses
    went straight to COMPLETED. This test keeps that bug from coming back.
    """
    qc = _qc(status=QcStatus.REVIEW, reasons=[ReasonCode.AUDIO_TOO_SHORT])
    d = ReviewRouter().route(qc, _assessment(3.20), _features())
    assert d.status is Status.REVIEW_REQUIRED
    assert d.needs_teacher
