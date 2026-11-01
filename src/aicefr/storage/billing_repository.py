"""Storage of orders (D033, D060): run packs bought through a payment gateway.

An order holds nothing about a person beyond the account that placed it: the
runs, the money, and what each payment gateway said about it -- codes and
transaction numbers -- as its `events`. No card number, bank account or payer
name ever reaches this file (BR-32).

Marking an order paid is one conditional update, guarded by the order's
status: when the browser's return and the gateway's notification report the
same payment at once, exactly one of them settles it.

D075: one centre and no service plans. The `license` collection of D033 is
neither read nor written any more; what a deployment already holds there is
left as it was.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dc_fields
from pathlib import Path

from pymongo import DESCENDING, ReturnDocument

from aicefr.billing.payments import SETTLEABLE, OrderStatus
from aicefr.storage.db import (
    MongoStore,
    ensure_indexes,
    ensure_system,
    get_setting,
    set_setting,
    setting_once,
)
from aicefr.storage.db import now_iso as _now

# order: seats is the runs of the pack, amount_vnd what was paid (the plan
# fields of D033 orders stay on old documents); gateway none | sandbox |
# stripe (vnpay | momo on orders from before D075); live 1 for real money
# (D035); checkout_ref the gateway's id for the checkout. An event's
# fingerprint is its detail without "applied" (D035): repeats of an identical
# message are counted on the first.
INDEXES = {
    "order": [
        (("order_id",), True),
        (("created_at",), False),
        (("gateway", "checkout_ref"), False),
        (("status", "expires_at"), False),
        (("created_by", "kind"), False),
    ],
}
SETTING = "billing."  # this part's keys in `system`


# Every order is a pack of runs (D053, D075). The kind is still written on the
# document, so that the plan orders of D033 stored before stay out of reach.
CREDITS = "credits"


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
    gateway: str
    live: bool
    created_by: str
    created_at: str
    expires_at: str | None = None
    checkout_ref: str | None = None
    reference: str | None = None
    result_code: str | None = None
    settled_at: str | None = None
    credited_at: str | None = None
    events: list[dict] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Order:
        known = {f.name for f in dc_fields(cls)}
        found = {k: v for k, v in doc.items() if k in known}
        # A pack ordered before D075 kept its runs in `seats`.
        found["runs"] = int(doc.get("runs", doc.get("seats", 0)))
        found["live"] = bool(doc.get("live"))
        found["status"] = OrderStatus(doc["status"])
        return cls(**found)

    def to_doc(self) -> dict:
        return {**asdict(self), "status": self.status.value, "kind": CREDITS}

    def view(self) -> dict:
        """The order as the screens and the service read it, without its events."""
        doc = self.to_doc()
        doc.pop("events")
        doc.pop("kind")
        return doc


def _view(row: dict | None) -> dict | None:
    return Order.from_doc(row).view() if row else None


class BillingRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "billing")
        ensure_system(self.db)

    # ------------------------------------------------------------ orders

    def create_order(self, order: dict) -> dict:
        made = Order.from_doc(order)
        self.col("order").insert_one(made.to_doc())
        return made.view()

    def set_checkout_ref(self, order_id: str, reference: str) -> None:
        self.col("order").update_one({"order_id": order_id}, {"$set": {"checkout_ref": reference}})

    def order_by_checkout(self, gateway: str, reference: str) -> dict | None:
        """The order whose checkout the gateway knows by `reference` (a Stripe session id)."""
        return _view(self.col("order").find_one({"gateway": gateway, "checkout_ref": reference}))

    def order(self, order_id: str) -> dict | None:
        return _view(self.col("order").find_one({"order_id": order_id}))

    def orders_by(self, account_id: str, limit: int = 20) -> list[dict]:
        """One account's own run packs, newest first."""
        rows = (
            self.col("order")
            .find({"created_by": account_id, "kind": CREDITS})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [Order.from_doc(r).view() for r in rows]

    def uncredited(self) -> list[dict]:
        """Paid run packs whose runs have not reached the wallet yet (D053)."""
        rows = self.col("order").find(
            {"kind": CREDITS, "status": OrderStatus.PAID.value, "credited_at": None}
        )
        return [Order.from_doc(r).view() for r in rows]

    def mark_credited(self, order_id: str) -> bool:
        done = self.col("order").update_one(
            {"order_id": order_id, "credited_at": None}, {"$set": {"credited_at": _now()}}
        )
        return bool(done.modified_count)

    def expire_pending(self, now: str) -> list[str]:
        """Pending orders past their time: expired. Returns their ids."""
        orders = self.col("order")
        rows = orders.find(
            {"status": OrderStatus.PENDING.value, "expires_at": {"$lte": now}}, {"order_id": 1}
        )
        ids = []
        for r in rows:
            # Each one guarded by its status: one paid meanwhile stays paid.
            done = orders.update_one(
                {"order_id": r["order_id"], "status": OrderStatus.PENDING.value},
                {"$set": {"status": OrderStatus.EXPIRED.value}},
            )
            if done.modified_count:
                ids.append(r["order_id"])
        return ids

    def retire(self, order_id: str) -> None:
        """A pending order replaced by a newer one: expired, so a late payment still counts."""
        self.col("order").update_one(
            {"order_id": order_id, "status": OrderStatus.PENDING.value},
            {"$set": {"status": OrderStatus.EXPIRED.value}},
        )

    def settle(
        self,
        order_id: str,
        status: OrderStatus,
        reference: str,
        code: str,
    ) -> bool:
        """Move an order from pending or expired to `status`.

        Guarded by the status the order is in: returns False, and changes
        nothing, when another message settled the order first.
        """
        settleable = [s.value for s in SETTLEABLE]
        at = _now()
        taken = self.col("order").find_one_and_update(
            {"order_id": order_id, "status": {"$in": settleable}},
            {"$set": {"status": status.value, "reference": reference, "result_code": code,
                      "settled_at": at}},
            return_document=ReturnDocument.AFTER,
        )  # fmt: skip
        return taken is not None

    # ------------------------------------------------------------ events and settings

    def add_event(self, order_id: str, kind: str, detail: dict | None = None) -> None:
        """Keep what was said about an order, on the order.

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
