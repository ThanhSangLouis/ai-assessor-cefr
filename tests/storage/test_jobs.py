from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

import pytest

from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import ActorRole, AuditEvent, ResponseStatus
from aicefr.storage.blob import BlobStore
from aicefr.storage.jobs import LeaseLost, SQLiteJobRepository
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def submitted(tmp_path):
    store = SQLiteStore(tmp_path / "jobs-data")
    auth = AuthService(store, store)
    owner = auth.bootstrap_fixture_account("fixture-jobs-owner", ActorRole.STUDENT, "password")
    consent = ConsentService(store)
    consent.activate(owner, "v1")
    responses = ResponseService(store, BlobStore(tmp_path / "jobs-data", max_bytes=1024), consent)
    response = responses.submit(
        owner,
        task_id="fixture-task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"synthetic test data",
    )
    return store, response


def test_enqueue_is_idempotent_and_claim_uses_revision_lease(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock, random_id=lambda: "job-1")

    first = jobs.enqueue(response.response_id)
    again = jobs.enqueue(response.response_id)
    claimed = jobs.claim("worker-a", lease_seconds=10)

    assert first == again
    assert claimed is not None
    assert claimed.attempt == 1 and claimed.revision == 1
    assert claimed.lease_owner == "worker-a" and claimed.lease_until == 110
    assert jobs.claim("worker-b", lease_seconds=10) is None
    assert jobs.heartbeat(claimed.job_id, "worker-a", claimed.revision, lease_seconds=10)
    assert not jobs.complete(claimed.job_id, "worker-b", claimed.revision)
    assert not jobs.complete(claimed.job_id, "worker-a", claimed.revision)
    store.connection.execute(
        "UPDATE responses SET status='COMPLETED' WHERE response_id=?", (response.response_id,)
    )
    assert jobs.complete(claimed.job_id, "worker-a", claimed.revision)
    assert jobs.get(claimed.job_id).state == "succeeded"
    store.close()


def test_expired_running_job_resets_response_and_fences_old_owner(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock, random_id=lambda: "job-2")
    jobs.enqueue(response.response_id)
    old = jobs.claim("old-worker", lease_seconds=5)
    assert old is not None
    running = store.claim_queued_response(response)

    jobs.assert_owned(
        old.job_id, "old-worker", old.revision, response.response_id, running.revision
    )
    clock.now += 6
    assert jobs.recover_expired() == 1
    queued = store.get_response(response.response_id)
    assert queued.status.value == "QUEUED"
    assert queued.revision == running.revision + 1
    with pytest.raises(LeaseLost):
        jobs.assert_owned(
            old.job_id, "old-worker", old.revision, response.response_id, running.revision
        )

    successor = jobs.claim("new-worker", lease_seconds=10)
    assert successor is not None and successor.attempt == 2
    jobs.assert_owned(
        successor.job_id, "new-worker", successor.revision, response.response_id, queued.revision
    )
    running_again = store.claim_queued_response(queued)
    with pytest.raises(LeaseLost):
        jobs.assert_owned(
            old.job_id,
            "old-worker",
            old.revision,
            response.response_id,
            running_again.revision,
        )
    store.close()


def test_startup_discovers_legacy_queued_response_without_job(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock, random_id=lambda: "job-3")
    assert jobs.discover_queued_responses() == 1
    assert jobs.discover_queued_responses() == 0
    assert jobs.get("job-3").response_id == response.response_id
    store.close()


def test_retry_limit_marks_response_failed_once(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock, random_id=iter(("job-4", "e" * 32)).__next__)
    jobs.enqueue(response.response_id, max_attempts=1)
    job = jobs.claim("worker", lease_seconds=10)
    assert job is not None

    assert jobs.fail(job.job_id, "worker", job.revision, "fixture-error")
    failed = store.get_response(response.response_id)
    assert failed.status.value == "FAILED"
    assert [event.action for event in store.list_audit()].count("pipeline_failed") == 1
    assert jobs.get(job.job_id).state == "failed"
    store.close()


def test_expired_claim_before_response_claim_is_requeued_then_bounded(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock)
    job = jobs.enqueue(response.response_id, max_attempts=2)
    first = jobs.claim("crashed-before-pipeline", lease_seconds=5)
    assert first is not None

    clock.now += 6
    assert jobs.recover_expired() == 1
    assert store.get_response(response.response_id).status.value == "QUEUED"
    second = jobs.claim("crashed-again", lease_seconds=5)
    assert second is not None and second.attempt == 2
    clock.now += 6
    assert jobs.recover_expired() == 1
    assert jobs.get(job.job_id).state == "failed"
    assert store.get_response(response.response_id).status.value == "FAILED"
    assert [event.action for event in store.list_audit()].count("pipeline_failed") == 1
    store.close()


def test_expired_job_after_terminal_commit_is_reconciled_without_new_audit(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock)
    jobs.enqueue(response.response_id)
    claimed = jobs.claim("worker", lease_seconds=5)
    assert claimed is not None
    running = store.claim_queued_response(response)
    with store.transaction() as connection:
        connection.execute(
            "UPDATE responses SET status=?,revision=revision+1 WHERE response_id=? AND revision=?",
            (ResponseStatus.COMPLETED, response.response_id, running.revision),
        )
        store._audit(
            connection,
            AuditEvent(
                event_id=uuid.uuid4().hex,
                actor_id="system-pipeline",
                action="pipeline_completed",
                object_id=response.response_id,
                recorded_at=datetime.now(UTC),
            ),
        )
    before = len(store.list_audit())
    store.close()
    restarted = SQLiteStore(tmp_path / "jobs-data")
    jobs = SQLiteJobRepository(restarted, clock=clock)

    clock.now += 6
    assert jobs.recover_expired() == 1
    assert jobs.get(claimed.job_id).state == "succeeded"
    assert len(restarted.list_audit()) == before
    restarted.close()


def test_expired_lease_rejects_stale_heartbeat_completion_and_failure(tmp_path):
    clock = Clock()
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store, clock=clock)
    jobs.enqueue(response.response_id)
    claimed = jobs.claim("worker", lease_seconds=5)
    assert claimed is not None

    clock.now += 6
    assert not jobs.heartbeat(claimed.job_id, "worker", claimed.revision, lease_seconds=5)
    assert not jobs.complete(claimed.job_id, "worker", claimed.revision)
    assert not jobs.fail(claimed.job_id, "worker", claimed.revision, "stale")
    assert jobs.get(claimed.job_id).state == "running"
    store.close()


def test_two_connections_cannot_claim_same_job(tmp_path):
    store, response = submitted(tmp_path)
    jobs = SQLiteJobRepository(store)
    jobs.enqueue(response.response_id)
    barrier = threading.Barrier(3)
    claimed = []

    def run_claim(owner):
        worker_store = SQLiteStore(store.data_dir)
        try:
            barrier.wait(timeout=5)
            claimed.append(SQLiteJobRepository(worker_store).claim(owner))
        finally:
            worker_store.close()

    workers = [threading.Thread(target=run_claim, args=(owner,)) for owner in ("a", "b")]
    for worker in workers:
        worker.start()
    barrier.wait(timeout=5)
    for worker in workers:
        worker.join(timeout=5)
    assert all(not worker.is_alive() for worker in workers)
    assert sum(job is not None for job in claimed) == 1
    store.close()
