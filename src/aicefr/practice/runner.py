"""Purpose-isolated audio runner for uns cored practice activities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from aicefr.asr.language import LanguageIdentifier
from aicefr.asr.service import AsrService, EngineResult, RawWord
from aicefr.contracts import AsrStatus, DecodedAudio, QCStatus, Transcript
from aicefr.lessons.model import StepResult
from aicefr.practice.contracts import (
    MissionMeasurement,
    PracticeMission,
    PracticePurpose,
    PracticeReason,
    PracticeResult,
    PracticeStatus,
    TimeSpan,
)
from aicefr.practice.missions import MissionChecker


@dataclass(frozen=True)
class PracticeRun:
    result: PracticeResult | StepResult | None
    reason: str | None = None


class _CroppedEngine:
    """ASR adapter that recognizes only VAD speech and restores source offsets."""

    def __init__(self, engine: Any, spans: Sequence[TimeSpan], language: Any) -> None:
        self._engine = engine
        self._spans = tuple(spans)
        self._language = language

    def detect_language(self, audio: DecodedAudio) -> tuple[str | None, float | None]:
        return self._language

    def transcribe(self, audio: DecodedAudio) -> EngineResult:
        if not self._spans:
            return EngineResult(
                text="",
                words=(),
                engine="practice-asr",
                engine_version="unavailable",
                weight_name="unavailable",
                language=self._language[0],
                language_probability=self._language[1],
                language_method="faster-whisper-detect-v1",
                language_version="1",
            )
        # Match the pinned runtime: recognize one bounding speech crop so pauses
        # and lexical context between VAD islands do not fragment ASR context.
        start = max(0, int(min(span.start_s for span in self._spans) * audio.sample_rate_hz))
        end = min(
            len(audio.samples), int(max(span.end_s for span in self._spans) * audio.sample_rate_hz)
        )
        clip = DecodedAudio(
            samples=audio.samples[start:end].copy(),
            sample_rate_hz=audio.sample_rate_hz,
            duration_s=(end - start) / audio.sample_rate_hz,
            audio_sha256=audio.audio_sha256,
        )
        last = self._engine.transcribe(clip)
        words = [
            RawWord(
                w.text,
                w.start_s + start / audio.sample_rate_hz,
                w.end_s + start / audio.sample_rate_hz,
                w.prob,
            )
            for w in last.words
        ]
        return EngineResult(
            text=last.text,
            words=tuple(words),
            engine=last.engine,
            engine_version=last.engine_version,
            weight_name=last.weight_name,
            test_only=last.test_only,
            language=self._language[0],
            language_probability=self._language[1],
            language_method="faster-whisper-detect-v1",
            language_version="1",
        )


class PracticeRunner:
    """Decode, QC, VAD, independently identify language, then apply pure rules."""

    def __init__(
        self,
        *,
        qc_config: Any,
        asr: AsrService,
        vad: Any,
        checker: MissionChecker | None = None,
        language_identifier: LanguageIdentifier | None = None,
        decoder: Any | None = None,
    ) -> None:
        self._qc_config = replace(
            qc_config,
            version="practice-qc-v1",
            min_duration_s=1.0,
            review_silence_ratio=0.90,
            reject_silence_ratio=0.97,
        )
        self._asr = asr
        self._vad = vad
        self._checker = checker or MissionChecker()
        self._language = language_identifier or LanguageIdentifier()
        self._decoder = decoder

    def run(
        self,
        mission: PracticeMission,
        data: bytes,
        extension: str,
        *,
        attempt_id: str,
        purpose: PracticePurpose = PracticePurpose.PRACTICE,
    ) -> PracticeRun:
        from aicefr.practice.rules import SUPPORTED_MISSION_RULES_VERSIONS

        if mission.rules_version not in SUPPORTED_MISSION_RULES_VERSIONS:
            raise ValueError(f"unsupported mission rules version: {mission.rules_version}")
        from aicefr.audio.decoder import decode_and_measure
        from aicefr.qc.policy import evaluate_qc

        decoded = (self._decoder or decode_and_measure)(data, extension, self._qc_config)
        if decoded.audio is None:
            reason = decoded.qc.reasons[0].value if decoded.qc.reasons else "AUDIO_REJECTED"
            return PracticeRun(None, reason)
        audio = decoded.audio
        if audio.duration_s < 1.0:
            return PracticeRun(None, "AUDIO_TOO_SHORT")
        qc = evaluate_qc(decoded.qc, self._qc_config)
        if qc.status is QCStatus.REJECT:
            reason = qc.reasons[0].value if qc.reasons else "AUDIO_REJECTED"
            return PracticeRun(None, reason)
        try:
            detected_spans = self._vad.segments(audio.samples, audio.sample_rate_hz)
        except Exception:
            return PracticeRun(None, "VAD_UNAVAILABLE")
        spans = tuple(
            TimeSpan(start_s=float(start), end_s=float(end))
            for start, end in detected_spans
            if 0 <= float(start) < float(end) <= audio.duration_s
        )
        if not spans:
            empty = Transcript(
                response_id=attempt_id,
                status=AsrStatus.UNRELIABLE,
                text="",
                words=(),
                reasons=(),
                engine="practice",
                engine_version="not-run",
                decode_config_version="practice-v1",
                audio_sha256=audio.audio_sha256,
            )
            return PracticeRun(self._checker.check(mission, empty, (), purpose=purpose))

        try:
            engine = self._asr.load_engine()
        except Exception:
            # Model loader errors may include local artifact paths. Keep the
            # durable state controlled and expose only a stable reason code.
            return PracticeRun(None, "ASR_UNAVAILABLE")
        try:
            language, confidence = engine.detect_language(audio)
        except Exception:
            language, confidence = None, None
        evidence = self._language.evaluate_language(language, confidence)
        if evidence.decision.value == "NON_ENGLISH":
            return PracticeRun(
                self._unmeasured(mission, spans, PracticeReason.LANGUAGE_NOT_ENGLISH, purpose)
            )
        if evidence.decision.value != "ENGLISH":
            return PracticeRun(
                self._unsure(mission, spans, PracticeReason.LANGUAGE_UNCERTAIN, purpose)
            )

        from aicefr.asr.service import AsrService

        cropped = _CroppedEngine(engine, spans, (evidence.language, evidence.confidence))
        service = AsrService(
            engine_loader=lambda: cropped,
            trained_asr_model=self._asr.trained_asr_model,
            weight_map=self._asr.weight_map,
            engine_name=self._asr.engine_name,
            hallucination=self._asr.hallucination,
        )
        transcript = service.transcribe(attempt_id, audio, qc)
        result = self._checker.check(mission, transcript, spans, purpose=purpose)
        return PracticeRun(result)

    def run_step(
        self,
        step: Any,
        data: bytes,
        extension: str,
        *,
        attempt_id: str,
        round_index: int | None = None,
    ) -> PracticeRun:
        """Recognize a lesson step through the same audio boundary, without scoring."""
        from aicefr.lessons.rules import SUPPORTED_LESSON_RULES_VERSIONS

        if step.rules_version not in SUPPORTED_LESSON_RULES_VERSIONS:
            raise ValueError(f"unsupported lesson rules version: {step.rules_version}")
        from aicefr.audio.decoder import decode_and_measure
        from aicefr.lessons.checks import evaluate_step
        from aicefr.lessons.model import StepResult, StepResultStatus
        from aicefr.qc.policy import evaluate_qc

        decoded = (self._decoder or decode_and_measure)(data, extension, self._qc_config)
        if decoded.audio is None:
            reason = decoded.qc.reasons[0].value if decoded.qc.reasons else "AUDIO_REJECTED"
            return PracticeRun(None, reason)
        audio = decoded.audio
        if audio.duration_s < 1.0:
            return PracticeRun(None, "AUDIO_TOO_SHORT")
        qc = evaluate_qc(decoded.qc, self._qc_config)
        if qc.status is QCStatus.REJECT:
            reason = qc.reasons[0].value if qc.reasons else "AUDIO_REJECTED"
            return PracticeRun(None, reason)
        try:
            detected_spans = self._vad.segments(audio.samples, audio.sample_rate_hz)
        except Exception:
            return PracticeRun(None, "VAD_UNAVAILABLE")
        spans = tuple(
            TimeSpan(start_s=float(start), end_s=float(end))
            for start, end in detected_spans
            if 0 <= float(start) < float(end) <= audio.duration_s
        )
        if not spans:
            transcript = Transcript(
                response_id=attempt_id,
                status=AsrStatus.UNRELIABLE,
                text="",
                words=(),
                reasons=(),
                engine="practice",
                engine_version="not-run",
                decode_config_version="practice-v1",
                audio_sha256=audio.audio_sha256,
            )
            return PracticeRun(
                evaluate_step(
                    step,
                    transcript,
                    spans,
                    round_index=round_index,
                    elapsed_seconds=audio.duration_s,
                )
            )
        try:
            engine = self._asr.load_engine()
        except Exception:
            return PracticeRun(None, "ASR_UNAVAILABLE")
        try:
            language, confidence = engine.detect_language(audio)
        except Exception:
            language, confidence = None, None
        evidence = self._language.evaluate_language(language, confidence)
        if evidence.decision.value == "NON_ENGLISH":
            return PracticeRun(None, "LANGUAGE_NOT_ENGLISH")
        if evidence.decision.value != "ENGLISH":
            status = StepResultStatus.UNSURE
            result = StepResult(
                step_id=step.step_id,
                kind=step.kind,
                status=status,
                round_index=round_index,
                round_count=(
                    len(step.payload.rounds) if getattr(step.payload, "rounds", None) else None
                ),
                elapsed_seconds=audio.duration_s,
                word_count=0,
                feedback="Chưa xác định chắc tiếng Anh; hãy ghi lại rõ hơn.",
            )
            return PracticeRun(result)
        cropped = _CroppedEngine(engine, spans, (evidence.language, evidence.confidence))
        service = AsrService(
            engine_loader=lambda: cropped,
            trained_asr_model=self._asr.trained_asr_model,
            weight_map=self._asr.weight_map,
            engine_name=self._asr.engine_name,
            hallucination=self._asr.hallucination,
        )
        transcript = service.transcribe(attempt_id, audio, qc)
        return PracticeRun(
            evaluate_step(
                step, transcript, spans, round_index=round_index, elapsed_seconds=audio.duration_s
            )
        )

    @staticmethod
    def _unmeasured(
        mission: PracticeMission,
        spans: Sequence[TimeSpan],
        reason: PracticeReason,
        purpose: PracticePurpose = PracticePurpose.PRACTICE,
    ) -> PracticeResult:
        measurements = tuple(
            MissionMeasurement(
                goal_id=g.goal_id,
                measured_value=None,
                target=g.target,
                status=PracticeStatus.UNMEASURED,
            )
            for g in mission.goals
        )
        duration = max((span.end_s for span in spans), default=0.0)
        return PracticeResult(
            mission_id=mission.mission_id,
            purpose=purpose,
            status=PracticeStatus.UNMEASURED,
            measurements=measurements,
            rules_version=mission.rules_version,
            reasons=(reason,),
            word_count=0,
            audio_duration_s=duration,
        )

    @staticmethod
    def _unsure(
        mission: PracticeMission,
        spans: Sequence[TimeSpan],
        reason: PracticeReason,
        purpose: PracticePurpose = PracticePurpose.PRACTICE,
    ) -> PracticeResult:
        measurements = tuple(
            MissionMeasurement(
                goal_id=g.goal_id,
                measured_value=None,
                target=g.target,
                status=PracticeStatus.UNSURE,
            )
            for g in mission.goals
        )
        duration = max((span.end_s for span in spans), default=0.0)
        return PracticeResult(
            mission_id=mission.mission_id,
            purpose=purpose,
            status=PracticeStatus.UNSURE,
            measurements=measurements,
            rules_version=mission.rules_version,
            reasons=(reason,),
            word_count=0,
            audio_duration_s=duration,
        )
