"""Offline faster-whisper adapter. Model files must already exist locally."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from aicefr.asr.service import EngineResult, ModelUnavailableError, RawWord
from aicefr.contracts import DecodedAudio

_SMALL_MODEL_SHA256 = {
    "model.bin": "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
    "config.json": "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
    "tokenizer.json": "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
    "vocabulary.txt": "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FasterWhisperEngine:
    """Lazy, local-only Whisper engine implementing :class:`AsrEngine`."""

    def __init__(
        self,
        model_dir: str | Path,
        *,
        weight_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_dir = Path(model_dir).expanduser()
        self.weight_name = weight_name
        self.device = device
        self.compute_type = compute_type
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        required = tuple(_SMALL_MODEL_SHA256)
        if not self.model_dir.is_dir() or any(
            not (self.model_dir / name).is_file() for name in required
        ):
            raise ModelUnavailableError("local ASR model directory unavailable")
        if self.weight_name == "small":
            try:
                if any(
                    _sha256_file(self.model_dir / name) != expected
                    for name, expected in _SMALL_MODEL_SHA256.items()
                ):
                    raise ModelUnavailableError("local ASR model provenance mismatch")
            except OSError as exc:
                raise ModelUnavailableError("local ASR model unavailable") from exc
        try:
            from importlib.metadata import version as package_version

            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelUnavailableError("faster-whisper dependency unavailable") from exc
        try:
            self._model = WhisperModel(
                str(self.model_dir),
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
                cpu_threads=1 if self.device == "cpu" else 0,
            )
            self._version = package_version("faster-whisper")
        except Exception as exc:
            # Constructor errors can include machine paths; expose only a stable refusal.
            raise ModelUnavailableError("local ASR model unavailable") from exc
        return self._model

    def transcribe(self, audio: DecodedAudio) -> EngineResult:
        model = self._load()
        try:
            language, language_probability = self.detect_language(audio)
        except Exception:
            # LID uncertainty must not abort the independent recognition pass.
            language, language_probability = None, None
        segments, _info = model.transcribe(
            audio.samples,
            language="en",
            word_timestamps=True,
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        words: list[RawWord] = []
        text: list[str] = []
        for segment in segments:
            text.append(str(segment.text))
            for word in segment.words or ():
                probability = getattr(word, "probability", None)
                words.append(
                    RawWord(
                        text=str(word.word),
                        start_s=float(word.start),
                        end_s=float(word.end),
                        prob=None if probability is None else float(probability),
                    )
                )
        return EngineResult(
            text="".join(text),
            words=tuple(words),
            engine="faster-whisper",
            engine_version=self._version,
            weight_name=f"Systran/faster-whisper-{self.weight_name}",
            language=language,
            language_probability=language_probability,
            language_method="faster-whisper-detect-v1",
            language_version=self._version,
        )

    def detect_language(self, audio: DecodedAudio) -> tuple[str | None, float | None]:
        """Detect from at most 30 seconds with multilingual auto-detection.

        `info` is available immediately; the unused segment generator is never
        decoded or iterated. This call is independent of forced-English ASR.
        """
        model = self._load()
        samples = audio.samples[: 30 * audio.sample_rate_hz]
        _segments, info = model.transcribe(
            samples,
            language=None,
            word_timestamps=False,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        language = getattr(info, "language", None)
        probability = getattr(info, "language_probability", None)
        if not isinstance(language, str) or not language.strip():
            return None, None
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            return language, None
        return language, float(probability)


__all__ = ["FasterWhisperEngine"]
