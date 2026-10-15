from __future__ import annotations

import base64
import json
import urllib.parse
from datetime import UTC, datetime
from io import BytesIO

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from aicefr.api.identity import IdentityApi
from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.auth.accounts import AccountService
from aicefr.auth.google import GoogleConfig, GoogleIdentityService
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole
from aicefr.local.app import SQLiteSessionRepository
from aicefr.portal.router import PortalRouter
from aicefr.storage.google_identity import google_subject_hash
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore

_CLIENT_ID = "offline-api-client.apps.googleusercontent.com"
_SUBJECT = "offline-api-google-subject-500"
_SECRET = "offline-api-client-secret"


class _NoStudentApi:
    def submit(self, _token, _request):  # pragma: no cover - routes are not under test
        raise AssertionError("student submission is outside this test")


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class _OfflineGoogle:
    """Fake Google HTTPS boundary; JWT signatures remain real RSA/RS256."""

    def __init__(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.claims: dict[str, object] = {}
        self.requests: list[tuple[str, str, dict[str, str] | None]] = []

    def request_json(self, method: str, url: str, **kwargs: object) -> dict[str, object]:
        data = kwargs.get("data")
        self.requests.append((method, url, data if isinstance(data, dict) else None))
        if url == "https://oauth2.googleapis.com/token":
            return {"id_token": self._jwt()}
        numbers = self.private_key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "offline-kid-1",
                    "alg": "RS256",
                    "use": "sig",
                    "n": _b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
                    "e": _b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
                }
            ]
        }

    def set_claims(self, clock: _Clock, authorization_url: str) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(authorization_url).query)
        self.claims = {
            "iss": "https://accounts.google.com",
            "aud": _CLIENT_ID,
            "sub": _SUBJECT,
            "iat": int(clock.now.timestamp()),
            "exp": int(clock.now.timestamp()) + 300,
            "nonce": query["nonce"][0],
        }

    def _jwt(self) -> str:
        header = _b64(
            json.dumps(
                {"alg": "RS256", "kid": "offline-kid-1", "typ": "JWT"},
                separators=(",", ":"),
            ).encode()
        )
        claims = _b64(json.dumps(self.claims, separators=(",", ":")).encode())
        message = f"{header}.{claims}".encode("ascii")
        signature = self.private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        return f"{header}.{claims}.{_b64(signature)}"


def _request(
    app,
    path: str,
    *,
    method: str = "GET",
    query: str = "",
    cookies: dict[str, str] | None = None,
    origin: bool = True,
    scheme: str = "http",
):
    result: dict[str, object] = {}
    cookie_header = "; ".join(f"{key}={value}" for key, value in (cookies or {}).items())
    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": "0",
        "CONTENT_TYPE": "",
        "HTTP_COOKIE": cookie_header,
        "HTTP_HOST": "localhost:8000",
        "HTTP_ORIGIN": f"{scheme}://localhost:8000" if origin else "",
        "wsgi.url_scheme": scheme,
        "wsgi.input": BytesIO(b""),
    }

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = headers

    body = b"".join(app(env, start_response))
    return str(result["status"]), list(result["headers"]), body


def _headers(headers: list[tuple[str, str]], name: str) -> list[str]:
    return [value for key, value in headers if key.lower() == name.lower()]


def _cookie_pair(set_cookie: str) -> tuple[str, str]:
    name, value = set_cookie.split(";", 1)[0].split("=", 1)
    return name, value


@pytest.fixture
def runtime(tmp_path):
    clock = _Clock()
    store = SQLiteStore(tmp_path / "google-api")
    identity_repository = IdentityRepository(store)
    auth = AuthService(
        store,
        SQLiteSessionRepository(store),
        clock=clock,
        identity_repository=identity_repository,
    )
    accounts = AccountService(auth, identity_repository)
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass-456")
    provider = _OfflineGoogle()
    config = GoogleConfig(
        enabled=True,
        client_id=_CLIENT_ID,
        client_secret=_SECRET,
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=store.data_dir,
    )
    google = GoogleIdentityService(
        auth,
        identity_repository,
        config,
        key=b"g" * 32,
        clock=clock,
        transport=provider,
    )
    identity_api = IdentityApi(auth, accounts, google)
    portal = PortalRouter(None, None, None, None, identity_api)
    app = StudentTeacherApp(StudentApi(_NoStudentApi()), auth=auth, portal=portal)
    token = auth.login("fixture-student", "student-pass-456")
    yield clock, store, identity_repository, auth, google, provider, app, token
    store.close()


