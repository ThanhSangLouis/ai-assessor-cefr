from __future__ import annotations

import hashlib
import io
import json
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from aicefr.asr.service import EngineResult, RawWord
from aicefr.audio.config import QCConfig
from aicefr.contracts import CURRENT_CONSENT_VERSION, ActorRole
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.portal.contracts import TaskRecord
from aicefr.portal.tasks import TaskRepository
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.blob import BlobStore
from aicefr.trust.service import RuntimeTrustEvaluator


def test_demo_config_seeds_two_w6_speaking_prompts():
    tasks = {item["task_id"]: item for item in _demo_config()["tasks"]}

    assert set(tasks) == {"demo-speaking", "demo-speaking-opinion"}
    for task in tasks.values():
        assert task["task_version"] == "1"
        assert task["min_seconds"] == 40
        assert task["max_seconds"] == 60
        assert "30 giây chuẩn bị" in task["prompt_text"]
        assert "nói bằng tiếng Anh" in task["prompt_text"]


def test_demo_seed_repairs_unused_legacy_speaking_placeholder(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    runtime = create_runtime(tmp_path / "data", config=config)
    try:
        item = config["tasks"][0]
        task = TaskRecord(**{"title": str(item["task_id"]), **item})
        with runtime.store.transaction() as connection:
            connection.execute(
                "UPDATE speaking_tasks SET title='demo-speaking',prompt_text='' "
                "WHERE task_id='demo-speaking' AND task_version='1'"
            )

        repository = TaskRepository(runtime.store)
        repository.seed_demo_task(task)

        upgraded = repository.get("demo-speaking", "1")
        assert upgraded is not None
        assert upgraded.title == task.title
        assert upgraded.prompt_text == task.prompt_text
        assert repository.get("demo-speaking", "2") is None
    finally:
        runtime.close()


def test_demo_seed_versions_used_legacy_speaking_placeholder(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    runtime = create_runtime(tmp_path / "data", config=config)
    try:
        item = config["tasks"][0]
        task = TaskRecord(**{"title": str(item["task_id"]), **item})
        actor = runtime.auth.bootstrap_fixture_account(
            "fixture-demo-seed-student", ActorRole.STUDENT, "fixture-password"
        )
        runtime.consents.activate(
            actor, CURRENT_CONSENT_VERSION, audio_storage_allowed=True
        )
        runtime.responses.submit(
            actor,
            task_id="demo-speaking",
            task_version="1",
            consent_version=CURRENT_CONSENT_VERSION,
            audio_bytes=b"synthetic task-version fixture",
        )
        with runtime.store.transaction() as connection:
            connection.execute(
                "UPDATE speaking_tasks SET title='demo-speaking',prompt_text='' "
                "WHERE task_id='demo-speaking' AND task_version='1'"
            )

        repository = TaskRepository(runtime.store)
        repository.seed_demo_task(task)

        legacy = repository.get("demo-speaking", "1")
        current = repository.get("demo-speaking", "2")
        assert legacy is not None and legacy.active is False and legacy.prompt_text == ""
        assert current is not None and current.active is True
        assert current.prompt_text == task.prompt_text
    finally:
        runtime.close()


def _get(runtime, path, *, token=None):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "HTTP_HOST": "127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(),
        "CONTENT_LENGTH": "0",
        "HTTP_ORIGIN": "http://127.0.0.1:8000",
    }
    if token is not None:
        environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    result = {}
    body = b"".join(
        runtime.app(environ, lambda status, headers: result.update(status=status, headers=headers))
    )
    result["code"] = int(result["status"].split()[0])
    result["body"] = body
    if result["headers"][0][1].startswith("application/json"):
        result["json"] = json.loads(body)
    return result


def test_runtime_injects_repository_providers(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    marker = object()
    received = []

    def build(store):
        received.append(store)
        return marker

    runtime = create_runtime(tmp_path / "data", config=config, repository_factory=build)
    try:
        assert runtime.providers is marker
        assert received == [runtime.store]
    finally:
        runtime.close()


def test_runtime_seeds_learning_catalogue_and_unknown_mission_is_not_found(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    runtime = create_runtime(tmp_path / "data", config=config)
    try:
        student = runtime.auth.bootstrap_fixture_account(
            "fixture-learning-student", ActorRole.STUDENT, "fixture-password"
        )
        runtime.consents.activate(
            student,
            str(config.get("consent_version", "consent-v2")),
            audio_storage_allowed=True,
        )
        token = runtime.auth.login(student.actor_id, "fixture-password")

        catalogue = _get(runtime, "/api/v1/learn/path", token=token)
        missing = _get(runtime, "/api/v1/practice/missions/not-a-mission", token=token)

        assert catalogue["code"] == 200
        assert catalogue["json"]["paths"]
        assert len(catalogue["json"]["paths"][0]["units"]) == 18
        assert missing["code"] == 404
        assert missing["json"]["error"] == "RESOURCE_UNAVAILABLE"
    finally:
        runtime.close()


def test_readiness_aliases_are_sanitized_and_static_assets_are_served(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    config.pop("asr_model_dir", None)
    runtime = create_runtime(tmp_path / "data", config=config)
    try:
        assert _get(runtime, "/live")["json"] == {"alive": True}
        assert _get(runtime, "/health")["json"] == {"alive": True}
        assert _get(runtime, "/healthz")["json"] == {"alive": True}
        ready = _get(runtime, "/ready")
        assert ready["code"] == 503
        assert ready["json"]["ready"] is False
        assert set(ready["json"]) == {"ready", "checks"}
        assert all(type(value) is bool for value in ready["json"]["checks"].values())
        assert _get(runtime, "/readyz")["code"] == 503
        rendered = str(ready["json"])
        assert str(Path(tmp_path)) not in rendered
        assert "fixture" not in rendered
        for path in ("/recorder.js", "/report.js"):
            response = _get(runtime, path)
            assert response["code"] == 200
            assert response["body"]
    finally:
        runtime.close()


def test_readiness_accepts_explicit_test_engines_but_rejects_failed_worker(
    tmp_path, make_symlink_or_skip
):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-model.json")
    blob_store = BlobStore(tmp_path / "data", max_bytes=config["qc"]["max_input_bytes"])
    scorer = SimpleNamespace(
        artifact=SimpleNamespace(
            sha256="a" * 64,
            feature_order=("x",),
            band_thresholds={"A2_B1": 2.75, "B1_B2": 3.75},
        )
    )
    # Synthetic calibration is test-only and provides a real verified loader path.
    calibration = tmp_path / "synthetic-calibration.json"
    payload = {
        "version": "cvplus-v1",
        "calibration_id": "fixture-local-readiness",
        "model_sha256": "a" * 64,
        "feature_order": ["x"],
        "band_thresholds": {"A2_B1": 2.75, "B1_B2": 3.75},
        "folds": [
            {"fold_index": i, "mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0}
            for i in range(2)
        ],
        "n_residuals": 10,
        "residuals": [
            {
                "sample_id": f"{i:064x}",
                "speaker_group": f"{i + 100:064x}",
                "fold_index": i % 2,
                "residual": 0.1,
            }
            for i in range(10)
        ],
        "provenance": {
            "manifest_sha256": "b" * 64,
            "model_sha256": "a" * 64,
            "config_sha256": "c" * 64,
            "seed": 17,
            "split_role": "calibration",
            "training_recipe_version": "fixture-readiness-v1",
            "alpha_default": 0.1,
            "speaker_group_count": 10,
        },
    }
    calibration.write_text(json.dumps(payload), encoding="utf-8")
    trust = RuntimeTrustEvaluator(
        scorer=scorer,
        config={
            "calibration_artifact": str(calibration),
            "expected_sha256": hashlib.sha256(calibration.read_bytes()).hexdigest(),
            "alpha": 0.1,
        },
    )
    pipeline = SimpleNamespace(
        _qc_config=QCConfig(**config["qc"]),
        _scorer=scorer,
        _trust_evaluator=trust,
        _asr=SimpleNamespace(_engine=None),
        _extractor=SimpleNamespace(_vad=object()),
        _responses=SimpleNamespace(blobs=blob_store),
        enqueue=lambda _response: None,
    )
    runtime = create_runtime(
        tmp_path / "data", config=config, pipeline=pipeline, asr_engine=object()
    )
    try:
        assert runtime.control.readiness()["ready"] is True
        with runtime.store.transaction() as connection:
            connection.execute(
                "INSERT INTO runtime_settings VALUES (?,?,?,?,?,?)",
                ("readiness-tx", "{}", 0, "test", "fixture", "2026-10-15T00:00:00+00:00"),
            )
            assert runtime.control.readiness()["checks"]["database"] is True
            assert connection.in_transaction
            assert connection.execute(
                "SELECT 1 FROM runtime_settings WHERE key='readiness-tx'"
            ).fetchone()

        checksum = runtime.store.connection.execute(
            "SELECT checksum FROM schema_migrations WHERE version=5"
        ).fetchone()[0]
        with runtime.store.transaction() as connection:
            connection.execute(
                "UPDATE schema_migrations SET checksum=? WHERE version=5", ("0" * 64,)
            )
        tampered = runtime.control.readiness()
        assert tampered["checks"]["schema"] is False
        assert str(tmp_path) not in json.dumps(tampered)
        with runtime.store.transaction() as connection:
            connection.execute(
                "UPDATE schema_migrations SET checksum=? WHERE version=5", (checksum,)
            )

        runtime.store.connection.execute("PRAGMA query_only=ON")
        try:
            read_only = runtime.control.readiness()
        finally:
            runtime.store.connection.execute("PRAGMA query_only=OFF")
        assert read_only["checks"]["database"] is False
        assert str(tmp_path) not in json.dumps(read_only)

        runtime.control.worker = SimpleNamespace(health=lambda: False)
        readiness = runtime.control.readiness()
        assert readiness["ready"] is False
        assert readiness["checks"]["worker"] is False
        root = blob_store.root
        moved = tmp_path / "blob-store-original"
        root.rename(moved)
        try:
            assert runtime.control.readiness()["checks"]["blobs"] is False
            make_symlink_or_skip(
                root, tmp_path / "external-blobs", target_is_directory=True
            )
            assert runtime.control.readiness()["checks"]["blobs"] is False
        finally:
            root.unlink(missing_ok=True)
            moved.rename(root)
    finally:
        runtime.close()


def test_practice_runtime_runs_without_assessment_scorer_or_calibration(tmp_path):
    class Engine:
        transcribe_calls = 0

        def detect_language(self, audio):
            return "en", 0.99

        def transcribe(self, audio):
            type(self).transcribe_calls += 1
            return EngineResult(
                text="and",
                words=(RawWord("and", 0.05, 0.25, 0.99),),
                engine="fixture-asr",
                engine_version="1",
                weight_name="fixture",
            )

    class Vad:
        def segments(self, samples, sample_rate_hz):
            return ((0.4, 0.8),)

    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-score-model.json")
    sample_rate = 16_000
    samples = (np.sin(np.arange(3 * sample_rate) * 0.08) * 4000).astype("<i2")
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())
    runtime = create_runtime(
        tmp_path / "learning-only",
        config=config,
        asr_engine=Engine(),
        vad_engine=Vad(),
        scorer=RidgeScorer.load(tmp_path / "missing-score-model.json"),
    )
    try:
        runtime.auth.bootstrap_fixture_account(
            "fixture-student", ActorRole.STUDENT, "fixture-password"
        )
        seeded_paths = runtime.lessons.paths()
        assert seeded_paths and len(seeded_paths[0].units) == 18
        mission = runtime.practice.catalogue()[0]
        record = runtime.practice.submit(
            "fixture-student",
            mission.mission_id,
            stream.getvalue(),
            "wav",
            "practice-no-scorer-1",
            prompt_version=mission.prompt_version,
            content_type="audio/wav",
        )
        assert record.state.value == "COMPLETED"
        assert record.result is not None
        assert runtime.control.pipeline._scorer.artifact is None
        replay = runtime.practice.submit(
            "fixture-student",
            mission.mission_id,
            stream.getvalue(),
            "wav",
            "practice-no-scorer-1",
            prompt_version=mission.prompt_version,
            content_type="audio/wav",
        )
        assert replay.attempt_id == record.attempt_id
        assert Engine.transcribe_calls == 1
        personal = runtime.portal.export_own(
            runtime.auth.login("fixture-student", "fixture-password")
        )
        exported_attempt = personal["learning"]["practice_attempts"][0]
        assert exported_attempt["mission_snapshot"]["mission_id"] == mission.mission_id
        assert exported_attempt["result"]["status"] == record.result.status.value
        assert "purpose" in exported_attempt and "attempt_state" in exported_attempt
        assert "heard_text" not in json.dumps(exported_attempt)
        exported_json = json.dumps(personal).lower()
        assert "token_digest" not in exported_json
        assert "password_hash" not in exported_json
        from aicefr.storage.learning import LearningConflict

        with pytest.raises(LearningConflict):
            runtime.practice.submit(
                "fixture-student",
                mission.mission_id,
                stream.getvalue() + b"changed",
                "wav",
                "practice-no-scorer-1",
                prompt_version=mission.prompt_version,
                content_type="audio/wav",
            )
    finally:
        runtime.close()


def test_readiness_rejects_corrupt_local_asr_artifact_without_disclosing_path(tmp_path):
    model_dir = tmp_path / "corrupt-asr"
    model_dir.mkdir()
    for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        (model_dir / name).write_bytes(b"fixture-corrupt-model")
    config = _demo_config()
    config["asr_model_dir"] = str(model_dir)
    config["model_artifact"] = str(tmp_path / "missing-scorer.json")
    runtime = create_runtime(tmp_path / "data", config=config)
    try:
        readiness = runtime.control.readiness()
        assert readiness["checks"]["asr_model"] is False
        assert readiness["ready"] is False
        assert str(model_dir) not in json.dumps(readiness)
    finally:
        runtime.close()
