"""Layer 2 -- INTEGRATION: profile, sessions, history, Google sign-in, account admin (D029).

Real SQLite in a temporary file and the real app through TestClient. Google is
never called: `aicefr.auth.google._post_form`, the one function that talks to
Google's token endpoint, is replaced by a stand-in that returns an ID token
built here, so every check on that token runs for real. Tests named after an
acceptance criterion carry the name given in SRS section 3.9d (FR-56..FR-60).
"""

from __future__ import annotations

import base64
import importlib
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import on_server
from dbutil import store
from fastapi.testclient import TestClient

from aicefr.auth import google
from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

PASSWORD = "matkhau-kiem-thu"
CLIENT_ID = "test-client.apps.googleusercontent.com"
CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


def make_app(monkeypatch, tmp_path, google_on: bool = True, domain: str | None = None):
    monkeypatch.chdir(tmp_path)
    if google_on:
        monkeypatch.setenv("AICEFR_GOOGLE_CLIENT_ID", CLIENT_ID)
        # Built, not written out, so the secret scanner sees no literal.
        monkeypatch.setenv("AICEFR_GOOGLE_CLIENT_SECRET", "x" * 24)
    if domain:
        monkeypatch.setenv("AICEFR_GOOGLE_DOMAIN", domain)
    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    return main


@pytest.fixture
def m(tmp_path, monkeypatch):
    return make_app(monkeypatch, tmp_path)


def login_as(m, pseudonym: str, role: str = "student", agent: str = CHROME_MAC) -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    return sign_in(m, pseudonym, agent)


def sign_in(m, pseudonym: str, agent: str = CHROME_MAC) -> TestClient:
    client = TestClient(m.app, headers={"user-agent": agent})
    r = client.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client


def account_id(m, pseudonym: str) -> str:
    return m.app.state.auth_repo.get_by_pseudonym(pseudonym)["account_id"]


def audit(m, action: str) -> list:
    return [e for e in m.audit(500) if e.action == action]


# ---------------------------------------------------------------- a stand-in Google


def id_token(claims: dict) -> str:
    def part(obj: dict) -> str:
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{part({'alg': 'RS256', 'typ': 'JWT'})}.{part(claims)}.c2lnbmF0dXJl"


def claims_for(flow: google.Flow, sub: str = "google-sub-1", **extra) -> dict:
    now = int(time.time())
    base = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "azp": CLIENT_ID,
        "sub": sub,
        "email": "sinhvien@example.edu.vn",
        "email_verified": True,
        "iat": now,
        "exp": now + 3600,
        "nonce": flow.nonce,
    }
    base.update(extra)
    return {k: v for k, v in base.items() if v is not None}


def start(client: TestClient, mode: str = "login", next_path: str = ""):
    r = client.get(f"/auth/google/start?mode={mode}&next={next_path}", follow_redirects=False)
    assert r.status_code == 303, r.text
    key = client.app.state.auth_repo.secret("google_flow")
    flow = google.decode_flow(client.cookies.get(google.COOKIE_NAME), key)
    return r, flow


def finish(monkeypatch, client: TestClient, flow, state: str | None = None, **claims):
    sent: dict = {}

    def fake_post(url: str, fields: dict) -> dict:
        sent.update(fields, url=url)
        return {"id_token": id_token(claims_for(flow, **claims)), "token_type": "Bearer"}

    monkeypatch.setattr("aicefr.auth.google._post_form", fake_post)
    r = client.get(
        f"/auth/google/callback?code=4%2Fcode&state={state or flow.state}", follow_redirects=False
    )
    return r, sent


def google_note(response) -> str | None:
    return parse_qs(urlparse(response.headers["location"]).query).get("google", [None])[0]


# ================================================================= profile (FR-56)


