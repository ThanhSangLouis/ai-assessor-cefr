"""Classes and the assessments a teacher sets them (D054).

Three collections:

* `classroom` -- a teacher's class: a name, and a join code the teacher hands
  out so students add themselves;
* `class_member` -- who is in which class, unique on (class, account);
* `assignment` -- one task set to one class, due at the end of a day.

What a student has done is not stored here: an assessment response of the
assigned task, made by a member after the task was set, is the submission, and
one made after the due day is late. The submission screen therefore needs no
new field, and a response a student made of their own accord counts too --
the work is the same work.
"""

from __future__ import annotations

import secrets
import uuid
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.storage.db import IntegrityError, MongoStore, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

CLASS_FIELDS = ("class_id", "name", "code", "teacher_id", "created_at", "archived")
ASSIGNMENT_FIELDS = (
    "assignment_id",
    "class_id",
    "task_id",
    "note",
    "due_on",
    "due_at",
    "created_by",
    "created_at",
)
# Without 0/O and 1/I/L: a code read aloud in class or copied off a board.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class ClassroomRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    # ------------------------------------------------------------ classes

    def create(self, name: str, teacher_id: str) -> dict:
        for _ in range(8):
            doc = {
                "class_id": "lop-" + uuid.uuid4().hex[:10],
                "name": name,
                "code": new_code(),
                "teacher_id": teacher_id,
                "created_at": _now(),
                "archived": False,
            }
            try:
                self.col("classroom").insert_one(doc)
            except IntegrityError:
                continue  # the code was taken: draw another
            return fields(doc, CLASS_FIELDS)  # type: ignore[return-value]
        raise RuntimeError("could not draw a free join code")

    def get(self, class_id: str) -> dict | None:
        return fields(self.col("classroom").find_one({"class_id": class_id}), CLASS_FIELDS)

    def by_code(self, code: str) -> dict | None:
        row = self.col("classroom").find_one({"code": code.strip().upper(), "archived": False})
        return fields(row, CLASS_FIELDS)

    def of_teacher(self, teacher_id: str | None) -> list[dict]:
        """A teacher's classes; every class when `teacher_id` is None (an administrator)."""
        query = {} if teacher_id is None else {"teacher_id": teacher_id}
        rows = self.col("classroom").find(query).sort([("created_at", DESCENDING)])
        return [fields(r, CLASS_FIELDS) for r in rows]  # type: ignore[misc]

    def set_archived(self, class_id: str, archived: bool) -> None:
        self.col("classroom").update_one({"class_id": class_id}, {"$set": {"archived": archived}})

    # ------------------------------------------------------------ members

    def add_member(self, class_id: str, account_id: str) -> bool:
        """False when the account is in the class already."""
        try:
            self.col("class_member").insert_one(
                {"class_id": class_id, "account_id": account_id, "joined_at": _now()}
            )
        except IntegrityError:
            return False
        return True

    def remove_member(self, class_id: str, account_id: str) -> bool:
        done = self.col("class_member").delete_one({"class_id": class_id, "account_id": account_id})
        return bool(done.deleted_count)

    def members(self, class_id: str) -> list[dict]:
        rows = self.col("class_member").find({"class_id": class_id}).sort("joined_at", ASCENDING)
        return [fields(r, ("account_id", "joined_at")) for r in rows]  # type: ignore[misc]

    def classes_of(self, account_id: str) -> list[str]:
        rows = self.col("class_member").find({"account_id": account_id}, {"class_id": 1})
        return [r["class_id"] for r in rows]

    def count_members(self, class_id: str) -> int:
        return self.col("class_member").count_documents({"class_id": class_id})

    def forget_account(self, account_id: str) -> None:
        """Erasure (FR-37): the account leaves every class."""
        self.col("class_member").delete_many({"account_id": account_id})

    # ------------------------------------------------------------ assignments

    def assign(
        self, class_id: str, task_id: str, due_on: str, due_at: str, note: str, by: str
    ) -> dict:
        doc = {
            "assignment_id": "bg-" + uuid.uuid4().hex[:10],
            "class_id": class_id,
            "task_id": task_id,
            "note": note,
            "due_on": due_on,
            "due_at": due_at,
            "created_by": by,
            "created_at": _now(),
        }
        self.col("assignment").insert_one(doc)
        return fields(doc, ASSIGNMENT_FIELDS)  # type: ignore[return-value]

    def assignment(self, assignment_id: str) -> dict | None:
        row = self.col("assignment").find_one({"assignment_id": assignment_id})
        return fields(row, ASSIGNMENT_FIELDS)

    def assignments(self, class_ids: list[str]) -> list[dict]:
        rows = (
            self.col("assignment")
            .find({"class_id": {"$in": class_ids}})
            .sort([("due_at", DESCENDING), ("created_at", DESCENDING)])
        )
        return [fields(r, ASSIGNMENT_FIELDS) for r in rows]  # type: ignore[misc]

    def remove_assignment(self, assignment_id: str) -> None:
        self.col("assignment").delete_one({"assignment_id": assignment_id})
