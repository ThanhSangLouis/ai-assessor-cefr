"""Classes and assignments (D054, D071): the teachers of a class set it assessment tasks.

D071: a class has one or more teachers. An administrator makes classes and
assigns teachers to them (a teacher who makes a class teaches it); one teacher
may teach many classes, and reviews only the work of their classes' members.
Students are added by email (a pseudonym still works for an account made
before D071) or join with the class's code. The teachers set assessment tasks
with a due day and see, for each assignment, who handed in on time, late or not
yet, and how the class's bands spread -- by the students' full names.

The submission is the response itself: an assessment of the assigned task by a
member, made after the task was set (`ClassroomRepository`).
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, STAFF_ONLY, STUDENT_ONLY
from aicefr.contracts import Band
from aicefr.practice.streak import LOCAL_TZ
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.classroom_repository import as_assignment
from aicefr.storage.db import now_iso

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_ADD = 200  # students in one request: a large lecture group
NOT_SCORED = ("REJECTED", "FAILED")
WAITING = ("QUEUED", "RUNNING")


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    # D071: an administrator names the teachers (emails); a teacher who makes
    # a class teaches it, and these are added beside them.
    teachers: list[str] = Field(default_factory=list, max_length=20)


class MembersIn(BaseModel):
    # Emails; a pseudonym still names an account made before D071.
    people: list[str] = Field(
        min_length=1, max_length=MAX_ADD, validation_alias=AliasChoices("people", "pseudonyms")
    )


class TeacherIn(BaseModel):
    email: str = Field(min_length=1, max_length=254, validation_alias=AliasChoices("email", "who"))


class AssignmentIn(BaseModel):
    task_id: str = Field(min_length=1, max_length=40)
    due_on: date
    note: str = Field(default="", max_length=300)


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


def due_at(day: date) -> str:
    """The end of `day` in Vietnam, as the UTC stamp responses carry."""
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
    return end.astimezone(UTC).isoformat(timespec="seconds")


def _owned(class_id: str, account: Account) -> dict:
    """The class, if this account teaches it or administers; 404 otherwise."""
    found = svc().classrooms.get(class_id)
    if found is None or (
        account.role is not Role.ADMIN and account.account_id not in found["teacher_ids"]
    ):
        raise HTTPException(404, "không có lớp này")
    return found


def _person(identifier: str) -> dict | None:
    return svc().peers.identity.by_sign_in_name(identifier=identifier.strip())


def _teacher_views(teacher_ids: list[str]) -> list[dict]:
    names = svc().peers.identity.display_names(account_ids=teacher_ids) if teacher_ids else {}
    return [{"account_id": t, "name": names.get(t, "?")} for t in teacher_ids]


def _task_title(task_id: str) -> str:
    task = svc().tasks.get(task_id)
    return task.title if task else task_id


def standing(assignment: dict, members: list[str], now: str | None = None) -> dict[str, dict]:
    """Each member's state on one assignment: on_time, late, open or missing.

    The latest response counts: a student who tried again handed in the
    second attempt. `open` is not yet handed in with the due day still ahead.
    """
    now = now or now_iso()
    responses = svc().repo.assessments_since(
        members, assignment["task_id"], assignment["created_at"]
    )
    latest = {r["account_id"]: r for r in responses}
    due = as_assignment(assignment)
    out = {}
    for account_id in members:
        r = latest.get(account_id)
        if r is None:
            state = "open" if now < assignment["due_at"] else "missing"
            out[account_id] = {"state": state}
            continue
        scored = r["status"] not in NOT_SCORED + WAITING
        out[account_id] = {
            "state": "late" if due.is_late(r["created_at"]) else "on_time",
            "response_id": r["response_id"],
            "submitted_at": r["created_at"],
            "status": r["status"],
            "band": r["overall_band"] if scored else None,
            "teacher_verified": bool(r["teacher_verified"]),
        }
    return out


def _summary(assignment: dict, states: dict[str, dict]) -> dict:
    counts = Counter(s["state"] for s in states.values())
    bands = Counter(s["band"] for s in states.values() if s.get("band"))
    return {
        "assignment_id": assignment["assignment_id"],
        "task_id": assignment["task_id"],
        "task_title": _task_title(assignment["task_id"]),
        "note": assignment["note"],
        "due_on": assignment["due_on"],
        "created_at": assignment["created_at"],
        "members": len(states),
        "on_time": counts["on_time"],
        "late": counts["late"],
        "open": counts["open"],
        "missing": counts["missing"],
        "bands": {b: bands.get(b, 0) for b in (band.value for band in Band)},
        "verified": sum(1 for s in states.values() if s.get("teacher_verified")),
    }


# ================================================================= teachers


@router.post("/api/v1/classes", tags=["teacher"])
def create_class(body: ClassIn, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    teachers = [] if account.role is Role.ADMIN else [account.account_id]
    unknown = []
    for who in body.teachers:
        found = _person(who)
        if found is None or found["role"] != Role.TEACHER.value:
            unknown.append(who)
        else:
            teachers.append(found["account_id"])
    if unknown:
        raise HTTPException(422, "không phải tài khoản giảng viên: " + ", ".join(unknown))
    made = s.classrooms.create(body.name.strip(), teachers)
    s.repo.write_audit(account.pseudonym, "class.create", made["class_id"], body.name.strip())
    return made


@router.get("/api/v1/classes", tags=["teacher"])
def list_classes(account: Account = STAFF_ONLY) -> list[dict]:
    """A teacher's classes; an administrator sees every class."""
    s = svc()
    mine = s.classrooms.of_teacher(None if account.role is Role.ADMIN else account.account_id)
    ids = [c["class_id"] for c in mine]
    per_class = Counter(a["class_id"] for a in s.classrooms.assignments(ids))
    return [
        {
            **c,
            "teachers": _teacher_views(c["teacher_ids"]),
            "members": s.classrooms.count_members(c["class_id"]),
            "assignments": per_class.get(c["class_id"], 0),
        }
        for c in mine
    ]


