"""Classes (D054, D071, D075): who teaches whom.

D071: a class has one or more teachers. An administrator makes classes and
assigns teachers to them (a teacher who makes a class teaches it); one teacher
may teach many classes, and reviews only the work of their classes' members.
Students are added by email. D074: the roster shows the bands each student studies.

D075: one centre that places its learners itself -- no assessment tasks set
to a class: a teacher reviews and writes band paths.

D109: a class lets its teachers see its members' work, so a student joins
only by their own act. A teacher's email invites the student, who accepts or
declines on "Lớp của tôi" (/my-classes); or the student types the class's
join code. An administrator adds students directly. A member may leave.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, STAFF_ONLY, STUDENT_ONLY
from aicefr.contracts import CLASS_INVITED, CLASS_JOINED
from aicefr.infra.limits import InMemoryRateLimiter
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.db import now_iso

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_ADD = 200  # students in one request: a large lecture group
JOIN_TRIES_PER_MINUTE = 10  # a code is six of 31 characters: guessing one takes far more

_join_tries = InMemoryRateLimiter()


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    # D071: an administrator names the teachers (emails); a teacher who makes
    # a class teaches it, and these are added beside them.
    teachers: list[str] = Field(default_factory=list, max_length=20)


class MembersIn(BaseModel):
    # The students' emails.
    people: list[str] = Field(min_length=1, max_length=MAX_ADD)


class CodeIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)


class TeacherIn(BaseModel):
    email: str = Field(min_length=1, max_length=254, validation_alias=AliasChoices("email", "who"))


def _owned(class_id: str, account: Account) -> dict:
    """The class, if this account teaches it or administers; 404 otherwise."""
    found = svc().classrooms.get(class_id)
    if found is None or (
        account.role is not Role.ADMIN and account.account_id not in found["teacher_ids"]
    ):
        raise HTTPException(404, "không có lớp này")
    return found


def _announce(topic: str, payload: dict) -> None:
    """Tell whoever listens (the identity service emails, D109); a failure is logged.

    The class has changed already: an email that could not be announced must
    not undo it or fail the request.
    """
    bus = getattr(svc(), "bus", None)
    if bus is None:
        return
    try:
        bus.publish(topic, {**payload, "at": now_iso()})
    except Exception:  # noqa: BLE001 - the bus is down; the pages still show it
        logger.exception("could not announce %s", topic)


def _joined(class_id: str, account_id: str, via: str) -> None:
    rooms = svc().classrooms
    found = rooms.get(class_id) or {}
    _announce(
        CLASS_JOINED,
        {
            "class_id": class_id,
            "class_name": found.get("name", ""),
            "account_id": account_id,
            "via": via,
            "teacher_ids": list(found.get("teacher_ids", [])),
            "members": rooms.count_members(class_id),
        },
    )


def _person(email: str) -> dict | None:
    return svc().peers.identity.by_email(email=email.strip())


def _teacher_views(teacher_ids: list[str]) -> list[dict]:
    names = svc().peers.identity.display_names(account_ids=teacher_ids) if teacher_ids else {}
    return [{"account_id": t, "name": names.get(t, "?")} for t in teacher_ids]


def _people(account_ids: list[str]) -> list[dict]:
    """Students by name and email, sorted by name."""
    s = svc()
    found = {a: s.peers.identity.account(account_id=a) or {} for a in account_ids}
    rows = [
        {
            "account_id": a,
            "name": found[a].get("full_name") or found[a].get("email") or "?",
            "email": found[a].get("email"),
        }
        for a in account_ids
    ]
    return sorted(rows, key=lambda r: r["name"].lower())


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
    s.repo.write_audit(account.account_id, "class.create", made["class_id"], body.name.strip())
    return made


@router.get("/api/v1/classes", tags=["teacher"])
def list_classes(account: Account = STAFF_ONLY) -> list[dict]:
    """A teacher's classes; an administrator sees every class."""
    s = svc()
    mine = s.classrooms.of_teacher(None if account.role is Role.ADMIN else account.account_id)
    return [
        {
            **c,
            "teachers": _teacher_views(c["teacher_ids"]),
            "members": s.classrooms.count_members(c["class_id"]),
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
    bands = _bands_of(members)
    return {
        **found,
        "teachers": _teacher_views(found["teacher_ids"]),
        "members": [{**p, "bands": bands.get(p["account_id"])} for p in _people(members)],
        # D109: invited and not yet answered; they give the teacher nothing yet.
        "invited": _people(s.classrooms.invited_of(class_id)),
    }


@router.post("/api/v1/classes/{class_id}/members", tags=["teacher"])
def add_members(class_id: str, body: MembersIn, account: Account = STAFF_ONLY) -> dict:
    """Students by email: an administrator adds them, a teacher invites them (D109).

    Says what was added or invited, already a member, invited before and not
    yet answered (`pending`), not a student, or unknown.
    """
    s = svc()
    found = _owned(class_id, account)
    direct = account.role is Role.ADMIN
    added, invited, already, pending, not_students, unknown = [], [], [], [], [], []
    # An email is kept lower case: what was added is echoed as the system keeps it.
    for raw in dict.fromkeys(p.strip().lower() for p in body.people if p.strip()):
        who = _person(raw)
        if who is None:
            unknown.append(raw)
        elif who.get("role") != Role.STUDENT.value:
            # A teacher's or an administrator's address: said as such, not "not found".
            not_students.append(raw)
        elif direct:
            (added if s.classrooms.add_member(class_id, who["account_id"]) else already).append(raw)
        else:
            outcome = s.classrooms.invite(class_id, who["account_id"])
            {"invited": invited, "already": already, "pending": pending}[outcome].append(raw)
            if outcome == "invited":
                _announce(
                    CLASS_INVITED,
                    {
                        "class_id": class_id,
                        "class_name": found["name"],
                        "account_id": who["account_id"],
                        "by": account.account_id,
                    },
                )
    if added:
        s.repo.write_audit(account.account_id, "class.add_members", class_id, f"n={len(added)}")
    if invited:
        s.repo.write_audit(account.account_id, "class.invite", class_id, f"n={len(invited)}")
    return {
        "added": added,
        "invited": invited,
        "already": already,
        "pending": pending,
        "not_students": not_students,
        "unknown": unknown,
    }


@router.delete("/api/v1/classes/{class_id}/invites/{account_id}", tags=["teacher"])
def withdraw_invite(class_id: str, account_id: str, account: Account = STAFF_ONLY) -> dict:
    """Take back an invitation the student has not answered (D109)."""
    s = svc()
    _owned(class_id, account)
    if not s.classrooms.withdraw(class_id, account_id):
        raise HTTPException(404, "không có lời mời này")
    return {"withdrawn": account_id}


@router.post("/api/v1/classes/{class_id}/code", tags=["teacher"])
def new_join_code(class_id: str, account: Account = STAFF_ONLY) -> dict:
    """Turn the join code on, or change it: the old one stops working (D109)."""
    s = svc()
    _owned(class_id, account)
    code = s.classrooms.set_join_code(class_id, True)
    s.repo.write_audit(account.account_id, "class.code", class_id, "on")
    return {"join_code": code}


@router.delete("/api/v1/classes/{class_id}/code", tags=["teacher"])
def drop_join_code(class_id: str, account: Account = STAFF_ONLY) -> dict:
    """Nobody joins by code any more; the members stay (D109)."""
    s = svc()
    _owned(class_id, account)
    s.classrooms.set_join_code(class_id, False)
    s.repo.write_audit(account.account_id, "class.code", class_id, "off")
    return {"join_code": None}


@router.delete("/api/v1/classes/{class_id}/members/{account_id}", tags=["teacher"])
def remove_member(class_id: str, account_id: str, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    _owned(class_id, account)
    who = s.peers.identity.account(account_id=account_id)
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
        s.repo.write_audit(account.account_id, "class.add_teacher", class_id, who["account_id"])
    return {"added": added, "teachers": _teacher_views(s.classrooms.get(class_id)["teacher_ids"])}


@router.delete("/api/v1/classes/{class_id}/teachers/{account_id}", tags=["admin"])
def remove_teacher(class_id: str, account_id: str, account: Account = ADMIN_ONLY) -> dict:
    s = svc()
    _owned(class_id, account)
    if not s.classrooms.remove_teacher(class_id, account_id):
        raise HTTPException(404, "giảng viên này không dạy lớp này")
    s.repo.write_audit(account.account_id, "class.remove_teacher", class_id, account_id)
    return {"teachers": _teacher_views(s.classrooms.get(class_id)["teacher_ids"])}


@router.post("/api/v1/classes/{class_id}/archive", tags=["teacher"])
def archive_class(class_id: str, account: Account = STAFF_ONLY) -> dict:
    """End a class (D108): its teachers no longer see its members' work.

    The class, its roster, the results and the reviews are kept; restoring
    the class gives the access back.
    """
    s = svc()
    _owned(class_id, account)
    if s.classrooms.set_archived(class_id, True):
        s.repo.write_audit(account.account_id, "class.archive", class_id, None)
    return {"archived": True}


@router.post("/api/v1/classes/{class_id}/restore", tags=["teacher"])
def restore_class(class_id: str, account: Account = STAFF_ONLY) -> dict:
    """Open an archived class again (D108): its teachers see its members' work again.

    A teacher of the class or an administrator. To take a class from one
    teacher, an administrator removes that teacher from it instead.
    """
    s = svc()
    _owned(class_id, account)
    if s.classrooms.set_archived(class_id, False):
        s.repo.write_audit(account.account_id, "class.restore", class_id, None)
    return {"archived": False}


# ================================================================= students (D109)


def _mine(c: dict) -> dict:
    """What a student sees of a class: its name and teachers, never its code."""
    return {
        "class_id": c["class_id"],
        "name": c["name"],
        "archived": c["archived"],
        "teachers": _teacher_views(c["teacher_ids"]),
    }


@router.get("/api/v1/me/classes", tags=["student"])
def my_classes(account: Account = STUDENT_ONLY) -> dict:
    """The classes this student is in, and the invitations waiting for an answer."""
    rooms = svc().classrooms
    return {
        "classes": [_mine(c) for c in rooms.joined_by(account.account_id)],
        "invitations": [_mine(c) for c in rooms.invitations_of(account.account_id)],
    }


@router.post("/api/v1/me/classes/join", tags=["student"])
def join_by_code(body: CodeIn, account: Account = STUDENT_ONLY) -> dict:
    """Join a running class by the code its teacher gave out."""
    s = svc()
    if not _join_tries.hit(f"join {account.account_id}", JOIN_TRIES_PER_MINUTE):
        raise HTTPException(429, "nhập sai quá nhiều lần, thử lại sau một phút")
    found, joined = s.classrooms.join_by_code(body.code, account.account_id)
    if found is None:
        raise HTTPException(404, "mã lớp không đúng hoặc lớp đã kết thúc")
    if joined:
        s.repo.write_audit(account.account_id, "class.join", found["class_id"], "code")
        _joined(found["class_id"], account.account_id, "code")
    return {"class": _mine(found), "joined": joined}


@router.post("/api/v1/me/classes/{class_id}/accept", tags=["student"])
def accept_invite(class_id: str, account: Account = STUDENT_ONLY) -> dict:
    s = svc()
    if not s.classrooms.accept(class_id, account.account_id):
        raise HTTPException(404, "không có lời mời này")
    s.repo.write_audit(account.account_id, "class.join", class_id, "invite")
    _joined(class_id, account.account_id, "invite")
    return {"joined": True}


@router.post("/api/v1/me/classes/{class_id}/decline", tags=["student"])
def decline_invite(class_id: str, account: Account = STUDENT_ONLY) -> dict:
    s = svc()
    if not s.classrooms.decline(class_id, account.account_id):
        raise HTTPException(404, "không có lời mời này")
    s.repo.write_audit(account.account_id, "class.decline", class_id, None)
    return {"declined": True}


@router.post("/api/v1/me/classes/{class_id}/leave", tags=["student"])
def leave_class(class_id: str, account: Account = STUDENT_ONLY) -> dict:
    """The student leaves: the class's teachers no longer see their work."""
    s = svc()
    if not s.classrooms.remove_member(class_id, account.account_id):
        raise HTTPException(404, "bạn không ở trong lớp này")
    s.repo.write_audit(account.account_id, "class.leave", class_id, None)
    return {"left": True}
