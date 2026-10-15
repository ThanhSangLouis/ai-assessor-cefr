"""Filesystem-free checks for the versioned M01/M07 SQLite migration."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from aicefr.auth.service import AccountRecord
from aicefr.contracts import (
    Actor,
    ActorRole,
    AuditEvent,
    BlobRef,
    ReasonCode,
    ResponseRecord,
    ResponseStatus,
)
from aicefr.storage.sqlite import ConcurrentResponseUpdate, SQLiteStore


def _memory_store() -> SQLiteStore:
    store = object.__new__(SQLiteStore)
    store.connection = sqlite3.connect(":memory:", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._migrate()
    return store


def _audit(response_id: str) -> AuditEvent:
    return AuditEvent(
        event_id=uuid.uuid4().hex,
        actor_id="fixture-student",
        action="fixture_event",
        object_id=response_id,
        recorded_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


def test_m01_sqlite_schema_v2_persists_status_reason_with_optimistic_locking():
    store = _memory_store()
    actor = Actor(actor_id="fixture-student", role=ActorRole.STUDENT)
    store.add_account(AccountRecord(actor, "fixture-hash"))
    record = ResponseRecord(
        response_id="a" * 32,
        owner_id=actor.actor_id,
        task_id="fixture-task",
        task_version="v1",
        blob=BlobRef(blob_id="b" * 32, sha256="c" * 64, size_bytes=1),
        status=ResponseStatus.QUEUED,
        created_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    store.save_response(record, _audit(record.response_id))

    updated = store.update_response_status(
        record.response_id,
        expected_revision=record.revision,
        status=ResponseStatus.FAILED,
        status_reason=ReasonCode.ASR_FAILED,
        event=_audit(record.response_id),
    )

    version = store.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == SQLiteStore.SCHEMA_VERSION == 10
    assert store.get_response(record.response_id) == updated
    assert updated.status is ResponseStatus.FAILED
    assert updated.status_reason is ReasonCode.ASR_FAILED
    assert updated.revision == 2


def test_m01_sqlite_migrates_legacy_submitted_status_to_queued_without_data_loss():
    store = object.__new__(SQLiteStore)
    store.connection = sqlite3.connect(":memory:", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._create_v1_schema()
    store.connection.execute(
        "INSERT INTO accounts VALUES (?, ?, ?)",
        ("fixture-student", "student", "x"),
    )
    store.connection.execute(
        "INSERT INTO responses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "a" * 32,
            "fixture-student",
            "fixture-task",
            "v1",
            "b" * 32,
            "c" * 64,
            1,
            "submitted",
            1,
            datetime(2026, 9, 28, tzinfo=UTC).isoformat(),
        ),
    )

    store._migrate()

    migrated = store.get_response("a" * 32)
    assert migrated is not None
    assert migrated.status is ResponseStatus.QUEUED
    assert migrated.status_reason is None
    version = store.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == SQLiteStore.SCHEMA_VERSION == 10


def test_pipeline_claim_is_queued_only_and_revision_checked():
    store = _memory_store()
    actor = Actor(actor_id="fixture-student", role=ActorRole.STUDENT)
    store.add_account(AccountRecord(actor, "fixture-hash"))
    record = ResponseRecord(
        response_id="e" * 32,
        owner_id=actor.actor_id,
        task_id="fixture-task",
        task_version="v1",
        blob=BlobRef(blob_id="f" * 32, sha256="1" * 64, size_bytes=1),
        created_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    store.save_response(record, _audit(record.response_id))
    claimed = store.claim_queued_response(record)
    assert claimed.status is ResponseStatus.RUNNING
    with pytest.raises(ConcurrentResponseUpdate):
        store.claim_queued_response(record)
    assert store.get_response(record.response_id) == claimed
