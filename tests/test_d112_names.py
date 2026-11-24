"""D112: stored names follow the class diagram; wallet and price list get their own id.

* a teacher's decision keeps `decided_at`, a response `reason_codes`, its
  report `feedback`, a learning plan `lessons`;
* a wallet is its owner's (`account_id`) under its own `wallet_id`, and a
  ledger entry points at it by `wallet_id`; a new price list version has a
  `price_list_id`;
* migration 27 moves the documents stored before to the new names, the
  indexes with them, and changes nothing more when run twice.
"""

from __future__ import annotations

import pytest

from aicefr.storage.db import database
from aicefr.storage.metering_repository import MeteredAction, MeteringRepository
from aicefr.storage.migrations import MIGRATIONS

pytestmark = pytest.mark.integration


def test_a_wallet_has_its_own_id_and_its_entries_point_at_it(tmp_path):
    store = MeteringRepository(tmp_path / "m.db", free_units=1000)
    entry = store.hold("a1", MeteredAction.ASSESSMENT, "r1", 1000)
    wallet = store.col("wallet").find_one({"account_id": "a1"})
    assert wallet["wallet_id"].startswith("wa") and "user_ref" not in wallet
    assert entry["wallet_id"] == wallet["wallet_id"] and "user_ref" not in entry
    store.settle("r1", MeteredAction.ASSESSMENT, result=False)  # gives back to the owner
    assert store.free_left("a1") == 1000
    assert [e["key"] for e in store.history("a1")] == ["r1"]
    assert store.history("nobody") == [] and store.runs_paid("nobody") == 0


def test_a_new_price_list_version_has_its_own_id(tmp_path):
    store = MeteringRepository(tmp_path / "m.db")
    first = store.set_price_list({"free_runs": 3.0, "packs": []})
    second = store.set_price_list({"free_runs": 3.0, "packs": []})
    assert first["price_list_id"].startswith("pl")
    assert first["price_list_id"] != second["price_list_id"]
    assert store.price_list()["price_list_id"] == second["price_list_id"]


def test_migration_27_moves_old_documents_to_the_new_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:26]:
        step.apply(db, str(target))
    db["response"].insert_one(
        {"response_id": "r1", "reasons": ["ASR_FAILED"],
         "assessment": {"overall_0_6": 3.0, "comments": [{"text": "ok"}]},
         "reviews": [{"review_id": 1, "reason": "x", "created_at": "t1"}]}
    )  # fmt: skip
    db["learning_plan"].insert_one({"plan_id": "lp1", "plan": {"units": []}})
    db["wallet"].insert_one({"user_ref": "a1", "balance": 2000, "grants": []})
    db["ledger"].insert_many(
        [{"entry_id": "e1", "user_ref": "a1", "action": "assessment", "key": "r1"},
         {"entry_id": "e2", "user_ref": "b1", "action": "assessment", "key": "r2"}]
    )  # fmt: skip
    db["price_list"].insert_one({"_id": "current", "version": "price-admin-1"})

    MIGRATIONS[26].apply(db, str(target))
    first = {w["account_id"]: w["wallet_id"] for w in db["wallet"].find()}
    price_id = db["price_list"].find_one({"_id": "current"})["price_list_id"]
    MIGRATIONS[26].apply(db, str(target))  # nothing more the second time

    r = db["response"].find_one({"response_id": "r1"})
    assert r["reason_codes"] == ["ASR_FAILED"] and "reasons" not in r
    assert r["assessment"]["feedback"] == [{"text": "ok"}] and "comments" not in r["assessment"]
    assert r["reviews"] == [{"review_id": 1, "reason": "x", "decided_at": "t1"}]
    assert db["learning_plan"].find_one({"plan_id": "lp1"})["lessons"] == {"units": []}
    assert {w["account_id"]: w["wallet_id"] for w in db["wallet"].find()} == first
    assert set(first) == {"a1", "b1"}  # an owner with entries but no wallet gets one
    entries = {e["entry_id"]: e for e in db["ledger"].find()}
    assert entries["e1"]["wallet_id"] == first["a1"] and "user_ref" not in entries["e1"]
    assert entries["e2"]["wallet_id"] == first["b1"]
    assert db["wallet"].find_one({"account_id": "a1"})["balance"] == 2000
    assert db["price_list"].find_one({"_id": "current"})["price_list_id"] == price_id
    names = {c: {i["name"] for i in db[c].list_indexes()} for c in ("wallet", "ledger", "response")}
    assert {"u_account_id", "u_wallet_id"} <= names["wallet"]
    assert "u_user_ref" not in names["wallet"]
    assert "i_wallet_id_created_at" in names["ledger"]
    assert "i_user_ref_created_at" not in names["ledger"]
    assert "i_reviews.decided_at" in names["response"]
    assert "i_reviews.created_at" not in names["response"]
