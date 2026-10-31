"""Common interface for every ASR engine. Cross-reference SDD section 4.3.

The point of this abstraction: swap engines without touching business logic,
and be able to write tests even before any model exists. That was the project's
single biggest risk, so it is addressed at the design layer.
"""

from __future__ import annotations

import re
from typing import Protocol

import numpy as np

from aicefr.contracts import Transcript


class AsrError(RuntimeError):
    """The engine failed. The pipeline must catch this and map it to the
    ASR_FAILED reason code."""


class AsrEngine(Protocol):
    """Every engine must return an Transcript, never a bare string."""

    name: str

    def transcribe(self, pcm: np.ndarray, sr: int) -> Transcript: ...


def model_family(name: str | None) -> str:
    """The Whisper model a name refers to, whatever the backend calls it.

    "small" (faster-whisper), "whisper-small" (an artifact's `trained_with`)
    and "mlx-community/whisper-small-mlx" are one model; "small.en" and
    "large-v3-turbo" are others. Compared exactly: a substring test read
    "whisper-small" as absent from "small" and flagged the right recogniser.
    """
    base = (name or "").strip().lower().rsplit("/", 1)[-1]
    base = re.sub(r"^(openai-|faster-)?whisper-", "", base)
    return re.sub(r"-(mlx|ct2|int8|fp16)$", "", base)
