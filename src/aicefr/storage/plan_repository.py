"""Paths the path model composed (D046): a learner's own, a teacher's drafts.

The collection came after the frozen baseline (migration 2, D045). The
learning part may keep a database of its own (D051), which never runs the core's
migrations, so this repository makes the indexes migration 2 defines itself.
A learner has at most one active plan; asking again replaces it, and the old
one stays, inactive, until the learner's data is erased.
"""

from __future__ import annotations

import json
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.lessons.model import new_id
from aicefr.storage.db import MongoStore, ensure_indexes, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import PLAN_INDEXES

AUDIENCES = ("student", "teacher")

PLAN_FIELDS = (
    "plan_id",
    "account_id",
    "audience",
    "goal_json",
    "plan_json",
    "model_version",
    "path_id",
    "active",
    "created_at",
)


class PlanRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, PLAN_INDEXES, "plans")

    def save(
        self, account_id: str, audience: str, goal: dict, plan: dict, model_version: str
    ) -> str:
        """Store a plan; a learner's new plan replaces their active one."""
        if audience not in AUDIENCES:
            raise ValueError(audience)
        plan_id = new_id("lp")
        plans = self.col("learning_plan")
        if audience == "student":
            plans.update_many(
                {"account_id": account_id, "audience": "student", "active": 1},
                {"$set": {"active": 0}},
            )
        plans.insert_one(
            {
                "plan_id": plan_id,
                "account_id": account_id,
                "audience": audience,
                "goal_json": json.dumps(goal, ensure_ascii=False),
                "plan_json": json.dumps(plan, ensure_ascii=False),
                "model_version": model_version,
                "path_id": None,
                "active": 1,
                "created_at": _now(),
            }
        )
        return plan_id

    @staticmethod
    def _row(row) -> dict:
        out = fields(row, PLAN_FIELDS)
        out["goal"] = json.loads(out.pop("goal_json"))  # type: ignore[union-attr]
        out["plan"] = json.loads(out.pop("plan_json"))  # type: ignore[union-attr]
        out["active"] = bool(out["active"])  # type: ignore[index]
        return out  # type: ignore[return-value]

    def get(self, plan_id: str) -> dict | None:
        row = self.col("learning_plan").find_one({"plan_id": plan_id})
        return self._row(row) if row else None

    def active(self, account_id: str) -> dict | None:
        """The learner's plan in force, if they asked for one."""
        row = self.col("learning_plan").find_one(
            {"account_id": account_id, "audience": "student", "active": 1},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        return self._row(row) if row else None

    def close(self, account_id: str) -> int:
        """The learner sets their plan aside; it is kept, inactive."""
        done = self.col("learning_plan").update_many(
            {"account_id": account_id, "audience": "student", "active": 1},
            {"$set": {"active": 0}},
        )
        return done.modified_count

    def saved_as(self, plan_id: str, path_id: str) -> None:
        """A teacher's plan became this draft path."""
        self.col("learning_plan").update_one(
            {"plan_id": plan_id}, {"$set": {"path_id": path_id, "active": 0}}
        )

    def of_account(self, account_id: str) -> list[dict]:
        """Every plan of one account, oldest first: the personal export."""
        rows = (
            self.col("learning_plan")
            .find({"account_id": account_id})
            .sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [self._row(r) for r in rows]

    def erase_account(self, account_id: str) -> int:
        return self.col("learning_plan").delete_many({"account_id": account_id}).deleted_count
