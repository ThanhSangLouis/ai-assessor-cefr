"""Classes and assignments (D054): a teacher sets an assessment task to a class, with a due day.

A teacher makes a class and hands out its join code, or adds students by
pseudonym; sets one of the assessment tasks with a due day; and sees, for each
assignment, who handed in on time, late or not yet, and how the class's bands
spread. A student joins with the code and sees what is set, what is due, and a
link that opens the submission screen on that task.

The submission is the response itself: an assessment of the assigned task by a
member, made after the task was set (`ClassroomRepository`). A teacher sees
pseudonyms only, as on every other staff screen.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import STAFF_ONLY, STUDENT_ONLY
from aicefr.contracts import Band
from aicefr.practice.streak import LOCAL_TZ
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.db import now_iso

router = APIRouter()

MAX_ADD = 200  # pseudonyms in one request: a large lecture group
NOT_SCORED = ("REJECTED", "FAILED")
WAITING = ("QUEUED", "RUNNING")


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class MembersIn(BaseModel):
    pseudonyms: list[str] = Field(min_length=1, max_length=MAX_ADD)


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
    found = svc().classrooms.get(class_id)
    if found is None or (
        account.role is not Role.ADMIN and found["teacher_id"] != account.account_id
    ):
        raise HTTPException(404, "không có lớp này")
    return found


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
    out = {}
    for account_id in members:
        r = latest.get(account_id)
        if r is None:
            state = "open" if now < assignment["due_at"] else "missing"
            out[account_id] = {"state": state}
            continue
        scored = r["status"] not in NOT_SCORED + WAITING
        out[account_id] = {
            "state": "on_time" if r["created_at"] < assignment["due_at"] else "late",
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
    made = s.classrooms.create(body.name.strip(), account.account_id)
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
            "members": s.classrooms.count_members(c["class_id"]),
            "assignments": per_class.get(c["class_id"], 0),
        }
        for c in mine
    ]


@router.get("/api/v1/classes/{class_id}", tags=["teacher"])
def class_detail(class_id: str, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    found = _owned(class_id, account)
    members = [m["account_id"] for m in s.classrooms.members(class_id)]
    names = s.peers.identity.pseudonyms(account_ids=members) if members else {}
    assignments = [_summary(a, standing(a, members)) for a in s.classrooms.assignments([class_id])]
    return {
        **found,
        "members": sorted(names.get(m, "?") for m in members),
        "assignments": assignments,
    }


@router.post("/api/v1/classes/{class_id}/members", tags=["teacher"])
def add_members(class_id: str, body: MembersIn, account: Account = STAFF_ONLY) -> dict:
    """Add students by pseudonym; what was added, already there, and unknown."""
    s = svc()
    _owned(class_id, account)
    added, already, unknown = [], [], []
    for raw in dict.fromkeys(p.strip().upper() for p in body.pseudonyms if p.strip()):
        who = s.peers.identity.by_pseudonym(pseudonym=raw)
        if who is None or who.get("role") != Role.STUDENT.value:
            unknown.append(raw)
        elif s.classrooms.add_member(class_id, who["account_id"]):
            added.append(raw)
        else:
            already.append(raw)
    if added:
        s.repo.write_audit(account.pseudonym, "class.add_members", class_id, f"n={len(added)}")
    return {"added": added, "already": already, "unknown": unknown}


@router.delete("/api/v1/classes/{class_id}/members/{pseudonym}", tags=["teacher"])
def remove_member(class_id: str, pseudonym: str, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    _owned(class_id, account)
    who = s.peers.identity.by_pseudonym(pseudonym=pseudonym)
    if who is None or not s.classrooms.remove_member(class_id, who["account_id"]):
        raise HTTPException(404, "sinh viên này không ở trong lớp")
    return {"removed": pseudonym}


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
    """Every member's state on one assignment, by pseudonym, with a link to the response."""
    s = svc()
    a = s.classrooms.assignment(assignment_id)
    if a is None:
        raise HTTPException(404, "không có bài được giao này")
    found = _owned(a["class_id"], account)
    members = [m["account_id"] for m in s.classrooms.members(a["class_id"])]
    states = standing(a, members)
    names = s.peers.identity.pseudonyms(account_ids=members) if members else {}
    rows = sorted(
        ({"pseudonym": names.get(m, "?"), **states[m]} for m in members),
        key=lambda r: r["pseudonym"],
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