def test_a_profile_takes_only_listed_avatars_and_goals(m):
    c = login_as(m, "SV-001")
    r = c.patch(
        "/api/v1/me/profile",
        json={"avatar_icon": "leaf", "avatar_color": "education", "daily_goal_s": 300},
    )
    assert r.status_code == 200, r.text
    profile = c.get("/api/v1/me/account").json()["profile"]
    assert profile == {"avatar_icon": "leaf", "avatar_color": "education", "daily_goal_s": 300}
    for bad in ({"avatar_icon": "<svg>"}, {"avatar_color": "red"}, {"daily_goal_s": 90}):
        assert c.patch("/api/v1/me/profile", json=bad).status_code == 422, bad
    entry = audit(m, "account.profile")[0]
    assert entry.detail == "avatar_color avatar_icon daily_goal_s"


def test_the_daily_goal_sets_the_target_on_the_path_page(m):
    c = login_as(m, "SV-001")
    c.post("/api/v1/me/terms")
    assert c.get("/api/v1/learn").json()["today"]["goal_seconds"] == 180
    c.patch("/api/v1/me/profile", json={"daily_goal_s": 600})
    assert c.get("/api/v1/learn").json()["today"]["goal_seconds"] == 600


def test_the_sidebar_draws_the_chosen_avatar(m):
    c = login_as(m, "GV-01", "teacher")
    c.patch("/api/v1/me/profile", json={"avatar_icon": "plane", "avatar_color": "travel"})
    page = c.get("/review").text
    assert 'class="avatar avatar-travel"' in page
    assert "#i-plane" in page


def test_the_account_page_has_four_parts_for_a_student_and_three_for_staff(m):
    student = login_as(m, "SV-001").get("/account").text
    for tab in ("tab-profile", "tab-security", "tab-activity", "tab-data"):
        assert f'id="{tab}"' in student
    teacher = login_as(m, "GV-01", "teacher").get("/account").text
    assert 'id="tab-data"' not in teacher
    assert 'id="goal-chips"' not in teacher


# ================================================================= sessions (FR-57)


def test_a_person_sees_their_sessions_and_ends_one(m):
    here = login_as(m, "SV-001", agent=CHROME_MAC)
    phone = sign_in(m, "SV-001", agent=SAFARI_IPHONE)
    rows = here.get("/api/v1/me/sessions").json()
    assert len(rows) == 2
    devices = {r["device"]: r for r in rows}
    assert devices["Chrome · macOS"]["current"] is True
    assert devices["Safari · iPhone/iPad"]["current"] is False
    assert all(len(r["session_id"]) == 16 and r["method"] == "password" for r in rows)

    other = devices["Safari · iPhone/iPad"]["session_id"]
    assert here.delete(f"/api/v1/me/sessions/{other}").json() == {"revoked": True, "current": False}
    assert phone.get("/api/v1/me").status_code == 401
    assert here.delete(f"/api/v1/me/sessions/{other}").status_code == 404
    assert here.delete("/api/v1/me/sessions/not-a-session").status_code == 404

    mine = devices["Chrome · macOS"]["session_id"]
    assert here.delete(f"/api/v1/me/sessions/{mine}").json()["current"] is True
    assert here.get("/api/v1/me").status_code == 401


def test_sessions_of_one_account_cannot_be_ended_by_another(m):
    a = login_as(m, "SV-001")
    b = login_as(m, "SV-002")
    theirs = b.get("/api/v1/me/sessions").json()[0]["session_id"]
    assert a.delete(f"/api/v1/me/sessions/{theirs}").status_code == 404
    assert b.get("/api/v1/me").status_code == 200


# ================================================================= history (FR-58)


def test_the_history_shows_sign_ins_failed_attempts_and_changes(m):
    c = login_as(m, "SV-001")
    TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "doan-sai-roi"}
    )
    c.post(
        "/api/v1/me/password",
        json={"current_password": PASSWORD, "new_password": PASSWORD + "-moi"},
    )
    rows = c.get("/api/v1/me/activity").json()
    actions = [r["action"] for r in rows]
    assert actions[:3] == ["account.password_change", "auth.login_failed", "auth.login"]
    failed = rows[1]
    assert failed["detail"] == "wrong_password"
    assert rows[2]["detail"] == "method=password"


