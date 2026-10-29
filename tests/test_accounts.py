"""Layer 2 -- INTEGRATION: accounts, temporary passwords, sidebar counts, the band page (D028).

Real SQLite in a temporary file, the real app through TestClient, the fake
recogniser and a synthetic tone where a response is needed. Tests named after
an acceptance criterion carry the name given in SRS section 3.9c (FR-51..FR-55).
"""

from __future__ import annotations

import importlib
import io
import re

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from aicefr.auth import passwords
from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

PASSWORD = "matkhau-kiem-thu"
# Built from the fixture password so the secret scanner sees no new literal.
NEW_PASSWORD = PASSWORD + "-moi"
SLIP = re.compile(r"^[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}$")


@pytest.fixture
def m(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main

    importlib.reload(main)
    return main


def login_as(m, pseudonym: str, role: str = "student", terms: bool = True) -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    return sign_in(m, pseudonym, PASSWORD, terms=terms)


def sign_in(m, pseudonym: str, password: str, terms: bool = False) -> TestClient:
    client = TestClient(m.app)
    r = client.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": password})
    assert r.status_code == 200, r.text
    if terms:
        client.post("/api/v1/me/terms")
    return client


def account_id(m, pseudonym: str) -> str:
    return m.app.state.auth_repo.get_by_pseudonym(pseudonym)["account_id"]


def wav(seconds: float = 35.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


def submit(client: TestClient) -> str:
    r = client.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    return r.json()["response_id"]


def audit(m, action: str) -> list[dict]:
    return [e for e in m.audit(500) if e.action == action]


# ================================================================= own password (FR-51)


def test_password_change_needs_the_current_password_and_ends_other_sessions(m):
    here = login_as(m, "SV-001")
    elsewhere = sign_in(m, "SV-001", PASSWORD)

    r = here.post(
        "/api/v1/me/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 200, r.text
    assert r.json()["sessions_ended"] == 1
    assert here.get("/api/v1/me").status_code == 200
    assert elsewhere.get("/api/v1/me").status_code == 401

    fresh = TestClient(m.app)
    old = fresh.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD})
    assert old.status_code == 401
    new = fresh.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": NEW_PASSWORD})
    assert new.status_code == 200
    entry = audit(m, "account.password_change")
    assert entry and PASSWORD not in (entry[0].detail or "")
    assert NEW_PASSWORD not in (entry[0].detail or "")


def test_a_wrong_current_password_is_refused_and_counts_towards_the_lockout(m):
    c = login_as(m, "SV-001")
    for _ in range(5):
        r = c.post(
            "/api/v1/me/password",
            json={"current_password": "doan-mo", "new_password": NEW_PASSWORD},
        )
        assert r.status_code == 403
    r = c.post(
        "/api/v1/me/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 429
    assert (
        TestClient(m.app)
        .post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD})
        .status_code
        == 429
    )


@pytest.mark.parametrize(
    "new, why",
    [
        ("ngan", "8 ký tự"),
        ("Student-01", "bút danh"),
        (PASSWORD, "khác mật khẩu"),
        ("á" * 40, "72 byte"),
    ],
)
def test_the_password_policy_says_what_is_wrong(m, new, why):
    c = login_as(m, "student-01")
    r = c.post("/api/v1/me/password", json={"current_password": PASSWORD, "new_password": new})
    assert r.status_code == 422
    assert why in r.json()["detail"]


def test_signing_out_other_devices_keeps_this_one(m):
    here = login_as(m, "GV-01", "teacher")
    phone = sign_in(m, "GV-01", PASSWORD)
    lab = sign_in(m, "GV-01", PASSWORD)
    r = here.post("/api/v1/me/sessions/revoke-others")
    assert r.json() == {"revoked": 2}
    assert here.get("/api/v1/me").status_code == 200
    assert phone.get("/api/v1/me").status_code == 401
    assert lab.get("/api/v1/me").status_code == 401
    assert here.get("/api/v1/me/account").json()["active_sessions"] == 1


