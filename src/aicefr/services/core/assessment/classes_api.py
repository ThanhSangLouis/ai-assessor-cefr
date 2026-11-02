"""Classes (D054, D071, D075): who teaches whom.

D071: a class has one or more teachers. An administrator makes classes and
assigns teachers to them (a teacher who makes a class teaches it); one teacher
may teach many classes, and reviews only the work of their classes' members.
Students are added by email (a pseudonym still works for an account made
before D071). D074: the roster shows the bands each student studies.

D075: one centre that places its learners itself -- no join code, and no
assessment tasks set to a class: a teacher reviews and writes band paths.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import AliasChoices, BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, STAFF_ONLY
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account, Role

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_ADD = 200  # students in one request: a large lecture group


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
    people = {m: s.peers.identity.account(account_id=m) or {} for m in members}
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
    """An archived class keeps its results and its members."""
    _owned(class_id, account)
    svc().classrooms.set_archived(class_id, True)
    return {"archived": True}
