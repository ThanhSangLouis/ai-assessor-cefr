"""D051: counters and histograms in Prometheus text format, without personal data."""

from __future__ import annotations

import pytest

from aicefr import observability as obs

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(obs, "_counters", obs.Counter())
    monkeypatch.setattr(obs, "_histograms", {})


def test_a_histogram_counts_each_observation_in_every_bucket_above_it():
    obs.observe("job_seconds", 0.3, purpose="assessment")
    obs.observe("job_seconds", 7.0, purpose="assessment")
    text = obs.render_metrics()
    assert "# TYPE aicefr_job_seconds histogram" in text
    assert 'aicefr_job_seconds_bucket{purpose="assessment",le="0.25"} 0' in text
    assert 'aicefr_job_seconds_bucket{purpose="assessment",le="0.5"} 1' in text
    assert 'aicefr_job_seconds_bucket{purpose="assessment",le="10.0"} 2' in text
    assert 'aicefr_job_seconds_bucket{purpose="assessment",le="+Inf"} 2' in text
    assert 'aicefr_job_seconds_sum{purpose="assessment"} 7.300000' in text
    assert 'aicefr_job_seconds_count{purpose="assessment"} 2' in text


def test_timed_records_a_block_that_raises():
    with pytest.raises(RuntimeError), obs.timed("pipeline_stage_seconds", stage="asr"):
        raise RuntimeError("recogniser down")
    assert 'aicefr_pipeline_stage_seconds_count{stage="asr"} 1' in obs.render_metrics()


def test_counters_keep_their_labels_apart_and_quotes_are_escaped():
    obs.count("requests_total")
    obs.count("metering_units_total", 10, action="assess", state="charged")
    obs.count("metering_units_total", 5, action="practice", state="charged")
    obs.count("odd_total", route='say "hi"')
    text = obs.render_metrics()
    assert text.count("# TYPE aicefr_metering_units_total counter") == 1
    assert 'aicefr_metering_units_total{action="assess",state="charged"} 10' in text
    assert 'aicefr_metering_units_total{action="practice",state="charged"} 5' in text
    assert "aicefr_requests_total 1" in text
    assert 'route="say \\"hi\\""' in text


def test_a_request_is_timed_by_its_route_template_not_its_path(tmp_path, monkeypatch):
    """A path holds ids; the template does not."""
    import importlib

    from fastapi.testclient import TestClient

    monkeypatch.chdir(tmp_path)
    from aicefr.api import main

    importlib.reload(main)
    TestClient(main.app).get("/api/v1/responses/abc123/status")
    text = obs.render_metrics()
    assert 'route="/api/v1/responses/{response_id}/status"' in text
    assert "abc123" not in text
