"""API layer tests. Cross-reference section 6 of the SDD."""

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

PASSWORD = "matkhau-check-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Every test gets its own database instead of sharing one."""
    monkeypatch.chdir(tmp_path)
    import importlib

    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def _create_account(app, pseudonym: str, role: str) -> None:
    from aicefr.storage.auth_repository import Role

    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))


def _login_as(app, pseudonym: str, role: str) -> TestClient:
    """Return a client already logged in with the given role.

    Logging in through the real endpoint instead of setting the cookie by hand, so that
    a broken login flow breaks these tests too rather than being quietly bypassed.
    """
    _create_account(app, pseudonym, role)
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def client(app):
    """Client logged in as a student. The default for most tests."""
    return _login_as(app, "SV-001", "student")


@pytest.fixture
def client_teacher(app):
    """Client logged in as a teacher."""
    return _login_as(app, "GV-01", "teacher")


@pytest.fixture
def client_admin(app):
    """Client logged in as an administrator."""
    return _login_as(app, "QT-01", "admin")


@pytest.fixture
def client_anonymous(app):
    """Client that has not logged in."""
    return TestClient(app)


def wav_bytes(seconds: float = 20.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, pcm, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def submit(client, speaker="SV-001", seconds=20.0):
    return client.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", wav_bytes(seconds), "audio/wav")},
        data={"speaker_id": speaker, "task_id": "P3"},
    )


def test_home_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Nộp bài nói" in r.text
    assert "Không cấp chứng chỉ" in r.text


def test_health_reports_model_version(client):
    d = client.get("/api/v1/health").json()
    assert d["status"] == "ok"
    assert d["model_version"] == "ridge_resp_v2"
    assert "mot bai noi" in d["unit_of_inference"]


def test_submit_returns_202_and_queued_status(client):
    """AC-05.1: accepting a response returns 202 with status QUEUED, it does not wait
    until scoring is finished.

    TestClient runs the background task right after the response is returned, so the
    later tests can still read the final result.
    """
    r = submit(client)
    assert r.status_code == 202
    d = r.json()
    assert len(d["response_id"]) == 12
    assert d["status"] == "QUEUED"
    assert "đang xử lý" in d["message"]


def test_read_back_just_submitted_report(client):
    rid = submit(client).json()["response_id"]
    d = client.get(f"/api/v1/responses/{rid}").json()
    assert d["response_id"] == rid
    assert d["qc"] is not None


def test_missing_response_returns_404(client):
    assert client.get("/api/v1/responses/khongcothat").status_code == 404


@pytest.mark.parametrize(
    "bad_id",
    ["MSSV21110001", "an.nguyen@gmail.com", "sdt0912345678", "21110001", "<svg onload=x>"],
)
def test_real_identifiers_rejected_when_the_account_is_created(app, bad_id):
    """The rule belongs where a pseudonym is created, not where one is submitted.

    It used to run on a form field at submission time. That was the wrong place
    twice over: a bad pseudonym could already exist in the account table, and a
    student could submit under somebody else's pseudonym because the field was
    theirs to fill in.
    """
    from aicefr.storage.auth_repository import Role

    with pytest.raises(ValueError):
        app.state.auth_repo.create_account(bad_id, PASSWORD, Role.STUDENT)


def test_submission_takes_the_pseudonym_from_the_session(app):
    """A student cannot submit under another student's pseudonym."""
    client = _login_as(app, "SV-001", "student")
    rid = submit(client).json()["response_id"]
    rows = client.get("/api/v1/me/responses").json()
    assert [r["response_id"] for r in rows] == [rid]
    assert rows[0]["speaker_id"] == "SV-001"


def test_non_audio_file_rejected(client):
    r = client.post(
        "/api/v1/responses",
        files={"audio": ("a.wav", b"day khong phai audio", "audio/wav")},
        data={"speaker_id": "SV-002", "task_id": "P3"},
    )
    assert r.status_code == 415


