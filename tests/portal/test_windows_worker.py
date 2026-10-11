from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from aicefr.contracts import (
    AsrStatus,
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    DecodedAudio,
    FeatureSet,
    FeatureValue,
    Provenance,
    ReasonCode,
    Transcript,
    Word,
)
from aicefr.local.worker import BackgroundPipeline
from aicefr.scoring.windows import score_windows, window_ranges
from conftest import submit_completed


@pytest.mark.parametrize("duration", [61, 70, 120, 130, 180, 300])
def test_windows_cover_tail_without_overlap_and_stay_in_training_duration(duration):
    ranges = window_ranges(duration)
    assert ranges[0][0] == 0 and ranges[-1][1] == duration
    assert all(30 <= end - start <= 60 for start, end in ranges)
    assert all(left[1] == right[0] for left, right in zip(ranges, ranges[1:], strict=False))


def test_window_scoring_requires_all_windows_and_keeps_relative_word_evidence():
    duration = 100
    audio = DecodedAudio(
        samples=np.full(duration * 16000, 0.2, dtype=np.float32),
        sample_rate_hz=16000,
        duration_s=duration,
        audio_sha256="a" * 64,
    )
    transcript = Transcript(
        response_id="fixture-response",
        status=AsrStatus.OK,
        text="one two",
        words=(Word(text="one", start_s=1, end_s=2), Word(text="two", start_s=51, end_s=52)),
        engine="fixture-asr",
        engine_version="1",
        decode_config_version="fixture-v1",
        audio_sha256=audio.audio_sha256,
        asr_model="whisper-small",
    )

    class Extractor:
        def extract(self, local_transcript, segment):
            assert local_transcript.words[0].start_s == 1
            assert local_transcript.words[0].end_s == 2
            assert local_transcript.audio_sha256 == segment.audio_sha256
            assert segment.duration_s == 50
            return FeatureSet(
                response_id=transcript.response_id,
                values=(FeatureValue(name="total_dur", value=50, unit="s"),),
                feature_version="fixture-v1",
                vad_name="fixture-vad",
                vad_version="1",
                vad_threshold=0.5,
                vad_min_silence_ms=150,
                asr_model="whisper-small",
                transcript_ref=transcript.response_id,
                audio_sha256=segment.audio_sha256,
            )

    class Scorer:
        artifact = SimpleNamespace(
            feature_order=("total_dur",),
            feature_lo=(26,),
            feature_hi=(61,),
            band_thresholds={"A2_B1": 3, "B1_B2": 4},
        )
        fail = False
        calls = 0

        def score(self, features, local_transcript):
            self.calls += 1
            failure = self.fail and self.calls % 2 == 0
            return Assessment(
                response_id=features.response_id,
                status=AssessmentStatus.NOT_EVALUATED if failure else AssessmentStatus.ESTIMATED,
                overall_score=None if failure else 3.5 + self.calls / 10,
                overall_band=None if failure else Band.B1,
                criteria=tuple(CriterionCoverage(criterion=c) for c in Criterion),
                reasons=(ReasonCode.OUT_OF_DISTRIBUTION,) if failure else (),
                provenance=Provenance(
                    model_version="fixture",
                    model_sha256="a" * 64,
                    feature_version="fixture-v1",
                    band_map_version="band-v1",
                    calibration_version="not-validated",
                    trained_with={},
                    unit_of_inference="one response",
                    scored_at="2026-10-08T00:00:00+00:00",
                ),
            )

    scorer = Scorer()
    candidate, provenance = score_windows(audio, transcript, Extractor(), scorer)
    assert candidate.status is AssessmentStatus.REVIEW_REQUIRED
    assert candidate.overall_score == pytest.approx(3.65)
    assert ReasonCode.SCORE_AGGREGATED in candidate.reasons
    rows = json.loads(provenance["window_results"])
    assert rows[1]["start_s"] == 50 and rows[1]["end_s"] == 100
    scorer.fail = True
    invalid, _ = score_windows(audio, transcript, Extractor(), scorer)
    assert invalid.status is AssessmentStatus.NOT_EVALUATED
    assert invalid.overall_score is None and invalid.overall_band is None
    assert ReasonCode.OUT_OF_DISTRIBUTION in invalid.reasons


def test_worker_owns_connection_and_processes_durable_queue(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?", ("QUEUED", response.response_id)
    )
    from aicefr.storage.sqlite import SQLiteStore

    ready = threading.Event()
    finished = threading.Event()
    threads = []

    def factory():
        store = SQLiteStore(runtime.store.data_dir)

        def enqueue(record):
            threads.append(threading.current_thread().name)
            store.claim_queued_response(record)
            finished.set()

        ready.set()
        return SimpleNamespace(
            store=store,
            control=SimpleNamespace(reload=lambda: None, pipeline=SimpleNamespace(enqueue=enqueue)),
            close=store.close,
        )

    worker = BackgroundPipeline(runtime.store, factory, capacity=1)
    try:
        assert ready.wait(5)
        worker.enqueue(response)
        assert finished.wait(5)
        assert threads == ["aicefr-local-worker"]
        assert runtime.store.get_response(response.response_id).status.value == "RUNNING"
    finally:
        worker.close()
    assert not worker._thread.is_alive()


def test_worker_capacity_rejects_extra_jobs_without_unbounded_memory(portal_runtime):
    runtime, tokens = portal_runtime
    first = submit_completed(runtime, tokens["a"])
    second = submit_completed(runtime, tokens["a"])
    runtime.store.connection.execute("UPDATE responses SET status=?", ("RUNNING",))
    # No worker DB mutations; use a connection opened only inside its thread.
    from aicefr.storage.sqlite import SQLiteStore

    def factory():
        store = SQLiteStore(runtime.store.data_dir)
        return SimpleNamespace(store=store, close=store.close)

    worker = BackgroundPipeline(runtime.store, factory, capacity=1)
    try:
        with pytest.raises(ValueError, match="full"):
            worker.enqueue(first)
        assert second.response_id != first.response_id
    finally:
        worker.close()
