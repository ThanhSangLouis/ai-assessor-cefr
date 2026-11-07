"""Layer 2 -- INTEGRATION: a run pack paid through payOS, end to end (D095).

The application is reloaded per test as in `test_billing.py`, with payOS the
gateway and real money switched on (payOS has no test environment). payOS's
server is replaced after start-up by a fake on the adapter's transport:
`FakePayos` keeps payment links the way payOS's API does. Its webhooks are
signed here the way payOS documents. Nothing leaves the machine.

Test case ids (TC-PO-Ixx) are listed in `docs/test/TEST_PLAN_D095.md`;
tests named after an acceptance criterion carry the name given in SRS FR-100.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode, urlparse

import pytest
from test_billing import PACKS, boot
from test_d095_payos_unit import API_KEY, CHECKSUM, CLIENT, mac
from test_lessons_integration import login_as

from aicefr.billing.transport import Reply

pytestmark = pytest.mark.integration

BODY = {"runs": 10, "gateway": "payos"}  # 49,000 dong
PRICE = 49_000
PAYOS = {
    "AICEFR_BILLING": "on",
    "AICEFR_METERING": "on",
    "AICEFR_CREDIT_PACKS": PACKS,
    "AICEFR_PAYMENT_GATEWAYS": "payos,sandbox",
    "AICEFR_PAYMENTS_LIVE": "on",
    "AICEFR_PAYOS_CLIENT_ID": CLIENT,
    "AICEFR_PAYOS_API_KEY": API_KEY,
    "AICEFR_PAYOS_CHECKSUM_KEY": CHECKSUM,
}


def ok(data: dict) -> Reply:
    return Reply(200, json.dumps({"code": "00", "desc": "success", "data": data}).encode())


class FakePayos:
    """payOS's API as far as this system uses it: open a payment link, read it back."""

    def __init__(self) -> None:
        self.links: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url))
        assert headers["x-client-id"] == CLIENT and headers["x-api-key"] == API_KEY
        if method == "POST" and url.endswith("/v2/payment-requests"):
            sent = json.loads(body)
            link_id = f"{len(self.links) + 1:032x}"
            self.links[link_id] = {
                "id": link_id,
                "orderCode": sent["orderCode"],
                "amount": sent["amount"],
                "amountPaid": 0,
                "status": "PENDING",
                "returnUrl": sent["returnUrl"],
                "cancelUrl": sent["cancelUrl"],
            }
            return ok(
                {"checkoutUrl": f"https://pay.payos.vn/web/{link_id}", "paymentLinkId": link_id}
            )
        if method == "GET" and "/v2/payment-requests/" in url:
            link_id = url.rsplit("/", 1)[1]
            if link_id not in self.links:
                return Reply(200, json.dumps({"code": "101", "desc": "Không tìm thấy"}).encode())
            return ok(self.links[link_id])
        return Reply(400, b"{}")

    def pay(self, link_id: str) -> str:
        """The payer transfers; returns where payOS then sends the browser."""
        link = self.links[link_id] | {"status": "PAID"}
        self.links[link_id] = link | {"amountPaid": link["amount"]}
        query = {"code": "00", "id": link_id, "cancel": "false", "status": "PAID"}
        return f"{link['returnUrl']}?{urlencode(query | {'orderCode': link['orderCode']})}"


@pytest.fixture
def payos(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, **PAYOS)
    fake = FakePayos()
    m.billing.gateways["payos"]._send = fake
    return m, fake


def place(buyer) -> dict:
    r = buyer.post("/api/v1/me/credit-orders", json=BODY)
    assert r.status_code == 200, r.text
    return r.json()


def path_of(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.path}?{parts.query}"


def wallet(buyer) -> float:
    return buyer.get("/api/v1/me/credits").json()["wallet_runs"]