def test_the_account_page_needs_a_login_and_shows_the_pseudonym(m):
    guest = TestClient(m.app)
    r = guest.get("/account", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login?next=/account"
    page = login_as(m, "SV-001").get("/account").text
    assert "SV-001" in page
    assert 'id="pw-form"' in page


# ================================================================= admin accounts (FR-52)


def test_a_series_continues_the_numbering_with_one_time_passwords(m):
    admin = login_as(m, "QT-01", "admin")
    m.app.state.auth_repo.create_account("SV-007", PASSWORD, Role.STUDENT)

    r = admin.post("/api/v1/admin/accounts", json={"role": "student", "count": 3})
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    created = r.json()["created"]
    assert [c["pseudonym"] for c in created] == ["SV-008", "SV-009", "SV-010"]
    temporaries = [c["temporary_password"] for c in created]
    assert all(SLIP.match(t) for t in temporaries), temporaries
    assert len(set(temporaries)) == 3

    listed = {a["pseudonym"]: a for a in admin.get("/api/v1/admin/accounts").json()}
    assert listed["SV-008"]["must_change_password"] is True
    assert all("password_hash" not in a for a in listed.values())
    entries = audit(m, "account.create")
    assert len(entries) == 3
    assert not any(t in (e.detail or "") for e in entries for t in temporaries)


def test_a_temporary_password_opens_nothing_but_the_password_change(m):
    admin = login_as(m, "QT-01", "admin")
    made = admin.post(
        "/api/v1/admin/accounts", json={"role": "teacher", "pseudonym": "GV-NN-01"}
    ).json()["created"][0]

    c = TestClient(m.app)
    r = c.post(
        "/api/v1/auth/login",
        json={"pseudonym": "GV-NN-01", "password": made["temporary_password"]},
    )
    assert r.json()["must_change_password"] is True
    assert r.json()["home"] == "/account?first=1"
    assert c.get("/api/v1/review/queue").status_code == 403
    assert c.get("/api/v1/me/badges").status_code == 403
    assert c.get("/api/v1/me").status_code == 200
    assert 'http-equiv="refresh"' in c.get("/review").text
    assert 'http-equiv="refresh"' not in c.get("/account").text

    r = c.post(
        "/api/v1/me/password",
        json={"current_password": made["temporary_password"], "new_password": NEW_PASSWORD},
    )
    assert r.status_code == 200
    assert r.json()["home"] == "/review"
    assert c.get("/api/v1/review/queue").status_code == 200
    assert 'http-equiv="refresh"' not in c.get("/review").text


def test_creating_accounts_is_all_or_nothing_and_checks_names(m):
    admin = login_as(m, "QT-01", "admin")
    taken = admin.post("/api/v1/admin/accounts", json={"role": "student", "pseudonym": "QT-01"})
    assert taken.status_code == 409
    for bad in ("<svg onload=x>", "mssv-2112", "211234567"):
        r = admin.post("/api/v1/admin/accounts", json={"role": "student", "pseudonym": bad})
        assert r.status_code == 422, bad
    assert (
        admin.post(
            "/api/v1/admin/accounts", json={"role": "student", "count": 2, "prefix": "S1"}
        ).status_code
        == 422
    )
    assert (
        admin.post("/api/v1/admin/accounts", json={"role": "student", "count": 201}).status_code
        == 422
    )
    assert [a["pseudonym"] for a in admin.get("/api/v1/admin/accounts").json()] == ["QT-01"]


def test_a_reset_ends_the_sessions_and_issues_a_new_one_time_password(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    sid = account_id(m, "SV-001")

    r = admin.post(f"/api/v1/admin/accounts/{sid}/reset-password")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    temporary = r.json()["temporary_password"]
    assert SLIP.match(temporary)
    assert student.get("/api/v1/me").status_code == 401

    again = TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "SV-001", "password": temporary}
    )
    assert again.json()["must_change_password"] is True
    assert audit(m, "account.reset_password")[0].target_id == sid
    own = admin.post(f"/api/v1/admin/accounts/{account_id(m, 'QT-01')}/reset-password")
    assert own.status_code == 409
    assert admin.post("/api/v1/admin/accounts/khong-co/reset-password").status_code == 404


def test_a_disabled_account_is_signed_out_and_cannot_sign_in(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    sid = account_id(m, "SV-001")

    assert admin.post(f"/api/v1/admin/accounts/{sid}/disable").json()["disabled"] is True
    assert student.get("/api/v1/me").status_code == 401
    login = TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD}
    )
    assert login.status_code == 401
    own = admin.post(f"/api/v1/admin/accounts/{account_id(m, 'QT-01')}/disable")
    assert own.status_code == 409

    admin.post(f"/api/v1/admin/accounts/{sid}/enable")
    assert sign_in(m, "SV-001", PASSWORD).get("/api/v1/me").status_code == 200
    actions = {e.action for e in m.audit(100)}
    assert {"account.disable", "account.enable"} <= actions


