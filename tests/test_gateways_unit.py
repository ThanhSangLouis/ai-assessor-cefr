"""Layer 1 -- UNIT: the Stripe and MoMo adapters and the gateway registry (D035).

No application, no database, no network: each adapter is handed a fake
transport that records what it would have sent and answers what Stripe or MoMo
would have answered. Signatures are recomputed here with the standard library
from what each gateway documents -- Stripe's `t=…,v1=…` HMAC-SHA256 over
"<t>.<body>", MoMo's HMAC-SHA256 over its named fields in a fixed order --
rather than trusted from the adapter.

Test case ids (TC-CT-Uxx) are listed in `docs/test/TEST_PLAN_D035.md`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

import pytest

from aicefr.billing import registry, transport
from aicefr.billing.payments import GatewayError, Incoming, OrderStatus
from aicefr.billing.stripe_gateway import StripeGateway
from aicefr.billing.transport import Reply, Unreachable
from aicefr.config import Settings

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 7, 3, 0, tzinfo=UTC)  # 10:00 in Vietnam
SK = "sk_test_51Thu" + "x" * 20
WHSEC = "whsec_" + "b" * 32
ORDER = "DH2610070A1B2C"
RETURN = "https://cefr.example.edu.vn/billing/return/stripe"


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


def answer(status: int, data: dict) -> Reply:
    return Reply(status, json.dumps(data).encode())


def session(**fields) -> dict:
    """A Checkout Session as Stripe returns it, paid unless told otherwise."""
    return {
        "id": "cs_test_a1B2c3",
        "object": "checkout.session",
        "client_reference_id": ORDER,
        "metadata": {"order_id": ORDER},
        "amount_total": 6_000_000,
        "currency": "vnd",
        "payment_status": "paid",
        "status": "complete",
        "payment_intent": "pi_3Thu",
        "livemode": False,
        "url": None,
        "customer_details": {"email": "nguoi.tra@example.com", "name": "Nguyễn Văn A"},
    } | fields


def signed(body: bytes, at: datetime, secret: str = WHSEC) -> dict[str, str]:
    """The Stripe-Signature header for `body`, made the way Stripe documents it."""
    t = int(at.timestamp())
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return {"stripe-signature": f"t={t},v1={mac}"}


def event(kind: str, obj: dict, live: bool = False) -> bytes:
    return json.dumps(
        {"id": "evt_1", "object": "event", "type": kind, "livemode": live, "data": {"object": obj}}
    ).encode()


# ================================================================= Stripe


def test_stripe_opens_a_checkout_session_in_dong_for_the_order():
    http = FakeHttp(answer(200, session(url="https://checkout.stripe.com/c/pay/cs_test_a1B2c3")))
    gw = StripeGateway(SK, WHSEC, transport=http)

    checkout = gw.checkout(ORDER, 6_000_000, "Thanh toan don", RETURN, "", "1.2.3.4", NOW)

    assert (checkout.url, checkout.reference) == (
        "https://checkout.stripe.com/c/pay/cs_test_a1B2c3",
        "cs_test_a1B2c3",
    )
    [(method, url, headers, body)] = http.calls
    assert (method, url) == ("POST", "https://api.stripe.com/v1/checkout/sessions")
    assert headers["Authorization"] == f"Bearer {SK}"
    assert headers["Idempotency-Key"] == f"aicefr-{ORDER}"
    sent = dict(parse_qsl(body.decode()))
    assert sent["mode"] == "payment"
    # The dong has no minor unit: 6,000,000 dong is sent as 6000000, not x100.
    assert sent["line_items[0][price_data][currency]"] == "vnd"
    assert sent["line_items[0][price_data][unit_amount]"] == "6000000"
    assert sent["client_reference_id"] == sent["metadata[order_id]"] == ORDER
    assert sent["success_url"] == RETURN + "?session_id={CHECKOUT_SESSION_ID}"
    assert sent["cancel_url"] == RETURN + "?left=1"
    assert int(sent["expires_at"]) == int((NOW + timedelta(minutes=31)).timestamp())
    assert sent["locale"] == "vi"


def test_stripe_refusals_read_as_sentences():
    too_small = {"error": {"code": "amount_too_small", "type": "invalid_request_error"}}
    cases = [
        (answer(400, too_small), "mức tối thiểu Stripe nhận", "amount_too_small"),
        (answer(401, {"error": {"type": "invalid_request_error"}}), "không hợp lệ", "401"),
        (answer(500, {}), "Stripe đang gặp sự cố", "500"),
        (Unreachable("timeout"), "Không kết nối được Stripe", "unreachable"),
        (answer(200, session(url="javascript:alert(1)")), "không dùng được", "session"),
        (Reply(302, b"<html>moved</html>"), "không mở được phiên thanh toán", "302"),
    ]
    for reply, words, code in cases:
        gw = StripeGateway(SK, WHSEC, transport=FakeHttp(reply))
        with pytest.raises(GatewayError) as caught:
            gw.checkout(ORDER, 6_000_000, "x", RETURN, "", "1.2.3.4", NOW)
        assert words in str(caught.value) and caught.value.code == code
    # A redirect is handed back, never followed with the secret key in tow.
    assert transport._NoRedirect().redirect_request(None, None, 302, "", {}, "https://x") is None


def test_stripe_return_is_read_back_from_stripe():
    http = FakeHttp(
        answer(200, session()),
        answer(200, session(payment_status="unpaid", status="complete")),
        answer(200, session(payment_status="unpaid", status="expired")),
        answer(200, session(currency="usd", amount_total=24_000)),
    )
    gw = StripeGateway(SK, WHSEC, transport=http)

    paid = gw.verify_return({"session_id": "cs_test_a1B2c3"})

    assert (paid.order_id, paid.outcome, paid.amount_vnd, paid.reference) == (
        ORDER,
        OrderStatus.PAID,
        6_000_000,
        "pi_3Thu",
    )
    # Ids only: the payer's email and name that Stripe holds are not kept (BR-32).
    assert paid.details == {"session": "cs_test_a1B2c3"} and paid.checkout == "cs_test_a1B2c3"
    assert http.calls[0][:2] == (
        "GET",
        "https://api.stripe.com/v1/checkout/sessions/cs_test_a1B2c3",
    )
    assert gw.verify_return({"session_id": "cs_test_a1B2c3"}).outcome is OrderStatus.PENDING
    assert gw.verify_return({"session_id": "cs_test_a1B2c3"}).outcome is OrderStatus.CANCELLED
    assert gw.verify_return({"session_id": "cs_test_a1B2c3"}).amount_vnd == -1  # not dong
    # Not a session id, or a live one on a test key: refused without asking Stripe.
    for bad in ("", "cs_test_a/../../v1/charges", "pi_3Thu", "cs_live_a1B2c3"):
        assert gw.verify_return({"session_id": bad}) is None
    assert len(http.calls) == 4
    down = StripeGateway(SK, WHSEC, transport=FakeHttp(Unreachable("dns")))
    with pytest.raises(GatewayError):
        down.verify_return({"session_id": "cs_test_a1B2c3"})


def test_stripe_events_count_only_when_signed_and_fresh():
    gw = StripeGateway(SK, WHSEC, transport=FakeHttp())
    body = event("checkout.session.completed", session())

    def check(headers, payload=body, at=NOW):
        return gw.verify_notification(Incoming({}, headers, payload), at)

    paid = check(signed(body, NOW))
    assert (paid.order_id, paid.outcome, paid.amount_vnd) == (ORDER, OrderStatus.PAID, 6_000_000)
    assert check(signed(body, NOW), at=NOW + timedelta(seconds=299)) is not None
    assert check(signed(body, NOW), at=NOW + timedelta(seconds=301)) is None  # replayed late
    assert check(signed(body, NOW), payload=body.replace(b"6000000", b"6000")) is None
    assert check(signed(body, NOW, secret="whsec_khac")) is None
    assert check({}) is None
    # A secret being rolled: several v1 values, one of them right.
    both = signed(body, NOW)["stripe-signature"].replace(",v1=", ",v1=" + "0" * 64 + ",v1=")
    assert check({"stripe-signature": both}) is not None
    live = event("checkout.session.completed", session(), live=True)
    assert check(signed(live, NOW), payload=live) is None  # a live event on a test key
    # Headers arrive as latin-1: odd characters are refused, never a crash.
    assert check({"stripe-signature": "t=\u00b2,v1=ab"}) is None
    assert check({"stripe-signature": "t=1" + "0" * 40 + ",v1=ab"}) is None
    stamp = signed(body, NOW)["stripe-signature"].split(",")[0]
    assert check({"stripe-signature": stamp + ",v1=\u00e9\u00e9"}) is None

    def outcome(kind, **fields):
        payload = event(kind, session(**fields))
        return check(signed(payload, NOW), payload=payload).outcome

    assert outcome("checkout.session.completed", payment_status="unpaid") is OrderStatus.PENDING
    assert outcome("checkout.session.async_payment_succeeded") is OrderStatus.PAID
    assert outcome("checkout.session.async_payment_failed") is OrderStatus.FAILED
    assert outcome("checkout.session.expired", status="expired") is OrderStatus.CANCELLED
    other = event("payment_intent.created", {"object": "payment_intent", "id": "pi_3Thu"})
    ignored = check(signed(other, NOW), payload=other)
    assert (ignored.order_id, ignored.outcome) == ("", OrderStatus.PENDING)
    assert (
        StripeGateway(SK, transport=FakeHttp()).verify_notification(
            Incoming({}, signed(body, NOW), body), NOW
        )
        is None
    )  # no signing secret set: no event is believed
    assert [gw.acknowledge(w).status for w in ("ok", "already", "signature", "error")] == [
        200,
        200,
        400,
        500,
    ]


def test_stripe_keys_decide_the_mode():
    test = StripeGateway(SK)
    assert test.live is False and "4242 4242 4242 4242" in test.note
    assert StripeGateway("rk_test_abc").live is False
    live = StripeGateway("sk_live_abc", WHSEC)
    assert live.live is True and live.note == ""
    for key, webhook in (("sk_live_abc", ""), ("pk_test_abc", ""), (SK, "khong-phai-whsec")):
        with pytest.raises(ValueError):
            StripeGateway(key, webhook)


# ================================================================= the registry


def settings(**changes) -> Settings:
    base = replace(
        Settings(),
        payment_gateways=("sandbox",),
        payments_live=False,
        stripe_secret_key="",
        stripe_webhook_secret="",
    )
    return replace(base, **changes)


def build(**changes):
    return registry.build_gateways(settings(**changes), lambda: b"bi-mat-cong-thu")


def test_the_registry_builds_what_the_settings_ask_for(monkeypatch):
    # The list as written in .env: a blank line means the default, not "none".
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", "  ")
    assert Settings().payment_gateways == ("sandbox",)
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", " Stripe , sandbox,,")
    assert Settings().payment_gateways == ("stripe", "sandbox")
    keys = dict(stripe_secret_key=SK, stripe_webhook_secret=WHSEC)

    gateways, problems = build(payment_gateways=("stripe", "sandbox"), **keys)

    assert list(gateways) == ["stripe", "sandbox"]
    assert problems == []
    assert not any(g.live for g in gateways.values())
    # Nothing set but the names: each one missing says what is missing; D075
    # removed VNPay and MoMo, which are now names like any unknown one.
    gateways, problems = build(payment_gateways=("stripe", "momo", "vnpay", "stripe"))
    assert gateways == {}
    assert any("AICEFR_STRIPE_SECRET_KEY" in p for p in problems)
    assert any("momo" in p for p in problems) and any("vnpay" in p for p in problems)
    assert len(problems) == 3  # the second "stripe" is not reported twice
    # Stripe in test mode without its webhook secret runs, with a warning.
    gateways, problems = build(payment_gateways=("stripe",), stripe_secret_key=SK)
    assert list(gateways) == ["stripe"]
    assert any("AICEFR_STRIPE_WEBHOOK_SECRET" in p for p in problems)


def test_real_money_is_never_a_default():
    live = dict(
        payment_gateways=("sandbox", "stripe"),
        stripe_secret_key="sk_live_abc",
        stripe_webhook_secret=WHSEC,
    )

    gateways, problems = build(**live)

    assert list(gateways) == ["sandbox"]
    assert any("AICEFR_PAYMENTS_LIVE" in p for p in problems)
    # Switched on, the live gateway runs and the sandbox goes.
    gateways, problems = build(payments_live=True, **live)
    assert list(gateways) == ["stripe"] and gateways["stripe"].live
    assert any("Cổng thử đã tắt" in p for p in problems)
    # Next to a gateway that takes real money, no test environment runs: the
    # sandbox beside a live Stripe key would sell real runs for a test card.
    assert "sandbox" not in gateways
