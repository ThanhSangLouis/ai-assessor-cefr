"""M04-TEST-S1 — smoke: the real Silero VAD 6.2.1 on audio we may use, offline.

Same inputs as `test_asr_smoke.py` (AICEFR_SMOKE_AUDIO, AICEFR_ASR_MODEL_DIR,
AICEFR_SMOKE_EVIDENCE). The pause features are measured by Silero on the audio;
`vad_articulation_rate` also needs the word count, which comes from the real
whisper-small transcript, never from a transcript written for the test.

Run:  AICEFR_SMOKE_AUDIO=<path> pytest -q -m smoke tests/smoke/test_vad_smoke.py
"""

from __future__ import annotations

import time
from importlib.metadata import version

import pytest
from test_asr_smoke import (
    MODEL_DIR,
    load_audio,
    machine,
    network_blocked,
    require_inputs,
    write_evidence,
)

from aicefr.asr.local import FasterWhisperEngine
from aicefr.asr.service import AsrService
from aicefr.contracts import AsrStatus, QCResult, QCStatus
from aicefr.features.extractor import FeatureExtractor
from aicefr.features.local import SileroVadEngine
from aicefr.features.pauses import VAD_FEATURES

pytestmark = pytest.mark.smoke


def test_s1_silero_segments_the_audio_offline_and_gives_every_pause_feature():
    audio = load_audio(require_inputs())
    vad = SileroVadEngine(threshold=0.5, min_silence_ms=150)

    with network_blocked() as no_network:
        started = time.perf_counter()
        segments = vad.segments(audio.samples, audio.sample_rate_hz)
        vad_s = time.perf_counter() - started

    assert no_network == [], "Silero tried to reach the network"
    assert segments, "Silero found no speech in a recording of speech"
    assert all(0 <= a < b <= audio.duration_s + 0.1 for a, b in segments)
    assert all(b1 <= a2 for (_a1, b1), (a2, _b2) in zip(segments, segments[1:], strict=False))

    engine = FasterWhisperEngine(MODEL_DIR)
    transcript = AsrService(engine_loader=lambda: engine, trained_asr_model="whisper-small")
    transcript = transcript.transcribe(
        "smoke-vad-s1", audio, QCResult(status=QCStatus.PASS, reasons=(), qc_config_version="smoke")
    )
    assert transcript.status is AsrStatus.OK, transcript.reasons
    names = tuple(VAD_FEATURES)
    trained = {"vad_name": "silero", "vad_threshold": 0.5, "vad_min_silence_ms": 150}
    features = FeatureExtractor(names, "v3", trained, vad).extract(transcript, audio)

    values = {v.name: v.value for v in features.values}
    assert len(values) == 10 == len(VAD_FEATURES)
    assert all(v is not None for v in values.values()), values
    assert features.vad_name == "silero" and features.reasons == ()
    write_evidence(
        "M04-TEST-S1",
        {
            "silero_vad": version("silero-vad"),
            "silero_license": "MIT (snakers4/silero-vad; model bundled in the package)",
            "torch": version("torch"),
            "threshold": vad.threshold,
            "min_silence_ms": vad.min_silence_ms,
            "machine": machine(),
            "network_attempts": len(no_network),
            "audio_sha256": audio.audio_sha256,
            "audio_duration_s": round(audio.duration_s, 3),
            "segments": len(segments),
            "vad_s": round(vad_s, 3),
            "vad_features": {k: round(v, 4) for k, v in values.items()},
        },
    )
