"""Persistence for the blind double rating of the field study (D030).

The tables sit in the same database file as the responses and cascade from
them: erasing a participant's response (FR-35) erases what raters said about
it. They never touch `response` or `review_action`: the operational review flow
stays exactly as it was (HUONG_PHAT_TRIEN_TIEP §2.1, "không đụng apply_review").

What a rater may see is decided in the API layer; this module still keeps the
two kinds of read apart: `rater_view` returns nothing a rater must not see
(no response id, no speaker, no machine score), `analysis_rows` returns
everything the analysis needs and is for administrators only.

Blindness is also a fact about the past. `machine_seen` notes who has opened
the machine's result for which response; with the teachers' review decisions it
says who is no longer blind to a response. Such a rater is never drawn for it,
and a sheet of theirs still pending stops taking a rating -- which is also what
keeps a batch that was closed, looked at, then reopened from collecting
anchored ratings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from aicefr.research import assign
from aicefr.research.agreement import BANDS, CRITERIA, RatedResponse, Rating, needs_adjudication
from aicefr.storage.db import Connection, DbRow, IntegrityError, SqlStore
from aicefr.storage.db import now_iso as _now

SCHEMA = """
CREATE TABLE IF NOT EXISTS rating_batch (
    batch_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    seed        INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_by  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rating_assignment (
    assignment_id   TEXT PRIMARY KEY,
    batch_id        TEXT NOT NULL REFERENCES rating_batch(batch_id) ON DELETE CASCADE,
    response_id     TEXT NOT NULL REFERENCES response(response_id) ON DELETE CASCADE,
    rater_id        TEXT NOT NULL,
    slot            INTEGER NOT NULL,
    position        INTEGER NOT NULL,
    opened_at       TEXT,
    UNIQUE (batch_id, response_id, slot),
    UNIQUE (batch_id, response_id, rater_id)
);
CREATE INDEX IF NOT EXISTS idx_rating_rater ON rating_assignment(rater_id, batch_id);

-- Who has had the machine's result for a response in view: its report, its
-- history, the review screen. The first time only; erased with the response.
CREATE TABLE IF NOT EXISTS machine_seen (
    account_id      TEXT NOT NULL,
    response_id     TEXT NOT NULL REFERENCES response(response_id) ON DELETE CASCADE,
    first_seen      TEXT NOT NULL,
    via             TEXT NOT NULL,
    PRIMARY KEY (account_id, response_id)
);

CREATE TABLE IF NOT EXISTS research_rating (
    assignment_id       TEXT PRIMARY KEY
                        REFERENCES rating_assignment(assignment_id) ON DELETE CASCADE,
    score_range         REAL,
    score_accuracy      REAL,
    score_fluency       REAL,
    score_coherence     REAL,
    score_phonology     REAL,
    score_overall       REAL,
    band                TEXT,
    unscorable          INTEGER NOT NULL DEFAULT 0,
    unscorable_reason   TEXT,
    reason              TEXT,
    submitted_at        TEXT NOT NULL
);
"""

# Why a recording could not be rated (appendix B of the survey plan).
UNSCORABLE_REASONS = {
    "broken": "Bản ghi hỏng",
    "inaudible": "Không nghe rõ",
    "off_task": "Nói sai đề",
}

# The machine's own output, before any teacher decision overwrote it: a review
# rewrites overall_0_6 and overall_band, and keeps the machine's values as the
# first review action's "old" columns. A response with a review was routed to a
# teacher, which is the routing flag RQ4 compares.
_MACHINE = """
    CASE WHEN EXISTS (SELECT 1 FROM review_action a WHERE a.response_id = r.response_id)
         THEN (SELECT a.old_score FROM review_action a WHERE a.response_id = r.response_id
               ORDER BY a.id LIMIT 1)
         ELSE r.overall_0_6 END AS ai_overall,
    CASE WHEN EXISTS (SELECT 1 FROM review_action a WHERE a.response_id = r.response_id)
         THEN (SELECT a.old_band FROM review_action a WHERE a.response_id = r.response_id
               ORDER BY a.id LIMIT 1)
         ELSE r.overall_band END AS ai_band,
    (r.status = 'REVIEW_REQUIRED'
     OR EXISTS (SELECT 1 FROM review_action a WHERE a.response_id = r.response_id)) AS flagged
"""


# Whether the rater of assignment `x` has seen the machine's result for its
# response: opened it (machine_seen), or decided a review on it -- decisions
# made before machine_seen existed count too.
_SEEN = (
    "(EXISTS (SELECT 1 FROM machine_seen s"
    " WHERE s.account_id = x.rater_id AND s.response_id = x.response_id)"
    " OR EXISTS (SELECT 1 FROM review_action a"
    " WHERE a.reviewer_id = x.rater_id AND a.response_id = x.response_id))"
)

# A sheet the rater still owes, blind: batch open, nothing submitted, and the
# rater has not seen the machine's result since.
_OWED = (
    " JOIN rating_batch b ON b.batch_id = x.batch_id AND b.status = 'open'"
    " WHERE x.rater_id = ? AND NOT EXISTS"
    " (SELECT 1 FROM research_rating g WHERE g.assignment_id = x.assignment_id)"
    f" AND NOT {_SEEN}"
)


class AlreadyRated(Exception):
    """This assignment already has its rating; ratings are final once submitted."""


class SeenMachine(Exception):
    """The rater has seen the machine's result for this response: the sheet is no longer blind."""


class RatingRepository(SqlStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    # ------------------------------------------------------------ eligibility

    def eligible(self, allowed_accounts: set[str], only_new: bool = True) -> list[str]:
        """Responses that may go to raters: assessed, recorded, owner consents to research.

        A practice attempt is not assessment data (D023); a response without its
        recording cannot be listened to; and rating is research use, so only
        owners whose standing consent allows research count. `only_new` leaves
        out responses already in a batch.
        """
        if not allowed_accounts:
            return []
        marks = ",".join("?" * len(allowed_accounts))
        sql = (
            "SELECT r.response_id, r.audio_path FROM response r"
            " WHERE r.purpose = 'assessment' AND r.audio_path IS NOT NULL"
            " AND r.status IN ('COMPLETED', 'REVIEW_REQUIRED')"
            f" AND r.account_id IN ({marks})"
        )
        if only_new:
            sql += (
                " AND NOT EXISTS (SELECT 1 FROM rating_assignment x"
                " WHERE x.response_id = r.response_id)"
            )
        with self._conn() as c:
            rows = c.execute(sql, sorted(allowed_accounts)).fetchall()
        return [r["response_id"] for r in rows if Path(r["audio_path"]).is_file()]

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
        batch_id = uuid.uuid4().hex[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO rating_batch(batch_id,name,seed,status,created_by,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (batch_id, name, seed, "open", created_by, _now()),
            )
            self._insert(c, batch_id, planned)
        return {
            "batch_id": batch_id,
            "responses": len(kept),
            "skipped_seen": len(set(response_ids)) - len(kept),
        }

    @staticmethod
    def _insert(c: Connection, batch_id: str, planned: list[assign.Planned]) -> None:
        c.executemany(
            "INSERT INTO rating_assignment(assignment_id,batch_id,response_id,rater_id,slot,"
            "position) VALUES(?,?,?,?,?,?)",
            [
                (uuid.uuid4().hex[:16], batch_id, p.response_id, p.rater_id, p.slot, p.position)
                for p in planned
            ],
        )

    def batch(self, batch_id: str) -> DbRow | None:
        with self._conn() as c:
            return c.execute("SELECT * FROM rating_batch WHERE batch_id=?", (batch_id,)).fetchone()

    def set_status(self, batch_id: str, status: str) -> None:
        if status not in ("open", "closed"):
            raise ValueError(status)
        with self._conn() as c:
            c.execute("UPDATE rating_batch SET status=? WHERE batch_id=?", (status, batch_id))

    def batches(self) -> list[dict]:
        """Every batch with its progress per rater and how many responses need a third rater."""
        with self._conn() as c:
            batches = c.execute("SELECT * FROM rating_batch ORDER BY created_at DESC").fetchall()
            rows = c.execute(
                "SELECT x.batch_id, x.rater_id, x.slot, x.response_id,"
                f" g.assignment_id IS NOT NULL AS done, {_SEEN} AS seen"
                " FROM rating_assignment x"
                " LEFT JOIN research_rating g ON g.assignment_id = x.assignment_id"
            ).fetchall()
        out = []
        for b in batches:
            mine = [r for r in rows if r["batch_id"] == b["batch_id"]]
            raters: dict[str, dict] = {}
            for r in mine:
                entry = raters.setdefault(
                    r["rater_id"], {"total": 0, "done": 0, "adjudication": 0, "voided": 0}
                )
                entry["total"] += 1
                entry["done"] += int(r["done"])
                entry["adjudication"] += int(r["slot"] == 3)
                # Owed, but the rater has seen the machine's result since: it
                # will never be rated blind.
                entry["voided"] += int(not r["done"] and r["seen"])
            out.append(
                {
                    "batch_id": b["batch_id"],
                    "name": b["name"],
                    "seed": b["seed"],
                    "status": b["status"],
                    "created_by": b["created_by"],
                    "created_at": b["created_at"],
                    "responses": len({r["response_id"] for r in mine}),
                    "assignments": len(mine),
                    "done": sum(int(r["done"]) for r in mine),
                    "voided": sum(int(not r["done"] and r["seen"]) for r in mine),
                    "raters": raters,
                    "needs_adjudication": len(self._to_adjudicate(b["batch_id"])),
                }
            )
        return out

    # ------------------------------------------------------------ raters

    def open_count(self, rater_id: str) -> int:
        """Sheets this rater still owes, blind, in batches still open."""
        with self._conn() as c:
            return c.execute(
                f"SELECT COUNT(*) FROM rating_assignment x{_OWED}", (rater_id,)
            ).fetchone()[0]

    def has_open(self, rater_id: str, response_id: str) -> bool:
        """Whether this rater still has to rate this response blind, in an open batch."""
        with self._conn() as c:
            row = c.execute(
                f"SELECT 1 FROM rating_assignment x{_OWED} AND x.response_id = ?",
                (rater_id, response_id),
            ).fetchone()
        return row is not None

    def blinded_responses(self, rater_id: str) -> set[str]:
        """Every response this rater still has to rate blind: kept out of their review queue."""
        with self._conn() as c:
            rows = c.execute(
                f"SELECT x.response_id FROM rating_assignment x{_OWED}", (rater_id,)
            ).fetchall()
        return {r["response_id"] for r in rows}

    def batch_responses(self, batch_id: str) -> set[str]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT response_id FROM rating_assignment WHERE batch_id=?", (batch_id,)
            ).fetchall()
        return {r["response_id"] for r in rows}

    # ------------------------------------------------------------ who has seen the machine

    def saw_machine(self, account_id: str, response_id: str, via: str) -> None:
        """Note that this person has had the machine's result for this response in view."""
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO machine_seen(account_id, response_id, first_seen, via)"
                " SELECT ?, response_id, ?, ? FROM response WHERE response_id = ?",
                (account_id, _now(), via, response_id),
            )

    def seen_by(self, response_ids: list[str]) -> dict[str, set[str]]:
        """Per response, everyone who has opened its machine result or decided a review on it."""
        wanted = set(response_ids)
        with self._conn() as c:
            rows = c.execute(
                "SELECT response_id, account_id FROM machine_seen"
                " UNION SELECT response_id, reviewer_id FROM review_action"
            ).fetchall()
        out: dict[str, set[str]] = {}
        for response_id, account_id in rows:
            if response_id in wanted:
                out.setdefault(response_id, set()).add(account_id)
        return out

    def rater_list(self, rater_id: str) -> list[dict]:
        """This rater's assignments, in their own order, without anything about the response."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT x.assignment_id, x.batch_id, x.position, x.opened_at, x.slot,"
                f" b.name, b.status, g.submitted_at, {_SEEN} AS seen"
                " FROM rating_assignment x"
                " JOIN rating_batch b ON b.batch_id = x.batch_id"
                " LEFT JOIN research_rating g ON g.assignment_id = x.assignment_id"
                " WHERE x.rater_id = ? ORDER BY b.created_at DESC, x.position",
                (rater_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def rater_view(self, assignment_id: str) -> dict | None:
        """One assignment as its rater may see it, plus the private fields the API needs.

        `response_id` and `audio_path` come back for the server's own use (the
        task prompt, the audio stream); the API must not pass them on.
        """
        with self._conn() as c:
            row = c.execute(
                "SELECT x.assignment_id, x.batch_id, x.rater_id, x.slot, x.position, x.opened_at,"
                f" x.response_id, b.name, b.status, r.task_id, r.audio_path, {_SEEN} AS seen,"
                " (SELECT COUNT(*) FROM rating_assignment y"
                "  WHERE y.batch_id = x.batch_id AND y.rater_id = x.rater_id) AS total"
                " FROM rating_assignment x"
                " JOIN rating_batch b ON b.batch_id = x.batch_id"
                " JOIN response r ON r.response_id = x.response_id"
                " WHERE x.assignment_id = ?",
                (assignment_id,),
            ).fetchone()
            if row is None:
                return None
            rating = c.execute(
                "SELECT * FROM research_rating WHERE assignment_id=?", (assignment_id,)
            ).fetchone()
            following = c.execute(
                "SELECT x.assignment_id FROM rating_assignment x"
                " WHERE x.batch_id = ? AND x.rater_id = ? AND NOT EXISTS"
                " (SELECT 1 FROM research_rating g WHERE g.assignment_id = x.assignment_id)"
                f" AND NOT {_SEEN}"
                " AND x.assignment_id <> ? ORDER BY x.position LIMIT 1",
                (row["batch_id"], row["rater_id"], assignment_id),
            ).fetchone()
        out = dict(row)
        out["rating"] = dict(rating) if rating else None
        out["next_assignment_id"] = following["assignment_id"] if following else None
        return out

    def mark_opened(self, assignment_id: str) -> None:
        """The first time the rater opens it, for the time-to-rate the report states."""
        with self._conn() as c:
            c.execute(
                "UPDATE rating_assignment SET opened_at=?"
                " WHERE assignment_id=? AND opened_at IS NULL",
                (_now(), assignment_id),
            )

    def submit(
        self, assignment_id: str, rating: Rating, reason: str | None, unscorable_reason: str | None
    ) -> None:
        """Record a rating. Final: a second submission raises AlreadyRated.

        A rater who has seen the machine's result for the response since the
        sheet was given (SeenMachine) can no longer rate it blind.
        """
        scores = {f"score_{k}": rating.criteria.get(k) for k in CRITERIA}
        try:
            with self._conn() as c:
                seen = c.execute(
                    f"SELECT {_SEEN} FROM rating_assignment x WHERE x.assignment_id = ?",
                    (assignment_id,),
                ).fetchone()
                if seen is not None and seen[0]:
                    raise SeenMachine(assignment_id)
                c.execute(
                    "INSERT INTO research_rating(assignment_id, score_range, score_accuracy,"
                    " score_fluency, score_coherence, score_phonology, score_overall, band,"
                    " unscorable, unscorable_reason, reason, submitted_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        assignment_id,
                        scores["score_range"],
                        scores["score_accuracy"],
                        scores["score_fluency"],
                        scores["score_coherence"],
                        scores["score_phonology"],
                        rating.overall,
                        rating.band,
                        int(rating.unscorable),
                        unscorable_reason,
                        reason,
                        _now(),
                    ),
                )
        except IntegrityError as e:
            raise AlreadyRated(assignment_id) from e

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
        with self._conn() as c:
            start = c.execute(
                "SELECT COALESCE(MAX(position), 0) FROM rating_assignment"
                " WHERE batch_id=? AND rater_id=?",
                (batch_id, adjudicator_id),
            ).fetchone()[0]
            self._insert(c, batch_id, assign.adjudication(usable, adjudicator_id, seed, start))
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
        with self._conn() as c:
            void = c.execute(
                "SELECT x.response_id, x.slot, x.assignment_id FROM rating_assignment x"
                " WHERE x.batch_id = ? AND NOT EXISTS"
                " (SELECT 1 FROM research_rating g WHERE g.assignment_id = x.assignment_id)"
                f" AND {_SEEN} ORDER BY x.response_id, x.slot",
                (batch_id,),
            ).fetchall()
            taken = {
                r["response_id"]
                for r in c.execute(
                    "SELECT response_id FROM rating_assignment WHERE batch_id=? AND rater_id=?",
                    (batch_id, rater_id),
                )
            }
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
        with self._conn() as c:
            start = c.execute(
                "SELECT COALESCE(MAX(position), 0) FROM rating_assignment"
                " WHERE batch_id=? AND rater_id=?",
                (batch_id, rater_id),
            ).fetchone()[0]
            c.executemany(
                "DELETE FROM rating_assignment WHERE assignment_id=?",
                [(v["assignment_id"],) for v in moved],
            )
            planned = assign.reassignment(
                [(v["response_id"], v["slot"]) for v in moved], rater_id, seed, start
            )
            self._insert(c, batch_id, planned)
        return {"created": len(moved), "skipped_own": own, "skipped_seen": blocked}

    # ------------------------------------------------------------ analysis

    def _ratings_by_response(self, batch_id: str, allowed: set[str] | None = None) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT x.response_id, x.rater_id, x.slot, x.opened_at, g.*,"
                " r.speaker_id, r.account_id, r.task_id, " + _MACHINE + " FROM rating_assignment x"
                " JOIN response r ON r.response_id = x.response_id"
                " LEFT JOIN research_rating g ON g.assignment_id = x.assignment_id"
                " WHERE x.batch_id = ? ORDER BY x.response_id, x.slot",
                (batch_id,),
            ).fetchall()
        items: dict[str, dict] = {}
        for r in rows:
            if allowed is not None and r["account_id"] not in allowed:
                continue
            item = items.setdefault(
                r["response_id"],
                {
                    "response_id": r["response_id"],
                    "speaker_id": r["speaker_id"],
                    "task_id": r["task_id"],
                    "ai_overall": r["ai_overall"],
                    "ai_band": r["ai_band"],
                    "flagged": bool(r["flagged"]),
                    "assigned": set(),
                    "raters": [],
                    "slots": {},
                    "rows": [],
                },
            )
            item["assigned"].add(r["slot"])
            item["raters"].append(r["rater_id"])
            if r["submitted_at"] is not None:
                item["slots"][r["slot"]] = _rating(r)
                item["rows"].append(dict(r))
        return list(items.values())

    def analysis_rows(self, batch_id: str, allowed: set[str]) -> list[dict]:
        """Every response of the batch whose owner still consents, with all its ratings.

        For administrators: holds the speaker pseudonym (the bootstrap resamples
        speakers) and the machine's own score next to the human ones.
        """
        return self._ratings_by_response(batch_id, allowed)

    def all_times_to_rate(self) -> list[float]:
        """Seconds from opening to submission, every batch: rating without the machine (D041)."""
        with self._conn() as c:
            batches = [r["batch_id"] for r in c.execute("SELECT batch_id FROM rating_batch")]
        return [s for b in batches for s in self.times_to_rate(b)]

    def times_to_rate(self, batch_id: str) -> list[float]:
        """Seconds from first opening to submission, per submitted rating."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT x.opened_at, g.submitted_at FROM rating_assignment x"
                " JOIN research_rating g ON g.assignment_id = x.assignment_id"
                " WHERE x.batch_id = ? AND x.opened_at IS NOT NULL",
                (batch_id,),
            ).fetchall()
        out = []
        for r in rows:
            seconds = (
                datetime.fromisoformat(r["submitted_at"]) - datetime.fromisoformat(r["opened_at"])
            ).total_seconds()
            out.append(max(0.0, seconds))
        return out


def _rating(row: DbRow) -> Rating:
    unscorable = bool(row["unscorable"])
    return Rating(
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
