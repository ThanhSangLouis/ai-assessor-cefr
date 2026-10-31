"""Layer 2 -- INTEGRATION: the signed Google round trip and its settings page (D036).

Same set-up as `test_profile.py`: the real app through TestClient, Google
replaced at `aicefr.auth.google._post_form`. Here the stand-in also counts its
calls, because the point of a signed flow cookie is that a forged one is
refused before Google is asked anything.

Test case ids (TC-GG-Ixx) are listed in `docs/test/TEST_PLAN_D036.md`; tests
named after an acceptance criterion carry the name given in SRS section 3.9i.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from test_profile import (
    CLIENT_ID,
    account_id,
    finish,
    google_note,
    login_as,
    make_app,
    start,
)

from aicefr.auth import google
from aicefr.storage.auth_repository import AuthRepository

pytestmark = pytest.mark.integration


def test_a_flow_cookie_this_server_did_not_sign_is_ignored(tmp_path, monkeypatch):
    m = make_app(monkeypatch, tmp_path)
    victim = login_as(m, "SV-001")
    asked: list[str] = []
    monkeypatch.setattr(
        "aicefr.auth.google._post_form", lambda url, fields: asked.append(url) or {}
    )
    # Someone able to set a cookie for this site writes a "link" flow for the
    # victim's account, with a verifier of their own, and signs it as best
    # they can: with a key of their own, or not at all.
    flow = google.new_flow("link", "", account_id(m, "SV-001"))
    for cookie in (google.encode_flow(flow, b"their-own-key"), google.encode_flow(flow, b"")[:-1]):
        victim.cookies.set(google.COOKIE_NAME, cookie, path="/auth/google")
        r = victim.get(
            f"/auth/google/callback?code=4%2Fstolen&state={flow.state}", follow_redirects=False
        )
        assert r.headers["location"] == "/login?google=state"

    assert asked == []  # Google was never asked to redeem the code
    assert victim.get("/api/v1/me/account").json()["google"]["linked"] is False


def test_behind_tls_the_flow_cookie_is_a_host_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("AICEFR_HTTPS_ONLY", "on")
    m = make_app(monkeypatch, tmp_path)
    login_as(m, "SV-001")
    linked = google.subject_hash("google-sub-1")
    m.app.state.auth_repo.link_identity(account_id(m, "SV-001"), google.PROVIDER, linked)
    browser = TestClient(m.app, base_url="https://testserver")

    r = browser.get("/auth/google/start?mode=login", follow_redirects=False)

    cookie = r.headers["set-cookie"]
    assert cookie.startswith("__Host-aicefr_oauth=")
    assert "Secure" in cookie and "Path=/;" in cookie and "HttpOnly" in cookie
    assert "Domain" not in cookie
    key = m.app.state.auth_repo.secret("google_flow")
    flow = google.decode_flow(browser.cookies.get(google.SECURE_COOKIE_NAME), key)
    done, _ = finish(monkeypatch, browser, flow, sub="google-sub-1")
    assert done.headers["location"] == "/practice"
    assert browser.get("/api/v1/me").json()["pseudonym"] == "SV-001"
    gone = [h for h in done.headers.get_list("set-cookie") if h.startswith("__Host-aicefr_oauth")]
    assert gone and "Max-Age=0" in gone[0]


def test_the_signing_key_is_made_once_and_kept(tmp_path, monkeypatch):
    m = make_app(monkeypatch, tmp_path)
    db = tmp_path / "aicefr.db"
    first = AuthRepository(db).secret("google_flow")

    assert len(first) == 32
    assert AuthRepository(db).secret("google_flow") == first  # another process
    assert AuthRepository(db).secret("something_else") != first
    # A round trip started before a restart finishes after it.
    login_as(m, "SV-001")
    linked = google.subject_hash("google-sub-1")
    m.app.state.auth_repo.link_identity(account_id(m, "SV-001"), google.PROVIDER, linked)
    browser = TestClient(m.app)
    _, flow = start(browser)
    cookie = browser.cookies.get(google.COOKIE_NAME)
    m = make_app(monkeypatch, tmp_path)  # restarted, same database
    again = TestClient(m.app)
    again.cookies.set(google.COOKIE_NAME, cookie, path="/auth/google")
    r, _ = finish(monkeypatch, again, flow, sub="google-sub-1")
    assert google_note(r) is None and r.headers["location"] == "/practice"


def test_the_administrator_sees_what_to_register_with_google(tmp_path, monkeypatch):
    m = make_app(monkeypatch, tmp_path)
    admin = login_as(m, "QT-01", "admin")

    seen = admin.get("/api/v1/admin/google").json()

    assert seen["enabled"] is True and seen["client_id"] == CLIENT_ID
    assert seen["redirect_uri"] == "http://testserver/auth/google/callback"
    assert seen["secret_set"] is True and "x" * 24 not in json.dumps(seen)
    assert seen["scopes"] == "openid email profile" and seen["linked_accounts"] == 0
    # http:// on a host that is not localhost: Google will not take it.
    assert any("AICEFR_PUBLIC_URL" in p for p in seen["problems"])
    for who, status in ((login_as(m, "GV-01", "teacher"), 403), (TestClient(m.app), 401)):
        assert who.get("/api/v1/admin/google").status_code == status

    from aicefr import config

    # Reached over https, but not told it runs behind TLS: the flow cookie
    # would not be a __Host- cookie, so the round trip does not start.
    monkeypatch.setenv("AICEFR_PUBLIC_URL", "https://cefr.example.edu.vn")
    monkeypatch.setenv("AICEFR_GOOGLE_CLIENT_ID", "1234-abc.apps.googleusercontent.com")
    config.get_settings.cache_clear()
    problems = admin.get("/api/v1/admin/google").json()["problems"]
    assert any("AICEFR_HTTPS_ONLY" in p for p in problems)
    browser = TestClient(m.app)
    refused = browser.get("/auth/google/start?mode=login", follow_redirects=False)
    assert refused.headers["location"] == "/login?google=insecure"
    assert (
        not browser.cookies
        and google.MESSAGES["insecure"] in browser.get("/login?google=insecure").text
    )

    monkeypatch.setenv("AICEFR_HTTPS_ONLY", "on")
    config.get_settings.cache_clear()
    seen = admin.get("/api/v1/admin/google").json()
    assert seen["redirect_uri"] == "https://cefr.example.edu.vn/auth/google/callback"
    assert seen["problems"] == [] and seen["flow_cookie"] == "__Host-aicefr_oauth"
    started = browser.get("/auth/google/start?mode=login", follow_redirects=False)
    assert started.headers["location"].startswith(google.AUTH_ENDPOINT)
    monkeypatch.setenv("AICEFR_PUBLIC_URL", "https://203.0.113.7")  # Google takes no raw IP
    config.get_settings.cache_clear()
    assert any("địa chỉ IP" in p for p in admin.get("/api/v1/admin/google").json()["problems"])
    monkeypatch.setenv("AICEFR_PUBLIC_URL", "http://[::1]:8000")  # loopback: allowed as is
    config.get_settings.cache_clear()
    assert admin.get("/api/v1/admin/google").json()["problems"] == []

    monkeypatch.delenv("AICEFR_GOOGLE_CLIENT_ID")
    monkeypatch.delenv("AICEFR_GOOGLE_CLIENT_SECRET")
    config.get_settings.cache_clear()
    off = admin.get("/api/v1/admin/google").json()
    assert off["enabled"] is False and off["client_id"] is None
    assert {"Chưa đặt AICEFR_GOOGLE_CLIENT_ID.", "Chưa đặt AICEFR_GOOGLE_CLIENT_SECRET."} <= set(
        off["problems"]
    )