def test_what_an_administrator_did_shows_as_an_administrator(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    admin.post(f"/api/v1/admin/accounts/{account_id(m, 'SV-001')}/revoke-sessions")
    student = sign_in(m, "SV-001")
    row = next(
        r
        for r in student.get("/api/v1/me/activity").json()
        if r["action"] == "account.sessions_revoked"
    )
    assert row["by_self"] is False


def test_an_unknown_pseudonym_leaves_nothing_in_the_audit_log(m):
    TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "<script>x</script>", "password": "a"}
    )
    assert not audit(m, "auth.login_failed")


# ================================================================= Google (FR-59)


def test_google_is_off_until_configured(tmp_path, monkeypatch):
    m = make_app(monkeypatch, tmp_path, google_on=False)
    client = TestClient(m.app)
    assert 'id="google-login"' not in client.get("/login").text
    r = client.get("/auth/google/start", follow_redirects=False)
    assert r.headers["location"] == "/login?google=not_configured"


def test_start_sends_the_browser_to_google_with_state_nonce_and_pkce(m):
    client = TestClient(m.app)
    assert 'id="google-login"' in client.get("/login").text
    r, flow = start(client)
    target = urlparse(r.headers["location"])
    assert f"{target.scheme}://{target.netloc}{target.path}" == google.AUTH_ENDPOINT
    q = {k: v[0] for k, v in parse_qs(target.query).items()}
    assert q["client_id"] == CLIENT_ID
    assert q["redirect_uri"].endswith("/auth/google/callback")
    assert q["response_type"] == "code" and q["scope"] == "openid email"
    assert q["state"] == flow.state and q["nonce"] == flow.nonce
    assert q["code_challenge_method"] == "S256"
    assert q["code_challenge"] == google._challenge(flow.verifier)
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Path=/auth/google" in cookie and "SameSite=lax" in cookie


def test_linking_then_signing_in_with_google(m, monkeypatch, tmp_path):
    student = login_as(m, "SV-001")
    _, flow = start(student, "link")
    r, sent = finish(monkeypatch, student, flow, sub="google-sub-1")
    assert r.headers["location"] == "/account?google=linked"
    assert sent["code_verifier"] == flow.verifier and sent["grant_type"] == "authorization_code"
    assert student.get("/api/v1/me/account").json()["google"]["linked"] is True
    assert audit(m, "account.google_link")[0].target_id == account_id(m, "SV-001")

    # Only a hash is kept: the email is nowhere in the identity service's store.
    links = [i for a in store()["account"].find() for i in a.get("identities") or []]
    stored = links[0]["subject_hash"]
    assert stored == google.subject_hash("google-sub-1") and len(stored) == 64
    if not on_server:
        # Nothing the provider said about the person is kept anywhere in the store.
        from bson import json_util

        everything = {n: list(store()[n].find()) for n in store().list_collection_names()}
        assert "sinhvien@example.edu.vn" not in json_util.dumps(everything)

    browser = TestClient(m.app, headers={"user-agent": CHROME_MAC})
    _, flow = start(browser, "login", "/my-progress")
    r, _ = finish(monkeypatch, browser, flow, sub="google-sub-1")
    assert r.headers["location"] == "/my-progress"
    assert browser.get("/api/v1/me").json()["pseudonym"] == "SV-001"
    session = next(s for s in browser.get("/api/v1/me/sessions").json() if s["current"])
    assert session["method"] == "google"
    assert audit(m, "auth.login")[0].detail == "method=google"


