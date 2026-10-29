"""Persistence for the blind double rating of the field study (D030).

One collection, `rating_batch` (D060): a batch and its sheets. A sheet is a
`Rating` -- one rater's slot on one response, and, once submitted, what they
said -- and lives in its batch's document (`RatingBatch ◆ Rating` on the class
diagram): it is drawn with the batch and has no life outside it. Erasing a
participant's response (FR-35) pulls every sheet about it
(`Repository._forget_responses`). The operational review flow is never
touched: a review decision stays where it was (HUONG_PHAT_TRIEN_TIEP §2.1,
"không đụng apply_review").

What a rater may see is decided in the API layer; this module still keeps the
two kinds of read apart: `rater_view` returns nothing a rater must not see
(no response id, no speaker, no machine score), `analysis_rows` returns
everything the analysis needs and is for administrators only.

Blindness is also a fact about the past. A response keeps who has opened its
machine result (`response.machine_seen`); with the teachers' review decisions
it says who is no longer blind to it. Such a rater is never drawn for it, and a
sheet of theirs still pending stops taking a rating -- which is also what keeps
a batch that was closed, looked at, then reopened from collecting anchored
ratings.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from pymongo import DESCENDING
from pymongo.database import Database

from aicefr.contracts import Band
from aicefr.infra.blobs import key_of
from aicefr.research import assign
from aicefr.research.agreement import (
    BANDS,
    CRITERIA,
    RatedResponse,
    RaterScore,
    needs_adjudication,
)
from aicefr.storage.db import MongoStore, ensure_indexes, fields
from aicefr.storage.db import now_iso as _now

INDEXES = {
    "rating_batch": [
        (("batch_id",), True),
        (("ratings.rater_id",), False),
        (("ratings.response_id",), False),
        (("ratings.assignment_id",), False),
    ],
}

RATING_FIELDS = (
    "assignment_id",
    "score_range",
    "score_accuracy",
    "score_fluency",
    "score_coherence",
    "score_phonology",
    "score_overall",
    "band",
    "unscorable",
    "unscorable_reason",
    "reason",
    "submitted_at",
)

# Why a recording could not be rated (appendix B of the survey plan).
UNSCORABLE_REASONS = {
    "broken": "Bản ghi hỏng",
    "inaudible": "Không nghe rõ",
    "off_task": "Nói sai đề",
}


@dataclass
class Rating:
    """One rater's sheet for one response in a batch, and what they gave once submitted."""

    assignment_id: str
    response_id: str
    rater_id: str
    slot: int  # 1 and 2 the primary raters, 3 the adjudicator
    position: int  # in the rater's own random order
    opened_at: str | None = None
    score_range: float | None = None
    score_accuracy: float | None = None
    score_fluency: float | None = None
    score_coherence: float | None = None
    score_phonology: float | None = None
    score_overall: float | None = None
    band: Band | None = None
    unscorable: int = 0
    unscorable_reason: str | None = None
    reason: str | None = None
    submitted_at: str | None = None

    @classmethod
    def from_doc(cls, doc: dict) -> Rating:
        band = doc.get("band")
        return cls(**{**doc, "band": Band(band) if band else None})

    def to_doc(self) -> dict:
        return {**asdict(self), "band": self.band.value if self.band else None}


@dataclass
class RatingBatch:
    batch_id: str
    name: str
    seed: int
    created_by: str
    created_at: str
    closed: bool = False
    ratings: list[Rating] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> RatingBatch:
        return cls(
            batch_id=doc["batch_id"],
            name=doc["name"],
            seed=doc["seed"],
            created_by=doc["created_by"],
            created_at=doc["created_at"],
            closed=bool(doc.get("closed", False)),
            ratings=[Rating.from_doc(r) for r in doc.get("ratings", [])],
        )

    def to_doc(self) -> dict:
        return {**asdict(self), "ratings": [r.to_doc() for r in self.ratings]}

    @property
    def status(self) -> str:
        """`open` or `closed`, as the screens name it."""
        return "closed" if self.closed else "open"


def _batches(db: Database, query: dict | None = None) -> list[RatingBatch]:
    rows = (
        db["rating_batch"].find(query or {}).sort([("created_at", DESCENDING), ("_id", DESCENDING)])
    )
    return [RatingBatch.from_doc(r) for r in rows]


