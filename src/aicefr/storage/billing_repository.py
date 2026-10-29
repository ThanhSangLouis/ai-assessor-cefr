"""Storage of licences and orders (D033), one collection each (D060).

Neither holds anything about a person: an order knows the account that placed
it, the plan, the seats and the money, and keeps what each payment gateway
said about it -- codes and transaction numbers -- as its `events`; the
organisation's name is a setting in `system`. No card number, bank account or
payer name ever reaches this file (BR-32).

A gateway message has no life apart from the order it is about, so it is part
of the order's document rather than a document of its own. A licence is not:
a trial or a licence key has no order, so `license` is a collection, and a
licence bought by an order points back at it.

Marking an order paid is one conditional update, guarded by the order's
status, and only the writer whose update took installs the licence it bought:
when the browser's return and the gateway's notification report the same
payment at once, exactly one of them installs a licence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dc_fields
from datetime import date
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database

from aicefr.billing.payments import SETTLEABLE, OrderStatus
from aicefr.billing.plans import License, OrderKind, ServicePlan
from aicefr.storage.db import (
    MongoStore,
    ensure_indexes,
    ensure_system,
    get_setting,
    set_setting,
    setting_once,
)
from aicefr.storage.db import now_iso as _now

# license.source: trial | order | key. order: list_vnd is students x months x
# unit price, discount_vnd a school year paid at once, gross_vnd list minus
# discount (what the licence is worth); gateway none | sandbox | vnpay | stripe
# | momo; live 1 for real money (D035); checkout_ref the gateway's id for the
# checkout. An event's fingerprint is its detail without "applied" (D035):
# repeats of an identical message are counted on the first.
INDEXES = {
    "license": [(("license_id",), True), (("installed_at",), False)],
    "order": [
        (("order_id",), True),
        (("created_at",), False),
        (("gateway", "checkout_ref"), False),
        (("status", "expires_at"), False),
        (("created_by", "kind"), False),
    ],
}
SETTING = "billing."  # this part's keys in `system`


@dataclass
class Order:
    """One purchase: a licence for the school, or a pack of runs for a learner."""

    order_id: str
    plan: ServicePlan | None
    seats: int
    months: int | None
    unit_price: int | None
    list_vnd: int | None
    discount_vnd: int | None
    gross_vnd: int | None
    credit_vnd: int | None
    amount_vnd: int
    kind: OrderKind
    starts_on: str | None
    ends_on: str | None
    status: OrderStatus
    gateway: str
    live: int | bool | None
    created_by: str
    created_at: str
    expires_at: str | None
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
        found["kind"] = OrderKind(doc["kind"])
        found["status"] = OrderStatus(doc["status"])
        found["plan"] = ServicePlan(doc["plan"]) if doc.get("plan") else None
        return cls(**found)

    def to_doc(self) -> dict:
        return {
            **asdict(self),
            "plan": self.plan.value if self.plan else None,
            "kind": self.kind.value,
            "status": self.status.value,
        }

    def view(self) -> dict:
        """The order as the screens and the service read it, without its events."""
        doc = self.to_doc()
        doc.pop("events")
        return doc


def _view(row: dict | None) -> dict | None:
    return Order.from_doc(row).view() if row else None


class BillingRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "billing")
        ensure_system(self.db)

    # ------------------------------------------------------------ licences

    @staticmethod
    def _license(row: dict) -> License:
        return License(
            license_id=row["license_id"],
            organization=row["organization"],
            plan=ServicePlan(row["plan"]),
            seats=row["seats"],
            valid_from=date.fromisoformat(row["valid_from"]),
            valid_to=date.fromisoformat(row["valid_to"]),
            source=row["source"],
            order_id=row.get("order_id"),
            value_vnd=row.get("value_vnd", 0),
            installed_at=row["installed_at"],
        )

    def licenses(self) -> list[License]:
        rows = self.col("license").find().sort([("installed_at", ASCENDING), ("_id", ASCENDING)])
        return [self._license(r) for r in rows]

    def has_license(self, license_id: str) -> bool:
        return self.col("license").find_one({"license_id": license_id}) is not None

    @staticmethod
    def _insert_license(
        db: Database, lic: License, key: str | None, by: str | None, at: str
    ) -> None:
        db["license"].insert_one(
            {
                "license_id": lic.license_id,
                "organization": lic.organization,
                "plan": lic.plan.value,
                "seats": lic.seats,
                "valid_from": lic.valid_from.isoformat(),
                "valid_to": lic.valid_to.isoformat(),
                "source": lic.source,
                "order_id": lic.order_id,
                "value_vnd": lic.value_vnd,
                "license_key": key,
                "installed_by": by,
                "installed_at": at,
            }
        )

    def add_license(self, lic: License, key: str | None = None, by: str | None = None) -> None:
        self._insert_license(self.db, lic, key, by, lic.installed_at or _now())

    def start_trial(self, lic: License) -> bool:
        """Install the deployment's one trial; False when it was started before.

        The marker goes in first and a unique index lets only one writer put it
        there, so two first requests at once start one trial, not two.
        """
        _kept, mine = setting_once(self.db, SETTING + "trial_started", lic.license_id)
        if not mine:
            return False
        self._insert_license(self.db, lic, None, None, lic.installed_at or _now())
        return True

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

    def orders(self, limit: int = 50) -> list[dict]:
        rows = (
            self.col("order")
            .find()
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [Order.from_doc(r).view() for r in rows]

    def orders_by(self, account_id: str, kind: str, limit: int = 20) -> list[dict]:
        """One account's own orders of one kind, newest first: a learner's run packs."""
        rows = (
            self.col("order")
            .find({"created_by": account_id, "kind": kind})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [Order.from_doc(r).view() for r in rows]

    def uncredited(self, kind: str) -> list[dict]:
        """Paid orders of `kind` whose runs have not reached the wallet yet (D053)."""
        rows = self.col("order").find(
            {"kind": kind, "status": OrderStatus.PAID.value, "credited_at": None}
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
        license: License | None = None,
        by: str | None = None,
    ) -> bool:
        """Move an order from pending or expired to `status`, installing `license` with it.

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
        if taken is None:
            return False
        if license is not None:
            self._insert_license(self.db, license, None, by, at)
        return True

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
