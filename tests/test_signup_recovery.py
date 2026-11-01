"""Self sign-up with an email and recovery codes for a forgotten password (D065, D071).

A student signs up with the email they sign in with, their full name and a
password; the system draws a pseudonym that stays inside. No mail is sent, so
a forgotten password is reset with a one-time recovery code: the code, with
the email, sets a new password at /forgot and is replaced by a new one each
time it is used. These tests run the real application through TestClient on
its own store.
"""

from __future__ import annotations

import importlib
import itertools
import re

import pytest
from fastapi.testclient import TestClient

from aicefr.auth import passwords
from aicefr.storage.auth_repository import MAX_FAILED_ATTEMPTS, Role

PASSWORD = "mot-cau-de-nho-123"
NEW_PASSWORD = "mot-cau-khac-456"
PSEUDONYM = re.compile(r"^SV-[0-9A-F]{6}$")
CODE = re.compile(r"^[a-z2-9]{4}(-[a-z2-9]{4}){3}$")


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


def recover(m, email: str, code: str, new: str = NEW_PASSWORD, client=None):
    c = client or TestClient(m.app)
    return c.post(
        "/api/v1/auth/recover",
        json={"email": email, "recovery_code": code, "new_password": new},
    )


def login(m, email: str, password: str) -> int:
    r = TestClient(m.app).post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.status_code


def actions(m) -> list[str]:
    return [e.action for e in m.audit(500)]


# ================================================================= codes


def test_recovery_codes_are_long_unlike_and_read_back_however_typed() -> None:
    codes = {passwords.recovery_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(CODE.match(c) for c in codes)
    code = next(iter(codes))
    assert passwords.normalize_code(code.upper().replace("-", " ")) == code
    assert passwords.normalize_code(f"  {code}  ") == code


# ================================================================= sign-up


def test_a_student_signs_up_with_a_password_and_is_signed_in(m) -> None:
    c, body = signup(m)
    assert PSEUDONYM.match(body["pseudonym"])
    assert CODE.match(body["recovery_code"])
    assert body["home"] == "/practice"
    me = c.get("/api/v1/me").json()
    assert me == {**me, "pseudonym": body["pseudonym"], "role": "student"}
    assert me["email"] == body["email"] and me["full_name"] == "Nguyễn Văn An"
    assert login(m, body["email"], PASSWORD) == 200
    # The pseudonym is an internal code now, not a second way in.
    assert login(m, body["pseudonym"], PASSWORD) == 401
    row = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])
    assert row["recovery_hash"] and body["recovery_code"] not in str(row)
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


# ================================================================= recovery


def test_the_recovery_code_sets_a_new_password_once(m) -> None:
    other_device, body = signup(m)
    pseudonym, code = body["email"], body["recovery_code"]

    r = recover(m, pseudonym, code)
    assert r.status_code == 200, r.text
    following = r.json()["recovery_code"]
    assert CODE.match(following) and following != code
    assert r.headers["cache-control"] == "no-store"

    assert login(m, pseudonym, NEW_PASSWORD) == 200
    assert login(m, pseudonym, PASSWORD) == 401
    # Whoever was signed in elsewhere is out.
    assert other_device.get("/api/v1/me").status_code == 401
    # Spent: the same code does not work twice; the new one does.
    assert recover(m, pseudonym, code, "lan-thu-ba-789").status_code == 401
    assert recover(m, pseudonym, following, "lan-thu-ba-789").status_code == 200
    assert "account.recover" in actions(m)


def test_the_code_is_read_however_it_was_typed(m) -> None:
    _, body = signup(m)
    typed = body["recovery_code"].upper().replace("-", "")
    assert recover(m, body["email"], typed).status_code == 200


def test_a_wrong_code_and_a_wrong_email_read_the_same(m) -> None:
    _, body = signup(m)
    wrong_code = recover(m, body["email"], passwords.recovery_code())
    wrong_name = recover(m, "khong.co@example.edu.vn", body["recovery_code"])
    assert wrong_code.status_code == wrong_name.status_code == 401
    assert wrong_code.json() == wrong_name.json()
    assert "auth.recover_failed" in actions(m)


