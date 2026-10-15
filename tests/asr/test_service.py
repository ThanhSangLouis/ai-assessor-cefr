import logging
import math

import pytest
from tests.asr.fixtures import CountingLoader, FakeAsrEngine, audio, qc, raw_words

from aicefr.asr.service import AsrService, EngineResult, RawWord
from aicefr.contracts import AsrStatus, QCStatus, ReasonCode


def service(engine=None, loader=None, trained="whisper-small"):
    return AsrService(engine_loader=loader or CountingLoader(engine or FakeAsrEngine()),
                      trained_asr_model=trained)  # fmt: skip


def result(words, text="fixture text", weight="Systran/faster-whisper-small"):
    return EngineResult(text=text, words=words, engine="fake-asr", engine_version="0.0-test",
                        weight_name=weight, test_only=True)  # fmt: skip


def test_ok_transcript_keeps_order_filler_and_provenance():
    """M03-TEST-001."""
    eng = FakeAsrEngine(result(raw_words(["um", "I", "think"]), text="um I think"))
    t = service(eng).transcribe("r1", audio(), qc())
    assert t.status is AsrStatus.OK and t.reasons == ()
    assert [w.text for w in t.words] == ["um", "I", "think"]
    assert (t.asr_model, t.engine, t.engine_version) == ("whisper-small", "fake-asr", "0.0-test")
    assert t.decode_config_version == "asr-decode-v1" and t.audio_sha256 == "b" * 64
    assert t.test_only is True


def test_missing_probability_stays_none():
    """M03-TEST-002 (regression REF-03: trước đây thành 0.0)."""
    ws = raw_words(["a", "b", "c"])
    ws[1] = RawWord("b", ws[1].start_s, ws[1].end_s, None)
    t = service(FakeAsrEngine(result(ws))).transcribe("r1", audio(), qc())
    assert t.words[1].prob is None and t.words[0].prob == 0.9


def test_independent_language_metadata_is_optional_and_propagated():
    base = result(raw_words(["hello", "there"]))
    t = service(FakeAsrEngine(base)).transcribe("r1", audio(), qc())
    assert (t.language, t.language_probability) == (None, None)
    assert t.language_method is None and t.language_version is None

    detected = EngineResult(
        text=base.text,
        words=base.words,
        engine=base.engine,
        engine_version=base.engine_version,
        weight_name=base.weight_name,
        test_only=base.test_only,
        language=" EN ",
        language_probability=0.91,
        language_method="fixture-lid",
        language_version="1",
    )
    transcript = service(FakeAsrEngine(detected)).transcribe("r1", audio(), qc())
    assert (transcript.language, transcript.language_probability) == ("en", 0.91)
    assert (transcript.language_method, transcript.language_version) == ("fixture-lid", "1")


def test_invalid_language_probability_becomes_missing_metadata():
    base = result(raw_words(["hello", "there"]))
    detected = EngineResult(
        text=base.text,
        words=base.words,
        engine=base.engine,
        engine_version=base.engine_version,
        weight_name=base.weight_name,
        language="vi",
        language_probability=math.nan,
        language_method="fixture-lid",
        language_version="1",
    )
    transcript = service(FakeAsrEngine(detected)).transcribe("r1", audio(), qc())
    assert transcript.status is AsrStatus.OK
    assert transcript.language == "vi" and transcript.language_probability is None
    assert (transcript.language_method, transcript.language_version) == ("fixture-lid", "1")


@pytest.mark.parametrize("error", [RuntimeError("engine hỏng"), TimeoutError("quá hạn")])
def test_engine_error_or_timeout_is_asr_failed(error):
    """M03-TEST-003."""
    t = service(FakeAsrEngine(error=error)).transcribe("r1", audio(), qc())
    assert t.status is AsrStatus.ASR_FAILED and t.reasons == (ReasonCode.ASR_FAILED,)
    assert t.words == ()


@pytest.mark.parametrize(
    "ws",
    [
        [RawWord("a", -0.1, 0.2, 0.9)],
        [RawWord("a", 0.5, 0.4, 0.9)],
        [RawWord("a", 1.0, 1.2, 0.9), RawWord("b", 0.8, 1.3, 0.9)],
        [RawWord("a", 0.0, 61.0, 0.9)],
        [RawWord("a", 0.0, 0.2, 1.5)],
    ],
    ids=["start_am", "end_truoc_start", "khong_don_dieu", "vuot_duration", "prob_ngoai_khoang"],
)
def test_invalid_words_are_asr_failed_without_words(ws):
    """M03-TEST-004."""
    t = service(FakeAsrEngine(result(ws))).transcribe("r1", audio(60.0), qc())
    assert t.status is AsrStatus.ASR_FAILED and t.words == ()


def test_qc_reject_does_not_call_engine():
    """M03-TEST-005."""
    eng = FakeAsrEngine()
    loader = CountingLoader(eng)
    rejected = qc(QCStatus.REJECT, (ReasonCode.QC_TOO_SHORT, ReasonCode.QC_SILENCE_REJECT))
    t = service(loader=loader).transcribe("r1", audio(), rejected)
    assert t.status is AsrStatus.NOT_RUN
    assert loader.calls == 0 and eng.calls == 0
    # Follow-up 07-A1-03: lý do QC đi theo transcript, giữ nguyên thứ tự.
    assert t.reasons == (ReasonCode.QC_TOO_SHORT, ReasonCode.QC_SILENCE_REJECT)
    assert (t.text, t.words) == ("", ())


