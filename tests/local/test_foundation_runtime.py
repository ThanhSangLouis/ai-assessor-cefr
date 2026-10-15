from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from aicefr.audio.config import QCConfig
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.storage.blob import BlobStore
from aicefr.trust.service import RuntimeTrustEvaluator


def _get(runtime, path):
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


def test_readiness_accepts_explicit_test_engines_but_rejects_failed_worker(tmp_path):
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
            root.symlink_to(tmp_path / "external-blobs", target_is_directory=True)
            assert runtime.control.readiness()["checks"]["blobs"] is False
        finally:
            root.unlink(missing_ok=True)
            moved.rename(root)
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
