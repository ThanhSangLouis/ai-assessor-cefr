"""Classes (D054, D071, D075, D108, D109): who teaches whom, no assignments; an
archived class gives its teachers no access until it is restored; a student
joins only by their own act -- an invitation they accept or the class's code."""

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


def join(teacher, student, name: str = "SV-001") -> str:
    """A class of the teacher's that the student has joined by accepting (D109)."""
    cid = make_class(teacher)["class_id"]
    teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of(name)]})
    assert student.post(f"/api/v1/me/classes/{cid}/accept").status_code == 200
    return cid


def test_an_administrator_adds_students_and_the_teacher_sees_them_by_name(m):
    # D109: the centre places its learners: an administrator adds directly.
    teacher = login_as(m, "GV-01", "teacher")
    admin = login_as(m, "QT-01", "admin")
    login_as(m, "SV-001")
    c = make_class(teacher)
    added = admin.post(
        f"/api/v1/classes/{c['class_id']}/members", json={"people": [email_of("SV-001")]}
    )
    assert added.status_code == 200 and added.json()["added"] == [email_of("SV-001")]
    detail = teacher.get(f"/api/v1/classes/{c['class_id']}").json()
    assert [r["email"] for r in detail["members"]] == [email_of("SV-001")]
    assert detail["invited"] == [] and "assignments" not in detail  # D075
    assert teacher.get("/api/v1/classes").json()[0]["members"] == 1


def test_another_teachers_class_is_not_found(m):
    owner = login_as(m, "GV-01", "teacher")
    other = login_as(m, "GV-02", "teacher")
    admin = login_as(m, "QT-01", "admin")
    c = make_class(owner)
    assert other.get(f"/api/v1/classes/{c['class_id']}").status_code == 404
    assert other.get("/api/v1/classes").json() == []
    assert admin.get(f"/api/v1/classes/{c['class_id']}").status_code == 200


def test_students_cannot_make_classes_and_classes_set_no_assessments(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    assert student.post("/api/v1/classes", json={"name": "x"}).status_code == 403
    assert student.get("/api/v1/classes").status_code == 403
    c = make_class(teacher)
    # D075: the assignments are gone.
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
    cid = join(teacher, student)
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


# ================================================================= D109


def test_an_invited_student_gives_the_teacher_nothing_until_they_accept(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    cid = make_class(teacher)["class_id"]
    sent = teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-001")]})
    assert sent.json()["invited"] == [email_of("SV-001")] and sent.json()["added"] == []
    again = teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-001")]})
    assert again.json()["pending"] == [email_of("SV-001")]

    # Invited is not a member: the teacher sees no work yet.
    detail = teacher.get(f"/api/v1/classes/{cid}").json()
    assert detail["members"] == [] and [r["email"] for r in detail["invited"]] == [
        email_of("SV-001")
    ]
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 404
    mine = student.get("/api/v1/me/classes").json()
    assert [c["class_id"] for c in mine["invitations"]] == [cid] and mine["classes"] == []
    assert "join_code" not in mine["invitations"][0]
    assert student.get("/api/v1/me/badges").json()["class_invites"] == 1

    assert student.post(f"/api/v1/me/classes/{cid}/accept").json() == {"joined": True}
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 200
    assert student.get("/api/v1/me/badges").json()["class_invites"] == 0
    assert [c["class_id"] for c in student.get("/api/v1/me/classes").json()["classes"]] == [cid]
    assert student.post(f"/api/v1/me/classes/{cid}/accept").status_code == 404  # answered


def test_a_declined_or_withdrawn_invitation_gives_no_access(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    other = login_as(m, "SV-002")
    rid = submit_assessment(student)
    cid = make_class(teacher)["class_id"]
    people = [email_of("SV-001"), email_of("SV-002")]
    teacher.post(f"/api/v1/classes/{cid}/members", json={"people": people})

    assert student.post(f"/api/v1/me/classes/{cid}/decline").json() == {"declined": True}
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 404
    other_id = next(
        r["account_id"] for r in teacher.get(f"/api/v1/classes/{cid}").json()["invited"]
    )
    assert teacher.delete(f"/api/v1/classes/{cid}/invites/{other_id}").status_code == 200
    assert other.post(f"/api/v1/me/classes/{cid}/accept").status_code == 404
    assert teacher.get(f"/api/v1/classes/{cid}").json()["invited"] == []


def test_a_student_joins_by_the_class_code_until_it_changes_or_goes(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    cid = make_class(teacher)["class_id"]
    assert teacher.get(f"/api/v1/classes/{cid}").json()["join_code"] is None
    code = teacher.post(f"/api/v1/classes/{cid}/code").json()["join_code"]
    assert len(code) == 6

    # Case, spaces and dashes do not matter.
    typed = f" {code[:3].lower()}-{code[3:]} "
    first = student.post("/api/v1/me/classes/join", json={"code": typed}).json()
    assert first["joined"] is True and first["class"]["class_id"] == cid
    assert "join_code" not in first["class"]
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 200
    assert student.post("/api/v1/me/classes/join", json={"code": code}).json()["joined"] is False

    late = login_as(m, "SV-002")
    changed = teacher.post(f"/api/v1/classes/{cid}/code").json()["join_code"]
    assert changed != code
    assert late.post("/api/v1/me/classes/join", json={"code": code}).status_code == 404
    teacher.delete(f"/api/v1/classes/{cid}/code")
    assert late.post("/api/v1/me/classes/join", json={"code": changed}).status_code == 404
    # An archived class takes nobody by code.
    again = teacher.post(f"/api/v1/classes/{cid}/code").json()["join_code"]
    teacher.post(f"/api/v1/classes/{cid}/archive")
    assert late.post("/api/v1/me/classes/join", json={"code": again}).status_code == 404


def test_another_teacher_neither_sees_nor_changes_a_class_code(m):
    owner = login_as(m, "GV-01", "teacher")
    other = login_as(m, "GV-02", "teacher")
    cid = make_class(owner)["class_id"]
    assert other.post(f"/api/v1/classes/{cid}/code").status_code == 404
    assert (
        other.post(f"/api/v1/classes/{cid}/members", json={"people": ["x@y.vn"]}).status_code == 404
    )


def test_a_student_who_leaves_takes_their_work_from_the_teacher(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    cid = join(teacher, student)
    assert student.post(f"/api/v1/me/classes/{cid}/leave").json() == {"left": True}
    assert teacher.get(f"/api/v1/responses/{rid}").status_code == 404
    assert student.get("/api/v1/me/classes").json()["classes"] == []
    assert student.post(f"/api/v1/me/classes/{cid}/leave").status_code == 404
    actions = [e["action"] for e in login_as(m, "QT-01", "admin").get("/api/v1/audit").json()]
    assert {"class.invite", "class.join", "class.leave"} <= set(actions)


def test_guessing_class_codes_is_limited(m):
    student = login_as(m, "SV-001")
    codes = [
        student.post("/api/v1/me/classes/join", json={"code": "ZZZZZ" + str(i % 10)}).status_code
        for i in range(12)
    ]
    assert codes[0] == 404 and codes[-1] == 429


def test_staff_have_no_my_classes_page(m):
    teacher = login_as(m, "GV-01", "teacher")
    gone = teacher.get("/my-classes", follow_redirects=False)
    assert (gone.status_code, gone.headers["location"]) == (303, "/teach/classes")
    assert login_as(m, "SV-001").get("/my-classes").status_code == 200
