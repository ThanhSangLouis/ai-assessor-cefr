from __future__ import annotations

import hashlib
import json
from io import BytesIO

from aicefr.api.identity import IdentityApi
from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp, _coarse_device_category
from aicefr.auth.accounts import AccountService
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole
from aicefr.local.__main__ import SafeAccessLogHandler
from aicefr.local.app import SQLiteSessionRepository
from aicefr.portal.router import PortalRouter
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore


class _NoStudentApi:
    def submit(self, token, request):  # pragma: no cover
        raise AssertionError("student routes are outside this test")


def _call(
    app,
    path,
    *,
    method="GET",
    token=None,
    body=None,
    origin=True,
    query="",
    scheme="http",
    host="localhost:8000",
    user_agent=None,
):
    raw = json.dumps(body).encode() if body is not None else b""
    result: dict[str, object] = {}
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(raw)),
        "CONTENT_TYPE": "application/json" if body is not None else "",
        "HTTP_COOKIE": (
            f"{'__Host-aicefr_session' if scheme == 'https' else 'aicefr_session'}={token}"
            if token
            else ""
        ),
        "HTTP_HOST": host,
        "HTTP_USER_AGENT": user_agent or "",
        "HTTP_ORIGIN": f"{scheme}://{host}" if origin else "",
        "wsgi.url_scheme": scheme,
        "wsgi.input": BytesIO(raw),
    }

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = headers

    response_body = b"".join(app(env, start_response))
    headers = dict(result["headers"])
    return str(result["status"]), headers, response_body


def _runtime(tmp_path):
    store = SQLiteStore(tmp_path / "identity-api")
    repository = IdentityRepository(store)
    auth = AuthService(
        store,
        SQLiteSessionRepository(store),
        identity_repository=repository,
    )
    accounts = AccountService(auth, repository)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "admin-pass-123")
    identity_api = IdentityApi(auth, accounts)
    portal = PortalRouter(None, None, None, None, identity_api)
    app = StudentTeacherApp(StudentApi(_NoStudentApi()), auth=auth, portal=portal)
    return store, auth, accounts, app


def test_admin_create_temp_account_password_rotation_and_gate(tmp_path):
    store, auth, _, app = _runtime(tmp_path)
    try:
        admin = auth.login("fixture-admin", "admin-pass-123")
        status, _, raw = _call(
            app,
            "/api/v1/admin/accounts",
            method="POST",
            token=admin,
            body={"accounts": [{"actor_id": "fixture-student-66", "role": "student", "goal": 3}]},
        )
        assert status.startswith("201")
        created = json.loads(raw)["accounts"][0]
        temporary_password = created["temporary_password"]
        assert "fixture-student-66" == created["actor"]["actor_id"]
        assert temporary_password in raw.decode()

        temp_token = auth.login("fixture-student-66", temporary_password)
        password_page_status, _, password_page = _call(app, "/password-change", token=temp_token)
        assert password_page_status.startswith("200")
        assert b'name="current_password"' in password_page
        assert b'name="new_password"' in password_page
        assert b'name="confirm_password"' in password_page
        safe_state, _, state_body = _call(app, "/api/v1/me", token=temp_token)
        assert safe_state.startswith("200")
        assert json.loads(state_body)["profile"]["temporary_password_required"] is True
        denied, _, denied_body = _call(app, "/api/v1/me/activity", token=temp_token)
        assert denied.startswith("403")
        assert json.loads(denied_body)["error"] == "PASSWORD_CHANGE_REQUIRED"

        no_origin, _, _ = _call(
            app,
            "/api/v1/me/password",
            method="POST",
            token=temp_token,
            body={
                "current_password": temporary_password,
                "new_password": "student-new-pass-456",
            },
            origin=False,
        )
        assert no_origin.startswith("403")

        rotated, headers, body = _call(
            app,
            "/api/v1/me/password",
            method="POST",
            token=temp_token,
            body={
                "current_password": temporary_password,
                "new_password": "student-new-pass-456",
            },
        )
        assert rotated.startswith("200")
        assert "aicefr_session=" in headers["Set-Cookie"]
        assert "HttpOnly" in headers["Set-Cookie"]
        assert temporary_password.encode() not in body
        new_token = headers["Set-Cookie"].split(";", 1)[0].split("=", 1)[1]

        allowed, _, me = _call(app, "/api/v1/me", token=new_token)
        assert allowed.startswith("200")
        payload = json.loads(me)
        assert payload["profile"]["actor_id"] == "fixture-student-66"
        assert len(payload["catalog"]["icons"]) == 15
        assert len(payload["catalog"]["colors"]) == 10
        assert payload["catalog"]["goals"] == [1, 2, 3, 5, 10]
        assert new_token.encode() not in me
    finally:
        store.close()


