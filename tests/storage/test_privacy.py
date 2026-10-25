from datetime import UTC, datetime

import pytest

from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import ActorRole
from aicefr.storage.blob import BlobStore
from aicefr.storage.paths import external_data_dir
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


def test_data_dir_is_explicit_and_outside_repository(tmp_path, caplog):
    with pytest.raises(ValueError):
        external_data_dir("")
    with pytest.raises(ValueError):
        SQLiteStore("src/aicefr/storage")
    data_dir = tmp_path / "fixture-store"
    store = SQLiteStore(data_dir)
    auth = AuthService(store, store, clock=lambda: datetime(2026, 9, 28, tzinfo=UTC))
    actor = auth.bootstrap_fixture_account("fixture-private", ActorRole.STUDENT, "secret")
    token = auth.login(actor.actor_id, "secret")
    consent = ConsentService(store, clock=lambda: datetime(2026, 9, 28, tzinfo=UTC))
    consent.activate(actor, "v1", audio_storage_allowed=True)
    responses = ResponseService(
        store,
        BlobStore(data_dir, max_bytes=32),
        consent,
        clock=lambda: datetime(2026, 9, 28, tzinfo=UTC),
    )
    responses.submit(
        actor,
        task_id="task",
        task_version="v1",
        consent_version="v1",
        audio_bytes=b"fixture",
    )
    db_bytes = (data_dir / "metadata.sqlite3").read_bytes()
    assert token.encode("ascii") not in db_bytes
    assert b"secret" not in caplog.text.encode()
    assert token not in caplog.text
    assert auth.resolve(token) == actor
    store.close()
