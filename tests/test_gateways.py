"""Layer 2 -- INTEGRATION: a run pack paid through Stripe, the gateway chosen (D035, D075).

The application is reloaded per test as in `test_billing.py`, with the
gateways named in `AICEFR_PAYMENT_GATEWAYS`. Stripe's and MoMo's servers are
replaced after start-up by fakes on the adapter's transport: `FakeStripe`
keeps Checkout Sessions the way Stripe's API does, `FakeMomo` answers MoMo's
create endpoint. Their messages back -- Stripe's webhook events, MoMo's IPN and
return address -- are signed here the way each gateway documents. Nothing
leaves the machine.

Test case ids (TC-CT-Ixx) are listed in `docs/test/TEST_PLAN_D035.md`; tests
named after an acceptance criterion carry the name given in SRS section 3.9h.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlparse

import pytest
from test_billing import PACKS, boot
from test_gateways_unit import SK, WHSEC, signed
from test_lessons_integration import login_as

from aicefr.billing.transport import Reply, Unreachable

pytestmark = pytest.mark.integration

BODY = {"runs": 10}  # 49,000 dong
PRICE = 49_000
PAYMENTS = {"AICEFR_BILLING": "on", "AICEFR_METERING": "on", "AICEFR_CREDIT_PACKS": PACKS}


def buyer_of(m):
    """A learner who buys runs (D075: every order is a pack of runs)."""
    return login_as(m, "SV-001")


def answer(status: int, data: dict) -> Reply:
    return Reply(status, json.dumps(data).encode())


class FakeStripe:
    """Stripe's API as far as this system uses it: open a Checkout Session, read it back."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []
        self.next: Reply | Exception | None = None  # what the next call gets instead

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url))
        if self.next is not None:
            reply, self.next = self.next, None
            if isinstance(reply, Exception):
                raise reply
            return reply
        assert headers["Authorization"] == f"Bearer {SK}"
        if method == "POST" and url.endswith("/v1/checkout/sessions"):
            sent = dict(parse_qsl(body.decode()))
            sid = f"cs_test_{len(self.sessions) + 1:04d}Thu"
            self.sessions[sid] = {
                "id": sid,
                "object": "checkout.session",
                "client_reference_id": sent["client_reference_id"],
                "metadata": {"order_id": sent["metadata[order_id]"]},
                "amount_total": int(sent["line_items[0][price_data][unit_amount]"]),
                "currency": sent["line_items[0][price_data][currency]"],
                "payment_status": "unpaid",
                "status": "open",
                "payment_intent": None,
                "livemode": False,
                "url": f"https://checkout.stripe.com/c/pay/{sid}",
                "success_url": sent["success_url"],
                "cancel_url": sent["cancel_url"],
            }
            return answer(200, self.sessions[sid])
        if method == "GET" and "/v1/checkout/sessions/" in url:
            sid = url.rsplit("/", 1)[1]
            if sid not in self.sessions:
                return answer(404, {"error": {"code": "resource_missing"}})
            return answer(200, self.sessions[sid])
        return answer(400, {"error": {"code": "unexpected"}})

    def pay(self, sid: str) -> str:
        """The payer pays on Stripe's page; returns where Stripe then sends the browser."""
        self.sessions[sid] |= {"payment_status": "paid", "status": "complete"}
        self.sessions[sid]["payment_intent"] = "pi_" + sid[8:]
        return self.sessions[sid]["success_url"].replace("{CHECKOUT_SESSION_ID}", sid)


@pytest.fixture
def stripe(tmp_path, monkeypatch):
    """Billing on with Stripe in test mode first and the sandbox second; Stripe is a fake."""
    m = boot(
        tmp_path,
        monkeypatch,
        **PAYMENTS,
        AICEFR_PAYMENT_GATEWAYS="stripe,sandbox",
        AICEFR_STRIPE_SECRET_KEY=SK,
        AICEFR_STRIPE_WEBHOOK_SECRET=WHSEC,
    )
    fake = FakeStripe()
    m.billing.gateways["stripe"]._send = fake
    return m, fake