def _sheets(db: Database, query: dict | None = None, **match) -> list[dict]:
    """Every sheet of the batches `query` picks whose fields equal `match`, with its batch id."""
    out = []
    for b in _batches(db, query):
        for r in b.ratings:
            sheet = {**r.to_doc(), "batch_id": b.batch_id}
            if all(sheet.get(k) == v for k, v in match.items()):
                out.append(sheet)
    return out


def _seen(db: Database, response_ids: list[str] | None = None) -> set[tuple[str, str]]:
    """(person, response) pairs where the person has seen the machine's result.

    Opened it (`response.machine_seen`), or decided a review on it -- decisions
    made before the opening was recorded count too.
    """
    query = {} if response_ids is None else {"response_id": {"$in": list(response_ids)}}
    pairs: set[tuple[str, str]] = set()
    for r in db["response"].find(query, {"response_id": 1, "machine_seen": 1, "reviews": 1}):
        pairs |= {(m["account_id"], r["response_id"]) for m in r.get("machine_seen") or []}
        pairs |= {(v["reviewer_id"], r["response_id"]) for v in r.get("reviews") or []}
    return pairs


def _rated(sheets: list[dict]) -> dict[str, dict]:
    """The ratings submitted on these sheets, by sheet."""
    return {
        x["assignment_id"]: fields(x, RATING_FIELDS)  # type: ignore[misc]
        for x in sheets
        if x.get("submitted_at") is not None
    }


def _machine(db: Database, responses: dict[str, dict]) -> dict[str, dict]:
    """The machine's own output per response, before any teacher decision overwrote it.

    A review rewrites overall_0_6 and overall_band, and keeps the machine's
    values as the first review's "old" fields. A response with a review was
    routed to a teacher, which is the routing flag RQ4 compares.
    """
    out = {}
    for rid, r in responses.items():
        reviews = sorted(r.get("reviews") or [], key=lambda v: v.get("review_id") or 0)
        review = reviews[0] if reviews else None
        out[rid] = {
            "ai_overall": review.get("old_score") if review else r.get("overall_0_6"),
            "ai_band": review.get("old_band") if review else r.get("overall_band"),
            "flagged": r.get("status") == "REVIEW_REQUIRED" or review is not None,
        }
    return out


class AlreadyRated(Exception):
    """This assignment already has its rating; ratings are final once submitted."""


class SeenMachine(Exception):
    """The rater has seen the machine's result for this response: the sheet is no longer blind."""


