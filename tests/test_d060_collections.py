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


def test_participants_and_their_surveys_move_into_the_study(db):
    db["study"].insert_one(
        {"study_id": "st-1", "name": "S", "seed": 1, "min_days": 7, "status": "survey",
         "created_by": "a", "created_at": "2026-10-01", "closed_at": None, "measured_until": None}
    )  # fmt: skip
    db["study_participant"].insert_many(
        [
            {"study_id": "st-1", "account_id": "b", "arm": "score_only", "code": "P002",
             "enrolled_at": "2026-10-01", "withdrawn_at": None},
            {"study_id": "st-1", "account_id": "a", "arm": "feedback", "code": "P001",
             "enrolled_at": "2026-10-01", "withdrawn_at": "2026-10-05"},
        ]
    )  # fmt: skip
    db["study_survey"].insert_one(
        {"study_id": "st-1", "account_id": "b", "answers_json": '{"trusted": 4}',
         "submitted_at": "2026-10-09"}
    )  # fmt: skip

    _twice(migrations._d060_study, db)

    doc = db["study"].find_one({"study_id": "st-1"})
    assert [p["code"] for p in doc["participants"]] == ["P001", "P002"]
    by = {p["account_id"]: p for p in doc["participants"]}
    assert by["b"]["survey_answers"] == {"trusted": 4} and by["b"]["surveyed_at"] == "2026-10-09"
    assert by["a"]["survey_answers"] is None and by["a"]["withdrawn_at"] == "2026-10-05"
    assert not {"study_participant", "study_survey"} & set(db.list_collection_names())
