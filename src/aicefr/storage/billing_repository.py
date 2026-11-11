"""Storage of orders (D033, D060, D104): run packs bought through a gateway.

An order is what was bought -- the runs, the money, its status, the account
that placed it -- and how the gateway took the money: the checkout and
transaction numbers, and everything the gateway said about it as `events`.
D084 kept the gateway's part in a `payment` collection of its own, one per
order; D104 folds it back, since it was never read without its order. Nothing
about a person beyond the account is held: no card number, bank account or
payer name ever reaches this file (BR-32).

Marking an order paid is one conditional update, guarded by the order's
status: when the browser's return and the gateway's notification report the
same payment at once, exactly one of them settles it, and the same update
writes the result.

D075: one centre and no service plans. The `license` collection of D033 is
neither read nor written any more; what a deployment already holds there is
left as it was.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dc_fields
from pathlib import Path

from pymongo import DESCENDING

from aicefr.billing.order_state import sources
from aicefr.billing.payments import OrderStatus
from aicefr.storage.db import (
    MongoStore,
    ensure_indexes,
    ensure_system,
    get_setting,
    set_setting,
    setting_once,
)
from aicefr.storage.db import now_iso as _now

# order: runs of the pack, amount_vnd what was paid, checkout_ref the gateway's
# id for the checkout. Which gateway, and whether it moves real money, is the
# deployment's (D103): it runs one gateway. An event's fingerprint is its
# detail without "applied" (D035): repeats of an identical message are counted
# on the first.
INDEXES = {
    "order": [
        (("order_id",), True),
        (("created_at",), False),
        (("status", "expires_at"), False),
        (("created_by",), False),
        (("checkout_ref",), False),
    ],
}
SETTING = "billing."  # this part's keys in `system`
NO_EVENTS = {"events": 0}  # what a list of orders reads: everything but the gateway's messages


def _known(cls, doc: dict) -> dict:
    names = {f.name for f in dc_fields(cls)}
    return {k: v for k, v in doc.items() if k in names}


@dataclass
class Order:
    """One purchase: a pack of runs for the account that ordered it (D053, D075).

    The account is the buyer -- a learner, or a teacher for their lesson drafts
    -- and the runs go to that account's wallet once the payment is settled.
    """

    order_id: str
    runs: int
    amount_vnd: int
    status: OrderStatus
    created_by: str
    created_at: str
    expires_at: str | None = None
    credited_at: str | None = None
    checkout_ref: str | None = None  # the gateway's id for the checkout opened
    reference: str | None = None  # the gateway's transaction number
    settled_at: str | None = None
    events: list[dict] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Order:
        found = _known(cls, doc)
        found["runs"] = int(doc["runs"])
        found["status"] = OrderStatus(doc["status"])
        return cls(**found)

    def to_doc(self) -> dict:
        return {**asdict(self), "status": self.status.value}


def _view(order: dict | None) -> dict | None:
    """An order as the screens and the service read it: without its events."""
    if order is None:
        return None
    return {k: v for k, v in Order.from_doc(order).to_doc().items() if k != "events"}


class BillingRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "billing")
        ensure_system(self.db)

    # ------------------------------------------------------------ orders

    def create_order(self, order: dict) -> dict:
        made = Order.from_doc(order)
        self.col("order").insert_one(made.to_doc())
        return _view(made.to_doc())  # type: ignore[return-value]

    def set_checkout_ref(self, order_id: str, reference: str) -> None:
        self.col("order").update_one({"order_id": order_id}, {"$set": {"checkout_ref": reference}})

    def _views(self, rows: list[dict]) -> list[dict]:
        return [_view(r) for r in rows]  # type: ignore[misc]

    def order_by_checkout(self, reference: str) -> dict | None:
        """The order whose checkout the gateway knows by `reference` (a payOS payment link id)."""
        return _view(self.col("order").find_one({"checkout_ref": reference}, NO_EVENTS))

    def order(self, order_id: str) -> dict | None:
        return _view(self.col("order").find_one({"order_id": order_id}, NO_EVENTS))

    def orders_by(self, account_id: str, limit: int = 20) -> list[dict]:
        """One account's own run packs, newest first."""
        rows = list(
            self.col("order")
            .find({"created_by": account_id}, NO_EVENTS)
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return self._views(rows)

    def open_since(self, since: str) -> list[dict]:
        """Pending or expired orders created since `since`: the ones a gateway may still settle."""
        may_settle = [s.value for s in sources(OrderStatus.PAID)]
        rows = list(
            self.col("order").find(
                {"status": {"$in": may_settle}, "created_at": {"$gte": since}}, NO_EVENTS
            )
        )
        return self._views(rows)

    def pending_count(self, account_id: str, since: str) -> int:
        """How many orders this account opened since `since` that are still waiting (D099)."""
        return self.col("order").count_documents(
            {
                "created_by": account_id,
                "status": OrderStatus.PENDING.value,
                "created_at": {"$gte": since},
            }
        )

    def recent(self, limit: int = 200, status: str | None = None) -> list[dict]:
        """Every account's run packs, newest first: the administrator's order list (D099)."""
        query: dict = {}
        if status:
            query["status"] = status
        rows = list(
            self.col("order")
            .find(query, NO_EVENTS)
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return self._views(rows)

    def count_by_status(self) -> dict[str, int]:
        """How many run packs are in each status, all time (D099)."""
        rows = self.col("order").aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])
        return {r["_id"]: r["n"] for r in rows}

    def paid_since(self, since: str) -> list[dict]:
        """Paid run packs ordered since `since`: what the daily totals add up (D099)."""
        rows = list(
            self.col("order").find(
                {"status": OrderStatus.PAID.value, "created_at": {"$gte": since}}
            )
        )
        return self._views(rows)

    def uncredited(self) -> list[dict]:
        """Paid run packs whose runs have not reached the wallet yet (D053)."""
        rows = list(
            self.col("order").find(
                {"status": OrderStatus.PAID.value, "credited_at": None}, NO_EVENTS
            )
        )
        return self._views(rows)

    def mark_credited(self, order_id: str) -> bool:
        done = self.col("order").update_one(
            {"order_id": order_id, "credited_at": None}, {"$set": {"credited_at": _now()}}
        )
        return bool(done.modified_count)

    def expire_pending(self, now: str) -> list[str]:
        """Pending orders past their time: expired. Returns their ids."""
        orders = self.col("order")
        # D098: only the states that may expire (pending) are looked at.
        may_expire = [s.value for s in sources(OrderStatus.EXPIRED)]
        rows = orders.find(
            {"status": {"$in": may_expire}, "expires_at": {"$lte": now}}, {"order_id": 1}
        )
        ids = []
        for r in rows:
            # Each one guarded by its status: one paid meanwhile stays paid.
            done = orders.update_one(
                {"order_id": r["order_id"], "status": {"$in": may_expire}},
                {"$set": {"status": OrderStatus.EXPIRED.value}},
            )
            if done.modified_count:
                ids.append(r["order_id"])
        return ids

    def retire(self, order_id: str) -> None:
        """A pending order replaced by a newer one: expired, so a late payment still counts."""
        may_expire = [s.value for s in sources(OrderStatus.EXPIRED)]
        self.col("order").update_one(
            {"order_id": order_id, "status": {"$in": may_expire}},
            {"$set": {"status": OrderStatus.EXPIRED.value}},
        )

    def settle(
        self,
        order_id: str,
        status: OrderStatus,
        reference: str,
    ) -> bool:
        """Move an order to `status`, from a state that allows the move (D098).

        Guarded by the status the order is in, in one atomic update: returns
        False, and changes nothing, when another message settled the order
        first. The same update writes the gateway's result (D104).
        """
        allowed = [s.value for s in sources(status)]
        done = self.col("order").update_one(
            {"order_id": order_id, "status": {"$in": allowed}},
            {"$set": {"status": status.value, "reference": reference, "settled_at": _now()}},
        )
        return bool(done.modified_count)

    # ------------------------------------------------------------ events and settings

    def add_event(self, order_id: str, kind: str, detail: dict | None = None) -> None:
        """Keep what the gateway said about an order, on the order (D104).

        A message identical to one already kept -- same kind, same content,
        whether or not it was applied -- is counted on that event rather than
        kept again: a signed address replayed a thousand times is one event
        that says a thousand, not a thousand events. Appending is conditional
        on no such event being there, so two writers at once keep it once.
        """
        detail = detail or {}
        # A string, sorted: MongoDB compares embedded documents field by field
        # in order, so two dicts with the same content could differ.
        fingerprint = json.dumps(
            {k: v for k, v in detail.items() if k != "applied"}, sort_keys=True, ensure_ascii=False
        )
        same = {"kind": kind, "fingerprint": fingerprint}
        orders = self.col("order")
        now = _now()
        for _ in range(2):
            counted = orders.update_one(
                {"order_id": order_id, "events": {"$elemMatch": same}},
                {"$inc": {"events.$.repeats": 1}, "$set": {"events.$.last_at": now}},
            )
            if counted.matched_count:
                return
            added = orders.update_one(
                {"order_id": order_id, "events": {"$not": {"$elemMatch": same}}},
                {"$push": {"events": {**same, "detail": detail, "created_at": now,
                                      "repeats": 0, "last_at": None}}},
            )  # fmt: skip
            if added.modified_count:
                return

    def events(self, order_id: str) -> list[dict]:
        row = self.col("order").find_one({"order_id": order_id}, {"events": 1})
        return [
            {
                "kind": e["kind"],
                "detail": e["detail"],
                "created_at": e["created_at"],
                "repeats": e.get("repeats", 0),
                "last_at": e.get("last_at"),
            }
            for e in (row or {}).get("events", [])
        ]

    def setting(self, key: str) -> str | None:
        return get_setting(self.db, SETTING + key)

    def set_setting(self, key: str, value: str, by: str | None = None) -> None:
        set_setting(self.db, SETTING + key, value, by)

    def setting_once(self, key: str, value: str) -> str:
        """Store `value` unless the key already has one; return the value kept."""
        return setting_once(self.db, SETTING + key, value)[0]