def test_google_link_and_login_are_consumable_through_http_cookies(runtime):
    clock, store, repository, auth, google, provider, app, token = runtime
    status, headers, body = _request(
        app,
        "/auth/google/start",
        method="POST",
        query="intent=link",
        cookies={"aicefr_session": token},
    )
    assert status.startswith("303")
    assert body == b""
    location = _headers(headers, "Location")[0]
    flow_cookie_header = _headers(headers, "Set-Cookie")[0]
    flow_cookie_name, flow_cookie = _cookie_pair(flow_cookie_header)
    assert flow_cookie_name == "aicefr_google_flow"
    assert "HttpOnly" in flow_cookie_header and "SameSite=Lax" in flow_cookie_header
    assert "Path=/auth/google/" in flow_cookie_header
    assert "Secure" not in flow_cookie_header and "Domain=" not in flow_cookie_header
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    assert query["scope"] == ["openid"]
    assert query["code_challenge_method"] == ["S256"]
    provider.set_claims(clock, location)

    callback_query = urllib.parse.urlencode(
        {"state": query["state"][0], "code": "offline-auth-code"}
    )
    status, callback_headers, body = _request(
        app,
        "/auth/google/callback",
        query=callback_query,
        cookies={flow_cookie_name: flow_cookie, "aicefr_session": token},
    )
    assert status.startswith("200")
    assert json.loads(body) == {"outcome": "linked", "actor_id": "fixture-student"}
    assert _headers(callback_headers, "Set-Cookie")[0].endswith("Max-Age=0")
    assert store.connection.execute(
        "SELECT account_id,provider,subject_hash FROM account_identities"
    ).fetchone() == ("fixture-student", "google", google_subject_hash(_SUBJECT))
    exchange = next(
        data
        for method, url, data in provider.requests
        if method == "POST" and url == "https://oauth2.googleapis.com/token"
    )
    assert exchange is not None
    assert exchange["code"] == "offline-auth-code"
    assert exchange["client_secret"] == _SECRET
    assert exchange["code_verifier"] and len(exchange["code_verifier"]) >= 43

    status, headers, _ = _request(app, "/auth/google/start")
    assert status.startswith("303")
    location = _headers(headers, "Location")[0]
    flow_cookie_name, flow_cookie = _cookie_pair(_headers(headers, "Set-Cookie")[0])
    provider.set_claims(clock, location)
    login_query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    callback_query = urllib.parse.urlencode(
        {"state": login_query["state"][0], "code": "offline-login-code"}
    )
    status, callback_headers, body = _request(
        app,
        "/auth/google/callback",
        query=callback_query,
        cookies={flow_cookie_name: flow_cookie},
    )
    assert status.startswith("200")
    payload = json.loads(body)
    assert payload == {"outcome": "authenticated", "actor_id": "fixture-student"}
    assert "offline-login-code" not in body.decode()
    assert _SECRET not in body.decode()
    set_cookies = _headers(callback_headers, "Set-Cookie")
    session_cookie = next(value for value in set_cookies if value.startswith("aicefr_session="))
    session_name, session_token = _cookie_pair(session_cookie)
    assert session_name == "aicefr_session"
    assert "HttpOnly" in session_cookie and "SameSite=Lax" in session_cookie
    assert session_token not in body.decode()
    me_status, _, me_body = _request(app, "/api/v1/me", cookies={session_name: session_token})
    assert me_status.startswith("200")
    assert json.loads(me_body)["profile"]["actor_id"] == "fixture-student"
    assert auth.resolve(session_token).actor_id == "fixture-student"
    assert google.is_linked(token) is True
    linked_status, _, linked_body = _request(
        app, "/api/v1/me/google", cookies={"aicefr_session": token}
    )
    assert linked_status.startswith("200")
    assert json.loads(linked_body) == {"linked": True, "enabled": True}


