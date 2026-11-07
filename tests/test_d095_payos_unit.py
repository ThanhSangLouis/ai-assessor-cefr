"""Layer 1 -- UNIT: the payOS adapter and its place in the gateway registry (D095).

No application, no database, no network: the adapter is handed a fake
transport that records what it would have sent and answers what payOS's API
would have answered. Signatures are recomputed here with the standard library
from what payOS documents -- HMAC-SHA256 under the checksum key over
"amount=…&cancelUrl=…&description=…&orderCode=…&returnUrl=…" for a link, over
the webhook's `data` fields sorted by name for a webhook -- rather than trusted
from the adapter.

Test case ids (TC-PO-Uxx) are listed in `docs/test/TEST_PLAN_D095.md`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from aicefr.billing import registry
from aicefr.billing.payments import GatewayError, Incoming, OrderStatus
from aicefr.billing.payos_gateway import PayosGateway, order_code, order_id_of
from aicefr.billing.transport import Reply, Unreachable
from aicefr.config import Settings

pytestmark = pytest.mark.unit

NOW = datetime(2026, 11, 7, 3, 0, tzinfo=UTC)  # 10:00 in Vietnam
CLIENT, API_KEY, CHECKSUM = "client-thu-123", "api-key-thu-456", "checksum-thu-789"
ORDER = "DL26110788C3E0"
RETURN = "https://speakup.example.vn/billing/return/payos"
LINK = "2e4acf1083304877bf1a8c108b30cccd"


class FakeHttp:
    """Stands in for the network: records each request, answers from a list."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[tuple[str, str, dict, bytes | None]] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, dict(headers), body))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def answer(status: int, body: dict) -> Reply:
    return Reply(status, json.dumps(body).encode())


def ok(data: dict) -> Reply:
    return answer(200, {"code": "00", "desc": "success", "data": data, "signature": "x"})


def mac(text: str, key: str = CHECKSUM) -> str:
    return hmac.new(key.encode(), text.encode(), hashlib.sha256).hexdigest()


def gateway(*replies) -> tuple[PayosGateway, FakeHttp]:
    fake = FakeHttp(*replies)
    return PayosGateway(CLIENT, API_KEY, CHECKSUM, transport=fake), fake


def hook(data: dict, key: str = CHECKSUM, code: str = "00") -> Incoming:
    """payOS's webhook: `data` signed as its fields sorted by name, joined `k=v&…`."""
    query = "&".join(f"{k}={'' if data[k] is None else data[k]}" for k in sorted(data))
    body = {"code": code, "desc": "success", "success": code == "00", "data": data}
    body["signature"] = mac(query, key)
    return Incoming(
        query={}, headers={"content-type": "application/json"}, body=json.dumps(body).encode()
    )


def paid_data(**changes) -> dict:
    data = {
        "orderCode": order_code(ORDER),
        "amount": 49000,
        "description": "SU88C3E0",
        "accountNumber": "12345678",
        "reference": "FT2611070001",
        "transactionDateTime": "2026-11-07 10:05:00",
        "currency": "VND",
        "paymentLinkId": LINK,
        "code": "00",
        "desc": "Thành công",
        "counterAccountBankId": "",
        "counterAccountBankName": "",
        "counterAccountName": None,
        "counterAccountNumber": None,
        "virtualAccountName": "",
        "virtualAccountNumber": "",
    }
    return data | changes


def test_order_ids_and_payos_order_codes_turn_into_each_other():
    for order in (ORDER, "DL261107000000", "DL991231FFFFFF"):
        code = order_code(order)
        assert isinstance(code, int) and 0 < code < 2**53  # an integer JavaScript keeps exactly
        assert order_id_of(code) == order and order_id_of(str(code)) == order
    for wrong in ("DH2610070A1B2C", "DL2611070a1b2c", "DL26110788C3E", ""):
        with pytest.raises(ValueError):
            order_code(wrong)
    for wrong in ("abc", "-5", "1.5", "²", 10**16, None):
        assert order_id_of(wrong) == ""


def test_the_payment_link_is_signed_the_way_payos_documents():
    gw, fake = gateway(
        ok({"checkoutUrl": f"https://pay.payos.vn/web/{LINK}", "paymentLinkId": LINK})
    )

    checkout = gw.checkout(ORDER, 49000, "Thanh toan don dai", RETURN, "/notify", "1.2.3.4", NOW)

    assert checkout.url == f"https://pay.payos.vn/web/{LINK}" and checkout.reference == LINK
    [(method, url, headers, body)] = fake.calls
    assert (method, url) == ("POST", "https://api-merchant.payos.vn/v2/payment-requests")
    assert headers["x-client-id"] == CLIENT and headers["x-api-key"] == API_KEY
    sent = json.loads(body)
    assert sent["orderCode"] == order_code(ORDER) and sent["amount"] == 49000
    # The transfer note fits the nine characters of a bank account payOS does not link.
    assert sent["description"] == "SU88C3E0" and len(sent["description"]) <= 9
    assert sent["returnUrl"] == RETURN and sent["cancelUrl"] == RETURN + "?left=1"
    assert sent["expiredAt"] == int(NOW.timestamp()) + 16 * 60
    expected = mac(
        f"amount=49000&cancelUrl={RETURN}?left=1&description=SU88C3E0"
        f"&orderCode={order_code(ORDER)}&returnUrl={RETURN}"
    )
    assert sent["signature"] == expected
    # Nothing about the payer goes to payOS (BR-32).
    assert not any(k.startswith("buyer") for k in sent)


