"""The words a learner says again from one of their recordings (D089).

One collection, `word_drill`: a `WordDrill` per learner, response and word,
holding its takes (`DrillTake`), which live and go with it. A drill exists only
once the learner has said the word again: the words offered are worked out
from the stored transcript each time (`lessons.drill.pick`), so a report
nobody practises from leaves nothing behind.

D090 adds `drill_passage`: a `DrillPassage` per passage written around a
learner's open drills, holding the drills it was written for and its reading
takes (`PassageTake`). A take of a passage is also a take of each of its
words, recorded on that word's `WordDrill`.

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
    "phrase",
    "streak",
    "passed",
    "takes",
    "created_at",
    "updated_at",
)
PASSAGE_FIELDS = (
    "passage_id",
    "account_id",
    "drill_ids",
    "text",
    "source",
    "takes",
    "created_at",
)
# Takes kept per passage, as per word.
MAX_PASSAGE_TAKES = MAX_TAKES


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


@dataclass
class PassageTake:
    """One reading of a passage: which of its words came through clearly."""

    clear: list[str]
    unclear: list[str]
    created_at: str


@dataclass
class DrillPassage:
    """A passage written around some of a learner's open drills (D090).

    `source` is "model" when the language model wrote it (and it was paid
    for), "phrases" when it is the learner's own phrases put together.
    `words` are the words of its drills (`drill_ids`), in that order: read
    from the drills, not stored with the passage (D105).
    """

    passage_id: str
    account_id: str
    words: list[str]
    drill_ids: list[str]
    text: str
    source: str
    takes: list[PassageTake] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def from_doc(cls, doc: dict, words: list[str]) -> DrillPassage:
        row = fields(doc, PASSAGE_FIELDS) or {}
        row["takes"] = [PassageTake(**t) for t in row.get("takes") or []]
        return cls(**row, words=words)

    def to_doc(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "words"}

    def view(self) -> dict:
        return {
            "passage_id": self.passage_id,
            "words": list(self.words),
            "text": self.text,
            "source": self.source,
            "takes": len(self.takes),
            "created_at": self.created_at,
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
            # Same second: the one written last first (D090 picks from the top).
            .sort([("updated_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [WordDrill.from_doc(r) for r in rows]

    def by_ids(self, account_id: str, drill_ids: list[str]) -> list[WordDrill]:
        """This learner's drills among `drill_ids`, in the order given."""
        rows = self.col("word_drill").find(
            {"account_id": account_id, "drill_id": {"$in": drill_ids}}
        )
        found = {d.drill_id: d for d in map(WordDrill.from_doc, rows)}
        return [found[i] for i in drill_ids if i in found]

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

    # ------------------------------------------------------------ passages (D090)

    def save_passage(self, passage: DrillPassage) -> DrillPassage:
        passage.created_at = passage.created_at or _now()
        self.col("drill_passage").insert_one(passage.to_doc())
        return passage

    def _passage(self, doc: dict | None) -> DrillPassage | None:
        """A stored passage with the words of its drills."""
        if doc is None:
            return None
        drills = self.by_ids(doc["account_id"], list(doc.get("drill_ids") or []))
        return DrillPassage.from_doc(doc, [d.word for d in drills])

    def passage(self, account_id: str, passage_id: str) -> DrillPassage | None:
        doc = self.col("drill_passage").find_one(
            {"account_id": account_id, "passage_id": passage_id}
        )
        return self._passage(doc)

    def passage_for(self, account_id: str, drill_ids: list[str]) -> DrillPassage | None:
        """The latest passage written for exactly these drills: read again, never paid again."""
        doc = self.col("drill_passage").find_one(
            {"account_id": account_id, "drill_ids": {"$size": len(drill_ids), "$all": drill_ids}},
            sort=[("created_at", DESCENDING)],
        )
        return self._passage(doc)

    def model_passages_since(self, account_id: str, since: str) -> int:
        """Passages the model wrote for this learner since `since`: their daily cap."""
        return self.col("drill_passage").count_documents(
            {"account_id": account_id, "source": "model", "created_at": {"$gte": since}}
        )

    def record_passage_take(self, account_id: str, passage_id: str, take: PassageTake) -> None:
        self.col("drill_passage").update_one(
            {"account_id": account_id, "passage_id": passage_id},
            {"$push": {"takes": {"$each": [asdict(take)], "$slice": -MAX_PASSAGE_TAKES}}},
        )

    def passages_of(self, account_id: str) -> list[dict]:
        """Every passage of one learner with its takes, oldest first."""
        rows = self.col("drill_passage").find({"account_id": account_id}).sort("created_at", 1)
        return [asdict(self._passage(r)) for r in rows]  # type: ignore[arg-type]

    def erase_account(self, account_id: str) -> int:
        """Forget the learner's drills and passages; how many documents went."""
        gone = self.col("word_drill").delete_many({"account_id": account_id}).deleted_count
        return (
            gone + self.col("drill_passage").delete_many({"account_id": account_id}).deleted_count
        )
