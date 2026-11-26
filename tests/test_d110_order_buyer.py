"""D110: an order names its buyer, `buyer_id`, as the class diagram's `Order.buyer`.

* a new order keeps the account that bought it in `buyer_id`, and the
  account's own order list finds it there;
* migration 26 renames `created_by` of the orders stored before, keeps every
  value, and moves the index with it.
"""

from __future__ import annotations

import pytest

from aicefr.storage.billing_repository import BillingRepository
from aicefr.storage.db import database
from aicefr.storage.migrations import MIGRATIONS

pytestmark = pytest.mark.integration


def _order(order_id: str, **who) -> dict:
    return {
        "order_id": order_id,
        "runs": 10,
        "amount_vnd": 20000,
        "status": "pending",
        "created_at": "2026-11-20T00:00:00+00:00",
        **who,
    }


def test_a_new_order_keeps_its_buyer(tmp_path):
    store = BillingRepository(tmp_path / "billing.db")
    made = store.create_order(_order("DL-1", buyer_id="a1"))
    assert made["buyer_id"] == "a1"
    assert "created_by" not in store.col("order").find_one({"order_id": "DL-1"})
    assert [o["order_id"] for o in store.orders_by("a1")] == ["DL-1"]


def test_migration_26_renames_created_by_to_buyer_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:25]:
        step.apply(db, str(target))
    db["order"].insert_many([_order("DL-1", created_by="a1"), _order("DL-2", created_by="a2")])
    db["order"].create_index([("created_by", 1)], name="i_created_by")
    for _ in range(2):  # nothing more the second time
        MIGRATIONS[25].apply(db, str(target))
    rows = {o["order_id"]: o for o in db["order"].find({}, {"_id": 0})}
    assert {k: o.get("buyer_id") for k, o in rows.items()} == {"DL-1": "a1", "DL-2": "a2"}
    assert not any("created_by" in o for o in rows.values())
    names = set(db["order"].index_information())
    assert "i_buyer_id" in names and "i_created_by" not in names
