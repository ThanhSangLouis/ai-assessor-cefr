"""Layer 1 -- UNIT: what lets the end-to-end test use a fake payOS, and nothing more (D099).

Plain HTTP reaches only this machine; a payment page over plain HTTP is taken
only from a payOS that is itself on this machine; reconciliation reads a link
back by its id. No application, no database, no network.

Test case ids (TC-PG-Uxx) are listed in `docs/test/TEST_PLAN_D099.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from test_d095_payos_unit import API_KEY, CHECKSUM, CLIENT, LINK, ORDER, RETURN, FakeHttp, ok

from aicefr.billing import transport
from aicefr.billing.payments import GatewayError, OrderStatus
from aicefr.billing.payos_gateway import PayosGateway, order_code

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 7, 3, 0, tzinfo=UTC)
FAKE = "http://127.0.0.1:8765"


def test_plain_http_reaches_only_this_machine():
    """TC-PG-U01: http://127.0.0.1:port is tried; any other plain address is refused unsent."""
    with pytest.raises(transport.Unreachable):
        transport.https("GET", "http://127.0.0.1:9/", {}, None)  # nothing listens on 9
    for address in ("http://localhost:8000/", "http://127.0.0.1.example.com/", "http://10.0.0.1/"):
        with pytest.raises(ValueError):
            transport.https("GET", address, {}, None)


def test_a_payment_page_over_http_comes_only_from_a_payos_on_this_machine():
    """TC-PG-U02: the real payOS handing back an http:// page is refused; the local fake is not."""
    page = {"checkoutUrl": f"{FAKE}/web/{LINK}", "paymentLinkId": LINK}
    real = PayosGateway(CLIENT, API_KEY, CHECKSUM, transport=FakeHttp(ok(page)))
    with pytest.raises(GatewayError):
        real.checkout(ORDER, 49_000, "x", RETURN, "", "127.0.0.1", NOW)

    send = FakeHttp(ok(page))
    fake = PayosGateway(CLIENT, API_KEY, CHECKSUM, transport=send, api=FAKE)
    assert (
        fake.checkout(ORDER, 49_000, "x", RETURN, "", "127.0.0.1", NOW).url == page["checkoutUrl"]
    )
    assert send.calls[0][1] == f"{FAKE}/v2/payment-requests"


def test_look_up_reads_a_link_back_by_its_id():
    """TC-PG-U03: reconciliation asks payOS about the link the order opened, and reads its word."""
    link = {"id": LINK, "orderCode": order_code(ORDER), "amount": 49_000,
            "amountPaid": 49_000, "status": "PAID"}  # fmt: skip
    send = FakeHttp(ok(link))
    gateway = PayosGateway(CLIENT, API_KEY, CHECKSUM, transport=send)

    result = gateway.look_up(LINK)

    assert send.calls[0][:2] == ("GET", f"https://api-merchant.payos.vn/v2/payment-requests/{LINK}")
    assert (result.order_id, result.outcome, result.checkout) == (ORDER, OrderStatus.PAID, LINK)
    assert gateway.look_up("not-a-link-id") is None