def test_an_unlinked_google_account_cannot_sign_in_or_create_one(m, monkeypatch):
    before = len(m.app.state.auth_repo.list_accounts())
    browser = TestClient(m.app)
    _, flow = start(browser)
    r, _ = finish(monkeypatch, browser, flow, sub="nobody-linked-this")
    assert google_note(r) == "not_linked"
    assert browser.get("/api/v1/me").status_code == 401
    assert len(m.app.state.auth_repo.list_accounts()) == before
    assert google.MESSAGES["not_linked"] in browser.get("/login?google=not_linked").text


@pytest.mark.parametrize(
    "tamper, note",
    [
        ({"state": "forged-state"}, "state"),
        ({"nonce": "another-nonce"}, "token"),
        ({"aud": "someone-else.apps.googleusercontent.com"}, "token"),
        ({"iss": "https://evil.example"}, "token"),
        ({"exp": 1000}, "token"),
    ],
)
def test_a_forged_or_stale_round_trip_is_refused(m, monkeypatch, tamper, note):
    login_as(m, "SV-001")
    browser = TestClient(m.app)
    _, flow = start(browser)
    state = tamper.pop("state", None)
    r, _ = finish(monkeypatch, browser, flow, state=state, **tamper)
    assert google_note(r) == note
    assert browser.get("/api/v1/me").status_code == 401


def test_a_callback_without_its_cookie_or_after_cancel_is_refused(m):
    browser = TestClient(m.app)
    r = browser.get("/auth/google/callback?code=x&state=y", follow_redirects=False)
    assert google_note(r) == "state"
    _, flow = start(browser)
    r = browser.get(
        f"/auth/google/callback?error=access_denied&state={flow.state}", follow_redirects=False
    )
    assert google_note(r) == "cancelled"


def test_one_google_account_links_to_one_pseudonym(m, monkeypatch):
    a = login_as(m, "SV-001")
    _, flow = start(a, "link")
    finish(monkeypatch, a, flow, sub="shared-google")
    b = login_as(m, "SV-002")
    _, flow = start(b, "link")
    r, _ = finish(monkeypatch, b, flow, sub="shared-google")
    assert r.headers["location"] == "/account?google=taken"
    assert b.get("/api/v1/me/account").json()["google"]["linked"] is False


def test_the_link_must_be_finished_by_the_account_that_started_it(m, monkeypatch):
    client = login_as(m, "SV-001")
    _, flow = start(client, "link")
    m.app.state.auth_repo.create_account("SV-002", PASSWORD, Role.STUDENT)
    client.post("/api/v1/auth/login", json={"pseudonym": "SV-002", "password": PASSWORD})
    r, _ = finish(monkeypatch, client, flow)
    assert r.headers["location"] == "/account?google=signin"


def test_the_domain_restriction_requires_a_verified_school_account(tmp_path, monkeypatch):
    m = make_app(monkeypatch, tmp_path, domain="example.edu.vn")
    student = login_as(m, "SV-001")
    r, flow = start(student, "link")
    assert parse_qs(urlparse(r.headers["location"]).query)["hd"] == ["example.edu.vn"]
    r, _ = finish(monkeypatch, student, flow)
    assert google_note(r) == "domain"
    _, flow = start(student, "link")
    r, _ = finish(monkeypatch, student, flow, hd="example.edu.vn", email_verified=False)
    assert google_note(r) == "unverified"
    _, flow = start(student, "link")
    r, _ = finish(monkeypatch, student, flow, hd="example.edu.vn")
    assert google_note(r) == "linked"


def test_a_disabled_account_cannot_sign_in_with_google(m, monkeypatch):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    _, flow = start(student, "link")
    finish(monkeypatch, student, flow, sub="g-2")
    admin.post(f"/api/v1/admin/accounts/{account_id(m, 'SV-001')}/disable")
    browser = TestClient(m.app)
    _, flow = start(browser)
    r, _ = finish(monkeypatch, browser, flow, sub="g-2")
    assert google_note(r) == "disabled"


