"""D101: free runs only with a verified email; a learner deletes their own account.

* An account that signed itself up gets the month's free runs and the day's
  free lesson recordings only once its email is verified; bought runs are
  spent either way; an account an administrator made (no email) keeps them.
* A student deletes their own account from the account page: the email (or
  pseudonym) typed again, recordings and reports erased, the account and its
  sessions gone; payments and the run ledger stay; staff cannot do it there.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from test_billing import boot
from test_lessons_integration import account_id, login_as, submit_assessment, wav

from aicefr.notify.email import outbox
from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.metering_repository import MeteredAction

pytestmark = pytest.mark.integration

# A test password, written as words so a secret scanner does not take it for a key.
PASSWORD = "-".join(["mot", "cau", "dai", "de", "nho", "789"])
EMAIL = "hoc.vien.moi@example.edu.vn"


@pytest.fixture
def m(tmp_path, monkeypatch):
    outbox().sent.clear()
    return boot(tmp_path, monkeypatch, AICEFR_METERING="on", AICEFR_EMAIL_PROVIDER="outbox")


def _signup(m, email: str = EMAIL) -> TestClient:
    c = TestClient(m.app)
    r = c.post(
        "/api/v1/auth/signup", json={"email": email, "full_name": "Trần Bình", "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return c


def _verify(c: TestClient) -> None:
    code = re.search(r"\b(\d{6})\b", outbox().sent[-1].text).group(1)
    assert c.post("/api/v1/me/email/verify", json={"code": code}).json() == {"verified": True}


def _me(c: TestClient) -> dict:
    return c.get("/api/v1/me/account").json()


def _submit(c: TestClient):
    return c.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(35.0), "audio/wav")},
        data={"task_id": "P3"},
    )


# ================================================================= free runs (FR-103)


def test_an_unverified_email_gets_no_free_runs(m):
    c = _signup(m)
    credits = c.get("/api/v1/me/credits").json()
    assert (credits["free_locked"], credits["free_runs_left"]) == (True, 0)
    assert credits["free_runs_per_cycle"] == 3
    assert c.get("/api/v1/me/credits/quote", params={"seconds": 60}).json()["free_locked"] is True
    refused = _submit(c)
    assert refused.status_code == 402, refused.text
    assert "Xác minh email" in refused.json()["detail"]


def test_verifying_the_email_opens_the_free_runs(m):
    c = _signup(m)
    _verify(c)
    credits = c.get("/api/v1/me/credits").json()
    assert (credits["free_locked"], credits["free_runs_left"]) == (False, 3)
    assert _submit(c).status_code == 202


def test_an_unverified_learner_still_spends_bought_runs(m):
    c = _signup(m)
    pseudonym = _me(c)["pseudonym"]
    admin = login_as(m, "QT-01", "admin")
    grant = {"pseudonym": pseudonym, "runs": 2, "reference": "phieu-d101"}
    assert admin.post("/api/v1/admin/credits/grant", json=grant).status_code == 200
    r = _submit(c)
    assert r.status_code == 202, r.text
    entry = m.core_parts.state["metering"].entry(r.json()["response_id"], MeteredAction.ASSESSMENT)
    assert entry["from_free"] == 0 and entry["from_wallet"] > 0


def test_no_free_lesson_recording_before_verifying(m):
    c = _signup(m)
    who = account_id(m, _me(c)["pseudonym"])
    quote = c.get("/api/v1/me/credits/lesson").json()
    assert (quote["free_locked"], quote["free_left_today"]) == (True, 0)
    refused = m.core_parts.facade.metering.hold_lesson(account_id=who, key="k1", max_seconds=30)
    assert refused["status"] == 402 and "Xác minh email" in refused["message"]
    # Nothing was counted for the day: the refusal gave the place back.
    today = MeteringFacade.today()
    assert m.core_parts.state["metering"].lesson_today(who, today) == {"used": 0, "free_used": 0}


def test_an_account_made_by_an_administrator_keeps_its_free_runs(m):
    student = login_as(m, "SV-101")  # no email: made by an administrator
    credits = student.get("/api/v1/me/credits").json()
    assert (credits["free_locked"], credits["free_runs_left"]) == (False, 3)
    assert submit_assessment(student)


# ================================================================= own deletion (FR-104)


def test_a_learner_deletes_their_own_account(m):
    student = login_as(m, "SV-102")
    who = account_id(m, "SV-102")
    submit_assessment(student)
    assert m.repo.list_by_account(who)
    r = student.post("/api/v1/me/delete-account", json={"confirm": "SV-102"})
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is True and r.json()["responses"] == 1
    assert m.repo.list_by_account(who) == []
    assert m.app.state.auth_repo.get(who) is None
    assert student.get("/api/v1/me/account").status_code == 401
    # The sign-in no longer works either.
    again = TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "SV-102", "password": "x" * 12}
    )
    assert again.status_code in (401, 404)


def test_the_confirmation_must_match_the_email(m):
    c = _signup(m)
    pseudonym = _me(c)["pseudonym"]
    wrong = c.post("/api/v1/me/delete-account", json={"confirm": pseudonym})
    assert wrong.status_code == 422 and "email" in wrong.json()["detail"]
    assert _me(c)["pseudonym"] == pseudonym  # nothing happened
    done = c.post("/api/v1/me/delete-account", json={"confirm": f"  {EMAIL.upper()} "})
    assert done.status_code == 200, done.text


def test_staff_cannot_delete_themselves_here(m):
    teacher = login_as(m, "GV-101", "teacher")
    r = teacher.post("/api/v1/me/delete-account", json={"confirm": "GV-101"})
    assert r.status_code == 403
    assert m.app.state.auth_repo.get(account_id(m, "GV-101")) is not None


def test_payments_and_the_ledger_stay(m):
    student = login_as(m, "SV-103")
    rid = submit_assessment(student)
    ledger = m.core_parts.state["metering"]
    assert ledger.entry(rid, MeteredAction.ASSESSMENT) is not None
    assert student.post("/api/v1/me/delete-account", json={"confirm": "sv-103"}).status_code == 200
    assert ledger.entry(rid, MeteredAction.ASSESSMENT) is not None


def test_the_account_page_offers_the_delete_card_to_students_only(m):
    page = login_as(m, "SV-104").get("/account").text
    assert 'id="delete-form"' in page and "Xoá vĩnh viễn" in page
    assert 'id="delete-form"' not in login_as(m, "GV-104", "teacher").get("/account").text
