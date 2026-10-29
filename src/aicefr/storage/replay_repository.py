"""What learners answered in guided listening (D056): one label per (response, moment).

A label keeps which source the moment came from (the machine's or a random
control) so the analysis needs no second computation, and the learner's own
words about what they meant to say. No audio, no transcript.

The labels are part of the response they are about (`Response.replay_labels`,
D060): they live in its document and go with it.
"""

from __future__ import annotations

from pathlib import Path

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


def _labels(rows) -> list[dict]:
    return [fields(x, LABEL_FIELDS) for r in rows for x in r.get("replay_labels") or []]


class ReplayRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def save(self, label: dict) -> dict:
        """Keep a learner's answer for one moment; answering again replaces it."""
        now = _now()
        responses = self.col("response")
        rid, moment = label["response_id"], label["moment_id"]
        before = next((x for x in self.of_response(rid) if x["moment_id"] == moment), None)
        item = {**label, "created_at": before["created_at"] if before else now, "updated_at": now}
        if before is None:
            responses.update_one(
                {"response_id": rid, "replay_labels.moment_id": {"$ne": moment}},
                {"$push": {"replay_labels": item}},
            )
        else:
            responses.update_one(
                {"response_id": rid, "replay_labels.moment_id": moment},
                {"$set": {"replay_labels.$": item}},
            )
        return fields(item, LABEL_FIELDS)  # type: ignore[return-value]

    def of_response(self, response_id: str) -> list[dict]:
        rows = self.col("response").find({"response_id": response_id}, {"replay_labels": 1})
        return sorted(_labels(rows), key=lambda x: x["moment_id"])

    def of_account(self, account_id: str) -> list[dict]:
        rows = self.col("response").find(
            {"replay_labels.account_id": account_id}, {"replay_labels": 1}
        )
        mine = [x for x in _labels(rows) if x["account_id"] == account_id]
        return sorted(mine, key=lambda x: (x["created_at"], x["moment_id"]))

    def all(self) -> list[dict]:
        rows = self.col("response").find(
            {"replay_labels.0": {"$exists": True}}, {"replay_labels": 1}
        )
        return _labels(rows)

    def forget_account(self, account_id: str) -> None:
        """Erasure (FR-35): the learner's answers go with their recordings."""
        self.col("response").update_many(
            {"replay_labels.account_id": account_id},
            {"$pull": {"replay_labels": {"account_id": account_id}}},
        )

    def forget_response(self, response_id: str) -> None:
        self.col("response").update_one(
            {"response_id": response_id}, {"$set": {"replay_labels": []}}
        )
