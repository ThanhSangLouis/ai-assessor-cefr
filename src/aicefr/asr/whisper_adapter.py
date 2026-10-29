"""Wraps Whisper behind the AsrEngine interface. Implements FR-10 to FR-13.

The backend is chosen per machine: Apple Silicon uses mlx-whisper running on
Metal, other machines use faster-whisper. The libraries are imported only when
actually called, so CI does not break on machines where they are not installed.

A warning about verbatimness: stock Whisper REMOVES hesitation words such as
"um" and "uh". As a result the filler_ratio feature will be close to zero. To
measure fluency properly a verbatim model is needed, for example
CrisperWhisper. The is_verbatim attribute of the result records which case
applies.
"""

from __future__ import annotations

import logging
import platform

import numpy as np

from aicefr.asr.base import AsrError
from aicefr.contracts import Transcript, Word

logger = logging.getLogger(__name__)

# 30 giay dau, dung cua so ma chinh Whisper dung de doan ngon ngu.
LID_SECONDS = 30

DEFAULT_MLX_REPO = "mlx-community/whisper-large-v3-turbo"
DEFAULT_CT2_MODEL = "large-v3"
VERBATIM_HINTS = ("crisper", "verbatim")

# Decoding options, and why each one is set rather than left at its default.
#
# These were chosen from a measurement on a real 94-second submission, not from
# a blog post. With the library defaults that recording produced 213 words
# ending in "...the second part of the Simpsons to work that is who is now
# here" -- speech that is not on the tape. The junk all landed in the second
# half, dragged `asr_conf_geo` there down to 0.389, and the scorer refused the
# window as out of distribution. Half the student's answer came back unscored.
#
# `condition_on_previous_text=False` is the fix and by far the most important
# line here. The default feeds the decoder its own previous output as context,
# so once it emits a plausible sentence it will happily continue the story
# through a pause -- which is exactly what a loop hallucination IS. Turning it
# off cut the same recording to 175 words ending where the speaker actually
# stopped, brought the second window's confidence to 0.915, and scored it 4.39.
#
# It also made the run FOUR TIMES faster (13.7 s to 3.2 s), which is not a
# coincidence: the fallback machinery below keeps re-decoding segments whose
# output looks degenerate, and a decoder that hallucinates spends most of its
# time being re-run.
#
# `hallucination_silence_threshold=2.0` skips ahead when a silence longer than
# two seconds opens up mid-recording, the other place these loops start. It
# needs word timestamps, which this call already requests.
#
# The three thresholds below are the library defaults, written out on purpose:
# they decide when a segment is re-decoded at a higher temperature, and leaving
# them implicit hides a mechanism that directly shapes the transcript a student
# is shown.
MLX_DECODE_OPTIONS = {
    "condition_on_previous_text": False,
    "hallucination_silence_threshold": 2.0,
    "compression_ratio_threshold": 2.4,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
}

# faster-whisper takes the same two ideas under the same names, plus its own
# voice-activity gate which does the job of the silence threshold above.
CT2_DECODE_OPTIONS = {
    "condition_on_previous_text": False,
    "vad_filter": True,
    "compression_ratio_threshold": 2.4,
    "log_prob_threshold": -1.0,
    "no_speech_threshold": 0.6,
}


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


