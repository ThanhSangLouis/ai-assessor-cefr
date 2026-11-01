"""Classes (D054, D071, D075): who teaches whom, members added by email, no assignments."""

from __future__ import annotations

import pytest
from test_billing import boot
from test_lessons_integration import login_as as _login_as


def login_as(m, pseudonym: str, role: str = "student"):
    """These tests are about classes: no class is arranged for them."""
    return _login_as(m, pseudonym, role, school=False)


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
    added = teacher.post(f"/api/v1/classes/{c['class_id']}/members", json={"people": ["SV-001"]})
    assert added.status_code == 200 and len(added.json()["added"]) == 1
    detail = teacher.get(f"/api/v1/classes/{c['class_id']}").json()
    assert [r["pseudonym"] for r in detail["members"]] == ["SV-001"]
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
