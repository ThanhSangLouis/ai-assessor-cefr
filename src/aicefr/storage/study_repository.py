"""Store of the feedback study (D040): the study, who is in which arm, their survey."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.research.study import STATUSES
from aicefr.storage.db import MongoStore, ensure_indexes, fields
from aicefr.storage.db import now_iso as _now

# study.status: running | survey | closed; study_participant.arm:
# feedback | score_only. measured_until ends the measured phase: scores after
# it, when both arms see feedback again, are not outcomes. A participant's
# `code` is fixed at enrolment so exports of different days line up.
INDEXES = {
    "study": [(("study_id",), True), (("status", "created_at"), False)],
    "study_participant": [(("study_id", "account_id"), True), (("account_id",), False)],
    "study_survey": [(("study_id", "account_id"), True), (("account_id",), False)],
}

STUDY_FIELDS = (
    "study_id",
    "name",
    "seed",
    "min_days",
    "status",
    "created_by",
    "created_at",
    "closed_at",
    "measured_until",
)
ACTIVE = ("running", "survey")


class StudyRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "study")

    def create(
        self, name: str, seed: int, min_days: int, created_by: str, arms: dict[str, str]
    ) -> str:
        study_id = "st-" + uuid.uuid4().hex[:10]
        now = _now()
        # The participants first: a study is listed only once its document is
        # there, and by then everybody in it is enrolled.
        participants = [
            {
                "study_id": study_id,
                "account_id": account_id,
                "arm": arm,
                "enrolled_at": now,
                "withdrawn_at": None,
                # Codes in the order of the random assignment: they say nothing
                # of who is who, and never change.
                "code": f"P{i:03d}",
            }
            for i, (account_id, arm) in enumerate(arms.items(), 1)
        ]
        if participants:
            self.col("study_participant").insert_many(participants)
        self.col("study").insert_one(
            {
                "study_id": study_id,
                "name": name,
                "seed": seed,
                "min_days": min_days,
                "status": "running",
                "created_by": created_by,
                "created_at": now,
                "closed_at": None,
                "measured_until": None,
            }
        )
        return study_id

    def get(self, study_id: str) -> dict | None:
        return fields(self.col("study").find_one({"study_id": study_id}), STUDY_FIELDS)

    def active(self) -> dict | None:
        """The study still running or collecting surveys; at most one at a time."""
        row = self.col("study").find_one(
            {"status": {"$in": list(ACTIVE)}},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        return fields(row, STUDY_FIELDS)

    def all(self) -> list[dict]:
        studies = list(
            self.col("study").find().sort([("created_at", DESCENDING), ("_id", DESCENDING)])
        )
        out = []
        for s in studies:
            item = fields(s, STUDY_FIELDS)
            item["participants"] = self.col("study_participant").count_documents(  # type: ignore[index]
                {"study_id": s["study_id"], "withdrawn_at": None}
            )
            item["surveys"] = self.col("study_survey").count_documents(  # type: ignore[index]
                {"study_id": s["study_id"]}
            )
            out.append(item)
        return out  # type: ignore[return-value]

    def set_status(self, study_id: str, status: str) -> None:
        if status not in STATUSES:
            raise ValueError(f"unknown study status {status}")
        now = _now()
        studies = self.col("study")
        studies.update_one(
            {"study_id": study_id},
            {"$set": {"status": status, "closed_at": now if status == "closed" else None}},
        )
        # The measured phase ends the first time the study leaves "running".
        studies.update_one(
            {"study_id": study_id, "measured_until": None}, {"$set": {"measured_until": now}}
        )

    def participants(self, study_id: str) -> list[dict]:
        rows = (
            self.col("study_participant").find({"study_id": study_id}).sort("account_id", ASCENDING)
        )
        names = ("account_id", "arm", "enrolled_at", "withdrawn_at", "code")
        return [fields(r, names) for r in rows]  # type: ignore[misc]

    def membership(self, account_id: str) -> dict | None:
        """This learner's place in the active study, withdrawn or not."""
        places = {
            p["study_id"]: p for p in self.col("study_participant").find({"account_id": account_id})
        }
        if not places:
            return None
        study = self.col("study").find_one(
            {"study_id": {"$in": list(places)}, "status": {"$in": list(ACTIVE)}},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        if study is None:
            return None
        place = places[study["study_id"]]
        return {
            "study_id": study["study_id"],
            "name": study["name"],
            "status": study["status"],
            "arm": place["arm"],
            "withdrawn_at": place.get("withdrawn_at"),
        }

    def withdraw(self, account_id: str) -> int:
        """Leave every active study; from then on the learner sees full feedback again."""
        active = [s["study_id"] for s in self.col("study").find({"status": {"$in": list(ACTIVE)}})]
        done = self.col("study_participant").update_many(
            {"account_id": account_id, "withdrawn_at": None, "study_id": {"$in": active}},
            {"$set": {"withdrawn_at": _now()}},
        )
        return done.modified_count

    def save_survey(self, study_id: str, account_id: str, answers: dict) -> None:
        self.col("study_survey").update_one(
            {"study_id": study_id, "account_id": account_id},
            {
                "$set": {
                    "answers_json": json.dumps(answers, ensure_ascii=False),
                    "submitted_at": _now(),
                }
            },
            upsert=True,
        )

    def surveys(self, study_id: str) -> dict[str, dict]:
        rows = self.col("study_survey").find({"study_id": study_id})
        return {r["account_id"]: json.loads(r["answers_json"]) for r in rows}

    def has_survey(self, study_id: str, account_id: str) -> bool:
        found = self.col("study_survey").find_one({"study_id": study_id, "account_id": account_id})
        return found is not None

    def erase_account(self, account_id: str) -> None:
        """Erasure (FR-35) takes the learner out of every study, past ones included."""
        self.col("study_survey").delete_many({"account_id": account_id})
        self.col("study_participant").delete_many({"account_id": account_id})
