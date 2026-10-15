"""Composition root for the local WSGI demonstrator."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aicefr.api.review import ReviewApi
from aicefr.api.student import (
    StudentApi,
    StudentService,
    UploadPolicy,
)
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.asr.service import AsrService, ModelUnavailableError
from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import ActorRole
from aicefr.features.extractor import FeatureExtractor
from aicefr.observability import Metrics
from aicefr.portal.contracts import TaskRecord
from aicefr.portal.control import RuntimeControl
from aicefr.portal.data import DataControl
from aicefr.portal.router import PortalRouter
from aicefr.portal.service import PortalService
from aicefr.portal.tasks import TaskRepository
from aicefr.review.service import ReviewService
from aicefr.review.sqlite import SQLiteReviewRepository
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.blob import BlobStore
from aicefr.storage.providers import RepositoryProviders, build_providers
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


@dataclass
class LocalRuntime:
    app: StudentTeacherApp
    store: SQLiteStore
    auth: AuthService
    consents: ConsentService
    responses: ResponseService
    portal: PortalService
    control: RuntimeControl
    data: DataControl
    worker: Any | None = None
    providers: RepositoryProviders | None = None

    def close(self) -> None:
        if self.worker is not None:
            self.worker.close()
        self.store.close()


class SQLiteSessionRepository:
    """Session port with digest-only revocation over the shared SQLite store."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def get_session(self, digest: str):
        return self._store.get_session(digest)

    def put_session(self, session: Any) -> None:
        self._store.put_session(session)

    def delete_session(self, digest: str) -> None:
        with self._store.transaction() as connection:
            connection.execute("DELETE FROM sessions WHERE token_digest=?", (digest,))


class _LazyVad:
    name = "silero"

    def __init__(self, threshold: float, min_silence_ms: int) -> None:
        self.threshold = threshold
        self.min_silence_ms = min_silence_ms
        self._engine = None

    @property
    def version(self) -> str:
        return self._load().version

    def _load(self):
        if self._engine is None:
            from aicefr.features.local import SileroVadEngine

            self._engine = SileroVadEngine(
                threshold=self.threshold, min_silence_ms=self.min_silence_ms
            )
        return self._engine

    def segments(self, samples: Any, sample_rate_hz: int):
        return self._load().segments(samples, sample_rate_hz)


