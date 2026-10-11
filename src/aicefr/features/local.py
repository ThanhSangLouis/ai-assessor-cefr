"""Offline Silero VAD adapter using the package's bundled JIT model."""

from __future__ import annotations

import math
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import numpy as np


class VadUnavailableError(RuntimeError):
    """Silero VAD package or its bundled model is unavailable."""


class SileroVadEngine:
    name = "silero"

    def __init__(self, *, threshold: float = 0.5, min_silence_ms: int = 150) -> None:
        if not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError("threshold must be finite and between 0 and 1")
        if type(min_silence_ms) is not int or min_silence_ms <= 0:
            raise ValueError("min_silence_ms must be a positive integer")
        self.threshold = float(threshold)
        self.min_silence_ms = int(min_silence_ms)
        self._model: Any = None
        try:
            self.version = version("silero-vad")
        except PackageNotFoundError:
            self.version = "unavailable"

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        if self.version == "unavailable":
            raise VadUnavailableError("Silero package version unavailable")
        try:
            from silero_vad import get_speech_timestamps, load_silero_vad
            model = load_silero_vad(onnx=False)
        except Exception as exc:
            raise VadUnavailableError("bundled local Silero model unavailable") from exc
        self._model = (model, get_speech_timestamps)
        return self._model

    def segments(self, samples: Any, sample_rate_hz: int) -> list[tuple[float, float]]:
        values = np.asarray(samples)
        if sample_rate_hz != 16_000 or values.ndim != 1 or values.dtype != np.float32:
            raise ValueError("Silero input must be mono float32 at 16 kHz")
        if not np.isfinite(values).all():
            raise ValueError("Silero input must be finite")
        if values.size == 0:
            return []
        model, get_speech_timestamps = self._load()
        import torch
        timestamps = get_speech_timestamps(
            torch.from_numpy(values.copy()), model, threshold=self.threshold,
            sampling_rate=16_000, min_silence_duration_ms=self.min_silence_ms,
            return_seconds=True,
        )
        return [(float(item["start"]), float(item["end"])) for item in timestamps]


__all__ = ["SileroVadEngine", "VadUnavailableError"]
