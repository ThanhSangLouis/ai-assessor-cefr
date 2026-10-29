"""Paths the path model composed (D046): a learner's own, a teacher's drafts.

The collection came after the frozen baseline (migration 2, D045). The
learning part may keep a database of its own (D051), which never runs the core's
migrations, so this repository makes the indexes migration 2 defines itself.
A learner has at most one active plan; asking again replaces it, and the old
one stays, inactive, until the learner's data is erased.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.lessons.model import new_id
from aicefr.storage.auth_repository import Role
from aicefr.storage.db import MongoStore, ensure_indexes, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import PLAN_INDEXES

AUDIENCES = (Role.STUDENT.value, Role.TEACHER.value)

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


@dataclass
class LearningPlan:
    """A path the path model composed for a learner, or proposed to a teacher (D046)."""

    plan_id: str
    account_id: str
    audience: Role  # a learner's own plan, or a teacher's proposal
    goal: dict
    plan: dict  # units, each with its lessons and the reasons they were picked
    model_version: str
    path_id: str | None  # the draft path a teacher saved it as
    active: bool
    created_at: str

    @classmethod
    def from_doc(cls, row: dict) -> LearningPlan:
        out = fields(row, PLAN_FIELDS)
        return cls(
            plan_id=out["plan_id"],  # type: ignore[index]
            account_id=out["account_id"],  # type: ignore[index]
            audience=Role(out["audience"]),  # type: ignore[index]
            goal=json.loads(out["goal_json"]),  # type: ignore[index]
            plan=json.loads(out["plan_json"]),  # type: ignore[index]
            model_version=out["model_version"],  # type: ignore[index]
            path_id=out["path_id"],  # type: ignore[index]
            active=bool(out["active"]),  # type: ignore[index]
            created_at=out["created_at"],  # type: ignore[index]
        )

    def view(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "account_id": self.account_id,
            "audience": self.audience.value,
            "model_version": self.model_version,
            "path_id": self.path_id,
            "active": self.active,
            "created_at": self.created_at,
            "goal": self.goal,
            "plan": self.plan,
        }


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
        audience = Role(audience).value
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
        return LearningPlan.from_doc(row).view()

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