class RatingRepository(MongoStore):
    def __init__(self, db_path: str | Path = "aicefr.db", blobs=None) -> None:
        self.db_path = str(db_path)
        self._blobs = blobs  # D051: where the recordings are; unset, the settings'
        ensure_indexes(self.db, INDEXES, "rating")

    @property
    def blobs(self):
        if self._blobs is None:
            from aicefr.config import get_settings
            from aicefr.infra.blobs import blob_store

            self._blobs = blob_store(get_settings())
        return self._blobs

    def _owed(self, rater_id: str, response_id: str | None = None) -> list[dict]:
        """Sheets the rater still owes, blind: batch open, nothing submitted, and the
        rater has not seen the machine's result since."""
        db = self.db
        match = {"rater_id": rater_id}
        if response_id is not None:
            match["response_id"] = response_id
        sheets = _sheets(db, {"closed": False, "ratings.rater_id": rater_id}, **match)
        if not sheets:
            return []
        seen = _seen(db, list({x["response_id"] for x in sheets}))
        return [
            x
            for x in sheets
            if x["submitted_at"] is None and (rater_id, x["response_id"]) not in seen
        ]

    # ------------------------------------------------------------ eligibility

    def eligible(self, allowed_accounts: set[str], only_new: bool = True) -> list[str]:
        """Responses that may go to raters: assessed, recorded, owner accepted the terms.

        A practice attempt is not assessment data (D023); a response without its
        recording cannot be listened to; and rating is research use, so only
        owners who accepted the terms of use (D058) count. `only_new` leaves
        out responses already in a batch.
        """
        if not allowed_accounts:
            return []
        rows = list(
            self.col("response").find(
                {
                    "purpose": "assessment",
                    "audio_path": {"$ne": None},
                    "status": {"$in": ["COMPLETED", "REVIEW_REQUIRED"]},
                    "account_id": {"$in": sorted(allowed_accounts)},
                },
                {"response_id": 1, "audio_path": 1},
            )
        )
        if only_new:
            batched = {x["response_id"] for x in _sheets(self.db)}
            rows = [r for r in rows if r["response_id"] not in batched]
        return [r["response_id"] for r in rows if self.blobs.exists(key_of(r["audio_path"]))]

    # ------------------------------------------------------------ batches

    def create_batch(
        self,
        name: str,
        created_by: str,
        response_ids: list[str],
        rater_ids: list[str],
        seed: int,
    ) -> dict:
        """A batch with two raters per response, each rater in their own random order.

        Nobody is given a response whose machine result they have already seen.
        A response that cannot find two raters who have not is left out and
        counted in `skipped_seen`; when that leaves nothing, ValueError.
        """
        planned = assign.plan(response_ids, rater_ids, seed, exclude=self.seen_by(response_ids))
        kept = {p.response_id for p in planned}
        if not kept:
            raise ValueError("no response has two raters who have not seen the machine's result")
        batch = RatingBatch(
            batch_id=uuid.uuid4().hex[:12],
            name=name,
            seed=seed,
            created_by=created_by,
            created_at=_now(),
            ratings=[_sheet(p) for p in planned],
        )
        # One document: the batch is listed with every sheet in it, never half.
        self.col("rating_batch").insert_one(batch.to_doc())
        batch_id = batch.batch_id
        return {
            "batch_id": batch_id,
            "responses": len(kept),
            "skipped_seen": len(set(response_ids)) - len(kept),
        }

    @staticmethod
    def _insert(db: Database, batch_id: str, planned: list[assign.Planned]) -> None:
        if not planned:
            return
        db["rating_batch"].update_one(
            {"batch_id": batch_id},
            {"$push": {"ratings": {"$each": [_sheet(p).to_doc() for p in planned]}}},
        )

    def batch(self, batch_id: str) -> dict | None:
        found = _batches(self.db, {"batch_id": batch_id})
        return _batch_view(found[0]) if found else None

    def set_status(self, batch_id: str, status: str) -> None:
        if status not in ("open", "closed"):
            raise ValueError(status)
        self.col("rating_batch").update_one(
            {"batch_id": batch_id}, {"$set": {"closed": status == "closed"}}
        )

    def batches(self) -> list[dict]:
        """Every batch with its progress per rater and how many responses need a third rater."""
        db = self.db
        batches = _batches(db)
        sheets = _sheets(db)
        rated = _rated(sheets)
        seen = _seen(db, list({x["response_id"] for x in sheets}))
        out = []
        for b in batches:
            mine = [x for x in sheets if x["batch_id"] == b.batch_id]
            raters: dict[str, dict] = {}
            done = voided = 0
            for x in mine:
                is_done = x["assignment_id"] in rated
                # Owed, but the rater has seen the machine's result since: it
                # will never be rated blind.
                is_void = not is_done and (x["rater_id"], x["response_id"]) in seen
                entry = raters.setdefault(
                    x["rater_id"], {"total": 0, "done": 0, "adjudication": 0, "voided": 0}
                )
                entry["total"] += 1
                entry["done"] += int(is_done)
                entry["adjudication"] += int(x["slot"] == 3)
                entry["voided"] += int(is_void)
                done += int(is_done)
                voided += int(is_void)
            out.append(
                {
                    **_batch_view(b),
                    "responses": len({x["response_id"] for x in mine}),
                    "assignments": len(mine),
                    "done": done,
                    "voided": voided,
                    "raters": raters,
                    "needs_adjudication": len(self._to_adjudicate(b.batch_id)),
                }
            )
        return out

    # ------------------------------------------------------------ raters

    def open_count(self, rater_id: str) -> int:
        """Sheets this rater still owes, blind, in batches still open."""
        return len(self._owed(rater_id))

    def has_open(self, rater_id: str, response_id: str) -> bool:
        """Whether this rater still has to rate this response blind, in an open batch."""
        return bool(self._owed(rater_id, response_id))

    def blinded_responses(self, rater_id: str) -> set[str]:
        """Every response this rater still has to rate blind: kept out of their review queue."""
        return {x["response_id"] for x in self._owed(rater_id)}

    def batch_responses(self, batch_id: str) -> set[str]:
        return {x["response_id"] for x in _sheets(self.db, {"batch_id": batch_id})}

    # ------------------------------------------------------------ who has seen the machine

    def saw_machine(self, account_id: str, response_id: str, via: str) -> None:
        """Note that this person has had the machine's result for this response in view."""
        # The first time only: appended where this person is not noted yet.
        self.col("response").update_one(
            {"response_id": response_id, "machine_seen.account_id": {"$ne": account_id}},
            {"$push": {"machine_seen": {"account_id": account_id, "first_seen": _now(),
                                        "via": via}}},
        )  # fmt: skip

    def seen_by(self, response_ids: list[str]) -> dict[str, set[str]]:
        """Per response, everyone who has opened its machine result or decided a review on it."""
        out: dict[str, set[str]] = {}
        for account_id, response_id in _seen(self.db, list(set(response_ids))):
            out.setdefault(response_id, set()).add(account_id)
        return out

    def rater_list(self, rater_id: str) -> list[dict]:
        """This rater's assignments, in their own order, without anything about the response."""
        db = self.db
        rows = []
        # Newest batch first (`_batches` sorts so), each in the rater's own order.
        for b in _batches(db, {"ratings.rater_id": rater_id}):
            mine = sorted(
                (x for x in b.ratings if x.rater_id == rater_id), key=lambda x: x.position
            )
            seen = _seen(db, list({x.response_id for x in mine}))
            rows += [
                {
                    "assignment_id": x.assignment_id,
                    "batch_id": b.batch_id,
                    "position": x.position,
                    "opened_at": x.opened_at,
                    "slot": x.slot,
                    "name": b.name,
                    "status": b.status,
                    "submitted_at": x.submitted_at,
                    "seen": int((rater_id, x.response_id) in seen),
                }
                for x in mine
            ]
        return rows

    def rater_view(self, assignment_id: str) -> dict | None:
        """One assignment as its rater may see it, plus the private fields the API needs.

        `response_id` and `audio_path` come back for the server's own use (the
        task prompt, the audio stream); the API must not pass them on.
        """
        db = self.db
        found = _batches(db, {"ratings.assignment_id": assignment_id})
        if not found:
            return None
        b = found[0]
        x = next(y.to_doc() for y in b.ratings if y.assignment_id == assignment_id)
        r = db["response"].find_one({"response_id": x["response_id"]})
        if r is None:
            return None
        mine = [y.to_doc() for y in b.ratings if y.rater_id == x["rater_id"]]
        rated = _rated(mine)
        seen = _seen(db, list({y["response_id"] for y in mine}))
        following = sorted(
            (
                y
                for y in mine
                if y["assignment_id"] != assignment_id
                and y["assignment_id"] not in rated
                and (x["rater_id"], y["response_id"]) not in seen
            ),
            key=lambda y: y["position"],
        )
        return {
            "assignment_id": x["assignment_id"],
            "batch_id": b.batch_id,
            "rater_id": x["rater_id"],
            "slot": x["slot"],
            "position": x["position"],
            "opened_at": x.get("opened_at"),
            "response_id": x["response_id"],
            "name": b.name,
            "status": b.status,
            "task_id": r.get("task_id"),
            "audio_path": r.get("audio_path"),
            "seen": int((x["rater_id"], x["response_id"]) in seen),
            "total": len(mine),
            "rating": rated.get(assignment_id),
            "next_assignment_id": following[0]["assignment_id"] if following else None,
        }

    def mark_opened(self, assignment_id: str) -> None:
        """The first time the rater opens it, for the time-to-rate the report states."""
        self.col("rating_batch").update_one(
            {"ratings": {"$elemMatch": {"assignment_id": assignment_id, "opened_at": None}}},
            {"$set": {"ratings.$.opened_at": _now()}},
        )

    def submit(
        self,
        assignment_id: str,
        rating: RaterScore,
        reason: str | None,
        unscorable_reason: str | None,
    ) -> None:
        """Record a rating. Final: a second submission raises AlreadyRated.

        A rater who has seen the machine's result for the response since the
        sheet was given (SeenMachine) can no longer rate it blind.
        """
        db = self.db
        found = _sheets(db, {"ratings.assignment_id": assignment_id}, assignment_id=assignment_id)
        x = found[0] if found else None
        if x is not None and (x["rater_id"], x["response_id"]) in _seen(db, [x["response_id"]]):
            raise SeenMachine(assignment_id)
        given = {
            **{f"ratings.$.score_{k}": rating.criteria.get(k) for k in CRITERIA},
            "ratings.$.score_overall": rating.overall,
            "ratings.$.band": rating.band,
            "ratings.$.unscorable": int(rating.unscorable),
            "ratings.$.unscorable_reason": unscorable_reason,
            "ratings.$.reason": reason,
            "ratings.$.submitted_at": _now(),
        }
        # Final: only a sheet with nothing submitted takes the rating.
        done = db["rating_batch"].update_one(
            {"ratings": {"$elemMatch": {"assignment_id": assignment_id, "submitted_at": None}}},
            {"$set": given},
        )
        if not done.modified_count:
            raise AlreadyRated(assignment_id)

    # ------------------------------------------------------------ adjudication

    def _to_adjudicate(self, batch_id: str) -> list[tuple[str, set[str]]]:
        """Responses whose two primary ratings disagree and have no third rater yet."""
        out = []
        for item in self._ratings_by_response(batch_id):
            slots = item["slots"]
            if 3 in item["assigned"] or 1 not in slots or 2 not in slots:
                continue
            if needs_adjudication(slots[1], slots[2]):
                out.append((item["response_id"], set(item["raters"])))
        return out

    def _last_position(self, batch_id: str, rater_id: str) -> int:
        mine = _sheets(self.db, {"batch_id": batch_id}, rater_id=rater_id)
        return max((int(x["position"]) for x in mine), default=0)

    def add_adjudication(self, batch_id: str, adjudicator_id: str, seed: int) -> dict:
        """A third rating, by one adjudicator, for every response that needs one.

        A response the adjudicator already rated as a primary rater is skipped
        and counted: adjudicating your own disagreement is not adjudication.
        So is one whose machine result they have seen: that would not be blind.
        """
        todo = self._to_adjudicate(batch_id)
        seen = self.seen_by([rid for rid, _ in todo])
        own = [rid for rid, raters in todo if adjudicator_id in raters]
        usable = [
            rid
            for rid, raters in todo
            if adjudicator_id not in raters and adjudicator_id not in seen.get(rid, set())
        ]
        start = self._last_position(batch_id, adjudicator_id)
        self._insert(self.db, batch_id, assign.adjudication(usable, adjudicator_id, seed, start))
        return {
            "created": len(usable),
            "skipped_own": len(own),
            "skipped_seen": len(todo) - len(usable) - len(own),
        }

    def replace_void(self, batch_id: str, rater_id: str, seed: int) -> dict:
        """Hand every sheet of the batch that went void to another rater, slot kept.

        A void sheet is owed but no longer blind: its rater has seen the
        machine's result since it was given. It has no rating to lose, so it is
        removed and its slot goes to `rater_id` -- unless that rater already
        rates the response in this batch (`skipped_own`) or has seen its machine
        result too (`skipped_seen`).
        """
        db = self.db
        sheets = _sheets(db, {"batch_id": batch_id})
        rated = _rated(sheets)
        seen_pairs = _seen(db, list({x["response_id"] for x in sheets}))
        void = sorted(
            (
                x
                for x in sheets
                if x["assignment_id"] not in rated
                and (x["rater_id"], x["response_id"]) in seen_pairs
            ),
            key=lambda x: (x["response_id"], x["slot"]),
        )
        taken = {x["response_id"] for x in sheets if x["rater_id"] == rater_id}
        seen = self.seen_by([v["response_id"] for v in void])
        moved, own, blocked = [], 0, 0
        for v in void:
            if v["response_id"] in taken:
                own += 1
            elif rater_id in seen.get(v["response_id"], set()):
                blocked += 1
            else:
                moved.append(v)
                taken.add(v["response_id"])
        start = self._last_position(batch_id, rater_id)
        if moved:
            db["rating_batch"].update_one(
                {"batch_id": batch_id},
                {
                    "$pull": {
                        "ratings": {"assignment_id": {"$in": [v["assignment_id"] for v in moved]}}
                    }
                },
            )
        planned = assign.reassignment(
            [(v["response_id"], v["slot"]) for v in moved], rater_id, seed, start
        )
        self._insert(db, batch_id, planned)
        return {"created": len(moved), "skipped_own": own, "skipped_seen": blocked}

    # ------------------------------------------------------------ analysis

    def _ratings_by_response(self, batch_id: str, allowed: set[str] | None = None) -> list[dict]:
        db = self.db
        sheets = sorted(
            _sheets(db, {"batch_id": batch_id}), key=lambda x: (x["response_id"], x["slot"])
        )
        responses = {
            r["response_id"]: r
            for r in db["response"].find(
                {"response_id": {"$in": list({x["response_id"] for x in sheets})}}
            )
        }
        machine = _machine(db, responses)
        rated = _rated(sheets)
        items: dict[str, dict] = {}
        for x in sheets:
            r = responses.get(x["response_id"])
            if r is None:
                continue
            if allowed is not None and r.get("account_id") not in allowed:
                continue
            item = items.setdefault(
                x["response_id"],
                {
                    "response_id": x["response_id"],
                    "speaker_id": r.get("speaker_id"),
                    "task_id": r.get("task_id"),
                    "ai_overall": machine[x["response_id"]]["ai_overall"],
                    "ai_band": machine[x["response_id"]]["ai_band"],
                    "flagged": bool(machine[x["response_id"]]["flagged"]),
                    "assigned": set(),
                    "raters": [],
                    "slots": {},
                    "rows": [],
                },
            )
            item["assigned"].add(x["slot"])
            item["raters"].append(x["rater_id"])
            rating = rated.get(x["assignment_id"])
            if rating is not None and rating["submitted_at"] is not None:
                row = {
                    "response_id": x["response_id"],
                    "rater_id": x["rater_id"],
                    "slot": x["slot"],
                    "opened_at": x.get("opened_at"),
                    **rating,
                    "speaker_id": r.get("speaker_id"),
                    "account_id": r.get("account_id"),
                    "task_id": r.get("task_id"),
                    **machine[x["response_id"]],
                }
                item["slots"][x["slot"]] = _rating(row)
                item["rows"].append(row)
        return list(items.values())

    def analysis_rows(self, batch_id: str, allowed: set[str]) -> list[dict]:
        """Every response of the batch whose owner is in `allowed`, with all its ratings.

        For administrators: holds the speaker pseudonym (the bootstrap resamples
        speakers) and the machine's own score next to the human ones.
        """
        return self._ratings_by_response(batch_id, allowed)

    def all_times_to_rate(self) -> list[float]:
        """Seconds from opening to submission, every batch: rating without the machine (D041)."""
        return [s for b in _batches(self.db) for s in self.times_to_rate(b.batch_id)]

    def times_to_rate(self, batch_id: str) -> list[float]:
        """Seconds from first opening to submission, per submitted rating."""
        done = [
            x
            for x in _sheets(self.db, {"batch_id": batch_id})
            if x["opened_at"] is not None and x["submitted_at"] is not None
        ]
        out = []
        for x in sorted(done, key=lambda x: x["submitted_at"]):
            seconds = (
                datetime.fromisoformat(x["submitted_at"]) - datetime.fromisoformat(x["opened_at"])
            ).total_seconds()
            out.append(max(0.0, seconds))
        return out


