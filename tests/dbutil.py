"""Open a service's store directly, to arrange documents by hand (D048)."""

from __future__ import annotations

from pymongo.database import Database

from aicefr.config import get_settings
from aicefr.storage.db import database


def store() -> Database:
    """This test's core store."""
    return database(get_settings().store("core"))


def teach(teacher: str, *students: str) -> None:
    """D071: put the students in a class the teacher teaches, by pseudonym.

    A teacher reviews only the work of their classes' members; a test that has
    a teacher open a student's response arranges the class first.
    """
    from aicefr.storage.classroom_repository import new_code
    from aicefr.storage.db import now_iso

    db = store()
    names = [teacher, *students]
    ids = {
        a["pseudonym"]: a["account_id"] for a in db["account"].find({"pseudonym": {"$in": names}})
    }
    missing = [n for n in names if n not in ids]
    assert not missing, f"no account for {missing}"
    db["classroom"].update_one(
        {"class_id": f"lop-test-{ids[teacher]}"},
        {
            "$setOnInsert": {
                "name": f"Lớp của {teacher}",
                "code": new_code(),
                "created_at": now_iso(),
                "archived": False,
                "assignments": [],
            },
            "$addToSet": {
                "teacher_ids": ids[teacher],
                "members": {"$each": [ids[s] for s in students]},
            },
        },
        upsert=True,
    )


def teach_all(teacher: str) -> None:
    """D071: put every student account there is now in a class the teacher teaches.

    For tests about reviewing, not about who may review: they arrange a
    teacher who teaches everyone. Students made later are not included.
    """
    students = [a["pseudonym"] for a in store()["account"].find({"role": "student"})]
    teach(teacher, *students)


def one_school(pseudonym: str, role: str) -> None:
    """D071: every test teacher teaches every test student, whichever is made first.

    Called by the `login_as` helpers of tests about reviewing rather than about
    who may review. A teacher gets a class with every student there is; a
    student joins every class such a teacher has.
    """
    if role == "teacher":
        teach_all(pseudonym)
    elif role == "student":
        db = store()
        found = db["account"].find_one({"pseudonym": pseudonym}, {"account_id": 1})
        if found:
            db["classroom"].update_many(
                {"class_id": {"$regex": "^lop-test-"}},
                {"$addToSet": {"members": found["account_id"]}},
            )
