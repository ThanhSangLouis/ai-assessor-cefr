"""Authentication and authorization tests. Cross-reference FR-32, NFR-07, FR-04.

Before iteration 2, /review and POST /api/v1/review/{id} were wide open: anyone who
knew the path could change scores and set teacher_verified. The tests here keep that
bug from coming back.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from aicefr.auth import passwords
from aicefr.auth.sessions import COOKIE_NAME
from aicefr.storage.auth_repository import MAX_FAILED_ATTEMPTS, Role

PASSWORD = "matkhau-check-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib

    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def make_account(app, pseudonym: str, role: str) -> None:
    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))


def login_as(app, pseudonym: str, role: str) -> TestClient:
    make_account(app, pseudonym, role)
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    # FR-01 (D058): recording requires the terms of use. Accepted through the real
    # endpoint so the fixtures walk the same path as a student.
    assert c.post("/api/v1/me/terms").status_code == 200
    return c


def wav(seconds: float = 40.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


def submit(c, speaker="SV-001"):
    return c.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", wav(), "audio/wav")},
        data={"speaker_id": speaker, "task_id": "P3"},
    )


# ---------- password hashing ----------


def test_hash_uses_bcrypt_cost_12_prefix() -> None:
    """NFR-07: bcrypt cost >= 12, the testable criterion is the $2b$12$ prefix."""
    assert passwords.hash_password("matkhau").startswith("$2b$12$")


def test_same_password_hashes_differently_each_time() -> None:
    """Every hash carries its own salt. Two identical hashes would mean no salt."""
    assert passwords.hash_password(PASSWORD) != passwords.hash_password(PASSWORD)


def test_corrupt_hash_does_not_crash_app() -> None:
    assert passwords.verify_password(PASSWORD, "khong-phai-hash") is False


# ---------- access control ----------


TEACHER_ENDPOINTS = ["/api/v1/review/queue"]
ADMIN_ENDPOINTS = ["/api/v1/responses", "/api/v1/stats", "/api/v1/audit"]


@pytest.mark.parametrize("url", TEACHER_ENDPOINTS + ADMIN_ENDPOINTS)
def test_anonymous_is_blocked(app, url: str) -> None:
    assert TestClient(app).get(url).status_code == 401


@pytest.mark.parametrize("url", TEACHER_ENDPOINTS + ADMIN_ENDPOINTS)
def test_student_cannot_reach_teacher_endpoints(app, url: str) -> None:
    assert login_as(app, "SV-001", "student").get(url).status_code == 403


@pytest.mark.parametrize("url", ADMIN_ENDPOINTS)
def test_teacher_cannot_reach_admin_endpoints(app, url: str) -> None:
    assert login_as(app, "GV-01", "teacher").get(url).status_code == 403


def test_student_cannot_review_a_response(app) -> None:
    """The crux: without this layer, teacher_verified means nothing."""
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    r = student.post(f"/api/v1/review/{rid}", json={"reason": "tu duyet bai cua chinh minh"})
    assert r.status_code == 403


def test_anonymous_cannot_submit(app) -> None:
    assert submit(TestClient(app)).status_code == 401


# ---------- who may read a response ----------


def test_another_users_response_returns_404_not_403(app) -> None:
    """FR-04: a 403 would confirm that the response exists, which still leaks information."""
    a = login_as(app, "SV-001", "student")
    rid = submit(a).json()["response_id"]
    b = login_as(app, "SV-002", "student")
    assert b.get(f"/api/v1/responses/{rid}").status_code == 404


def test_owner_can_view_own_response(app) -> None:
    a = login_as(app, "SV-001", "student")
    rid = submit(a).json()["response_id"]
    assert a.get(f"/api/v1/responses/{rid}").status_code == 200


def test_teacher_can_view_any_response(app) -> None:
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 200


def test_my_responses_lists_only_own_responses(app) -> None:
    a = login_as(app, "SV-001", "student")
    submit(a)
    b = login_as(app, "SV-002", "student")
    assert b.get("/api/v1/me/responses").json() == []
    assert len(a.get("/api/v1/me/responses").json()) == 1


# ---------- sessions ----------


def test_session_cookie_has_httponly_and_samesite(app) -> None:
    """NFR-07: HttpOnly stops JavaScript from reading the cookie, SameSite blocks basic CSRF."""
    make_account(app, "SV-001", "student")
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD})
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_logout_invalidates_old_cookie_immediately(app) -> None:
    """AC-32.4. This is exactly why server-side sessions were chosen over JWT."""
    c = login_as(app, "SV-001", "student")
    token = c.cookies[COOKIE_NAME]
    assert c.get("/api/v1/me").status_code == 200
    c.post("/api/v1/auth/logout")

    fresh_client = TestClient(app)
    fresh_client.cookies.set(COOKIE_NAME, token)
    assert fresh_client.get("/api/v1/me").status_code == 401


def test_forged_session_token_rejected(app) -> None:
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, "ma-tu-bia-ra")
    assert c.get("/api/v1/me").status_code == 401


def test_database_never_stores_raw_session_token(app) -> None:
    """Only the hash of the session token is stored. A leaked database copy therefore
    lets nobody impersonate any session."""
    c = login_as(app, "SV-001", "student")
    token = c.cookies[COOKIE_NAME]
    stored_hashes = [r["token_hash"] for r in app.state.auth_repo.col("auth_sessions").find()]
    assert token not in stored_hashes
    assert len(stored_hashes) == 1


# ---------- account lockout ----------


def test_repeated_wrong_password_locks_and_returns_429(app) -> None:
    """NFR-07: lock for 15 minutes after 5 failures, the 6th attempt returns HTTP 429."""
    make_account(app, "SV-001", "student")
    c = TestClient(app)
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert (
            c.post(
                "/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai"}
            ).status_code
            == 401
        )
    r = c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai"})
    assert r.status_code == 429


def test_locked_account_rejects_even_correct_password(app) -> None:
    make_account(app, "SV-001", "student")
    c = TestClient(app)
    for _ in range(MAX_FAILED_ATTEMPTS):
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai"})
    r = c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD})
    assert r.status_code == 429


def test_successful_login_clears_failure_count(app) -> None:
    make_account(app, "SV-001", "student")
    c = TestClient(app)
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai"})
    assert (
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD}).status_code
        == 200
    )
    assert app.state.auth_repo.get_by_pseudonym("SV-001")["failed_attempts"] == 0


def test_error_does_not_distinguish_unknown_user_from_wrong_password(app) -> None:
    """Telling the two cases apart would leak which accounts actually exist."""
    make_account(app, "SV-001", "student")
    c = TestClient(app)
    a = c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai"})
    b = c.post("/api/v1/auth/login", json={"pseudonym": "khong-ton-tai", "password": "sai"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


# ---------- audit log ----------


def test_audit_records_real_reviewer_account(app) -> None:
    """Before iteration 2 the reviewer identity was self-declared by the client, so the
    audit log could not prove who had changed a score."""
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    teacher.post(f"/api/v1/review/{rid}", json={"reason": "nghe lai thay phat am ro hon"})

    admin = login_as(app, "QT-01", "admin")
    entries = admin.get("/api/v1/audit").json()
    assert entries, "there must be at least one audit entry"
    teacher_id = app.state.auth_repo.get_by_pseudonym("GV-01")["account_id"]
    assert any(e["actor_id"] == teacher_id for e in entries)


# ---------- background processing ----------


def test_response_finishes_after_202(app) -> None:
    """Once the background task has finished, the status must have left QUEUED."""
    student = login_as(app, "SV-001", "student")
    r = submit(student)
    assert r.status_code == 202
    state = student.get(f"/api/v1/responses/{r.json()['response_id']}/status").json()
    assert state["status"] in {"COMPLETED", "REVIEW_REQUIRED", "REJECTED", "FAILED"}
    assert state["is_pending"] is False


def test_another_users_status_returns_404(app) -> None:
    a = login_as(app, "SV-001", "student")
    rid = submit(a).json()["response_id"]
    b = login_as(app, "SV-002", "student")
    assert b.get(f"/api/v1/responses/{rid}/status").status_code == 404


def test_stuck_running_response_marked_failed(app, monkeypatch) -> None:
    """NFR-11: if the process dies halfway, a response must not sit in RUNNING forever."""
    from aicefr.api import main as m
    from aicefr.contracts import Response, Status

    m.repo.save(
        Response(response_id="ket001", status=Status.RUNNING, config_version="v1"),
        "SV-001",
        "P3",
    )
    # The response was just created and is not overdue yet; call with a 0-minute
    # deadline to simulate an old one.
    stuck = m.repo.fail_stuck(minutes=0)
    assert "ket001" in stuck
    assert m.repo.status_of("ket001")["status"] == "FAILED"


# ---------- replaying a recording ----------


def test_owner_can_replay_audio(app) -> None:
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    r = student.get(f"/api/v1/responses/{rid}/audio")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/")


def test_audio_supports_range_for_seeking(app) -> None:
    """FR-24 requires that clicking a piece of evidence jumps the player to the right
    timestamp."""
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    r = student.get(f"/api/v1/responses/{rid}/audio", headers={"Range": "bytes=0-1023"})
    assert r.status_code == 206
    assert len(r.content) == 1024


def test_another_users_audio_returns_404(app) -> None:
    """Audio must not become a detour to data that the report itself already blocks.

    A voice identifies the person, so this is personal data even more sensitive than
    the transcript.
    """
    a = login_as(app, "SV-001", "student")
    rid = submit(a).json()["response_id"]
    b = login_as(app, "SV-002", "student")
    assert b.get(f"/api/v1/responses/{rid}/audio").status_code == 404


def test_teacher_can_replay_any_response(app) -> None:
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    assert teacher.get(f"/api/v1/responses/{rid}/audio").status_code == 200


def test_does_not_leak_filesystem_path(app) -> None:
    """The returned filename follows the response id, not the original name, and does
    not reveal the directory."""
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    cd = student.get(f"/api/v1/responses/{rid}/audio").headers.get("content-disposition", "")
    assert rid in cd
    assert "uploads" not in cd


# ---------- review lock (FR-29) ----------


def test_second_teacher_cannot_lock_a_held_response(app) -> None:
    """Without a lock, two teachers overwrite each other's decision and nobody notices."""
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    a = login_as(app, "GV-01", "teacher")
    b = login_as(app, "GV-02", "teacher")
    assert a.post(f"/api/v1/review/{rid}/lock").status_code == 200
    r = b.post(f"/api/v1/review/{rid}/lock")
    assert r.status_code == 409
    assert "GV-01" in r.json()["detail"]


