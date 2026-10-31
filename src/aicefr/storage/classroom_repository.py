"""Classes and the assessments a teacher sets them (D054).

One collection, `classroom`, one document per class (D060). The document is a
`Classroom`: a name, a join code the teacher hands out so students add
themselves, the members, and the assignments -- one task set to the class, due
at the end of a day. An assignment lives and dies with its class, so it is part
of the class's document, not a document of its own (the composition
`Classroom ◆ Assignment` of the class diagram). The members are a many-to-many
association with accounts: the class keeps the account ids, in the order they
joined, and no linking record stands between them.

What a student has done is not stored here: an assessment response of the
assigned task, made by a member after the task was set, is the submission, and
one made after the due day is late. The submission screen therefore needs no
new field, and a response a student made of their own accord counts too --
the work is the same work.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pymongo import DESCENDING

from aicefr.storage.db import IntegrityError, MongoStore
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

# Without 0/O and 1/I/L: a code read aloud in class or copied off a board.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


@dataclass
class Assignment:
    """One assessment task set to a class, due at the end of `due_on` (Vietnam)."""

    assignment_id: str
    task_id: str
    note: str
    due_on: str
    due_at: str  # the end of the due day as the UTC stamp responses carry
    created_by: str
    created_at: str

    def is_late(self, at: str) -> bool:
        """Whether a response made at `at` came after the due day."""
        return at >= self.due_at


@dataclass
class Classroom:
    """A class: its teachers, its join code, its members, what it was set.

    D071: a class has one or more teachers (`teacher_ids`), an administrator
    assigns them, and a teacher reviews only the work of their classes'
    members. One teacher may teach many classes.
    """

    class_id: str
    name: str
    code: str
    created_at: str
    teacher_ids: list[str] = field(default_factory=list)  # account ids
    archived: bool = False
    members: list[str] = field(default_factory=list)  # account ids, in joining order
    assignments: list[Assignment] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Classroom:
        return cls(
            class_id=doc["class_id"],
            name=doc["name"],
            code=doc["code"],
            # A document from before migration 9 still names one teacher.
            teacher_ids=list(doc.get("teacher_ids") or [t for t in [doc.get("teacher_id")] if t]),
            created_at=doc["created_at"],
            archived=bool(doc.get("archived", False)),
            members=list(doc.get("members", [])),
            assignments=[Assignment(**a) for a in doc.get("assignments", [])],
        )

    def to_doc(self) -> dict:
        return asdict(self)

    def view(self) -> dict:
        """What the screens show of the class itself, without members or assignments."""
        return {
            "class_id": self.class_id,
            "name": self.name,
            "code": self.code,
            "teacher_ids": list(self.teacher_ids),
            "created_at": self.created_at,
            "archived": self.archived,
        }


def _assignment_view(a: Assignment, class_id: str) -> dict:
    return {"class_id": class_id, **asdict(a)}


def as_assignment(view: dict) -> Assignment:
    """The assignment back from what the repository hands out."""
    return Assignment(**{k: view[k] for k in Assignment.__dataclass_fields__})


class ClassroomRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def _load(self, query: dict) -> Classroom | None:
        doc = self.col("classroom").find_one(query)
        return Classroom.from_doc(doc) if doc else None

    # ------------------------------------------------------------ classes

    def create(self, name: str, teacher_ids: list[str]) -> dict:
        for _ in range(8):
            made = Classroom(
                class_id="lop-" + uuid.uuid4().hex[:10],
                name=name,
                code=new_code(),
                teacher_ids=list(dict.fromkeys(teacher_ids)),
                created_at=_now(),
            )
            try:
                self.col("classroom").insert_one(made.to_doc())
            except IntegrityError:
                continue  # the code was taken: draw another
            return made.view()
        raise RuntimeError("could not draw a free join code")

    def get(self, class_id: str) -> dict | None:
        found = self._load({"class_id": class_id})
        return found.view() if found else None

    def by_code(self, code: str) -> dict | None:
        found = self._load({"code": code.strip().upper(), "archived": False})
        return found.view() if found else None

    def of_teacher(self, teacher_id: str | None) -> list[dict]:
        """A teacher's classes; every class when `teacher_id` is None (an administrator)."""
        query = {} if teacher_id is None else {"teacher_ids": teacher_id}
        rows = self.col("classroom").find(query).sort([("created_at", DESCENDING)])
        return [Classroom.from_doc(r).view() for r in rows]

    def set_archived(self, class_id: str, archived: bool) -> None:
        self.col("classroom").update_one({"class_id": class_id}, {"$set": {"archived": archived}})

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
        """Whether the student is a member of a class the teacher teaches, archived or not."""
        found = self.col("classroom").find_one(
            {"teacher_ids": teacher_id, "members": student_id}, {"_id": 1}
        )
        return found is not None

    def students_of(self, teacher_id: str) -> set[str]:
        """Every member of every class the teacher teaches."""
        rows = self.col("classroom").find({"teacher_ids": teacher_id}, {"members": 1})
        return {m for r in rows for m in r.get("members", [])}

    # ------------------------------------------------------------ members

    def add_member(self, class_id: str, account_id: str) -> bool:
        """False when the account is in the class already.

        One conditional update: the account is appended only where it is not
        a member yet, so two joins at once add it once.
        """
        done = self.col("classroom").update_one(
            {"class_id": class_id, "members": {"$ne": account_id}},
            {"$push": {"members": account_id}},
        )
        return bool(done.modified_count)

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
        """Erasure (FR-37): the account leaves every class, as a member or a teacher."""
        self.col("classroom").update_many(
            {"members": account_id}, {"$pull": {"members": account_id}}
        )
        self.col("classroom").update_many(
            {"teacher_ids": account_id}, {"$pull": {"teacher_ids": account_id}}
        )

    # ------------------------------------------------------------ assignments

    def assign(
        self, class_id: str, task_id: str, due_on: str, due_at: str, note: str, by: str
    ) -> dict:
        made = Assignment(
            assignment_id="bg-" + uuid.uuid4().hex[:10],
            task_id=task_id,
            note=note,
            due_on=due_on,
            due_at=due_at,
            created_by=by,
            created_at=_now(),
        )
        self.col("classroom").update_one(
            {"class_id": class_id}, {"$push": {"assignments": asdict(made)}}
        )
        return _assignment_view(made, class_id)

    def assignment(self, assignment_id: str) -> dict | None:
        found = self._load({"assignments.assignment_id": assignment_id})
        if found is None:
            return None
        a = next(a for a in found.assignments if a.assignment_id == assignment_id)
        return _assignment_view(a, found.class_id)

    def assignments(self, class_ids: list[str]) -> list[dict]:
        rows = self.col("classroom").find({"class_id": {"$in": class_ids}})
        out = [
            _assignment_view(a, c.class_id)
            for c in map(Classroom.from_doc, rows)
            for a in c.assignments
        ]
        # Latest due first, then latest set first.
        return sorted(out, key=lambda a: (a["due_at"], a["created_at"]), reverse=True)

    def remove_assignment(self, assignment_id: str) -> None:
        self.col("classroom").update_one(
            {"assignments.assignment_id": assignment_id},
            {"$pull": {"assignments": {"assignment_id": assignment_id}}},
        )
