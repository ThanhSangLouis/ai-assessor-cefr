"""Store of the feedback study (D040): the study, who is in which arm, their survey.

One collection, `study`, one document per study (D060). The document is a
`Study`, and its participants are part of it (`Study ◆ Participant` on the
class diagram): a participant exists only inside one study, and a learner's
closing survey is part of their participation, so the answers sit on the
participant rather than in a collection of their own.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pymongo import DESCENDING

from aicefr.research.study import StudyStatus
from aicefr.storage.db import MongoStore, ensure_indexes
from aicefr.storage.db import now_iso as _now

# arm: feedback | score_only. measured_until ends the measured phase: scores
# after it, when both arms see feedback again, are not outcomes. A
# participant's `code` is fixed at enrolment so exports of different days line up.
INDEXES = {
    "study": [
        (("study_id",), True),
        (("status", "created_at"), False),
        (("participants.account_id",), False),
    ],
}
ACTIVE = (StudyStatus.RUNNING.value, StudyStatus.SURVEY.value)


@dataclass
class Participant:
    """One learner in one study: the arm drawn for them, and their survey."""

    code: str
    account_id: str
    arm: str
    enrolled_at: str
    withdrawn_at: str | None = None
    survey_answers: dict | None = None
    surveyed_at: str | None = None


@dataclass
class Study:
    study_id: str
    name: str
    seed: int
    min_days: int
    status: StudyStatus
    created_by: str
    created_at: str
    closed_at: str | None = None
    measured_until: str | None = None
    participants: list[Participant] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Study:
        return cls(
            study_id=doc["study_id"],
            name=doc["name"],
            seed=doc["seed"],
            min_days=doc["min_days"],
            status=StudyStatus(doc["status"]),
            created_by=doc["created_by"],
            created_at=doc["created_at"],
            closed_at=doc.get("closed_at"),
            measured_until=doc.get("measured_until"),
            participants=[Participant(**p) for p in doc.get("participants", [])],
        )

    def to_doc(self) -> dict:
        return {**asdict(self), "status": self.status.value}

    def view(self) -> dict:
        """The study without its participants, as the screens list it."""
        return {
            "study_id": self.study_id,
            "name": self.name,
            "seed": self.seed,
            "min_days": self.min_days,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "measured_until": self.measured_until,
        }

    def place_of(self, account_id: str) -> Participant | None:
        return next((p for p in self.participants if p.account_id == account_id), None)


class StudyRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "study")

    def _load(self, study_id: str) -> Study | None:
        doc = self.col("study").find_one({"study_id": study_id})
        return Study.from_doc(doc) if doc else None

    def create(
        self, name: str, seed: int, min_days: int, created_by: str, arms: dict[str, str]
    ) -> str:
        now = _now()
        study = Study(
            study_id="st-" + uuid.uuid4().hex[:10],
            name=name,
            seed=seed,
            min_days=min_days,
            status=StudyStatus.RUNNING,
            created_by=created_by,
            created_at=now,
            # Codes in the order of the random assignment: they say nothing of
            # who is who, and never change. One document: the study is listed
            # with everybody in it enrolled, never half.
            participants=[
                Participant(code=f"P{i:03d}", account_id=account_id, arm=arm, enrolled_at=now)
                for i, (account_id, arm) in enumerate(arms.items(), 1)
            ],
        )
        self.col("study").insert_one(study.to_doc())
        return study.study_id

    def get(self, study_id: str) -> dict | None:
        found = self._load(study_id)
        return found.view() if found else None

    def active(self) -> dict | None:
        """The study still running or collecting surveys; at most one at a time."""
        row = self.col("study").find_one(
            {"status": {"$in": list(ACTIVE)}},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        return Study.from_doc(row).view() if row else None

    def all(self) -> list[dict]:
        rows = self.col("study").find().sort([("created_at", DESCENDING), ("_id", DESCENDING)])
        out = []
        for study in map(Study.from_doc, rows):
            out.append(
                {
                    **study.view(),
                    "participants": sum(p.withdrawn_at is None for p in study.participants),
                    "surveys": sum(p.survey_answers is not None for p in study.participants),
                }
            )
        return out

    def set_status(self, study_id: str, status: str) -> None:
        status = StudyStatus(status).value  # ValueError on anything else
        now = _now()
        studies = self.col("study")
        studies.update_one(
            {"study_id": study_id},
            {
                "$set": {
                    "status": status,
                    "closed_at": now if status == StudyStatus.CLOSED.value else None,
                }
            },
        )
        # The measured phase ends the first time the study leaves "running".
        studies.update_one(
            {"study_id": study_id, "measured_until": None}, {"$set": {"measured_until": now}}
        )

    def participants(self, study_id: str) -> list[dict]:
        found = self._load(study_id)
        rows = sorted(found.participants if found else [], key=lambda p: p.account_id)
        return [
            {
                "account_id": p.account_id,
                "arm": p.arm,
                "enrolled_at": p.enrolled_at,
                "withdrawn_at": p.withdrawn_at,
                "code": p.code,
            }
            for p in rows
        ]

    def membership(self, account_id: str) -> dict | None:
        """This learner's place in the active study, withdrawn or not."""
        row = self.col("study").find_one(
            {"participants.account_id": account_id, "status": {"$in": list(ACTIVE)}},
            sort=[("created_at", DESCENDING), ("_id", DESCENDING)],
        )
        if row is None:
            return None
        study = Study.from_doc(row)
        place = study.place_of(account_id)
        return {
            "study_id": study.study_id,
            "name": study.name,
            "status": study.status.value,
            "arm": place.arm,  # type: ignore[union-attr]
            "withdrawn_at": place.withdrawn_at,  # type: ignore[union-attr]
        }

    def withdraw(self, account_id: str) -> int:
        """Leave every active study; from then on the learner sees full feedback again."""
        done = self.col("study").update_many(
            {
                "status": {"$in": list(ACTIVE)},
                "participants": {"$elemMatch": {"account_id": account_id, "withdrawn_at": None}},
            },
            {"$set": {"participants.$.withdrawn_at": _now()}},
        )
        return done.modified_count

    def save_survey(self, study_id: str, account_id: str, answers: dict) -> None:
        self.col("study").update_one(
            {"study_id": study_id, "participants.account_id": account_id},
            {
                "$set": {
                    "participants.$.survey_answers": answers,
                    "participants.$.surveyed_at": _now(),
                }
            },
        )

    def surveys(self, study_id: str) -> dict[str, dict]:
        found = self._load(study_id)
        return {
            p.account_id: p.survey_answers
            for p in (found.participants if found else [])
            if p.survey_answers is not None
        }

    def has_survey(self, study_id: str, account_id: str) -> bool:
        found = self._load(study_id)
        place = found.place_of(account_id) if found else None
        return place is not None and place.survey_answers is not None

    def erase_account(self, account_id: str) -> None:
        """Erasure (FR-35) takes the learner out of every study, past ones included."""
        self.col("study").update_many(
            {"participants.account_id": account_id},
            {"$pull": {"participants": {"account_id": account_id}}},
        )
