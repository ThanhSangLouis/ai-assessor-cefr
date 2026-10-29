"""D051: recordings in a blob store -- the upload folder, or S3-compatible object storage.

The adapters first (the S3 one against a real server only with AICEFR_TEST_S3,
e.g. `http://key:secret@127.0.0.1:8333`), then the application with a store
that has no local file, the way object storage behaves: submitting, listening,
erasing, the retention sweep and the orphan sweep must all go through the store.
Last, the learning part on a database of its own.
"""

from __future__ import annotations

import importlib
import os
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_lessons_integration import (
    KEYWORD_TEXT,
    KEYWORDS,
    SAMPLE,
    account_id,
    login_as,
    record,
    submit_assessment,
)

from aicefr.asr.vad import EnergyVad
from aicefr.infra.blobs import LocalBlobStore, S3BlobStore, audio_response, key_of
from aicefr.storage.lesson_repository import LessonRepository

pytestmark = pytest.mark.integration


class MemoryBlobStore:
    """Object storage in a dict: no file to hand out, like S3."""

    name = "memory"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self.objects[key] = data
        return key

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def local_path(self, key: str) -> Path | None:
        return None

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.objects

    def size(self, key: str) -> int | None:
        return len(self.objects[key]) if key in self.objects else None

    def keys(self) -> Iterator[str]:
        return iter(list(self.objects))


# ================================================================= adapters


def test_a_key_comes_out_of_a_key_or_an_old_full_path():
    assert key_of("abc.wav") == "abc.wav"
    assert key_of("/srv/uploads/abc.wav") == "abc.wav"
    assert key_of("uploads/abc.wav") == "abc.wav"
    assert key_of(None) is None and key_of("") is None


def test_the_local_store_lists_its_keys_but_not_an_upload_in_progress(tmp_path):
    store = LocalBlobStore(tmp_path / "up")
    store.put("a.wav", b"RIFF1234")
    (tmp_path / "up" / "b.part").write_bytes(b"RIFF")  # still being written
    old = tmp_path / "up" / "c.part"
    old.write_bytes(b"RIFF")
    os.utime(old, (time.time() - 7200, time.time() - 7200))  # abandoned two hours ago
    assert sorted(store.keys()) == ["a.wav", "c.part"]
    assert store.size("a.wav") == 8 and store.size("zz.wav") is None
    with pytest.raises(ValueError):
        store.put("../escape.wav", b"x")


def test_a_store_without_files_streams_the_bytes():
    store = MemoryBlobStore()
    store.put("r1.wav", b"RIFFbytes")
    response = audio_response(store, "r1.wav", "r1.wav")
    assert response.body == b"RIFFbytes"
    assert 'filename="r1.wav"' in response.headers["content-disposition"]
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as gone:
        audio_response(store, "nothing.wav", "x.wav")
    assert gone.value.status_code == 404


S3 = os.getenv("AICEFR_TEST_S3")


@pytest.mark.skipif(not S3, reason="AICEFR_TEST_S3 is not set")
def test_the_s3_store_keeps_lists_and_deletes_against_a_real_server():
    url = urlsplit(S3)
    store = S3BlobStore(
        f"aicefr-test-{uuid.uuid4().hex[:8]}",
        url.netloc.split("@")[-1],
        url.username or "",
        url.password or "",
        secure=url.scheme == "https",
    )
    assert store.put("r1.wav", b"RIFF" + b"x" * 100) == "r1.wav"
    assert store.exists("r1.wav") and store.size("r1.wav") == 104
    assert store.get("r1.wav").startswith(b"RIFF")
    assert store.local_path("r1.wav") is None
    assert list(store.keys()) == ["r1.wav"]
    store.delete("r1.wav")
    assert not store.exists("r1.wav") and store.size("r1.wav") is None
    with pytest.raises(ValueError):
        store.put("a/b.wav", b"x")


# ============================================================ the application on object storage


@pytest.fixture
def on_objects(tmp_path, monkeypatch):
    """The application with recordings in a store that has no local files."""
    store = MemoryBlobStore()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", KEYWORD_TEXT)
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    for module in (
        "aicefr.services.core.assessment.app",
        "aicefr.services.core.learning.app",
        "aicefr.services.speech.app",
    ):
        monkeypatch.setattr(f"{module}.blob_store", lambda _settings: store)
    from aicefr.api import main

    importlib.reload(main)
    main.store = store
    return main


def test_a_recording_lives_in_the_store_and_is_heard_from_it(on_objects):
    m = on_objects
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    key = m.repo.audio_path_of(rid)
    assert key == f"{rid}.wav" and m.store.exists(key)  # a key, not a path on disk
    assert not list(Path.cwd().rglob(key)), "no copy left on disk"
    assert m.repo.status_of(rid)["status"] != "FAILED"  # the speech service read it from the store
    heard = student.get(f"/api/v1/responses/{rid}/audio")
    assert heard.status_code == 200 and heard.content.startswith(b"RIFF")


def test_erasing_a_response_deletes_its_object(on_objects):
    m = on_objects
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    assert student.delete(f"/api/v1/responses/{rid}").status_code in (200, 204)
    assert not m.store.exists(f"{rid}.wav")
    assert student.get(f"/api/v1/responses/{rid}/audio").status_code == 404


def test_retention_and_the_orphan_sweep_work_on_the_store(on_objects):
    from aicefr.retention import apply_retention, orphaned_recordings

    m = on_objects
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    m.store.put("stray.wav", b"RIFF")  # a recording nothing points at
    assert [p.name for p in orphaned_recordings(m.repo)] == ["stray.wav"]

    preview = apply_retention(m.repo, days=-1, dry_run=True)
    assert preview.audio_deleted == 1 and m.store.exists(f"{rid}.wav")
    apply_retention(m.repo, days=-1, dry_run=False)
    assert not m.store.exists(f"{rid}.wav")
    assert m.repo.audio_path_of(rid) is None


# ================================================================= the learning part's own database


def test_the_learning_part_writes_its_own_database_and_is_erased_there(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", KEYWORD_TEXT)
    learning_db = str(tmp_path / "learning.db")
    monkeypatch.setenv("AICEFR_LEARNING_DB", learning_db)
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    student = login_as(main, "SV-001")
    record(student, SAMPLE, KEYWORDS)
    who = account_id(main, "SV-001")
    core_db = main.settings.store("core")
    assert core_db != learning_db
    assert LessonRepository(learning_db, seed=False).count_attempts(who) == 1
    assert LessonRepository(core_db, seed=False).count_attempts(who) == 0

    admin = login_as(main, "QT-01", "admin")
    erased = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert erased.status_code == 200 and erased.json()["lesson_attempts"] == 1
    assert LessonRepository(learning_db, seed=False).count_attempts(who) == 0
