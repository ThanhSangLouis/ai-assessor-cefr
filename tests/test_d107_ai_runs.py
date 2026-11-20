"""D107: what a paid language model writes for a learner is paid for by a run.

* one run scores a recording and brings its AI rewrite and one reading
  passage: they take nothing more, the ledger keeps them marked `included`,
  and the screens say "đã gồm" instead of quoting a price;
* the rewrite of a recording no run paid for, and a passage past the ones the
  runs brought, are one run each;
* migration 24 turns an administrator's price list that still had these at 0
  (D106) into one run each, and leaves a price set above 0 alone.
"""

from __future__ import annotations

import pytest

from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.db import database
from aicefr.storage.metering_repository import MeteredAction, MeteringRepository
from aicefr.storage.migrations import MIGRATIONS

pytestmark = pytest.mark.integration


def _facade(tmp_path):
    store = MeteringRepository(tmp_path / "metering.db")
    return store, MeteringFacade(
        store, AuditLog(tmp_path / "metering.db", "metering"), enabled=True
    )


def test_the_rewrite_of_a_scored_recording_is_part_of_its_run(tmp_path):
    store, facade = _facade(tmp_path)
    assert facade.hold(account_id="a1", action="assessment", key="r1", max_seconds=60) is None
    facade.settle(key="r1", action="assessment", result=True, seconds=48.0)
    assert facade.upgrade_price("r1") == {"runs": 0, "idpoint": 0, "included": True}
    assert facade.hold_upgrade(account_id="a1", key="upgrade-r1", response_id="r1") is None
    facade.settle_upgrade(key="upgrade-r1", result=True)
    entry = store.entry("upgrade-r1", MeteredAction.UPGRADE)
    assert (entry["included"], entry["held"], entry["charged"]) == (True, 0, 0)
    assert store.balance("a1") == {"wallet": 0, "free_left": 2000}  # the one run of r1


def test_a_recording_no_run_paid_for_pays_a_run_for_its_rewrite(tmp_path):
    store, facade = _facade(tmp_path)
    # Scored, then failed: the run went back, so it did not pay for a rewrite.
    facade.hold(account_id="a1", action="assessment", key="r1", max_seconds=60)
    facade.settle(key="r1", action="assessment", result=False, seconds=None)
    assert facade.upgrade_price("r1") == {"runs": 1, "idpoint": 2000}
    assert facade.hold_upgrade(account_id="a1", key="upgrade-r1", response_id="r1") is None
    facade.settle_upgrade(key="upgrade-r1", result=True)
    assert store.entry("upgrade-r1", MeteredAction.UPGRADE)["charged"] == 1000


def test_each_paid_run_brings_one_reading_passage_then_a_passage_is_a_run(tmp_path):
    store, facade = _facade(tmp_path)
    assert facade.passage_price("a1") == {"runs": 1, "idpoint": 2000}  # nothing scored yet
    for rid in ("r1", "r2"):
        facade.hold(account_id="a1", action="assessment", key=rid, max_seconds=60)
        facade.settle(key=rid, action="assessment", result=True, seconds=40.0)
    assert facade.passage_price("a1") == {"runs": 0, "idpoint": 0, "included": True, "left": 2}
    for n in (1, 2):
        assert facade.hold_upgrade(account_id="a1", key=f"p{n}", action="drill_passage") is None
        facade.settle_upgrade(key=f"p{n}", result=True, action="drill_passage")
        assert store.entry(f"p{n}", MeteredAction.DRILL_PASSAGE)["included"] is True
    # A passage the model failed to write gives its place back: still none left here.
    assert facade.passage_price("a1") == {"runs": 1, "idpoint": 2000}
    assert facade.hold_upgrade(account_id="a1", key="p3", action="drill_passage") is None
    facade.settle_upgrade(key="p3", result=True, action="drill_passage")
    assert store.entry("p3", MeteredAction.DRILL_PASSAGE)["charged"] == 1000
    assert store.balance("a1") == {"wallet": 0, "free_left": 0}


def test_a_failed_included_passage_gives_its_place_back(tmp_path):
    store, facade = _facade(tmp_path)
    facade.hold(account_id="a1", action="assessment", key="r1", max_seconds=60)
    facade.settle(key="r1", action="assessment", result=True, seconds=40.0)
    facade.hold_upgrade(account_id="a1", key="p1", action="drill_passage")
    facade.settle_upgrade(key="p1", result=False, action="drill_passage")
    assert facade.passage_price("a1")["left"] == 1


def test_migration_24_prices_the_model_answers_at_one_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:23]:
        step.apply(db, str(target))
    db["price_list"].insert_one(
        {"_id": "current", "version": "price-admin-2", "first_minute_runs": 1.0,
         "extra_minute_runs": 0.0, "upgrade_runs": 0.0, "passage_runs": 2.0,
         "lesson_minute_runs": 0.0, "idpoint_per_run": 2000, "free_runs": 3.0}
    )  # fmt: skip
    for _ in range(2):  # nothing more the second time
        MIGRATIONS[23].apply(db, str(target))
    prices = db["price_list"].find_one({"_id": "current"})
    assert (prices["upgrade_runs"], prices["passage_runs"]) == (1.0, 2.0)
    assert prices["lesson_minute_runs"] == 0.0
