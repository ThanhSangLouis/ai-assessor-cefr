"""Self sign-up with an email and a password (D065, D071); no recovery code (D081).

A student signs up with the email they sign in with, their full name and a
password; the system draws a pseudonym that stays inside. A forgotten password
is replaced with a code sent by email (D079, `test_d079_email.py`); the
one-time recovery code of D065 is gone, with its routes and its stored hash.
These tests run the real application through TestClient on its own store.
"""

from __future__ import annotations

import importlib
import itertools
import re

import pytest
from fastapi.testclient import TestClient

from aicefr.storage.auth_repository import Role

PASSWORD = "mot-cau-de-nho-123"
NEW_PASSWORD = "mot-cau-khac-456"
PSEUDONYM = re.compile(r"^SV-[0-9A-F]{6}$")


def make_app(monkeypatch, tmp_path, signup: bool = True, rate: int | None = None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_SELF_SIGNUP", "1" if signup else "0")
    if rate is not None:
        monkeypatch.setenv("AICEFR_LOGIN_RATE", str(rate))
    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    return main


@pytest.fixture
def m(tmp_path, monkeypatch):
    return make_app(monkeypatch, tmp_path)


_n = itertools.count(1)


def form(password: str = PASSWORD, **extra) -> dict:
    """A sign-up form with a fresh email each time."""
    return {
        "email": f"hoc.vien{next(_n)}@example.edu.vn",
        "full_name": "Nguyễn Văn An",
        "password": password,
        **extra,
    }


def signup(m, password: str = PASSWORD) -> tuple[TestClient, dict]:
    c = TestClient(m.app)
    r = c.post("/api/v1/auth/signup", json=form(password))
    assert r.status_code == 200, r.text
    return c, r.json()


def login(m, email: str, password: str) -> int:
    r = TestClient(m.app).post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.status_code


def actions(m) -> list[str]:
    return [e.action for e in m.audit(500)]


# ================================================================= sign-up


def test_a_student_signs_up_with_a_password_and_is_signed_in(m) -> None:
    c, body = signup(m)
    assert PSEUDONYM.match(body["pseudonym"])
    assert "recovery_code" not in body
    assert body["home"] == "/practice"
    me = c.get("/api/v1/me").json()
    assert me == {**me, "pseudonym": body["pseudonym"], "role": "student"}
    assert me["email"] == body["email"] and me["full_name"] == "Nguyễn Văn An"
    assert login(m, body["email"], PASSWORD) == 200
    # The pseudonym is an internal code now, not a second way in.
    assert login(m, body["pseudonym"], PASSWORD) == 401
    row = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])
    assert "recovery_hash" not in row and "recovery_issued_at" not in row
    assert "account.signup" in actions(m)


def test_a_sign_up_is_not_kept_by_the_browser(m) -> None:
    r = TestClient(m.app).post("/api/v1/auth/signup", json=form())
    assert r.headers["cache-control"] == "no-store"


def test_a_short_password_opens_no_account(m) -> None:
    before = len(m.app.state.auth_repo.list_accounts())
    r = TestClient(m.app).post("/api/v1/auth/signup", json=form("ngan"))
    assert r.status_code == 422
    assert "8 ký tự" in r.json()["detail"]
    assert len(m.app.state.auth_repo.list_accounts()) == before


def test_sign_up_chooses_no_pseudonym_and_no_role(m) -> None:
    """Extra fields are ignored: the pseudonym is drawn, the role is student."""
    r = TestClient(m.app).post(
        "/api/v1/auth/signup", json=form(pseudonym="NguyenVanA", role="admin")
    )
    assert r.status_code == 200
    assert PSEUDONYM.match(r.json()["pseudonym"])
    row = m.app.state.auth_repo.get_by_pseudonym(r.json()["pseudonym"])
    assert row["role"] == Role.STUDENT.value
    assert m.app.state.auth_repo.get_by_pseudonym("NguyenVanA") is None


def test_sign_up_can_be_turned_off(tmp_path, monkeypatch) -> None:
    m = make_app(monkeypatch, tmp_path, signup=False)
    c = TestClient(m.app, follow_redirects=False)
    assert c.post("/api/v1/auth/signup", json=form()).status_code == 404
    assert c.get("/signup").headers["location"] == "/login"
    assert c.get("/forgot").headers["location"] == "/login"
    page = c.get("/login").text
    assert 'id="signup-link"' not in page and 'id="forgot-link"' not in page


def test_sign_up_is_rate_limited_apart_from_login(tmp_path, monkeypatch) -> None:
    m = make_app(monkeypatch, tmp_path, rate=2)
    c = TestClient(m.app)
    codes = [c.post("/api/v1/auth/signup", json=form()).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    # The login count is its own: two sign-ups did not use it up.
    body = {"email": "khong.co@example.edu.vn", "password": PASSWORD}
    assert c.post("/api/v1/auth/login", json=body).status_code == 401


# ================================================================= no recovery code (D081)


def test_the_recovery_code_routes_are_gone(m) -> None:
    c, body = signup(m)
    gone = {
        "email": body["email"],
        "recovery_code": "abcd-efgh-jkmn-pqrs",
        "new_password": "x" * 12,
    }
    assert TestClient(m.app).post("/api/v1/auth/recover", json=gone).status_code in (404, 405)
    assert c.post("/api/v1/me/recovery-code").status_code in (404, 405)
    assert "recovery" not in c.get("/api/v1/me/account").json()


def test_migration_12_removes_the_stored_codes(tmp_path) -> None:
    from aicefr.storage.db import database
    from aicefr.storage.migrations import MIGRATIONS, migrate

    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:11]:
        step.apply(db, str(target))
    db["account"].insert_one(
        {"account_id": "a1", "recovery_hash": "$2b$x", "recovery_issued_at": "2026-10-01"}
    )
    migrate(target)
    row = db["account"].find_one({"account_id": "a1"}, {"_id": 0})
    assert "recovery_hash" not in row and "recovery_issued_at" not in row


# ================================================================= pages


def test_the_login_page_leads_to_sign_up_and_a_forgotten_password(m) -> None:
    page = TestClient(m.app).get("/login").text
    assert 'href="/signup"' in page and 'href="/forgot"' in page


@pytest.mark.parametrize("path", ["/signup", "/forgot"])
def test_sign_up_and_forgot_pages_are_for_the_signed_out(m, path: str) -> None:
    visitor = TestClient(m.app)
    page = visitor.get(path)
    assert page.status_code == 200 and "khôi phục" not in page.text
    c, _ = signup(m)
    c.follow_redirects = False
    r = c.get(path)
    assert r.status_code == 303 and r.headers["location"] == "/practice"


def test_the_login_page_puts_both_links_inside_the_form_card(m) -> None:
    """Both links sit under the sign-in card, after the page heading, not above the page."""
    page = TestClient(m.app).get("/login").text
    heading = page.index('id="login-h"')
    assert heading < page.index('id="forgot-link"') < page.index('id="signup-link"')
    assert page.count("auth-help") == 1
