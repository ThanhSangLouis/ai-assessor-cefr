"""QC module tests. Cross-reference FR-06 to FR-09."""

import numpy as np
import pytest

from aicefr.contracts import QcStatus, ReasonCode
from aicefr.qc.audio_qc import (
    MAX_BYTES,
    AudioQualityChecker,
    clipping_ratio,
    silence_ratio,
)


def test_valid_audio_passes(tone, sr):
    r = AudioQualityChecker().check(tone, sr)
    assert r.qc_status is QcStatus.PASS
    assert r.passed is True
    assert r.reasons == []
    assert r.sample_rate_hz == sr
    assert 39_000 <= r.duration_ms <= 41_000


def test_response_under_20_seconds_rejected(tone, sr):
    """AC-07.1: 14 seconds of audio must be REJECTed and ASR must not be called at all."""
    r = AudioQualityChecker().check(tone[: sr * 14], sr)
    assert r.qc_status is QcStatus.REJECT
    assert r.passed is False
    assert ReasonCode.AUDIO_TOO_SHORT in r.reasons


def test_20_to_29_second_response_goes_to_teacher(tone, sr):
    """The SRS middle zone: scorable, but the result must not be treated as certain."""
    r = AudioQualityChecker().check(tone[: sr * 25], sr)
    assert r.qc_status is QcStatus.REVIEW
    assert r.passed is True
    assert ReasonCode.AUDIO_TOO_SHORT in r.reasons


def test_30_second_response_passes(tone, sr):
    r = AudioQualityChecker().check(tone[: sr * 30], sr)
    assert r.qc_status is QcStatus.PASS


def test_too_long_response_blocked(sr):
    long_pcm = np.zeros(sr * 400, dtype=np.float32)
    r = AudioQualityChecker().check(long_pcm, sr)
    assert ReasonCode.AUDIO_TOO_LONG in r.reasons
    assert r.qc_status is QcStatus.REJECT


def test_wrong_sample_rate_blocked(tone):
    r = AudioQualityChecker().check(tone, 8_000)
    assert ReasonCode.WRONG_SAMPLE_RATE in r.reasons
    assert r.qc_status is QcStatus.REJECT


def test_oversized_file_blocked(tone, sr):
    r = AudioQualityChecker().check(tone, sr, size_bytes=MAX_BYTES + 1)
    assert ReasonCode.AUDIO_TOO_LARGE in r.reasons
    assert r.qc_status is QcStatus.REJECT


def test_detects_clipping(tone, sr):
    r = AudioQualityChecker().check(np.clip(tone * 10, -1, 1).astype(np.float32), sr)
    assert ReasonCode.CLIPPING_DETECTED in r.reasons


def test_complete_silence_rejected(sr):
    r = AudioQualityChecker().check(np.zeros(sr * 40, dtype=np.float32), sr)
    assert ReasonCode.HIGH_SILENCE_RATIO in r.reasons
    assert r.qc_status is QcStatus.REJECT


def test_qc_records_threshold_version(tone, sr):
    """The report must be traceable back to the threshold set that was used, per FR-27."""
    assert AudioQualityChecker().check(tone, sr).qc_config_version == "qc-v1"


@pytest.mark.parametrize("n", [0, 1, 100])
def test_does_not_break_on_very_short_input(n, sr):
    r = AudioQualityChecker().check(np.zeros(n, dtype=np.float32), sr)
    assert 0.0 <= r.silence_ratio <= 1.0


def test_clipping_ratio_of_empty_array_is_zero():
    assert clipping_ratio(np.array([], dtype=np.float32)) == 0.0


def test_silence_ratio_within_unit_interval(tone, sr):
    assert 0.0 <= silence_ratio(tone, sr) <= 1.0
