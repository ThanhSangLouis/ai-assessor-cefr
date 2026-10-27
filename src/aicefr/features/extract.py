"""Extracts features from the transcript and from the VAD output.

Ported from the draft at sandi-work/features_v3.py. Implements FR-14 to FR-17.

An important note: Whisper's timestamps CANNOT be used to measure pauses. A
measurement on the dev set showed that 92.7% of the gaps between words were
exactly 0.00 seconds. The pause features must therefore come from a VAD run
over the waveform.
"""

from __future__ import annotations

import math

import numpy as np

from aicefr.contracts import Feature, FeatureSet, ReasonCode, Word

FEATURE_VERSION = "v3"
FILLERS = {"um", "uh", "hmm", "mm", "erm", "ah", "eh", "er"}
PAUSE_MIN_S = 0.30
LONG_PAUSE_S = 1.00
MIN_WORDS = 10

TEXT_FEATURES = (
    "n_words",
    "words_per_sec",
    "total_dur",
    "mean_word_len",
    "ttr",
    "log_uniq",
    "asr_conf_mean",
    "asr_conf_geo",
    "filler_ratio",
)
VAD_FEATURES = (
    "vad_silence_ratio",
    "vad_mean_pause",
    "vad_pause_per_min",
    "vad_long_pause_ratio",
    "vad_pause_sd",
    "vad_mean_seg_len",
    "vad_n_seg_per_min",
    "vad_articulation_rate",
    "vad_onset_delay",
    "vad_speech_sec",
)
ALL_FEATURES = TEXT_FEATURES + VAD_FEATURES


def _norm(text: str) -> str:
    return text.strip().strip('.,?!;:"').lower()


def text_features(words: list[Word], total_dur_s: float) -> dict[str, float]:
    """Transcript-based features. total_dur_s is the total length of the response."""
    toks = [_norm(w.text) for w in words if _norm(w.text)]
    n = len(toks)
    dur = total_dur_s if total_dur_s > 0 else 1e-6
    uniq = len(set(toks))
    probs = [w.prob for w in words if w.prob is not None]
    # No probabilities means unknown, not zero.
    #
    # Returning 0.0 made the router read "confidence below 0.65" and report
    # ASR_LOW_CONFIDENCE, so a teacher was told the recogniser was unsure when
    # in fact it had not reported confidence at all. The contract is explicit:
    # missing data returns None with a reason code, never a fabricated number.
    conf_mean = sum(probs) / len(probs) if probs else None
    conf_geo = math.exp(sum(math.log(max(p, 1e-4)) for p in probs) / len(probs)) if probs else None
    return {
        "n_words": float(n),
        "words_per_sec": n / dur,
        "total_dur": dur,
        "mean_word_len": sum(len(t) for t in toks) / max(n, 1),
        "ttr": uniq / max(n, 1),
        "log_uniq": math.log(uniq + 1),
        "asr_conf_mean": conf_mean,
        "asr_conf_geo": conf_geo,
        "filler_ratio": sum(t in FILLERS for t in toks) / max(n, 1),
    }


def vad_features(
    segments: list[tuple[float, float]], total_dur_s: float, n_words: int
) -> dict[str, float]:
    """Pause features. `segments` holds the speech segments, in seconds."""
    dur = total_dur_s if total_dur_s > 0 else 1e-6
    if not segments:
        return dict.fromkeys(VAD_FEATURES, 0.0)

    seg = sorted(segments)
    speech = sum(e - s for s, e in seg)
    seglens = [e - s for s, e in seg]
    gaps = [seg[i + 1][0] - seg[i][1] for i in range(len(seg) - 1)]
    tail = dur - seg[-1][1]
    if tail > PAUSE_MIN_S:
        gaps.append(tail)
    pauses = [g for g in gaps if g > PAUSE_MIN_S]

    return {
        "vad_silence_ratio": 1 - speech / dur,
        "vad_mean_pause": float(np.mean(pauses)) if pauses else 0.0,
        "vad_pause_per_min": len(pauses) / (dur / 60),
        "vad_long_pause_ratio": (
            sum(p > LONG_PAUSE_S for p in pauses) / len(pauses) if pauses else 0.0
        ),
        "vad_pause_sd": float(np.std(pauses)) if len(pauses) > 1 else 0.0,
        "vad_mean_seg_len": float(np.mean(seglens)),
        "vad_n_seg_per_min": len(seg) / (dur / 60),
        "vad_articulation_rate": n_words / max(speech, 1e-6),
        "vad_onset_delay": seg[0][0],
        "vad_speech_sec": speech,
    }


class FeatureExtractor:
    """Builds a FeatureSet from one transcript and its VAD segments.

    A class rather than a bare function because the feature version is
    configuration that has to travel with every FeatureSet it produces, and
    because the minimum word count is a decision that should be stated
    explicitly instead of hidden in a global constant. A scoring model is only
    valid against the exact feature version it was trained on, so the version
    belongs to the object that emits the features rather than to the module.
    """

    def __init__(
        self,
        feature_version: str = FEATURE_VERSION,
        min_words: int = MIN_WORDS,
    ) -> None:
        self.feature_version = feature_version
        self.min_words = min_words

    def extract(
        self,
        words: list[Word],
        segments: list[tuple[float, float]],
        total_dur_s: float,
    ) -> FeatureSet:
        """Merge both feature groups. A response that is too short marks the affected
        features as not computable."""
        t = text_features(words, total_dur_s)
        v = vad_features(segments, total_dur_s, int(t["n_words"]))
        values: dict[str, float | None] = {**t, **v}
        invalid: dict[str, ReasonCode] = {}

        if t["n_words"] < self.min_words:
            for name in ("ttr", "log_uniq", "mean_word_len", "filler_ratio"):
                values[name] = None
                invalid[name] = ReasonCode.TOO_FEW_WORDS
        if not segments:
            for name in VAD_FEATURES:
                values[name] = None
                invalid[name] = ReasonCode.FEATURE_NOT_COMPUTABLE

        # Whatever came back None WITHOUT a reason above gets one here, and this
        # line exists because one case really did slip through: `text_features`
        # returns `asr_conf_mean` as None when no word carries a probability, and
        # nothing recorded why. `Feature` now refuses a value-less measurement
        # with no reason, so the gap cannot reopen silently.
        for name, value in values.items():
            if value is None and name not in invalid:
                invalid[name] = ReasonCode.FEATURE_NOT_COMPUTABLE

        return FeatureSet(
            items=[
                Feature(name=name, value=value, reason=invalid.get(name))
                for name, value in values.items()
            ],
            feature_version=self.feature_version,
        )
