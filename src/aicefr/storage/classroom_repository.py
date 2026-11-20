"""Classes: who teaches whom (D054, D071, D075).

One collection, `classroom`, one document per class (D060). The document is a
`Classroom`: a name, its teachers and its members, both many-to-many
associations with accounts kept as account ids. A teacher reviews only the
work of their classes' members (D071).

D075: one centre that places its learners in classes itself. A class sets no
assessments any more (the assignments of D054 are gone; a class document
from before keeps its old list, unread), and nobody joins with a code: an
administrator or a teacher adds members by email. A class from before keeps
its old join code, unread (migration 10 dropped its index).

D108: an archived class gives its teachers no access any more: they keep
seeing the class and its roster, but not its members' work, and its members'
recordings are no longer theirs to be told about. Restoring the class gives
the access back. The results and the reviews are kept either way.

D109: a student joins a class only by their own act, so that no teacher gives
themselves a student's work. A teacher invites by email and the student
accepts or declines (`invited`), or the student types the class's join code
(`join_code`, which the teacher turns on, changes or turns off). An
administrator still adds members directly: the centre places its learners.
A member may leave a class.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from aicefr.storage.db import MongoStore
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current


@dataclass
class Classroom:
    """A class: its teachers and its members.

    D071: a class has one or more teachers (`teacher_ids`), an administrator
    assigns them, and a teacher reviews only the work of their classes'
    members. One teacher may teach many classes.
    """

    class_id: str
    name: str
    created_at: str
    teacher_ids: list[str] = field(default_factory=list)  # account ids
    archived: bool = False
    members: list[str] = field(default_factory=list)  # account ids, in joining order
    invited: list[str] = field(default_factory=list)  # account ids not yet answered (D109)
    join_code: str | None = None  # None: nobody joins by code (D109)

    @classmethod
    def from_doc(cls, doc: dict) -> Classroom:
        return cls(
            class_id=doc["class_id"],
            name=doc["name"],
            # A document from before migration 9 still names one teacher.
            teacher_ids=list(doc.get("teacher_ids") or [t for t in [doc.get("teacher_id")] if t]),
            created_at=doc["created_at"],
            archived=bool(doc.get("archived", False)),
            members=list(doc.get("members", [])),
            invited=list(doc.get("invited", [])),
            join_code=doc.get("join_code"),
        )

    def to_doc(self) -> dict:
        doc = asdict(self)
        # No code is no field: the unique index covers only the classes that have one.
        if doc["join_code"] is None:
            del doc["join_code"]
        return doc

    def view(self) -> dict:
        """What the screens show of the class itself, without its members."""
        return {
            "class_id": self.class_id,
            "name": self.name,
            "teacher_ids": list(self.teacher_ids),
            "created_at": self.created_at,
            "archived": self.archived,
            "join_code": self.join_code,
        }


# A join code: six letters and digits, none that read as another (no 0/O, 1/I/L).
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_join_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def clean_code(raw: str) -> str:
    """A code as typed: case, spaces and dashes do not matter."""
    return "".join(ch for ch in raw.upper() if ch.isalnum())


# Only a class still running gives its teachers access to its members (D108).
ACTIVE = {"archived": {"$ne": True}}


class ClassroomRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def _load(self, query: dict) -> Classroom | None:
        doc = self.col("classroom").find_one(query)
        return Classroom.from_doc(doc) if doc else None

    # ------------------------------------------------------------ classes

    def create(self, name: str, teacher_ids: list[str]) -> dict:
        made = Classroom(
            class_id="lop-" + uuid.uuid4().hex[:10],
            name=name,
            teacher_ids=list(dict.fromkeys(teacher_ids)),
            created_at=_now(),
        )
        self.col("classroom").insert_one(made.to_doc())
        return made.view()

    def get(self, class_id: str) -> dict | None:
        found = self._load({"class_id": class_id})
        return found.view() if found else None

    def of_teacher(self, teacher_id: str | None) -> list[dict]:
        """A teacher's classes; every class when `teacher_id` is None (an administrator)."""
        query = {} if teacher_id is None else {"teacher_ids": teacher_id}
        rows = self.col("classroom").find(query).sort([("created_at", DESCENDING)])
        return [Classroom.from_doc(r).view() for r in rows]

    def set_archived(self, class_id: str, archived: bool) -> bool:
        """False when the class was in that state already."""
        done = self.col("classroom").update_one(
            {"class_id": class_id, "archived": {"$ne": archived}}, {"$set": {"archived": archived}}
        )
        return bool(done.modified_count)

    # ------------------------------------------------------------ teachers (D071)

    def add_teacher(self, class_id: str, account_id: str) -> bool:
        """False when the account teaches the class already."""
        done = self.col("classroom").update_one(
            {"class_id": class_id, "teacher_ids": {"$ne": account_id}},
            {"$push": {"teacher_ids": account_id}},
        )
        return bool(done.modified_count)

    def remove_teacher(self, class_id: str, account_id: str) -> bool:
        done = self.col("classroom").update_one(
            {"class_id": class_id, "teacher_ids": account_id},
            {"$pull": {"teacher_ids": account_id}},
        )
        return bool(done.modified_count)

    def teaches(self, teacher_id: str, student_id: str) -> bool:
        """Whether the student is a member of a class the teacher teaches and that
        is not archived (D108)."""
        found = self.col("classroom").find_one(
            {"teacher_ids": teacher_id, "members": student_id, **ACTIVE}, {"_id": 1}
        )
        return found is not None

    def students_of(self, teacher_id: str) -> set[str]:
        """Every member of every class the teacher teaches, archived classes aside (D108)."""
        rows = self.col("classroom").find({"teacher_ids": teacher_id, **ACTIVE}, {"members": 1})
        return {m for r in rows for m in r.get("members", [])}

    def teachers_of(self, student_id: str) -> set[str]:
        """Every teacher of every class the student is a member of (D086), archived
        classes aside (D108)."""
        rows = self.col("classroom").find({"members": student_id, **ACTIVE}, {"teacher_ids": 1})
        return {t for r in rows for t in r.get("teacher_ids", [])}

    # ------------------------------------------------------------ members

    def add_member(self, class_id: str, account_id: str) -> bool:
        """False when the account is in the class already.

        One conditional update: the account is appended only where it is not
        a member yet, so two joins at once add it once. An open invitation is
        answered by it (D109).
        """
        done = self.col("classroom").update_one(
            {"class_id": class_id, "members": {"$ne": account_id}},
            {"$push": {"members": account_id}, "$pull": {"invited": account_id}},
        )
        return bool(done.modified_count)

    # ------------------------------------------------------------ joining (D109)

    def invite(self, class_id: str, account_id: str) -> str:
        """ "invited", "already" (a member) or "pending" (invited before)."""
        done = self.col("classroom").update_one(
            {"class_id": class_id, "members": {"$ne": account_id}, "invited": {"$ne": account_id}},
            {"$push": {"invited": account_id}},
        )
        if done.modified_count:
            return "invited"
        found = self.col("classroom").find_one(
            {"class_id": class_id, "members": account_id}, {"_id": 1}
        )
        return "already" if found else "pending"

    def withdraw(self, class_id: str, account_id: str) -> bool:
        """The teacher takes an invitation back; False when there was none."""
        done = self.col("classroom").update_one(
            {"class_id": class_id, "invited": account_id}, {"$pull": {"invited": account_id}}
        )
        return bool(done.modified_count)

    def accept(self, class_id: str, account_id: str) -> bool:
        """The student takes up an invitation to a running class; False when there is none."""
        done = self.col("classroom").update_one(
            {"class_id": class_id, "invited": account_id, **ACTIVE},
            {"$pull": {"invited": account_id}, "$addToSet": {"members": account_id}},
        )
        return bool(done.modified_count)

    def decline(self, class_id: str, account_id: str) -> bool:
        return self.withdraw(class_id, account_id)

    def invitations_of(self, account_id: str) -> list[dict]:
        """The running classes that invite this student, newest first."""
        rows = (
            self.col("classroom")
            .find({"invited": account_id, **ACTIVE})
            .sort([("created_at", DESCENDING)])
        )
        return [Classroom.from_doc(r).view() for r in rows]

    def count_invitations(self, account_id: str) -> int:
        return self.col("classroom").count_documents({"invited": account_id, **ACTIVE})

    def joined_by(self, account_id: str) -> list[dict]:
        """The classes this account is a member of, running ones first, newest first."""
        rows = (
            self.col("classroom").find({"members": account_id}).sort([("created_at", DESCENDING)])
        )
        found = [Classroom.from_doc(r).view() for r in rows]
        return sorted(found, key=lambda c: c["archived"])

    def invited_of(self, class_id: str) -> list[str]:
        found = self._load({"class_id": class_id})
        return list(found.invited) if found else []

    def set_join_code(self, class_id: str, on: bool) -> str | None:
        """A new code for the class (the old one stops working), or none when `on` is False."""
        if not on:
            self.col("classroom").update_one({"class_id": class_id}, {"$unset": {"join_code": ""}})
            return None
        for _ in range(8):  # 31**6 codes: a clash is rare, eight in a row is not going to happen
            code = new_join_code()
            try:
                self.col("classroom").update_one(
                    {"class_id": class_id}, {"$set": {"join_code": code}}
                )
            except DuplicateKeyError:
                continue
            return code
        raise RuntimeError("no free join code")

    def join_by_code(self, code: str, account_id: str) -> tuple[dict | None, bool]:
        """The running class with this code, and whether the account was added to it.

        (None, False) when no running class has the code. An open invitation to
        that class is answered by joining.
        """
        cleaned = clean_code(code)
        if len(cleaned) != CODE_LENGTH:
            return None, False
        found = self._load({"join_code": cleaned, **ACTIVE})
        if found is None:
            return None, False
        return found.view(), self.add_member(found.class_id, account_id)

    def remove_member(self, class_id: str, account_id: str) -> bool:
        done = self.col("classroom").update_one(
            {"class_id": class_id, "members": account_id}, {"$pull": {"members": account_id}}
        )
        return bool(done.modified_count)

    def members(self, class_id: str) -> list[dict]:
        found = self._load({"class_id": class_id})
        return [{"account_id": m} for m in (found.members if found else [])]

    def classes_of(self, account_id: str) -> list[str]:
        rows = self.col("classroom").find({"members": account_id}, {"class_id": 1})
        return [r["class_id"] for r in rows]

    def count_members(self, class_id: str) -> int:
        found = self._load({"class_id": class_id})
        return len(found.members) if found else 0

    def forget_account(self, account_id: str) -> None:
        """Erasure (FR-37): the account leaves every class, as a member, a teacher or
        an invited student."""
        self.col("classroom").update_many(
            {"members": account_id}, {"$pull": {"members": account_id}}
        )
        self.col("classroom").update_many(
            {"teacher_ids": account_id}, {"$pull": {"teacher_ids": account_id}}
        )
        self.col("classroom").update_many(
            {"invited": account_id}, {"$pull": {"invited": account_id}}
        )
