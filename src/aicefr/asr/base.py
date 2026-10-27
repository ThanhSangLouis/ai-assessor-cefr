"""Common interface for every ASR engine. Cross-reference SDD section 4.3.

The point of this abstraction: swap engines without touching business logic,
and be able to write tests even before any model exists. That was the project's
single biggest risk, so it is addressed at the design layer.
"""

from __future__ import annotations

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
