"""The ledger of the metered channel (D049): holds, charges, releases, balances.

Two collections (D060), as the class diagram has them:

* `wallet` -- one document per account (`Wallet`): what it has paid for in
  advance (on the NetID channel, what NetID reports as prepaid IDPoint), the
  free runs used in the current monthly cycle, and every top-up (`grants`),
  each kept once per (source, reference) so a payment notification replayed
  never credits twice;
* `ledger` -- one `LedgerEntry` per (response, purpose): what was held when the
  recording came in, what was charged when it had a result, or that it was
  released. Unique on (key, action), so a retried submission or a duplicated
  event never charges twice. Entries grow with every recording, so they are
  documents of their own, pointing at the wallet by its owner.

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

from aicefr.contracts import TaskPurpose
from aicefr.metering.pricing import FREE_UNITS_PER_CYCLE, PRICE_VERSION, TokenUsage
from aicefr.storage.db import IntegrityError, MongoStore
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current


class MeteredAction(str, Enum):
    """What a ledger entry paid for: a recording of either purpose, or (D072) an
    upgraded answer. The first two carry the values of `TaskPurpose`, so the
    entries written before D072 read back unchanged."""

    ASSESSMENT = "assessment"
    PRACTICE = "practice"
    UPGRADE = "upgrade"


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
    held: int
    from_free: int
    from_wallet: int
    charged: int
    state: LedgerState
    period: str
    price_version: str
    created_at: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    usage_estimated: bool | None = None
    settled_at: str | None = None

    @classmethod
    def from_doc(cls, doc: dict) -> LedgerEntry:
        known = cls.__dataclass_fields__
        found = {k: v for k, v in doc.items() if k in known}
        found["action"] = MeteredAction(doc["action"])
        found["state"] = LedgerState(doc["state"])
        return cls(**found)

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

    @classmethod
    def from_doc(cls, doc: dict) -> Wallet:
        return cls(
            user_ref=doc["user_ref"],
            balance=int(doc.get("balance", 0)),
            period=doc.get("period", ""),
            free_used=int(doc.get("free_used", 0)),
            grants=list(doc.get("grants", [])),
        )

    def available(self, free_units: int, period: str) -> int:
        """What can be spent now: the free runs left in `period`, then the balance."""
        used = self.free_used if self.period == period else 0
        return max(0, free_units - used) + self.balance


def _entry(row: dict | None) -> dict | None:
    return LedgerEntry.from_doc(row).to_doc() if row else None


class InsufficientCredits(Exception):
    """Neither the free runs left nor the wallet cover what the action needs."""

    def __init__(self, needed: int, available: int) -> None:
        super().__init__(f"needed {needed} units, {available} available")
        self.needed = needed
        self.available = available


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
        self.free_units = free_units
        ensure_current(self.db_path)

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

    def free_left(self, user_ref: str, period: str | None = None) -> int:
        w = self._wallet(user_ref)
        used = w.free_used if w.period == (period or cycle()) else 0
        return max(0, self.free_units - used)

    def balance(self, user_ref: str) -> dict:
        return {"wallet": self.wallet(user_ref), "free_left": self.free_left(user_ref)}

    def available(self, user_ref: str) -> int:
        return self._wallet(user_ref).available(self.free_units, cycle())

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

    def entry(self, key: str, action: TaskPurpose | MeteredAction) -> dict | None:
        return _entry(self.col("ledger").find_one({"key": key, "action": action.value}))

    def hold(
        self,
        user_ref: str,
        action: TaskPurpose | MeteredAction,
        key: str,
        units: int,
        version: str = PRICE_VERSION,
    ) -> dict:
        """Hold `units` for `key`: free runs first, then the wallet.

        Idempotent: holding a key held before returns the existing entry and
        takes nothing. Raises InsufficientCredits, holding nothing, when the
        two together fall short.
        """
        existing = self.entry(key, action)
        if existing is not None:
            return existing
        period = cycle()
        free = self._take_free(user_ref, period, units)
        rest = units - free
        if rest:
            paid = self.col("wallet").update_one(
                {"user_ref": user_ref, "balance": {"$gte": rest}}, {"$inc": {"balance": -rest}}
            )
            if not paid.modified_count:
                self._give_back(user_ref, period, free, 0)
                raise InsufficientCredits(units, self.available(user_ref))
        entry = LedgerEntry(
            entry_id=uuid.uuid4().hex[:16],
            user_ref=user_ref,
            action=MeteredAction(action.value),
            key=key,
            held=units,
            from_free=free,
            from_wallet=rest,
            charged=0,
            state=LedgerState.HELD,
            period=period,
            price_version=version,
            created_at=_now(),
        )
        try:
            self.col("ledger").insert_one(entry.to_doc())
        except IntegrityError:
            # The same key held by a concurrent request: give back what this one took.
            self._give_back(user_ref, period, free, rest)
            return self.entry(key, action)  # type: ignore[return-value]
        return entry.to_doc()

    def settle(
        self,
        key: str,
        action: TaskPurpose | MeteredAction,
        result: bool,
        charge: int | None = None,
        usage: TokenUsage | None = None,
    ) -> dict | None:
        """Charge a held entry when the person got a result, release it otherwise.

        `charge` is what the recording really cost (the whole hold when not
        given), never more than was held; the rest goes back, to the wallet
        first. `usage`, the tokens behind the charge, is kept with the entry.
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
        tokens = (
            {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
             "usage_estimated": usage.estimated}
            if result and usage is not None else {}
        )  # fmt: skip
        to = LedgerState.CHARGED if result else LedgerState.RELEASED
        moved = self.col("ledger").find_one_and_update(
            {"key": key, "action": action.value, "state": LedgerState.HELD.value},
            {"$set": {"state": to.value, "charged": charged, "settled_at": _now(), **tokens}},
            return_document=ReturnDocument.AFTER,
        )
        if moved is None:
            return self.entry(key, action)  # settled by another event a moment ago
        refund = current["held"] - charged
        to_wallet = min(refund, current["from_wallet"])
        self._give_back(current["user_ref"], current["period"], refund - to_wallet, to_wallet)
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
