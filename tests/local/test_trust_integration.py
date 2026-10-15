from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from aicefr.contracts import (
    AsrStatus,
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    FeatureSet,
    FeatureValue,
    Interaction,
    Provenance,
    ReasonCode,
    Transcript,
    Word,
)
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.scoring.conformal import CalibrationArtifactError
from aicefr.trust.contracts import (
    GuardDecision,
    LanguageDecision,
    TrustDisposition,
)
from aicefr.trust.service import RuntimeTrustEvaluator


def _synthetic_calibration(path: Path, scorer) -> str:
    """Write a deterministic test-only artifact bound to its synthetic scorer."""
    artifact = scorer.artifact
    payload = {
        "version": "cvplus-v1",
        "calibration_id": "fixture-local-trust",
        "model_sha256": artifact.sha256,
        "feature_order": list(artifact.feature_order),
        "band_thresholds": artifact.band_thresholds,
        "folds": [
            {
                "fold_index": fold,
                "mean": [0.0] * len(artifact.feature_order),
                "scale": [1.0] * len(artifact.feature_order),
                "coef": [0.0] * len(artifact.feature_order),
                "intercept": 3.2,
            }
            for fold in range(2)
        ],
        "n_residuals": 10,
        "residuals": [
            {
                "sample_id": f"{index:064x}",
                "speaker_group": f"{index + 100:064x}",
                "fold_index": index % 2,
                "residual": 0.1,
            }
            for index in range(10)
        ],
        "provenance": {
            "manifest_sha256": "d" * 64,
            "model_sha256": artifact.sha256,
            "config_sha256": "e" * 64,
            "seed": 17,
            "split_role": "calibration",
            "training_recipe_version": "fixture-training-v1",
            "alpha_default": 0.1,
            "speaker_group_count": 10,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assessment() -> Assessment:
    return Assessment(
        response_id="a" * 32,
        status=AssessmentStatus.ESTIMATED,
        overall_score=3.2,
        overall_band=Band.B1,
        criteria=tuple(CriterionCoverage(criterion=item, coverage=0.5) for item in Criterion),
        interaction=Interaction(),
        provenance=Provenance(
            model_version="fixture-model",
            model_sha256="b" * 64,
            feature_version="fixture-features",
            band_map_version="fixture-band-map",
            calibration_version=None,
            trained_with={},
            unit_of_inference="fixture response",
            scored_at="2026-10-15T00:00:00+00:00",
        ),
    )


def _scorer():
    return SimpleNamespace(
        artifact=SimpleNamespace(
            sha256="c" * 64,
            feature_order=("words_per_minute",),
            band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
        )
    )


def _trust_transcript(*, metadata: bool = False) -> Transcript:
    words = tuple(
        Word(text="weather", start_s=index / 20, end_s=(index + 1) / 20) for index in range(30)
    )
    return Transcript(
        response_id="a" * 32,
        status=AsrStatus.OK,
        text=" ".join(word.text for word in words),
        words=words,
        engine="fixture-engine",
        engine_version="1",
        decode_config_version="fixture-asr-v1",
        audio_sha256="d" * 64,
        **(
            {
                "language": "en",
                "language_probability": 0.97,
                "language_method": "fixture-lid",
                "language_version": "fixture-v1",
            }
            if metadata
            else {}
        ),
    )


def _features() -> FeatureSet:
    return FeatureSet(
        response_id="a" * 32,
        values=(FeatureValue(name="words_per_minute", value=120.0, unit="words/min"),),
        feature_version="fixture-features",
        vad_name="fixture-vad",
        vad_version="1",
        vad_threshold=0.5,
        vad_min_silence_ms=150,
        asr_model="fixture-asr",
        transcript_ref="a" * 32,
        audio_sha256="d" * 64,
    )


def test_runtime_trust_uses_transcript_lid_metadata_and_valid_calibration(tmp_path):
    scorer = SimpleNamespace(
        artifact=SimpleNamespace(
            sha256="c" * 64,
            feature_order=("words_per_minute",),
            band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
        )
    )
    path = tmp_path / "synthetic.json"
    digest = _synthetic_calibration(path, scorer)
    evaluator = RuntimeTrustEvaluator(
        scorer=scorer,
        config={"calibration_artifact": str(path), "expected_sha256": digest},
        tasks={
            ("fixture-task", "v1"): {
                "prompt_text": "Describe your school experience",
                "topic_keywords": ["school"],
            }
        },
    )
    assert evaluator.ready
    same_model = evaluator.rebind(
        SimpleNamespace(
            artifact=SimpleNamespace(
                sha256="c" * 64,
                feature_order=("words_per_minute",),
                band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
            )
        )
    )
    assert same_model.ready
    changed_model = evaluator.rebind(
        SimpleNamespace(
            artifact=SimpleNamespace(
                sha256="f" * 64,
                feature_order=("words_per_minute",),
                band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
            )
        )
    )
    assert changed_model.ready is False
    assert changed_model._calibration_reason is ReasonCode.CALIBRATION_INVALID
    transcript = Transcript(
        response_id="a" * 32,
        status=AsrStatus.OK,
        text="I enjoy studying at my local school with friends every day.",
        words=tuple(
            Word(text=word, start_s=index / 20, end_s=(index + 1) / 20)
            for index, word in enumerate(
                "I enjoy studying at my local school with friends every day".split()
            )
        ),
        engine="fixture-engine",
        engine_version="1",
        decode_config_version="fixture-asr-v1",
        audio_sha256="d" * 64,
        language="en",
        language_probability=0.96,
        language_method="fixture-independent-lid",
        language_version="fixture-lid-v1",
    )
    features = FeatureSet(
        response_id="a" * 32,
        values=(FeatureValue(name="words_per_minute", value=120.0, unit="words/min"),),
        feature_version="fixture-features",
        vad_name="fixture-vad",
        vad_version="1",
        vad_threshold=0.5,
        vad_min_silence_ms=150,
        asr_model="fixture-asr",
        transcript_ref="a" * 32,
        audio_sha256="d" * 64,
    )

    trust = evaluator.assess(
        audio=SimpleNamespace(),
        transcript=transcript,
        features=features,
        assessment=_assessment(),
        task_id="fixture-task",
        task_version="v1",
        asr=SimpleNamespace(_engine=None),
    )

    assert trust.language.decision is LanguageDecision.ENGLISH
    assert trust.language.method == "fixture-independent-lid"
    assert trust.prediction_set.bands == (Band.B1,)
    assert trust.disposition is TrustDisposition.CONTINUE
    assert len(trust.criterion_indicators) == 5
    assert all(item.label == "chỉ báo" for item in trust.criterion_indicators)


def test_missing_and_wrong_hash_calibration_remain_closed_with_observed_reasons(tmp_path):
    scorer = SimpleNamespace(
        artifact=SimpleNamespace(
            sha256="c" * 64,
            feature_order=("words_per_minute",),
            band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
        )
    )
    missing = RuntimeTrustEvaluator(scorer=scorer, config={})
    assert not missing.ready
    assert missing._calibration_reason is ReasonCode.CALIBRATION_MISSING

    path = tmp_path / "synthetic.json"
    _synthetic_calibration(path, scorer)
    mismatch = RuntimeTrustEvaluator(
        scorer=scorer,
        config={"calibration_artifact": str(path), "expected_sha256": "0" * 64},
    )
    assert not mismatch.ready
    assert mismatch._calibration_reason is ReasonCode.CALIBRATION_HASH_MISMATCH


def test_runtime_trust_rejects_invalid_alpha_model_and_artifact_path(tmp_path):
    scorer = _scorer()
    path = tmp_path / "synthetic.json"
    digest = _synthetic_calibration(path, scorer)
    for alpha in (True, 0.5, float("nan"), "not-a-number"):
        evaluator = RuntimeTrustEvaluator(
            scorer=scorer,
            config={
                "alpha": alpha,
                "calibration_artifact": str(path),
                "expected_sha256": digest,
            },
        )
        assert evaluator.ready is False
        assert evaluator._calibration_reason is ReasonCode.CALIBRATION_INVALID

    no_model = RuntimeTrustEvaluator(
        scorer=SimpleNamespace(artifact=None),
        config={"calibration_artifact": str(path), "expected_sha256": digest},
    )
    invalid_path = RuntimeTrustEvaluator(
        scorer=scorer,
        config={"calibration_artifact": object(), "expected_sha256": digest},
    )
    assert no_model._calibration_reason is ReasonCode.CALIBRATION_INVALID
    assert invalid_path._calibration_reason is ReasonCode.CALIBRATION_INVALID


def test_runtime_trust_uses_independent_detector_and_exact_task_repository_version(tmp_path):
    scorer = _scorer()
    path = tmp_path / "synthetic.json"
    digest = _synthetic_calibration(path, scorer)
    task = SimpleNamespace(prompt_text="Describe school", topic_keywords=("school",))

    class Tasks:
        calls = []

        def get(self, task_id, task_version):
            self.calls.append((task_id, task_version))
            return task if task_version == "v2" else None

    class Detector:
        def detect_language(self, audio):
            assert audio == "audio"
            return "en", 0.97

    tasks = Tasks()
    evaluator = RuntimeTrustEvaluator(
        scorer=scorer,
        config={"calibration_artifact": str(path), "expected_sha256": digest},
        tasks=tasks,
    )
    trust = evaluator.assess(
        audio="audio",
        transcript=_trust_transcript(),
        features=_features(),
        assessment=_assessment(),
        task_id="fixture-task",
        task_version="v2",
        asr=SimpleNamespace(_engine=Detector()),
    )
    assert tasks.calls == [("fixture-task", "v2")]
    assert trust.language.decision is LanguageDecision.ENGLISH
    assert trust.relevance[0].decision is GuardDecision.SUSPECTED
    assert ReasonCode.OFF_TOPIC_SUSPECTED in trust.reasons

    class BrokenDetector:
        def detect_language(self, audio):
            raise RuntimeError("detector unavailable")

    uncertain = evaluator.assess(
        audio="audio",
        transcript=_trust_transcript(),
        features=_features(),
        assessment=_assessment(),
        task_id="fixture-task",
        task_version="v1",
        asr=SimpleNamespace(_engine=BrokenDetector()),
    )
    assert uncertain.language.decision is LanguageDecision.UNCERTAIN
    assert ReasonCode.LANGUAGE_UNCERTAIN in uncertain.reasons


def test_loader_failure_reason_fallback_is_stable(tmp_path):
    path = tmp_path / "present.json"
    path.write_text("{}", encoding="utf-8")
    missing = RuntimeTrustEvaluator._loader_reason(SimpleNamespace(reason="missing"), path)
    mismatch = RuntimeTrustEvaluator._loader_reason(SimpleNamespace(reason="hash_mismatch"), path)
    invalid = RuntimeTrustEvaluator._loader_reason(SimpleNamespace(reason="schema"), path)
    unreadable = RuntimeTrustEvaluator._loader_reason(
        SimpleNamespace(reason="schema"), tmp_path / "absent.json"
    )
    assert missing is ReasonCode.CALIBRATION_MISSING
    assert mismatch is ReasonCode.CALIBRATION_HASH_MISMATCH
    assert invalid is ReasonCode.CALIBRATION_INVALID
    assert unreadable is ReasonCode.CALIBRATION_MISSING


def test_runtime_trust_prediction_failures_are_local_and_window_sets_union(tmp_path, monkeypatch):
    scorer = _scorer()
    path = tmp_path / "synthetic.json"
    digest = _synthetic_calibration(path, scorer)
    evaluator = RuntimeTrustEvaluator(
        scorer=scorer,
        config={"calibration_artifact": str(path), "expected_sha256": digest},
    )
    assert evaluator.ready
    windows = evaluator.predict_windows((_features(), _features()))
    assert windows is not None and len(windows) == 2
    assert evaluator.predict_windows(()) == ()

    b2 = windows[0].model_copy(update={"bands": (Band.B2,), "low": 3.8, "high": 4.1})
    union = evaluator._aggregate_sets((windows[0], b2))
    assert union.bands == (Band.B1, Band.B2)
    assert (union.low, union.high) == (windows[0].low, 4.1)
    assert (
        evaluator._aggregate_sets((windows[0], b2.model_copy(update={"checksum": "f" * 64})))
        is None
    )
    assert evaluator._aggregate_sets(()) is None

    transcript = _trust_transcript(metadata=True)
    aggregated = evaluator.assess(
        audio=None,
        transcript=transcript,
        features=_features(),
        assessment=_assessment(),
        task_id="missing-task",
        task_version="v1",
        asr=SimpleNamespace(_engine=None),
        conformal_sets=windows,
    )
    assert aggregated.prediction_set.bands == windows[0].bands
    invalid_aggregate = evaluator.assess(
        audio=None,
        transcript=transcript,
        features=_features(),
        assessment=_assessment(),
        task_id="missing-task",
        task_version="v1",
        asr=SimpleNamespace(_engine=None),
        conformal_sets=(),
    )
    assert invalid_aggregate.prediction_set is None
    assert invalid_aggregate.disposition is TrustDisposition.NOT_EVALUATED
    assert ReasonCode.CALIBRATION_INVALID in invalid_aggregate.reasons

    monkeypatch.setattr(
        "aicefr.trust.service.predict_conformal",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            CalibrationArtifactError(ReasonCode.CALIBRATION_INVALID)
        ),
    )
    failed = evaluator.assess(
        audio=None,
        transcript=transcript,
        features=_features(),
        assessment=_assessment(),
        task_id="missing-task",
        task_version="v1",
        asr=SimpleNamespace(_engine=None),
    )
    assert failed.disposition is TrustDisposition.NOT_EVALUATED
    assert ReasonCode.CALIBRATION_INVALID in failed.reasons
    assert evaluator.predict_windows((_features(),)) == ()
    assert evaluator._calibration_reason is None


def test_runtime_trust_missing_calibration_and_lid_metadata_fail_closed():
    missing = RuntimeTrustEvaluator(scorer=_scorer(), config={})
    assert missing.predict_windows((_features(),)) is None
    assert missing.predict_windows(()) is None
    trust = missing.assess(
        audio=None,
        transcript=_trust_transcript(),
        features=_features(),
        assessment=_assessment(),
        task_id="unknown-task",
        task_version="legacy",
        asr=SimpleNamespace(_engine=None),
    )
    assert trust.language.decision is LanguageDecision.UNCERTAIN
    assert trust.disposition is TrustDisposition.NOT_EVALUATED
    assert ReasonCode.LANGUAGE_UNCERTAIN in trust.reasons
    assert ReasonCode.CALIBRATION_MISSING in trust.reasons


def test_production_runtime_always_wires_missing_calibration_fail_closed(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    runtime = create_runtime(tmp_path / "runtime-data", config=config)
    try:
        pipeline = runtime.app._student_api._service._pipeline
        assert pipeline._trust_evaluator is not None
        assert pipeline._trust_evaluator.ready is False
        assert pipeline._trust_evaluator._calibration_reason is ReasonCode.CALIBRATION_MISSING
        assert runtime.control.readiness()["checks"]["trust_calibration"] is False
    finally:
        runtime.close()