def test_a_temporary_password_still_has_to_be_replaced_after_google(m, monkeypatch):
    admin = login_as(m, "QT-01", "admin")
    temporary = admin.post(
        "/api/v1/admin/accounts", json={"role": "student", "pseudonym": "SV-NEW"}
    ).json()["created"][0]["temporary_password"]
    newcomer = TestClient(m.app)
    newcomer.post("/api/v1/auth/login", json={"pseudonym": "SV-NEW", "password": temporary})
    _, flow = start(newcomer, "link")
    finish(monkeypatch, newcomer, flow, sub="g-3")
    browser = TestClient(m.app)
    _, flow = start(browser, "login", "/practice")
    r, _ = finish(monkeypatch, browser, flow, sub="g-3")
    assert r.headers["location"] == "/account?first=1"


def test_unlinking_google_by_the_person_or_an_administrator(m, monkeypatch):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    for who in ("self", "admin"):
        _, flow = start(student, "link")
        finish(monkeypatch, student, flow, sub="g-4")
        if who == "self":
            assert student.post("/api/v1/me/google/unlink").json() == {"linked": False}
        else:
            target = account_id(m, "SV-001")
            r = admin.post(f"/api/v1/admin/accounts/{target}/unlink-google")
            assert r.json()["google_linked"] is False
        browser = TestClient(m.app)
        _, flow = start(browser)
        r, _ = finish(monkeypatch, browser, flow, sub="g-4")
        assert google_note(r) == "not_linked"
    assert student.post("/api/v1/me/google/unlink").status_code == 404
    assert len(audit(m, "account.google_unlink")) == 2


# ================================================================= admin (FR-60)


def test_an_administrator_changes_a_role_but_not_their_own(m):
    admin = login_as(m, "QT-01", "admin")
    user = login_as(m, "SV-001")
    assert user.get("/api/v1/review/queue").status_code == 403
    target = account_id(m, "SV-001")
    r = admin.post(f"/api/v1/admin/accounts/{target}/role", json={"role": "teacher"})
    assert r.json() == {"account_id": target, "role": "teacher", "previous_role": "student"}
    assert user.get("/api/v1/review/queue").status_code == 200
    me = account_id(m, "QT-01")
    own = admin.post(f"/api/v1/admin/accounts/{me}/role", json={"role": "student"})
    assert own.status_code == 409
    assert audit(m, "account.role_change")[0].detail == "from=student to=teacher"


def test_an_administrator_signs_an_account_out_everywhere(m):
    admin = login_as(m, "QT-01", "admin")
    laptop = login_as(m, "SV-001")
    phone = sign_in(m, "SV-001", agent=SAFARI_IPHONE)
    target = account_id(m, "SV-001")
    assert admin.post(f"/api/v1/admin/accounts/{target}/revoke-sessions").json()["revoked"] == 2
    assert laptop.get("/api/v1/me").status_code == 401
    assert phone.get("/api/v1/me").status_code == 401
    me = account_id(m, "QT-01")
    assert admin.post(f"/api/v1/admin/accounts/{me}/revoke-sessions").status_code == 409


def test_the_account_detail_shows_sessions_link_and_history(m, monkeypatch):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    _, flow = start(student, "link")
    finish(monkeypatch, student, flow, sub="g-5")
    detail = admin.get(f"/api/v1/admin/accounts/{account_id(m, 'SV-001')}").json()
    assert detail["pseudonym"] == "SV-001" and detail["google_linked"] is True
    assert detail["google_linked_at"]
    assert detail["sessions"][0]["device"] == "Chrome · macOS"
    assert {"auth.login", "account.google_link"} <= {a["action"] for a in detail["activity"]}
    assert "password_hash" not in detail
    assert admin.get("/api/v1/admin/accounts/khong-co").status_code == 404
    assert student.get(f"/api/v1/admin/accounts/{account_id(m, 'SV-001')}").status_code == 403
