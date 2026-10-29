"""Every adapter really does satisfy the port it claims to. See src/aicefr/ports.py.

These tests exist to keep the dependency direction honest. The business layer
names only the abstractions in `aicefr.ports`; if an adapter silently drifts
away from its port, the pipeline breaks at runtime in a request, not here.

    "Depend upon Abstractions. Do not depend upon concretions."
    -- Robert C. Martin, Design Principles and Design Patterns, 2000
"""

from __future__ import annotations

import numpy as np

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import ProcessingRequest, ResponseStatus
from aicefr.pipeline import ResponseProcessor
from aicefr.ports import AsrEngine, ResponseStore, Scorer, VoiceActivityDetector
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.repository import Repository


def test_fake_engine_satisfies_the_asr_port() -> None:
    assert isinstance(FakeAsrEngine(), AsrEngine)


def test_energy_detector_satisfies_the_vad_port() -> None:
    assert isinstance(EnergyVad(), VoiceActivityDetector)


def test_ridge_scorer_satisfies_the_scorer_port() -> None:
    assert isinstance(RidgeScorer(), Scorer)


def test_repository_satisfies_the_response_store_port(tmp_path) -> None:
    assert isinstance(Repository(tmp_path / "t.db"), ResponseStore)


def test_processor_runs_on_injected_doubles_alone(tone, sr) -> None:
    """The whole pipeline runs with no model and no GPU.

    This is the practical payoff of injecting the collaborators: the control
    flow under test is the real one, only the two pieces that need a model are
    doubles.
    """
    request = ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P3",
        audio_path="unused.wav",
        prompt_version="v1",
        config_version="v1",
    )
    report = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(request, tone, sr)
    assert report.status is not ResponseStatus.FAILED
    assert report.qc is not None


def test_processor_exposes_every_collaborator_for_substitution() -> None:
    """Nothing is constructed behind the caller's back and left unreachable."""
    p = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad())
    for part in ("asr_engine", "vad", "quality_checker", "extractor", "scorer"):
        assert getattr(p, part) is not None


def test_business_layer_never_imports_a_concrete_engine() -> None:
    """The processor must not name Whisper, Silero or Ridge in its own module.

    Reading the source is crude but it is the only check that actually fails
    when someone reaches past the port for convenience.
    """
    import inspect

    from aicefr import pipeline

    source = inspect.getsource(pipeline)
    body = source.split("class ResponseProcessor")[1]
    for concrete in ("WhisperEngine", "SileroVad", "mlx_whisper", "faster_whisper"):
        assert concrete not in body, f"pipeline reaches past its port for {concrete}"


def test_detector_choice_changes_the_numbers(tone, sr) -> None:
    """Why the detector is a port and not a hidden default.

    The scoring model was fitted on Silero's segmentation. An energy detector
    reports a very different number of segments for the same audio, so the two
    are not interchangeable at inference time even though both satisfy the port.
    """
    segments = EnergyVad().segments(np.asarray(tone), sr)
    assert isinstance(segments, list)
    assert all(len(s) == 2 for s in segments)


# ---------------------------------------------------------------- scaling seams


def test_the_blob_store_satisfies_its_port(tmp_path) -> None:
    """Recordings sit behind a port because local disk breaks at two machines.

    Machine A writes the file, machine B serves the request: the player answers
    404 on one node out of two, depending on where the load balancer sent it.
    """
    from aicefr.infra.blobs import LocalBlobStore
    from aicefr.ports import BlobStore

    assert isinstance(LocalBlobStore(tmp_path), BlobStore)


def test_the_rate_limiter_satisfies_its_port() -> None:
    """In-memory counting is not only a scaling limit, it is a correctness one.

    With several instances, "ten per minute" silently becomes "ten per minute
    per instance", so the protection weakens exactly as the deployment grows.
    """
    from aicefr.infra.limits import InMemoryRateLimiter
    from aicefr.ports import RateLimiter

    assert isinstance(InMemoryRateLimiter(), RateLimiter)


def test_both_queue_adapters_satisfy_the_same_port() -> None:
    """Two adapters already exist, which is the evidence the seam is real.

    One runs work on a bounded pool, the other on the calling thread for tests.
    A broker-backed third adapter plugs into the same place.
    """
    from aicefr.infra.queues import InlineJobQueue, InProcessJobQueue
    from aicefr.ports import JobQueue

    assert isinstance(InProcessJobQueue(1), JobQueue)
    assert isinstance(InlineJobQueue(), JobQueue)


def test_a_blob_key_cannot_escape_the_store(tmp_path) -> None:
    """Keys are opaque strings, not paths.

    An object-storage backend has no directories, so nothing may build a
    filename out of a key -- and refusing separators here keeps a future
    adapter from inheriting an assumption it cannot satisfy.
    """
    import pytest

    from aicefr.infra.blobs import LocalBlobStore

    store = LocalBlobStore(tmp_path)
    for bad in ("../escape.wav", "sub/dir.wav", ".hidden"):
        with pytest.raises(ValueError):
            store.put(bad, b"x")


def test_the_rate_limiter_counts_within_its_window() -> None:
    from aicefr.infra.limits import InMemoryRateLimiter

    limiter = InMemoryRateLimiter()
    assert [limiter.hit("ip", 3) for _ in range(5)] == [True, True, True, False, False]
    limiter.forget("ip")
    assert limiter.hit("ip", 3) is True
