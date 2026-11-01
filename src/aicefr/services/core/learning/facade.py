"""What other services may ask the learning service (D043).

A learner's lesson attempts, achievements and composed paths (the personal
export, the feedback study), the review count for the sidebar, and erasure of
one account's lesson data, recordings included.
"""

from __future__ import annotations

import logging

from aicefr.platform.rpc import exposed
from aicefr.ports import BlobStore
from aicefr.services.core.learning import lessons_api
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.plan_repository import PlanRepository

logger = logging.getLogger(__name__)


class LearningFacade:
    def __init__(
        self,
        lessons: LessonRepository,
        blobs: BlobStore,
        audit: AuditLog,
        plans: PlanRepository | None = None,
    ) -> None:
        self.lessons = lessons
        self.blobs = blobs
        self.audit = audit
        self.plans = plans

    @exposed
    def attempts(self, account_id: str, limit: int | None = None) -> list[dict]:
        """One learner's attempts, oldest first, each with its result as JSON."""
        return [
            {
                "attempt_id": a["attempt_id"],
                "lesson_id": a["lesson_id"],
                "lesson_version": a["lesson_version"],
                "step_id": a["step_id"],
                "round": a["round"],
                "created_at": a["created_at"],
                "result": a["result"].model_dump(mode="json"),
            }
            for a in self.lessons.attempts(account_id=account_id, limit=limit)
        ]

    @exposed
    def achievements(self, account_id: str) -> dict[str, dict]:
        return self.lessons.achievements(account_id)

    @exposed
    def plans_of(self, account_id: str) -> list[dict]:
        """Every path the path model composed for this account (D046)."""
        if self.plans is None:
            return []
        return [
            {
                "plan_id": p["plan_id"],
                "audience": p["audience"],
                "goal": p["goal"],
                "lessons": [item["lesson_id"] for u in p["plan"]["units"] for item in u["lessons"]],
                "model_version": p["model_version"],
                "active": p["active"],
                "created_at": p["created_at"],
            }
            for p in self.plans.of_account(account_id)
        ]

    @exposed
    def band_choices(self, account_ids: list[str]) -> dict[str, dict]:
        """The bands each learner studies, from their plan in force (D074).

        `{account_id: {band_from, band_to, assigned_by, path_title}}`; a learner
        without a plan is left out.
        """
        if self.plans is None:
            return {}
        out = {}
        for account_id, p in self.plans.active_of(account_ids).items():
            goal = p["goal"] or {}
            if not (goal.get("band_from") or goal.get("band_to")):
                continue
            out[account_id] = {
                "band_from": goal.get("band_from"),
                "band_to": goal.get("band_to"),
                "assigned_by": goal.get("assigned_by"),
                "path_title": goal.get("path_title"),
            }
        return out

    @exposed
    def reviews_due(self, account_id: str) -> int:
        return lessons_api.reviews_due(account_id)

    @exposed
    def count_attempts(self, account_id: str) -> int:
        return self.lessons.count_attempts(account_id)

    @exposed
    def erase_account(self, account_id: str) -> int:
        """Erase every attempt, review, achievement and composed path of one account,
        recordings included."""
        keys = self.lessons.erase_account(account_id)
        if self.plans is not None:
            self.plans.erase_account(account_id)
        for key in keys:
            try:
                self.blobs.delete(key)
            except (FileNotFoundError, OSError):
                logger.warning("lesson audio already gone: %s", key)
        return len(keys)

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
