"""Email (D079): a code for a forgotten password, verifying the address, study reminders.

* signing up sends a code; the code verifies the address, once;
* a forgotten password: the same answer for any address, a code that lasts ten
  minutes and is spent once, a new password and every other session ended;
* with email off, the pages say so and the recovery code is the way in;
* the daily reminder: only to a verified address with reminders on, only when
  the learner has not spoken today and has a reason, once a day, and the link
  in it turns reminders off without signing in.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from test_billing import boot

from aicefr.notify import reminders
from aicefr.notify.email import outbox
from aicefr.notify.messages import code_email, reminder_email, unsubscribe_token
from aicefr.services.core.identity import email_api

# Test passwords, written as words so a secret scanner does not take them for keys.
PASSWORD = "-".join(["mot", "cau", "dai", "de", "nho", "123"])
NEW_PASSWORD = "-".join(["mot", "cau", "khac", "hoan", "toan", "456"])
EMAIL = "hoc.vien@example.edu.vn"


def _code() -> str:
    return re.search(r"\b(\d{6})\b", outbox().sent[-1].text).group(1)


@pytest.fixture
def m(tmp_path, monkeypatch):
    outbox().sent.clear()
    return boot(tmp_path, monkeypatch, AICEFR_EMAIL_PROVIDER="outbox")


def _signup(m) -> TestClient:
    c = TestClient(m.app)
    r = c.post(
        "/api/v1/auth/signup", json={"email": EMAIL, "full_name": "Nguyễn An", "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    assert r.json()["email_verification"] == "sent"
    return c


@pytest.mark.unit
def test_the_messages_say_what_they_are_for():
    code = code_email(EMAIL, "reset", "123456", 10)
    assert "123456" in code.subject and "10 phút" in code.text and "bỏ qua" in code.text
    stop = "https://x.vn/api/v1/email/unsubscribe?t=abc"
    note = reminder_email(EMAIL, "An", ["Chuỗi 3 ngày."], "https://x.vn", stop)
    assert note.headers["List-Unsubscribe"] == f"<{stop}>" and stop in note.text


@pytest.mark.integration
def test_signing_up_sends_a_code_that_verifies_the_address_once(m):
    c = _signup(m)
    assert c.get("/api/v1/me/email").json() == {
        "email": EMAIL,
        "verified": False,
        "reminders": True,
        "sending": True,
    }
    code = _code()
    assert c.post("/api/v1/me/email/verify", json={"code": "000000"}).status_code == 422
    assert c.post("/api/v1/me/email/verify", json={"code": code}).json() == {"verified": True}
    assert c.post("/api/v1/me/email/verify", json={"code": code}).status_code == 422  # spent
    assert c.get("/api/v1/me/email").json()["verified"] is True


@pytest.mark.integration
def test_a_forgotten_password_is_replaced_with_a_code_from_the_email(m):
    old = _signup(m)
    outbox().sent.clear()
    anon = TestClient(m.app)
    unknown = anon.post("/api/v1/auth/forgot/email", json={"email": "nobody@example.edu.vn"})
    known = anon.post("/api/v1/auth/forgot/email", json={"email": EMAIL})
    assert unknown.json() == known.json()  # nobody learns who has an account
    assert [e.to for e in outbox().sent] == [EMAIL]
    code = _code()
    # A second request within the minute sends nothing new.
    anon.post("/api/v1/auth/forgot/email", json={"email": EMAIL})
    assert len(outbox().sent) == 1

    body = {"email": EMAIL, "code": "999999", "new_password": NEW_PASSWORD}
    assert anon.post("/api/v1/auth/forgot/email/reset", json=body).status_code == 401
    done = anon.post("/api/v1/auth/forgot/email/reset", json={**body, "code": code})
    assert done.status_code == 200, done.text
    assert anon.get("/api/v1/me").status_code == 200  # signed in
    assert old.get("/api/v1/me").status_code == 401  # every other session ended
    again = anon.post("/api/v1/auth/forgot/email/reset", json={**body, "code": code})
    assert again.status_code == 401  # spent
    fresh = TestClient(m.app)
    login = fresh.post("/api/v1/auth/login", json={"email": EMAIL, "password": NEW_PASSWORD})
    assert login.status_code == 200
    assert fresh.get("/api/v1/me/email").json()["verified"] is True


@pytest.mark.integration
def test_with_email_off_the_recovery_code_is_the_way(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    anon = TestClient(m.app)
    assert anon.post("/api/v1/auth/forgot/email", json={"email": EMAIL}).status_code == 503
    page = anon.get("/forgot").text
    assert 'id="fe"' not in page and 'id="code"' in page


@pytest.mark.integration
def test_the_forgot_page_offers_the_email_code_first(m):
    page = TestClient(m.app).get("/forgot").text
    assert 'id="fe"' in page and "Dùng mã khôi phục thay cho email" in page


class Learning:
    def __init__(self, practiced: bool = False, streak: int = 3, reviews: int = 0) -> None:
        self.practiced, self.streak, self.reviews = practiced, streak, reviews

    def daily(self, account_id: str, goal_seconds: int) -> dict:
        return {"practiced_today": self.practiced, "streak": self.streak}

    def reviews_due(self, account_id: str) -> int:
        return self.reviews


EVENING = datetime(2026, 11, 2, 13, 0, tzinfo=UTC)  # 20:00 in Vietnam
MORNING = datetime(2026, 11, 2, 2, 0, tzinfo=UTC)  # 09:00


@pytest.mark.integration
def test_the_daily_reminder_goes_once_to_who_needs_it_and_stops_on_request(m):
    c = _signup(m)
    auth = m.app.state.auth_repo
    secret = b"k" * 32
    send = lambda learning, now=EVENING: reminders.send_due(  # noqa: E731
        now, 19, auth, learning, outbox(), "https://x.vn", secret
    )
    code = _code()  # sent with the account
    outbox().sent.clear()
    assert send(Learning()) == 0  # the address is not verified yet
    assert c.post("/api/v1/me/email/verify/send").json() == {"status": "wait"}  # within a minute
    c.post("/api/v1/me/email/verify", json={"code": code})
    outbox().sent.clear()

    assert send(Learning(), now=MORNING) == 0  # before the hour
    assert send(Learning(practiced=True)) == 0  # spoke today
    assert send(Learning(streak=0, reviews=0)) == 0  # no reason
    assert send(Learning()) == 1 and "Chuỗi 3 ngày" in outbox().sent[-1].text
    assert send(Learning()) == 0  # once a day

    account_id = c.get("/api/v1/me").json()["account_id"]
    link = f"/api/v1/email/unsubscribe?t={unsubscribe_token(email_api.svc().secret, account_id)}"
    assert "Đã tắt nhắc học" in TestClient(m.app).get(link).text
    assert c.get("/api/v1/me/email").json()["reminders"] is False
    forged = TestClient(m.app).get("/api/v1/email/unsubscribe?t=" + account_id + ".beef")
    assert "không hợp lệ" in forged.text