class WhisperEngine:
    """Wraps mlx-whisper or faster-whisper depending on the platform.

    `temperature` fixes the decoding temperature; None keeps the library's
    fallback schedule (see Settings.asr_temperature for why both exist).
    """

    def __init__(
        self,
        model: str | None = None,
        backend: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self.backend = backend or ("mlx" if _is_apple_silicon() else "ct2")
        self.model = model or (DEFAULT_MLX_REPO if self.backend == "mlx" else DEFAULT_CT2_MODEL)
        self.name = f"whisper-{self.backend}"
        self.temperature = temperature
        self._ct2 = None

    @property
    def decoding(self) -> str:
        """How this engine decodes, for reports: "fallback" or "temperature=0.0"."""
        return "fallback" if self.temperature is None else f"temperature={self.temperature}"

    def _options(self, base: dict) -> dict:
        return base if self.temperature is None else {**base, "temperature": self.temperature}

    @property
    def is_verbatim(self) -> bool:
        """True if the model is known to keep hesitation words."""
        return any(h in self.model.lower() for h in VERBATIM_HINTS)

    def transcribe(self, pcm: np.ndarray, sr: int) -> Transcript:
        try:
            if self.backend == "mlx":
                words, text, tokens = self._mlx(pcm)
            else:
                words, text, tokens = self._ct2_transcribe(pcm)
        except ImportError as exc:
            raise AsrError(f"chưa cài backend {self.backend}: {exc}") from exc
        except Exception as exc:
            raise AsrError(str(exc)) from exc

        language = self.detect_language(pcm)
        return Transcript(
            text=text,
            words=words,
            engine=self.name,
            model_version=self.model,
            is_verbatim=self.is_verbatim,
            language=language[0] if language else None,
            language_probability=round(language[1], 4) if language else None,
            output_tokens=tokens,
        )

    def detect_language(self, pcm: np.ndarray) -> tuple[str, float] | None:
        """Ngon ngu Whisper doan tren 30 giay dau, kem xac suat. D022.

        Ban chep luon ep `language="en"`, nen Whisper co the "dich" loi tieng
        Viet thanh chu tieng Anh -- va ban chep do duoc cham nhu mot bai noi that.
        Lan doan ngon ngu nay tach rieng de bat ca do.

        Loi o day KHONG lam hong viec nhan dang: tra None, ghi log. Thieu mot
        lop phong ve thi kem, nhung lam mat ca ban chep vi no thi te hon.
        Model chi tieng Anh (`*.en`) khong doan duoc ngon ngu: cung tra None.
        """
        head = pcm[: LID_SECONDS * 16_000]
        try:
            if self.backend == "mlx":
                return self._mlx_language(head)
            return self._ct2_language(head)
        except Exception:  # noqa: BLE001 - lop phong ve phu, khong duoc lam hong ban chep
            logger.warning("khong doan duoc ngon ngu", exc_info=True)
            return None

    def _mlx_language(self, pcm: np.ndarray) -> tuple[str, float] | None:
        import mlx.core as mx
        from mlx_whisper.audio import N_FRAMES, N_SAMPLES, log_mel_spectrogram, pad_or_trim
        from mlx_whisper.transcribe import ModelHolder

        model = ModelHolder.get_model(self.model, mx.float16)
        if not model.is_multilingual:
            return None
        mel = log_mel_spectrogram(pcm, n_mels=model.dims.n_mels, padding=N_SAMPLES)
        segment = pad_or_trim(mel, N_FRAMES, axis=-2).astype(mx.float16)
        _, probs = model.detect_language(segment)
        best = max(probs, key=probs.get)
        return best, float(probs[best])

    def _ct2_language(self, pcm: np.ndarray) -> tuple[str, float] | None:
        from faster_whisper import WhisperModel

        if self._ct2 is None:
            self._ct2 = WhisperModel(self.model, device="auto", compute_type="int8")
        if not self._ct2.model.is_multilingual:
            return None
        # transcribe() doan ngon ngu ngay khi goi; khong lap qua segment nen
        # khong ton cong giai ma.
        _, info = self._ct2.transcribe(pcm, language=None, word_timestamps=False)
        return info.language, float(info.language_probability)

    def _mlx(self, pcm: np.ndarray) -> tuple[list[Word], str, int]:
        import mlx_whisper

        r = mlx_whisper.transcribe(
            pcm,
            path_or_hf_repo=self.model,
            word_timestamps=True,
            language="en",
            verbose=False,
            **self._options(MLX_DECODE_OPTIONS),
        )
        words = [
            Word(
                text=w["word"].strip(),
                start_s=round(float(w["start"]), 3),
                end_s=round(float(w["end"]), 3),
                prob=round(float(w.get("probability", 0.0)), 4),
            )
            for seg in r.get("segments", [])
            for w in seg.get("words", [])
        ]
        # D057: what the decoder produced, the output side of the price.
        tokens = sum(len(seg.get("tokens", [])) for seg in r.get("segments", []))
        return words, r.get("text", "").strip(), tokens

    def _ct2_transcribe(self, pcm: np.ndarray) -> tuple[list[Word], str, int]:
        from faster_whisper import WhisperModel

        if self._ct2 is None:
            self._ct2 = WhisperModel(self.model, device="auto", compute_type="int8")
        segs, _ = self._ct2.transcribe(
            pcm, word_timestamps=True, language="en", **self._options(CT2_DECODE_OPTIONS)
        )
        words, parts, tokens = [], [], 0
        for seg in segs:
            parts.append(seg.text)
            tokens += len(seg.tokens or [])
            for w in seg.words or []:
                words.append(
                    Word(
                        text=w.word.strip(),
                        start_s=round(float(w.start), 3),
                        end_s=round(float(w.end), 3),
                        prob=round(float(w.probability), 4),
                    )
                )
        return words, "".join(parts).strip(), tokens
