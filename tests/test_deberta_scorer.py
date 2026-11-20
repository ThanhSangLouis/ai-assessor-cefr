"""The fusion scorer (Ridge v4 + DeBERTa LoRA) and how the app picks it.

Runs on synthetic artifacts only: the ridge half is the fake `ridge_resp_v2`
fixture renamed, the text model is a stand-in, so no torch, no weights and no
corpus statistics are needed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from conftest import feature_set

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import ProcessingRequest, ReasonCode
from aicefr.pipeline import ResponseProcessor
from aicefr.ports import Scorer
from aicefr.scoring.factory import build_scorer
from aicefr.scoring.fusion import DebertaScorer
from aicefr.scoring.scorer import IncompatibleModelError, RidgeScorer, load_model
from aicefr.scoring.text_model import DebertaTextModel, TextModelError

FIXTURES = Path(__file__).parent / "fixtures" / "models"
FUSION = {"intercept": -0.3, "w_ridge": 0.56, "w_text": 0.5, "inputs": "test"}
INTERVAL = {"method": "oof-residual-quantile", "alpha": 0.1, "q_fusion": 0.4, "q_ridge": 0.45}
TEXT_SPEC = {
    "version": "deberta_lora_test",
    "base_dir": "base",
    "base_sha256": {"config.json": "0" * 64},
    "adapter_dir": "adapter",
    "adapter_sha256": {"adapter_model.safetensors": "0" * 64},
    "lora_r": 16,
    "lora_alpha": 32,
    "max_length": 256,
    "target_norm": [4.0, 0.74],
}


class FakeText:
    """Stands in for DebertaTextModel and records what it was asked."""

    def __init__(self, value: float = 4.2, fail: bool = False) -> None:
        self.value, self.fail, self.calls = value, fail, []

    def predict(self, text: str) -> float:
        self.calls.append(text)
        if self.fail:
            raise RuntimeError("simulated text model failure")
        return self.value

    def missing_files(self) -> list[str]:
        return []


def _write(folder: Path, name: str, data: dict) -> str:
    raw = json.dumps(data, indent=2).encode()
    (folder / f"{name}.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def models(tmp_path, monkeypatch) -> Path:
    """A model folder with ridge_resp_v4 and fusion_resp_v4 built from the fake v2 artifact."""
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, tmp_path / f.name)
    ridge = {
        **json.loads((FIXTURES / "ridge_resp_v2.json").read_text()),
        "model_version": "ridge_resp_v4",
    }
    reference = json.loads((FIXTURES / "conformal_resp_v2.json").read_text())["indicator_reference"]
    fusion = {
        **ridge,
        "model_version": "fusion_resp_v4",
        "calibration_version": "oofq90_test",
        "ridge_model": "ridge_resp_v4",
        "fusion": FUSION,
        "interval": INTERVAL,
        "indicator_reference": reference,
        "text_model": TEXT_SPEC,
    }
    pins = [
        f"{n}={_write(tmp_path, n, d)}"
        for n, d in (("ridge_resp_v4", ridge), ("fusion_resp_v4", fusion))
    ]
    sums = (FIXTURES / "SHA256SUMS").read_text().splitlines()
    pins += [
        f"{line.split()[1].removesuffix('.json')}={line.split()[0]}"
        for line in sums
        if line.strip()
    ]
    monkeypatch.setenv("AICEFR_MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("AICEFR_MODEL_PINS", ",".join(pins))
    return tmp_path


@pytest.fixture
def typical(models):
    m = load_model("ridge_resp_v4")
    return feature_set(
        {
            n: (lo + hi) / 2
            for n, lo, hi in zip(m["feature_order"], m["feature_lo"], m["feature_hi"], strict=True)
        }
    )


def test_fused_score_is_the_stacked_combination(typical):
    text = FakeText(4.2)
    a = DebertaScorer("fusion_resp_v4", text_model=text).score(typical, text="I like my city")
    ridge = RidgeScorer("ridge_resp_v4").score(typical).overall_0_6
    expected = FUSION["intercept"] + FUSION["w_ridge"] * ridge + FUSION["w_text"] * 4.2
    assert a.overall_0_6 == pytest.approx(expected, abs=0.011)
    assert a.model_version == "fusion_resp_v4"
    assert text.calls == ["I like my city"]
    assert a.interval.method == "oof-residual-quantile"
    assert a.interval.coverage == pytest.approx(0.9)
    assert a.interval.high - a.interval.low == pytest.approx(2 * INTERVAL["q_fusion"], abs=0.011)
    assert a.indicators, "percentile indicators come from the artifact's reference"


@pytest.mark.parametrize("text", [None, "", "   "])
def test_no_transcript_means_ridge_alone_and_says_so(typical, text):
    a = DebertaScorer("fusion_resp_v4", text_model=FakeText()).score(typical, text=text)
    assert a.overall_0_6 == RidgeScorer("ridge_resp_v4").score(typical).overall_0_6
    # The stored version names an artifact that really produced this number.
    assert a.model_version == "ridge_resp_v4"
    assert a.calibration_version.endswith("-ridge")
    assert a.interval.high - a.interval.low == pytest.approx(2 * INTERVAL["q_ridge"], abs=0.011)


def test_text_model_failure_falls_back_instead_of_losing_the_response(typical):
    a = DebertaScorer("fusion_resp_v4", text_model=FakeText(fail=True)).score(
        typical, text="hello there"
    )
    assert a.overall_0_6 is not None
    assert a.model_version == "ridge_resp_v4"


def test_out_of_distribution_input_is_not_scored_and_text_not_read(typical):
    values = {f.name: f.value for f in typical.items}
    values["total_dur"] = 10_000.0
    text = FakeText()
    a = DebertaScorer("fusion_resp_v4", text_model=text).score(feature_set(values), text="words")
    assert a.overall_0_6 is None and a.overall_band is None
    assert ReasonCode.OUT_OF_DISTRIBUTION in a.reasons
    assert text.calls == []


def _replace(models: Path, monkeypatch, name: str, data: dict) -> None:
    digest = _write(models, name, data)
    pins = [p for p in os.environ["AICEFR_MODEL_PINS"].split(",") if not p.startswith(f"{name}=")]
    monkeypatch.setenv("AICEFR_MODEL_PINS", ",".join([*pins, f"{name}={digest}"]))


def test_wide_interval_sends_the_response_to_a_teacher(models, typical, monkeypatch):
    fusion = json.loads((models / "fusion_resp_v4.json").read_text())
    _replace(
        models, monkeypatch, "fusion_resp_v4", {**fusion, "interval": {**INTERVAL, "q_fusion": 1.6}}
    )
    a = DebertaScorer("fusion_resp_v4", text_model=FakeText()).score(typical, text="words")
    assert not a.interval.is_single_band
    assert ReasonCode.SCORE_NEAR_BOUNDARY in a.reasons


def test_refuses_a_fusion_whose_ridge_half_differs_from_the_fallback(models, monkeypatch):
    ridge = json.loads((models / "ridge_resp_v4.json").read_text())
    _replace(models, monkeypatch, "ridge_resp_v4", {**ridge, "intercept": ridge["intercept"] + 0.5})
    with pytest.raises(IncompatibleModelError):
        DebertaScorer("fusion_resp_v4", text_model=FakeText())


def test_contributions_are_points_in_the_fused_score(typical):
    fused = DebertaScorer("fusion_resp_v4", text_model=FakeText()).contributions(typical)
    ridge = RidgeScorer("ridge_resp_v4").contributions(typical)
    assert fused.keys() == ridge.keys()
    for name, value in ridge.items():
        assert fused[name] == pytest.approx(FUSION["w_ridge"] * value)


def test_factory_picks_the_adapter_the_artifact_needs(models):
    fusion = build_scorer("fusion_resp_v4")
    assert isinstance(fusion, DebertaScorer) and isinstance(fusion, Scorer)
    assert isinstance(build_scorer("ridge_resp_v4"), RidgeScorer)
    assert isinstance(build_scorer("ridge_resp_v2"), RidgeScorer)
    # Building it reads versions only: the text weights are not loaded yet.
    assert fusion.text_model._model is None
    assert fusion.missing_files(), "the synthetic folder has no text-model files"


def test_pipeline_hands_the_transcript_to_the_scorer(tone, sr):
    """The synthetic tone is out of range for any model, so record the call instead of a score."""

    class Recording(RidgeScorer):
        texts: list = []

        def score(self, features, text=None):
            self.texts.append(text)
            return super().score(features, text)

    scorer = Recording()
    request = ProcessingRequest(
        response_id="r1", task_id="P3", audio_path="x.wav", prompt_version="v1", config_version="v1"
    )
    report = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad(), scorer=scorer).process(
        request, tone, sr
    )
    assert scorer.texts and all(t for t in scorer.texts)
    assert scorer.texts[-1] == report.asr.text or report.assessment.windows


def test_text_model_refuses_missing_or_tampered_files(tmp_path):
    model = DebertaTextModel(TEXT_SPEC, tmp_path)
    assert len(model.missing_files()) == 2
    with pytest.raises(TextModelError, match="không tìm thấy"):
        model.predict("hello")
    (tmp_path / "base").mkdir()
    (tmp_path / "adapter").mkdir()
    (tmp_path / "base" / "config.json").write_text("{}")
    (tmp_path / "adapter" / "adapter_model.safetensors").write_bytes(b"x")
    assert model.missing_files() == []
    with pytest.raises(TextModelError, match="SHA-256"):
        model.predict("hello")
