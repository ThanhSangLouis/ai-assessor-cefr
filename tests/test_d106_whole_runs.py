"""D106: a learner counts in whole runs.

* migration 23 rounds every wallet to whole runs in the learner's favour: the
  prepaid balance up, the free runs used this cycle down; the administrator's
  price list keeps only the whole part of each price; charges already made keep
  what they were, and running it twice changes nothing more;
* with the default prices a scored recording is one run, and an AI answer, a
  reading passage or a lesson recording takes nothing and shows no price.
"""

from __future__ import annotations

import pytest

from aicefr.metering.pricing import PriceList
from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.db import database
from aicefr.storage.metering_repository import MeteredAction, MeteringRepository
from aicefr.storage.migrations import MIGRATIONS, migrate

pytestmark = pytest.mark.integration


def test_migration_23_rounds_wallets_and_prices_in_the_learners_favour(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:22]:
        step.apply(db, str(target))
    db["wallet"].insert_many(
        [
            {"user_ref": "a", "balance": 1300, "period": "2026-11", "free_used": 1700},
            {"user_ref": "b", "balance": 2000, "period": "2026-11", "free_used": 1000},
            {"user_ref": "c", "balance": 0, "period": "2026-11", "free_used": 300},
        ]
    )
    db["ledger"].insert_one(
        {"entry_id": "e1", "user_ref": "a", "action": "upgrade", "key": "upgrade-r1",
         "from_free": 300, "from_wallet": 0, "charged": 300, "state": "charged",
         "period": "2026-11", "created_at": "2026-11-10T00:00:00+00:00"}
    )  # fmt: skip
    db["price_list"].insert_one(
        {"_id": "current", "version": "price-admin-1", "first_minute_runs": 1.0,
         "extra_minute_runs": 0.7, "upgrade_runs": 0.3, "passage_runs": 0.1,
         "lesson_minute_runs": 0.1, "idpoint_per_run": 2000, "free_runs": 3.0,
         "packs": [{"runs": 10, "price_vnd": 19000}]}
    )  # fmt: skip

    migrate(target)
    migrate(target)  # nothing more the second time

    wallets = {w["user_ref"]: (w["balance"], w["free_used"]) for w in db["wallet"].find()}
    assert wallets == {"a": (2000, 1000), "b": (2000, 1000), "c": (0, 0)}
    assert db["ledger"].find_one({"entry_id": "e1"})["charged"] == 300  # history kept
    prices = db["price_list"].find_one({"_id": "current"})
    assert [prices[f] for f in ("first_minute_runs", "extra_minute_runs", "upgrade_runs",
                                "passage_runs", "lesson_minute_runs", "free_runs")] == [
        1.0, 0.0, 0.0, 0.0, 0.0, 3.0]  # fmt: skip
    assert prices["version"] == "price-admin-1"


def test_by_default_only_a_scored_recording_costs_a_run(tmp_path):
    store = MeteringRepository(tmp_path / "metering.db")
    facade = MeteringFacade(store, AuditLog(tmp_path / "metering.db", "metering"), enabled=True)
    assert facade.hold(account_id="a1", action="assessment", key="r1", max_seconds=60) is None
    facade.settle(key="r1", action="assessment", result=True, seconds=48.0)
    assert store.entry("r1", MeteredAction.ASSESSMENT)["charged"] == 1000
    assert facade.upgrade_price() is None and facade.passage_price() is None
    for action in ("upgrade", "drill_passage", "lesson_draft"):
        assert facade.hold_upgrade(account_id="a1", key=f"{action}-r1", action=action) is None
        assert store.entry(f"{action}-r1", MeteredAction(action)) is None
    assert store.balance("a1") == {"wallet": 0, "free_left": 2000}


def test_a_hold_taken_at_an_older_price_is_charged_todays(tmp_path):
    # An AI answer held at 0.3 of a run a moment before D106: charged nothing.
    store = MeteringRepository(tmp_path / "metering.db")
    store.hold("a1", MeteredAction.UPGRADE, "upgrade-r1", 300)
    facade = MeteringFacade(store, AuditLog(tmp_path / "metering.db", "metering"), enabled=True)
    facade.settle_upgrade(key="upgrade-r1", result=True)
    entry = store.entry("upgrade-r1", MeteredAction.UPGRADE)
    assert (entry["state"], entry["charged"]) == ("charged", 0)
    assert store.balance("a1") == {"wallet": 0, "free_left": 3000}
    # A seller who charges a whole run still gets it.
    priced = MeteringFacade(
        store, AuditLog(tmp_path / "metering.db", "metering"), True, PriceList(upgrade_runs=1)
    )
    assert priced.hold_upgrade(account_id="a1", key="upgrade-r2") is None
    priced.settle_upgrade(key="upgrade-r2", result=True)
    assert store.entry("upgrade-r2", MeteredAction.UPGRADE)["charged"] == 1000