def place(admin, gateway: str = "stripe", **changes) -> dict:
    r = admin.post("/api/v1/me/credit-orders", json=BODY | {"gateway": gateway} | changes)
    assert r.status_code == 200, r.text
    return r.json()


def path_of(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.path}?{parts.query}"


def webhook(client, kind: str, session: dict, secret: str = WHSEC):
    """Stripe's server posting an event, signed with the endpoint's secret."""
    event = {"id": "evt_1", "object": "event", "type": kind, "livemode": False}
    body = json.dumps(event | {"data": {"object": session}}).encode()
    headers = signed(body, datetime.now(UTC), secret) | {"content-type": "application/json"}
    return client.post("/api/v1/billing/notify/stripe", content=body, headers=headers)


# ================================================================= Stripe


def test_paying_through_stripe_is_read_back_and_counted_once(stripe):
    m, fake = stripe
    admin = buyer_of(m)

    placed = place(admin)

    order, url = placed["order"], placed["checkout_url"]
    [sid] = fake.sessions
    assert url == f"https://checkout.stripe.com/c/pay/{sid}"
    assert (order["gateway"], order["gateway_title"], order["live"]) == ("stripe", "Stripe", False)
    assert m.billing_store.order(order["order_id"])["checkout_ref"] == sid
    assert fake.sessions[sid]["amount_total"] == PRICE
    assert fake.sessions[sid]["success_url"].startswith("http://testserver/billing/return/stripe?")
    # The payer pays; Stripe sends the browser back with the session's id only.
    page = admin.get(path_of(fake.pay(sid)))
    assert "Thanh toán thành công" in page.text and "Môi trường thử của Stripe" in page.text
    assert fake.calls[-1] == ("GET", f"https://api.stripe.com/v1/checkout/sessions/{sid}")
    now = m.billing_store.order(order["order_id"])
    assert (now["status"], now["reference"]) == ("paid", "pi_" + sid[8:])
    assert now["credited_at"]
    # Stripe's webhook for the same payment, then the browser again: nothing
    # more -- and the settled order is shown without asking Stripe again.
    assert webhook(admin, "checkout.session.completed", fake.sessions[sid]).json() == {
        "received": True
    }
    asked = len(fake.calls)
    again = admin.get(path_of(fake.pay(sid)))
    assert "Thanh toán thành công" in again.text and len(fake.calls) == asked
    # The runs reaching the wallet is an event of its own, between the two messages.
    events = [e for e in m.billing_store.events(order["order_id"]) if e["kind"] != "credited"]
    assert [e["kind"] for e in events] == ["created", "return", "notify"]
    assert [e["detail"]["applied"] for e in events[1:]] == [True, False]
    receipt = admin.get(f"/billing/orders/{order['order_id']}/receipt").text
    assert "Stripe (môi trường thử, không có tiền thật)" in receipt


def test_the_stripe_webhook_alone_credits_the_runs(stripe):
    m, fake = stripe
    admin = buyer_of(m)
    order = place(admin)["order"]
    [sid] = fake.sessions
    fake.pay(sid)  # paid, and the tab closed before coming back

    forged = webhook(admin, "checkout.session.completed", fake.sessions[sid], secret="whsec_khac")
    bare = admin.post("/api/v1/billing/notify/stripe", content=b"{}")
    as_get = admin.get("/api/v1/billing/notify/stripe")
    odd = admin.post(
        "/api/v1/billing/notify/stripe", content=b"{}", headers={"stripe-signature": b"t=\xb2,v1=a"}
    )
    huge = admin.post("/api/v1/billing/notify/stripe", content=b"x" * (256 * 1024 + 1))
    # A session someone else opened on the same Stripe account, naming this
    # order and its amount, is signed by Stripe -- and still not this order's.
    foreign = fake.sessions[sid] | {"id": "cs_test_9999Khac", "payment_intent": "pi_khac"}
    elsewhere = webhook(admin, "checkout.session.completed", foreign)

    assert (forged.status_code, bare.status_code, as_get.status_code) == (400, 400, 400)
    assert (odd.status_code, huge.status_code, elsewhere.status_code) == (400, 413, 200)
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    ok = webhook(admin, "checkout.session.completed", fake.sessions[sid])
    assert (ok.status_code, ok.json()) == (200, {"received": True})
    assert m.billing_store.order(order["order_id"])["status"] == "paid"
    assert m.billing_store.order(order["order_id"])["credited_at"]
    # An event about something else on the same Stripe account is received and dropped.
    other = webhook(admin, "customer.created", {"object": "customer", "id": "cus_1"})
    assert other.status_code == 200


