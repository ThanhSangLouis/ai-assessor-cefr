"""What other services may ask the learning service (D043).

A learner's lesson attempts and achievements (the personal export, the feedback
study), the review count for the sidebar, and erasure of one account's lesson
data, recordings included.
"""

from __future__ import annotations

import logging

from aicefr.platform.rpc import exposed
from aicefr.ports import BlobStore
from aicefr.services.core.learning import lessons_api
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.lesson_repository import LessonRepository

logger = logging.getLogger(__name__)


class LearningFacade:
    def __init__(self, lessons: LessonRepository, blobs: BlobStore, audit: AuditLog) -> None:
        self.lessons = lessons
        self.blobs = blobs
        self.audit = audit

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
    def reviews_due(self, account_id: str) -> int:
        return lessons_api.reviews_due(account_id)

    @exposed
    def count_attempts(self, account_id: str) -> int:
        return self.lessons.count_attempts(account_id)

    @exposed
    def erase_account(self, account_id: str) -> int:
        """Erase every attempt, review and achievement of one account, recordings included."""
        keys = self.lessons.erase_account(account_id)
        for key in keys:
            try:
                self.blobs.delete(key)
            except (FileNotFoundError, OSError):
                logger.warning("lesson audio already gone: %s", key)
        return len(keys)

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
