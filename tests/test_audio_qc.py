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


# ------------------------------------------- SEC-02: ngan sach PCM sau giai ma


def _wav(seconds: float, rate: int, channels: int = 1, fmt: str = "WAV") -> bytes:
    import io

    import soundfile as sf

    n = int(seconds * rate)
    t = np.arange(n) / rate
    mono = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    pcm = np.repeat(mono[:, None], channels, axis=1) if channels > 1 else mono
    buf = io.BytesIO()
    sf.write(buf, pcm, rate, format=fmt)
    return buf.getvalue()


def test_default_decoded_budget_is_330s_of_96khz_mono_float32(monkeypatch):
    """Mac dinh = MAX_DECODE_SECONDS x 96 kHz x 4 byte mono (~121 MiB)."""
    from aicefr import config
    from aicefr.audio.decoder import MAX_DECODE_SECONDS

    monkeypatch.delenv("AICEFR_MAX_DECODED_BYTES", raising=False)
    config.get_settings.cache_clear()
    assert config.get_settings().max_decoded_pcm_bytes == MAX_DECODE_SECONDS * 96_000 * 4
    monkeypatch.setenv("AICEFR_MAX_DECODED_BYTES", "1234")
    config.get_settings.cache_clear()
    assert config.get_settings().max_decoded_pcm_bytes == 1234
    config.get_settings.cache_clear()


@pytest.mark.parametrize("fmt", ["WAV", "FLAC"])
def test_over_budget_header_is_rejected_before_reading_pcm(fmt, monkeypatch):
    """Header khai 2 s x 48 kHz = 384 KB float32 mono; ngan sach 300 KB -> tu choi.

    Khong duoc doc mau nao: `SoundFile.read` bi chan, neu bi goi la test do.
    """
    import soundfile as sf

    from aicefr.audio.decoder import DecodeBudgetExceeded, SoundFileDecoder

    data = _wav(2.0, 48_000, channels=8, fmt=fmt)

    def no_read(*a, **k):
        raise AssertionError("PCM bi doc truoc khi kiem ngan sach")

    monkeypatch.setattr(sf.SoundFile, "read", no_read)
    monkeypatch.setattr(sf, "read", no_read)
    with pytest.raises(DecodeBudgetExceeded) as ei:
        SoundFileDecoder(max_pcm_bytes=300_000).decode(data, "a." + fmt.lower())
    e = ei.value
    assert e.reason is ReasonCode.AUDIO_TOO_LARGE
    assert e.channels == 8 and e.sample_rate == 48_000
    assert e.declared_seconds == pytest.approx(2.0)
    assert e.budget_bytes == 300_000
    assert e.needed_bytes == 2 * 48_000 * 4


def test_budget_counts_the_mono_array_kept_not_the_channels(monkeypatch):
    """Bo giai ma tron mono theo khoi, nen kenh khong nhan ngan sach (SEC-02).

    96 kHz stereo dai toi da 330 s van qua ngan sach mac dinh; header 192 kHz x
    8 kenh (~1,9 GiB neu giu ca mang da kenh) van bi tu choi.
    """
    from aicefr import config
    from aicefr.audio.decoder import MAX_DECODE_SECONDS, DecodeBudgetExceeded, check_budget

    monkeypatch.delenv("AICEFR_MAX_DECODED_BYTES", raising=False)
    config.get_settings.cache_clear()
    budget = config.get_settings().max_decoded_pcm_bytes
    config.get_settings.cache_clear()
    check_budget(2, 96_000, int(MAX_DECODE_SECONDS * 96_000), budget)
    with pytest.raises(DecodeBudgetExceeded):
        check_budget(8, 192_000, int(MAX_DECODE_SECONDS * 192_000), budget)


def test_budget_comes_from_settings_when_not_given(monkeypatch):
    from aicefr import config
    from aicefr.audio.decoder import DecodeBudgetExceeded, SoundFileDecoder

    monkeypatch.setenv("AICEFR_MAX_DECODED_BYTES", "10000")
    config.get_settings.cache_clear()
    try:
        with pytest.raises(DecodeBudgetExceeded):
            SoundFileDecoder().decode(_wav(1.0, 16_000), "a.wav")
    finally:
        config.get_settings.cache_clear()


