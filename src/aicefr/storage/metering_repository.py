"""The ledger of the metered channel (D049): holds, charges, releases, balances.

Three collections (D060, D078), as the class diagram has them:

* `wallet` -- one document per account (`Wallet`): what it has paid for in
  advance (on the NetID channel, what NetID reports as prepaid IDPoint), the
  free runs used in the current monthly cycle, the lesson recordings of the
  current Vietnam day (D094: how many were measured, how many of them free),
  and every top-up (`grants`), each kept once per (source, reference) so a
  payment notification replayed never credits twice;
* `ledger` -- one `LedgerEntry` per (response, purpose): what was held when the
  recording came in, what was charged when it had a result, or that it was
  released. Unique on (key, action), so a retried submission or a duplicated
  event never charges twice. Entries grow with every recording, so they are
  documents of their own, pointing at the wallet by its owner;
* `price_list` -- one document, the prices an administrator set on the
  dashboard (D078): what a recording, a practice attempt and an upgraded
  answer cost, the free runs each month and the run packs on sale, with every
  earlier version and who set it. Absent until the first change: the settings
  (`AICEFR_PRICE_*`) stand until then.

No multi-document transactions (D048): every step that must not race is one
conditional update of one document. A top-up records itself and raises the
balance in the same update; a hold takes from the free runs and the balance
before its ledger entry is written, giving back what it took when the entry
turns out to exist already. Entries hold no recording, transcript or name: an
account id, a purpose, units and times.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pymongo import DESCENDING, ReturnDocument

from aicefr.metering.pricing import FREE_UNITS_PER_CYCLE, UNITS_PER_RUN
from aicefr.storage.db import IntegrityError, MongoStore
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current


class MeteredAction(str, Enum):
    """What a ledger entry paid for: a recording, (D072) an upgraded answer,
    (D075) a teacher's lesson draft, (D090) a reading passage, or (D094) a
    recording on the lesson path. PRACTICE is a recording of a practice task
    (D023): none is made since D083, the entries made before keep it."""

    ASSESSMENT = "assessment"
    PRACTICE = "practice"
    UPGRADE = "upgrade"
    LESSON_DRAFT = "lesson_draft"
    DRILL_PASSAGE = "drill_passage"
    LESSON = "lesson"


class LedgerState(str, Enum):
    """Where a ledger entry is: held at submission, then charged or released, once."""

    HELD = "held"
    CHARGED = "charged"
    RELEASED = "released"


@dataclass
class LedgerEntry:
    """What one recording held, and what it was charged or given back."""

    entry_id: str
    user_ref: str  # the wallet's owner
    action: MeteredAction
    key: str  # the response; "upgrade-<response id>" for an upgraded answer
    from_free: int
    from_wallet: int
    charged: int
    state: LedgerState
    period: str
    created_at: str
    settled_at: str | None = None
    # D094, a lesson recording: the Vietnam day whose count it took, and
    # whether it was one of that day's free recordings.
    day: str | None = None
    free_slot: bool | None = None

    @classmethod
    def from_doc(cls, doc: dict) -> LedgerEntry:
        known = cls.__dataclass_fields__
        found = {k: v for k, v in doc.items() if k in known}
        found["action"] = MeteredAction(doc["action"])
        found["state"] = LedgerState(doc["state"])
        return cls(**found)

    @property
    def held(self) -> int:
        """What was held: the free runs and the wallet runs taken together (D103)."""
        return self.from_free + self.from_wallet

    def to_doc(self) -> dict:
        return {**asdict(self), "action": self.action.value, "state": self.state.value}


@dataclass
class Wallet:
    """One account's runs: prepaid balance, this cycle's free runs used, top-ups."""

    user_ref: str  # the owner
    balance: int = 0
    period: str = ""  # the cycle `free_used` counts in
    free_used: int = 0
    grants: list[dict] = field(default_factory=list)
    # D094: the lesson recordings of `lesson_day`, and how many were free.
    lesson_day: str = ""
    lesson_used: int = 0
    lesson_free_used: int = 0

    @classmethod
    def from_doc(cls, doc: dict) -> Wallet:
        return cls(
            user_ref=doc["user_ref"],
            balance=int(doc.get("balance", 0)),
            period=doc.get("period", ""),
            free_used=int(doc.get("free_used", 0)),
            grants=list(doc.get("grants", [])),
            lesson_day=doc.get("lesson_day", ""),
            lesson_used=int(doc.get("lesson_used", 0)),
            lesson_free_used=int(doc.get("lesson_free_used", 0)),
        )

    def available(self, free_units: int, period: str) -> int:
        """What can be spent now: the free runs left in `period`, then the balance."""
        used = self.free_used if self.period == period else 0
        return max(0, free_units - used) + self.balance


def _entry(row: dict | None) -> dict | None:
    if not row:
        return None
    entry = LedgerEntry.from_doc(row)
    return {**entry.to_doc(), "held": entry.held}


class InsufficientCredits(Exception):
    """Neither the free runs left nor the wallet cover what the action needs."""

    def __init__(self, needed: int, available: int) -> None:
        super().__init__(f"needed {needed} units, {available} available")
        self.needed = needed
        self.available = available


class DailyCapReached(Exception):
    """D094: the lesson recordings of this day reached the cap."""

    def __init__(self, cap: int) -> None:
        super().__init__(f"{cap} lesson recordings today")
        self.cap = cap


def cycle(now: datetime | None = None) -> str:
    """The monthly cycle `now` falls in, named by the month it starts in.

    Cycles start on the 16th, as NetID's accounts renew (`Chu kỳ sử dụng`), so
    the free runs come back on the same day the user's NetID month does.
    """
    now = now or datetime.now(UTC)
    year, month = now.year, now.month
    if now.day < 16:
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return f"{year:04d}-{month:02d}"


class MeteringRepository(MongoStore):
    def __init__(self, db_path: str | Path, free_units: int = FREE_UNITS_PER_CYCLE) -> None:
        self.db_path = str(db_path)
        self._free_units = free_units
        ensure_current(self.db_path)

    # ------------------------------------------------------------ prices (D078)

    def price_list(self) -> dict | None:
        """The prices an administrator set, or None while the settings stand."""
        return self.col("price_list").find_one({"_id": "current"}, {"_id": 0})

    def price_history(self, limit: int = 10) -> list[dict]:
        """The versions before the one in force, newest first, from the audit log (D105).

        Each change of the prices is audited (`metering.prices`, its version as
        the detail): that is the history, so the price list keeps no copy.
        """
        current = (self.price_list() or {}).get("version")
        rows = (
            self.col("audit_log")
            .find({"service": "metering", "action": "metering.prices"})
            .sort("id", DESCENDING)
            .limit(limit + 1)
        )
        return [
            {"version": r["detail"], "changed_at": r["created_at"]}
            for r in rows
            if r.get("detail") != current
        ][:limit]

    def set_price_list(self, values: dict) -> dict:
        """A new version of the prices, numbered on from the one in force."""
        before = self.price_list()
        number = int(str((before or {}).get("version", "0")).rsplit("-", 1)[-1] or 0) + 1
        doc = {**values, "version": f"price-admin-{number}", "changed_at": _now()}
        self.col("price_list").replace_one({"_id": "current"}, doc, upsert=True)
        return doc

    @property
    def free_units(self) -> int:
        """Free runs each month, in thousandths: the administrator's, else the setting."""
        doc = self.price_list()
        if doc and doc.get("free_runs") is not None:
            return int(round(float(doc["free_runs"]) * UNITS_PER_RUN))
        return self._free_units

    def _wallet(self, user_ref: str) -> Wallet:
        row = self.col("wallet").find_one({"user_ref": user_ref})
        return Wallet.from_doc(row) if row else Wallet(user_ref=user_ref)

    def _ensure_wallet(self, user_ref: str) -> None:
        try:
            self.col("wallet").update_one(
                {"user_ref": user_ref},
                {"$setOnInsert": {"balance": 0, "period": "", "free_used": 0, "grants": []}},
                upsert=True,
            )
        except IntegrityError:
            pass  # made a moment ago by another request

    # ------------------------------------------------------------ balances

    def wallet(self, user_ref: str) -> int:
        return self._wallet(user_ref).balance

    def free_left(self, user_ref: str, period: str | None = None, free: bool = True) -> int:
        """The free units left in `period`; none for an account not allowed them (D101)."""
        if not free:
            return 0
        w = self._wallet(user_ref)
        used = w.free_used if w.period == (period or cycle()) else 0
        return max(0, self.free_units - used)

    def balance(self, user_ref: str, free: bool = True) -> dict:
        return {"wallet": self.wallet(user_ref), "free_left": self.free_left(user_ref, free=free)}

    def available(self, user_ref: str, free: bool = True) -> int:
        return self._wallet(user_ref).available(self.free_units if free else 0, cycle())

    # ------------------------------------------------------------ top-ups

    def grant(self, user_ref: str, units: int, source: str, ref: str, by: str | None) -> bool:
        """Credit `units` once per (source, ref); False when this top-up was credited before.

        One update records the top-up and raises the balance, and only where
        no top-up of that (source, ref) is recorded yet.
        """
        if units <= 0:
            raise ValueError("số lượt cộng phải dương")
        self._ensure_wallet(user_ref)
        top_up = {
            "grant_id": uuid.uuid4().hex[:16],
            "units": units,
            "source": source,
            "ref": ref,
            "by": by,
            "created_at": _now(),
        }
        done = self.col("wallet").update_one(
            {
                "user_ref": user_ref,
                "grants": {"$not": {"$elemMatch": {"source": source, "ref": ref}}},
            },
            {"$push": {"grants": top_up}, "$inc": {"balance": units}},
        )
        return bool(done.modified_count)

    def _add_to_wallet(self, user_ref: str, units: int) -> None:
        if units:
            self._ensure_wallet(user_ref)
            self.col("wallet").update_one({"user_ref": user_ref}, {"$inc": {"balance": units}})

    # ------------------------------------------------------------ hold, charge, release

    def _take_free(self, user_ref: str, period: str, wanted: int) -> int:
        """Take up to `wanted` free units of this cycle, atomically; what was taken."""
        wallets = self.col("wallet")
        self._ensure_wallet(user_ref)
        # A new cycle starts from nothing used.
        wallets.update_one(
            {"user_ref": user_ref, "period": {"$ne": period}},
            {"$set": {"period": period, "free_used": 0}},
        )
        for _ in range(8):
            w = self._wallet(user_ref)
            take = min(wanted, self.free_units - w.free_used)
            if take <= 0:
                return 0
            # Compare-and-set on the count read: two holds at once never both
            # take the last free run.
            done = wallets.update_one(
                {"user_ref": user_ref, "period": period, "free_used": w.free_used},
                {"$inc": {"free_used": take}},
            )
            if done.modified_count:
                return take
        return 0

    def _give_back(self, user_ref: str, period: str, free: int, wallet: int) -> None:
        if free:
            # Only into the cycle it came from: a new cycle starts afresh anyway.
            self.col("wallet").update_one(
                {"user_ref": user_ref, "period": period}, {"$inc": {"free_used": -free}}
            )
        self._add_to_wallet(user_ref, wallet)

    def entry(self, key: str, action: MeteredAction) -> dict | None:
        return _entry(self.col("ledger").find_one({"key": key, "action": action.value}))

    def _take(
        self, user_ref: str, period: str, units: int, free_ok: bool = True
    ) -> tuple[int, int]:
        """Take `units`: free runs of `period` first, then the wallet; (free, wallet).

        Without `free_ok` (D101: an email not yet verified) only the wallet pays.
        Raises InsufficientCredits, taking nothing, when the two fall short.
        """
        free = self._take_free(user_ref, period, units) if free_ok else 0
        rest = units - free
        if rest:
            paid = self.col("wallet").update_one(
                {"user_ref": user_ref, "balance": {"$gte": rest}}, {"$inc": {"balance": -rest}}
            )
            if not paid.modified_count:
                self._give_back(user_ref, period, free, 0)
                raise InsufficientCredits(units, self.available(user_ref, free_ok))
        return free, rest

    def hold(
        self,
        user_ref: str,
        action: MeteredAction,
        key: str,
        units: int,
        free_ok: bool = True,
    ) -> dict:
        """Hold `units` for `key`: free runs first (when `free_ok`), then the wallet.

        Idempotent: holding a key held before returns the existing entry and
        takes nothing. Raises InsufficientCredits, holding nothing, when the
        two together fall short.
        """
        existing = self.entry(key, action)
        if existing is not None:
            return existing
        period = cycle()
        free, rest = self._take(user_ref, period, units, free_ok)
        entry = LedgerEntry(
            entry_id=uuid.uuid4().hex[:16],
            user_ref=user_ref,
            action=MeteredAction(action.value),
            key=key,
            from_free=free,
            from_wallet=rest,
            charged=0,
            state=LedgerState.HELD,
            period=period,
            created_at=_now(),
        )
        try:
            self.col("ledger").insert_one(entry.to_doc())
        except IntegrityError:
            # The same key held by a concurrent request: give back what this one took.
            self._give_back(user_ref, period, free, rest)
            return self.entry(key, action)  # type: ignore[return-value]
        return _entry(entry.to_doc())

    # ------------------------------------------------------------ lesson recordings (D094)

    def lesson_today(self, user_ref: str, day: str) -> dict:
        """The lesson recordings of `day` so far: measured, and free among them."""
        w = self._wallet(user_ref)
        if w.lesson_day != day:
            return {"used": 0, "free_used": 0}
        return {"used": w.lesson_used, "free_used": w.lesson_free_used}

    def _take_lesson_slot(self, user_ref: str, day: str, cap: int) -> str:
        """Count one more lesson recording of `day`, or raise DailyCapReached.

        One conditional update moves the count up only while it is under the
        cap, so two recordings at once never both take the last place (and
        `_take_free_lesson` does the same for the free ones). Returns the day
        counted in: `day`, unless another request already moved the wallet on
        to the next one.
        """
        wallets = self.col("wallet")
        self._ensure_wallet(user_ref)
        # A new day starts from nothing. Only forward: a request computed a
        # moment before midnight never takes the wallet back a day.
        wallets.update_one(
            {
                "user_ref": user_ref,
                "$or": [{"lesson_day": {"$exists": False}}, {"lesson_day": {"$lt": day}}],
            },
            {"$set": {"lesson_day": day, "lesson_used": 0, "lesson_free_used": 0}},
        )
        for _ in range(3):
            day = max(day, self._wallet(user_ref).lesson_day)
            counted = wallets.update_one(
                {"user_ref": user_ref, "lesson_day": day, "lesson_used": {"$lt": cap}},
                {"$inc": {"lesson_used": 1}},
            )
            if counted.modified_count:
                return day
            if self._wallet(user_ref).lesson_day == day:
                raise DailyCapReached(cap)
        raise DailyCapReached(cap)

    def _take_free_lesson(self, user_ref: str, day: str, free_per_day: int) -> bool:
        took = self.col("wallet").update_one(
            {"user_ref": user_ref, "lesson_day": day, "lesson_free_used": {"$lt": free_per_day}},
            {"$inc": {"lesson_free_used": 1}},
        )
        return bool(took.modified_count)

    def _give_back_slot(self, user_ref: str, day: str, free_slot: bool) -> None:
        """Uncount a lesson recording of `day` that got no result; a later day is left alone."""
        give: dict = {"lesson_used": -1}
        where: dict = {"user_ref": user_ref, "lesson_day": day, "lesson_used": {"$gt": 0}}
        if free_slot:
            give["lesson_free_used"] = -1
            where["lesson_free_used"] = {"$gt": 0}
        self.col("wallet").update_one(where, {"$inc": give})

    def hold_lesson(
        self,
        user_ref: str,
        key: str,
        units: int,
        day: str,
        free_per_day: int,
        cap: int,
        free_ok: bool = True,
    ) -> dict:
        """Hold one lesson recording (D094): a place among the day's `cap`, then its price.

        The first `free_per_day` recordings of a day hold nothing; the others
        hold `units`, free runs of the month first, then the wallet. Raises
        DailyCapReached when the day is full, InsufficientCredits when the
        runs fall short; either way nothing is counted or taken. Idempotent on
        `key`, as `hold` is.
        """
        existing = self.entry(key, MeteredAction.LESSON)
        if existing is not None:
            return existing
        day = self._take_lesson_slot(user_ref, day, cap)
        # D101: no free recording of the day, nor free run of the month, for
        # an account whose email is not verified yet.
        free_slot = free_ok and self._take_free_lesson(user_ref, day, free_per_day)
        units = 0 if free_slot else units
        period = cycle()
        try:
            free, rest = self._take(user_ref, period, units, free_ok)
        except InsufficientCredits:
            self._give_back_slot(user_ref, day, free_slot)
            raise
        entry = LedgerEntry(
            entry_id=uuid.uuid4().hex[:16],
            user_ref=user_ref,
            action=MeteredAction.LESSON,
            key=key,
            from_free=free,
            from_wallet=rest,
            charged=0,
            state=LedgerState.HELD,
            period=period,
            created_at=_now(),
            day=day,
            free_slot=free_slot,
        )
        try:
            self.col("ledger").insert_one(entry.to_doc())
        except IntegrityError:
            self._give_back(user_ref, period, free, rest)
            self._give_back_slot(user_ref, day, free_slot)
            return self.entry(key, MeteredAction.LESSON)  # type: ignore[return-value]
        return _entry(entry.to_doc())

    def settle(
        self,
        key: str,
        action: MeteredAction,
        result: bool,
        charge: int | None = None,
    ) -> dict | None:
        """Charge a held entry when the person got a result, release it otherwise.

        `charge` is what the recording really cost (the whole hold when not
        given), never more than was held; the rest goes back, to the wallet
        first.
        Settling twice changes nothing: the state moves from `held` once, by
        one conditional update.
        """
        current = self.entry(key, action)
        if current is None:
            return None
        if current["state"] != LedgerState.HELD.value:
            return current
        charged = (
            min(current["held"] if charge is None else charge, current["held"]) if result else 0
        )
        to = LedgerState.CHARGED if result else LedgerState.RELEASED
        moved = self.col("ledger").find_one_and_update(
            {"key": key, "action": action.value, "state": LedgerState.HELD.value},
            {"$set": {"state": to.value, "charged": charged, "settled_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )
        if moved is None:
            return self.entry(key, action)  # settled by another event a moment ago
        refund = current["held"] - charged
        to_wallet = min(refund, current["from_wallet"])
        self._give_back(current["user_ref"], current["period"], refund - to_wallet, to_wallet)
        if not result and current.get("day"):
            # D094: a lesson recording with no result gives its place of the day back.
            self._give_back_slot(current["user_ref"], current["day"], bool(current["free_slot"]))
        return _entry(moved)

    def release_stale(self, cutoff: str) -> list[str]:
        """Release every hold older than `cutoff`: its result will never come."""
        stale = self.col("ledger").find(
            {"state": LedgerState.HELD.value, "created_at": {"$lte": cutoff}},
            {"key": 1, "action": 1},
        )
        released = []
        for row in list(stale):
            done = self.settle(row["key"], MeteredAction(row["action"]), result=False)
            if done and done["state"] == LedgerState.RELEASED.value:
                released.append(row["key"])
        return released

    def history(self, user_ref: str, limit: int = 50) -> list[dict]:
        rows = (
            self.col("ledger")
            .find({"user_ref": user_ref})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [_entry(r) for r in rows]  # type: ignore[misc]

    def totals(self, since: str, until: str) -> dict[str, int]:
        """Units charged per purpose in [since, until): the statement to reconcile."""
        out: dict[str, int] = {}
        rows = self.col("ledger").find(
            {"state": LedgerState.CHARGED.value, "settled_at": {"$gte": since, "$lt": until}},
            {"action": 1, "charged": 1},
        )
        for r in rows:
            out[r["action"]] = out.get(r["action"], 0) + int(r["charged"])
        return out
