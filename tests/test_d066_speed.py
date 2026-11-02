"""The recogniser the model was fitted on, and requests that never wait on each other (D066).

On the two-vCPU production host, Whisper large-v3 took 55 s to transcribe a
42 s answer and 11 s more to tell its language, and every response was flagged
ASR_VERSION_MISMATCH because the scoring model was fitted on Whisper small.
The same answer through small takes a few seconds. Two handlers also waited for
the speech service on the event loop, so one lesson step held every other
request of the core service until it was measured.
"""

from __future__ import annotations

import asyncio

import pytest
from test_lessons_integration import (  # noqa: F401
    KEYWORDS,
    SAMPLE,
    login_as,
    m,
    record,
    submit_assessment,
)

from aicefr.asr.base import model_family
from aicefr.asr.whisper_adapter import (
    DEFAULT_CT2_MODEL,
    DEFAULT_MLX_REPO,
    WhisperEngine,
    threads_per_job,
)
from aicefr.contracts import ReasonCode, Transcript


@pytest.mark.parametrize(
    ("name", "family"),
    [
        ("small", "small"),
        ("whisper-small", "small"),
        ("mlx-community/whisper-small-mlx", "small"),
        ("Systran/faster-whisper-small", "small"),
        ("small.en", "small.en"),
        ("large-v3", "large-v3"),
        ("mlx-community/whisper-large-v3-turbo", "large-v3-turbo"),
        ("distil-large-v3", "distil-large-v3"),
        (None, ""),
    ],
)
def test_a_model_is_known_by_its_family_whatever_the_backend_calls_it(name, family) -> None:
    assert model_family(name) == family


def test_the_default_recogniser_is_the_one_the_model_was_fitted_on() -> None:
    from aicefr.scoring.scorer import RidgeScorer

    trained = model_family(RidgeScorer().trained_with["asr_model"])
    assert model_family(DEFAULT_CT2_MODEL) == trained
    assert model_family(DEFAULT_MLX_REPO) == trained
    assert WhisperEngine(backend="ct2").model == DEFAULT_CT2_MODEL


def test_faster_whisper_small_raises_no_mismatch_and_large_v3_does() -> None:
    """The old substring test read "whisper-small" as absent from "small"."""
    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.pipeline import ResponseProcessor

    processor = ResponseProcessor(FakeAsrEngine())

    def flags(model: str) -> list:
        heard = Transcript(text="x", engine="whisper-ct2", model_version=model)
        return processor._version_mismatches(heard)  # noqa: SLF001

    assert ReasonCode.ASR_VERSION_MISMATCH not in flags("small")
    assert ReasonCode.ASR_VERSION_MISMATCH in flags("large-v3")
    assert ReasonCode.ASR_VERSION_MISMATCH in flags("small.en")


def test_concurrent_jobs_share_the_cores_instead_of_fighting_over_them(monkeypatch) -> None:
    monkeypatch.setattr("os.cpu_count", lambda: 2)
    assert threads_per_job(2) == 1
    assert threads_per_job(1) == 2
    monkeypatch.setattr("os.cpu_count", lambda: 8)
    assert threads_per_job(2) == 4
    assert threads_per_job(0) == 8


def test_the_speech_worker_loads_its_recogniser_ahead_of_the_first_job() -> None:
    from aicefr.config import get_settings
    from aicefr.services.speech.worker import SpeechWorker

    loaded = []

    class Engine:
        model = "small"

        def warm_up(self):
            loaded.append(True)

    worker = SpeechWorker(get_settings(), blobs=None, report=lambda _m: None)
    worker._engine = Engine()  # noqa: SLF001
    worker.warm_up()
    assert loaded == [True]

    class Broken(Engine):
        def warm_up(self):
            raise RuntimeError("no model")

    worker._engine = Broken()  # noqa: SLF001
    worker.warm_up()  # logged, never raised: the first job reports it


def _off_the_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return True
    return False


def test_a_lesson_step_is_measured_off_the_event_loop(m, monkeypatch):  # noqa: F811
    from aicefr.services.core.learning import lessons_api

    seen = []
    real = lessons_api._measure

    def watched(*args, **kwargs):
        seen.append(_off_the_loop())
        return real(*args, **kwargs)

    monkeypatch.setattr(lessons_api, "_measure", watched)
    record(login_as(m, "SV-SP1"), SAMPLE, KEYWORDS)
    assert seen == [True]


def test_a_submission_is_stored_and_queued_off_the_event_loop(m, monkeypatch):  # noqa: F811
    from aicefr.services.core.assessment import responses_api

    seen = []
    real = responses_api.scoring.dispatch

    def watched(*args, **kwargs):
        seen.append(_off_the_loop())
        return real(*args, **kwargs)

    monkeypatch.setattr(responses_api.scoring, "dispatch", watched)
    submit_assessment(login_as(m, "SV-SP2"))
    assert seen == [True]