def test_payos_refusals_read_as_sentences():
    cases = [
        (answer(401, {"code": "401", "desc": "Unauthorized"}), "Client ID hoặc API Key"),
        (
            answer(200, {"code": "231", "desc": "Đơn thanh toán đã tồn tại", "data": None}),
            "đã tồn tại",
        ),
        (answer(503, {}), "đang gặp sự cố"),
        (Unreachable("timeout"), "Không kết nối được payOS"),
        (ok({"checkoutUrl": "http://khong-an-toan", "paymentLinkId": LINK}), "không dùng được"),
    ]
    for reply, words in cases:
        gw, _ = gateway(reply)
        with pytest.raises(GatewayError) as e:
            gw.checkout(ORDER, 49000, "", RETURN, "", "", NOW)
        assert words in str(e.value)
    for missing in (("", API_KEY, CHECKSUM), (CLIENT, "", CHECKSUM), (CLIENT, API_KEY, "")):
        with pytest.raises(ValueError):
            PayosGateway(*missing)


def test_the_return_is_read_back_from_payos_and_its_address_is_not_believed():
    link = {"id": LINK, "orderCode": order_code(ORDER), "amount": 49000}
    gw, fake = gateway(
        ok(link | {"status": "PAID", "amountPaid": 49000}),
        ok(link | {"status": "PENDING", "amountPaid": 0}),
        ok(link | {"status": "PAID", "amountPaid": 20000}),
        ok(link | {"status": "CANCELLED", "amountPaid": 0}),
    )
    claim = {"id": LINK, "status": "PAID", "code": "00", "orderCode": str(order_code(ORDER))}

    paid = gw.verify_return(claim)
    assert (paid.order_id, paid.outcome, paid.amount_vnd, paid.checkout) == (
        ORDER,
        OrderStatus.PAID,
        49000,
        LINK,
    )
    assert fake.calls[0][:2] == ("GET", f"https://api-merchant.payos.vn/v2/payment-requests/{LINK}")
    # The address says PAID; payOS's own record says otherwise, and decides.
    assert gw.verify_return(claim).outcome is OrderStatus.PENDING
    assert gw.verify_return(claim).outcome is OrderStatus.PENDING  # part of the money only
    assert gw.verify_return(claim).outcome is OrderStatus.CANCELLED
    # An id that is not a payOS link is not even asked about.
    asked = len(fake.calls)
    assert gw.verify_return({"id": "../admin"}) is None and gw.verify_return({}) is None
    assert len(fake.calls) == asked
    assert gw.return_reference({"id": LINK}) == LINK


def test_a_webhook_counts_only_when_its_data_is_signed_with_the_checksum_key():
    gw, fake = gateway()

    result = gw.verify_notification(hook(paid_data()), NOW)

    assert (result.order_id, result.outcome, result.amount_vnd) == (ORDER, OrderStatus.PAID, 49000)
    assert (result.reference, result.checkout) == ("FT2611070001", LINK)
    assert gw.verify_notification(hook(paid_data(), key="khoa-khac"), NOW) is None
    tampered = json.loads(hook(paid_data()).body)
    tampered["data"]["amount"] = 1000
    assert gw.verify_notification(Incoming({}, {}, json.dumps(tampered).encode()), NOW) is None
    for junk in (b"", b"[]", b'{"data": "x", "signature": 1}', b"\xff"):
        assert gw.verify_notification(Incoming({}, {}, junk), NOW) is None
    # Authentic but not a payment: acknowledged, about no order.
    other = gw.verify_notification(hook(paid_data(code="01"), code="01"), NOW)
    assert (other.order_id, other.outcome) == ("", OrderStatus.PENDING)
    # The sample payOS posts when its dashboard saves the address: order 123 is none of ours.
    sample = gw.verify_notification(hook(paid_data(orderCode=123)), NOW)
    assert sample.order_id == "DL00000000007B"
    assert fake.calls == []  # a webhook never makes this system call payOS
    assert gw.acknowledge("ok").status == 200 and gw.acknowledge("signature").status == 400
    assert gw.acknowledge("error").status == 500


def settings(**changes) -> Settings:
    base = replace(
        Settings(),
        payment_gateways=("payos", "sandbox"),
        payments_live=False,
        payos_client_id=CLIENT,
        payos_api_key=API_KEY,
        payos_checksum_key=CHECKSUM,
    )
    return replace(base, **changes)


def test_payos_moves_real_money_so_it_runs_only_when_switched_on():
    gateways, problems = registry.build_gateways(settings(), lambda: b"bi-mat")

    assert list(gateways) == ["sandbox"]
    assert any("payOS" in p and "AICEFR_PAYMENTS_LIVE" in p for p in problems)
    gateways, problems = registry.build_gateways(settings(payments_live=True), lambda: b"bi-mat")
    assert list(gateways) == ["payos"] and gateways["payos"].live
    assert gateways["payos"].note == ""  # no test card: every link is real money
    assert any("Cổng thử đã tắt" in p for p in problems)
    gateways, problems = registry.build_gateways(
        settings(payments_live=True, payos_checksum_key=""), lambda: b"bi-mat"
    )
    assert "payos" not in gateways
    assert any("AICEFR_PAYOS_CHECKSUM_KEY" in p for p in problems)