def test_qc_reject_reasons_reach_the_scorer(tmp_path):
    """M03-TEST-005 (nối M05): bài QC REJECT ra NOT_EVALUATED kèm đúng lý do QC."""
    import hashlib
    import json

    from aicefr.contracts import AssessmentStatus, FeatureSet
    from aicefr.scoring.artifact import load_artifact
    from aicefr.scoring.scorer import RidgeScorer

    payload = {
        "model_version": "fake", "feature_version": "v3", "unit_of_inference": "mot bai noi",
        "trained_with": {"asr_model": "whisper-small"}, "feature_order": ["a"], "mean": [0.0],
        "scale": [1.0], "coef": [0.0], "intercept": 3.0, "feature_lo": [0.0],
        "feature_hi": [1.0], "ood_tolerance": 0.5,
        "band_thresholds": {"A2_B1": 2.75, "B1_B2": 3.75}, "boundary_margin": 0.5,
    }  # fmt: skip
    path = tmp_path / "fake.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    art = load_artifact(path, hashlib.sha256(path.read_bytes()).hexdigest())
    t = service().transcribe("r1", audio(), qc(QCStatus.REJECT, (ReasonCode.QC_TOO_SHORT,)))
    fs = FeatureSet(
        response_id="r1", values=(), feature_version="v3", asr_model=None,
        vad_name=None, vad_version=None, vad_threshold=None, vad_min_silence_ms=None,
        transcript_ref="r1", audio_sha256=t.audio_sha256,
    )  # fmt: skip
    a = RidgeScorer(artifact=art).score(fs, t)
    assert a.status is AssessmentStatus.NOT_EVALUATED
    assert a.reasons == (ReasonCode.QC_TOO_SHORT,)


def test_qc_review_still_runs_engine():
    t = service().transcribe("r1", audio(), qc(QCStatus.REVIEW))
    assert t.status is AsrStatus.OK


def test_missing_model_is_not_run_without_download():
    """M03-TEST-006: loader báo thiếu weight một lần, không thử tải."""
    loader = CountingLoader(unavailable=True)
    t = service(loader=loader).transcribe("r1", audio(), qc())
    assert t.status is AsrStatus.NOT_RUN and t.reasons == (ReasonCode.ASR_FAILED,)
    assert loader.calls == 1


def test_engine_is_loaded_once_and_reused():
    loader = CountingLoader(FakeAsrEngine())
    s = service(loader=loader)
    s.transcribe("r1", audio(), qc())
    s.transcribe("r2", audio(), qc())
    assert loader.calls == 1


@pytest.mark.parametrize(("ws", "text"), [([], ""), (raw_words(["a"]), "   ")])
def test_empty_transcript_is_unreliable(ws, text):
    """M03-TEST-007."""
    t = service(FakeAsrEngine(result(ws, text=text))).transcribe("r1", audio(), qc())
    assert t.status is AsrStatus.UNRELIABLE
    assert t.reasons == (ReasonCode.ASR_EMPTY_TRANSCRIPT,)


def test_hallucination_is_unreliable():
    ws = raw_words(["a", "b"] + ["okay"] * 7)
    t = service(FakeAsrEngine(result(ws, text="a b okay"))).transcribe("r1", audio(), qc())
    assert t.status is AsrStatus.UNRELIABLE and t.reasons == (ReasonCode.ASR_HALLUCINATION,)


def test_matching_weight_has_no_mismatch():
    """M03-TEST-013."""
    t = service().transcribe("r1", audio(), qc())
    assert t.asr_model == "whisper-small" and t.reasons == ()


def test_english_only_weight_is_mismatch_but_status_unchanged():
    """M03-TEST-014 (regression F-04)."""
    eng = FakeAsrEngine(weight="Systran/faster-whisper-small.en")
    t = service(eng).transcribe("r1", audio(), qc())
    assert t.asr_model is None
    assert t.reasons == (ReasonCode.ASR_VERSION_MISMATCH,) and t.status is AsrStatus.OK


def test_other_model_is_mismatch_but_status_unchanged():
    """M03-TEST-015."""
    s = AsrService(
        engine_loader=CountingLoader(FakeAsrEngine(weight="m")),
        trained_asr_model="whisper-small",
        weight_map={"m": "whisper-medium"},
    )
    t = s.transcribe("r1", audio(), qc())
    assert t.asr_model == "whisper-medium" and t.status is AsrStatus.OK
    assert t.reasons == (ReasonCode.ASR_VERSION_MISMATCH,)


def test_log_does_not_contain_transcript_text(caplog):
    """M03-TEST-016."""
    ws = raw_words(["SECRET-NAME-123", "says", "hello"])
    eng = FakeAsrEngine(result(ws, text="SECRET-NAME-123 says hello"))
    with caplog.at_level(logging.INFO, logger="aicefr.asr.service"):
        service(eng).transcribe("r1", audio(), qc())
    assert "SECRET-NAME-123" not in caplog.text
    assert "response_id=r1" in caplog.text and "status=OK" in caplog.text
