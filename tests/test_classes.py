"""Classes and assignments (D054): set a task to a class, see who handed in, on time or late."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from test_billing import boot
from test_lessons_integration import login_as, submit_assessment

from aicefr.services.core.assessment.classes_api import due_at

pytestmark = pytest.mark.integration


def today() -> date:
    """Today in Vietnam, as the server counts due days -- not the test machine's UTC date."""
    from datetime import datetime

    from aicefr.practice.streak import LOCAL_TZ

    return datetime.now(LOCAL_TZ).date()


@pytest.fixture
def m(tmp_path, monkeypatch):
    return boot(tmp_path, monkeypatch)


def make_class(teacher, name: str = "Tiếng Anh 2 · nhóm 03") -> dict:
    r = teacher.post("/api/v1/classes", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


def assign(teacher, class_id: str, days: int = 3, task: str = "P3") -> dict:
    due = (today() + timedelta(days=days)).isoformat()
    r = teacher.post(
        f"/api/v1/classes/{class_id}/assignments", json={"task_id": task, "due_on": due}
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_a_student_joins_with_the_code_and_sees_the_assignment(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    assign(teacher, c["class_id"])
    joined = student.post("/api/v1/me/classes/join", json={"code": c["code"].lower()}).json()
    assert joined == {"class_name": c["name"], "joined": True}
    mine = student.get("/api/v1/me/assignments").json()
    assert [a["state"] for a in mine["todo"]] == ["open"] and mine["done"] == []


def test_a_submission_of_the_task_counts_as_handed_in(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student, _, idle = login_as(m, "SV-001"), login_as(m, "SV-002"), login_as(m, "SV-003")
    c = make_class(teacher)
    added = teacher.post(
        f"/api/v1/classes/{c['class_id']}/members",
        json={"pseudonyms": ["sv-001", "SV-002", "SV-404"]},
    ).json()
    assert (added["added"], added["unknown"]) == (["SV-001", "SV-002"], ["SV-404"])
    a = assign(teacher, c["class_id"])
    rid = submit_assessment(student)
    detail = teacher.get(f"/api/v1/assignments/{a['assignment_id']}").json()
    by = {s["pseudonym"]: s for s in detail["students"]}
    assert by["SV-001"]["state"] == "on_time" and by["SV-001"]["response_id"] == rid
    assert by["SV-002"]["state"] == "open"
    assert (detail["on_time"], detail["open"]) == (1, 1)
    assert student.get("/api/v1/me/assignments").json()["done"][0]["response_id"] == rid
    assert idle.get("/api/v1/me/assignments").json()["todo"] == []  # not in the class


def test_work_before_the_task_was_set_does_not_count(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    student.post("/api/v1/me/classes/join", json={"code": c["code"]})
    submit_assessment(student)
    a = assign(teacher, c["class_id"])
    # Set a moment later: stamps have a resolution of one second, and a
    # response in the same second as the assignment is given the benefit.
    from aicefr.services.core.assessment import context

    context.svc().classrooms.col("assignment").update_one(
        {"assignment_id": a["assignment_id"]}, {"$set": {"created_at": "9999-01-01T00:00:00+00:00"}}
    )
    assert teacher.get(f"/api/v1/assignments/{a['assignment_id']}").json()["open"] == 1


def test_a_submission_after_the_due_day_is_late(m):
    from aicefr.services.core.assessment import context

    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    student.post("/api/v1/me/classes/join", json={"code": c["code"]})
    a = assign(teacher, c["class_id"], days=0)
    yesterday = today() - timedelta(days=1)
    context.svc().classrooms.col("assignment").update_one(
        {"assignment_id": a["assignment_id"]},
        {"$set": {"due_on": yesterday.isoformat(), "due_at": due_at(yesterday)}},
    )
    submit_assessment(student)
    assert teacher.get(f"/api/v1/assignments/{a['assignment_id']}").json()["late"] == 1


def test_another_teachers_class_is_not_found(m):
    owner = login_as(m, "GV-01", "teacher", terms=False)
    other = login_as(m, "GV-02", "teacher", terms=False)
    admin = login_as(m, "QT-01", "admin", terms=False)
    c = make_class(owner)
    assert other.get(f"/api/v1/classes/{c['class_id']}").status_code == 404
    assert other.get("/api/v1/classes").json() == []
    assert admin.get(f"/api/v1/classes/{c['class_id']}").status_code == 200


def test_only_open_assessment_tasks_with_a_future_due_day_are_set(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    c = make_class(teacher)
    url = f"/api/v1/classes/{c['class_id']}/assignments"
    past = (today() - timedelta(days=1)).isoformat()
    soon = (today() + timedelta(days=1)).isoformat()
    assert teacher.post(url, json={"task_id": "P3", "due_on": past}).status_code == 422
    assert teacher.post(url, json={"task_id": "PR-FLU-A2", "due_on": soon}).status_code == 422
    assert teacher.post(url, json={"task_id": "KHONG-CO", "due_on": soon}).status_code == 422


def test_students_cannot_make_classes_and_teachers_cannot_join(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    assert student.post("/api/v1/classes", json={"name": "x"}).status_code == 403
    c = make_class(teacher)
    assert teacher.post("/api/v1/me/classes/join", json={"code": c["code"]}).status_code == 403


def test_an_archived_class_takes_no_one_new(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    teacher.post(f"/api/v1/classes/{c['class_id']}/archive")
    assert student.post("/api/v1/me/classes/join", json={"code": c["code"]}).status_code == 404


def test_the_pages_render(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = make_class(teacher)
    assert teacher.get("/teach/classes").status_code == 200
    assert c["class_id"] in teacher.get(f"/teach/classes/{c['class_id']}").text
    assert 'href="/my-assignments"' in student.get("/my-assignments").text
