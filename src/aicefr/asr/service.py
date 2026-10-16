"""Dịch vụ ASR (M03 Spec v0.2): biến kết quả engine thành Transcript có trạng thái.

Engine thật (faster-whisper) là adapter riêng, nạp lười qua `engine_loader`;
module này không import thư viện ASR nào nên unit test không cần model.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import ValidationError

from aicefr.asr.hallucination import HallucinationConfig, detect_hallucination
from aicefr.asr.identity import asr_version_reasons, resolve_asr_model
from aicefr.asr.validation import timestamp_problem
from aicefr.contracts import (
    AsrStatus,
    DecodedAudio,
    QCResult,
    QCStatus,
    ReasonCode,
    Transcript,
    Word,
)

log = logging.getLogger(__name__)

DECODE_CONFIG_VERSION = "asr-decode-v1"


class ModelUnavailableError(Exception):
    """Weight chưa có local. Không tự tải (M03-D-002)."""


@dataclass(frozen=True)
class RawWord:
    text: str
    start_s: float
    end_s: float
    prob: float | None = None  # engine không trả probability → None, không phải 0.0


@dataclass(frozen=True)
class EngineResult:
    text: str
    words: Sequence[RawWord]
    engine: str
    engine_version: str
    weight_name: str
    test_only: bool = False
    language: str | None = None
    language_probability: float | None = None
    language_method: str | None = None
    language_version: str | None = None


class AsrEngine(Protocol):
    def transcribe(self, audio: DecodedAudio) -> EngineResult: ...

    def detect_language(self, audio: DecodedAudio) -> tuple[str | None, float | None]: ...


@dataclass
class AsrService:
    engine_loader: Callable[[], AsrEngine]
    trained_asr_model: str | None
    weight_map: Mapping[str, str] | None = None
    engine_name: str = "faster-whisper"
    hallucination: HallucinationConfig = field(default_factory=HallucinationConfig)
    _engine: AsrEngine | None = field(default=None, init=False, repr=False)

    def transcribe(self, response_id: str, audio: DecodedAudio, qc: QCResult) -> Transcript:
        transcript = self._transcribe(response_id, audio, qc)
        log.info(
            "asr response_id=%s status=%s reasons=%s words=%d",
            response_id,
            transcript.status.value,
            ",".join(r.value for r in transcript.reasons) or "-",
            len(transcript.words),
        )
        return transcript

    def _transcribe(self, response_id: str, audio: DecodedAudio, qc: QCResult) -> Transcript:
        base: dict[str, Any] = {
            "response_id": response_id,
            "engine": self.engine_name,
            "engine_version": "not-loaded",
            "decode_config_version": DECODE_CONFIG_VERSION,
            "audio_sha256": audio.audio_sha256,
            "language": None,
            "language_probability": None,
            "language_method": None,
            "language_version": None,
        }
        if qc.status is QCStatus.REJECT:
            # Chép lý do QC của M02 để M05/M06 báo được vì sao bài không chấm.
            return Transcript(status=AsrStatus.NOT_RUN, reasons=qc.reasons, **base)
        try:
            engine = self._load_engine()
        except ModelUnavailableError:
            return Transcript(status=AsrStatus.NOT_RUN, reasons=(ReasonCode.ASR_FAILED,), **base)
        try:
            result = engine.transcribe(audio)
        except Exception:  # lỗi engine có thể chứa transcript/path; không ghi chi tiết
            log.warning("engine ASR lỗi response_id=%s status=ASR_FAILED", response_id)
            return Transcript(status=AsrStatus.ASR_FAILED, reasons=(ReasonCode.ASR_FAILED,), **base)

        asr_model = resolve_asr_model(result.weight_name, self.weight_map)
        raw_language_probability = result.language_probability
        language_probability = (
            float(raw_language_probability)
            if isinstance(raw_language_probability, (int, float))
            and not isinstance(raw_language_probability, bool)
            and math.isfinite(raw_language_probability)
            and 0.0 <= raw_language_probability <= 1.0
            else None
        )
        language = (
            result.language.strip().lower()
            if isinstance(result.language, str) and result.language.strip()
            else None
        )
        base |= {
            "engine": result.engine,
            "engine_version": result.engine_version,
            "asr_model": asr_model,
            "test_only": result.test_only,
            "language": language,
            "language_probability": language_probability,
            "language_method": result.language_method if language is not None else None,
            "language_version": result.language_version if language is not None else None,
        }
        version_reasons = asr_version_reasons(asr_model, self.trained_asr_model)
        try:
            words = tuple(
                Word(text=w.text, start_s=w.start_s, end_s=w.end_s, prob=w.prob)
                for w in result.words
            )
        except ValidationError:  # vd. prob ngoài [0,1]
            return Transcript(status=AsrStatus.ASR_FAILED, reasons=(ReasonCode.ASR_FAILED,), **base)
        if timestamp_problem(words, audio.duration_s):
            return Transcript(status=AsrStatus.ASR_FAILED, reasons=(ReasonCode.ASR_FAILED,), **base)
        if not words or not result.text.strip():
            return Transcript(
                status=AsrStatus.UNRELIABLE,
                text=result.text,
                words=words,
                reasons=(ReasonCode.ASR_EMPTY_TRANSCRIPT, *version_reasons),
                **base,
            )
        status, reasons = AsrStatus.OK, version_reasons
        if detect_hallucination(words, self.hallucination) is not None:
            status, reasons = AsrStatus.UNRELIABLE, (ReasonCode.ASR_HALLUCINATION, *version_reasons)
        return Transcript(status=status, text=result.text, words=words, reasons=reasons, **base)

    def _load_engine(self) -> AsrEngine:
        if self._engine is None:
            self._engine = self.engine_loader()
        return self._engine

    def load_engine(self) -> AsrEngine:
        """Return the configured lazy engine for purpose-specific runtime adapters."""
        return self._load_engine()
