"""Authorized billing workflows; payment verification stays behind gateways."""

from __future__ import annotations

import calendar
import hashlib
import json
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from aicefr.auth.errors import AuthorizationError
from aicefr.billing.contracts import Order, Plan, Quote, Receipt
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS, get_plan
from aicefr.billing.quotes import quote_amount
from aicefr.contracts import ActorRole
from aicefr.storage.billing import BillingRepository

_IDEM_RE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")


def utc_now() -> datetime:
    return datetime.now(UTC)


def _live_configuration_requested(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in {"live", "live_mode"} and item not in (False, None, "", 0):
                return True
            if normalized in {"mode", "payment_mode"} and isinstance(item, str):
                if item.lower() == "live":
                    return True
            if _live_configuration_requested(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_live_configuration_requested(item) for item in value)
    return False


def _add_calendar_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class BillingService:
    def __init__(
        self,
        auth: Any,
        repository: BillingRepository,
        gateways: Any,
        licenses: Any,
        config: Mapping[str, Any] | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._auth = auth
        self._repository = repository
        self._gateways = gateways
        self._licenses = licenses
        if not callable(getattr(self._licenses, "apply_entitlement", None)):
            raise BillingError("license_installation_unavailable", 503)
        self._config = dict(config or {})
        self._clock = clock
        self.organization_id = self._repository.bind_organization(
            self._config.get("organization_id", "local-demo"), now=self._now()
        )
        # W5 deliberately has no live payment path, even when callers pass a live flag.
        self._live_locked = True

    def overview(self, token: str) -> dict[str, Any]:
        self._admin(token)
        now = self._now()
        entitlement = self._repository.current_entitlement(now)
        scheduled = self._repository.scheduled_entitlement(now)
        seat_count = self._repository.active_student_count()
        assessment_count = self._repository.current_month_assessment_count(now)
        quota = entitlement.warning_quota
        threshold_80 = (quota * 80 + 99) // 100
        warnings = []
        if quota > 0 and assessment_count >= threshold_80:
            warnings.append(
                {
                    "code": "assessment_usage_80_percent",
                    "used": assessment_count,
                    "quota": quota,
                }
            )
        if quota > 0 and assessment_count >= quota:
            warnings.append(
                {
                    "code": "assessment_usage_100_percent",
                    "used": assessment_count,
                    "quota": quota,
                }
            )
        if entitlement.plan_code == "FREE":
            entitlement_state = "FREE"
        elif entitlement.expires_at is not None and now > entitlement.expires_at:
            entitlement_state = (
                "GRACE"
                if entitlement.grace_until is not None and now <= entitlement.grace_until
                else "FREE"
            )
        else:
            entitlement_state = "ACTIVE"
        plans = tuple(self._public_plan(p) for p in self._repository.list_plans())
        status = self._gateways.status()
        if not isinstance(status, (dict, tuple, list)):
            status = {"internal": {"enabled": True, "mode": "sandbox"}}
        return {
            "plans": plans,
            "entitlement": {
                "plan_code": entitlement.plan_code,
                "features": tuple(sorted(entitlement.features)),
                "student_limit": entitlement.student_limit,
                "warning_quota": entitlement.warning_quota,
                "effective_at": entitlement.effective_at,
                "expires_at": entitlement.expires_at,
                "grace_until": entitlement.grace_until,
                "status": entitlement_state,
            },
            "scheduled_entitlement": scheduled,
            "usage": {
                "active_students": seat_count,
                "student_limit": entitlement.student_limit,
                "students_remaining": max(0, entitlement.student_limit - seat_count),
                "assessments_current_month": assessment_count,
                "assessment_warning_quota": quota,
                "warnings": warnings,
                "research_exclusion_enabled": False,
            },
            "gateways": status,
            "sandbox": True,
        }

    def quote(self, token: str, plan_code: str, months: int, idempotency_key: str) -> Quote:
        actor = self._admin(token)
        now = self._now()
        key_hash = self._idempotency_digest(idempotency_key)
        plan = get_plan(plan_code)
        if plan.code == "TRIAL" and months != 1:
            raise BillingError("invalid_billing_term")
        params_hash = self._hash_json(
            {"actor_id": actor.actor_id, "plan_code": plan.code, "months": months}
        )
        setting = self._repository.find_setting(f"billing.quote.{key_hash}")
        if setting:
            try:
                saved = json.loads(setting)
                if saved.get("input_hash") != params_hash:
                    raise BillingError("idempotency_key_reused", 409)
                quote = self._repository.get_quote(saved["quote_id"])
                if quote is None:
                    raise BillingError("quote_unavailable", 409)
                return quote
            except (ValueError, KeyError, TypeError) as exc:
                raise BillingError("idempotency_record_invalid", 500) from exc
        if plan.code == "TRIAL" and self._repository.trial_used():
            raise BillingError("trial_already_used", 409)
        current = self._repository.current_entitlement(now)
        credit = 0
        rank = {"FREE": 0, "TRIAL": 1, "STANDARD": 2, "ADVANCED": 3}
        if (
            plan.monthly_minor > 0
            and rank[plan.code] > rank.get(current.plan_code, 0)
            and current.expires_at is not None
        ):
            current_plan = PLANS[current.plan_code]
            if plan.monthly_minor > current_plan.monthly_minor:
                credit = self._repository.paid_value_remaining(current, now)
        effective_at = now
        if (
            current.expires_at is not None
            and now < current.expires_at
            and rank[plan.code] <= rank.get(current.plan_code, 0)
        ):
            effective_at = current.expires_at
        if plan.code == "FREE":
            ends_at = None
            change_kind = "free"
        elif plan.code == "TRIAL":
            ends_at = effective_at + timedelta(days=30)
            change_kind = "trial"
        else:
            ends_at = _add_calendar_months(effective_at, months)
            if current.plan_code == "FREE":
                change_kind = "initial"
            elif rank[plan.code] > rank.get(current.plan_code, 0):
                change_kind = "upgrade"
            elif rank[plan.code] < rank.get(current.plan_code, 0):
                change_kind = "downgrade"
            else:
                change_kind = "renewal"
        context = {
            "entitlement_snapshot": self._entitlement_snapshot(current),
            "credit_basis_minor": credit,
            "effective_at": effective_at.isoformat(),
            "ends_at": ends_at.isoformat() if ends_at is not None else None,
            "change_kind": change_kind,
        }
        subtotal, discount, applied_credit, total = quote_amount(
            plan, months, current_credit_minor=credit
        )
        quote = Quote(
            quote_id=uuid.uuid4().hex,
            account_id=actor.actor_id,
            plan_code=plan.code,
            months=months,
            subtotal_minor=subtotal,
            discount_minor=discount,
            credit_minor=applied_credit,
            total_minor=total,
            currency=plan.currency,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
            context_json=json.dumps(context, sort_keys=True, separators=(",", ":")),
            effective_at=effective_at,
            ends_at=ends_at,
            change_kind=change_kind,
        )
        self._repository.save_quote_with_idempotency(
            quote, key_hash=key_hash, input_hash=params_hash, token=token
        )
        saved = self._repository.find_setting(f"billing.quote.{key_hash}")
        if saved:
            persisted = self._repository.get_quote(json.loads(saved)["quote_id"])
            if persisted is not None:
                return persisted
        return quote

    def create_order(self, token: str, quote_id: str, gateway: str, idempotency_key: str) -> Order:
        actor = self._admin(token)
        now = self._now()
        key_hash = self._idempotency_digest(idempotency_key)
        quote = self._repository.get_quote(quote_id)
        if quote is None or quote.account_id != actor.actor_id:
            raise BillingError("quote_unavailable", 404)
        existing = self._repository.get_order_idempotency(key_hash)
        expected_gateway = gateway if quote.total_minor > 0 else "sandbox"
        if existing:
            if existing.quote_id != quote_id or existing.gateway != expected_gateway:
                raise BillingError("idempotency_key_reused", 409)
            if existing.checkout_ref is None and existing.state == "PENDING":
                if now >= quote.expires_at:
                    raise BillingError("quote_expired", 409)
                try:
                    expected_snapshot = json.loads(quote.context_json)["entitlement_snapshot"]
                except (ValueError, KeyError, TypeError) as exc:
                    raise BillingError("quote_invalid", 409) from exc
                current_snapshot = self._entitlement_snapshot(
                    self._repository.current_entitlement(now)
                )
                if expected_snapshot != current_snapshot:
                    raise BillingError("quote_stale", 409)
                return self._open_checkout(existing, quote, token, actor.actor_id)
            return existing
        if now >= quote.expires_at:
            raise BillingError("quote_expired", 409)
        try:
            expected_snapshot = json.loads(quote.context_json)["entitlement_snapshot"]
        except (ValueError, KeyError, TypeError) as exc:
            raise BillingError("quote_invalid", 409) from exc
        current_snapshot = self._entitlement_snapshot(self._repository.current_entitlement(now))
        if expected_snapshot != current_snapshot:
            raise BillingError("quote_stale", 409)
        plan = get_plan(quote.plan_code)
        if plan.code == "TRIAL" and self._repository.trial_used():
            raise BillingError("trial_already_used", 409)
        if self._live_locked and _live_configuration_requested(self._config):
            raise BillingError("live_payment_disabled", 503)
        mode = "sandbox"
        if quote.total_minor > 0:
            status = self._gateways.status(gateway)
            if (
                not isinstance(status, Mapping)
                or not status.get("enabled")
                or not status.get("ready")
            ):
                raise BillingError("gateway_unavailable", 503)
            mode = str(status.get("mode", "sandbox"))
            if mode != "test" and mode != "sandbox":
                raise BillingError("live_payment_disabled", 503)
        order = self._repository.create_order(
            order_id=uuid.uuid4().hex,
            quote=quote,
            gateway=gateway if quote.total_minor > 0 else "sandbox",
            mode=mode,
            idempotency_hash=key_hash,
            now=now,
            token=token,
            expected_entitlement_snapshot=expected_snapshot,
        )
        if quote.total_minor == 0:
            checkout = f"zero-{order.order_id}"
            order = self._repository.set_checkout(
                order.order_id, checkout, now, token=token, actor_id=actor.actor_id
            )
            event = {
                "event_id": f"zero-{order.order_id}",
                "order_id": order.order_id,
                "checkout_id": checkout,
                "amount": 0,
                "currency": quote.currency,
                "status": "paid",
                "mode": "sandbox",
                "gateway": "sandbox",
                "payload_hash": hashlib.sha256(
                    f"aicefr:zero:v1:{order.order_id}".encode("ascii")
                ).hexdigest(),
                "signature_valid": True,
                "occurred_at": now,
            }
            return self._repository.settle(
                event,
                now=now,
                apply_entitlement=self._apply_entitlement,
                organization_id=self.organization_id,
                admin_token=token,
                admin_actor_id=actor.actor_id,
            )
        return self._open_checkout(order, quote, token, actor.actor_id)

    def _open_checkout(self, order: Order, quote: Quote, token: str, actor_id: str) -> Order:
        result = self._gateways.create_session(
            order.gateway,
            {
                "order_id": order.order_id,
                "amount": order.amount_minor,
                "currency": order.currency,
                "mode": order.mode,
                "idempotency_key": order.order_id,
            },
        )
        if not isinstance(result, Mapping):
            raise BillingError("gateway_unavailable", 503)
        if result.get("gateway") != order.gateway or result.get("mode") != order.mode:
            raise BillingError("gateway_binding_mismatch", 503)
        checkout_ref = result.get("checkout_id")
        if not isinstance(checkout_ref, str):
            raise BillingError("gateway_unavailable", 503)
        return self._repository.set_checkout(
            order.order_id, checkout_ref, self._now(), token=token, actor_id=actor_id
        )

    def settle_sandbox(
        self, token: str, order_id: str, outcome: str, idempotency_key: str
    ) -> Order:
        actor = self._admin(token)
        self._idempotency_digest(idempotency_key)
        if outcome not in {"paid", "failed", "pending", "cancelled"}:
            raise BillingError("invalid_payment_outcome")
        order = self._repository.get_order(order_id)
        if order is None:
            raise BillingError("order_unavailable", 404)
        if order.mode not in {"sandbox", "test"}:
            raise BillingError("live_payment_disabled", 503)
        gateway = self._gateways.get(order.gateway)
        builder = getattr(gateway, "sandbox_event", None)
        if not callable(builder):
            raise BillingError("sandbox_settlement_unavailable", 503)
        event = builder(order=order, outcome=outcome, idempotency_key=idempotency_key)
        return self._repository.settle(
            event,
            now=self._now(),
            apply_entitlement=self._apply_entitlement,
            organization_id=self.organization_id,
            admin_token=token,
            admin_actor_id=actor.actor_id,
            idempotency_key_hash=self._idempotency_digest(idempotency_key),
        )

    def handle_event(
        self,
        gateway: str,
        payload: bytes | str | Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        channel: str = "webhook",
    ) -> Order:
        if channel not in {"webhook", "return"}:
            raise BillingError("invalid_payment_channel")
        try:
            event = self._gateways.verify_event(gateway, payload, headers, channel)
        except BillingError:
            raise
        except Exception as exc:
            raise BillingError("invalid_payment_event", 422) from exc
        if not isinstance(event, Mapping):
            raise BillingError("invalid_payment_event")
        order = self._repository.settle(
            event,
            now=self._now(),
            apply_entitlement=self._apply_entitlement,
            organization_id=self.organization_id,
        )
        return order

    def list_orders(self, token: str) -> tuple[Order, ...]:
        self._admin(token)
        return self._repository.list_orders()

    def receipt(self, token: str, order_id: str) -> Receipt:
        self._admin(token)
        order = self._repository.get_order(order_id)
        if order is None:
            raise BillingError("order_unavailable", 404)
        receipt = self._repository.receipt(order_id)
        if receipt is None:
            raise BillingError("receipt_unavailable", 404)
        return receipt

    def cancel_order(self, token: str, order_id: str, idempotency_key: str) -> Order:
        actor = self._admin(token)
        key_hash = self._idempotency_digest(idempotency_key)
        order = self._repository.get_order(order_id)
        if order is None:
            raise BillingError("order_unavailable", 404)
        return self._repository.cancel_order_idempotent(
            order_id, key_hash, actor.actor_id, self._now(), token
        )

    def can_add_students(self, count: int) -> bool:
        return self._repository.can_add_students(count, self.organization_id, now=self._now())

    def _apply_entitlement(self, db: Any, **values: Any) -> None:
        self._licenses.apply_entitlement(db, **values)

    def _admin(self, token: str):
        try:
            actor = self._auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
        except AuthorizationError as exc:
            raise BillingError("access_denied", 403) from exc
        if actor.role is not ActorRole.ADMIN:
            raise BillingError("access_denied", 403)
        return actor

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise BillingError("timezone_required", 500)
        return now.astimezone(UTC)

    @staticmethod
    def _idempotency_digest(key: str) -> str:
        if (
            not isinstance(key, str)
            or not 8 <= len(key) <= 128
            or any(ch not in _IDEM_RE for ch in key)
        ):
            raise BillingError("invalid_idempotency_key")
        return hashlib.sha256(b"aicefr:billing-idempotency:v1:" + key.encode("ascii")).hexdigest()

    @staticmethod
    def _hash_json(value: Mapping[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _public_plan(plan: Plan) -> dict[str, Any]:
        return {
            "code": plan.code,
            "title": plan.title,
            "monthly_minor": plan.monthly_minor,
            "currency": plan.currency,
            "student_limit": plan.student_limit,
            "warning_quota": plan.warning_quota,
            "features": tuple(sorted(plan.features)),
            "sandbox": True,
        }

    @staticmethod
    def _entitlement_snapshot(entitlement: Any) -> dict[str, Any]:
        return {
            "entitlement_id": entitlement.entitlement_id,
            "plan_code": entitlement.plan_code,
            "source_order": entitlement.source_order,
            "effective_at": (
                entitlement.effective_at.astimezone(UTC).isoformat()
                if entitlement.effective_at is not None
                else None
            ),
            "expires_at": (
                entitlement.expires_at.astimezone(UTC).isoformat()
                if entitlement.expires_at is not None
                else None
            ),
        }
