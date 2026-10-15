"""Bounded payment gateway adapters.

The default adapter is an in-process signed sandbox. Provider adapters only
use an explicitly injected transport; this module never creates a network
client or sends outbound traffic itself.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from aicefr.billing.errors import BillingError
from aicefr.billing.secrets import KeyRing

MAX_PAYLOAD = 65_536
EVENT_TOLERANCE_SECONDS = 300
KNOWN = frozenset({"sandbox", "stripe", "momo", "vnpay"})
_ENDPOINTS = {
    "stripe": "https://api.stripe.com/v1/checkout/sessions",
    "momo": "https://test-payment.momo.vn/v2/gateway/api/create",
    "vnpay": "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html",
}


class GatewayError(BillingError):
    """A provider-neutral, secret-safe adapter error."""

    def __init__(self, code: str = "gateway_invalid") -> None:
        self.code = code
        status_code = 503 if code in {"gateway_not_ready", "gateway_unavailable"} else 422
        if code in {"gateway_event_replayed", "gateway_mode_mismatch"}:
            status_code = 409
        super().__init__(code, status_code)


def _canonical(value: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise GatewayError("gateway_invalid_payload") from None
    if len(encoded) > MAX_PAYLOAD:
        raise GatewayError("gateway_payload_too_large")
    return encoded


def _strict_json(payload: bytes | str | Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    if isinstance(payload, Mapping):
        obj = dict(payload)
        raw = _canonical(obj)
    else:
        if isinstance(payload, str):
            try:
                raw = payload.encode("utf-8", "strict")
            except UnicodeError:
                raise GatewayError("gateway_invalid_payload") from None
        elif isinstance(payload, bytes):
            raw = payload
        else:
            raise GatewayError("gateway_invalid_payload")
        if len(raw) > MAX_PAYLOAD:
            raise GatewayError("gateway_payload_too_large")

        def pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise GatewayError("gateway_duplicate_field")
                result[key] = value
            return result

        try:
            obj = json.loads(
                raw.decode("utf-8", "strict"),
                object_pairs_hook=pairs_no_dupes,
                parse_constant=lambda _: (_ for _ in ()).throw(
                    GatewayError("gateway_invalid_payload")
                ),
            )
        except GatewayError:
            raise
        except (json.JSONDecodeError, UnicodeError, TypeError):
            raise GatewayError("gateway_invalid_payload") from None
        if not isinstance(obj, dict):
            raise GatewayError("gateway_invalid_payload")
    return obj, raw


def _text(value: Any, limit: int = 160) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise GatewayError("gateway_invalid_payload")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise GatewayError("gateway_invalid_payload")
    return value


def _integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GatewayError("gateway_invalid_amount")
    return value


def _timestamp(value: Any, *, millis: bool = False, clock: Callable[[], datetime]) -> datetime:
    if isinstance(value, bool):
        raise GatewayError("gateway_expired_event")
    if millis:
        if not isinstance(value, int) or value < 0:
            raise GatewayError("gateway_expired_event")
        try:
            result = datetime.fromtimestamp(value / 1000, tz=UTC)
        except (OverflowError, OSError, ValueError):
            raise GatewayError("gateway_expired_event") from None
    elif isinstance(value, int):
        try:
            result = datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError):
            raise GatewayError("gateway_expired_event") from None
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if result.tzinfo is None:
                raise ValueError
            result = result.astimezone(UTC)
        except (ValueError, OverflowError):
            raise GatewayError("gateway_expired_event") from None
    else:
        raise GatewayError("gateway_expired_event")
    delta = abs((clock().astimezone(UTC) - result).total_seconds())
    if delta > EVENT_TOLERANCE_SECONDS:
        raise GatewayError("gateway_expired_event")
    return result


def _headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    if headers is None:
        return {}
    if not isinstance(headers, Mapping) or len(headers) > 40:
        raise GatewayError("gateway_invalid_headers")
    result: dict[str, str] = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise GatewayError("gateway_invalid_headers")
        if len(name) > 100 or len(value) > 1024 or any(ord(c) < 32 for c in value):
            raise GatewayError("gateway_invalid_headers")
        normalized = name.lower()
        if normalized in result:
            raise GatewayError("gateway_duplicate_header")
        result[normalized] = value
    return result


def _safe_config(config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(config, Mapping) or len(config) > len(KNOWN):
        raise ValueError("invalid gateway configuration")
    result: dict[str, dict[str, Any]] = {}
    allowed = {
        "enabled",
        "mode",
        "test_secret_key",
        "webhook_secret",
        "access_key",
        "secret_key",
        "partner_code",
        "terminal_code",
        "hash_secret",
    }
    for gateway, settings in config.items():
        if gateway not in KNOWN - {"sandbox"} or not isinstance(settings, Mapping):
            raise ValueError("invalid gateway configuration")
        if set(settings) - allowed:
            raise ValueError("unknown gateway configuration")
        mode = settings.get("mode", "test")
        if mode != "test":
            # In particular, configuration cannot activate live payment.
            raise ValueError("live gateways are disabled")
        enabled = settings.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("invalid gateway configuration")
        copied = dict(settings)
        copied["mode"] = mode
        copied["enabled"] = enabled
        result[str(gateway)] = copied
    return result


class GatewayRegistry:
    """Safe registry for internal sandbox and explicitly configured test providers."""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        data_dir: Any = None,
        transport: Any = None,
        *,
        keyring: KeyRing | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = _safe_config({} if config is None else config)
        self._transport = transport
        self._clock = clock or (lambda: datetime.now(UTC))
        if keyring is None and data_dir is None:
            raise ValueError("data_dir is required when no keyring is supplied")
        self._keyring = keyring or KeyRing(data_dir)

    def status(self, gateway: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        names = [gateway] if gateway is not None else ["sandbox", "stripe", "momo", "vnpay"]
        rows = [self._status_one(name) for name in names]
        return rows[0] if gateway is not None else rows

    def _status_one(self, name: str) -> dict[str, Any]:
        if name not in KNOWN:
            raise GatewayError("gateway_unknown")
        if name == "sandbox":
            return {"gateway": name, "enabled": True, "mode": "sandbox", "ready": True}
        settings = self._config.get(name, {})
        credentials_ok = self._credentials_ok(name, settings)
        ready = bool(settings.get("enabled")) and credentials_ok and self._transport is not None
        reason = None
        if not settings.get("enabled"):
            reason = "disabled"
        elif not credentials_ok:
            reason = "test_configuration_incomplete"
        elif self._transport is None:
            reason = "mock_transport_required"
        return {
            "gateway": name,
            "enabled": bool(settings.get("enabled")),
            "mode": "test",
            "ready": ready,
            "reason": reason,
        }

    @staticmethod
    def _credentials_ok(name: str, settings: Mapping[str, Any]) -> bool:
        if name == "stripe":
            key, hook = settings.get("test_secret_key"), settings.get("webhook_secret")
            return (
                isinstance(key, str)
                and key.startswith("sk_test_")
                and 16 <= len(key) <= 256
                and isinstance(hook, str)
                and hook.startswith("whsec_")
                and 16 <= len(hook) <= 256
            )
        if name == "momo":
            return all(
                isinstance(settings.get(field), str) and 4 <= len(settings[field]) <= 256
                for field in ("access_key", "secret_key", "partner_code")
            )
        if name == "vnpay":
            return all(
                isinstance(settings.get(field), str) and 4 <= len(settings[field]) <= 256
                for field in ("terminal_code", "hash_secret")
            )
        return False

    def get(self, gateway: str) -> GatewayRegistry | None:
        if gateway not in KNOWN:
            raise GatewayError("gateway_unknown")
        status = self._status_one(gateway)
        return self if status["ready"] else None

    def sandbox_event(self, *, order: Any, outcome: str, idempotency_key: str) -> dict[str, Any]:
        """Build an internal, deterministic settlement event for local QA."""
        if outcome not in {"paid", "failed", "pending", "cancelled"}:
            raise GatewayError("gateway_invalid_outcome")
        try:
            order_id = _text(order.order_id, 128)
            gateway = _text(order.gateway, 32)
            checkout_id = _text(order.checkout_ref, 256)
            mode = _text(order.mode, 16)
            amount = _integer(order.amount_minor)
            currency = _text(order.currency, 3).upper()
            idem = _text(idempotency_key, 160)
        except AttributeError:
            raise GatewayError("gateway_invalid_order") from None
        if gateway not in KNOWN or mode not in {"sandbox", "test"}:
            raise GatewayError("gateway_mode_mismatch")
        when = self._clock().astimezone(UTC)
        event_id = (
            "test_"
            + hashlib.sha256(f"{gateway}\0{order_id}\0{idem}\0{outcome}".encode()).hexdigest()[:32]
        )
        payload = _canonical(
            {
                "event_id": event_id,
                "order_id": order_id,
                "checkout_id": checkout_id,
                "amount": amount,
                "currency": currency,
                "status": outcome,
                "mode": mode,
                "gateway": gateway,
                "idempotency_key": idem,
                "occurred_at": when.isoformat(),
            }
        )
        return {
            "event_id": event_id,
            "order_id": order_id,
            "checkout_id": checkout_id,
            "amount": amount,
            "currency": currency,
            "status": outcome,
            "mode": mode,
            "gateway": gateway,
            "idempotency_key": idem,
            "occurred_at": when,
            "payload_hash": hashlib.sha256(payload).hexdigest(),
            "signature_valid": True,
        }

    def create_session(self, gateway: str, order: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(order, Mapping):
            raise GatewayError("gateway_invalid_order")
        order_id = _text(order.get("order_id"), 128)
        amount = _integer(order.get("amount"))
        currency = _text(order.get("currency"), 3).upper()
        if len(currency) != 3 or amount <= 0:
            raise GatewayError("gateway_invalid_order")
        if gateway == "sandbox":
            checkout_id = "sbx_" + uuid.uuid4().hex
            return {
                "gateway": "sandbox",
                "mode": "sandbox",
                "checkout_id": checkout_id,
                "redirect_url": None,
            }
        status = self._status_one(gateway)
        if not status["ready"]:
            raise GatewayError("gateway_not_ready")
        return self._create_provider_session(gateway, order_id, amount, currency)

    def _create_provider_session(
        self, gateway: str, order_id: str, amount: int, currency: str
    ) -> dict[str, Any]:
        """Call only the supplied mock transport, never a library/network default."""
        settings = self._config[gateway]
        endpoint = _ENDPOINTS[gateway]
        payload: dict[str, Any]
        if gateway == "stripe":
            payload = {
                "mode": "payment",
                "client_reference_id": order_id,
                "metadata[order_id]": order_id,
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": str(amount),
                "line_items[0][price_data][product_data][name]": "AI Assessor sandbox plan",
                "line_items[0][quantity]": "1",
                "success_url": "https://example.invalid/billing/return",
                "cancel_url": "https://example.invalid/billing/cancel",
            }
            headers = {"Authorization": "Bearer " + settings["test_secret_key"]}
        elif gateway == "momo":
            request_id = uuid.uuid4().hex
            payload = {
                "partnerCode": settings["partner_code"],
                "accessKey": settings["access_key"],
                "requestId": request_id,
                "amount": str(amount),
                "orderId": order_id,
                "orderInfo": "AI Assessor sandbox plan",
                "redirectUrl": "https://example.invalid/billing/return",
                "ipnUrl": "https://example.invalid/billing/webhook",
                "requestType": "captureWallet",
                "extraData": "",
                "autoCapture": True,
                "lang": "vi",
            }
            payload["signature"] = _momo_signature(payload, settings["secret_key"])
            headers = {"Content-Type": "application/json; charset=UTF-8"}
        else:
            # VNPAY redirects are generated locally. This injected adapter
            # transport is deliberately only used to capture/fixture the URL.
            params = {
                "vnp_Version": "2.1.0",
                "vnp_Command": "pay",
                "vnp_TmnCode": settings["terminal_code"],
                "vnp_Amount": str(amount * 100),
                "vnp_CurrCode": currency,
                "vnp_TxnRef": order_id,
                "vnp_OrderInfo": "AI Assessor sandbox plan",
                "vnp_OrderType": "other",
                "vnp_Locale": "vn",
                "vnp_ReturnUrl": "https://example.invalid/billing/return",
                "vnp_CreateDate": self._clock()
                .astimezone(timezone(timedelta(hours=7)))
                .strftime("%Y%m%d%H%M%S"),
            }
            params["vnp_SecureHash"] = _vnpay_signature(params, settings["hash_secret"])
            payload = params
            headers = {}
        try:
            if callable(self._transport):
                response = self._transport(endpoint=endpoint, payload=payload, headers=headers)
            else:
                response = self._transport.post(
                    endpoint, data=payload, headers=headers, timeout=5, allow_redirects=False
                )
            if hasattr(response, "json"):
                response = response.json()
            if not isinstance(response, Mapping):
                raise GatewayError("gateway_unavailable")
        except GatewayError:
            raise
        except Exception:
            # Do not leak provider body, key, URL, or exception text.
            raise GatewayError("gateway_unavailable") from None
        if gateway == "stripe":
            checkout_id = response.get("id")
            redirect_url = response.get("url")
        elif gateway == "momo":
            checkout_id = response.get("requestId") or response.get("orderId")
            redirect_url = response.get("payUrl")
        else:
            checkout_id = response.get("vnp_TxnRef") or order_id
            redirect_url = response.get("redirect_url")
        checkout_id = _text(checkout_id, 256)
        expected_hosts = {
            "stripe": {"checkout.stripe.com"},
            "momo": {"test-payment.momo.vn"},
            "vnpay": {"sandbox.vnpayment.vn"},
        }[gateway]
        try:
            parsed_url = urlsplit(redirect_url) if isinstance(redirect_url, str) else None
        except ValueError:
            parsed_url = None
        if (
            parsed_url is None
            or parsed_url.scheme != "https"
            or parsed_url.hostname not in expected_hosts
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise GatewayError("gateway_unavailable")
        if len(redirect_url) > 4096:
            raise GatewayError("gateway_unavailable")
        return {
            "gateway": gateway,
            "mode": "test",
            "checkout_id": checkout_id,
            "redirect_url": redirect_url,
        }

    def sign_sandbox_event(self, event: Mapping[str, Any]) -> tuple[bytes, dict[str, str]]:
        """Create a signed internal callback fixture for local tests/demo only."""
        obj = dict(event)
        obj.setdefault("gateway", "sandbox")
        obj.setdefault("mode", "sandbox")
        obj.setdefault("occurred_at", self._clock().astimezone(UTC).isoformat())
        raw = _canonical(obj)
        return raw, {"X-Sandbox-Signature": self._keyring.sign_gateway_event(raw)}

    def verify_event(
        self,
        gateway: str,
        payload: bytes | str | Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
        channel: str = "webhook",
    ) -> dict[str, Any]:
        if gateway not in KNOWN:
            raise GatewayError("gateway_unknown")
        if channel not in {"webhook", "return", "sandbox"}:
            raise GatewayError("gateway_invalid_channel")
        hdrs = _headers(headers)
        if gateway in {"stripe", "momo", "vnpay"} and not self._status_one(gateway)["ready"]:
            raise GatewayError("gateway_not_ready")
        if gateway == "vnpay":
            return self._verify_vnpay(payload)
        obj, raw = _strict_json(payload)
        if gateway == "sandbox":
            signature = hdrs.get("x-sandbox-signature", "")
            if not self._keyring.verify_gateway_event(raw, signature):
                raise GatewayError("gateway_invalid_signature")
            when = _timestamp(obj.get("occurred_at"), clock=self._clock)
            result = self._normalize(obj, gateway, "sandbox", when)
            result["payload_hash"] = hashlib.sha256(raw).hexdigest()
            return result
        if gateway == "stripe":
            signature = hdrs.get("stripe-signature", "")
            match_t = re.search(r"(?:^|,)\s*t=(\d+)(?:,|$)", signature)
            signatures = re.findall(r"(?:^|,)\s*v1=([0-9a-fA-F]{64})(?:,|$)", signature)
            if not match_t or not signatures:
                raise GatewayError("gateway_invalid_signature")
            when = _timestamp(int(match_t.group(1)), clock=self._clock)
            secret = self._config.get("stripe", {}).get("webhook_secret", "")
            signed = match_t.group(1).encode("ascii") + b"." + raw
            expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
            if not any(hmac.compare_digest(expected, sig.lower()) for sig in signatures):
                raise GatewayError("gateway_invalid_signature")
            return self._normalize_stripe(obj, raw, when)
        return self._verify_momo(obj, raw)

    def _normalize(
        self, obj: Mapping[str, Any], gateway: str, mode: str, when: datetime
    ) -> dict[str, Any]:
        event_id = _text(obj.get("event_id"), 200)
        order_id = _text(obj.get("order_id"), 128)
        checkout_id = _text(obj.get("checkout_id"), 256)
        amount = _integer(obj.get("amount"))
        currency = _text(obj.get("currency"), 3).upper()
        status = _text(obj.get("status"), 16).lower()
        if len(currency) != 3 or status not in {"paid", "failed", "pending", "cancelled"}:
            raise GatewayError("gateway_invalid_payload")
        payload_gateway = obj.get("gateway", gateway)
        payload_mode = obj.get("mode", mode)
        if payload_gateway != gateway or payload_mode != mode:
            raise GatewayError("gateway_mode_mismatch")
        idem = obj.get("idempotency_key")
        return {
            "event_id": event_id,
            "order_id": order_id,
            "checkout_id": checkout_id,
            "amount": amount,
            "currency": currency,
            "status": status,
            "mode": mode,
            "gateway": gateway,
            "idempotency_key": _text(idem, 160) if idem is not None else None,
            "occurred_at": when,
            "signature_valid": True,
        }

    def _normalize_stripe(
        self, obj: Mapping[str, Any], raw: bytes, when: datetime
    ) -> dict[str, Any]:
        data = obj.get("data")
        session = data.get("object") if isinstance(data, Mapping) else None
        if not isinstance(session, Mapping):
            raise GatewayError("gateway_invalid_payload")
        if obj.get("livemode") is not False or session.get("livemode") is not False:
            raise GatewayError("gateway_mode_mismatch")
        metadata = session.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        order_id = session.get("client_reference_id") or metadata.get("order_id")
        checkout_id = session.get("id")
        payment_status = session.get("payment_status")
        event_type = obj.get("type")
        status = (
            "paid"
            if payment_status == "paid"
            and event_type
            in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
            else "failed"
            if event_type == "checkout.session.async_payment_failed"
            else "pending"
        )
        event = {
            "event_id": obj.get("id"),
            "order_id": order_id,
            "checkout_id": checkout_id,
            "amount": session.get("amount_total"),
            "currency": session.get("currency"),
            "status": status,
            "gateway": "stripe",
            "mode": "test",
            "idempotency_key": metadata.get("idempotency_key"),
        }
        if event["mode"] != "test":
            raise GatewayError("gateway_mode_mismatch")
        result = self._normalize(event, "stripe", "test", when)
        result["payload_hash"] = hashlib.sha256(raw).hexdigest()
        return result

    def _verify_momo(self, obj: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
        settings = self._config.get("momo", {})
        if not self._credentials_ok("momo", settings):
            raise GatewayError("gateway_not_ready")
        supplied = obj.get("signature")
        expected = _momo_signature(
            obj, settings["secret_key"], response=True, access_key=settings["access_key"]
        )
        if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied.lower()):
            raise GatewayError("gateway_invalid_signature")
        if obj.get("partnerCode") != settings["partner_code"]:
            raise GatewayError("gateway_mode_mismatch")
        when = _timestamp(obj.get("responseTime"), millis=True, clock=self._clock)
        code = obj.get("resultCode")
        if isinstance(code, bool) or not isinstance(code, int):
            raise GatewayError("gateway_invalid_payload")
        event = {
            "event_id": str(obj.get("transId") or obj.get("requestId") or ""),
            "order_id": obj.get("orderId"),
            "checkout_id": obj.get("requestId") or obj.get("orderId"),
            "amount": obj.get("amount"),
            "currency": "VND",
            "status": "paid"
            if code == 0
            else "pending"
            if code in {7000, 7002, 9000}
            else "failed",
            "gateway": "momo",
            "mode": "test",
            "idempotency_key": None,
        }
        result = self._normalize(event, "momo", "test", when)
        result["payload_hash"] = hashlib.sha256(raw).hexdigest()
        return result

    def _verify_vnpay(self, payload: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
        settings = self._config.get("vnpay", {})
        if not self._credentials_ok("vnpay", settings):
            raise GatewayError("gateway_not_ready")
        if isinstance(payload, Mapping):
            obj = dict(payload)
            raw = _canonical(obj)
        elif isinstance(payload, bytes):
            raw = payload
            if len(raw) > MAX_PAYLOAD:
                raise GatewayError("gateway_payload_too_large")
            try:
                pairs = parse_qsl(raw.decode("ascii"), keep_blank_values=True, max_num_fields=80)
            except (UnicodeError, ValueError):
                raise GatewayError("gateway_invalid_payload") from None
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise GatewayError("gateway_duplicate_field")
                obj[key] = value
        elif isinstance(payload, str):
            try:
                return self._verify_vnpay(payload.encode("ascii", "strict"))
            except UnicodeError:
                raise GatewayError("gateway_invalid_payload") from None
        else:
            raise GatewayError("gateway_invalid_payload")
        if len(obj) > 80 or any(not isinstance(k, str) or len(k) > 100 for k in obj):
            raise GatewayError("gateway_invalid_payload")
        supplied = obj.get("vnp_SecureHash")
        expected = _vnpay_signature(obj, settings["hash_secret"])
        if not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied.lower()):
            raise GatewayError("gateway_invalid_signature")
        if obj.get("vnp_TmnCode") != settings["terminal_code"]:
            raise GatewayError("gateway_mode_mismatch")
        timestamp = obj.get("vnp_PayDate") or obj.get("vnp_CreateDate")
        try:
            # VNPAY v2.1.0 timestamps use GMT+7.
            when = (
                datetime.strptime(str(timestamp), "%Y%m%d%H%M%S")
                .replace(tzinfo=timezone(timedelta(hours=7)))
                .astimezone(UTC)
            )
        except (TypeError, ValueError):
            raise GatewayError("gateway_expired_event") from None
        # Historical VNPAY callbacks can arrive after a day boundary; the
        # billing service independently checks the local order/quote expiry.
        if abs((self._clock().astimezone(UTC) - when).total_seconds()) > 86_400:
            raise GatewayError("gateway_expired_event")
        status_codes = [
            obj[field] for field in ("vnp_ResponseCode", "vnp_TransactionStatus") if field in obj
        ]
        if not status_codes:
            raise GatewayError("gateway_invalid_payload")
        status_code = "00" if all(code == "00" for code in status_codes) else "failed"
        raw_amount = obj.get("vnp_Amount")
        if (
            not isinstance(raw_amount, str)
            or not raw_amount.isascii()
            or not raw_amount.isdigit()
            or len(raw_amount) > 15
        ):
            raise GatewayError("gateway_invalid_amount")
        amount_minor = int(raw_amount)
        if amount_minor <= 0 or amount_minor % 100:
            raise GatewayError("gateway_invalid_amount")
        if obj.get("vnp_CurrCode") != "VND":
            raise GatewayError("gateway_currency_mismatch")
        event = {
            "event_id": obj.get("vnp_TransactionNo") or obj.get("vnp_TxnRef"),
            "order_id": obj.get("vnp_TxnRef"),
            "checkout_id": obj.get("vnp_TxnRef"),
            "amount": amount_minor // 100,
            "currency": "VND",
            "status": "paid" if status_code == "00" else "failed",
            "gateway": "vnpay",
            "mode": "test",
            "idempotency_key": None,
        }
        result = self._normalize(event, "vnpay", "test", when)
        result["payload_hash"] = hashlib.sha256(raw).hexdigest()
        return result


def _momo_signature(
    fields: Mapping[str, Any],
    secret: str,
    *,
    response: bool = False,
    access_key: str | None = None,
) -> str:
    if response:
        names = (
            "accessKey",
            "amount",
            "extraData",
            "message",
            "orderId",
            "orderInfo",
            "orderType",
            "partnerCode",
            "payType",
            "requestId",
            "responseTime",
            "resultCode",
            "transId",
        )
    else:
        names = (
            "accessKey",
            "amount",
            "extraData",
            "ipnUrl",
            "orderId",
            "orderInfo",
            "partnerCode",
            "redirectUrl",
            "requestId",
            "requestType",
        )
    values = {
        name: access_key if name == "accessKey" and access_key is not None else fields.get(name, "")
        for name in names
    }
    message = "&".join(f"{name}={values[name]}" for name in names)
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _vnpay_signature(fields: Mapping[str, Any], secret: str) -> str:
    from urllib.parse import quote_plus

    items = sorted(
        (key, str(value))
        for key, value in fields.items()
        if key not in {"vnp_SecureHash", "vnp_SecureHashType"}
    )
    message = "&".join(f"{key}={quote_plus(value, safe='')}" for key, value in items)
    return hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha512).hexdigest()
