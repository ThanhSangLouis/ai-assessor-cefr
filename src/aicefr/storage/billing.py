"""Transactional persistence for M14 billing over the shared v9 SQLite store."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from aicefr.billing.contracts import Entitlement, Order, Plan, Quote, Receipt
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS
from aicefr.storage.sqlite import SQLiteStore


def _datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise BillingError("timezone_required")
    return value.astimezone(UTC).isoformat()


def ensure_organization_binding(
    connection: sqlite3.Connection, organization_id: str, now: datetime
) -> str:
    """Bind one pseudonymous organization ID to this installation exactly once.

    The caller owns a write transaction. The ID is installation metadata, never an
    account-level entitlement selector.
    """
    valid = organization_id == "local-demo" or (
        isinstance(organization_id, str)
        and organization_id.startswith("org_")
        and 8 <= len(organization_id[4:]) <= 59
        and all(char.isascii() and (char.isalnum() or char in "_-") for char in organization_id[4:])
    )
    if not valid:
        raise BillingError("organization_unavailable", 503)
    key = "billing.installation.organization"
    row = connection.execute("SELECT payload FROM runtime_settings WHERE key=?", (key,)).fetchone()
    if row is None:
        connection.execute(
            "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
            "VALUES(?,?,1,'v1','billing',?)",
            (
                key,
                json.dumps({"organization_id": organization_id}, separators=(",", ":")),
                _iso(now),
            ),
        )
        return organization_id
    try:
        saved = json.loads(row[0])["organization_id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise BillingError("organization_binding_invalid", 503) from exc
    if saved != organization_id:
        raise BillingError("organization_binding_mismatch", 409)
    return organization_id


def _plan_from_row(row: tuple[Any, ...]) -> Plan:
    return Plan(
        code=str(row[0]),
        title=str(row[1]),
        monthly_minor=0,
        student_limit=int(row[3]),
        warning_quota=int(row[4]),
        features=frozenset(json.loads(row[2])),
        active=bool(row[5]),
    )


class BillingRepository:
    """Persistence adapter; all methods share the injected store and transaction."""

    def __init__(self, store: SQLiteStore) -> None:
        self.storage = store
        self.connection = store.connection
        with self.storage.transaction() as db:
            for plan in PLANS.values():
                db.execute(
                    "INSERT OR IGNORE INTO billing_plans(plan_code,title,features_json,"
                    "student_limit,warning_quota,active,revision) VALUES(?,?,?,?,?,1,0)",
                    (
                        plan.code,
                        plan.title,
                        json.dumps(sorted(plan.features), separators=(",", ":")),
                        plan.student_limit,
                        plan.warning_quota,
                    ),
                )

    def list_plans(self) -> tuple[Plan, ...]:
        rows = self.connection.execute(
            "SELECT plan_code,title,features_json,student_limit,warning_quota,active "
            "FROM billing_plans ORDER BY CASE plan_code WHEN 'FREE' THEN 0 "
            "WHEN 'TRIAL' THEN 1 WHEN 'STANDARD' THEN 2 ELSE 3 END"
        ).fetchall()
        prices = {p.code: p.monthly_minor for p in PLANS.values()}
        return tuple(
            Plan(
                p.code,
                p.title,
                prices.get(p.code, 0),
                p.student_limit,
                p.warning_quota,
                p.features,
                p.currency,
                p.active,
            )
            for p in (_plan_from_row(row) for row in rows)
        )

    def bind_organization(self, organization_id: str, *, now: datetime) -> str:
        with self.storage.transaction() as db:
            return ensure_organization_binding(db, organization_id, now)

    def save_quote(self, quote: Quote) -> None:
        with self.storage.transaction() as db:
            db.execute(
                "INSERT INTO billing_quotes(quote_id,account_id,plan_code,inputs_json,"
                "subtotal_minor,discount_minor,credit_minor,total_minor,currency,expires_at,"
                "created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    quote.quote_id,
                    quote.account_id,
                    quote.plan_code,
                    json.dumps(
                        {"months": quote.months, **json.loads(quote.context_json)},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    quote.subtotal_minor,
                    quote.discount_minor,
                    quote.credit_minor,
                    quote.total_minor,
                    quote.currency,
                    _iso(quote.expires_at),
                    _iso(quote.created_at),
                ),
            )

    def save_quote_with_idempotency(
        self, quote: Quote, *, key_hash: str, input_hash: str, token: str
    ) -> None:
        with self.storage.transaction() as db:
            self.assert_admin_session(db, token, quote.account_id, quote.created_at)
            existing = db.execute(
                "SELECT payload FROM runtime_settings WHERE key=?",
                (f"billing.quote.{key_hash}",),
            ).fetchone()
            if existing:
                saved = json.loads(existing[0])
                if saved.get("input_hash") != input_hash:
                    raise BillingError("idempotency_key_reused", 409)
                return
            db.execute(
                "INSERT INTO billing_quotes(quote_id,account_id,plan_code,inputs_json,"
                "subtotal_minor,discount_minor,credit_minor,total_minor,currency,expires_at,"
                "created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    quote.quote_id,
                    quote.account_id,
                    quote.plan_code,
                    json.dumps(
                        {"months": quote.months, **json.loads(quote.context_json)},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    quote.subtotal_minor,
                    quote.discount_minor,
                    quote.credit_minor,
                    quote.total_minor,
                    quote.currency,
                    _iso(quote.expires_at),
                    _iso(quote.created_at),
                ),
            )
            self.set_setting(
                db,
                f"billing.quote.{key_hash}",
                {"input_hash": input_hash, "quote_id": quote.quote_id},
                quote.created_at,
            )

    def get_quote(self, quote_id: str) -> Quote | None:
        row = self.connection.execute(
            "SELECT quote_id,account_id,plan_code,inputs_json,subtotal_minor,discount_minor,"
            "credit_minor,total_minor,currency,expires_at,created_at FROM billing_quotes "
            "WHERE quote_id=?",
            (quote_id,),
        ).fetchone()
        if row is None:
            return None
        inputs = json.loads(row[3])
        context = {key: value for key, value in inputs.items() if key != "months"}
        return Quote(
            quote_id=str(row[0]),
            account_id=str(row[1]),
            plan_code=str(row[2]),
            months=int(inputs["months"]),
            subtotal_minor=int(row[4]),
            discount_minor=int(row[5]),
            credit_minor=int(row[6]),
            total_minor=int(row[7]),
            currency=str(row[8]),
            created_at=_datetime(row[10]),
            expires_at=_datetime(row[9]),
            context_json=json.dumps(context, sort_keys=True, separators=(",", ":")),
            effective_at=_datetime(inputs.get("effective_at")),
            ends_at=_datetime(inputs.get("ends_at")),
            change_kind=str(inputs.get("change_kind", "initial")),
        )

    def find_setting(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT payload FROM runtime_settings WHERE key=?", (key,)
        ).fetchone()
        return str(row[0]) if row else None

    def set_setting(
        self, db: sqlite3.Connection, key: str, payload: Mapping[str, Any], now: datetime
    ) -> None:
        db.execute(
            "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
            "VALUES(?,?,1,'v1','billing',?) ON CONFLICT(key) DO UPDATE SET "
            "payload=excluded.payload,revision=runtime_settings.revision+1,updated_at=excluded.updated_at",
            (key, json.dumps(payload, sort_keys=True, separators=(",", ":")), _iso(now)),
        )

    def save_quote_idempotency(
        self, db: sqlite3.Connection, key_hash: str, input_hash: str, quote_id: str, now: datetime
    ) -> None:
        self.set_setting(
            db,
            f"billing.quote.{key_hash}",
            {"input_hash": input_hash, "quote_id": quote_id},
            now,
        )

    def get_order_idempotency(self, key_hash: str) -> Order | None:
        row = self.connection.execute(
            "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
            "currency,created_at,updated_at FROM billing_orders WHERE idempotency_key=?",
            (key_hash,),
        ).fetchone()
        return self._order(row) if row else None

    def create_order(
        self,
        *,
        order_id: str,
        quote: Quote,
        gateway: str,
        mode: str,
        idempotency_hash: str,
        now: datetime,
        token: str,
        expected_entitlement_snapshot: Mapping[str, Any] | None = None,
    ) -> Order:
        with self.storage.transaction() as db:
            self.assert_admin_session(db, token, quote.account_id, now)
            current = self.current_entitlement(now)
            snapshot = {
                "entitlement_id": current.entitlement_id,
                "plan_code": current.plan_code,
                "source_order": current.source_order,
                "effective_at": (
                    current.effective_at.astimezone(UTC).isoformat()
                    if current.effective_at is not None
                    else None
                ),
                "expires_at": (
                    current.expires_at.astimezone(UTC).isoformat()
                    if current.expires_at is not None
                    else None
                ),
            }
            if expected_entitlement_snapshot is not None and snapshot != dict(
                expected_entitlement_snapshot
            ):
                raise BillingError("quote_stale", 409)
            prior = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE idempotency_key=?",
                (idempotency_hash,),
            ).fetchone()
            if prior:
                existing = self._order(prior)
                if (existing.quote_id, existing.gateway) != (quote.quote_id, gateway):
                    raise BillingError("idempotency_key_reused", 409)
                return existing
            db.execute(
                "INSERT INTO billing_orders(order_id,quote_id,account_id,state,gateway,mode,"
                "idempotency_key,amount_minor,currency,created_at,updated_at) "
                "VALUES(?,?,?,'PENDING',?,?,?,?,?,?,?)",
                (
                    order_id,
                    quote.quote_id,
                    quote.account_id,
                    gateway,
                    mode,
                    idempotency_hash,
                    quote.total_minor,
                    quote.currency,
                    _iso(now),
                    _iso(now),
                ),
            )
            self._audit(db, quote.account_id, "billing_order_created", order_id, now)
            row = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            return self._order(row)

    def set_checkout(
        self, order_id: str, checkout_ref: str, now: datetime, *, token: str, actor_id: str
    ) -> Order:
        if not checkout_ref or len(checkout_ref) > 200:
            raise BillingError("invalid_checkout_reference")
        with self.storage.transaction() as db:
            self.assert_admin_session(db, token, actor_id, now)
            db.execute(
                "UPDATE billing_orders SET checkout_ref=?,updated_at=? WHERE order_id=? "
                "AND state='PENDING' AND (checkout_ref IS NULL OR checkout_ref=?)",
                (checkout_ref, _iso(now), order_id, checkout_ref),
            )
            row = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise BillingError("order_unavailable", 404)
            order = self._order(row)
            if order.checkout_ref != checkout_ref:
                raise BillingError("checkout_reference_conflict", 409)
            return order

    def get_order(self, order_id: str) -> Order | None:
        row = self.connection.execute(
            "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
            "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
            (order_id,),
        ).fetchone()
        return self._order(row) if row else None

    def list_orders(self, limit: int = 100) -> tuple[Order, ...]:
        rows = self.connection.execute(
            "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
            "currency,created_at,updated_at FROM billing_orders ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return tuple(self._order(row) for row in rows)

    def set_order_state(self, order_id: str, state: str, now: datetime) -> Order:
        with self.storage.transaction() as db:
            row = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise BillingError("order_unavailable", 404)
            order = self._order(row)
            if order.state == state:
                return order
            if order.state != "PENDING" or state not in {"CANCELLED", "EXPIRED"}:
                raise BillingError("invalid_order_transition", 409)
            db.execute(
                "UPDATE billing_orders SET state=?,updated_at=? "
                "WHERE order_id=? AND state='PENDING'",
                (state, _iso(now), order_id),
            )
            self._audit(db, order.account_id, f"billing_order_{state.lower()}", order_id, now)
            return self.get_order(order_id)

    def cancel_order_idempotent(
        self, order_id: str, key_hash: str, actor_id: str, now: datetime, token: str
    ) -> Order:
        setting_key = f"billing.cancel.{key_hash}"
        with self.storage.transaction() as db:
            self.assert_admin_session(db, token, actor_id, now)
            prior = db.execute(
                "SELECT payload FROM runtime_settings WHERE key=?", (setting_key,)
            ).fetchone()
            if prior:
                saved = json.loads(prior[0])
                if saved.get("order_id") != order_id:
                    raise BillingError("idempotency_key_reused", 409)
                row = db.execute(
                    "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,"
                    "amount_minor,"
                    "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                    (order_id,),
                ).fetchone()
                if row is None:
                    raise BillingError("order_unavailable", 404)
                return self._order(row)
            row = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise BillingError("order_unavailable", 404)
            order = self._order(row)
            if order.state != "PENDING":
                raise BillingError("invalid_order_transition", 409)
            db.execute(
                "UPDATE billing_orders SET state='CANCELLED',updated_at=? "
                "WHERE order_id=? AND state='PENDING'",
                (_iso(now), order_id),
            )
            self.set_setting(db, setting_key, {"order_id": order_id}, now)
            self._audit(db, actor_id, "billing_order_cancelled", order_id, now)
            result = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            return self._order(result)

    def settle(
        self,
        event: Mapping[str, Any],
        *,
        now: datetime,
        apply_entitlement: Callable[..., None],
        organization_id: str,
        admin_token: str | None = None,
        admin_actor_id: str | None = None,
        idempotency_key_hash: str | None = None,
    ) -> Order:
        required = {
            "event_id",
            "order_id",
            "checkout_id",
            "amount",
            "currency",
            "status",
            "mode",
            "gateway",
            "payload_hash",
            "signature_valid",
            "occurred_at",
        }
        if not required <= event.keys() or event.get("signature_valid") is not True:
            raise BillingError("invalid_payment_event", 422)
        order_id = event["order_id"]
        with self.storage.transaction() as db:
            if admin_token is not None and admin_actor_id is not None:
                self.assert_admin_session(db, admin_token, admin_actor_id, now)
            row = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise BillingError("order_unavailable", 404)
            order = self._order(row)
            if (
                event["gateway"] != order.gateway
                or event["mode"] != order.mode
                or event["checkout_id"] != order.checkout_ref
                or type(event["amount"]) is not int
                or event["amount"] != order.amount_minor
                or event["currency"] != order.currency
                or not isinstance(event["payload_hash"], str)
                or len(event["payload_hash"]) != 64
            ):
                raise BillingError("payment_binding_mismatch", 409)
            occurred = event["occurred_at"]
            if isinstance(occurred, str):
                occurred = _datetime(occurred)
            if not isinstance(occurred, datetime) or occurred.tzinfo is None:
                raise BillingError("invalid_payment_timestamp")
            occurred = occurred.astimezone(UTC)
            if occurred < _datetime(order.created_at) - timedelta(
                minutes=5
            ) or occurred > now + timedelta(minutes=5):
                raise BillingError("invalid_payment_timestamp", 409)
            if idempotency_key_hash is not None:
                idem_setting = f"billing.sandbox.{idempotency_key_hash}"
                prior_idem = db.execute(
                    "SELECT payload FROM runtime_settings WHERE key=?", (idem_setting,)
                ).fetchone()
                if prior_idem:
                    prior = json.loads(prior_idem[0])
                    if (
                        prior.get("order_id") != order.order_id
                        or prior.get("payload_hash") != event["payload_hash"]
                    ):
                        raise BillingError("idempotency_key_reused", 409)
                    return order
                self.set_setting(
                    db,
                    idem_setting,
                    {"order_id": order.order_id, "payload_hash": event["payload_hash"]},
                    now,
                )
            duplicate = db.execute(
                "SELECT order_id,processed_state FROM payment_events WHERE normalized_hash=?",
                (event["payload_hash"],),
            ).fetchone()
            if duplicate is not None:
                if duplicate[0] != order.order_id:
                    raise BillingError("payment_event_replayed", 409)
                return order
            event_id_row = db.execute(
                "SELECT normalized_hash FROM payment_events WHERE event_id=?",
                (event["event_id"],),
            ).fetchone()
            if event_id_row is not None:
                raise BillingError("payment_event_conflict", 409)
            target = {
                "paid": "PAID",
                "failed": "FAILED",
                "cancelled": "CANCELLED",
                "pending": "PENDING",
            }.get(event["status"])
            if target is None:
                raise BillingError("invalid_payment_status")
            quote = self.get_quote(order.quote_id)
            if quote is None:
                raise BillingError("quote_unavailable", 409)
            checkout_expired = occurred > quote.expires_at
            processed_state = target
            if checkout_expired:
                processed_state = "late_success_review" if target == "PAID" else "expired_checkout"
            db.execute(
                "INSERT INTO payment_events(event_id,order_id,gateway,normalized_hash,"
                "signature_valid,"
                "payload_redacted,received_at,processed_state) VALUES(?,?,?,?,1,?,?,?)",
                (
                    str(event["event_id"]),
                    order.order_id,
                    order.gateway,
                    event["payload_hash"],
                    json.dumps({"status": target}, sort_keys=True),
                    _iso(now),
                    processed_state,
                ),
            )
            if checkout_expired and order.state == "PENDING":
                db.execute(
                    "UPDATE billing_orders SET state='EXPIRED',updated_at=? "
                    "WHERE order_id=? AND state='PENDING'",
                    (_iso(now), order.order_id),
                )
                self._audit(db, order.account_id, "billing_order_expired", order.order_id, now)
                if target == "PAID":
                    self._audit(
                        db,
                        order.account_id,
                        "billing_payment_late_success_review",
                        order.order_id,
                        now,
                    )
                fresh = db.execute(
                    "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,"
                    "amount_minor,"
                    "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                    (order.order_id,),
                ).fetchone()
                return self._order(fresh)
            if order.state in {"CANCELLED", "PAID"}:
                if order.state == "PAID" and target == "PAID":
                    return order
                if order.state == "CANCELLED" and target == "PAID":
                    db.execute(
                        "UPDATE payment_events SET processed_state='late_success_review' "
                        "WHERE normalized_hash=?",
                        (event["payload_hash"],),
                    )
                    self._audit(
                        db,
                        order.account_id,
                        "billing_payment_late_success_review",
                        order.order_id,
                        now,
                    )
                    return order
                raise BillingError("invalid_order_transition", 409)
            if order.state in {"FAILED", "EXPIRED"} and target != "PAID":
                return order
            if target == "PAID":
                if order.state in {"FAILED", "EXPIRED"}:
                    db.execute(
                        "UPDATE payment_events SET processed_state='late_success_review' "
                        "WHERE normalized_hash=?",
                        (event["payload_hash"],),
                    )
                    return order
                updated = db.execute(
                    "UPDATE billing_orders SET state='PAID',updated_at=? WHERE order_id=? "
                    "AND state IN ('PENDING','FAILED','EXPIRED')",
                    (_iso(now), order.order_id),
                )
                if updated.rowcount != 1:
                    raise BillingError("payment_race_lost", 409)
                plan = next((p for p in PLANS.values() if p.code == quote.plan_code), None)
                if plan is None:
                    raise BillingError("unknown_plan")
                try:
                    quote_context = json.loads(quote.context_json)
                    effective = _datetime(quote_context["effective_at"])
                    if effective is None:
                        raise ValueError
                except (ValueError, KeyError, TypeError) as exc:
                    raise BillingError("quote_invalid", 409) from exc
                expires = (
                    None
                    if plan.code == "FREE"
                    else (
                        effective + timedelta(days=30)
                        if plan.code == "TRIAL"
                        else _add_months(effective, quote.months)
                    )
                )
                grace = (
                    expires + timedelta(days=14)
                    if expires is not None and plan.code not in {"FREE", "TRIAL"}
                    else None
                )
                apply_entitlement(
                    db,
                    account_id=order.account_id,
                    organization_id=organization_id,
                    plan_code=plan.code,
                    features=plan.features,
                    student_limit=plan.student_limit,
                    warning_quota=plan.warning_quota,
                    effective_at=effective,
                    expires_at=expires,
                    grace_until=grace,
                    source_order=order.order_id,
                )
                receipt = {
                    "receipt_id": uuid.uuid4().hex,
                    "order_id": order.order_id,
                    "plan_code": plan.code,
                    "amount_minor": order.amount_minor,
                    "currency": order.currency,
                }
                db.execute(
                    "INSERT INTO billing_receipts(receipt_id,order_id,account_id,receipt_json,"
                    "issued_at) "
                    "VALUES(?,?,?,?,?)",
                    (
                        receipt["receipt_id"],
                        order.order_id,
                        order.account_id,
                        json.dumps(receipt, sort_keys=True, separators=(",", ":")),
                        _iso(now),
                    ),
                )
                self._audit(db, order.account_id, "billing_payment_settled", order.order_id, now)
            elif target != order.state:
                allowed = order.state == "PENDING" and target in {"FAILED", "CANCELLED"}
                if not allowed:
                    raise BillingError("invalid_order_transition", 409)
                db.execute(
                    "UPDATE billing_orders SET state=?,updated_at=? "
                    "WHERE order_id=? AND state='PENDING'",
                    (target, _iso(now), order.order_id),
                )
            fresh = db.execute(
                "SELECT order_id,quote_id,account_id,state,gateway,mode,checkout_ref,amount_minor,"
                "currency,created_at,updated_at FROM billing_orders WHERE order_id=?",
                (order.order_id,),
            ).fetchone()
            return self._order(fresh)

    def receipt(self, order_id: str) -> Receipt | None:
        row = self.connection.execute(
            "SELECT receipt_id,order_id,account_id,receipt_json,issued_at "
            "FROM billing_receipts WHERE order_id=?",
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[3])
        return Receipt(
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(value["plan_code"]),
            int(value["amount_minor"]),
            str(value["currency"]),
            _datetime(row[4]),
        )

    def current_entitlement(self, now: datetime) -> Entitlement:
        row = self.connection.execute(
            "SELECT entitlement_id,plan_code,features_json,student_limit,warning_quota,"
            "effective_at,"
            "expires_at,grace_until,source_order FROM entitlements WHERE effective_at<=? "
            "ORDER BY effective_at DESC,created_at DESC,rowid DESC LIMIT 1",
            (_iso(now),),
        ).fetchone()
        if row:
            entitlement = Entitlement(
                str(row[1]),
                frozenset(json.loads(row[2])),
                int(row[3]),
                int(row[4]),
                _datetime(row[5]),
                _datetime(row[6]),
                _datetime(row[7]),
                str(row[0]),
                str(row[8]) if row[8] is not None else None,
            )
            if entitlement.expires_at is None or now <= entitlement.expires_at:
                return entitlement
            if entitlement.grace_until is not None and now <= entitlement.grace_until:
                return entitlement
        free = PLANS["FREE"]
        return Entitlement(free.code, free.features, free.student_limit, free.warning_quota, None)

    def paid_value_remaining(self, entitlement: Entitlement, now: datetime) -> int:
        if (
            entitlement.source_order is None
            or entitlement.effective_at is None
            or entitlement.expires_at is None
            or now >= entitlement.expires_at
        ):
            return 0
        row = self.connection.execute(
            "SELECT amount_minor FROM billing_orders WHERE order_id=? AND state='PAID'",
            (entitlement.source_order,),
        ).fetchone()
        if row is None:
            return 0
        start = entitlement.effective_at.astimezone(UTC)
        end = entitlement.expires_at.astimezone(UTC)
        total_seconds = int((end - start).total_seconds())
        remaining_seconds = int((end - now).total_seconds())
        if total_seconds <= 0 or remaining_seconds <= 0:
            return 0
        return int(row[0]) * remaining_seconds // total_seconds

    def trial_used(self) -> bool:
        return (
            self.connection.execute(
                "SELECT 1 FROM entitlements WHERE plan_code='TRIAL' LIMIT 1"
            ).fetchone()
            is not None
        )

    def can_add_students(
        self, count: int, organization_id: str = "local-demo", *, now: datetime | None = None
    ) -> bool:
        if type(count) is not int or count < 1:
            return False
        binding = self.find_setting("billing.installation.organization")
        try:
            bound_organization = json.loads(binding)["organization_id"] if binding else None
        except (ValueError, KeyError, TypeError):
            return False
        if bound_organization != organization_id:
            return False
        instant = now or datetime.now(UTC)
        entitlement = self.current_entitlement(instant)
        active = self.connection.execute(
            "SELECT COUNT(*) FROM accounts WHERE role='student' AND disabled=0"
        ).fetchone()[0]
        return int(active) + count <= entitlement.student_limit

    def active_student_count(self) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM accounts WHERE role='student' AND disabled=0"
            ).fetchone()[0]
        )

    def current_month_assessment_count(self, now: datetime) -> int:
        start = now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = _add_months(start, 1)
        row = self.connection.execute(
            "SELECT COUNT(*) FROM responses WHERE created_at>=? AND created_at<?",
            (_iso(start), _iso(next_month)),
        ).fetchone()
        return int(row[0])

    def scheduled_entitlement(self, now: datetime) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT entitlement_id,plan_code,features_json,student_limit,warning_quota,"
            "effective_at,expires_at,grace_until,source_order FROM entitlements "
            "WHERE effective_at>? ORDER BY effective_at,created_at DESC,rowid DESC LIMIT 1",
            (_iso(now),),
        ).fetchone()
        if row is None:
            return None
        return {
            "entitlement_id": str(row[0]),
            "plan_code": str(row[1]),
            "features": tuple(sorted(json.loads(row[2]))),
            "student_limit": int(row[3]),
            "warning_quota": int(row[4]),
            "effective_at": _datetime(row[5]),
            "expires_at": _datetime(row[6]),
            "grace_until": _datetime(row[7]),
            "source_order": str(row[8]) if row[8] is not None else None,
        }

    def _audit(
        self, db: sqlite3.Connection, actor: str, action: str, object_id: str, now: datetime
    ) -> None:
        db.execute(
            "INSERT INTO audit(event_id,actor_id,action,object_id,recorded_at,reason) "
            "VALUES(?,?,?,?,?,NULL)",
            (uuid.uuid4().hex, actor, action, object_id, _iso(now)),
        )

    @staticmethod
    def assert_admin_session(
        db: sqlite3.Connection, token: str, actor_id: str, now: datetime
    ) -> None:
        try:
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        except (AttributeError, UnicodeEncodeError):
            raise BillingError("access_denied", 403) from None
        row = db.execute(
            "SELECT s.actor_id,s.role,s.idle_expires_at,s.absolute_expires_at,a.role,a.disabled "
            "FROM sessions s JOIN accounts a ON a.actor_id=s.actor_id WHERE s.token_digest=?",
            (digest,),
        ).fetchone()
        if (
            row is None
            or row[0] != actor_id
            or row[1] != "admin"
            or row[4] != "admin"
            or bool(row[5])
            or now >= _datetime(row[2])
            or now >= _datetime(row[3])
        ):
            raise BillingError("access_denied", 403)

    @staticmethod
    def _order(row: tuple[Any, ...]) -> Order:
        return Order(
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
            str(row[5]),
            str(row[6]) if row[6] is not None else None,
            int(row[7]),
            str(row[8]),
            _datetime(row[9]),
            _datetime(row[10]),
        )


def _add_months(value: datetime, months: int) -> datetime:
    import calendar

    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
