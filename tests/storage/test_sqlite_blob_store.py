import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aicefr.auth.service import AuthorizationError, AuthService, ConsentService, ResourceNotFound
from aicefr.contracts import ActorRole, BlobRef, ConsentState
from aicefr.storage.blob import BlobIntegrityError, BlobStore
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


def test_blob_read_preserves_binary_newlines_and_control_bytes(tmp_path):
    blobs = BlobStore(tmp_path / "binary-fixture", max_bytes=64)
    payload = b"fixture\r\n\x1a\x00tail"
    blob = blobs.store(payload)

    assert blobs.read(blob) == payload
    assert (blobs.root / blob.blob_id).read_bytes() == payload


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 28, tzinfo=UTC)

    def __call__(self):
        return self.now


def setup_service(tmp_path):
    clock = Clock()
    store = SQLiteStore(tmp_path / "m08-data")
    blobs = BlobStore(tmp_path / "m08-data", max_bytes=64)
    auth = AuthService(store, store, clock=clock)
    owner = auth.bootstrap_fixture_account("fixture-owner", ActorRole.STUDENT, "password")
    other = auth.bootstrap_fixture_account("fixture-other", ActorRole.STUDENT, "password")
    consent = ConsentService(store, clock=clock)
    consent.activate(owner, "v1")
    return (
        clock,
        store,
        blobs,
        auth,
        owner,
        other,
        consent,
        ResponseService(store, blobs, consent, clock=clock),
    )


def test_restart_restores_response_audit_session_and_checksum(tmp_path):
    clock, store, blobs, auth, owner, _, consent, responses = setup_service(tmp_path)
    token = auth.login(owner.actor_id, "password")
    record = responses.submit(
        owner,
        task_id="fixture-task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"synthetic fixture bytes",
    )
    assert responses.get_blob(owner, record.response_id) == b"synthetic fixture bytes"
    assert [event.action for event in store.list_audit()] == [
        "consent_active",
        "response_submitted",
    ]
    store.close()

    restarted = SQLiteStore(tmp_path / "m08-data")
    restarted_auth = AuthService(restarted, restarted, clock=clock)
    restarted_responses = ResponseService(
        restarted,
        BlobStore(tmp_path / "m08-data", max_bytes=64),
        ConsentService(restarted, clock=clock),
        clock=clock,
    )
    assert restarted_auth.resolve(token) == owner
    assert restarted_responses.get_response(owner, record.response_id) == record
    assert restarted_responses.get_blob(owner, record.response_id) == b"synthetic fixture bytes"
    assert len(restarted.list_audit()) == 2
    version = restarted.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == SQLiteStore.SCHEMA_VERSION == 9
    assert restarted.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    restarted.close()


def test_owner_denied_before_blob_read_and_withdrawal_blocks_submit(tmp_path, monkeypatch):
    _, store, blobs, _, owner, other, consent, responses = setup_service(tmp_path)
    record = responses.submit(
        owner,
        task_id="task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"fixture",
    )

    def never_read(_):
        raise AssertionError("blob content was read before authorization")

    monkeypatch.setattr(blobs, "read", never_read)
    with pytest.raises(ResourceNotFound) as foreign:
        responses.get_blob(other, record.response_id)
    with pytest.raises(ResourceNotFound) as missing:
        responses.get_blob(owner, "0" * 32)
    assert str(foreign.value) == str(missing.value)
    consent.withdraw(owner)
    assert store.get_consent(owner.actor_id).state == ConsentState.WITHDRAWN
    with pytest.raises(AuthorizationError):
        responses.submit(
            owner,
            task_id="task",
            task_version="v1",
            consent_version="v1",
            audio_bytes=b"new fixture",
        )
    assert store.get_response(record.response_id) == record
    assert "consent_withdrawn" in [event.action for event in store.list_audit()]
    store.close()


