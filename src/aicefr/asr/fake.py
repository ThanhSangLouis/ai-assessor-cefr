"""Stub engine used for tests and for demos before a real model is available.

It loads no model, needs no network, and its output is deterministic. This
engine is what let the whole pipeline and its tests run green before the model
was ready.
"""

from __future__ import annotations

import numpy as np

from aicefr.contracts import Transcript, Word


class FakeAsrEngine:
    """Emits a fixed transcript with timestamps spread evenly over the audio length."""

    name = "fake"

    def __init__(
        self,
        transcript: str | None = None,
        prob: float = 0.9,
        language: str | None = None,
        language_probability: float | None = None,
    ) -> None:
        self._text = transcript or (
            "i think that learning a new language is very useful for my future "
            "career because it helps me communicate with people from other countries"
        )
        self._prob = prob
        # Gia lap ket qua doan ngon ngu (D022). Mac dinh rong: ban gia lap
        # khong doan gi ca, giong mot model chi tieng Anh.
        self._language = language
        self._language_probability = language_probability

    def transcribe(self, pcm: np.ndarray, sr: int) -> Transcript:
        dur = pcm.size / sr if sr else 0.0
        toks = self._text.split()
        step = dur / max(len(toks), 1)
        words = [
            Word(
                text=t,
                start_s=round(i * step, 3),
                end_s=round(i * step + step * 0.8, 3),
                prob=self._prob,
            )
            for i, t in enumerate(toks)
        ]
        return Transcript(
            text=self._text,
            words=words,
            engine=self.name,
            model_version="fake-v1",
            is_verbatim=False,
            language=self._language,
            language_probability=self._language_probability,
        )
