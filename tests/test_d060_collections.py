"""D060: the collections follow the class diagram, one per aggregate root.

A store written before D060 keeps the parts of an aggregate in collections of
their own. Migration 7 moves each part into its root's document and drops the
old collection; these tests build such a store by hand, run the step, and read
the result -- and run it a second time, which must change nothing.
"""

from __future__ import annotations

import uuid

import pytest

from aicefr.storage import migrations
from aicefr.storage.db import database

pytestmark = pytest.mark.integration


@pytest.fixture
def db():
    return database(f"mongomock://d060-{uuid.uuid4().hex[:8]}")


def _twice(step, db) -> None:
    step(db)
    step(db)  # idempotent: the second run finds nothing to move


def test_members_and_assignments_move_into_their_class(db):
    db["classroom"].insert_one(
        {"class_id": "lop-1", "name": "A", "code": "ABC234", "teacher_id": "t",
         "created_at": "2026-10-01T00:00:00+00:00", "archived": False}
    )  # fmt: skip
    db["class_member"].insert_many(
        [
            {"class_id": "lop-1", "account_id": "s2", "joined_at": "2026-10-03"},
            {"class_id": "lop-1", "account_id": "s1", "joined_at": "2026-10-02"},
        ]
    )
    db["assignment"].insert_one(
        {"assignment_id": "bg-1", "class_id": "lop-1", "task_id": "P3", "note": "",
         "due_on": "2026-10-10", "due_at": "2026-10-10T17:00:00+00:00",
         "created_by": "t", "created_at": "2026-10-04T00:00:00+00:00"}
    )  # fmt: skip

    _twice(migrations._d060_classroom, db)

    doc = db["classroom"].find_one({"class_id": "lop-1"})
    assert doc["members"] == ["s1", "s2"]  # in the order they joined
    assert [a["assignment_id"] for a in doc["assignments"]] == ["bg-1"]
    assert "class_id" not in doc["assignments"][0]  # the class is the owner
    assert not {"class_member", "assignment"} & set(db.list_collection_names())
