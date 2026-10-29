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


def test_payment_events_move_into_their_order_and_settings_into_system(db):
    db["billing_order"].insert_one({"order_id": "o-1", "kind": "credits", "status": "paid"})
    db["billing_event"].insert_many(
        [
            {"event_id": 2, "order_id": "o-1", "kind": "return", "fingerprint": "{}",
             "detail_json": '{"code": "00"}', "created_at": "t2", "repeats": 3},
            {"event_id": 1, "order_id": "o-1", "kind": "created", "fingerprint": "{}",
             "detail_json": "{}", "created_at": "t1", "repeats": 0},
        ]
    )  # fmt: skip
    db["billing_license"].insert_one({"license_id": "lic-1", "source": "trial"})
    db["billing_setting"].insert_one({"key": "organization", "value": "Trường A"})

    _twice(migrations._d060_billing, db)

    order = db["order"].find_one({"order_id": "o-1"})
    assert [e["kind"] for e in order["events"]] == ["created", "return"]
    assert order["events"][1]["detail"] == {"code": "00"} and order["events"][1]["repeats"] == 3
    assert db["license"].count_documents({}) == 1
    assert db["system"].find_one({"key": "billing.organization"})["value"] == "Trường A"
    gone = {"billing_order", "billing_event", "billing_license", "billing_setting"}
    assert not gone & set(db.list_collection_names())


def test_the_wallet_gathers_balance_free_runs_and_top_ups(db):
    db["credit_wallet"].insert_one({"user_ref": "a1", "balance": 4000})
    db["free_quota"].insert_many(
        [{"user_ref": "a1", "period": "2026-09", "used": 3000},
         {"user_ref": "a1", "period": "2026-10", "used": 1000}]
    )  # fmt: skip
    db["credit_grant"].insert_one(
        {"grant_id": "g1", "user_ref": "a1", "units": 5000, "source": "order", "ref": "o-1",
         "by": None, "created_at": "t1"}
    )  # fmt: skip
    db["usage_ledger"].insert_one(
        {"entry_id": "e1", "user_ref": "a1", "action": "assess", "key": "r1", "state": "held"}
    )

    _twice(migrations._d060_metering, db)

    w = db["wallet"].find_one({"user_ref": "a1"})
    assert (w["balance"], w["period"], w["free_used"]) == (4000, "2026-10", 1000)
    assert [g["ref"] for g in w["grants"]] == ["o-1"]
    assert db["ledger"].find_one({"key": "r1"})["action"] == "assessment"
    gone = {"credit_wallet", "free_quota", "credit_grant", "usage_ledger"}
    assert not gone & set(db.list_collection_names())


def test_identities_markers_sessions_and_secrets_find_their_places(db):
    db["account"].insert_one({"account_id": "a1", "pseudonym": "SV-001"})
    db["account_identity"].insert_one(
        {"account_id": "a1", "provider": "google", "subject_hash": "h", "linked_at": "t1"}
    )
    db["seen_marker"].insert_one({"account_id": "a1", "marker": "results", "seen_at": "t2"})
    db["auth_sessions"].insert_one({"token_hash": "x", "account_id": "a1"})
    db["server_secret"].insert_one({"name": "oauth", "value_hex": "ab", "created_at": "t0"})
    db["app_config"].insert_one({"key": "review_policy", "value": "v", "version": "1"})

    _twice(migrations._d060_identity, db)

    a = db["account"].find_one({"account_id": "a1"})
    assert [i["provider"] for i in a["identities"]] == ["google"]
    assert a["seen_markers"] == {"results": "t2"}
    assert db["session"].count_documents({"token_hash": "x"}) == 1
    assert db["system"].find_one({"key": "identity.secret.oauth"})["value"] == "ab"
    assert db["system"].find_one({"key": "assessment.review_policy"})["version"] == "1"
    gone = {"account_identity", "seen_marker", "auth_sessions", "server_secret", "app_config"}
    assert not gone & set(db.list_collection_names())