def test_leaving_stripe_changes_nothing_until_the_session_expires(stripe):
    m, fake = stripe
    admin = buyer_of(m)
    order = place(admin)["order"]
    [sid] = fake.sessions

    page = admin.get(path_of(fake.sessions[sid]["cancel_url"]))

    assert "Bạn đã rời trang thanh toán" in page.text
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    fake.sessions[sid]["status"] = "expired"
    assert webhook(admin, "checkout.session.expired", fake.sessions[sid]).status_code == 200
    assert m.billing_store.order(order["order_id"])["status"] == "cancelled"


def test_a_gateway_that_will_not_open_fails_the_order_with_a_reason(stripe):
    m, fake = stripe
    admin = buyer_of(m)
    fake.next = answer(400, {"error": {"code": "amount_too_small"}})

    refused = admin.post("/api/v1/me/credit-orders", json=BODY | {"gateway": "stripe"})

    assert refused.status_code == 502
    assert refused.json()["detail"].startswith("Stripe: ")
    assert "mức tối thiểu" in refused.json()["detail"]
    [failed] = admin.get("/api/v1/me/credit-packs").json()["orders"]
    assert (failed["status"], failed["result_code"]) == ("failed", "amount_too_small")
    fake.next = Unreachable("timeout")
    down = admin.post("/api/v1/me/credit-orders", json=BODY | {"gateway": "stripe"})
    assert down.status_code == 502 and "Không kết nối được Stripe" in down.json()["detail"]
    orders = admin.get("/api/v1/me/credit-packs").json()["orders"]
    assert not [o for o in orders if o["status"] == "pending"]


def test_a_return_stripe_cannot_confirm_says_so(stripe):
    m, fake = stripe
    admin = buyer_of(m)
    order = place(admin)["order"]
    [sid] = fake.sessions
    back = path_of(fake.pay(sid))
    fake.next = Unreachable("timeout")

    page = admin.get(back)

    assert "Chưa xác nhận được với Stripe" in page.text
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    assert "Thanh toán thành công" in admin.get(back).text  # asked again, Stripe answers


def test_stripe_is_asked_only_about_checkouts_this_system_opened(stripe):
    m, fake = stripe
    admin = buyer_of(m)
    place(admin)
    asked = len(fake.calls)

    for sid in ("cs_test_0099Thu", "cs_test_" + "a" * 60, "khong-phai-ma-phien"):
        page = admin.get(f"/billing/return/stripe?session_id={sid}")
        assert "Không xác nhận được kết quả thanh toán" in page.text

    assert len(fake.calls) == asked  # Stripe was not asked about any of them
    assert admin.get("/api/v1/me/credit-packs").json()["orders"][0]["status"] == "pending"