def test_queue_holds_only_responses_needing_review(app):
    client = _login_as(app, "SV-001", "student")
    submit(client)
    teacher = _login_as(app, "GV-01", "teacher")
    for item in teacher.get("/api/v1/review/queue").json():
        assert item["status"] == "REVIEW_REQUIRED"


def test_teacher_must_give_a_reason(app):
    rid = submit(_login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = _login_as(app, "GV-01", "teacher")
    r = teacher.post(f"/api/v1/review/{rid}", json={"reason": "ok"})
    assert r.status_code == 422  # reason shorter than 5 characters


def test_invalid_band_rejected(app):
    rid = submit(_login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = _login_as(app, "GV-01", "teacher")
    r = teacher.post(
        f"/api/v1/review/{rid}",
        json={"new_band": "D1", "reason": "thu band ngoai pham vi"},
    )
    assert r.status_code == 422


def test_stats_and_audit_endpoints_work(app):
    submit(_login_as(app, "SV-001", "student"))
    admin = _login_as(app, "QT-01", "admin")
    s = admin.get("/api/v1/stats").json()
    assert s["total"] >= 1
    assert admin.get("/api/v1/audit").status_code == 200


def test_queue_and_report_pages_render(client_teacher):
    client = client_teacher
    assert "Hàng đợi chờ duyệt" in client.get("/review").text
    assert "abc123" in client.get("/report/abc123").text


def test_the_database_and_upload_paths_come_from_the_environment(tmp_path, monkeypatch) -> None:
    """AICEFR_DB va AICEFR_UPLOADS phai thuc su duoc dung.

    Ca hai co trong config.py va trong huong dan chay localhost, nhung main.py
    ghi cung "aicefr.db": chay thu voi mot CSDL rieng van ghi vao CSDL that.
    """
    import importlib

    from aicefr import config
    from aicefr.api import main as m

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AICEFR_CORE_DB", raising=False)  # AICEFR_DB, then
    monkeypatch.setenv("AICEFR_DB", str(tmp_path / "rieng" / "test.db"))
    monkeypatch.setenv("AICEFR_UPLOADS", str(tmp_path / "rieng" / "up"))
    (tmp_path / "rieng").mkdir()
    config.get_settings.cache_clear()
    try:
        importlib.reload(m)
        assert m.repo.db_path == str(tmp_path / "rieng" / "test.db")
        from aicefr.services.core.assessment.context import svc as assessment

        assert assessment().tasks.db_path == m.repo.db_path
        # D043: a service with no store of its own uses the shared one.
        assert m.app.state.auth_repo.db_path == m.settings.store("core")
        assert m.settings.upload_dir == tmp_path / "rieng" / "up"
        assert not (tmp_path / "aicefr.db").exists()
    finally:
        config.get_settings.cache_clear()


def test_the_fake_engine_can_be_steered_from_the_environment(monkeypatch) -> None:
    import numpy as np

    from aicefr.services.speech.worker import fake_engine_from_env

    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", "hello there my friend")
    monkeypatch.setenv("AICEFR_FAKE_LANGUAGE", "vi:0.95")
    t = fake_engine_from_env().transcribe(np.zeros(16_000, dtype=np.float32), 16_000)
    assert t.text == "hello there my friend"
    assert (t.language, t.language_probability) == ("vi", 0.95)

    monkeypatch.delenv("AICEFR_FAKE_TRANSCRIPT")
    monkeypatch.delenv("AICEFR_FAKE_LANGUAGE")
    t = fake_engine_from_env().transcribe(np.zeros(16_000, dtype=np.float32), 16_000)
    assert t.language is None and len(t.text.split()) == 24


def test_a_malformed_fake_language_is_ignored_not_fatal(monkeypatch) -> None:
    import numpy as np

    from aicefr.services.speech.worker import fake_engine_from_env

    monkeypatch.setenv("AICEFR_FAKE_LANGUAGE", "vi:cao")
    t = fake_engine_from_env().transcribe(np.zeros(16_000, dtype=np.float32), 16_000)
    assert t.language is None