def test_identity_json_rejects_duplicate_fields_without_echoing_secret(tmp_path):
    store, auth, _, app = _runtime(tmp_path)
    try:
        token = auth.login("fixture-admin", "admin-pass-123")
        raw = b'{"accounts":[],"accounts":[{"password":"SENSITIVE"}]}'
        result: dict[str, object] = {}
        env = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/v1/admin/accounts",
            "QUERY_STRING": "",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "HTTP_COOKIE": f"aicefr_session={token}",
            "HTTP_HOST": "localhost:8000",
            "HTTP_ORIGIN": "http://localhost:8000",
            "wsgi.url_scheme": "http",
            "wsgi.input": BytesIO(raw),
        }

        def start_response(status, headers):
            result["status"] = status

        body = b"".join(app(env, start_response))
        assert str(result["status"]).startswith("400")
        assert b"SENSITIVE" not in body
    finally:
        store.close()


def test_google_callback_access_log_omits_path_query_and_credentials():
    messages: list[str] = []

    class Sink:
        command = "GET"
        requestline = "GET /auth/google/callback?code=provider-secret&state=state-secret HTTP/1.1"

        def log_message(self, format, *args):
            messages.append(format % args)

    SafeAccessLogHandler.log_request(Sink(), 302, 128)
    assert len(messages) == 1
    assert "302" in messages[0] and "128" in messages[0]
    assert "callback" not in messages[0]
    assert "provider-secret" not in messages[0]
    assert "state-secret" not in messages[0]


def test_identity_auth_matrix_foreign_sessions_self_guard_and_profile_allowlist(tmp_path):
    store, auth, accounts, app = _runtime(tmp_path)
    try:
        auth.bootstrap_fixture_account("fixture-student-a", ActorRole.STUDENT, "student-a-pass")
        auth.bootstrap_fixture_account("fixture-student-b", ActorRole.STUDENT, "student-b-pass")
        token_a = auth.login("fixture-student-a", "student-a-pass")
        token_b = auth.login("fixture-student-b", "student-b-pass")
        assert _call(app, "/api/v1/me")[0].startswith("401")

        non_admin, _, body = _call(
            app,
            "/api/v1/admin/accounts",
            method="POST",
            token=token_a,
            body={"accounts": [{"actor_id": "fixture-extra", "role": "student"}]},
        )
        assert non_admin.startswith("403")
        assert json.loads(body)["error"] == "ACCESS_DENIED"

        profile, _, profile_body = _call(
            app,
            "/api/v1/me/profile",
            method="PATCH",
            token=token_a,
            body={"email": "private@example.invalid"},
        )
        assert profile.startswith("422")
        assert b"private@example.invalid" not in profile_body

        foreign_id = accounts.list_sessions(token_b)[0].session_id
        foreign, _, foreign_body = _call(
            app,
            f"/api/v1/me/sessions/{foreign_id}",
            method="DELETE",
            token=token_a,
        )
        assert foreign.startswith("404")
        assert json.loads(foreign_body)["error"] == "RESOURCE_UNAVAILABLE"

        admin = auth.login("fixture-admin", "admin-pass-123")
        disabled, _, _ = _call(
            app,
            "/api/v1/admin/accounts/fixture-student-b/disable",
            method="POST",
            token=admin,
            body={},
        )
        assert disabled.startswith("200")
        listed, _, listed_body = _call(app, "/api/v1/admin/accounts", token=admin)
        assert listed.startswith("200")
        safe_accounts = json.loads(listed_body)["accounts"]
        assert (
            next(row for row in safe_accounts if row["actor_id"] == "fixture-student-b")["disabled"]
            is True
        )
        self_action, _, self_body = _call(
            app,
            "/api/v1/admin/accounts/fixture-admin/disable",
            method="POST",
            token=admin,
            body={},
        )
        assert self_action.startswith("409")
        assert json.loads(self_body)["error"] == "SELF_ACTION_PROHIBITED"
    finally:
        store.close()


def test_consent_activation_and_withdrawal_use_versioned_api(tmp_path):
    store, auth, _, app = _runtime(tmp_path)
    try:
        auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass-123")
        token = auth.login("fixture-student", "student-pass-123")
        before_events = store.connection.execute(
            "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-student'"
        ).fetchone()[0]
        accepted, _, accepted_body = _call(
            app,
            "/api/v1/me/consent",
            method="POST",
            token=token,
            body={"version": "consent-v1", "research_allowed": True},
        )
        assert accepted.startswith("200")
        assert json.loads(accepted_body)["state"] == "active"
        withdrawn, _, withdrawn_body = _call(
            app,
            "/api/v1/me/consent",
            method="POST",
            token=token,
            body={
                "version": "consent-v1",
                "research_allowed": False,
                "active": False,
            },
        )
        assert withdrawn.startswith("200")
        assert json.loads(withdrawn_body)["state"] == "withdrawn"
        assert (
            store.connection.execute(
                "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-student'"
            ).fetchone()[0]
            == before_events + 2
        )
    finally:
        store.close()


