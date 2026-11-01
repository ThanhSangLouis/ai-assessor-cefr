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
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pymongo import DESCENDING

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
        )

    def to_doc(self) -> dict:
        return asdict(self)

    def view(self) -> dict:
        """What the screens show of the class itself, without its members."""
        return {
            "class_id": self.class_id,
            "name": self.name,
            "teacher_ids": list(self.teacher_ids),
            "created_at": self.created_at,
            "archived": self.archived,
        }


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
