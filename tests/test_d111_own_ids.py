"""D111: an achievement and an upgraded answer carry their own identifier.

* a new achievement is stored with `achievement_id`; the pair learner + rule
  code stays unique, so a learner still reaches each rule once;
* a new upgraded answer is kept with `upgrade_id`, and reads back through its
  contract;
* migration 26 gives one to every achievement and upgrade stored before, under
  a unique index for `achievement_id`, and changes nothing more when run twice.
"""

from __future__ import annotations

import pytest

from aicefr.contracts import CoachUpgrade
from aicefr.storage.db import database
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.migrations import MIGRATIONS

pytestmark = pytest.mark.integration


def test_a_new_achievement_has_its_own_id_and_is_reached_once(tmp_path):
    repo = LessonRepository(tmp_path / "learning.db", seed=False)
    assert repo.unlock("a1", ["streak_3", "first_step"]) == ["streak_3", "first_step"]
    assert repo.unlock("a1", ["streak_3"]) == []  # the same rule again: not stored twice
    rows = list(repo.col("achievement").find({"account_id": "a1"}))
    ids = {r["achievement_id"] for r in rows}
    assert len(rows) == 2 and len(ids) == 2
    assert all(i.startswith("ac") for i in ids)


def test_an_upgraded_answer_reads_back_with_its_id():
    kept = {"upgrade_id": "up0123456789", "from_band": "B1", "to_band": "B2",
            "upgraded": "text", "created_at": "2026-11-24T00:00:00+00:00"}  # fmt: skip
    assert CoachUpgrade.model_validate(kept).upgrade_id == "up0123456789"


def test_migration_26_gives_old_achievements_and_upgrades_an_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:25]:
        step.apply(db, str(target))
    db["achievement"].insert_many(
        [{"account_id": "a1", "code": "streak_3", "unlocked_at": "t1"},
         {"account_id": "a1", "code": "first_step", "unlocked_at": "t2"}]
    )  # fmt: skip
    db["response"].insert_many(
        [{"response_id": "r1", "coach_upgrade": {"from_band": "B1", "to_band": "B2",
                                                 "upgraded": "x", "created_at": "t"}},
         {"response_id": "r2"}]
    )  # fmt: skip
    MIGRATIONS[25].apply(db, str(target))
    first = {r["code"]: r["achievement_id"] for r in db["achievement"].find()}
    upgrade = db["response"].find_one({"response_id": "r1"})["coach_upgrade"]["upgrade_id"]
    MIGRATIONS[25].apply(db, str(target))  # nothing more the second time
    assert {r["code"]: r["achievement_id"] for r in db["achievement"].find()} == first
    assert db["response"].find_one({"response_id": "r1"})["coach_upgrade"]["upgrade_id"] == upgrade
    assert len(set(first.values())) == 2 and upgrade.startswith("up")
    assert "coach_upgrade" not in db["response"].find_one({"response_id": "r2"})
    indexes = {i["name"]: i for i in db["achievement"].list_indexes()}
    assert indexes["u_achievement_id"]["unique"]