def test_corruption_limits_and_reconciliation_report_only(tmp_path):
    _, store, blobs, _, owner, _, _, responses = setup_service(tmp_path)
    with pytest.raises(ValueError):
        blobs.store(b"")
    with pytest.raises(ValueError):
        blobs.store(b"x" * 65)
    with pytest.raises(ValidationError):
        BlobRef(blob_id="../outside", sha256="0" * 64, size_bytes=1)
    record = responses.submit(
        owner,
        task_id="task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"fixture",
    )
    path = blobs.root / record.blob.blob_id
    path.write_bytes(b"tamperd")
    with pytest.raises(BlobIntegrityError):
        responses.get_blob(owner, record.response_id)
    path.unlink()
    orphan = blobs.root / ("a" * 32)
    orphan.write_bytes(b"orphan")
    staging = blobs.root / "tmp-fixture.part"
    staging.write_bytes(b"staged")
    assert responses.report_orphans() == ("a" * 32, "tmp-fixture.part")
    assert orphan.exists() and staging.exists()
    store.close()


def test_symlinked_blob_is_rejected_when_platform_supports_it(tmp_path):
    _, store, blobs, _, owner, _, _, responses = setup_service(tmp_path)
    record = responses.submit(
        owner,
        task_id="task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"fixture",
    )
    path = blobs.root / record.blob.blob_id
    path.unlink()
    try:
        path.symlink_to(tmp_path / "outside")
    except OSError as error:
        store.close()
        pytest.skip(f"symlink creation is unavailable on this Windows host: {error.winerror}")

    with pytest.raises(BlobIntegrityError):
        responses.get_blob(owner, record.response_id)
    path.unlink()
    store.close()


def test_failed_metadata_transaction_compensates_blob_and_audit(tmp_path):
    _, store, blobs, _, owner, _, _, responses = setup_service(tmp_path)
    audit_before = len(store.list_audit())
    store.connection.execute(
        """CREATE TRIGGER fail_response BEFORE INSERT ON responses
        BEGIN SELECT RAISE(ABORT, 'forced test failure'); END"""
    )
    with pytest.raises(sqlite3.IntegrityError):
        responses.submit(
            owner,
            task_id="task",
            task_version="v1",
            consent_version="v1",
            audio_bytes=b"fixture",
        )
    assert list(blobs.root.iterdir()) == []
    assert store.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
    assert len(store.list_audit()) == audit_before
    store.close()


def test_audit_is_append_only_and_schema_version_is_rejected(tmp_path):
    _, store, _, _, _, _, _, _ = setup_service(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute("DELETE FROM audit")
    store.connection.execute(f"PRAGMA user_version={SQLiteStore.SCHEMA_VERSION + 1}")
    store.close()
    with pytest.raises(RuntimeError, match="unsupported"):
        SQLiteStore(tmp_path / "m08-data")


def test_session_idle_expiry_persists_after_restart(tmp_path):
    clock, store, _, auth, owner, _, _, _ = setup_service(tmp_path)
    token = auth.login(owner.actor_id, "password")
    store.close()
    clock.now += timedelta(minutes=30)
    restarted = SQLiteStore(tmp_path / "m08-data")
    with pytest.raises(AuthorizationError):
        AuthService(restarted, restarted, clock=clock).resolve(token)
    restarted.close()


def test_blob_failure_paths_are_bounded_and_leave_no_stage(tmp_path, monkeypatch):
    import aicefr.storage.blob as blob_module

    with pytest.raises(ValueError):
        BlobStore(tmp_path / "data", max_bytes=0)
    blobs = BlobStore(tmp_path / "data", max_bytes=8)

    def fail_replace(source, destination):
        raise OSError("forced rename failure")

    monkeypatch.setattr(blob_module.os, "replace", fail_replace)
    with pytest.raises(OSError):
        blobs.store(b"fixture")
    assert list(blobs.root.iterdir()) == []
    monkeypatch.undo()
    ref = blobs.store(b"fixture")
    (blobs.root / ref.blob_id).unlink()
    with pytest.raises(BlobIntegrityError):
        blobs.read(ref)


def test_repositories_return_none_for_absent_ids(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    assert store.get_account("missing") is None
    assert store.get_session("0" * 64) is None
    assert store.get_consent("missing") is None
    assert store.get_response("0" * 32) is None
    store.close()


def test_migration_error_rolls_back_partial_schema(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    connection = sqlite3.connect(path / "metadata.sqlite3")
    connection.execute("CREATE TABLE accounts (id TEXT)")
    connection.commit()
    connection.close()
    with pytest.raises(sqlite3.OperationalError):
        SQLiteStore(path)
    connection = sqlite3.connect(path / "metadata.sqlite3")
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
    assert (
        connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit'"
        ).fetchone()
        is None
    )
    connection.close()
