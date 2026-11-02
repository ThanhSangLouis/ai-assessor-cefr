"""The words a learner says again from one of their recordings (D089).

One collection, `word_drill`: a `WordDrill` per learner, response and word,
holding its takes (`DrillTake`), which live and go with it. A drill exists only
once the learner has said the word again: the words offered are worked out
from the stored transcript each time (`lessons.drill.pick`), so a report
nobody practises from leaves nothing behind.

It lives in the learning store, beside the attempts and reviews, and is erased
with them (`LessonRepository.erase_account` is not enough: see
`LearningFacade.erase_account`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from pymongo import DESCENDING

from aicefr.lessons.drill import MAX_TAKES, PASS_STREAK, next_streak
from aicefr.lessons.model import new_id
from aicefr.storage.db import IntegrityError, MongoStore, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

DRILL_FIELDS = (
    "drill_id",
    "account_id",
    "response_id",
    "word",
    "word_index",
    "phrase",
    "streak",
    "passed",
    "takes",
    "created_at",
    "updated_at",
)


@dataclass
class DrillTake:
    """One spoken take of the phrase: whether the word came through clearly."""

    passed: bool
    said: str | None
    created_at: str


@dataclass
class WordDrill:
    drill_id: str
    account_id: str
    response_id: str
    word: str
    word_index: int
    phrase: str
    streak: int = 0
    passed: bool = False
    takes: list[DrillTake] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_doc(cls, doc: dict) -> WordDrill:
        row = fields(doc, DRILL_FIELDS) or {}
        row["takes"] = [DrillTake(**t) for t in row.get("takes") or []]
        row["streak"] = int(row.get("streak") or 0)
        row["passed"] = bool(row.get("passed"))
        return cls(**row)

    def view(self) -> dict:
        return {
            "drill_id": self.drill_id,
            "word": self.word,
            "streak": self.streak,
            "passed": self.passed,
            "takes": len(self.takes),
            "last_said": self.takes[-1].said if self.takes else None,
        }


class DrillRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def of_response(self, account_id: str, response_id: str) -> dict[str, WordDrill]:
        rows = self.col("word_drill").find({"account_id": account_id, "response_id": response_id})
        return {d.word: d for d in map(WordDrill.from_doc, rows)}

    def record(
        self,
        account_id: str,
        response_id: str,
        word: str,
        word_index: int,
        phrase: str,
        passed: bool,
        said: str | None,
    ) -> WordDrill:
        """Add one take, made the first time the word is said again; the drill after it.

        A drill already passed stays passed: saying it once more is practice,
        not a test it can fail.
        """
        col = self.col("word_drill")
        key = {"account_id": account_id, "response_id": response_id, "word": word}
        now = _now()
        if col.find_one(key) is None:
            try:
                col.insert_one(
                    {
                        **key,
                        "drill_id": new_id("d"),
                        "word_index": word_index,
                        "phrase": phrase,
                        "streak": 0,
                        "passed": False,
                        "takes": [],
                        "created_at": now,
                        "updated_at": now,
                    }
                )
            except IntegrityError:
                pass  # made by another request a moment ago
        drill = WordDrill.from_doc(col.find_one(key))
        streak = next_streak(drill.streak, passed)
        take = asdict(DrillTake(passed=passed, said=said, created_at=now))
        col.update_one(
            key,
            {
                "$push": {"takes": {"$each": [take], "$slice": -MAX_TAKES}},
                "$set": {
                    "streak": streak,
                    "passed": drill.passed or streak >= PASS_STREAK,
                    "updated_at": now,
                },
            },
        )
        return WordDrill.from_doc(col.find_one(key))

    def open_words(self, account_id: str, limit: int = 30) -> list[WordDrill]:
        """Words said again but not yet clear twice in a row, the latest first."""
        rows = (
            self.col("word_drill")
            .find({"account_id": account_id, "passed": False})
            .sort([("updated_at", DESCENDING)])
            .limit(limit)
        )
        return [WordDrill.from_doc(r) for r in rows]

    def all_of(self, account_id: str) -> list[dict]:
        """Every drill of one learner with its takes, oldest first."""
        rows = self.col("word_drill").find({"account_id": account_id}).sort("created_at", 1)
        return [asdict(WordDrill.from_doc(r)) for r in rows]

    def counts(self, account_id: str) -> dict:
        col = self.col("word_drill")
        return {
            "practised": col.count_documents({"account_id": account_id}),
            "passed": col.count_documents({"account_id": account_id, "passed": True}),
        }

    def erase_account(self, account_id: str) -> int:
        return self.col("word_drill").delete_many({"account_id": account_id}).deleted_count
