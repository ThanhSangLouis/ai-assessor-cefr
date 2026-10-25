from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from aicefr.contracts import CURRENT_CONSENT_VERSION, ActorRole, ResponseStatus
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.local.worker import BackgroundPipeline
from aicefr.storage.jobs import SQLiteJobRepository
from aicefr.storage.sqlite import SQLiteStore


def _submitted_runtime(tmp_path):
    runtime = create_runtime(tmp_path / "data", config=_demo_config())
    actor = runtime.auth.bootstrap_fixture_account(
        "fixture-worker", ActorRole.STUDENT, "fixture-password"
    )
    runtime.consents.activate(
        actor, CURRENT_CONSENT_VERSION, audio_storage_allowed=True
    )
    response = runtime.responses.submit(
        actor,
        task_id="fixture-task",
        task_version="v1",
        consent_version=CURRENT_CONSENT_VERSION,
        audio_bytes=b"synthetic worker test data",
    )
    return runtime, response


def test_worker_recovers_lease_that_expires_after_startup(tmp_path):
    runtime, response = _submitted_runtime(tmp_path)
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?",
        (ResponseStatus.COMPLETED, response.response_id),
    )
    worker_store_ready = threading.Event()
    processed = threading.Event()

    def factory():
        store = SQLiteStore(runtime.store.data_dir)

        class Pipeline:
            def set_commit_guard(self, _guard):
                return None

            def enqueue(self, queued):
                store.claim_queued_response(queued)
                store.connection.execute(
                    "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                    (ResponseStatus.COMPLETED, queued.response_id),
                )
                processed.set()

        worker_store_ready.set()
        return SimpleNamespace(
            store=store,
            control=SimpleNamespace(reload=lambda: None, pipeline=Pipeline()),
            close=store.close,
        )

    worker = BackgroundPipeline(runtime.store, factory, lease_seconds=3)
    try:
        assert worker_store_ready.wait(5)
        deadline = time.monotonic() + 5
        while not worker.health() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert worker.health()

        jobs = SQLiteJobRepository(runtime.store)
        with runtime.store.transaction():
            runtime.store.connection.execute(
                "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                (ResponseStatus.QUEUED, response.response_id),
            )
            jobs.enqueue(response.response_id)
            stale = jobs.claim("crashed-worker", lease_seconds=3)
            assert stale is not None
            queued = runtime.store.get_response(response.response_id)
            running = runtime.store.claim_queued_response(queued)
            runtime.store.connection.execute(
                "UPDATE durable_jobs SET lease_until=0 WHERE job_id=?", (stale.job_id,)
            )

        assert processed.wait(5)
        assert runtime.store.get_response(response.response_id).status is ResponseStatus.COMPLETED
        deadline = time.monotonic() + 5
        while jobs.get(stale.job_id).state != "succeeded" and time.monotonic() < deadline:
            time.sleep(0.01)
        assert jobs.get(stale.job_id).state == "succeeded"
        assert runtime.store.get_response(response.response_id).revision > running.revision
    finally:
        worker.close()
        runtime.close()


def test_worker_factory_failure_marks_health_false_without_traceback(tmp_path, caplog):
    store = SQLiteStore(tmp_path / "data")

    def broken_factory():
        raise RuntimeError("fixture path /should/not/be/logged")

    worker = BackgroundPipeline(store, broken_factory)
    worker._thread.join(timeout=5)
    try:
        assert not worker.health()
        assert "Traceback" not in caplog.text
        assert "/should/not/be/logged" not in caplog.text
    finally:
        worker.close()
        store.close()


