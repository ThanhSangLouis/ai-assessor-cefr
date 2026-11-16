"""Classes (D054, D071, D075, D108): who teaches whom, members added by email, no
assignments; an archived class gives its teachers no access until it is restored."""

from __future__ import annotations

import pytest
from dbutil import email_of
from test_billing import boot
from test_lessons_integration import login_as as _login_as
from test_lessons_integration import submit_assessment


def login_as(m, name: str, role: str = "student"):
    """These tests are about classes: no class is arranged for them."""
    return _login_as(m, name, role, school=False)


pytestmark = pytest.mark.integration


@pytest.fixture
def m(tmp_path, monkeypatch):
    return boot(tmp_path, monkeypatch)


def make_class(teacher, name: str = "Tiếng Anh 2 · nhóm 03") -> dict:
    r = teacher.post("/api/v1/classes", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_teacher_adds_students_and_sees_them_by_name(m):
    teacher = login_as(m, "GV-01", "teacher")
    login_as(m, "SV-001")
    c = make_class(teacher)
    added = teacher.post(
        f"/api/v1/classes/{c['class_id']}/members", json={"people": [email_of("SV-001")]}
    )
    assert added.status_code == 200 and len(added.json()["added"]) == 1
    detail = teacher.get(f"/api/v1/classes/{c['class_id']}").json()
    assert [r["email"] for r in detail["members"]] == [email_of("SV-001")]
    assert "assignments" not in detail and "code" not in detail  # D075
    assert teacher.get("/api/v1/classes").json()[0]["members"] == 1


def test_another_teachers_class_is_not_found(m):
    owner = login_as(m, "GV-01", "teacher")
    other = login_as(m, "GV-02", "teacher")
    admin = login_as(m, "QT-01", "admin")
    c = make_class(owner)
    assert other.get(f"/api/v1/classes/{c['class_id']}").status_code == 404
    assert other.get("/api/v1/classes").json() == []
    assert admin.get(f"/api/v1/classes/{c['class_id']}").status_code == 200


def test_students_cannot_make_classes_and_nobody_joins_with_a_code(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    assert student.post("/api/v1/classes", json={"name": "x"}).status_code == 403
    c = make_class(teacher)
    # D075: the centre places its learners; the join code and assignments are gone.
    assert student.post("/api/v1/me/classes/join", json={"code": "ABCDEF"}).status_code == 404
    assert student.get("/api/v1/me/assignments").status_code == 404
    url = f"/api/v1/classes/{c['class_id']}/assignments"
    assert teacher.post(url, json={"task_id": "P3", "due_on": "2030-01-01"}).status_code == 404


def test_the_pages_render(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    assert teacher.get("/teach/classes").status_code == 200
    assert c["class_id"] in teacher.get(f"/teach/classes/{c['class_id']}").text
    # The old address of the assignments goes to the path (D075).
    gone = student.get("/my-assignments", follow_redirects=False)
    assert (gone.status_code, gone.headers["location"]) == (301, "/practice")


def test_an_archived_class_gives_its_teachers_no_access_until_restored(m):
    # D108: archiving ends the teacher's access; the results and the class stay.
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    c = make_class(teacher)
    cid = c["class_id"]
    teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-001")]})
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 200

    assert teacher.post(f"/api/v1/classes/{cid}/archive").json() == {"archived": True}

    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 404
    assert teacher.get(f"/api/v1/responses/{rid}/audio").status_code == 404
    assert all(r["response_id"] != rid for r in teacher.get("/api/v1/review/queue").json())
    kept = teacher.get(f"/api/v1/classes/{cid}").json()
    assert kept["archived"] is True and len(kept["members"]) == 1  # the roster stays
    assert student.get(f"/api/v1/responses/{rid}").status_code == 200  # the result stays

    assert teacher.post(f"/api/v1/classes/{cid}/restore").json() == {"archived": False}
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 200
    actions = [e["action"] for e in login_as(m, "QT-01", "admin").get("/api/v1/audit").json()]
    assert "class.archive" in actions and "class.restore" in actions


def test_only_the_class_teachers_or_an_administrator_restore_it(m):
    owner = login_as(m, "GV-01", "teacher")
    other = login_as(m, "GV-02", "teacher")
    admin = login_as(m, "QT-01", "admin")
    cid = make_class(owner)["class_id"]
    owner.post(f"/api/v1/classes/{cid}/archive")
    assert other.post(f"/api/v1/classes/{cid}/restore").status_code == 404
    assert admin.post(f"/api/v1/classes/{cid}/restore").status_code == 200
    assert owner.get(f"/api/v1/classes/{cid}").json()["archived"] is False


def test_a_staff_address_is_said_not_to_be_a_student(m):
    teacher = login_as(m, "GV-01", "teacher")
    login_as(m, "GV-02", "teacher")
    cid = make_class(teacher)["class_id"]
    added = teacher.post(
        f"/api/v1/classes/{cid}/members",
        json={"people": [email_of("GV-02"), "khong-co@vidu.vn"]},
    ).json()
    assert added["not_students"] == [email_of("GV-02")]
    assert added["unknown"] == ["khong-co@vidu.vn"]
    assert added["added"] == []
