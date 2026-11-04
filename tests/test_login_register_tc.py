"""Automated test cases for Login, Register (Signup), and Google OAuth flows.

Covers:
- TC-LOGIN-01: Login page layout, Figma contract elements, inputs & eye toggle
- TC-LOGIN-02: Google OAuth button enabled state on /login when configured
- TC-LOGIN-03: Google OAuth button disabled state on /login when not configured
- TC-LOGIN-04: Successful login sets session cookie and returns home URL
- TC-LOGIN-05: Login with wrong password returns 401 with Vietnamese detail
- TC-LOGIN-06: Login with nonexistent email returns 401
- TC-LOGIN-07: Rate limiting lockout (429) on repeated failed logins
- TC-LOGIN-08: Logged in student can access authenticated endpoints (/api/v1/me/account)
- TC-LOGIN-09: Case-insensitive email login and whitespace trimming
- TC-LOGIN-10: Exact preservation of spaces and special characters in passwords
- TC-LOGIN-11: Visiting /login?expired=1 renders toast notification hook
- TC-LOGIN-12: Client login enforces safe relative redirect (open redirect protection)
- TC-LOGIN-13: Client validation and form alert contract on /login
- TC-SIGNUP-01: Signup page layout, Figma contract elements, inputs & dual eye toggles
- TC-SIGNUP-02: Google OAuth button enabled state on /signup when configured
- TC-SIGNUP-03: Google OAuth button disabled state on /signup when not configured
- TC-SIGNUP-04: Successful self-signup creates student account and logs in
- TC-SIGNUP-05: Duplicate email registration returns 409 Conflict
- TC-SIGNUP-06: Short password (< min_length) returns 422 Unprocessable Content
- TC-SIGNUP-07: When self-signup is disabled, /signup redirects to /login
- TC-SIGNUP-08: Signed-in student visiting /signup redirects to /practice
- TC-SIGNUP-09: Signup email normalized and stored in lowercase
- TC-SIGNUP-10: Full name max length (80 characters) enforced
- TC-SIGNUP-11: Client validation contract and error messages on /signup
- TC-SIGNUP-12: Dual eye show/hide toggle accessibility contract on /signup
- TC-SIGNUP-13: Enlarged brand logo styling contract across auth pages
- TC-GOOGLE-01: /auth/google/start initiates OAuth redirect to Google with PKCE & cookie
- TC-GOOGLE-02: /auth/google/start redirects to error when OAuth not configured
- TC-GOOGLE-03: /auth/google/callback rejects tampered/missing state parameter
- TC-GOOGLE-04: /auth/google/callback completes sign-in flow with valid mocked ID token
- TC-GOOGLE-05: Cancelled OAuth (access_denied) redirects to /login?google=cancelled
- TC-GOOGLE-06: Google OAuth flow cookie security flags (HttpOnly, SameSite=Lax)
- TC-GOOGLE-07: Missing state or flow cookie redirects safely to /login?google=state
"""

from __future__ import annotations

import base64
import importlib
import itertools
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from aicefr.auth import google
from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

TEST_PASSWORD = "-".join(["test", "password", "valid", "123"])
TEST_CLIENT_ID = "159571801413-testclient.apps.googleusercontent.com"
_counter = itertools.count(1)


