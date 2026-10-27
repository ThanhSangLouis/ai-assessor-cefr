"""Layer 1 -- UNIT: the decoding temperature switch and the repeatability numbers.

HUONG_PHAT_TRIEN_TIEP §2.2: the same recording can come back with a different
transcript, because Whisper re-decodes some segments by random sampling. The
switch that turns that off must actually reach the recogniser, and the numbers
that say how much it matters must be computed the way they are named.
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from aicefr.research.repeatability import Run, summarise

pytestmark = pytest.mark.unit


def test_the_setting_reads_a_temperature_or_keeps_the_fallback(monkeypatch) -> None:
    from aicefr.config import Settings

    for raw, expected in (
        (None, None),
        ("fallback", None),
        ("0", 0.0),
        ("0.2", 0.2),
        ("abc", None),
        ("2", None),
    ):
        if raw is None:
            monkeypatch.delenv("AICEFR_ASR_TEMPERATURE", raising=False)
        else:
            monkeypatch.setenv("AICEFR_ASR_TEMPERATURE", raw)
        assert Settings().asr_temperature == expected, raw


def test_a_fixed_temperature_reaches_mlx_and_the_fallback_sends_none(monkeypatch) -> None:
    from aicefr.asr.whisper_adapter import WhisperEngine

    calls: list[dict] = []

    def transcribe(audio, **kwargs):
        calls.append(kwargs)
        return {"text": "hello", "segments": []}

    monkeypatch.setitem(sys.modules, "mlx_whisper", types.SimpleNamespace(transcribe=transcribe))
    pcm = np.zeros(16_000, dtype=np.float32)
    WhisperEngine(backend="mlx", temperature=0.0).transcribe(pcm, 16_000)
    WhisperEngine(backend="mlx").transcribe(pcm, 16_000)
    fixed, fallback = (c for c in calls if c.get("word_timestamps"))
    assert fixed["temperature"] == 0.0
    assert "temperature" not in fallback
    assert WhisperEngine(backend="mlx", temperature=0.0).decoding == "temperature=0.0"
    assert WhisperEngine(backend="mlx").decoding == "fallback"


def test_a_fixed_temperature_reaches_faster_whisper(monkeypatch) -> None:
    from aicefr.asr.whisper_adapter import WhisperEngine

    seen: dict = {}

    class Model:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, pcm, **kwargs):
            if kwargs.get("word_timestamps"):
                seen.update(kwargs)
            info = types.SimpleNamespace(language="en", language_probability=0.99)
            return iter(()), info

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=Model))
    WhisperEngine(backend="ct2", temperature=0.0).transcribe(np.zeros(16_000, np.float32), 16_000)
    assert seen["temperature"] == 0.0


def test_repeatability_is_the_root_mean_within_file_variance() -> None:
    runs = {
        "a": [Run(3.0, "B1"), Run(3.2, "B1"), Run(3.4, "B1")],  # variance 0.04
        "b": [Run(4.0, "B2"), Run(4.0, "B2"), Run(4.0, "B2")],  # variance 0
    }
    out = summarise(runs)
    assert out["sigma_r"] == pytest.approx((0.04 / 2) ** 0.5)
    assert out["files"] == 2 and out["runs"] == 6
    assert out["largest_range"] == pytest.approx(0.4)
    assert out["band_change_rate"] == 0.0


def test_band_changes_are_counted_over_every_pair_of_runs_of_a_file() -> None:
    runs = {"a": [Run(3.7, "B1"), Run(3.8, "B2"), Run(3.7, "B1"), Run(3.8, "B2")]}
    out = summarise(runs)
    # Six pairs, four of them across the boundary.
    assert out["band_change_rate"] == pytest.approx(4 / 6)


def test_unscored_runs_and_repetition_loops_are_reported_not_hidden() -> None:
    runs = {
        "a": [Run(3.0, "B1"), Run(None, None), Run(3.1, "B1", hallucination=True)],
        "b": [Run(None, None), Run(2.0, "A2")],
    }
    out = summarise(runs)
    assert out["unscored_runs"] == 2
    assert out["hallucination_runs"] == 1
    # "b" has a single scored run: it says nothing about repeatability.
    assert out["files_with_two_scores"] == 1
    assert out["sigma_r"] == pytest.approx(((3.0 - 3.05) ** 2 * 2 / 1) ** 0.5)


def test_no_scored_pairs_gives_no_number_rather_than_zero() -> None:
    out = summarise({"a": [Run(None, None), Run(None, None)]})
    assert out["sigma_r"] is None and out["band_change_rate"] is None


def test_the_bench_reads_its_configurations_and_reports_both_columns() -> None:
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[1] / "tools" / "repeatability_bench.py"
    spec = importlib.util.spec_from_file_location("repeatability_bench", path)
    bench = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bench)

    assert bench.temperatures("fallback, 0") == [None, 0.0]
    summary = summarise({"a": [Run(3.0, "B1"), Run(3.2, "B1", hallucination=True)]})
    text = bench.markdown({"fallback": summary, "temperature=0.0": summary}, runs=2)
    assert "σ_r" in text and "bộ dò lặp" in text
    # Named for what it is: repeatability, never an SEM.
    assert "Không gọi σ_r là SEM" in text