@pytest.mark.parametrize("bad_flow", ["forged-cookie", "wrong-state"])
def test_forged_flow_callback_clears_cookie_and_redacts_provider_inputs(runtime, bad_flow):
    _clock, _store, _repository, _auth, _google, provider, app, _token = runtime
    status, headers, _ = _request(app, "/auth/google/start")
    assert status.startswith("303")
    location = _headers(headers, "Location")[0]
    name, value = _cookie_pair(_headers(headers, "Set-Cookie")[0])
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    cookie = (
        value[:-1] + ("A" if value[-1] != "A" else "B") if bad_flow == "forged-cookie" else value
    )
    state = (
        "forged-state-value-012345678901234567890"
        if bad_flow == "wrong-state"
        else params["state"][0]
    )
    query = urllib.parse.urlencode({"state": state, "code": "provider-secret-code-DO-NOT-ECHO"})
    status, callback_headers, body = _request(
        app, "/auth/google/callback", query=query, cookies={name: cookie}
    )
    assert status.startswith("400")
    assert _headers(callback_headers, "Set-Cookie")[0].endswith("Max-Age=0")
    for secret in ("provider-secret-code-DO-NOT-ECHO", state, cookie, _SECRET):
        assert secret.encode() not in body
    assert provider.requests == []


def test_google_routes_fail_closed_when_google_is_unavailable(tmp_path):
    store = SQLiteStore(tmp_path / "google-disabled-api")
    repository = IdentityRepository(store)
    auth = AuthService(store, SQLiteSessionRepository(store), identity_repository=repository)
    accounts = AccountService(auth, repository)
    identity_api = IdentityApi(auth, accounts, google=None)
    portal = PortalRouter(None, None, None, None, identity_api)
    app = StudentTeacherApp(StudentApi(_NoStudentApi()), auth=auth, portal=portal)
    try:
        for path in ("/auth/google/start", "/auth/google/callback"):
            status, _headers_out, body = _request(app, path)
            assert status.startswith("503")
            assert json.loads(body)["error"] == "GOOGLE_UNAVAILABLE"
    finally:
        store.close()


def test_google_http_methods_and_link_csrf_are_enforced(runtime):
    _clock, _store, _repository, _auth, _google, _provider, app, token = runtime
    status, _, _ = _request(app, "/auth/google/start", query="intent=link")
    assert status.startswith("405")
    status, _, body = _request(
        app,
        "/auth/google/start",
        method="POST",
        query="intent=link",
        cookies={"aicefr_session": token},
        origin=False,
    )
    assert status.startswith("403")
    assert b"SESSION" not in body

    status, headers, _ = _request(app, "/auth/google/start")
    assert status.startswith("303")
    clear_cookie = _headers(headers, "Set-Cookie")[0]
    status, callback_headers, _ = _request(
        app,
        "/auth/google/callback",
        method="POST",
        cookies={_cookie_pair(clear_cookie)[0]: _cookie_pair(clear_cookie)[1]},
    )
    assert status.startswith("405")
    assert _headers(callback_headers, "Set-Cookie")[0].endswith("Max-Age=0")

    status, _, _ = _request(
        app,
        "/api/v1/me/google",
        method="POST",
        cookies={"aicefr_session": token},
        origin=False,
    )
    assert status.startswith("403")


def test_secure_deployment_uses_host_cookie_flags(tmp_path):
    clock = _Clock()
    store = SQLiteStore(tmp_path / "google-secure-api")
    identity_repository = IdentityRepository(store)
    auth = AuthService(
        store,
        SQLiteSessionRepository(store),
        clock=clock,
        identity_repository=identity_repository,
    )
    accounts = AccountService(auth, identity_repository)
    provider = _OfflineGoogle()
    config = GoogleConfig(
        enabled=True,
        client_id=_CLIENT_ID,
        client_secret=_SECRET,
        redirect_uri="https://app.example/auth/google/callback",
        data_dir=store.data_dir,
        secure_deployment=True,
    )
    google = GoogleIdentityService(
        auth,
        identity_repository,
        config,
        key=b"s" * 32,
        clock=clock,
        transport=provider,
    )
    app = StudentTeacherApp(
        StudentApi(_NoStudentApi()),
        auth=auth,
        portal=PortalRouter(None, None, None, None, IdentityApi(auth, accounts, google)),
    )
    try:
        status, headers, _ = _request(app, "/auth/google/start", scheme="https")
        assert status.startswith("303")
        cookie = _headers(headers, "Set-Cookie")[0]
        assert cookie.startswith("__Host-aicefr_google_flow=")
        assert "Secure" in cookie and "Path=/" in cookie
        assert "Domain=" not in cookie
    finally:
        store.close()