def test_non_holder_cannot_save(app) -> None:
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    a = login_as(app, "GV-01", "teacher")
    b = login_as(app, "GV-02", "teacher")
    a.post(f"/api/v1/review/{rid}/lock")
    r = b.post(f"/api/v1/review/{rid}", json={"reason": "thu ghi de quyet dinh nguoi khac"})
    assert r.status_code == 409


def test_saving_releases_lock_for_others(app) -> None:
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    a = login_as(app, "GV-01", "teacher")
    a.post(f"/api/v1/review/{rid}/lock")
    a.post(f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"})
    b = login_as(app, "GV-02", "teacher")
    assert b.post(f"/api/v1/review/{rid}/lock").status_code == 200


def test_expired_lock_can_be_reclaimed(app) -> None:
    """A teacher closing the review screen halfway must not leave a response stuck forever."""
    from aicefr.api import main as m

    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    granted, _ = m.repo.lock_response(rid, "gv-cu", "GV-CU", minutes=-1)  # lock already expired
    assert granted
    assert m.repo.locked_by(rid) is None, "an expired lock counts as held by nobody"
    b = login_as(app, "GV-02", "teacher")
    assert b.post(f"/api/v1/review/{rid}/lock").status_code == 200


def test_queue_shows_who_is_reviewing(app) -> None:
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    a = login_as(app, "GV-01", "teacher")
    a.post(f"/api/v1/review/{rid}/lock")
    b = login_as(app, "GV-02", "teacher")
    queue_items = b.get("/api/v1/review/queue").json()
    item = next((x for x in queue_items if x["response_id"] == rid), None)
    if item is not None:
        assert item["locked_by"] == "GV-01"


def test_history_records_before_and_after_values(app) -> None:
    """FR-31: the history must hold the old value, the new value, the reason and the actor."""
    rid = submit(login_as(app, "SV-001", "student")).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    teacher.post(
        f"/api/v1/review/{rid}",
        json={"new_score": 3.5, "new_band": "B1", "reason": "phat am ro hon may danh gia"},
    )
    history = teacher.get(f"/api/v1/responses/{rid}/history").json()
    assert len(history) == 1
    assert history[0]["new_score"] == 3.5
    assert history[0]["new_band"] == "B1"
    assert "phat am" in history[0]["reason"]


def test_student_cannot_read_review_history(app) -> None:
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    assert student.get(f"/api/v1/responses/{rid}/history").status_code == 403