def test_login_lockout_uses429_without_echoing_credentials(tmp_path):
    store, _, _, app = _runtime(tmp_path)
    try:
        statuses = []
        for _ in range(5):
            status, _, body = _call(
                app,
                "/login",
                method="POST",
                body={"actor_id": "fixture-admin", "password": "wrong-secret"},
            )
            statuses.append(int(status.split()[0]))
            assert b"wrong-secret" not in body
        assert statuses[-1] == 429
    finally:
        store.close()


def test_https_login_and_rotation_use_host_cookie_without_http_fallback(tmp_path):
    store, auth, _, app = _runtime(tmp_path)
    try:
        auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass-123")
        raw_user_agent = (
            "Mozilla/5.0 (Linux; Android 14; Pixel-Secret-Device) "
            "AppleWebKit/537.36 Chrome/123.0 Mobile"
        )
        login_status, headers, _ = _call(
            app,
            "/login",
            method="POST",
            body={"actor_id": "fixture-student", "password": "student-pass-123"},
            scheme="https",
            host="localhost:8443",
            user_agent=raw_user_agent,
        )
        assert login_status.startswith("303")
        cookie = headers["Set-Cookie"]
        assert cookie.startswith("__Host-aicefr_session=")
        assert "Secure" in cookie and "HttpOnly" in cookie and "Path=/" in cookie
        token = cookie.split(";", 1)[0].split("=", 1)[1]
        sessions_status, _, sessions_body = _call(
            app,
            "/api/v1/me/sessions",
            token=token,
            scheme="https",
            host="localhost:8443",
        )
        assert sessions_status.startswith("200")
        session_payload = json.loads(sessions_body)
        current_session = next(item for item in session_payload["sessions"] if item["current"])
        assert current_session["device"] == "mobile"
        assert b"Pixel-Secret-Device" not in sessions_body
        assert raw_user_agent.encode() not in sessions_body
        assert token.encode() not in sessions_body
        assert b"student-pass-123" not in sessions_body
        assert hashlib.sha256(token.encode("ascii")).hexdigest().encode() not in sessions_body
        assert b"token_digest" not in sessions_body
        stored_device = store.connection.execute(
            "SELECT m.device FROM session_metadata m JOIN sessions s "
            "ON s.token_digest=m.token_digest WHERE s.actor_id='fixture-student'"
        ).fetchone()[0]
        assert stored_device == "mobile"
        assert _call(app, "/api/v1/me", token=token, scheme="https", host="localhost:8443")[
            0
        ].startswith("200")

        insecure_env = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/me",
            "QUERY_STRING": "",
            "CONTENT_LENGTH": "0",
            "CONTENT_TYPE": "",
            "HTTP_COOKIE": f"aicefr_session={token}",
            "HTTP_HOST": "localhost:8443",
            "wsgi.url_scheme": "https",
            "wsgi.input": BytesIO(),
        }
        captured: dict[str, object] = {}

        def start_response(status, headers):
            captured["status"] = status

        b"".join(app(insecure_env, start_response))
        assert str(captured["status"]).startswith("401")

        admin = auth.login("fixture-admin", "admin-pass-123")
        created_status, _, created_body = _call(
            app,
            "/api/v1/admin/accounts",
            method="POST",
            token=admin,
            body={"accounts": [{"actor_id": "fixture-temp", "role": "student"}]},
        )
        assert created_status.startswith("201")
        temporary_password = json.loads(created_body)["accounts"][0]["temporary_password"]
        temp_login, temp_headers, _ = _call(
            app,
            "/login",
            method="POST",
            body={"actor_id": "fixture-temp", "password": temporary_password},
            scheme="https",
            host="localhost:8443",
        )
        assert temp_login.startswith("303")
        temp_token = temp_headers["Set-Cookie"].split(";", 1)[0].split("=", 1)[1]
        rotated, rotated_headers, _ = _call(
            app,
            "/api/v1/me/password",
            method="POST",
            token=temp_token,
            body={
                "current_password": temporary_password,
                "new_password": "rotated-password-456",
            },
            scheme="https",
            host="localhost:8443",
        )
        assert rotated.startswith("200")
        rotated_cookie = rotated_headers["Set-Cookie"]
        assert rotated_cookie.startswith("__Host-aicefr_session=")
        assert "Secure" in rotated_cookie and "HttpOnly" in rotated_cookie
        rotated_token = rotated_cookie.split(";", 1)[0].split("=", 1)[1]
        assert _call(
            app,
            "/api/v1/me",
            token=rotated_token,
            scheme="https",
            host="localhost:8443",
        )[0].startswith("200")
    finally:
        store.close()


def test_user_agent_is_reduced_to_known_device_categories():
    assert _coarse_device_category("Android 14 Mobile") == "mobile"
    assert _coarse_device_category("iPhone OS 17") == "mobile"
    assert _coarse_device_category("iPad; CPU OS 17") == "tablet"
    assert _coarse_device_category("Windows NT 10.0") == "desktop"
    assert _coarse_device_category("nonstandard private-agent") == "unknown"
