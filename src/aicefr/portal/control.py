"""Versioned QC configuration, pinned model activation and readiness."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aicefr.contracts import ActorRole
from aicefr.portal.contracts import QCChange
from aicefr.portal.service import PortalService
from aicefr.scoring.artifact import ModelArtifactError, default_artifact_path, load_artifact
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.sqlite import ConcurrentResponseUpdate


class RuntimeControl:
    QC_EDITABLE = frozenset(
        {
            "min_duration_s",
            "max_duration_s",
            "silence_threshold",
            "clipping_threshold",
            "review_silence_ratio",
            "reject_silence_ratio",
            "review_clipping_ratio",
            "reject_clipping_ratio",
        }
    )

    def __init__(self, portal: PortalService, pipeline: Any, config: dict[str, Any]) -> None:
        self.portal, self.pipeline, self.config = portal, pipeline, config
        self.worker = None

    def _setting(self, key: str):
        return self.portal.store.connection.execute(
            "SELECT payload,revision,version FROM runtime_settings WHERE key=?", (key,)
        ).fetchone()

    def reload(self) -> None:
        """Workers adopt committed policy only between responses."""
        from aicefr.audio.config import QCConfig

        qc = self._setting("qc_config")
        if qc:
            self.pipeline._qc_config = QCConfig(**json.loads(qc[0]))
        model = self._setting("active_model")
        if model:
            name = json.loads(model[0])["name"]
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name):
                raise ValueError("invalid persisted model name")
            artifact = getattr(self.pipeline._scorer, "artifact", None)
            if artifact is None or artifact.name != name:
                self.pipeline._scorer = RidgeScorer(
                    artifact=load_artifact(self._model_dir() / f"{name}.json")
                )

    def _save(self, token: str, key: str, payload: dict, version: str, expected: int) -> None:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        with self.portal.store.transaction() as connection:
            current = self._setting(key)
            if (current[1] if current else 0) != expected:
                raise ConcurrentResponseUpdate("configuration revision is stale")
            connection.execute(
                "INSERT INTO runtime_settings VALUES (?,?,?,?,?,?) ON CONFLICT(key) "
                "DO UPDATE SET payload=excluded.payload,revision=excluded.revision,"
                "version=excluded.version,updated_by=excluded.updated_by,"
                "updated_at=excluded.updated_at",
                (
                    key,
                    json.dumps(payload, sort_keys=True),
                    expected + 1,
                    version,
                    actor.actor_id,
                    datetime.now(UTC).isoformat(),
                ),
            )
            self.portal.audit(actor, f"{key}_changed", version)

    def qc(self, token: str) -> dict[str, Any]:
        self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        setting = self._setting("qc_config")
        return {
            "revision": setting[1] if setting else 0,
            "qc": asdict(self.pipeline._qc_config),
            "editable_fields": sorted(self.QC_EDITABLE),
            "candidate_thresholds": True,
        }

    def change_qc(self, token: str, request: QCChange) -> dict[str, Any]:
        self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if set(request.changes) - self.QC_EDITABLE:
            raise ValueError("unknown or non-editable QC setting")
        updated = replace(
            self.pipeline._qc_config, version=f"qc-{uuid.uuid4().hex}", **request.changes
        )
        if updated.max_duration_s > 300 or updated.min_duration_s < 1:
            raise ValueError("local QC duration must remain between 1 and 300 seconds")
        self._save(token, "qc_config", asdict(updated), updated.version, request.expected_revision)
        self.pipeline._qc_config = updated
        return self.qc(token)

    def _model_dir(self) -> Path:
        path = self.config.get("model_artifact")
        return (Path(path) if path else default_artifact_path()).parent

    def models(self, token: str) -> dict[str, Any]:
        self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        try:
            directory = self._model_dir()
        except ModelArtifactError:
            return {"items": [], "revision": 0}
        active = getattr(self.pipeline._scorer, "artifact", None)
        items = []
        for path in sorted(directory.glob("*.json"))[:100]:
            try:
                artifact = load_artifact(path)
            except ModelArtifactError as error:
                items.append(
                    {
                        "name": path.stem,
                        "compatible": False,
                        "reason": error.reason.value,
                        "active": False,
                    }
                )
            else:
                items.append(
                    {
                        "name": path.stem,
                        "compatible": True,
                        "model_version": artifact.model_version,
                        "sha256": artifact.sha256,
                        "unit_of_inference": artifact.unit_of_inference,
                        "calibration_version": artifact.calibration_version,
                        "active": active is not None and active.name == path.stem,
                    }
                )
        setting = self._setting("active_model")
        return {
            "items": items,
            "revision": setting[1] if setting else 0,
            "note": "Chỉ kích hoạt artifact đúng pin và cùng đơn vị suy luận; "
            "báo cáo cũ giữ provenance đã lưu.",
        }

    def activate_model(self, token: str, name: str, expected_revision: int) -> dict[str, Any]:
        self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name):
            raise ValueError("invalid model name")
        artifact = load_artifact(self._model_dir() / f"{name}.json")
        self._save(token, "active_model", {"name": name}, artifact.model_version, expected_revision)
        self.pipeline._scorer = RidgeScorer(artifact=artifact)
        return self.models(token)

    def readiness(self) -> dict[str, Any]:
        checks = {}
        if self.worker is not None:
            checks["worker"] = self.worker._thread.is_alive()
        connection = self.portal.store.connection
        try:
            connection.execute("SAVEPOINT readiness_check")
            connection.execute("UPDATE runtime_settings SET revision=revision WHERE 0")
            connection.execute("ROLLBACK TO readiness_check")
            connection.execute("RELEASE readiness_check")
            checks["database"] = True
        except Exception:
            try:
                connection.execute("ROLLBACK TO readiness_check")
                connection.execute("RELEASE readiness_check")
            except Exception:
                pass
            checks["database"] = False
        checks["scoring_model"] = getattr(self.pipeline._scorer, "artifact", None) is not None
        try:
            self.pipeline._asr._load_engine()._load()
            checks["asr_model"] = True
        except Exception:
            checks["asr_model"] = False
        try:
            self.pipeline._extractor._vad._load()._load()
            checks["vad_model"] = True
        except Exception:
            checks["vad_model"] = False
        return {"ready": all(checks.values()), "checks": checks}
