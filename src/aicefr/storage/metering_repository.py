"""The ledger of the metered channel (D049): holds, charges, releases, balances.

Four collections:

* `usage_ledger` -- one entry per (response, action): what was held when the
  recording came in, what was charged when it had a result, or that it was
  released. Unique on (key, action), so a retried submission or a duplicated
  event never charges twice;
* `credit_wallet` -- what each account has paid for in advance (on the NetID
  channel: what NetID reports as prepaid IDPoint);
* `free_quota` -- the free runs each account used in each monthly cycle;
* `credit_grant` -- every top-up, unique on (source, reference), so a payment
  notification replayed never credits twice.

No multi-document transactions (D048): every step that must not race is one
conditional update of one document, and a hold takes from the free quota and
the wallet before its ledger entry is written, giving back what it took when
the entry turns out to exist already. Entries hold no recording, transcript
or name: an account id, an action, units and times.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from pymongo import DESCENDING, ReturnDocument

from aicefr.metering.pricing import FREE_UNITS_PER_CYCLE, PRICE_VERSION, Action, TokenUsage
from aicefr.storage.db import IntegrityError, MongoStore, fields
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

HELD, CHARGED, RELEASED = "held", "charged", "released"
ENTRY_FIELDS = (
    "entry_id",
    "user_ref",
    "action",
    "key",
    "held",
    "from_free",
    "from_wallet",
    "charged",
    "state",
    "period",
    "price_version",
    "input_tokens",
    "output_tokens",
    "usage_estimated",
    "created_at",
    "settled_at",
)


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

    # ------------------------------------------------------------ balances

    def wallet(self, user_ref: str) -> int:
        row = self.col("credit_wallet").find_one({"user_ref": user_ref})
        return int(row["balance"]) if row else 0

    def free_left(self, user_ref: str, period: str | None = None) -> int:
        row = self.col("free_quota").find_one({"user_ref": user_ref, "period": period or cycle()})
        return max(0, self.free_units - (int(row["used"]) if row else 0))

    def balance(self, user_ref: str) -> dict:
        return {"wallet": self.wallet(user_ref), "free_left": self.free_left(user_ref)}

    # ------------------------------------------------------------ top-ups

    def grant(self, user_ref: str, units: int, source: str, ref: str, by: str | None) -> bool:
        """Credit `units` once per (source, ref); False when this top-up was credited before."""
        if units <= 0:
            raise ValueError("số lượt cộng phải dương")
        try:
            self.col("credit_grant").insert_one(
                {
                    "grant_id": uuid.uuid4().hex[:16],
                    "user_ref": user_ref,
                    "units": units,
                    "source": source,
                    "ref": ref,
                    "by": by,
                    "created_at": _now(),
                }
            )
        except IntegrityError:
            return False
        self._add_to_wallet(user_ref, units)
        return True

    def _add_to_wallet(self, user_ref: str, units: int) -> None:
        if units:
            self.col("credit_wallet").update_one(
                {"user_ref": user_ref}, {"$inc": {"balance": units}}, upsert=True
            )

    # ------------------------------------------------------------ hold, charge, release

    def _take_free(self, user_ref: str, period: str, wanted: int) -> int:
        """Take up to `wanted` free units of this cycle, atomically; what was taken."""
        quotas = self.col("free_quota")
        try:
            quotas.update_one(
                {"user_ref": user_ref, "period": period},
                {"$setOnInsert": {"used": 0}},
                upsert=True,
            )
        except IntegrityError:
            pass  # made a moment ago by another request
        for _ in range(8):
            row = quotas.find_one({"user_ref": user_ref, "period": period})
            take = min(wanted, self.free_units - int(row["used"]))
            if take <= 0:
                return 0
            # Compare-and-set on the count read: two holds at once never both
            # take the last free run.
            done = quotas.update_one(
                {"user_ref": user_ref, "period": period, "used": row["used"]},
                {"$inc": {"used": take}},
            )
            if done.modified_count:
                return take
        return 0

    def _give_back(self, user_ref: str, period: str, free: int, wallet: int) -> None:
        if free:
            self.col("free_quota").update_one(
                {"user_ref": user_ref, "period": period}, {"$inc": {"used": -free}}
            )
        self._add_to_wallet(user_ref, wallet)

    def entry(self, key: str, action: Action) -> dict | None:
        return fields(
            self.col("usage_ledger").find_one({"key": key, "action": action.value}), ENTRY_FIELDS
        )

    def hold(
        self, user_ref: str, action: Action, key: str, units: int, version: str = PRICE_VERSION
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
            paid = self.col("credit_wallet").update_one(
                {"user_ref": user_ref, "balance": {"$gte": rest}}, {"$inc": {"balance": -rest}}
            )
            if not paid.modified_count:
                self._give_back(user_ref, period, free, 0)
                raise InsufficientCredits(units, self.free_left(user_ref) + self.wallet(user_ref))
        entry = {
            "entry_id": uuid.uuid4().hex[:16],
            "user_ref": user_ref,
            "action": action.value,
            "key": key,
            "held": units,
            "from_free": free,
            "from_wallet": rest,
            "charged": 0,
            "state": HELD,
            "period": period,
            "price_version": version,
            "input_tokens": None,
            "output_tokens": None,
            "usage_estimated": None,
            "created_at": _now(),
            "settled_at": None,
        }
        try:
            self.col("usage_ledger").insert_one(entry)
        except IntegrityError:
            # The same key held by a concurrent request: give back what this one took.
            self._give_back(user_ref, period, free, rest)
            return self.entry(key, action)  # type: ignore[return-value]
        return fields(entry, ENTRY_FIELDS)  # type: ignore[return-value]

    def settle(
        self,
        key: str,
        action: Action,
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
        if current["state"] != HELD:
            return current
        charged = (
            min(current["held"] if charge is None else charge, current["held"]) if result else 0
        )
        tokens = (
            {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
             "usage_estimated": usage.estimated}
            if result and usage is not None else {}
        )  # fmt: skip
        moved = self.col("usage_ledger").find_one_and_update(
            {"key": key, "action": action.value, "state": HELD},
            {"$set": {"state": CHARGED if result else RELEASED, "charged": charged,
                      "settled_at": _now(), **tokens}},
            return_document=ReturnDocument.AFTER,
        )  # fmt: skip
        if moved is None:
            return self.entry(key, action)  # settled by another event a moment ago
        refund = current["held"] - charged
        to_wallet = min(refund, current["from_wallet"])
        self._give_back(current["user_ref"], current["period"], refund - to_wallet, to_wallet)
        return fields(moved, ENTRY_FIELDS)

    def release_stale(self, cutoff: str) -> list[str]:
        """Release every hold older than `cutoff`: its result will never come."""
        stale = self.col("usage_ledger").find(
            {"state": HELD, "created_at": {"$lte": cutoff}}, {"key": 1, "action": 1}
        )
        released = []
        for row in list(stale):
            done = self.settle(row["key"], Action(row["action"]), result=False)
            if done and done["state"] == RELEASED:
                released.append(row["key"])
        return released

    def history(self, user_ref: str, limit: int = 50) -> list[dict]:
        rows = (
            self.col("usage_ledger")
            .find({"user_ref": user_ref})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [fields(r, ENTRY_FIELDS) for r in rows]  # type: ignore[misc]

    def totals(self, since: str, until: str) -> dict[str, int]:
        """Units charged per action in [since, until): the statement to reconcile."""
        out: dict[str, int] = {}
        rows = self.col("usage_ledger").find(
            {"state": CHARGED, "settled_at": {"$gte": since, "$lt": until}},
            {"action": 1, "charged": 1},
        )
        for r in rows:
            out[r["action"]] = out.get(r["action"], 0) + int(r["charged"])
        return out
