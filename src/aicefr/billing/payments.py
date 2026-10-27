"""Orders and what a gateway says about them (D033, D035).

An order moves once: pending, then paid, failed or cancelled. A pending order
that nobody paid within `PENDING_MINUTES` expires, but a payment that still
arrives for it is honoured -- the money has moved. Every later word about an
order already settled changes nothing, which is what makes it safe for the
browser's return and the gateway's own notification to report the same result
in either order.

The other types here are what passes between the service and a gateway
adapter (`aicefr.ports.PaymentGateway`): where to send the payer (`Checkout`),
a message from the gateway's server as it arrived (`Incoming`), the answer that
server expects (`Ack`), and the error of a gateway that would not open a
payment (`GatewayError`).
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


ORDER_STATUS_NAMES = {
    OrderStatus.PENDING: "Chờ thanh toán",
    OrderStatus.PAID: "Đã thanh toán",
    OrderStatus.FAILED: "Không thành công",
    OrderStatus.CANCELLED: "Đã huỷ",
    OrderStatus.EXPIRED: "Hết hạn chờ",
}
PENDING_MINUTES = 15
SETTLEABLE = frozenset({OrderStatus.PENDING, OrderStatus.EXPIRED})


@dataclass(frozen=True)
class PaymentResult:
    """A gateway's signed word about one order."""

    order_id: str
    # PAID, FAILED or CANCELLED; PENDING when the gateway has no final word yet
    # (Stripe before an asynchronous payment clears, MoMo while the payer
    # confirms in the app). A pending word is kept, and changes nothing.
    outcome: OrderStatus
    amount_vnd: int
    reference: str  # the gateway's transaction number
    code: str  # the gateway's own result code, kept for reconciliation
    message: str  # what the result page tells the payer
    # Bank code, pay date, card type: what reconciliation needs, never a card
    # number or a name (BR-32).
    details: Mapping[str, str] = field(default_factory=dict)
    # The gateway's id of the checkout this result is about, when it has one
    # (Stripe's session, MoMo's request); must be the one the order opened.
    checkout: str = ""


class GatewayError(Exception):
    """A gateway that would not open a payment: it refused, or could not be reached.

    `str(e)` is the sentence the administrator reads, in Vietnamese; `code` is
    the gateway's own, kept with the order for reconciliation.
    """

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Checkout:
    """Where to send the payer's browser, and the gateway's own id for the payment, if any."""

    url: str
    reference: str = ""  # Stripe's Checkout Session id; empty for VNPay and the sandbox


@dataclass(frozen=True)
class Incoming:
    """A message from a gateway's server, as it arrived."""

    query: Mapping[str, str]
    headers: Mapping[str, str]  # names in lower case
    body: bytes = b""


@dataclass(frozen=True)
class Ack:
    """The answer a gateway's server expects to a notification."""

    status: int
    body: dict | None = None  # None: no body (MoMo expects 204 No Content)


def same_text(expected: str, received: str) -> bool:
    """Constant-time equality of a computed signature and one received.

    False, not an exception, for text that is not ASCII: a header or a field
    from outside can hold any character, and `hmac.compare_digest` refuses
    non-ASCII strings with a TypeError.
    """
    return received.isascii() and hmac.compare_digest(expected, received)


def digits(text: str) -> bool:
    """ASCII digits only: '²'.isdigit() is True, and int('²') fails."""
    return text.isascii() and text.isdigit()


def notify_status(what: str, received: int = 200) -> int:
    """The HTTP status answering a notification, for a gateway that reads the status.

    400 when the message is not the gateway's (sending the same bytes again
    will not help), 500 when this system failed (please send it again), and the
    gateway's own "received" for everything else -- a repeat or a wrong amount
    included, which reconciliation settles, not a retry.
    """
    return {"signature": 400, "error": 500}.get(what, received)
