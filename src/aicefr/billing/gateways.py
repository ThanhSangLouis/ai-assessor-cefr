"""Payment gateways (D033, D035, D075): the sandbox inside the app.

Stripe is the one real gateway (`stripe_gateway`); VNPay and MoMo were removed
in D075. The sandbox stands in for a gateway's page where no money should
move: the browser is sent to its page with the order signed into the address,
and the result comes back signed to a return address and, separately, to the
notification address. A result is believed only when its signature checks out
and its amount is the order's (BR-33). Which gateways a deployment offers is
decided in `registry`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlencode

from aicefr.billing.payments import (
    Ack,
    Checkout,
    Incoming,
    OrderStatus,
    PaymentResult,
    digits,
    same_text,
)
from aicefr.practice.streak import LOCAL_TZ

# ---------------------------------------------------------------- sandbox

SANDBOX_OUTCOMES = {
    "paid": (OrderStatus.PAID, "Thanh toán thử thành công. Không có tiền thật nào được chuyển."),
    "failed": (OrderStatus.FAILED, "Thanh toán thử không thành công."),
    "cancelled": (OrderStatus.CANCELLED, "Bạn đã huỷ giao dịch thử."),
}
SANDBOX_FIELDS = ("order_id", "amount", "outcome", "ref", "at")


class SignedRedirect:
    """A gateway whose result comes back signed in a query string: the return
    address and the notification (a GET) carry the same signed fields, and the
    notification is answered with an RspCode. Subclasses provide `verify`."""

    def verify(self, params: Mapping[str, str]) -> PaymentResult | None:
        raise NotImplementedError

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        return None  # the return address carries the signed result

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        return self.verify(query)

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        return self.verify(message.query)

    def acknowledge(self, what: str) -> Ack:
        return signed_ack(what)


class SandboxGateway(SignedRedirect):
    """A gateway inside the app, for tests and demonstrations: no money moves.

    Its page lets the person pick the outcome. What it sends back is signed the
    way a real gateway signs, so the return page and the notification run the
    same checks against it that they run against VNPay. It must never be the
    gateway of a deployment that sells for real: anyone holding a checkout
    address can mark that order paid.
    """

    name = "sandbox"
    title = "Cổng thử"
    methods = "Trang thanh toán thử ngay trong ứng dụng"
    live = False
    note = "Chọn kết quả muốn thử trên trang của cổng; không có tiền thật nào được chuyển."

    def __init__(self, secret: bytes) -> None:
        self._secret = secret

    def _mac(self, text: str) -> str:
        return hmac.new(self._secret, text.encode("utf-8"), hashlib.sha256).hexdigest()

    def token(self, order_id: str, amount_vnd: int) -> str:
        """What the checkout address carries, so its page opens for that order only."""
        return self._mac(f"checkout|{order_id}|{amount_vnd}")[:32]

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
        query = urlencode({"t": self.token(order_id, amount_vnd)})
        return Checkout(f"/billing/sandbox/{order_id}?{query}")

    def result(self, order_id: str, amount_vnd: int, outcome: str, now: datetime) -> dict[str, str]:
        """The signed parameters the sandbox sends back, to the browser and to the notification."""
        if outcome not in SANDBOX_OUTCOMES:
            raise ValueError(outcome)
        params = {
            "order_id": order_id,
            "amount": str(amount_vnd),
            "outcome": outcome,
            "ref": "SB" + secrets.token_hex(5).upper(),
            "at": now.astimezone(LOCAL_TZ).strftime("%Y%m%d%H%M%S"),
        }
        params["sig"] = self._mac("|".join(params[k] for k in SANDBOX_FIELDS))
        return params

    def verify(self, params: Mapping[str, str]) -> PaymentResult | None:
        if any(k not in params for k in (*SANDBOX_FIELDS, "sig")):
            return None
        expected = self._mac("|".join(str(params[k]) for k in SANDBOX_FIELDS))
        if not same_text(expected, str(params["sig"])):
            return None
        if params["outcome"] not in SANDBOX_OUTCOMES or not digits(str(params["amount"])):
            return None
        status, message = SANDBOX_OUTCOMES[params["outcome"]]
        return PaymentResult(
            order_id=str(params["order_id"]),
            outcome=status,
            amount_vnd=int(params["amount"]),
            reference=str(params["ref"]),
            code=str(params["outcome"]),
            message=message,
            details={"pay_date": str(params["at"])},
        )


# What the sandbox's notification endpoint answers, by what happened to the
# order: the RspCode form the Vietnamese gateways answer with, which the
# sandbox kept when VNPay and MoMo were removed (D075).
SIGNED_ACK = {
    "ok": ("00", "Confirm Success"),
    "not_found": ("01", "Order not found"),
    "already": ("02", "Order already confirmed"),
    "amount": ("04", "Invalid amount"),
    "signature": ("97", "Invalid signature"),
    "error": ("99", "Unknown error"),
}


def signed_ack(what: str) -> Ack:
    """Always HTTP 200: what happened is read from RspCode, not from the status."""
    code, message = SIGNED_ACK.get(what, SIGNED_ACK["error"])
    return Ack(200, {"RspCode": code, "Message": message})
