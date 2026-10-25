from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode

from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.auth.service import AuthorizationError, AuthService, ConsentService
from aicefr.contracts import CURRENT_CONSENT_VERSION, ActorRole
from aicefr.local.app import SQLiteSessionRepository
from aicefr.storage.sqlite import SQLiteStore


class _StudentBoundary:
    def submit(self, token, request):  # pragma: no cover - unrelated route
        raise AssertionError("no submission expected")


def _request(app, method, path, *, body=b"", cookie="", headers=None, content_type=""):
    captured = {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_COOKIE": cookie,
        "HTTP_HOST": "127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
    }
    environ.update(headers or {})

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    captured["body"] = b"".join(app(environ, start_response))
    return captured


def test_login_consent_and_logout_revoke_persistent_session(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    auth = AuthService(store, SQLiteSessionRepository(store))
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "fixture-password")
    consents = ConsentService(store)
    app = StudentTeacherApp(
        StudentApi(_StudentBoundary()),
        auth=auth,
        consents=consents,
        consent_version=CURRENT_CONSENT_VERSION,
    )

    login = _request(
        app,
        "POST",
        "/login",
        body=urlencode({"actor_id": "fixture-student", "password": "fixture-password"}).encode(),
        content_type="application/x-www-form-urlencoded",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
    )
    assert login["status"].startswith("303")
    cookie = login["headers"]["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Path=/" in cookie
    token = cookie.split(";", 1)[0].split("=", 1)[1]
    assert auth.resolve(token).actor_id == "fixture-student"
    consents.activate(
        auth.resolve(token), "consent-v1", research_allowed=True, audio_storage_allowed=True
    )
    store.close()
    store = SQLiteStore(tmp_path / "data")
    auth = AuthService(store, SQLiteSessionRepository(store))
    consents = ConsentService(store)
    app = StudentTeacherApp(
        StudentApi(_StudentBoundary()),
        auth=auth,
        consents=consents,
        consent_version=CURRENT_CONSENT_VERSION,
    )
    assert auth.resolve(token).actor_id == "fixture-student"

    page = _request(app, "GET", "/student/consent", cookie=f"aicefr_session={token}")
    assert page["status"].startswith("200")
    assert "chưa lưu lựa chọn" in page["body"].decode()
    page_body = page["body"].decode()
    assert 'name="audio_storage_allowed"' in page_body
    assert 'name="research_allowed"' in page_body
    assert 'value="true"\nchecked' not in page_body
    assert "Thời hạn lưu/xóa chưa được chốt" in page["body"].decode()
    assert 'href="/static/consent-v2.pdf"' in page["body"].decode()
    pdf = _request(app, "GET", "/static/consent-v2.pdf")
    assert pdf["status"].startswith("200")
    assert pdf["headers"]["Content-Type"] == "application/pdf"
    assert pdf["body"].startswith(b"%PDF-")
    unanswered = _request(
        app,
        "POST",
        "/student/consent/accept",
        cookie=f"aicefr_session={token}",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
    )
    assert unanswered["status"].startswith("303")
    unanswered_record = consents.current(auth.resolve(token))
    assert unanswered_record.research_allowed is False
    assert unanswered_record.audio_storage_allowed is False
    accepted = _request(
        app,
        "POST",
        "/student/consent/accept",
        body=urlencode(
            {"audio_storage_allowed": "true", "research_allowed": "false"}
        ).encode(),
        cookie=f"aicefr_session={token}",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
        content_type="application/x-www-form-urlencoded",
    )
    assert accepted["status"].startswith("303")
    active = consents.current(auth.resolve(token))
    assert active.consent_version == CURRENT_CONSENT_VERSION
    assert active.audio_storage_allowed is True
    assert active.research_allowed is False

    withdrawn = _request(
        app,
        "POST",
        "/student/consent/withdraw",
        cookie=f"aicefr_session={token}",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
    )
    assert withdrawn["status"].startswith("303")
    assert consents.current(auth.resolve(token)).state.value == "withdrawn"
    logged_out = _request(
        app,
        "POST",
        "/logout",
        cookie=f"aicefr_session={token}",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
    )
    assert logged_out["status"].startswith("303")
    assert "Max-Age=0" in logged_out["headers"]["Set-Cookie"]
    try:
        auth.resolve(token)
    except AuthorizationError:
        pass
    else:  # pragma: no cover - explicit negative assertion
        raise AssertionError("logout must revoke the server-side session")
    store.close()


def test_cookie_unsafe_route_requires_same_origin_and_login_error_is_generic(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    auth = AuthService(store, SQLiteSessionRepository(store))
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "fixture-password")
    app = StudentTeacherApp(
        StudentApi(_StudentBoundary()), auth=auth, consents=ConsentService(store)
    )
    denied = _request(
        app,
        "POST",
        "/login",
        body=b"actor_id=fixture-student&password=fixture-password",
        content_type="application/x-www-form-urlencoded",
        headers={"HTTP_ORIGIN": "https://attacker.invalid"},
    )
    assert denied["status"].startswith("403")
    rebound = _request(
        app,
        "POST",
        "/login",
        body=b"actor_id=fixture-student&password=fixture-password",
        content_type="application/x-www-form-urlencoded",
        headers={"HTTP_HOST": "evil.example", "HTTP_ORIGIN": "http://evil.example"},
    )
    assert rebound["status"].startswith("403")
    failed = _request(
        app,
        "POST",
        "/login",
        body=b"actor_id=fixture-missing&password=secret-value",
        content_type="application/x-www-form-urlencoded",
        headers={"HTTP_ORIGIN": "http://127.0.0.1:8000"},
    )
    assert failed["status"].startswith("401")
    body = failed["body"].decode()
    assert "secret-value" not in body and "fixture-missing" not in body
    store.close()
