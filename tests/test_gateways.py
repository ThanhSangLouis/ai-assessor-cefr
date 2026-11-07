"""Layer 2 -- INTEGRATION: the rules every payment gateway keeps (D035, D075, D097).

Stripe was removed in D097; payOS (D095) is the one real gateway, the sandbox
the test one. What is checked here holds for any gateway: one that will not
open its page fails the order with a reason, a return it cannot confirm says
so and settles nothing, a gateway never settles another gateway's order nor an
order of the other money mode, and the settings' problems are logged. payOS's
server is the fake of `test_d095_payos.py`; nothing leaves the machine.

Test case ids (TC-CT-Ixx) are listed in `docs/test/TEST_PLAN_D035.md`;
tests named after an acceptance criterion carry the name given in SRS section 3.9h.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

import pytest
from test_billing import PACKS, boot
from test_d095_payos import PAYOS, FakePayos
from test_lessons_integration import login_as

from aicefr.billing.transport import Reply, Unreachable

pytestmark = pytest.mark.integration

BODY = {"runs": 10, "gateway": "payos"}  # 49,000 dong
PRICE = 49_000


@pytest.fixture
def payos(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, **PAYOS)
    fake = FakePayos()
    m.billing.gateways["payos"]._send = fake
    return m, fake


def path_of(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.path}?{parts.query}"


def test_a_gateway_that_will_not_open_fails_the_order_with_a_reason(payos):
    m, fake = payos
    buyer = login_as(m, "SV-001")
    refusal = Reply(200, '{"code": "231", "desc": "Đơn thanh toán đã tồn tại"}'.encode())
    m.billing.gateways["payos"]._send = lambda *a: refusal

    refused = buyer.post("/api/v1/me/credit-orders", json=BODY)

    assert refused.status_code == 502
    assert (
        refused.json()["detail"].startswith("payOS: ") and "đã tồn tại" in refused.json()["detail"]
    )
    [failed] = buyer.get("/api/v1/me/credit-packs").json()["orders"]
    assert (failed["status"], failed["result_code"]) == ("failed", "231")

    def down(*a):
        raise Unreachable("timeout")

    m.billing.gateways["payos"]._send = down
    gone = buyer.post("/api/v1/me/credit-orders", json=BODY)
    assert gone.status_code == 502 and "Không kết nối được payOS" in gone.json()["detail"]
    orders = buyer.get("/api/v1/me/credit-packs").json()["orders"]
    assert not [o for o in orders if o["status"] == "pending"]


def test_a_return_the_gateway_cannot_confirm_says_so(payos):
    m, fake = payos
    buyer = login_as(m, "SV-001")
    order = buyer.post("/api/v1/me/credit-orders", json=BODY).json()["order"]
    [link_id] = fake.links
    back = path_of(fake.pay(link_id))

    def down(*a):
        raise Unreachable("timeout")

    m.billing.gateways["payos"]._send = down
    page = buyer.get(back)

    assert "Chưa xác nhận được với payOS" in page.text
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    m.billing.gateways["payos"]._send = fake
    assert "Thanh toán thành công" in buyer.get(back).text  # asked again, payOS answers


def test_one_gateway_cannot_settle_another_gateways_order(payos, tmp_path, monkeypatch):
    m, fake = payos
    buyer = login_as(m, "SV-001")
    order = buyer.post("/api/v1/me/credit-orders", json=BODY).json()["order"]
    # A result signed by the sandbox -- of a test deployment, say -- for this
    # payOS order: the sandbox is not even offered next to real money, and the
    # service settles nothing that another gateway signed.
    from aicefr.billing.gateways import SandboxGateway

    sandbox = SandboxGateway(b"bi-mat-cua-ban-thu")
    forged = sandbox.verify(sandbox.result(order["order_id"], PRICE, "paid", datetime.now(UTC)))

    assert buyer.get("/api/v1/billing/notify/sandbox?x=1").status_code == 404
    assert m.billing.settle(forged, "notify", "sandbox") == "not_found"
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    assert [e["kind"] for e in m.billing_store.events(order["order_id"])][:2] == [
        "created",
        "rejected",
    ]
    # The same gateway in the other money mode never settles it either.
    [link_id] = fake.links
    fake.pay(link_id)
    gw = m.billing.gateways["payos"]
    paid = gw.verify_return({"id": link_id})
    gw.live = False
    assert m.billing.settle(paid, "notify", "payos") == "not_found"
    gw.live = True
    assert m.billing.settle(paid, "notify", "payos") == "ok"


def test_the_problems_of_the_gateways_are_logged(tmp_path, monkeypatch):
    m = boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_METERING="on",
        AICEFR_CREDIT_PACKS=PACKS,
        AICEFR_PAYMENT_GATEWAYS="stripe, momo, payos, sandbox",
    )
    buyer = login_as(m, "SV-001")

    seen = buyer.get("/api/v1/me/credit-packs").json()

    assert [(g["name"], g["live"]) for g in seen["gateways"]] == [("sandbox", False)]
    problems = " ".join(m.billing.gateway_problems)
    assert "stripe" in problems and "momo" in problems  # D097, D075: unknown names now
    assert "AICEFR_PAYOS_CLIENT_ID" in problems  # payOS named without its keys
    off = buyer.post("/api/v1/me/credit-orders", json={"runs": 10, "gateway": "stripe"})
    assert off.status_code == 422
    first = buyer.post("/api/v1/me/credit-orders", json={"runs": 10}).json()
    assert first["checkout_url"].startswith("/billing/sandbox/")  # the first one offered
