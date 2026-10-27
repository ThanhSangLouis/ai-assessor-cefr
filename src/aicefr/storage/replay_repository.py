"""What learners answered in guided listening (D056): one label per (response, moment).

A label keeps which source the moment came from (the machine's or a random
control) so the analysis needs no second computation, and the learner's own
words about what they meant to say. No audio, no transcript.
"""

from __future__ import annotations

from pathlib import Path

from pymongo import ASCENDING

from aicefr.storage.db import MongoStore, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

LABEL_FIELDS = (
    "response_id",
    "moment_id",
    "account_id",
    "source",
    "kind",
    "start_s",
    "end_s",
    "choice",
    "intended",
    "created_at",
    "updated_at",
)


class ReplayRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def save(self, label: dict) -> dict:
        """Keep a learner's answer for one moment; answering again replaces it."""
        now = _now()
        key = {"response_id": label["response_id"], "moment_id": label["moment_id"]}
        self.col("replay_label").update_one(
            key,
            {"$set": {**label, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return fields(self.col("replay_label").find_one(key), LABEL_FIELDS)  # type: ignore[return-value]

    def of_response(self, response_id: str) -> list[dict]:
        rows = self.col("replay_label").find({"response_id": response_id}).sort("moment_id", 1)
        return [fields(r, LABEL_FIELDS) for r in rows]  # type: ignore[misc]

    def of_account(self, account_id: str) -> list[dict]:
        rows = (
            self.col("replay_label")
            .find({"account_id": account_id})
            .sort([("created_at", ASCENDING), ("moment_id", ASCENDING)])
        )
        return [fields(r, LABEL_FIELDS) for r in rows]  # type: ignore[misc]

    def all(self) -> list[dict]:
        return [fields(r, LABEL_FIELDS) for r in self.col("replay_label").find()]  # type: ignore[misc]

    def forget_account(self, account_id: str) -> None:
        """Erasure (FR-35): the learner's answers go with their recordings."""
        self.col("replay_label").delete_many({"account_id": account_id})

    def forget_response(self, response_id: str) -> None:
        self.col("replay_label").delete_many({"response_id": response_id})
