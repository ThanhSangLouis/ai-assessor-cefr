"""Audio quality checks run before ASR. Implements FR-06 to FR-09.

The thresholds come from SRS section FR-07, under `qc_config_version = "qc-v1"`.
The SRS states plainly that these are candidate thresholds that have not been
validated yet, so every change must bump the version and be recorded in the
report.

Three outcome levels instead of a single bool:

    REJECT  stop outright, do not call ASR   (AC-07.1)
    REVIEW  still score, but flag it for a teacher to look at
    PASS    normal

The module used to return a `passed` bool whose blocking set held only the three
codes about size and format. The consequence: AUDIO_TOO_SHORT did not block, so
a 5-second file went straight through to scoring and was handed a CEFR band.
That is exactly the warning layer that is lost when the middle ground is folded
into PASS.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aicefr.config import get_settings
from aicefr.contracts import QcResult, QcStatus, ReasonCode

QC_CONFIG_VERSION = "qc-v1"

# Mot nguon duy nhat: AICEFR_MAX_UPLOAD (mac dinh 25 MiB). Truoc day ghi cung o
# day va o main.py, nen bien moi truong co trong huong dan nhung khong tac dung.
MAX_BYTES = get_settings().max_upload_bytes
TARGET_SR = 16_000

# Duration, in seconds. SRS: REJECT < 20 or > 300; REVIEW 20-29; PASS 30-300.
MIN_DURATION_S = 20.0
REVIEW_DURATION_S = 30.0
MAX_DURATION_S = 300.0

# Ratio of samples hitting the amplitude ceiling. SRS: REJECT > 0.05; REVIEW 0.01-0.05.
REVIEW_CLIPPING_RATIO = 0.01
MAX_CLIPPING_RATIO = 0.05

# Ratio of silent frames. SRS: REJECT > 0.70; REVIEW 0.50-0.70.
REVIEW_SILENCE_RATIO = 0.50
MAX_SILENCE_RATIO = 0.70

# Signal-to-noise ratio, in dB. SRS: REJECT < 5; REVIEW 5-12; PASS > 12.
MIN_SNR_DB = 5.0
REVIEW_SNR_DB = 12.0

CLIP_LEVEL = 0.999
SILENCE_DBFS = -40.0
FRAME_MS = 30


@dataclass(frozen=True)
class QcThresholds:
    """Configurable thresholds. Every change must bump qc_config_version."""

    min_duration_s: float = MIN_DURATION_S
    review_duration_s: float = REVIEW_DURATION_S
    max_duration_s: float = MAX_DURATION_S
    review_clipping_ratio: float = REVIEW_CLIPPING_RATIO
    max_clipping_ratio: float = MAX_CLIPPING_RATIO
    review_silence_ratio: float = REVIEW_SILENCE_RATIO
    max_silence_ratio: float = MAX_SILENCE_RATIO
    min_snr_db: float = MIN_SNR_DB
    review_snr_db: float = REVIEW_SNR_DB
    silence_dbfs: float = SILENCE_DBFS


def _frame_levels(pcm: np.ndarray, sr: int) -> np.ndarray:
    """Per-frame level in dBFS. Each frame is FRAME_MS milliseconds wide."""
    n = max(int(sr * FRAME_MS / 1000), 1)
    if pcm.size < n:
        return np.array([], dtype=np.float64)
    frames = pcm[: pcm.size // n * n].reshape(-1, n)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-10))


def silence_ratio(pcm: np.ndarray, sr: int, dbfs: float = SILENCE_DBFS) -> float:
    """Ratio of frames whose level is below the threshold. No VAD, energy only."""
    level = _frame_levels(pcm, sr)
    if level.size == 0:
        return 1.0
    return float(np.mean(level < dbfs))


def clipping_ratio(pcm: np.ndarray, level: float = CLIP_LEVEL) -> float:
    """Ratio of samples hitting the amplitude ceiling, a sign of recording too loud."""
    if pcm.size == 0:
        return 0.0
    return float(np.mean(np.abs(pcm) >= level))


def estimate_snr_db(pcm: np.ndarray, sr: int, dbfs: float = SILENCE_DBFS) -> float | None:
    """Estimate the signal-to-noise ratio from the recording itself.

    Method: split frames by level, take the median energy of the loud group as
    the signal and the median of the quiet group as the noise floor, then take
    the difference in dB.

    This is an ESTIMATE, not an exact measurement. There is no clean reference
    recording, so true noise cannot be separated from quietly spoken passages.
    Returns None when the recording does not contain both groups of frames,
    rather than inventing a number.
    """
    level = _frame_levels(pcm, sr)
    if level.size < 4:
        return None
    speech = level[level >= dbfs]
    noise = level[level < dbfs]
    if speech.size == 0 or noise.size == 0:
        return None
    return float(np.median(speech) - np.median(noise))


class AudioQualityChecker:
    """Applies the SRS quality thresholds to a single recording.

    A class rather than a bare function because the thresholds are
    configuration, not arguments: they belong to the object, they carry a
    version, and every report has to state which set produced it. Passing them
    per call made it far too easy to check one recording against one set and
    the next against another.
    """

    def __init__(
        self, thresholds: QcThresholds | None = None, config_version: str | None = None
    ) -> None:
        self.thresholds = thresholds or QcThresholds()
        # The version travels with the thresholds, not with the module. An
        # administrator who changes a threshold at runtime (FR-08) gets a new
        # label, so a report can always be traced to the exact numbers that
        # produced it -- including the ones that were only in force for a week.
        self.config_version = config_version or QC_CONFIG_VERSION

    def check(
        self,
        pcm: np.ndarray,
        sr: int,
        channels: int = 1,
        size_bytes: int | None = None,
    ) -> QcResult:
        """Run every check and return the three-level outcome with its reasons."""
        t = self.thresholds
        reject: list[ReasonCode] = []
        review: list[ReasonCode] = []

        duration_s = pcm.size / sr if sr else 0.0

        # --- Input: a failure here stops outright, there is no middle ground ---
        if size_bytes is not None and size_bytes > MAX_BYTES:
            reject.append(ReasonCode.AUDIO_TOO_LARGE)
        if sr != TARGET_SR:
            reject.append(ReasonCode.WRONG_SAMPLE_RATE)

        # --- Duration ---
        if duration_s > t.max_duration_s:
            reject.append(ReasonCode.AUDIO_TOO_LONG)
        elif duration_s < t.min_duration_s:
            reject.append(ReasonCode.AUDIO_TOO_SHORT)
        elif duration_s < t.review_duration_s:
            review.append(ReasonCode.AUDIO_TOO_SHORT)

        # --- Clipping ---
        clip = clipping_ratio(pcm)
        if clip > t.max_clipping_ratio:
            reject.append(ReasonCode.CLIPPING_DETECTED)
        elif clip >= t.review_clipping_ratio:
            review.append(ReasonCode.CLIPPING_DETECTED)

        # --- Silence ---
        sil = silence_ratio(pcm, sr, t.silence_dbfs)
        if sil > t.max_silence_ratio:
            reject.append(ReasonCode.HIGH_SILENCE_RATIO)
        elif sil >= t.review_silence_ratio:
            review.append(ReasonCode.HIGH_SILENCE_RATIO)

        # --- Signal-to-noise ratio ---
        snr = estimate_snr_db(pcm, sr, t.silence_dbfs)
        if snr is not None:
            if snr < t.min_snr_db:
                reject.append(ReasonCode.LOW_SNR)
            elif snr <= t.review_snr_db:
                review.append(ReasonCode.LOW_SNR)

        if reject:
            status = QcStatus.REJECT
        elif review:
            status = QcStatus.REVIEW
        else:
            status = QcStatus.PASS

        return QcResult(
            duration_ms=int(duration_s * 1000),
            sample_rate_hz=sr,
            channels=channels,
            silence_ratio=round(sil, 4),
            clipping_ratio=round(clip, 4),
            snr_db=round(snr, 2) if snr is not None else None,
            qc_status=status,
            qc_config_version=self.config_version,
            reasons=list(dict.fromkeys(reject + review)),
        )
