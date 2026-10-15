from __future__ import annotations

import numpy as np
import pytest

from aicefr.asr.service import AsrService, EngineResult, RawWord
from aicefr.audio.config import AudioFormat, QCConfig
from aicefr.audio.decoder import DecodeResult
from aicefr.contracts import DecodedAudio, QCResult, QCStatus
from aicefr.lessons.seed import sample_catalogue
from aicefr.practice.bank import get_mission
from aicefr.practice.contracts import PracticeReason
from aicefr.practice.missions import MissionChecker
from aicefr.practice.runner import PracticeRunner
from aicefr.qc.measurements import measure_audio


def _qc() -> QCConfig:
    return QCConfig(
        version="fixture-qc",
        accepted_formats=(AudioFormat.WAV_PCM,),
        max_input_bytes=100_000,
        min_duration_s=2,
        max_duration_s=10,
        max_input_sample_rate_hz=48_000,
        silence_threshold=0.01,
        clipping_threshold=0.99,
        review_silence_ratio=0.2,
        reject_silence_ratio=0.8,
        review_clipping_ratio=0.01,
        reject_clipping_ratio=0.2,
    )


class _Vad:
    def segments(self, samples, sample_rate_hz):
        return ((0.5, 0.8), (1.2, 1.5))


class _Engine:
    def __init__(self, language: str | None, confidence: float | None) -> None:
        self.language, self.confidence = language, confidence
        self.transcribe_durations: list[float] = []

    def detect_language(self, audio):
        return self.language, self.confidence

    def transcribe(self, audio):
        self.transcribe_durations.append(audio.duration_s)
        return EngineResult(
            text="and",
            words=(RawWord("and", 0.1, 0.2, 0.99),),
            engine="fixture",
            engine_version="1",
            weight_name="fixture",
        )


class _CaptureChecker:
    def __init__(self) -> None:
        self.transcript = None
        self.spans = ()
        self.checker = MissionChecker()

    def check(self, mission, transcript, spans, *, purpose):
        self.transcript = transcript
        self.spans = tuple(spans)
        return self.checker.check(mission, transcript, spans, purpose=purpose)


def _runner(engine: _Engine, checker: _CaptureChecker | None = None) -> PracticeRunner:
    sample_rate = 16_000
    samples = (np.sin(np.arange(3 * sample_rate, dtype=np.float32) * 0.05) * 0.1).astype(np.float32)
    audio = DecodedAudio(
        samples=samples, sample_rate_hz=sample_rate, duration_s=3.0, audio_sha256="a" * 64
    )
    qc = QCResult(
        status=QCStatus.PASS,
        qc_config_version="fixture-qc",
        measurements=measure_audio(audio, _qc()),
    )

    def decode(_data, _extension, config):
        return DecodeResult(
            audio=audio, qc=qc.model_copy(update={"qc_config_version": config.version})
        )

    asr = AsrService(
        engine_loader=lambda: engine, trained_asr_model="fixture", weight_map={"fixture": "fixture"}
    )
    return PracticeRunner(qc_config=_qc(), asr=asr, vad=_Vad(), checker=checker, decoder=decode)


def test_english_runner_uses_one_bounding_crop_and_restores_original_word_times() -> None:
    engine = _Engine("en", 0.99)
    checker = _CaptureChecker()
    runner = _runner(engine, checker)

    runner.run(get_mission("PR-COH-A2"), b"fixture", "wav", attempt_id="attempt-1")

    assert engine.transcribe_durations == [1.0]
    assert checker.transcript is not None
    assert checker.transcript.words[0].start_s == 0.6
    assert checker.transcript.words[0].end_s == 0.7
    assert tuple(span.start_s for span in checker.spans) == (0.5, 1.2)


def test_non_english_and_uncertain_language_never_run_forced_english_asr() -> None:
    mission = get_mission("PR-COH-A2")
    non_english_engine = _Engine("vi", 0.99)
    rejected = _runner(non_english_engine).run(mission, b"fixture", "wav", attempt_id="a1")
    assert rejected.result is not None
    assert rejected.result.status.value == "UNMEASURED"
    assert rejected.result.reasons == (PracticeReason.LANGUAGE_NOT_ENGLISH,)
    assert non_english_engine.transcribe_durations == []

    uncertain_engine = _Engine("en", 0.80)
    unsure = _runner(uncertain_engine).run(mission, b"fixture", "wav", attempt_id="a2")
    assert unsure.result is not None
    assert unsure.result.status.value == "UNSURE"
    assert unsure.result.reasons == (PracticeReason.LANGUAGE_UNCERTAIN,)
    assert uncertain_engine.transcribe_durations == []


def test_missing_asr_model_returns_a_safe_not_evaluated_reason() -> None:
    def unavailable_engine():
        raise RuntimeError("missing /private/model/path")

    asr = AsrService(engine_loader=unavailable_engine, trained_asr_model=None)
    runner = PracticeRunner(
        qc_config=_qc(), asr=asr, vad=_Vad(), decoder=_runner(_Engine("en", 0.99))._decoder
    )

    run = runner.run(get_mission("PR-COH-A2"), b"fixture", "wav", attempt_id="no-asr")

    assert run.result is None
    assert run.reason == "ASR_UNAVAILABLE"
    assert "/private" not in str(run)


def test_runner_rejects_unsupported_pinned_rule_versions_before_language_gates() -> None:
    runner = _runner(_Engine("vi", 0.99))
    mission = get_mission("PR-COH-A2").model_copy(update={"rules_version": "mission-rules-v2"})
    with pytest.raises(ValueError, match="unsupported mission rules version"):
        runner.run(mission, b"fixture", "wav", attempt_id="invalid-rules")

    lesson = sample_catalogue()[2][0][1]
    step = lesson.steps[0].model_copy(update={"rules_version": "lesson-rules-v2"})
    with pytest.raises(ValueError, match="unsupported lesson rules version"):
        runner.run_step(step, b"fixture", "wav", attempt_id="invalid-step-rules")