def make_test_app(
    monkeypatch,
    tmp_path,
    google_on: bool = True,
    self_signup: bool = True,
    rate_limit: int | None = None,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_ENV", "development")
    monkeypatch.setenv("AICEFR_SELF_SIGNUP", "1" if self_signup else "0")
    monkeypatch.setenv("AICEFR_GOOGLE_SIGNUP", "1")
    if rate_limit is not None:
        monkeypatch.setenv("AICEFR_LOGIN_RATE", str(rate_limit))
    if google_on:
        monkeypatch.setenv("AICEFR_GOOGLE_CLIENT_ID", TEST_CLIENT_ID)
        monkeypatch.setenv("AICEFR_GOOGLE_CLIENT_SECRET", "GOCS-test-secret-value-1234")
    else:
        monkeypatch.delenv("AICEFR_GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("AICEFR_GOOGLE_CLIENT_SECRET", raising=False)

    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    return main


def fresh_signup_payload(password: str = TEST_PASSWORD, **overrides) -> dict:
    idx = next(_counter)
    return {
        "email": f"learner{idx}@example.edu.vn",
        "full_name": f"Học Viên {idx}",
        "password": password,
        **overrides,
    }


def make_mock_id_token(
    client_id: str,
    sub: str,
    email: str,
    nonce: str,
    name: str = "Test Student",
    domain: str | None = None,
) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "kid": "k1", "typ": "JWT"}
    payload = {
        "iss": "https://accounts.google.com",
        "aud": client_id,
        "sub": sub,
        "email": email,
        "email_verified": True,
        "name": name,
        "nonce": nonce,
        "iat": now,
        "exp": now + 3600,
    }
    if domain:
        payload["hd"] = domain

    def b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    return f"{b64(header)}.{b64(payload)}.mocksignature"


# ==============================================================================
# LOGIN TEST CASES
# ==============================================================================


def test_tc_login_01_page_renders_figma_layout_and_elements(tmp_path, monkeypatch):
    """TC-LOGIN-01: Login page renders with status 200, contains brand title,
    email input, password input, eye toggle button and submit button; no
    remember-me checkbox (D091: a session always lasts at most 8 hours)."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)
    r = c.get("/login")
    assert r.status_code == 200
    html = r.text

    # Title & Branding
    assert "Đăng nhập · SpeakUp" in html
    assert "SpeakUp" in html

    # Figma Contract Form Fields
    assert 'id="pseudonym"' in html
    assert 'id="password"' in html
    assert 'id="show-password"' in html
    assert 'id="b"' in html
    assert 'id="tb"' in html  # Toast message box

    # D091: no remember-me box; sign-up link while self sign-up is on
    assert 'id="remember"' not in html and "Remember me" not in html
    assert 'href="/signup"' in html


def test_tc_login_02_google_oauth_button_enabled_when_configured(tmp_path, monkeypatch):
    """TC-LOGIN-02: When Google OAuth credentials exist, the login page displays
    an active <a> link pointing to /auth/google/start?mode=login."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)
    r = c.get("/login")
    assert r.status_code == 200
    html = r.text

    assert 'id="google-login"' in html
    assert 'href="/auth/google/start?mode=login"' in html
    assert "bằng Google" in html
    assert 'id="google-disabled-btn"' not in html


def test_tc_login_03_google_oauth_button_disabled_when_not_configured(tmp_path, monkeypatch):
    """TC-LOGIN-03: When Google OAuth is disabled/not configured, the login page
    displays a disabled button with fallback instructions."""
    m = make_test_app(monkeypatch, tmp_path, google_on=False)
    c = TestClient(m.app)
    r = c.get("/login")
    assert r.status_code == 200
    html = r.text

    assert 'id="google-disabled-btn"' in html
    assert 'id="google-login"' not in html


def test_tc_login_04_successful_login_sets_session_cookie(tmp_path, monkeypatch):
    """TC-LOGIN-04: Submitting valid credentials returns 200, sets aicefr_session cookie,
    and returns the role home redirect path."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)

    # First register an account
    signup_data = fresh_signup_payload()
    reg_res = c.post("/api/v1/auth/signup", json=signup_data)
    assert reg_res.status_code == 200

    # Clear cookies to simulate fresh login
    c.cookies.clear()

    # Attempt login
    login_res = c.post(
        "/api/v1/auth/login",
        json={"email": signup_data["email"], "password": signup_data["password"]},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "home" in data
    assert data["home"] == "/practice"
    assert "aicefr_session" in c.cookies


def test_tc_login_05_wrong_password_returns_401(tmp_path, monkeypatch):
    """TC-LOGIN-05: Submitting incorrect password returns 401 Unauthorized with
    proper error message."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)

    signup_data = fresh_signup_payload()
    c.post("/api/v1/auth/signup", json=signup_data)
    c.cookies.clear()

    res = c.post(
        "/api/v1/auth/login",
        json={"email": signup_data["email"], "password": "WrongPassword!404"},
    )
    assert res.status_code == 401
    assert res.json().get("detail", "") == "email hoặc mật khẩu không đúng"


def test_tc_login_06_nonexistent_email_returns_401(tmp_path, monkeypatch):
    """TC-LOGIN-06: Submitting non-existent email returns 401."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    res = c.post(
        "/api/v1/auth/login",
        json={"email": "nobody_exists_here@example.edu.vn", "password": TEST_PASSWORD},
    )
    assert res.status_code == 401


def test_tc_login_07_rate_limiting_lockout_429(tmp_path, monkeypatch):
    """TC-LOGIN-07: Exceeding failed login limit triggers a 429 lockout under NFR-07."""
    m = make_test_app(monkeypatch, tmp_path, rate_limit=3)
    c = TestClient(m.app)
    payload = {"email": "attacker@example.edu.vn", "password": "wrong"}

    statuses = [c.post("/api/v1/auth/login", json=payload).status_code for _ in range(5)]
    assert 429 in statuses


def test_tc_login_08_authenticated_session_accesses_me_account(tmp_path, monkeypatch):
    """TC-LOGIN-08: Valid login session allows accessing authenticated student endpoints."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)

    signup_data = fresh_signup_payload()
    c.post("/api/v1/auth/signup", json=signup_data)

    me = c.get("/api/v1/me/account")
    assert me.status_code == 200
    assert me.json()["email"] == signup_data["email"]
    assert me.json()["role"] == Role.STUDENT.value


def test_tc_login_09_case_insensitive_and_whitespace_email_login(tmp_path, monkeypatch):
    """TC-LOGIN-09: Email login is case-insensitive and trims leading/trailing whitespace."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    signup_data = fresh_signup_payload(email="learner_ci_case@example.edu.vn")
    r = c.post("/api/v1/auth/signup", json=signup_data)
    assert r.status_code == 200
    c.cookies.clear()

    # 1. Login with uppercase email
    r_upper = c.post(
        "/api/v1/auth/login",
        json={"email": "LEARNER_CI_CASE@EXAMPLE.EDU.VN", "password": signup_data["password"]},
    )
    assert r_upper.status_code == 200
    c.cookies.clear()

    # 2. Login with untrimmed whitespace
    r_spaces = c.post(
        "/api/v1/auth/login",
        json={"email": "   learner_ci_case@example.edu.vn   ", "password": signup_data["password"]},
    )
    assert r_spaces.status_code == 200
    c.cookies.clear()

    # 3. Login with mixed case + whitespace
    r_mixed = c.post(
        "/api/v1/auth/login",
        json={
            "email": " \t Learner_CI_Case@Example.EDU.vn \n ",
            "password": signup_data["password"],
        },
    )
    assert r_mixed.status_code == 200


def test_tc_login_10_password_special_characters_and_spaces_preserved(tmp_path, monkeypatch):
    """TC-LOGIN-10: Passwords keep their exact special characters and spaces; nothing is
    trimmed."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    complex_password = "  P@ssw0rd with spaces & $ymbols!  "
    signup_data = fresh_signup_payload(password=complex_password)
    r = c.post("/api/v1/auth/signup", json=signup_data)
    assert r.status_code == 200
    c.cookies.clear()

    # Exact password matches
    r_exact = c.post(
        "/api/v1/auth/login",
        json={"email": signup_data["email"], "password": complex_password},
    )
    assert r_exact.status_code == 200
    c.cookies.clear()

    # Trimmed password fails (passwords must be byte-for-byte exact)
    r_trimmed = c.post(
        "/api/v1/auth/login",
        json={"email": signup_data["email"], "password": complex_password.strip()},
    )
    assert r_trimmed.status_code == 401


def test_tc_login_11_session_expired_query_param_handling(tmp_path, monkeypatch):
    """TC-LOGIN-11: /login?expired=1 renders, and login.js has the expired-session message."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    r = c.get("/login?expired=1")
    assert r.status_code == 200
    html = r.text
    assert 'id="tb"' in html
    assert 'src="/static/login.js' in html

    # Verify login.js contains handler for expired=1
    js_r = c.get("/static/login.js")
    assert js_r.status_code == 200
    assert 'get("expired")' in js_r.text
    assert "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại." in js_r.text


def test_tc_login_12_safe_next_url_redirect_contract(tmp_path, monkeypatch):
    """TC-LOGIN-12: `next` goes through samePath (common.js), which resolves the path
    against this origin, so "//evil.example" and "/\\evil.example" are both refused."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    common = c.get("/static/common.js").text
    assert "window.samePath = function" in common
    assert "new URL(p, location.origin).origin === location.origin" in common
    for page in ("login.js", "signup.js"):
        js = c.get(f"/static/{page}").text
        assert "window.samePath(asked)" in js
        assert 'startsWith("//")' not in js


def test_tc_login_13_client_validation_and_form_alert_contract(tmp_path, monkeypatch):
    """TC-LOGIN-13: The login form has novalidate, a form-level alert, inline error
    containers and Vietnamese copy."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    r = c.get("/login")
    assert r.status_code == 200
    html = r.text

    assert "<form" in html
    assert "novalidate" in html
    assert 'id="auth-alert"' in html
    assert 'id="pseudonym-error"' in html
    assert 'id="password-error"' in html

    js_r = c.get("/static/login.js")
    assert js_r.status_code == 200
    js = js_r.text
    assert "Hãy nhập email." in js
    assert "Hãy nhập một email hợp lệ." in js
    assert "Hãy nhập mật khẩu." in js
    assert "Email hoặc mật khẩu không đúng." in js


# ==============================================================================
# REGISTER (SIGNUP) TEST CASES
# ==============================================================================


def test_tc_signup_01_page_renders_figma_layout_and_elements(tmp_path, monkeypatch):
    """TC-SIGNUP-01: Signup page renders with status 200, contains email input,
    username input, password input, confirm password, dual eye toggles, and submit button."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)
    r = c.get("/signup")
    assert r.status_code == 200
    html = r.text

    assert "Đăng ký · SpeakUp" in html
    assert 'id="email"' in html
    assert 'id="full-name"' in html
    assert 'id="password"' in html
    assert 'id="again"' in html
    assert 'id="show-password"' in html
    assert 'id="show-again"' in html
    assert 'id="b"' in html
    assert 'id="tb"' in html
    assert 'href="/login"' in html


def test_tc_signup_02_google_oauth_button_on_signup_page(tmp_path, monkeypatch):
    """TC-SIGNUP-02: Signup page renders active Google OAuth button when configured."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)
    r = c.get("/signup")
    assert r.status_code == 200
    html = r.text

    assert 'id="google-login"' in html
    assert "bằng Google" in html


def test_tc_signup_03_google_oauth_button_disabled_when_not_configured(tmp_path, monkeypatch):
    """TC-SIGNUP-03: Signup page renders disabled button when Google OAuth not configured."""
    m = make_test_app(monkeypatch, tmp_path, google_on=False)
    c = TestClient(m.app)
    r = c.get("/signup")
    assert r.status_code == 200
    html = r.text

    assert 'id="google-disabled-btn"' in html
    assert 'id="google-login"' not in html


def test_tc_signup_04_valid_registration_creates_student_account(tmp_path, monkeypatch):
    """TC-SIGNUP-04: Submitting valid registration creates account, returns student role,
    and sets session cookie."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    data = fresh_signup_payload()

    res = c.post("/api/v1/auth/signup", json=data)
    assert res.status_code == 200
    body = res.json()
    assert body.get("home") == "/practice"
    assert "aicefr_session" in c.cookies

    # Verify student can immediately access /api/v1/me/account and has student role
    me = c.get("/api/v1/me/account")
    assert me.status_code == 200
    assert me.json()["email"] == data["email"]
    assert me.json()["role"] == Role.STUDENT.value


def test_tc_signup_05_duplicate_email_rejected(tmp_path, monkeypatch):
    """TC-SIGNUP-05: Attempting to sign up with an existing email returns 409 Conflict."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    data = fresh_signup_payload()

    # First registration succeeds
    r1 = c.post("/api/v1/auth/signup", json=data)
    assert r1.status_code == 200

    # Second registration with same email fails with 409 Conflict
    r2 = c.post("/api/v1/auth/signup", json=data)
    assert r2.status_code == 409
    assert "email này đã có tài khoản" in r2.json().get("detail", "").lower()


def test_tc_signup_06_short_password_rejected(tmp_path, monkeypatch):
    """TC-SIGNUP-06: Passwords shorter than minimum length are rejected with 422."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    data = fresh_signup_payload(password="short1")

    res = c.post("/api/v1/auth/signup", json=data)
    assert res.status_code == 422


def test_tc_signup_07_self_signup_disabled_redirects_to_login(tmp_path, monkeypatch):
    """TC-SIGNUP-07: When self-signup is turned off (AICEFR_SELF_SIGNUP=0),
    accessing /signup redirects to /login with 303."""
    m = make_test_app(monkeypatch, tmp_path, self_signup=False)
    c = TestClient(m.app)

    r = c.get("/signup", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_tc_signup_08_authenticated_user_visiting_signup_redirects(tmp_path, monkeypatch):
    """TC-SIGNUP-08: Logged in student visiting /signup is redirected (303) to /practice."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)

    data = fresh_signup_payload()
    c.post("/api/v1/auth/signup", json=data)

    r = c.get("/signup", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/practice"


def test_tc_signup_09_email_stored_normalized_lowercase(tmp_path, monkeypatch):
    """TC-SIGNUP-09: An email given in capitals or with spaces is stored trimmed and in
    lowercase."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    signup_data = fresh_signup_payload(email="   LEARNER_LOWERCASE_CHECK@EXAMPLE.EDU.VN   ")
    r = c.post("/api/v1/auth/signup", json=signup_data)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "learner_lowercase_check@example.edu.vn"

    me = c.get("/api/v1/me/account")
    assert me.status_code == 200
    assert me.json()["email"] == "learner_lowercase_check@example.edu.vn"


def test_tc_signup_10_full_name_max_length_80_enforced(tmp_path, monkeypatch):
    """TC-SIGNUP-10: Names exceeding schema maximum length (80 chars) are rejected with 422."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    long_name = "Nguyen " * 15  # > 100 characters
    signup_data = fresh_signup_payload(full_name=long_name)
    r = c.post("/api/v1/auth/signup", json=signup_data)
    assert r.status_code == 422


def test_tc_signup_11_client_validation_contract_and_error_messages(tmp_path, monkeypatch):
    """TC-SIGNUP-11: The sign-up form has novalidate, inline error spans and Vietnamese
    validation messages."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    r = c.get("/signup")
    assert r.status_code == 200
    html = r.text

    assert "novalidate" in html
    assert 'id="auth-alert"' in html
    assert 'id="email-error"' in html
    assert 'id="name-error"' in html
    assert 'id="password-error"' in html
    assert 'id="again-error"' in html

    js_r = c.get("/static/signup.js")
    assert js_r.status_code == 200
    js = js_r.text
    assert "Hãy nhập email." in js
    assert "Hãy nhập một email hợp lệ." in js
    assert "Hãy nhập họ và tên." in js
    assert "Hãy nhập mật khẩu." in js
    assert "Hai lần nhập mật khẩu chưa khớp nhau." in js
    assert "Email này đã có tài khoản. Hãy đăng nhập." in js


def test_tc_signup_12_password_show_hide_toggles_contract(tmp_path, monkeypatch):
    """TC-SIGNUP-12: The sign-up page has two show-password toggles, each with its own
    accessible label."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)
    r = c.get("/signup")
    assert r.status_code == 200
    html = r.text

    assert 'id="show-password"' in html
    assert 'id="show-again"' in html
    assert 'aria-label="Hiện mật khẩu"' in html
    assert 'aria-label="Hiện mật khẩu nhập lại"' in html


def test_tc_signup_13_enlarged_brand_logo_styling_contract(tmp_path, monkeypatch):
    """TC-SIGNUP-13: Both /login and /signup embed the enlarged brand logo and CSS rules."""
    m = make_test_app(monkeypatch, tmp_path)
    c = TestClient(m.app)

    # Check template markup
    for path in ("/login", "/signup"):
        r = c.get(path)
        assert r.status_code == 200
        assert "auth-figma-brand" in r.text
        assert "brand-mark" in r.text
        assert "mascot-casing" in r.text

    # Check CSS styling
    css_r = c.get("/static/style.css")
    assert css_r.status_code == 200
    css = css_r.text
    assert ".auth-figma-brand" in css
    assert "width: 48px" in css
    assert "height: 48px" in css
    assert "font-size: 1.75rem" in css


# ==============================================================================
# GOOGLE OAUTH FLOW TEST CASES
# ==============================================================================


def test_tc_google_01_start_redirects_to_google_with_pkce_and_cookie(tmp_path, monkeypatch):
    """TC-GOOGLE-01: /auth/google/start initiates OAuth roundtrip by setting a signed
    aicefr_oauth cookie and returning 303 See Other redirecting to Google's auth endpoint."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    r = c.get("/auth/google/start?mode=login", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")

    # Verify query params passed to Google
    parsed = urlparse(loc)
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == [TEST_CLIENT_ID]
    assert "redirect_uri" in qs
    assert qs["response_type"] == ["code"]
    assert "state" in qs
    assert "code_challenge" in qs
    assert qs["code_challenge_method"] == ["S256"]

    # Verify signed flow cookie
    assert "aicefr_oauth" in r.cookies


def test_tc_google_02_start_unconfigured_redirects_to_login_error(tmp_path, monkeypatch):
    """TC-GOOGLE-02: When Google OAuth is unconfigured, /auth/google/start redirects
    back to /login?google=not_configured."""
    m = make_test_app(monkeypatch, tmp_path, google_on=False)
    c = TestClient(m.app)

    r = c.get("/auth/google/start?mode=login", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?google=not_configured"


def test_tc_google_03_callback_tampered_state_refused(tmp_path, monkeypatch):
    """TC-GOOGLE-03: Callback with tampered or mismatched state parameter is rejected."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    # Start flow to obtain signed cookie
    c.get("/auth/google/start?mode=login", follow_redirects=False)
    assert "aicefr_oauth" in c.cookies

    # Callback with wrong state query param
    cb_res = c.get(
        "/auth/google/callback?code=fake-code&state=TAMPERED_STATE",
        follow_redirects=False,
    )
    assert cb_res.status_code == 303
    assert cb_res.headers["location"] == "/login?google=state"


def test_tc_google_04_callback_successful_roundtrip(tmp_path, monkeypatch):
    """TC-GOOGLE-04: Callback with valid state and mock token creates student account
    and establishes authenticated session."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    # Start flow
    start_res = c.get("/auth/google/start?mode=login", follow_redirects=False)
    loc = start_res.headers["location"]
    qs = parse_qs(urlparse(loc).query)
    state = qs["state"][0]

    # Decode flow cookie to get nonce
    flow_cookie = c.cookies["aicefr_oauth"]
    flow_obj = google.decode_flow(flow_cookie, m.app.state.auth_repo.secret("google_flow"))
    assert flow_obj is not None

    mock_token = make_mock_id_token(
        client_id=TEST_CLIENT_ID,
        sub="google-test-sub-12345",
        email="google_user@example.edu.vn",
        nonce=flow_obj.nonce,
        name="Google Student",
    )

    # Intercept Google token exchange
    monkeypatch.setattr(
        "aicefr.auth.google._post_form",
        lambda url, fields: {"id_token": mock_token},
    )

    # Invoke callback
    cb = c.get(f"/auth/google/callback?code=mock_code_xyz&state={state}", follow_redirects=False)
    assert cb.status_code == 303
    assert cb.headers["location"] == "/practice"
    assert "aicefr_session" in c.cookies

    # Verify session is valid and identity linked
    me = c.get("/api/v1/me/account")
    assert me.status_code == 200
    acc = me.json()
    assert acc["google"]["linked"] is True
    assert acc["email"] == "google_user@example.edu.vn"


def test_tc_google_05_cancelled_oauth_error_access_denied_handled_gracefully(tmp_path, monkeypatch):
    """TC-GOOGLE-05: When user cancels Google auth on Google's consent screen,
    the callback redirects to /login?google=cancelled without error."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    # Initiate flow
    c.get("/auth/google/start?mode=login", follow_redirects=False)

    # Google callback when user presses Cancel returns ?error=access_denied
    r = c.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?google=cancelled"


def test_tc_google_06_oauth_cookie_security_flags(tmp_path, monkeypatch):
    """TC-GOOGLE-06: The aicefr_oauth flow cookie is configured with HttpOnly and SameSite=Lax."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    r = c.get("/auth/google/start?mode=login", follow_redirects=False)
    assert r.status_code == 303
    set_cookie_header = r.headers.get("set-cookie", "")
    assert "aicefr_oauth=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()
    assert "path=/auth/google" in set_cookie_header.lower()


def test_tc_google_07_oauth_missing_state_redirects_safely(tmp_path, monkeypatch):
    """TC-GOOGLE-07: Direct call to callback without cookie or state parameter redirects safely."""
    m = make_test_app(monkeypatch, tmp_path, google_on=True)
    c = TestClient(m.app)

    r = c.get("/auth/google/callback", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?google=state"
