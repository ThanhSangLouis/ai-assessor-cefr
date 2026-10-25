from __future__ import annotations

import hashlib
import io
import json
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from aicefr.audio.config import QCConfig
from aicefr.contracts import (
    CURRENT_CONSENT_VERSION,
    ActorRole,
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Interaction,
    Provenance,
    ResponseStatus,
)
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.report.service import ReportInput
from aicefr.scoring.scorer import RidgeScorer
from aicefr.trust.service import RuntimeTrustEvaluator


@pytest.fixture
def portal_runtime(tmp_path):
    config = _demo_config()
    config["tasks"][0]["prompt_text"] = "Talk about learning and education."
    config["tasks"][0]["topic_keywords"] = ("learning", "education")
    # Synthetic test-only scorer/calibration pair for the custom portal pipeline.
    trust_scorer = SimpleNamespace(
        artifact=SimpleNamespace(
            sha256="a" * 64,
            feature_order=("words_per_minute",),
            band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
        )
    )
    calibration = tmp_path / "synthetic-portal-calibration.json"
    thresholds = trust_scorer.artifact.band_thresholds
    payload = {
        "version": "cvplus-v1",
        "calibration_id": "fixture-portal",
        "model_sha256": trust_scorer.artifact.sha256,
        "feature_order": list(trust_scorer.artifact.feature_order),
        "band_thresholds": thresholds,
        "folds": [
            {
                "fold_index": fold,
                "mean": [0.0] * len(trust_scorer.artifact.feature_order),
                "scale": [1.0] * len(trust_scorer.artifact.feature_order),
                "coef": [0.0] * len(trust_scorer.artifact.feature_order),
                "intercept": 3.0,
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
            "manifest_sha256": "b" * 64,
            "model_sha256": trust_scorer.artifact.sha256,
            "config_sha256": "c" * 64,
            "seed": 17,
            "split_role": "calibration",
            "training_recipe_version": "fixture-portal-v1",
            "alpha_default": 0.1,
            "speaker_group_count": 10,
        },
    }
    calibration.write_text(json.dumps(payload), encoding="utf-8")
    trust = RuntimeTrustEvaluator(
        scorer=trust_scorer,
        config={
            "calibration_artifact": str(calibration),
            "expected_sha256": hashlib.sha256(calibration.read_bytes()).hexdigest(),
            "alpha": 0.1,
        },
    )
    pipeline = SimpleNamespace(
        _qc_config=QCConfig(**config["qc"]),
        _scorer=RidgeScorer.load(),
        _trust_evaluator=trust,
        enqueue=lambda response: None,
    )
    runtime = create_runtime(tmp_path / "data", config=config, pipeline=pipeline)
    tokens = {}
    for name, role in [
        ("a", ActorRole.STUDENT),
        ("b", ActorRole.STUDENT),
        ("teacher", ActorRole.TEACHER),
        ("other-teacher", ActorRole.TEACHER),
        ("admin", ActorRole.ADMIN),
    ]:
        actor = runtime.auth.bootstrap_fixture_account("fixture-" + name, role, "fixture-password")
        tokens[name] = runtime.auth.login(actor.actor_id, "fixture-password")
        if role is ActorRole.STUDENT:
            runtime.consents.activate(
                actor,
                CURRENT_CONSENT_VERSION,
                audio_storage_allowed=True,
            )
    yield runtime, tokens
    runtime.close()


def submit_completed(runtime, token, *, score=4.3, band=Band.B2):
    from aicefr.api.student import SubmitRequest

    stream = io.BytesIO()
    sf.write(stream, np.full(16000, 0.2, dtype=np.float32), 16000, format="WAV")
    submitted = runtime.app._student_api.submit(
        token,
        SubmitRequest(
            task_id="demo-speaking",
            task_version="1",
            consent_version=runtime.app._consent_version,
            filename="fixture.wav",
            content_type="audio/wav",
            audio_bytes=stream.getvalue(),
        ),
    )
    record = runtime.store.get_response(submitted.response_id)
    current = runtime.store.claim_queued_response(record)
    runtime.responses.transition_status(
        response_id=record.response_id,
        expected_revision=current.revision,
        status=ResponseStatus.COMPLETED,
        actor_id="fixture-pipeline",
        action="fixture_completed",
    )
    assessment = Assessment(
        response_id=record.response_id,
        status=AssessmentStatus.ESTIMATED,
        overall_score=score,
        overall_band=band,
        criteria=tuple(CriterionCoverage(criterion=c, coverage=0.5) for c in Criterion),
        interaction=Interaction(),
        provenance=Provenance(
            model_version="fixture-model",
            model_sha256="0" * 64,
            feature_version="fixture-v1",
            band_map_version="band-v1",
            calibration_version="not-validated",
            trained_with={},
            unit_of_inference="one response",
            scored_at="2026-10-08T00:00:00+00:00",
        ),
    )
    runtime.app._reports.build_and_store(
        ReportInput(response_id=record.response_id, audio_duration_s=1, assessment=assessment)
    )
    return runtime.store.get_response(record.response_id)


def http(
    runtime, path, token=None, *, method="GET", payload=None, cookie=False, origin=True, query=""
):
    body = json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_HOST": "127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/json",
    }
    if token:
        environ["HTTP_COOKIE" if cookie else "HTTP_AUTHORIZATION"] = (
            "aicefr_session=" if cookie else "Bearer "
        ) + token
    if origin:
        environ["HTTP_ORIGIN"] = "http://127.0.0.1:8000"
    captured = {}
    data = b"".join(
        runtime.app(
            environ, lambda status, headers: captured.update(status=status, headers=dict(headers))
        )
    )
    captured["body"] = data
    captured["code"] = int(captured["status"].split()[0])
    if captured["headers"]["Content-Type"].startswith("application/json"):
        captured["json"] = json.loads(data)
    return captured