def create_runtime(
    data_dir: Path | str,
    *,
    config: dict[str, Any],
    asr_engine: Any | None = None,
    vad_engine: Any | None = None,
    scorer: Any | None = None,
    pipeline: Any | None = None,
    repository_factory: Callable[[SQLiteStore], RepositoryProviders] | None = None,
) -> LocalRuntime:
    """Build persistent services; injected engines are for deterministic tests."""
    from aicefr.audio.config import AudioFormat, QCConfig
    from aicefr.report.service import ReportService
    from aicefr.report.sqlite import SQLiteReportRepository

    qc = QCConfig(
        version=str(config["qc"]["version"]),
        accepted_formats=tuple(AudioFormat(item) for item in config["qc"]["accepted_formats"]),
        max_input_bytes=int(config["qc"]["max_input_bytes"]),
        min_duration_s=float(config["qc"]["min_duration_s"]),
        max_duration_s=float(config["qc"]["max_duration_s"]),
        max_input_sample_rate_hz=int(config["qc"]["max_input_sample_rate_hz"]),
        silence_threshold=float(config["qc"]["silence_threshold"]),
        clipping_threshold=float(config["qc"]["clipping_threshold"]),
        review_silence_ratio=float(config["qc"]["review_silence_ratio"]),
        reject_silence_ratio=float(config["qc"]["reject_silence_ratio"]),
        review_clipping_ratio=float(config["qc"]["review_clipping_ratio"]),
        reject_clipping_ratio=float(config["qc"]["reject_clipping_ratio"]),
    )
    store = SQLiteStore(data_dir)
    worker = None
    try:
        stored_qc = store.connection.execute(
            "SELECT payload FROM runtime_settings WHERE key='qc_config'"
        ).fetchone()
        if stored_qc:
            qc = QCConfig(**json.loads(stored_qc[0]))
        providers = (repository_factory or build_providers)(store)
        blobs = BlobStore(store.data_dir, max_bytes=qc.max_input_bytes)
        consents = ConsentService(store)
        auth = AuthService(store, SQLiteSessionRepository(store))
        responses = ResponseService(store, blobs, consents)
        if config.get("recover_interrupted", False):
            from aicefr.contracts import ReasonCode, ResponseStatus

            durable_jobs_exists = store.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='durable_jobs'"
            ).fetchone()
            recovery_query = "SELECT * FROM responses WHERE status=?"
            if durable_jobs_exists:
                recovery_query += (
                    " AND NOT EXISTS (SELECT 1 FROM durable_jobs j "
                    "WHERE j.response_id=responses.response_id)"
                )
            for row in store.connection.execute(
                recovery_query, (ResponseStatus.RUNNING,)
            ).fetchall():
                interrupted = store._response_from_row(row)
                responses.transition_status(
                    response_id=interrupted.response_id,
                    expected_revision=interrupted.revision,
                    status=ResponseStatus.FAILED,
                    actor_id="system-startup",
                    action="pipeline_interrupted",
                    reason=ReasonCode.PIPELINE_INTERRUPTED,
                )
        report_repository = SQLiteReportRepository(store)
        reports = ReportService(report_repository, decision_verifier=SQLiteReviewRepository(store))
        review_repository = SQLiteReviewRepository(store)
        reviews = ReviewService(review_repository, report_sink=reports)
        if pipeline is None:
            stored_model = store.connection.execute(
                "SELECT payload FROM runtime_settings WHERE key='active_model'"
            ).fetchone()
            if stored_model and scorer is None:
                from re import fullmatch

                from aicefr.scoring.artifact import default_artifact_path

                model_name = json.loads(stored_model[0])["name"]
                if not fullmatch(r"[A-Za-z0-9_-]{1,80}", model_name):
                    raise ValueError("invalid persisted model name")
                directory = (
                    Path(config["model_artifact"])
                    if config.get("model_artifact")
                    else default_artifact_path()
                ).parent
                scorer = RidgeScorer.load(directory / f"{model_name}.json")
            scorer_instance = scorer or RidgeScorer.load(
                Path(config["model_artifact"]) if config.get("model_artifact") else None
            )
            artifact = getattr(scorer_instance, "artifact", None)
            if asr_engine is None:
                model_dir = config.get("asr_model_dir")

                def load_asr():
                    if not model_dir:
                        raise ModelUnavailableError("local ASR model is not configured")
                    from aicefr.asr.local import FasterWhisperEngine

                    return FasterWhisperEngine(
                        Path(model_dir),
                        weight_name=str(config.get("asr_weight_name", "small")),
                        device=str(config.get("asr_device", "cpu")),
                        compute_type=str(config.get("asr_compute_type", "int8")),
                    )

                asr = AsrService(
                    engine_loader=load_asr,
                    trained_asr_model=(
                        artifact.trained_with.get("asr_model") if artifact is not None else None
                    ),
                )
            else:
                asr = AsrService(
                    engine_loader=lambda: asr_engine,
                    trained_asr_model=(
                        artifact.trained_with.get("asr_model") if artifact is not None else None
                    ),
                )
            if artifact is not None:
                feature_order = artifact.feature_order
                feature_version = artifact.feature_version
                trained_with = artifact.trained_with
            else:
                feature_order, feature_version, trained_with = (), "unavailable", {}
            extractor = (
                FeatureExtractor.from_artifact(
                    artifact,
                    vad_engine
                    or (
                        _LazyVad(
                            float(config.get("vad_threshold", 0.5)),
                            int(config.get("vad_min_silence_ms", 150)),
                        )
                        if config.get("vad_enabled", True)
                        else None
                    ),
                )
                if artifact is not None
                else FeatureExtractor(feature_order, feature_version, trained_with, vad_engine)
            )
            from aicefr.pipeline.coordinator import PipelineCoordinator

            pipeline = PipelineCoordinator(
                responses=responses,
                reports=reports,
                reviews=reviews,
                qc_config=qc,
                asr=asr,
                extractor=extractor,
                scorer=scorer_instance,
                long_response_windows=bool(config.get("long_response_windows", False)),
            )
        tasks = TaskRepository(store)
        for item in config["tasks"]:
            tasks.seed(TaskRecord(**{"title": str(item["task_id"]), **item}))
        portal = PortalService(auth, store, tasks)
        control = RuntimeControl(portal, pipeline, config)
        control._asr_injected = asr_engine is not None
        data = DataControl(portal, blobs)
        metrics = Metrics()
        worker = None
        starter = pipeline
        if config.get("async_pipeline", False):
            if asr_engine is not None or vad_engine is not None or scorer is not None:
                raise ValueError("async mode creates its own real model adapters")
            from aicefr.local.worker import BackgroundPipeline

            worker_config = {**config, "async_pipeline": False, "recover_interrupted": False}
            worker = BackgroundPipeline(
                store,
                lambda: create_runtime(data_dir, config=worker_config),
                capacity=int(config.get("queue_capacity", 8)),
            )
            starter = worker
            control.worker = worker
        student = StudentService(
            auth,
            responses,
            reports,
            UploadPolicy(
                allowed_media_types=frozenset(config["allowed_media_types"]),
                max_bytes=qc.max_input_bytes,
            ),
            tasks,
            starter,
        )
        app = StudentTeacherApp(
            StudentApi(student),
            review_api=ReviewApi(auth, reviews),
            auth=auth,
            consents=consents,
            responses=responses,
            reviews=review_repository,
            reports=reports,
            demo=bool(config.get("demo", False)),
            consent_version=str(config.get("consent_version", "local-v1")),
            max_request_bytes=qc.max_input_bytes + 1024 * 1024,
            portal=PortalRouter(portal, control, data, metrics),
            metrics=metrics,
        )
        return LocalRuntime(
            app, store, auth, consents, responses, portal, control, data, worker, providers
        )
    except Exception:
        if worker is not None:
            worker.close()
        store.close()
        raise


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("configuration unavailable or invalid") from error
    if not isinstance(value, dict):
        raise ValueError("configuration must be a JSON object")
    required = {"qc", "allowed_media_types", "tasks"}
    if not required.issubset(value):
        raise ValueError("configuration is missing required settings")
    return value


def provision_fixture(runtime: LocalRuntime, actor_id: str, role: ActorRole, password: str) -> None:
    runtime.auth.bootstrap_fixture_account(actor_id, role, password)
