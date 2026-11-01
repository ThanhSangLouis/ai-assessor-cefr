"""Storage of orders and their payments (D033, D060, D084): run packs bought through a gateway.

An order is what was bought: the runs, the money, its status, the account that
placed it. Its payment (D084, one per order) is how the gateway took the money:
which gateway, real money or a test, the checkout and transaction numbers, the
result code, and everything the gateway said about it as `events`. Neither holds
anything about a person beyond the account: no card number, bank account or
payer name ever reaches this file (BR-32). Read back, an order carries its
payment's fields, so the billing service sees one record.

Marking an order paid is one conditional update, guarded by the order's
status: when the browser's return and the gateway's notification report the
same payment at once, exactly one of them settles it, and only that one writes
the payment's result.

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

# order: runs of the pack (`seats` before D075), amount_vnd what was paid (the
# plan fields of D033 orders stay on old documents). payment (D084): gateway
# none | sandbox | stripe (vnpay | momo on orders from before D075); live 1 for
# real money (D035); checkout_ref the gateway's id for the checkout. An event's
# fingerprint is its detail without "applied" (D035): repeats of an identical
# message are counted on the first.
INDEXES = {
    "order": [
        (("order_id",), True),
        (("created_at",), False),
        (("status", "expires_at"), False),
        (("created_by", "kind"), False),
    ],
    "payment": [
        (("order_id",), True),
        (("gateway", "checkout_ref"), False),
    ],
}
SETTING = "billing."  # this part's keys in `system`


# Every order is a pack of runs (D053, D075). The kind is still written on the
# document, so that the plan orders of D033 stored before stay out of reach.
CREDITS = "credits"


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

    @classmethod
    def from_doc(cls, doc: dict) -> Order:
        found = _known(cls, doc)
        # A pack ordered before D075 kept its runs in `seats`.
        found["runs"] = int(doc.get("runs", doc.get("seats", 0)))
        found["status"] = OrderStatus(doc["status"])
        return cls(**found)

    def to_doc(self) -> dict:
        return {**asdict(self), "status": self.status.value, "kind": CREDITS}


@dataclass
class Payment:
    """How the gateway took the money for one order (D084): its numbers and messages."""

    order_id: str
    gateway: str
    live: bool
    checkout_ref: str | None = None
    reference: str | None = None
    result_code: str | None = None
    settled_at: str | None = None
    events: list[dict] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Payment:
        found = _known(cls, doc)
        found["live"] = bool(doc.get("live"))
        return cls(**found)

    def to_doc(self) -> dict:
        return asdict(self)


def _view(order: dict | None, payment: dict | None) -> dict | None:
    """An order as the screens and the service read it: with its payment, without events."""
    if order is None:
        return None
    made = Order.from_doc(order).to_doc()
    made.pop("kind")
    paid = Payment.from_doc({"order_id": order["order_id"], "gateway": "none", **(payment or {})})
    return {**made, **{k: v for k, v in paid.to_doc().items() if k != "events"}}


class BillingRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "billing")
        ensure_system(self.db)

    # ------------------------------------------------------------ orders

    def create_order(self, order: dict) -> dict:
        made = Order.from_doc(order)
        paid = Payment.from_doc(order)
        self.col("order").insert_one(made.to_doc())
        self.col("payment").insert_one(paid.to_doc())
        return _view(made.to_doc(), paid.to_doc())  # type: ignore[return-value]

    def set_checkout_ref(self, order_id: str, reference: str) -> None:
        self.col("payment").update_one(
            {"order_id": order_id}, {"$set": {"checkout_ref": reference}}
        )

    def _payment(self, order_id: str) -> dict | None:
        return self.col("payment").find_one({"order_id": order_id}, {"events": 0})

    def _views(self, rows: list[dict]) -> list[dict]:
        """Orders with their payments, in one read for all the payments."""
        ids = [r["order_id"] for r in rows]
        payments = {
            p["order_id"]: p
            for p in self.col("payment").find({"order_id": {"$in": ids}}, {"events": 0})
        }
        return [_view(r, payments.get(r["order_id"])) for r in rows]  # type: ignore[misc]

    def order_by_checkout(self, gateway: str, reference: str) -> dict | None:
        """The order whose checkout the gateway knows by `reference` (a Stripe session id)."""
        paid = self.col("payment").find_one(
            {"gateway": gateway, "checkout_ref": reference}, {"events": 0}
        )
        if paid is None:
            return None
        return _view(self.col("order").find_one({"order_id": paid["order_id"]}), paid)

    def order(self, order_id: str) -> dict | None:
        return _view(self.col("order").find_one({"order_id": order_id}), self._payment(order_id))

    def orders_by(self, account_id: str, limit: int = 20) -> list[dict]:
        """One account's own run packs, newest first."""
        rows = list(
            self.col("order")
            .find({"created_by": account_id, "kind": CREDITS})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return self._views(rows)

    def uncredited(self) -> list[dict]:
        """Paid run packs whose runs have not reached the wallet yet (D053)."""
        rows = list(
            self.col("order").find(
                {"kind": CREDITS, "status": OrderStatus.PAID.value, "credited_at": None}
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
        nothing, when another message settled the order first. Only the
        message that moved the order writes the payment's result (D084).
        """
        settleable = [s.value for s in SETTLEABLE]
        taken = self.col("order").find_one_and_update(
            {"order_id": order_id, "status": {"$in": settleable}},
            {"$set": {"status": status.value}},
            return_document=ReturnDocument.AFTER,
        )
        if taken is None:
            return False
        self.col("payment").update_one(
            {"order_id": order_id},
            {"$set": {"reference": reference, "result_code": code, "settled_at": _now()}},
        )
        return True

    # ------------------------------------------------------------ events and settings

    def add_event(self, order_id: str, kind: str, detail: dict | None = None) -> None:
        """Keep what the gateway said about an order, on its payment (D084).

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
        orders = self.col("payment")
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
        row = self.col("payment").find_one({"order_id": order_id}, {"events": 1})
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
