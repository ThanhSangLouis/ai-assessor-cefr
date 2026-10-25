from __future__ import annotations

import pytest

from aicefr.api.student import (
    AllowlistedTaskAccess,
    StudentService,
    SubmitRequest,
    UploadPolicy,
)
from aicefr.auth.service import AuthorizationError, AuthService, ConsentService
from aicefr.contracts import ActorRole
from aicefr.local.app import SQLiteSessionRepository
from aicefr.report.service import MemoryReportRepository
from aicefr.storage.blob import BlobStore
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


def test_withdrawn_consent_blocks_new_submission_before_blob_write(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    auth = AuthService(store, SQLiteSessionRepository(store))
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "fixture-password")
    token = auth.login("fixture-student", "fixture-password")
    actor = auth.resolve(token)
    consent = ConsentService(store)
    responses = ResponseService(store, BlobStore(store.data_dir, max_bytes=1000), consent)
    student = StudentService(
        auth,
        responses,
        MemoryReportRepository(),
        UploadPolicy(allowed_media_types=frozenset({"audio/wav"}), max_bytes=1000),
        AllowlistedTaskAccess(frozenset({("demo-task", "1")})),
    )
    request = SubmitRequest(
        task_id="demo-task",
        task_version="1",
        consent_version="v1",
        filename="sample.wav",
        content_type="audio/wav",
        audio_bytes=b"generated fixture bytes",
    )
    consent.activate(actor, "v1", audio_storage_allowed=True)
    submitted = student.submit(token, request)
    assert store.get_response(submitted.response_id) is not None
    blobs_before = set(responses.metadata.referenced_blob_ids())

    consent.withdraw(actor)
    with pytest.raises(AuthorizationError):
        student.submit(token, request)
    assert set(responses.metadata.referenced_blob_ids()) == blobs_before
    assert len(list(responses.blobs.root.iterdir())) == 1
    store.close()