def test_worker_renews_lease_while_pipeline_is_blocked(tmp_path):
    runtime, response = _submitted_runtime(tmp_path)
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?",
        (ResponseStatus.COMPLETED, response.response_id),
    )
    pipeline_entered, release_pipeline = threading.Event(), threading.Event()
    store_ready = threading.Event()

    def factory():
        store = SQLiteStore(runtime.store.data_dir)

        class Pipeline:
            def set_commit_guard(self, _guard):
                return None

            def enqueue(self, queued):
                store.claim_queued_response(queued)
                pipeline_entered.set()
                assert release_pipeline.wait(5)
                store.connection.execute(
                    "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                    (ResponseStatus.COMPLETED, queued.response_id),
                )

        store_ready.set()
        return SimpleNamespace(
            store=store,
            control=SimpleNamespace(reload=lambda: None, pipeline=Pipeline()),
            close=store.close,
        )

    worker = BackgroundPipeline(runtime.store, factory, lease_seconds=3)
    try:
        assert store_ready.wait(5)
        deadline = time.monotonic() + 5
        while not worker.health() and time.monotonic() < deadline:
            time.sleep(0.01)
        with runtime.store.transaction():
            runtime.store.connection.execute(
                "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                (ResponseStatus.QUEUED, response.response_id),
            )
            worker.enqueue(response)
        assert pipeline_entered.wait(5)
        jobs = SQLiteJobRepository(runtime.store)
        initial_lease = jobs.get(
            runtime.store.connection.execute(
                "SELECT job_id FROM durable_jobs WHERE response_id=?", (response.response_id,)
            ).fetchone()[0]
        ).lease_until
        assert initial_lease is not None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            extended_lease = jobs.get(
                runtime.store.connection.execute(
                    "SELECT job_id FROM durable_jobs WHERE response_id=?",
                    (response.response_id,),
                ).fetchone()[0]
            ).lease_until
            if extended_lease is not None and extended_lease > initial_lease + 0.5:
                break
            time.sleep(0.05)
        assert extended_lease is not None and extended_lease > initial_lease + 0.5
        release_pipeline.set()
        deadline = time.monotonic() + 5
        while (
            jobs.get(
                runtime.store.connection.execute(
                    "SELECT job_id FROM durable_jobs WHERE response_id=?", (response.response_id,)
                ).fetchone()[0]
            ).state
            != "succeeded"
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert (
            jobs.get(
                runtime.store.connection.execute(
                    "SELECT job_id FROM durable_jobs WHERE response_id=?", (response.response_id,)
                ).fetchone()[0]
            ).state
            == "succeeded"
        )
    finally:
        release_pipeline.set()
        worker.close()
        runtime.close()


def test_worker_retries_transient_failure_after_backoff(tmp_path):
    runtime, response = _submitted_runtime(tmp_path)
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?",
        (ResponseStatus.COMPLETED, response.response_id),
    )
    calls, succeeded, store_ready = [], threading.Event(), threading.Event()

    def factory():
        store = SQLiteStore(runtime.store.data_dir)

        class Pipeline:
            def set_commit_guard(self, _guard):
                return None

            def enqueue(self, queued):
                calls.append(time.monotonic())
                if len(calls) == 1:
                    raise RuntimeError("synthetic transient failure")
                store.connection.execute(
                    "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                    (ResponseStatus.COMPLETED, queued.response_id),
                )
                succeeded.set()

        store_ready.set()
        return SimpleNamespace(
            store=store,
            control=SimpleNamespace(reload=lambda: None, pipeline=Pipeline()),
            close=store.close,
        )

    worker = BackgroundPipeline(
        runtime.store, factory, lease_seconds=3, max_attempts=3, backoff_seconds=0.2
    )
    try:
        assert store_ready.wait(5)
        deadline = time.monotonic() + 5
        while not worker.health() and time.monotonic() < deadline:
            time.sleep(0.01)
        with runtime.store.transaction():
            runtime.store.connection.execute(
                "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                (ResponseStatus.QUEUED, response.response_id),
            )
            worker.enqueue(response)
        deadline = time.monotonic() + 5
        while len(calls) < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(calls) == 1
        time.sleep(0.05)
        assert len(calls) == 1
        assert succeeded.wait(5)
        assert len(calls) == 2
        job_id = runtime.store.connection.execute(
            "SELECT job_id FROM durable_jobs WHERE response_id=?", (response.response_id,)
        ).fetchone()[0]
        jobs = SQLiteJobRepository(runtime.store)
        deadline = time.monotonic() + 5
        while jobs.get(job_id).state != "succeeded" and time.monotonic() < deadline:
            time.sleep(0.01)
        job = jobs.get(job_id)
        assert job.attempt == 2 and job.state == "succeeded"
    finally:
        worker.close()
        runtime.close()


def test_worker_retry_exhaustion_fails_response_and_audits_once(tmp_path):
    runtime, response = _submitted_runtime(tmp_path)
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?",
        (ResponseStatus.COMPLETED, response.response_id),
    )
    calls, store_ready = [], threading.Event()

    def factory():
        store = SQLiteStore(runtime.store.data_dir)

        class Pipeline:
            def set_commit_guard(self, _guard):
                return None

            def enqueue(self, _queued):
                calls.append(1)
                raise RuntimeError("synthetic persistent failure")

        store_ready.set()
        return SimpleNamespace(
            store=store,
            control=SimpleNamespace(reload=lambda: None, pipeline=Pipeline()),
            close=store.close,
        )

    worker = BackgroundPipeline(
        runtime.store, factory, lease_seconds=3, max_attempts=2, backoff_seconds=0
    )
    try:
        assert store_ready.wait(5)
        deadline = time.monotonic() + 5
        while not worker.health() and time.monotonic() < deadline:
            time.sleep(0.01)
        with runtime.store.transaction():
            runtime.store.connection.execute(
                "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=?",
                (ResponseStatus.QUEUED, response.response_id),
            )
            worker.enqueue(response)
        deadline = time.monotonic() + 5
        while len(calls) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(calls) == 2
        job_id = runtime.store.connection.execute(
            "SELECT job_id FROM durable_jobs WHERE response_id=?", (response.response_id,)
        ).fetchone()[0]
        jobs = SQLiteJobRepository(runtime.store)
        deadline = time.monotonic() + 5
        while jobs.get(job_id).state != "failed" and time.monotonic() < deadline:
            time.sleep(0.01)
        assert jobs.get(job_id).state == "failed"
        assert jobs.get(job_id).attempt == 2
        assert runtime.store.get_response(response.response_id).status is ResponseStatus.FAILED
        assert [event.action for event in runtime.store.list_audit()].count("pipeline_failed") == 1
    finally:
        worker.close()
        runtime.close()