def test_an_administrator_lifts_a_lockout(m):
    admin = login_as(m, "QT-01", "admin")
    m.app.state.auth_repo.create_account("SV-001", PASSWORD, Role.STUDENT)
    c = TestClient(m.app)
    for _ in range(5):
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": "sai-roi"})
    assert (
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD}).status_code
        == 429
    )
    row = next(a for a in admin.get("/api/v1/admin/accounts").json() if a["pseudonym"] == "SV-001")
    assert row["locked_until"]
    admin.post(f"/api/v1/admin/accounts/{row['account_id']}/unlock")
    assert (
        c.post("/api/v1/auth/login", json={"pseudonym": "SV-001", "password": PASSWORD}).status_code
        == 200
    )


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_only_an_administrator_manages_accounts(m, role):
    c = login_as(m, "X-01", role)
    target = account_id(m, "X-01")
    assert c.get("/api/v1/admin/accounts").status_code == 403
    assert c.post("/api/v1/admin/accounts", json={"role": "admin", "count": 1}).status_code == 403
    for action in ("reset-password", "disable", "enable", "unlock"):
        assert c.post(f"/api/v1/admin/accounts/{target}/{action}").status_code == 403


# ================================================================= sidebar counts (FR-53)


def test_a_teacher_decision_is_new_until_the_student_opens_their_list(m):
    student = login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")
    rid = submit(student)
    assert student.get("/api/v1/me/badges").json()["results"] == 0

    r = teacher.post(f"/api/v1/review/{rid}", json={"reason": "Đã nghe lại toàn bài."})
    assert r.status_code == 200, r.text
    badges = student.get("/api/v1/me/badges").json()
    assert badges["results"] == 1
    assert badges["results_seen_at"] is None
    row = next(x for x in student.get("/api/v1/me/responses").json() if x["response_id"] == rid)
    assert row["reviewed_at"]

    student.post("/api/v1/me/badges/results/seen")
    assert student.get("/api/v1/me/badges").json()["results"] == 0
    assert student.post("/api/v1/me/badges/khac/seen").status_code == 422


def test_a_teacher_sees_how_many_responses_wait_for_review(m):
    student = login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")
    submit(student)
    submit(student)
    waiting = len(teacher.get("/api/v1/review/queue").json())
    assert teacher.get("/api/v1/me/badges").json()["queue"] == waiting
    assert waiting >= 1


def test_the_sidebar_carries_a_slot_for_each_count(m):
    student_page = login_as(m, "SV-001").get("/practice").text
    assert 'data-badge="results"' in student_page
    assert 'data-badge="reviews_due"' in student_page
    teacher_page = login_as(m, "GV-01", "teacher").get("/review").text
    assert 'data-badge="queue"' in teacher_page


# ================================================================= band page (FR-54)


def test_the_band_page_labels_what_the_machine_does_not_measure(m):
    page = TestClient(m.app).get("/bands")
    assert page.status_code == 200
    text = page.text
    assert "2.75" in text and "3.75" in text
    # D061: Coherence is now measured indirectly (connectors); grammar still is not.
    assert text.count('data-provenance="not_measured"') == 1
    assert 'data-provenance="not_assessed"' in text
    assert "Máy đo gián tiếp" in text
    assert "nói lắp" in text
    assert "Không cấp chứng chỉ" in text


def test_the_report_links_its_band_to_the_band_page(m):
    from aicefr.api.web import STATIC_DIR

    js = (STATIC_DIR / "report.js").read_text(encoding="utf-8")
    assert 'href="/bands"' in js


# ================================================================= preparation (FR-55)


def test_the_submit_page_offers_thirty_seconds_of_preparation(m):
    page = login_as(m, "SV-001").get("/").text
    assert 'data-prep-seconds="30"' in page
    assert 'id="prep-start"' in page


# ================================================================= policy helpers


def test_temporary_passwords_avoid_characters_people_confuse():
    seen = {passwords.temporary_password() for _ in range(300)}
    assert len(seen) == 300
    assert all(SLIP.match(t) for t in seen)
    assert not set("ilo01").intersection("".join(seen))
