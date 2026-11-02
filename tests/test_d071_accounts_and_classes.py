"""Accounts of real people, classes with teachers, review by class (D071).

* a person signs in with their email, by password or by Google: the same
  verified address is the same account; the pseudonym stays inside;
* an account made before D071 still signs in with its pseudonym until its
  owner adds an email, and changing an email needs the password;
* a class has one or more teachers, assigned by an administrator; a teacher
  reads and reviews only the work of their classes' members, by name; the
  work of a student in no class is the administrator's;
* migration 9 turns the one `teacher_id` of a class into `teacher_ids`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from test_lessons_integration import PASSWORD as OLD_PASSWORD
from test_lessons_integration import login_as as _login_as
from test_lessons_integration import m, submit_assessment  # noqa: F401
from test_profile import finish, start
from test_profile import make_app as profile_app

from aicefr.platform.callers import decode_account, encode_account
from aicefr.storage.auth_repository import Account, Role

PASSWORD = "mot-cau-de-nho-123"


def login_as(m, pseudonym: str, role: str = "student") -> TestClient:
    return _login_as(m, pseudonym, role, school=False)


def signup(m, email: str, name: str = "Nguyễn Văn An") -> tuple[TestClient, dict]:
    c = TestClient(m.app)
    r = c.post(
        "/api/v1/auth/signup", json={"email": email, "full_name": name, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return c, r.json()


def sign_in(m, identifier: str, password: str = PASSWORD) -> int:
    return (
        TestClient(m.app)
        .post("/api/v1/auth/login", json={"email": identifier, "password": password})
        .status_code
    )


# ================================================================= one email, one account


def test_the_email_is_the_way_in_and_one_account_per_email(m):
    _, body = signup(m, "An.Nguyen@Truong.edu.vn")
    assert body["email"] == "an.nguyen@truong.edu.vn"
    assert sign_in(m, "AN.NGUYEN@truong.edu.vn") == 200
    assert sign_in(m, body["pseudonym"]) == 401  # the pseudonym is an internal code now
    r = TestClient(m.app).post(
        "/api/v1/auth/signup",
        json={"email": "an.nguyen@truong.edu.vn", "full_name": "Khác", "password": PASSWORD},
    )
    assert r.status_code == 409


def test_an_older_account_adds_an_email_then_signs_in_with_it(m):
    old = login_as(m, "SV-001")
    assert sign_in(m, "SV-001", OLD_PASSWORD) == 200  # no email yet: the pseudonym opens it
    r = old.patch("/api/v1/me/contact", json={"email": "sv1@truong.edu.vn", "full_name": "Lê B"})
    assert r.status_code == 200 and r.json()["email"] == "sv1@truong.edu.vn"
    assert sign_in(m, "sv1@truong.edu.vn", OLD_PASSWORD) == 200
    assert sign_in(m, "SV-001", OLD_PASSWORD) == 401
    # Moving the account to another address needs its password.
    moved = old.patch("/api/v1/me/contact", json={"email": "khac@truong.edu.vn"})
    assert moved.status_code == 403
    moved = old.patch(
        "/api/v1/me/contact",
        json={"email": "khac@truong.edu.vn", "current_password": OLD_PASSWORD},
    )
    assert moved.status_code == 200, moved.text
    assert old.get("/api/v1/me").json()["full_name"] == "Lê B"


def test_a_taken_or_malformed_email_is_refused(m):
    signup(m, "a@truong.edu.vn")
    other = login_as(m, "SV-002")
    assert other.patch("/api/v1/me/contact", json={"email": "a@truong.edu.vn"}).status_code == 409
    assert other.patch("/api/v1/me/contact", json={"email": "khong-phai-email"}).status_code == 422


def test_the_gateway_carries_the_name_and_the_email():
    who = Account("a1", "SV-001", Role.STUDENT, email="a@b.vn", full_name="Trần Thị C")
    back = decode_account(encode_account(who))
    assert (back.email, back.full_name, back.display_name) == ("a@b.vn", "Trần Thị C", "Trần Thị C")


# ================================================================= Google, by the same email


def test_google_with_the_address_of_a_password_account_opens_that_account(tmp_path, monkeypatch):
    m = profile_app(monkeypatch, tmp_path)
    _, body = signup(m, "sinhvien@example.edu.vn")
    browser = TestClient(m.app)
    _, flow = start(browser)
    r, _ = finish(monkeypatch, browser, flow, sub="g-71", name="Nguyễn Văn An")
    assert r.status_code == 303 and "google=" not in r.headers["location"]
    assert browser.get("/api/v1/me").json()["pseudonym"] == body["pseudonym"]
    row = m.app.state.auth_repo.get_by_pseudonym(body["pseudonym"])
    assert row["email_verified"] == 1
    # The address was typed at sign-up, never proved: whoever typed it may not
    # own it, so the password it was given no longer opens the account.
    assert sign_in(m, "sinhvien@example.edu.vn") == 401


def test_a_new_google_account_brings_its_name_and_address(tmp_path, monkeypatch):
    m = profile_app(monkeypatch, tmp_path)
    browser = TestClient(m.app)
    _, flow = start(browser)
    finish(monkeypatch, browser, flow, sub="g-72", email="moi@example.edu.vn", name="Phạm D")
    me = browser.get("/api/v1/me").json()
    assert (me["email"], me["full_name"], me["role"]) == ("moi@example.edu.vn", "Phạm D", "student")


def test_an_address_google_has_not_verified_names_no_account(tmp_path, monkeypatch):
    m = profile_app(monkeypatch, tmp_path)
    _, body = signup(m, "sinhvien@example.edu.vn")
    browser = TestClient(m.app)
    _, flow = start(browser)
    finish(monkeypatch, browser, flow, sub="g-73", email_verified=False)
    me = browser.get("/api/v1/me").json()
    assert me["pseudonym"] != body["pseudonym"] and me["email"] is None


# ================================================================= classes and who reviews


def class_with(admin: TestClient, *teacher_emails: str) -> dict:
    r = admin.post(
        "/api/v1/classes", json={"name": "Tiếng Anh 2", "teachers": list(teacher_emails)}
    )
    assert r.status_code == 200, r.text
    return r.json()


def named(client: TestClient, email: str, name: str) -> None:
    r = client.patch("/api/v1/me/contact", json={"email": email, "full_name": name})
    assert r.status_code == 200, r.text


def test_an_administrator_assigns_teachers_and_a_teacher_has_many_classes(m):
    admin = login_as(m, "QT-01", "admin")
    one, two = login_as(m, "GV-01", "teacher"), login_as(m, "GV-02", "teacher")
    named(one, "gv1@truong.edu.vn", "Cô Hoa")
    named(two, "gv2@truong.edu.vn", "Thầy Nam")
    a = class_with(admin, "gv1@truong.edu.vn", "gv2@truong.edu.vn")
    b = class_with(admin, "gv1@truong.edu.vn")
    assert {c["class_id"] for c in one.get("/api/v1/classes").json()} == {
        a["class_id"],
        b["class_id"],
    }
    assert [c["class_id"] for c in two.get("/api/v1/classes").json()] == [a["class_id"]]
    assert two.get(f"/api/v1/classes/{b['class_id']}").status_code == 404
    names = [t["name"] for t in one.get(f"/api/v1/classes/{a['class_id']}").json()["teachers"]]
    assert names == ["Cô Hoa", "Thầy Nam"]
    # Only an administrator assigns or removes a teacher.
    r = one.post(f"/api/v1/classes/{b['class_id']}/teachers", json={"email": "gv2@truong.edu.vn"})
    assert r.status_code == 403
    r = admin.post(f"/api/v1/classes/{b['class_id']}/teachers", json={"email": "gv2@truong.edu.vn"})
    assert r.status_code == 200 and r.json()["added"] is True
    gv2 = m.app.state.auth_repo.get_by_pseudonym("GV-02")["account_id"]
    assert admin.delete(f"/api/v1/classes/{b['class_id']}/teachers/{gv2}").status_code == 200
    # A student is not a teacher.
    login_as(m, "SV-009")
    r = admin.post("/api/v1/classes", json={"name": "Lớp X", "teachers": ["SV-009"]})
    assert r.status_code == 422


def test_a_teacher_reviews_only_the_work_of_their_classes(m):
    admin = login_as(m, "QT-01", "admin")
    mine, other = login_as(m, "GV-01", "teacher"), login_as(m, "GV-02", "teacher")
    named(mine, "gv1@truong.edu.vn", "Cô Hoa")
    named(other, "gv2@truong.edu.vn", "Thầy Nam")
    inside, outside, nowhere = login_as(m, "SV-001"), login_as(m, "SV-002"), login_as(m, "SV-003")
    named(inside, "sv1@truong.edu.vn", "Nguyễn Văn An")
    named(outside, "sv2@truong.edu.vn", "Trần Thị Bình")
    a, b = class_with(admin, "gv1@truong.edu.vn"), class_with(admin, "gv2@truong.edu.vn")
    for cls, who in ((a, "sv1@truong.edu.vn"), (b, "sv2@truong.edu.vn")):
        r = admin.post(f"/api/v1/classes/{cls['class_id']}/members", json={"people": [who]})
        assert r.json()["added"] == [who]
    r_in, r_out, r_none = (submit_assessment(c) for c in (inside, outside, nowhere))

    assert mine.get(f"/api/v1/responses/{r_in}").status_code == 200
    for rid in (r_out, r_none):
        assert mine.get(f"/api/v1/responses/{rid}").status_code == 404
        assert mine.get(f"/api/v1/responses/{rid}/audio").status_code == 404
        assert mine.post(f"/api/v1/review/{rid}/lock").status_code == 404
        assert mine.get(f"/api/v1/responses/{rid}/history").status_code == 404
        r = mine.post(f"/api/v1/review/{rid}", json={"reason": "thử chấm bài lớp khác"})
        assert r.status_code == 404
    # The student in no class is the administrator's.
    assert admin.get(f"/api/v1/responses/{r_none}").status_code == 200
    assert admin.post(f"/api/v1/review/{r_none}/lock").status_code == 200

    detail = mine.get(f"/api/v1/classes/{a['class_id']}").json()
    assert [(s["name"], s["email"]) for s in detail["members"]] == [
        ("Nguyễn Văn An", "sv1@truong.edu.vn")
    ]


def test_the_queue_is_the_teachers_classes_by_name(m, monkeypatch):
    admin = login_as(m, "QT-01", "admin")
    mine = login_as(m, "GV-01", "teacher")
    named(mine, "gv1@truong.edu.vn", "Cô Hoa")
    inside, outside = login_as(m, "SV-001"), login_as(m, "SV-002")
    named(inside, "sv1@truong.edu.vn", "Nguyễn Văn An")
    a = class_with(admin, "gv1@truong.edu.vn")
    admin.post(f"/api/v1/classes/{a['class_id']}/members", json={"people": ["sv1@truong.edu.vn"]})
    rids = [submit_assessment(c) for c in (inside, outside)]
    from dbutil import store

    store()["response"].update_many(
        {"response_id": {"$in": rids}}, {"$set": {"status": "REVIEW_REQUIRED"}}
    )
    queue = mine.get("/api/v1/review/queue").json()
    assert [(q["response_id"], q["student_name"]) for q in queue] == [(rids[0], "Nguyễn Văn An")]
    assert {q["response_id"] for q in admin.get("/api/v1/review/queue").json()} == set(rids)
    assert mine.get("/api/v1/me/badges").json()["queue"] == 1
    assert admin.get("/api/v1/me/badges").json()["queue"] == 2


def test_migration_9_gives_an_old_class_its_teacher_as_a_list(tmp_path):
    from aicefr.storage import migrations
    from aicefr.storage.classroom_repository import Classroom
    from aicefr.storage.db import database

    target = str(tmp_path / "old.db")
    db = database(target)
    db["classroom"].insert_one(
        {"class_id": "lop-cu", "name": "Cũ", "code": "ABCDEF", "teacher_id": "gv-1",
         "created_at": "2026-10-01T00:00:00+00:00", "members": [], "assignments": []}
    )  # fmt: skip
    migrations._d071_class_teachers(db, target)
    doc = db["classroom"].find_one({"class_id": "lop-cu"})
    assert doc["teacher_ids"] == ["gv-1"] and "teacher_id" not in doc
    assert Classroom.from_doc(doc).teacher_ids == ["gv-1"]