def test_one_gateway_cannot_settle_another_gateways_order(stripe):
    m, _fake = stripe
    admin = buyer_of(m)
    order = place(admin)["order"]
    sandbox = m.billing.gateways["sandbox"]
    forged = sandbox.result(order["order_id"], PRICE, "paid", datetime.now(UTC))

    answered = admin.get("/api/v1/billing/notify/sandbox?" + urlencode(forged)).json()

    assert answered["RspCode"] == "01"
    assert m.billing_store.order(order["order_id"])["status"] == "pending"
    assert [e["kind"] for e in m.billing_store.events(order["order_id"])][:2] == [
        "created",
        "rejected",
    ]
    page = admin.get("/billing/return/sandbox?" + urlencode(forged))
    assert "Không xác nhận được kết quả thanh toán" in page.text
    # The same gateway in the other money mode: a key switched to live after
    # this test-mode order was placed never settles it, and the reverse.
    [sid] = _fake.sessions
    _fake.pay(sid)
    stripe_gw = m.billing.gateways["stripe"]
    paid = stripe_gw._result(_fake.sessions[sid], None)
    stripe_gw.live = True
    assert m.billing.settle(paid, "notify", "stripe") == "not_found"
    stripe_gw.live = False
    assert m.billing.settle(paid, "notify", "stripe") == "ok"
    sandbox_page = admin.get(f"/billing/sandbox/{order['order_id']}?t=" + sandbox.token("x", 1))
    assert sandbox_page.status_code == 404


# ================================================================= choosing a gateway


def test_the_buyer_picks_the_gateway_and_the_problems_are_logged(tmp_path, monkeypatch):
    m = boot(
        tmp_path,
        monkeypatch,
        **PAYMENTS,
        AICEFR_PAYMENT_GATEWAYS="stripe, momo, sandbox",
        AICEFR_STRIPE_SECRET_KEY=SK,
    )
    m.billing.gateways["stripe"]._send = FakeStripe()
    buyer = buyer_of(m)

    seen = buyer.get("/api/v1/me/credit-packs").json()

    assert [(g["name"], g["title"], g["live"]) for g in seen["gateways"]] == [
        ("stripe", "Stripe", False),
        ("sandbox", "Cổng thử", False),
    ]
    problems = " ".join(m.billing.gateway_problems)
    assert "momo" in problems  # D075: removed, read as an unknown gateway
    assert "AICEFR_STRIPE_WEBHOOK_SECRET" in problems
    assert SK not in json.dumps(seen)  # a key is never shown
    off = buyer.post("/api/v1/me/credit-orders", json=BODY | {"gateway": "momo"})  # not offered
    assert off.status_code == 422
    first = buyer.post("/api/v1/me/credit-orders", json=BODY).json()
    assert first["order"]["gateway"] == "stripe"  # the first one offered
    other = place(buyer, gateway="sandbox")
    assert other["checkout_url"].startswith("/billing/sandbox/")


def test_real_money_needs_to_be_switched_on(tmp_path, monkeypatch):
    live = dict(
        **PAYMENTS,
        AICEFR_PAYMENT_GATEWAYS="stripe,sandbox",
        AICEFR_STRIPE_SECRET_KEY="sk_live_khong-phai-khoa-that",
        AICEFR_STRIPE_WEBHOOK_SECRET=WHSEC,
    )
    m = boot(tmp_path, monkeypatch, **live)

    assert list(m.billing.gateways) == ["sandbox"]
    assert any("AICEFR_PAYMENTS_LIVE" in p for p in m.billing.gateway_problems)
    elsewhere = tmp_path / "switched-on"  # a deployment of its own
    elsewhere.mkdir()
    m = boot(
        elsewhere,
        monkeypatch,
        AICEFR_DB=str(elsewhere / "aicefr.db"),
        AICEFR_CORE_DB=str(elsewhere / "aicefr.db"),
        AICEFR_PAYMENTS_LIVE="on",
        **live,
    )
    assert [(g.name, g.live) for g in m.billing.gateways.values()] == [("stripe", True)]
    assert any("Cổng thử đã tắt" in p for p in m.billing.gateway_problems)
    assert buyer_of(m).get("/billing/sandbox/DL1?t=x").status_code == 404
