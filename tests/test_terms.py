"""The terms of use (FR-01, D058), which replaced the research consent form.

A recording is personal data: nothing of a learner's voice is stored before
they accept the terms, and the check runs before the upload touches the disk.
Accepting is one step, kept with its first date. Research use (blind rating,
the feedback study, the research export) covers exactly the accounts that
accepted.
"""

from __future__ import annotations

import importlib
import io
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def _client(app, pseudonym: str = "SV-001", role: str = "student") -> TestClient:
    """Logged in, deliberately WITHOUT accepting the terms."""
    from aicefr.storage.auth_repository import Role

    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def _wav(seconds: float = 35.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, pcm, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _submit(client: TestClient):
    return client.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", _wav(), "audio/wav")},
        data={"task_id": "P3"},
    )


def test_without_the_terms_a_submission_is_refused_and_nothing_is_written(app, tmp_path) -> None:
    c = _client(app)
    r = _submit(c)
    assert r.status_code == 403
    assert "TERMS_NOT_ACCEPTED" in r.text
    uploads = Path(tmp_path) / "uploads"
    assert not uploads.exists() or not list(uploads.iterdir())


def test_after_accepting_the_terms_a_submission_is_queued(app) -> None:
    c = _client(app)
    state = c.post("/api/v1/me/terms").json()
    assert state["accepted"] is True and state["may_submit"] is True
    r = _submit(c)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "QUEUED"


def test_the_state_says_whether_and_when_the_terms_were_accepted(app) -> None:
    c = _client(app)
    before = c.get("/api/v1/me/terms").json()
    assert before == {
        "accepted": False,
        "accepted_at": None,
        "may_submit": False,
        "role": "student",
    }
    c.post("/api/v1/me/terms")
    after = c.get("/api/v1/me/terms").json()
    assert after["accepted"] is True and after["accepted_at"]


def test_accepting_again_keeps_the_first_date_and_audits_once(app) -> None:
    c = _client(app)
    first = c.post("/api/v1/me/terms").json()["accepted_at"]
    second = c.post("/api/v1/me/terms").json()["accepted_at"]
    assert first == second
    admin = _client(app, "QT-01", "admin")
    actions = [e["action"] for e in admin.get("/api/v1/audit").json()]
    assert actions.count("terms.accept") == 1


def test_research_use_covers_the_accounts_that_accepted(app) -> None:
    accepted, other = _client(app, "SV-001"), _client(app, "SV-002")
    accepted.post("/api/v1/me/terms")
    assert _submit(accepted).status_code == 202
    assert _submit(other).status_code == 403

    admin = _client(app, "QT-01", "admin")
    body = admin.get("/api/v1/admin/export/research.json").json()
    assert body["accounts_with_terms"] == 1 and body["row_count"] == 1
    # The export answers "does the machine agree with the raters": numbers, no words.
    assert all("transcript" not in row for row in body["rows"])


def test_the_terms_page_and_the_old_consent_address(app) -> None:
    c = _client(app)
    page = c.get("/terms")
    assert page.status_code == 200 and "Điều khoản sử dụng" in page.text
    old = c.get("/consent", follow_redirects=False)
    assert old.status_code == 301 and old.headers["location"] == "/terms"


def test_migration_turns_a_standing_signature_into_accepted_terms(tmp_path) -> None:
    """D058: who could submit before need not accept again; a withdrawn signature does not count."""
    from aicefr.storage import migrations
    from aicefr.storage.auth_repository import AuthRepository, Role
    from aicefr.storage.db import database

    store = str(tmp_path / "old.db")
    auth = AuthRepository(store)
    signed = auth.create_account("SV-001", PASSWORD, Role.STUDENT)
    withdrawn = auth.create_account("SV-002", PASSWORD, Role.STUDENT)
    refused_audio = auth.create_account("SV-003", PASSWORD, Role.STUDENT)
    db = database(store)
    migrations.migrate(store)
    # A store from before D058: version 6 not applied yet, signatures on file.
    db["schema_migrations"].delete_many({"version": 6})
    db["consent"].insert_many(
        [
            {
                "account_id": signed,
                "audio_storage_allowed": 1,
                "signed_at": "2026-10-01T00:00:00+00:00",
                "withdrawn_at": None,
            },
            {
                "account_id": withdrawn,
                "audio_storage_allowed": 1,
                "signed_at": "2026-10-02T00:00:00+00:00",
                "withdrawn_at": "2026-10-03T00:00:00+00:00",
            },
            {
                "account_id": refused_audio,
                "audio_storage_allowed": 0,
                "signed_at": "2026-10-04T00:00:00+00:00",
                "withdrawn_at": None,
            },
        ]
    )

    assert migrations.migrate(store) == [6]

    assert auth.get(signed)["terms_accepted_at"] == "2026-10-01T00:00:00+00:00"
    assert auth.get(withdrawn)["terms_accepted_at"] is None
    assert auth.get(refused_audio)["terms_accepted_at"] is None
    assert "consent" not in db.list_collection_names()