def _bands_of(members: list[str]) -> dict[str, dict]:
    """The bands each member studies (D074), from the learning service; none if it is down."""
    learning = getattr(svc().peers, "learning", None)
    if learning is None or not members:
        return {}
    try:
        return learning.band_choices(account_ids=members)
    except Exception:  # noqa: BLE001 - the roster still shows without the bands
        logger.warning("class roster without bands: learning service did not answer")
        return {}


@router.get("/api/v1/classes/{class_id}", tags=["teacher"])
def class_detail(class_id: str, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    found = _owned(class_id, account)
    members = [m["account_id"] for m in s.classrooms.members(class_id)]
    people = {m: s.peers.identity.account(account_id=m) or {} for m in members}
    assignments = [_summary(a, standing(a, members)) for a in s.classrooms.assignments([class_id])]
    bands = _bands_of(members)
    roster = [
        {
            "account_id": m,
            "name": people[m].get("full_name") or people[m].get("pseudonym") or "?",
            "email": people[m].get("email"),
            "pseudonym": people[m].get("pseudonym"),
            "bands": bands.get(m),
        }
        for m in members
    ]
    return {
        **found,
        "teachers": _teacher_views(found["teacher_ids"]),
        "members": sorted(roster, key=lambda r: r["name"].lower()),
        "assignments": assignments,
    }


@router.post("/api/v1/classes/{class_id}/members", tags=["teacher"])
def add_members(class_id: str, body: MembersIn, account: Account = STAFF_ONLY) -> dict:
    """Add students by email (or legacy pseudonym); what was added, already there, unknown."""
    s = svc()
    _owned(class_id, account)
    added, already, unknown = [], [], []
    # An email is kept lower case, a pseudonym upper case: what was added is
    # echoed in the form the system keeps.
    typed = (p.strip() for p in body.people if p.strip())
    for raw in dict.fromkeys(p.lower() if "@" in p else p.upper() for p in typed):
        who = _person(raw)
        if who is None or who.get("role") != Role.STUDENT.value:
            unknown.append(raw)
        elif s.classrooms.add_member(class_id, who["account_id"]):
            added.append(raw)
        else:
            already.append(raw)
    if added:
        s.repo.write_audit(account.pseudonym, "class.add_members", class_id, f"n={len(added)}")
    return {"added": added, "already": already, "unknown": unknown}


@router.delete("/api/v1/classes/{class_id}/members/{account_id}", tags=["teacher"])
def remove_member(class_id: str, account_id: str, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    _owned(class_id, account)
    # By account id; a pseudonym still works for links made before D071.
    who = s.peers.identity.account(account_id=account_id) or s.peers.identity.by_pseudonym(
        pseudonym=account_id
    )
    if who is None or not s.classrooms.remove_member(class_id, who["account_id"]):
        raise HTTPException(404, "sinh viên này không ở trong lớp")
    return {"removed": account_id}


@router.post("/api/v1/classes/{class_id}/teachers", tags=["admin"])
def add_teacher(class_id: str, body: TeacherIn, account: Account = ADMIN_ONLY) -> dict:
    """Assign a teacher to a class (D071): only an administrator does."""
    s = svc()
    _owned(class_id, account)
    who = _person(body.email)
    if who is None or who["role"] != Role.TEACHER.value:
        raise HTTPException(422, "không có tài khoản giảng viên với email này")
    added = s.classrooms.add_teacher(class_id, who["account_id"])
    if added:
        s.repo.write_audit(account.pseudonym, "class.add_teacher", class_id, who["pseudonym"])
    return {"added": added, "teachers": _teacher_views(s.classrooms.get(class_id)["teacher_ids"])}


@router.delete("/api/v1/classes/{class_id}/teachers/{account_id}", tags=["admin"])
def remove_teacher(class_id: str, account_id: str, account: Account = ADMIN_ONLY) -> dict:
    s = svc()
    _owned(class_id, account)
    if not s.classrooms.remove_teacher(class_id, account_id):
        raise HTTPException(404, "giảng viên này không dạy lớp này")
    s.repo.write_audit(account.pseudonym, "class.remove_teacher", class_id, account_id)
    return {"teachers": _teacher_views(s.classrooms.get(class_id)["teacher_ids"])}


@router.post("/api/v1/classes/{class_id}/archive", tags=["teacher"])
def archive_class(class_id: str, account: Account = STAFF_ONLY) -> dict:
    """An archived class keeps its results; its code no longer lets anyone join."""
    _owned(class_id, account)
    svc().classrooms.set_archived(class_id, True)
    return {"archived": True}


@router.post("/api/v1/classes/{class_id}/assignments", tags=["teacher"])
def create_assignment(class_id: str, body: AssignmentIn, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    found = _owned(class_id, account)
    if found["archived"]:
        raise HTTPException(409, "lớp đã lưu trữ, không giao thêm bài")
    task = s.tasks.get(body.task_id)
    if task is None or task.is_practice:
        raise HTTPException(422, "chỉ giao được đề đánh giá đang mở")
    today = datetime.now(LOCAL_TZ).date()
    if body.due_on < today:
        raise HTTPException(422, "hạn nộp đã qua")
    made = s.classrooms.assign(
        class_id, body.task_id, body.due_on.isoformat(), due_at(body.due_on), body.note.strip(),
        account.account_id,
    )  # fmt: skip
    s.repo.write_audit(
        account.pseudonym, "class.assign", made["assignment_id"], f"{class_id} {body.task_id}"
    )
    return made


@router.get("/api/v1/assignments/{assignment_id}", tags=["teacher"])
def assignment_detail(assignment_id: str, account: Account = STAFF_ONLY) -> dict:
    """Every member's state on one assignment, by name, with a link to the response."""
    s = svc()
    a = s.classrooms.assignment(assignment_id)
    if a is None:
        raise HTTPException(404, "không có bài được giao này")
    found = _owned(a["class_id"], account)
    members = [m["account_id"] for m in s.classrooms.members(a["class_id"])]
    states = standing(a, members)
    names = s.peers.identity.display_names(account_ids=members) if members else {}
    rows = sorted(
        ({"name": names.get(m, "?"), **states[m]} for m in members),
        key=lambda r: r["name"].lower(),
    )
    return {"class_name": found["name"], **_summary(a, states), "students": rows}


@router.delete("/api/v1/assignments/{assignment_id}", tags=["teacher"])
def remove_assignment(assignment_id: str, account: Account = STAFF_ONLY) -> dict:
    """Withdraw an assignment. The responses stay: they are the students' work."""
    s = svc()
    a = s.classrooms.assignment(assignment_id)
    if a is None:
        raise HTTPException(404, "không có bài được giao này")
    _owned(a["class_id"], account)
    s.classrooms.remove_assignment(assignment_id)
    return {"removed": assignment_id}


# ================================================================= students


@router.post("/api/v1/me/classes/join", tags=["student"])
def join_class(body: JoinIn, account: Account = STUDENT_ONLY) -> dict:
    s = svc()
    found = s.classrooms.by_code(body.code)
    if found is None:
        raise HTTPException(404, "mã lớp không đúng hoặc lớp đã đóng")
    joined = s.classrooms.add_member(found["class_id"], account.account_id)
    return {"class_name": found["name"], "joined": joined}


@router.get("/api/v1/me/assignments", tags=["student"])
def my_assignments(account: Account = STUDENT_ONLY) -> dict:
    """What my classes set me: due first, then done, each with my state and a link."""
    return assignments_for(account.account_id)


def assignments_for(account_id: str) -> dict:
    """One student's assignments: to do (open or overdue) and done, with their classes."""
    s = svc()
    class_ids = s.classrooms.classes_of(account_id)
    classes = {c: s.classrooms.get(c) for c in class_ids}
    out = []
    for a in s.classrooms.assignments(class_ids):
        mine = standing(a, [account_id])[account_id]
        out.append(
            {
                "assignment_id": a["assignment_id"],
                "class_name": (classes.get(a["class_id"]) or {}).get("name", ""),
                "task_id": a["task_id"],
                "task_title": _task_title(a["task_id"]),
                "note": a["note"],
                "due_on": a["due_on"],
                **mine,
            }
        )
    todo = sorted((x for x in out if x["state"] in ("open", "missing")), key=lambda x: x["due_on"])
    done = [x for x in out if x["state"] in ("on_time", "late")]
    return {
        "classes": [c["name"] for c in classes.values() if c],
        "todo": todo,
        "done": done,
    }
