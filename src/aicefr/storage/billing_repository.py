"""Storage of licences, orders and payment events (D033).

Four collections, none of them holding anything about a person: an order knows the
administrator account that placed it, the plan, the seats and the money; a
payment event keeps the gateway's codes and transaction number; the
organisation's name is a setting. No card number, bank account or payer name
ever reaches this file (BR-32).

Marking an order paid is one conditional update, guarded by the order's
status, and only the writer whose update took installs the licence it bought:
when the browser's return and the gateway's notification report the same
payment at once, exactly one of them installs a licence.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database

from aicefr.billing.payments import SETTLEABLE, OrderStatus
from aicefr.billing.plans import License, ServicePlan
from aicefr.storage.db import IntegrityError, MongoStore, ensure_indexes, fields, next_id
from aicefr.storage.db import now_iso as _now

# billing_license.source: trial | order | key. billing_order: list_vnd is
# students x months x unit price, discount_vnd a school year paid at once,
# gross_vnd list minus discount (what the licence is worth); status pending |
# paid | failed | cancelled | expired; gateway none | sandbox | vnpay | stripe |
# momo; live 1 for real money (D035); checkout_ref the gateway's id for the
# checkout. billing_event.fingerprint is the detail without "applied" (D035),
# repeats the identical messages after the first.
INDEXES = {
    "billing_license": [(("license_id",), True), (("installed_at",), False)],
    "billing_order": [
        (("order_id",), True),
        (("created_at",), False),
        (("gateway", "checkout_ref"), False),
        (("status", "expires_at"), False),
    ],
    "billing_event": [(("event_id",), True), (("order_id", "kind", "fingerprint"), True)],
    "billing_setting": [(("key",), True)],
}

ORDER_FIELDS = (
    "order_id",
    "plan",
    "seats",
    "months",
    "unit_price",
    "list_vnd",
    "discount_vnd",
    "gross_vnd",
    "credit_vnd",
    "amount_vnd",
    "kind",
    "starts_on",
    "ends_on",
    "status",
    "gateway",
    "live",
    "checkout_ref",
    "reference",
    "result_code",
    "created_by",
    "created_at",
    "expires_at",
    "settled_at",
    "credited_at",
)


class BillingRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "billing")

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
        rows = (
            self.col("billing_license")
            .find()
            .sort([("installed_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [self._license(r) for r in rows]

    def has_license(self, license_id: str) -> bool:
        return self.col("billing_license").find_one({"license_id": license_id}) is not None

    @staticmethod
    def _insert_license(
        db: Database, lic: License, key: str | None, by: str | None, at: str
    ) -> None:
        db["billing_license"].insert_one(
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
        try:
            self.col("billing_setting").insert_one(
                {"key": "trial_started", "value": lic.license_id, "updated_by": None,
                 "updated_at": _now()}
            )  # fmt: skip
        except IntegrityError:
            return False
        self._insert_license(self.db, lic, None, None, lic.installed_at or _now())
        return True

    # ------------------------------------------------------------ orders

    def create_order(self, order: dict) -> dict:
        cols = (
            "order_id plan seats months unit_price list_vnd discount_vnd gross_vnd credit_vnd"
            " amount_vnd kind"
            " starts_on ends_on status gateway live created_by created_at expires_at"
        ).split()
        document = dict.fromkeys(ORDER_FIELDS)
        document.update({k: order[k] for k in cols})
        self.col("billing_order").insert_one(document)
        return self.order(order["order_id"])  # type: ignore[return-value]

    def set_checkout_ref(self, order_id: str, reference: str) -> None:
        self.col("billing_order").update_one(
            {"order_id": order_id}, {"$set": {"checkout_ref": reference}}
        )

    def order_by_checkout(self, gateway: str, reference: str) -> dict | None:
        """The order whose checkout the gateway knows by `reference` (a Stripe session id)."""
        row = self.col("billing_order").find_one({"gateway": gateway, "checkout_ref": reference})
        return fields(row, ORDER_FIELDS)

    def order(self, order_id: str) -> dict | None:
        return fields(self.col("billing_order").find_one({"order_id": order_id}), ORDER_FIELDS)

    def orders(self, limit: int = 50) -> list[dict]:
        rows = (
            self.col("billing_order")
            .find()
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [fields(r, ORDER_FIELDS) for r in rows]  # type: ignore[misc]

    def orders_by(self, account_id: str, kind: str, limit: int = 20) -> list[dict]:
        """One account's own orders of one kind, newest first: a learner's run packs."""
        rows = (
            self.col("billing_order")
            .find({"created_by": account_id, "kind": kind})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [fields(r, ORDER_FIELDS) for r in rows]  # type: ignore[misc]

    def uncredited(self, kind: str) -> list[dict]:
        """Paid orders of `kind` whose runs have not reached the wallet yet (D053)."""
        rows = self.col("billing_order").find(
            {"kind": kind, "status": OrderStatus.PAID.value, "credited_at": None}
        )
        return [fields(r, ORDER_FIELDS) for r in rows]  # type: ignore[misc]

    def mark_credited(self, order_id: str) -> bool:
        done = self.col("billing_order").update_one(
            {"order_id": order_id, "credited_at": None}, {"$set": {"credited_at": _now()}}
        )
        return bool(done.modified_count)

    def expire_pending(self, now: str) -> list[str]:
        """Pending orders past their time: expired. Returns their ids."""
        orders = self.col("billing_order")
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
        self.col("billing_order").update_one(
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
        taken = self.col("billing_order").find_one_and_update(
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

    def add_event(self, order_id: str | None, kind: str, detail: dict | None = None) -> None:
        """Keep what was said about an order.

        A message identical to one already kept -- same kind, same content,
        whether or not it was applied -- is counted on that document rather than
        stored again: a signed address replayed a thousand times is one document
        that says a thousand, not a thousand documents.
        """
        detail = detail or {}
        fingerprint = json.dumps(
            {k: v for k, v in detail.items() if k != "applied"}, sort_keys=True, ensure_ascii=False
        )
        events = self.col("billing_event")
        key = {"order_id": order_id, "kind": kind, "fingerprint": fingerprint}
        now = _now()
        if events.update_one(key, {"$inc": {"repeats": 1}, "$set": {"last_at": now}}).matched_count:
            return
        try:
            events.insert_one(
                {
                    **key,
                    "event_id": next_id(self.db, "billing_event"),
                    "detail_json": json.dumps(detail, ensure_ascii=False),
                    "created_at": now,
                    "repeats": 0,
                    "last_at": None,
                }
            )
        except IntegrityError:
            # The same message, kept by another writer a moment ago.
            events.update_one(key, {"$inc": {"repeats": 1}, "$set": {"last_at": now}})

    def events(self, order_id: str) -> list[dict]:
        rows = self.col("billing_event").find({"order_id": order_id}).sort("event_id", ASCENDING)
        return [
            {
                "kind": r["kind"],
                "detail": json.loads(r["detail_json"]),
                "created_at": r["created_at"],
                "repeats": r.get("repeats", 0),
                "last_at": r.get("last_at"),
            }
            for r in rows
        ]

    def setting(self, key: str) -> str | None:
        row = self.col("billing_setting").find_one({"key": key})
        return row["value"] if row else None

    def set_setting(self, key: str, value: str, by: str | None = None) -> None:
        self.col("billing_setting").update_one(
            {"key": key},
            {"$set": {"value": value, "updated_by": by, "updated_at": _now()}},
            upsert=True,
        )

    def setting_once(self, key: str, value: str) -> str:
        """Store `value` unless the key already has one; return the value kept."""
        settings = self.col("billing_setting")
        try:
            settings.insert_one(
                {"key": key, "value": value, "updated_by": None, "updated_at": _now()}
            )
        except IntegrityError:
            pass
        return settings.find_one({"key": key})["value"]