def webhook(client, link: dict, key: str = CHECKSUM, **changes):
    """payOS's server posting a transfer that arrived, signed over `data` sorted by name."""
    data = {
        "orderCode": link["orderCode"],
        "amount": link["amount"],
        "description": "SU" + "x" * 6,
        "accountNumber": "12345678",
        "reference": "FT2611070001",
        "transactionDateTime": "2026-11-07 10:05:00",
        "currency": "VND",
        "paymentLinkId": link["id"],
        "code": "00",
        "desc": "Thành công",
    } | changes
    body = {"code": "00", "desc": "success", "success": True, "data": data}
    body["signature"] = mac("&".join(f"{k}={data[k]}" for k in sorted(data)), key)
    return client.post("/api/v1/billing/notify/payos", json=body)


def test_paying_through_payos_is_read_back_and_credited_once(payos):
    m, fake = payos
    buyer = login_as(m, "SV-001")

    order = place(buyer)

    [link_id] = fake.links
    link = fake.links[link_id]
    assert order["checkout_url"] == f"https://pay.payos.vn/web/{link_id}"
    assert link["amount"] == PRICE and link["returnUrl"].endswith("/billing/return/payos")
    assert order["order"]["live"] is True and order["order"]["gateway_title"] == "payOS"
    page = buyer.get(path_of(fake.pay(link_id)))
    assert "Thanh toán thành công" in page.text
    assert fake.calls[-1] == ("GET", f"https://api-merchant.payos.vn/v2/payment-requests/{link_id}")
    assert wallet(buyer) == 10
    # The same address again: read from the database, payOS is not asked again.
    asked = len(fake.calls)
    assert "Thanh toán thành công" in buyer.get(path_of(fake.pay(link_id))).text
    assert len(fake.calls) == asked and wallet(buyer) == 10


def test_the_payos_webhook_alone_credits_the_runs_once(payos):
    m, fake = payos
    buyer = login_as(m, "SV-001")
    place(buyer)
    [link_id] = fake.links
    fake.pay(link_id)  # paid, and the tab closed before coming back
    link = fake.links[link_id]

    forged = webhook(buyer, link, key="khoa-khac")
    assert forged.status_code == 400 and wallet(buyer) == 0
    cheaper = webhook(buyer, link, amount=1000)
    assert cheaper.status_code == 200 and wallet(buyer) == 0  # a wrong amount pays nothing
    foreign = webhook(buyer, link, paymentLinkId="f" * 32)
    assert foreign.status_code == 200 and wallet(buyer) == 0  # another link of the same order
    assert webhook(buyer, link).json() == {"success": True}
    assert wallet(buyer) == 10
    assert webhook(buyer, link).status_code == 200 and wallet(buyer) == 10  # sent again
    # The sample payOS posts when the address is saved in its dashboard.
    sample = webhook(buyer, link | {"orderCode": 123, "id": "a" * 32})
    assert sample.status_code == 200 and wallet(buyer) == 10


def test_a_return_address_alone_proves_nothing(payos):
    m, fake = payos
    buyer = login_as(m, "SV-001")
    place(buyer)
    [link_id] = fake.links
    claim = {"code": "00", "id": link_id, "cancel": "false", "status": "PAID"}

    page = buyer.get("/billing/return/payos?" + urlencode(claim))

    assert "Thanh toán thành công" not in page.text and wallet(buyer) == 0
    # A link no order of ours opened is not even asked about.
    asked = len(fake.calls)
    stranger = buyer.get("/billing/return/payos?" + urlencode(claim | {"id": "e" * 32}))
    assert stranger.status_code == 200 and len(fake.calls) == asked
    # Leaving payOS's page settles nothing; the order waits, then expires.
    left = buyer.get("/billing/return/payos?left=1&cancel=true&status=CANCELLED")
    assert left.status_code == 200 and len(fake.calls) == asked
    [mine] = buyer.get("/api/v1/me/credit-packs").json()["orders"]
    assert mine["status"] == "pending"


def test_payos_is_offered_only_when_real_money_is_switched_on(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, **(PAYOS | {"AICEFR_PAYMENTS_LIVE": ""}))
    buyer = login_as(m, "SV-001")

    on_sale = buyer.get("/api/v1/me/credit-packs").json()

    assert [g["name"] for g in on_sale["gateways"]] == ["sandbox"]
    refused = buyer.post("/api/v1/me/credit-orders", json=BODY)
    assert refused.status_code in (400, 422) and wallet(buyer) == 0
