"""Voice activity detection. Cross-reference SDD section 4.2.

IMPORTANT: pause features must use the SAME VAD at training time and at scoring
time, otherwise the values drift badly. This actually bit us: the energy-based
VAD chops speech into many tiny segments, yielding about 90 segments per minute
where Silero yields roughly 3 to 34. The model then treats the input as
out-of-distribution and refuses to score it.

The currently trained model uses SileroVad. EnergyVad exists only to run tests
and as a fallback when Silero is not installed.
"""

from __future__ import annotations

import numpy as np


class EnergyVad:
    """Crude VAD based on per-frame energy. Deterministic, no extra dependency.

    For tests only. Do NOT use it to generate features for the model that was
    trained with Silero.
    """

    name = "energy"
    frame_ms = 30
    dbfs = -40.0

    def segments(self, pcm: np.ndarray, sr: int) -> list[tuple[float, float]]:
        n = max(int(sr * self.frame_ms / 1000), 1)
        if pcm.size < n:
            return []
        frames = pcm[: pcm.size // n * n].reshape(-1, n)
        rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
        voiced = 20 * np.log10(np.maximum(rms, 1e-10)) >= self.dbfs
        out: list[tuple[float, float]] = []
        start = None
        for i, v in enumerate(voiced):
            if v and start is None:
                start = i
            elif not v and start is not None:
                out.append((start * n / sr, i * n / sr))
                start = None
        if start is not None:
            out.append((start * n / sr, len(voiced) * n / sr))
        return out


class SileroVad:
    """The VAD used to generate model features. Its parameters must stay as they are.

    min_silence_duration_ms = 150 is the value used when the training features
    were computed. Changing it means the model has to be retrained.
    """

    name = "silero"
    threshold = 0.5
    min_silence_ms = 150

    def __init__(self) -> None:
        from silero_vad import load_silero_vad

        self._model = load_silero_vad()

    def segments(self, pcm: np.ndarray, sr: int) -> list[tuple[float, float]]:
        import torch
        from silero_vad import get_speech_timestamps

        ts = get_speech_timestamps(
            torch.from_numpy(np.ascontiguousarray(pcm)),
            self._model,
            sampling_rate=sr,
            return_seconds=True,
            threshold=self.threshold,
            min_silence_duration_ms=self.min_silence_ms,
        )
        return [(float(t["start"]), float(t["end"])) for t in ts]


def default_vad():
    """Use Silero when it is installed, otherwise fall back to EnergyVad."""
    try:
        return SileroVad()
    except Exception:
        return EnergyVad()