def _sheet(p: assign.Planned) -> Rating:
    return Rating(
        assignment_id=uuid.uuid4().hex[:16],
        response_id=p.response_id,
        rater_id=p.rater_id,
        slot=p.slot,
        position=p.position,
    )


def _batch_view(b: RatingBatch) -> dict:
    return {
        "batch_id": b.batch_id,
        "name": b.name,
        "seed": b.seed,
        "status": b.status,
        "created_by": b.created_by,
        "created_at": b.created_at,
    }


def _rating(row: dict) -> RaterScore:
    unscorable = bool(row["unscorable"])
    return RaterScore(
        rater_id=row["rater_id"],
        overall=None if unscorable else row["score_overall"],
        band=None if unscorable else row["band"],
        criteria={} if unscorable else {k: row[f"score_{k}"] for k in CRITERIA},
        unscorable=unscorable,
        adjudication=row["slot"] == 3,
    )


def rated_responses(rows: list[dict]) -> list[RatedResponse]:
    """Turn `analysis_rows` into what the agreement report takes.

    A machine result counts only whole: a score on the 0-6 scale and one of the
    three bands. Anything else is "no machine score", which the report counts
    and states, rather than a value it would have to guess at.
    """
    items = []
    for row in rows:
        slots = row["slots"]
        ratings = tuple(slots[s] for s in (1, 2, 3) if s in slots)
        if 3 in slots and (1 not in slots or 2 not in slots):
            ratings = tuple(slots[s] for s in (1, 2) if s in slots)
        score, band = row["ai_overall"], row["ai_band"]
        whole = band in BANDS and score is not None and 0 <= score <= 6
        items.append(
            RatedResponse(
                response_id=row["response_id"],
                speaker_id=row["speaker_id"],
                ratings=ratings,
                ai_overall=score if whole else None,
                ai_band=band if whole else None,
                flagged=row["flagged"],
            )
        )
    return items
