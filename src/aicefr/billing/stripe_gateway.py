"""Stripe Checkout as a payment gateway (D035).

Stripe works the other way round from VNPay. Nothing is signed into the
browser's address: this system first asks Stripe's API for a Checkout Session
(the amount in dong, the order's id as `client_reference_id`) and sends the
browser to the page Stripe answers with. Afterwards two things can say how it
went, and both are checked before anything is believed:

* the browser comes back with the session's id in the address. That id is a
  claim, not a proof, so the session is read back from Stripe's API with the
  secret key, and its own `payment_status`, amount and currency decide;
* Stripe's server posts an event to the webhook address. The event is believed
  only when the `Stripe-Signature` header is an HMAC-SHA256 of its exact bytes
  under the endpoint's signing secret, made within the last five minutes.

Test mode (`sk_test_…`) is Stripe's sandbox: the same API and pages, test card
numbers, no money. A live key moves real money and is refused unless the
deployment says so (`AICEFR_PAYMENTS_LIVE`, see `registry`).

The payer types the card on Stripe's page, never here; what is kept is the
session's and the payment's ids, never the payer's email, name or card (BR-32).
The standard library is enough to call the API, so there is no Stripe SDK.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from urllib.parse import urlencode

from aicefr.billing.payments import (
    Ack,
    Checkout,
    GatewayError,
    Incoming,
    OrderStatus,
    PaymentResult,
    notify_status,
    same_text,
)
from aicefr.billing.transport import Transport, Unreachable, https

API = "https://api.stripe.com/v1"
# How old a signed event may be: Stripe's own libraries allow five minutes.
TOLERANCE_S = 300
# Stripe keeps a Checkout Session open for 30 minutes at least; one more for a
# server clock a little ahead of Stripe's.
SESSION_MINUTES = 31
SESSION_ID = re.compile(r"cs_(test|live)_[A-Za-z0-9]{1,250}")
# The events that speak of a Checkout Session's payment. None: read the
# session's own payment_status (paid, or not yet for a slower payment method).
EVENTS: dict[str, OrderStatus | None] = {
    "checkout.session.completed": None,
    "checkout.session.async_payment_succeeded": OrderStatus.PAID,
    "checkout.session.async_payment_failed": OrderStatus.FAILED,
    "checkout.session.expired": OrderStatus.CANCELLED,
}
MESSAGES = {
    OrderStatus.PAID: "Stripe xác nhận đã thanh toán.",
    OrderStatus.FAILED: "Stripe báo khoản thanh toán không thành công.",
    OrderStatus.CANCELLED: "Phiên thanh toán của Stripe đã hết hạn mà chưa được trả.",
    OrderStatus.PENDING: "Stripe chưa xác nhận khoản thanh toán này.",
}
# Why Stripe would not open a session, in the administrator's words.
ERRORS = {
    "amount_too_small": (
        "Số tiền nhỏ hơn mức tối thiểu Stripe nhận cho một lần thanh toán (khoảng 0,50 USD); "
        "hãy chọn cổng khác."
    ),
    "amount_too_large": "Số tiền vượt mức tối đa Stripe nhận cho một lần thanh toán.",
    "api_key_expired": "Khoá bí mật Stripe đã hết hạn.",
}
UNREACHABLE = "Không kết nối được Stripe; thử lại sau ít phút."
STATUS_ERRORS = {
    401: "Khoá bí mật Stripe không hợp lệ hoặc đã bị thu hồi.",
    403: "Khoá Stripe không có quyền tạo phiên thanh toán (Checkout Sessions).",
    429: "Stripe đang giới hạn số yêu cầu; thử lại sau ít phút.",
}


class StripeGateway:
    """Stripe Checkout through its HTTP API and secret key; events through a signed webhook."""

    name = "stripe"
    title = "Stripe"
    methods = "Thẻ quốc tế Visa, Mastercard, JCB"

    def __init__(self, secret_key: str, webhook_secret: str = "", transport: Transport = https):
        if not secret_key.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
            raise ValueError("khoá bí mật Stripe phải bắt đầu bằng sk_test_ hoặc sk_live_")
        if webhook_secret and not webhook_secret.startswith("whsec_"):
            raise ValueError("khoá ký webhook Stripe phải bắt đầu bằng whsec_")
        self.live = secret_key[3:8] == "live_"
        if self.live and not webhook_secret:
            # Without the webhook, a payer who closes the tab before coming back
            # pays without the plan being installed: tolerable in test mode only.
            raise ValueError("Stripe chạy thật cần khoá ký webhook (whsec_…)")
        self._key = secret_key
        self._webhook_secret = webhook_secret.encode("utf-8")
        self._send = transport
        self.note = (
            ""
            if self.live
            else "Chế độ thử của Stripe: thẻ 4242 4242 4242 4242, hạn bất kỳ trong tương lai, "
            "CVC bất kỳ."
        )

    # ------------------------------------------------------------ the API

    def _call(
        self, method: str, path: str, fields: dict[str, str] | None = None, key: str = ""
    ) -> dict:
        headers = {"Authorization": f"Bearer {self._key}"}
        body = None
        if fields is not None:
            body = urlencode(fields).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if key:
            # Sent twice by a retry, the same request opens one session, not two.
            headers["Idempotency-Key"] = key
        try:
            reply = self._send(method, API + path, headers, body)
        except Unreachable as e:
            raise GatewayError(UNREACHABLE, "unreachable") from e
        try:
            data = json.loads(reply.body or b"{}")
        except ValueError:
            data = None
        if not 200 <= reply.status < 300 or not isinstance(data, dict):
            error = data.get("error") if isinstance(data, dict) else None
            code = str((error or {}).get("code") or reply.status)
            raise GatewayError(_refusal(reply.status, code), code)
        return data

    def checkout(
        self,
        order_id: str,
        amount_vnd: int,
        description: str,
        return_url: str,
        notify_url: str,
        client_ip: str,
        now: datetime,
    ) -> Checkout:
        """Open a Checkout Session for the order and return its page.

        The dong has no minor unit, so the amount goes as it is. The order's id
        rides in `client_reference_id` and the metadata, which is how a webhook
        event finds its order. Leaving Stripe's page without paying comes back
        with `left=1`: nothing is settled then, the session simply expires.
        """
        fields = {
            "mode": "payment",
            "client_reference_id": order_id,
            "metadata[order_id]": order_id,
            "payment_intent_data[metadata][order_id]": order_id,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": "vnd",
            "line_items[0][price_data][unit_amount]": str(amount_vnd),
            "line_items[0][price_data][product_data][name]": description,
            "success_url": return_url + "?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": return_url + "?left=1",
            "expires_at": str(int((now + timedelta(minutes=SESSION_MINUTES)).timestamp())),
            "locale": "vi",
            "submit_type": "pay",
        }
        session = self._call("POST", "/checkout/sessions", fields, key=f"aicefr-{order_id}")
        url, session_id = session.get("url"), session.get("id")
        if (
            not isinstance(url, str)
            or not url.startswith("https://")
            or not isinstance(session_id, str)
        ):
            raise GatewayError("Stripe trả về một phiên thanh toán không dùng được.", "session")
        return Checkout(url, session_id)

    # ------------------------------------------------------------ results

    def _result(self, session: Mapping, outcome: OrderStatus | None) -> PaymentResult:
        metadata = session.get("metadata")
        order_id = session.get("client_reference_id") or (
            metadata.get("order_id") if isinstance(metadata, dict) else None
        )
        if outcome is None:
            if session.get("payment_status") == "paid":
                outcome = OrderStatus.PAID
            elif session.get("status") == "expired":
                outcome = OrderStatus.CANCELLED
            else:
                outcome = OrderStatus.PENDING
        amount = session.get("amount_total")
        if session.get("currency") != "vnd" or not isinstance(amount, int):
            amount = -1  # matches no order: settled as a wrong amount, never as paid
        intent = session.get("payment_intent")
        return PaymentResult(
            order_id=str(order_id or ""),
            outcome=outcome,
            amount_vnd=amount,
            reference=intent if isinstance(intent, str) else str(session.get("id", "")),
            code=str(session.get("payment_status", "")),
            message=MESSAGES[outcome],
            details={"session": str(session.get("id", ""))},
            checkout=str(session.get("id", "")),
        )

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        """The session id the address names: what Stripe is asked about, and only if it is ours."""
        return str(query.get("session_id", ""))

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        """Read the session the address names back from Stripe; None for an id that is not one.

        Raises GatewayError when Stripe cannot be asked: the payment may well
        have gone through, and the webhook will say so.
        """
        session_id = str(query.get("session_id", ""))
        if not SESSION_ID.fullmatch(session_id) or session_id.startswith("cs_live_") != self.live:
            return None
        return self._result(self._call("GET", f"/checkout/sessions/{session_id}"), None)

    def _signed(self, header: str, body: bytes, now: float) -> bool:
        """Stripe's scheme: `t=<unix time>,v1=<hex HMAC-SHA256 of "<t>.<body>">`, v1 repeatable."""
        stamp, signatures = "", []
        for part in header.split(","):
            key, _, value = part.strip().partition("=")
            if key == "t":
                stamp = value
            elif key == "v1":
                signatures.append(value)
        # A header may carry any latin-1 character: only plain digits are a time.
        if not (stamp.isascii() and stamp.isdigit() and len(stamp) <= 12) or not signatures:
            return False
        if abs(now - int(stamp)) > TOLERANCE_S:
            return False
        expected = hmac.new(
            self._webhook_secret, stamp.encode("ascii") + b"." + body, hashlib.sha256
        ).hexdigest()
        return any(same_text(expected, s) for s in signatures)

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        """A webhook event, if Stripe signed it; None otherwise.

        An authentic event that is not about a Checkout Session's payment comes
        back as a pending word for no order: acknowledged, and nothing changes.
        """
        header = message.headers.get("stripe-signature", "")
        if not self._webhook_secret or not self._signed(header, message.body, now.timestamp()):
            return None
        try:
            event = json.loads(message.body)
        except ValueError:
            return None
        if not isinstance(event, dict) or bool(event.get("livemode")) != self.live:
            return None
        kind = str(event.get("type", ""))
        data = event.get("data")
        session = data.get("object") if isinstance(data, dict) else None
        if (
            kind not in EVENTS
            or not isinstance(session, dict)
            or session.get("object") != "checkout.session"
        ):
            return PaymentResult("", OrderStatus.PENDING, 0, str(event.get("id", "")), kind, "")
        return self._result(session, EVENTS[kind])

    def acknowledge(self, what: str) -> Ack:
        """Stripe reads only the status: any 2xx is received, anything else is sent again."""
        return Ack(notify_status(what), {"received": what not in ("signature", "error")})


def _refusal(status: int, code: str) -> str:
    if code in ERRORS:
        return ERRORS[code]
    if status in STATUS_ERRORS:
        return STATUS_ERRORS[status]
    if status >= 500:
        return "Stripe đang gặp sự cố; thử lại sau ít phút."
    return f"Stripe không mở được phiên thanh toán (mã {code})."