def test_audio_within_budget_still_decodes_to_16k_mono():
    from aicefr.audio.decoder import SoundFileDecoder

    pcm, out_sr = SoundFileDecoder(max_pcm_bytes=10_000_000).decode(
        _wav(2.0, 48_000, channels=2, fmt="FLAC"), "a.flac"
    )
    assert out_sr == 16_000
    assert pcm.ndim == 1
    assert pcm.size == pytest.approx(32_000, abs=2)


def test_first_match_does_not_fall_through_on_budget():
    """Vuot ngan sach la ket luan, khong phai loi dinh dang: khong thu ffmpeg nua."""
    from aicefr.audio.decoder import DecodeBudgetExceeded, FirstMatchDecoder, SoundFileDecoder

    called = []

    class Spy:
        name = "spy"

        def can_decode(self, filename):
            return True

        def decode(self, data, filename):
            called.append(filename)
            return np.zeros(10, dtype=np.float32), 16_000

    dec = FirstMatchDecoder([SoundFileDecoder(max_pcm_bytes=1000), Spy()])
    with pytest.raises(DecodeBudgetExceeded):
        dec.decode(_wav(1.0, 16_000), "a.wav")
    assert called == []


class _Blobs:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def get(self, key):
        return self.data


def _worker(monkeypatch, data: bytes, budget: int, reports: list):
    from aicefr import config
    from aicefr.services.speech.worker import SpeechWorker

    monkeypatch.setenv("AICEFR_MAX_DECODED_BYTES", str(budget))
    config.get_settings.cache_clear()
    settings = config.get_settings()
    config.get_settings.cache_clear()
    return SpeechWorker(settings, blobs=_Blobs(data), report=reports.append)


def test_worker_reports_too_large_without_crashing(monkeypatch, caplog):
    import logging

    reports: list = []
    w = _worker(monkeypatch, _wav(2.0, 48_000, channels=2), 1000, reports)
    with caplog.at_level(logging.WARNING, logger="aicefr.services.speech.worker"):
        w.score({"response_id": "r-sec02", "audio_key": "r-sec02.wav", "priority": 1})
    assert reports[-1] == {"response_id": "r-sec02", "failed": ReasonCode.AUDIO_TOO_LARGE.value}
    rec = [r for r in caplog.records if r.getMessage().startswith("audio.decode_rejected")]
    assert rec, "thieu log audio.decode_rejected"
    msg = rec[0].getMessage()
    assert "decoded_budget_exceeded" in msg and "r-sec02" in msg
    assert "channels=2" in msg and "rate=48000" in msg and "threshold=1000" in msg


def test_worker_step_decodes_under_the_semaphore(monkeypatch):
    """Nhanh bai luyen tung giai ma TRUOC semaphore: N request = N mang PCM cung luc."""
    from aicefr.audio.decoder import DecodeError

    reports: list = []
    w = _worker(monkeypatch, _wav(1.0, 16_000), 10_000_000, reports)
    held = []

    class Slots:
        inside = False

        def __enter__(self):
            Slots.inside = True

        def __exit__(self, *a):
            Slots.inside = False

    class Dec:
        def decode(self, data, filename):
            held.append(Slots.inside)
            raise DecodeError("x")

    w.slots = Slots()
    w.decoder = Dec()
    out = w.step({"audio_key": "k.wav", "step": {}})
    assert out["error"] == "decode"
    assert held == [True]


def test_worker_step_and_probe_refuse_over_budget(monkeypatch):
    reports: list = []
    w = _worker(monkeypatch, _wav(2.0, 48_000, channels=2), 1000, reports)
    for out in (w.step({"audio_key": "k.wav", "step": {}}), w.probe({"audio_key": "k.wav"})):
        assert out["error"] == "decode"
        assert out["reason"] == ReasonCode.AUDIO_TOO_LARGE.value
