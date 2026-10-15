"""Local durable worker with its own runtime and SQLite connections."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from threading import Event, Thread
from typing import Any

from aicefr.contracts import ResponseRecord, ResponseStatus
from aicefr.storage.jobs import Job, SQLiteJobRepository
from aicefr.storage.sqlite import SQLiteStore

log = logging.getLogger(__name__)
_TERMINAL_SUCCESS = {
    ResponseStatus.COMPLETED,
    ResponseStatus.REJECTED,
    ResponseStatus.REVIEW_REQUIRED,
}


class BackgroundPipeline:
    """Poll and run durable jobs. ``health()``/``ready`` expose a sanitized boolean."""

    def __init__(
        self,
        store: SQLiteStore,
        factory: Callable[[], Any],
        *,
        capacity: int = 8,
        lease_seconds: float = 30.0,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        if not 1 <= capacity <= 100:
            raise ValueError("worker capacity must be between 1 and 100")
        if lease_seconds < 3 or max_attempts < 1 or backoff_seconds < 0:
            raise ValueError("invalid durable worker lease or retry configuration")
        self.store, self.factory, self.capacity = store, factory, capacity
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self._wake, self._stop, self._ready = Event(), Event(), Event()
        self._state_lock = threading.Lock()
        self._healthy = False
        self._owner = uuid.uuid4().hex
        self._thread = Thread(target=self._run, name="aicefr-local-worker", daemon=True)
        self._thread.start()

    @property
    def ready(self) -> bool:
        return self.health()

    def health(self) -> bool:
        """True after runtime initialization and startup recovery while worker remains alive."""
        with self._state_lock:
            healthy = self._healthy
        return healthy and self._thread.is_alive() and not self._stop.is_set()

    def enqueue(self, response: ResponseRecord) -> None:
        repository = SQLiteJobRepository(self.store)
        repository.enqueue(
            response.response_id,
            max_attempts=self.max_attempts,
            capacity=self.capacity,
        )
        self._wake.set()

    def _run(self) -> None:
        runtime = None
        try:
            runtime = self.factory()
            repository = SQLiteJobRepository(runtime.store)
            repository.recover_expired()
            repository.discover_queued_responses(max_attempts=self.max_attempts)
            with self._state_lock:
                self._healthy = True
            self._ready.set()
            while not self._stop.is_set():
                repository.recover_expired()
                repository.discover_queued_responses(max_attempts=self.max_attempts)
                job = repository.claim(self._owner, lease_seconds=self.lease_seconds)
                if job is None:
                    self._wake.wait(0.5)
                    self._wake.clear()
                    continue
                self._process(runtime, repository, job)
        except Exception as error:
            with self._state_lock:
                self._healthy = False
            log.error("local worker stopped error_type=%s", type(error).__name__)
        finally:
            self._ready.set()
            if runtime is not None:
                runtime.close()

    def _process(self, runtime, repository: SQLiteJobRepository, job: Job) -> None:
        owner, revision = self._owner, job.revision
        pulse_stop = Event()
        pulse = Thread(
            target=self._heartbeat,
            args=(runtime.store.data_dir, job, pulse_stop),
            name="aicefr-worker-lease",
            daemon=True,
        )
        try:
            row = runtime.store.connection.execute(
                "SELECT * FROM responses WHERE response_id=?", (job.response_id,)
            ).fetchone()
            if row is None:
                repository.fail(job.job_id, owner, revision, "response_unavailable")
                return
            response = runtime.store._response_from_row(row)
            pipeline = runtime.control.pipeline
            runtime.control.reload()

            def guard(response_id: str, response_revision: int) -> None:
                repository.assert_owned(job.job_id, owner, revision, response_id, response_revision)

            pipeline.set_commit_guard(guard)
            pulse.start()
            pipeline.enqueue(response)
            latest = runtime.store.get_response(job.response_id)
            if latest is not None and latest.status in _TERMINAL_SUCCESS:
                if not repository.complete(job.job_id, owner, revision):
                    log.warning("job lease lost after terminal commit job_id=%s", job.job_id)
            else:
                repository.fail(
                    job.job_id,
                    owner,
                    revision,
                    "pipeline_returned_without_terminal_response",
                    retry_delay=self._retry_delay(job.attempt),
                )
        except Exception as error:
            repository.fail(
                job.job_id,
                owner,
                revision,
                type(error).__name__,
                retry_delay=self._retry_delay(job.attempt),
            )
            log.warning(
                "pipeline job failed job_id=%s error_type=%s",
                job.job_id,
                type(error).__name__,
            )
        finally:
            pulse_stop.set()
            if pulse.is_alive():
                pulse.join()
            pipeline = getattr(getattr(runtime, "control", None), "pipeline", None)
            if pipeline is not None:
                pipeline.set_commit_guard(None)

    def _heartbeat(self, data_dir, job: Job, stop: Event) -> None:
        """Use a connection created and closed by this heartbeat thread."""
        interval = self.lease_seconds / 3
        try:
            heartbeat_store = SQLiteStore(data_dir)
            repository = SQLiteJobRepository(heartbeat_store)
            try:
                while not stop.wait(interval):
                    if not repository.heartbeat(
                        job.job_id,
                        self._owner,
                        job.revision,
                        lease_seconds=self.lease_seconds,
                    ):
                        return
            finally:
                heartbeat_store.close()
        except Exception as error:
            log.error(
                "worker lease heartbeat stopped job_id=%s error_type=%s",
                job.job_id,
                type(error).__name__,
            )

    def _retry_delay(self, attempt: int) -> float:
        return self.backoff_seconds * (2 ** max(0, attempt - 1))

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join()
