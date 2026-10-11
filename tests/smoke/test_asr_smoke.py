"""M03-TEST-S1/S2 — smoke: the real faster-whisper `small` on audio we may use, offline.

Needs, outside the repository (M03 Test Plan v0.2):
  AICEFR_SMOKE_AUDIO       16 kHz mono WAV whose use is cleared (DEP-06)
  AICEFR_ASR_MODEL_DIR     CTranslate2 weight `whisper-small` (M03-EV-001);
                           default ~/models/faster-whisper-small
  AICEFR_SMOKE_EVIDENCE    optional JSON file to write the S1/S2 record into
Without the audio or the model the test is skipped, never passed. The record
holds metadata only: no transcript, no audio, no path inside the repository.

Run:  AICEFR_SMOKE_AUDIO=<path> pytest -q -m smoke tests/smoke/test_asr_smoke.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from aicefr.asr.local import FasterWhisperEngine
from aicefr.asr.service import DECODE_CONFIG_VERSION, AsrService
from aicefr.contracts import AsrStatus, DecodedAudio, QCResult, QCStatus, ReasonCode

pytestmark = pytest.mark.smoke

AUDIO = os.environ.get("AICEFR_SMOKE_AUDIO")
MODEL_DIR = Path(os.environ.get("AICEFR_ASR_MODEL_DIR", "~/models/faster-whisper-small"))
MODEL_DIR = MODEL_DIR.expanduser()
EVIDENCE = os.environ.get("AICEFR_SMOKE_EVIDENCE")
# asr_conf_mean seen in training (M03 Research I-01); S2 records, never gates.
TRAINING_RANGE = (0.691, 0.950)
MODEL_FILES = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_audio(path: Path) -> DecodedAudio:
    """The smoke audio as M02 hands it on: float32 mono at 16 kHz, with its hash."""
    import soundfile as sf

    samples, rate = sf.read(str(path), dtype="float32", always_2d=False)
    if rate != 16_000 or samples.ndim != 1:
        pytest.fail("smoke audio must be 16 kHz mono (prepare it outside the repository)")
    return DecodedAudio(
        samples=np.ascontiguousarray(samples),
        sample_rate_hz=16_000,
        duration_s=len(samples) / 16_000,
        audio_sha256=_sha256(path),
    )


def machine() -> dict:
    try:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        ram = None
    return {
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gib": round(ram / 2**30, 1) if ram else None,
        "python": platform.python_version(),
    }


def write_evidence(key: str, record: dict) -> None:
    if not EVIDENCE:
        return
    path = Path(EVIDENCE).expanduser()
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[key] = record
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def network_blocked() -> Iterator[list[str]]:
    """Any attempt to open a connection fails and is counted: "offline" is checked, not hoped."""
    attempts: list[str] = []

    def refuse(*args, **kwargs):
        attempts.append(repr(args[:2]))
        raise OSError("network disabled for the smoke test")

    with (
        patch.object(socket.socket, "connect", refuse),
        patch.object(socket.socket, "connect_ex", refuse),
        patch.object(socket, "create_connection", refuse),
        patch.object(socket, "getaddrinfo", refuse),
        patch.dict(os.environ, {"HF_HUB_OFFLINE": "1"}),
    ):
        yield attempts


def require_inputs() -> Path:
    if not AUDIO or not Path(AUDIO).expanduser().is_file():
        pytest.skip("AICEFR_SMOKE_AUDIO is not set to an existing file (DEP-06)")
    if not all((MODEL_DIR / name).is_file() for name in MODEL_FILES):
        pytest.skip(f"whisper-small weight not found in {MODEL_DIR} (M03-EV-001)")
    return Path(AUDIO).expanduser()


def test_s1_faster_whisper_small_runs_offline_and_s2_records_confidence():
    audio_path = require_inputs()
    audio = load_audio(audio_path)
    engine = FasterWhisperEngine(MODEL_DIR)
    service = AsrService(engine_loader=lambda: engine, trained_asr_model="whisper-small")
    qc = QCResult(status=QCStatus.PASS, reasons=(), qc_config_version="smoke")

    with network_blocked() as no_network:
        started = time.perf_counter()
        transcript = service.transcribe("smoke-s1", audio, qc)
        elapsed = time.perf_counter() - started

    # S1: a real, canonical model ran, offline, and gave a usable transcript.
    assert no_network == [], "the adapter tried to reach the network"
    assert transcript.status is AsrStatus.OK, transcript.reasons
    assert transcript.asr_model == "whisper-small"
    assert ReasonCode.ASR_VERSION_MISMATCH not in transcript.reasons
    assert transcript.test_only is False
    assert transcript.words and transcript.text.strip()
    assert all(0 <= w.start_s <= w.end_s <= audio.duration_s + 0.5 for w in transcript.words)

    # S2: observed, compared with the training range; out of range is reported, not failed.
    probs = [w.prob for w in transcript.words if w.prob is not None]
    conf_mean = sum(probs) / len(probs) if probs else None
    low, high = TRAINING_RANGE
    write_evidence(
        "M03-TEST-S1",
        {
            "weight": "whisper-small (Systran/faster-whisper-small, CTranslate2)",
            "weight_source": "Hugging Face Systran/faster-whisper-small (M03-EV-001)",
            "weight_license": "MIT (OpenAI Whisper weights, converted by SYSTRAN)",
            "weight_sha256": {name: _sha256(MODEL_DIR / name) for name in MODEL_FILES},
            "engine": transcript.engine,
            "engine_version": transcript.engine_version,
            "faster_whisper": version("faster-whisper"),
            "ctranslate2": version("ctranslate2"),
            "decode_config": {
                "version": DECODE_CONFIG_VERSION,
                "language": "en",
                "word_timestamps": True,
                "beam_size": 5,
                "vad_filter": False,
                "condition_on_previous_text": False,
                "device": engine.device,
                "compute_type": engine.compute_type,
            },
            "machine": machine(),
            "network_attempts": len(no_network),
            "audio_sha256": audio.audio_sha256,
            "audio_duration_s": round(audio.duration_s, 3),
            "audio_source": os.environ.get("AICEFR_SMOKE_AUDIO_SOURCE", "not stated"),
            "processing_s": round(elapsed, 3),
            "status": transcript.status.value,
            "reasons": [r.value for r in transcript.reasons],
            "n_words": len(transcript.words),
        },
    )
    write_evidence(
        "M03-TEST-S2",
        {
            "asr_conf_mean": None if conf_mean is None else round(conf_mean, 4),
            "words_with_prob": len(probs),
            "training_range": list(TRAINING_RANGE),
            "inside_training_range": conf_mean is not None and low <= conf_mean <= high,
        },
    )
    assert conf_mean is not None, "the engine returned no word probabilities"