def test_guessing_codes_locks_the_account_like_guessing_passwords(m) -> None:
    _, body = signup(m)
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert recover(m, body["email"], passwords.recovery_code()).status_code == 401
    # Locked now: even the right code waits, and so does the password.
    assert recover(m, body["email"], body["recovery_code"]).status_code == 429
    assert login(m, body["email"], PASSWORD) == 429


def test_an_unacceptable_new_password_spends_nothing(m) -> None:
    _, body = signup(m)
    r = recover(m, body["email"], body["recovery_code"], new="ngan")
    assert r.status_code == 422
    r = recover(m, body["email"], body["recovery_code"], new=body["pseudonym"] + "-x")
    assert r.status_code == 200
    row = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])
    assert row["failed_attempts"] == 0


def test_an_account_without_a_code_cannot_be_recovered(m) -> None:
    m.app.state.auth_repo.create_account("SV-CU01", PASSWORD, Role.STUDENT)
    assert recover(m, "SV-CU01", passwords.recovery_code()).status_code == 401
    assert login(m, "SV-CU01", PASSWORD) == 200


def test_a_disabled_account_cannot_be_recovered(m) -> None:
    _, body = signup(m)
    aid = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])["account_id"]
    m.app.state.auth_repo.set_disabled(aid, True)
    assert recover(m, body["email"], body["recovery_code"]).status_code == 401


def test_an_administrator_reset_voids_the_recovery_code(m) -> None:
    """Whoever took the account may have made a code; a reset shuts that door too."""
    _, body = signup(m)
    aid = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])["account_id"]
    m.app.state.auth_repo.set_temporary_password(aid)
    assert recover(m, body["email"], body["recovery_code"]).status_code == 401


# ================================================================= a code from the account page


def test_a_signed_in_person_makes_a_new_code_and_the_old_one_stops(m) -> None:
    c, body = signup(m)
    assert c.get("/api/v1/me/account").json()["recovery"]["issued_at"]
    r = c.post("/api/v1/me/recovery-code")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    fresh = r.json()["recovery_code"]
    assert recover(m, body["email"], body["recovery_code"]).status_code == 401
    assert recover(m, body["email"], fresh).status_code == 200


def test_making_a_code_needs_a_session(m) -> None:
    assert TestClient(m.app).post("/api/v1/me/recovery-code").status_code == 401


def test_the_history_shows_sign_up_and_recovery(m) -> None:
    c, body = signup(m)
    c.post("/api/v1/me/recovery-code")
    later = TestClient(m.app)
    recover(m, body["email"], passwords.recovery_code(), client=later)
    code = c.post("/api/v1/me/recovery-code").json()["recovery_code"]
    assert recover(m, body["email"], code, client=later).status_code == 200
    seen = {a["action"] for a in later.get("/api/v1/me/activity").json()}
    assert {"account.signup", "account.recovery_code", "account.recover"} <= seen
    assert "auth.recover_failed" in seen


def test_an_account_opened_with_google_gets_a_password_through_a_code(m) -> None:
    """D063 accounts have a random password nobody knows; a code is their way to one."""
    auth = m.app.state.auth_repo
    aid = auth.create_with_identity("google", "h" * 64)
    pseudonym = auth.get(aid)["pseudonym"]
    code = auth.issue_recovery_code(aid)
    assert recover(m, pseudonym, code).status_code == 200
    assert login(m, pseudonym, NEW_PASSWORD) == 200


# ================================================================= pages


def test_the_login_page_leads_to_sign_up_and_recovery(m) -> None:
    page = TestClient(m.app).get("/login").text
    assert 'href="/signup"' in page and 'href="/forgot"' in page


@pytest.mark.parametrize("path", ["/signup", "/forgot"])
def test_sign_up_and_recovery_pages_are_for_the_signed_out(m, path: str) -> None:
    visitor = TestClient(m.app)
    page = visitor.get(path)
    assert page.status_code == 200 and 'id="recovery-slip"' in page.text
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
