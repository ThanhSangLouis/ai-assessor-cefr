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
from aicefr.billing.momo_gateway import TEST_ENDPOINT, MomoGateway
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


# ================================================================= MoMo

MOMO_SECRET = "bi-mat-momo-cua-bai-kiem-thu"


def momo_mac(values: dict, fields: tuple[str, ...]) -> str:
    raw = "&".join(f"{k}={values[k]}" for k in fields)
    return hmac.new(MOMO_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()


def momo() -> MomoGateway:
    return MomoGateway("MOMOTHU01", "ACCESSTHU", MOMO_SECRET, transport=FakeHttp())


def momo_result(code: int = 0, amount: int = 6_000_000, as_text: bool = False) -> dict:
    """What MoMo sends back, signed: JSON numbers in the IPN, text in the return address."""
    values = {
        "partnerCode": "MOMOTHU01",
        "orderId": ORDER,
        "requestId": ORDER,
        "amount": amount,
        "orderInfo": "Thanh toan don",
        "orderType": "momo_wallet",
        "transId": 4088878653,
        "resultCode": code,
        "message": "Thành công.",
        "payType": "qr",
        "responseTime": 1791345600000,
        "extraData": "",
    }
    order = (
        "accessKey amount extraData message orderId orderInfo orderType partnerCode payType"
        " requestId responseTime resultCode transId"
    ).split()
    values["signature"] = momo_mac(values | {"accessKey": "ACCESSTHU"}, tuple(order))
    return {k: str(v) for k, v in values.items()} if as_text else values


def test_momo_signs_the_create_request_as_documented():
    http = FakeHttp(answer(200, {"resultCode": 0, "payUrl": "https://test-payment.momo.vn/pay/x"}))
    gw = MomoGateway("MOMOTHU01", "ACCESSTHU", MOMO_SECRET, transport=http)

    checkout = gw.checkout(
        ORDER, 6_000_000, "Thanh toan don", "https://x.vn/r", "https://x.vn/n", "1.2.3.4", NOW
    )

    assert checkout.url == "https://test-payment.momo.vn/pay/x"
    [(method, url, headers, body)] = http.calls
    assert (method, url) == ("POST", TEST_ENDPOINT)
    assert headers["Content-Type"].startswith("application/json")
    sent = json.loads(body)
    assert sent["amount"] == 6_000_000 and sent["requestType"] == "captureWallet"
    assert (sent["redirectUrl"], sent["ipnUrl"]) == ("https://x.vn/r", "https://x.vn/n")
    order = (
        "accessKey amount extraData ipnUrl orderId orderInfo partnerCode redirectUrl requestId"
        " requestType"
    ).split()
    assert sent["signature"] == momo_mac(sent | {"accessKey": "ACCESSTHU"}, tuple(order))
    assert "accessKey" not in sent and MOMO_SECRET not in body.decode()
    assert gw.live is False and gw.note
    # More than MoMo takes in one payment (50,000,000 dong): said without asking MoMo.
    quiet = FakeHttp()
    too_much = MomoGateway("MOMOTHU01", "ACCESSTHU", MOMO_SECRET, transport=quiet)
    with pytest.raises(GatewayError) as caught:
        too_much.checkout(ORDER, 90_000_000, "x", "https://x.vn/r", "https://x.vn/n", "", NOW)
    assert caught.value.code == "22" and "50.000.000 đ" in str(caught.value)
    assert quiet.calls == []
    refused = MomoGateway(
        "MOMOTHU01",
        "ACCESSTHU",
        MOMO_SECRET,
        transport=FakeHttp(answer(200, {"resultCode": 13, "message": "Merchant auth failed"})),
    )
    with pytest.raises(GatewayError) as caught:
        refused.checkout(ORDER, 6_000_000, "x", "https://x.vn/r", "https://x.vn/n", "", NOW)
    assert caught.value.code == "13" and "không xác thực được" in str(caught.value)


def test_momo_results_map_to_outcomes_and_forgeries_are_refused():
    gw = momo()

    def ipn(values: dict):
        return gw.verify_notification(Incoming({}, {}, json.dumps(values).encode()), NOW)

    paid = ipn(momo_result())
    assert (paid.order_id, paid.outcome, paid.amount_vnd, paid.reference) == (
        ORDER,
        OrderStatus.PAID,
        6_000_000,
        "4088878653",
    )
    assert paid.details == {"pay_type": "qr", "response_time": "1791345600000"}
    assert paid.checkout == ORDER  # the request this result answers
    assert gw.verify_return(momo_result(as_text=True)).outcome is OrderStatus.PAID
    assert ipn(momo_result(1006)).outcome is OrderStatus.CANCELLED
    assert ipn(momo_result(1000)).outcome is OrderStatus.PENDING
    assert ipn(momo_result(1001)).outcome is OrderStatus.FAILED
    assert ipn(momo_result(4001)).outcome is OrderStatus.FAILED
    # A code MoMo's table does not call final stays open for a later word.
    assert ipn(momo_result(8000)).outcome is OrderStatus.PENDING
    assert ipn(momo_result() | {"signature": "\u00e9"}) is None
    deep = Incoming({}, {}, b"[" * 100_000 + b"]" * 100_000)
    assert gw.verify_notification(deep, NOW) is None
    assert ipn(momo_result() | {"amount": 6_000}) is None  # a changed amount
    assert ipn(momo_result() | {"partnerCode": "KHAC"}) is None
    assert ipn({k: v for k, v in momo_result().items() if k != "transId"}) is None
    other = MomoGateway("MOMOTHU01", "ACCESSTHU", "khoa-khac", transport=FakeHttp())
    message = Incoming({}, {}, json.dumps(momo_result()).encode())
    assert other.verify_notification(message, NOW) is None  # another secret
    assert gw.verify_notification(Incoming({}, {}, b"khong-phai-json"), NOW) is None
    assert [gw.acknowledge(w).status for w in ("ok", "already", "signature", "error")] == [
        204,
        204,
        400,
        500,
    ]
    assert gw.acknowledge("ok").body is None
    with pytest.raises(ValueError):
        MomoGateway("", "ACCESSTHU", MOMO_SECRET)


# ================================================================= the registry


def settings(**changes) -> Settings:
    base = replace(
        Settings(),
        payment_gateways=("sandbox",),
        payments_live=False,
        vnpay_tmn_code="",
        vnpay_hash_secret="",
        vnpay_url=None,
        stripe_secret_key="",
        stripe_webhook_secret="",
        momo_partner_code="",
        momo_access_key="",
        momo_secret_key="",
        momo_endpoint=None,
    )
    return replace(base, **changes)


def build(**changes):
    return registry.build_gateways(settings(**changes), lambda: b"bi-mat-cong-thu")


def test_the_registry_builds_what_the_settings_ask_for(monkeypatch):
    # The list as written in .env: a blank line means the default, not "none".
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", "  ")
    assert Settings().payment_gateways == ("sandbox",)
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", " Stripe , momo,,")
    assert Settings().payment_gateways == ("stripe", "momo")
    keys = dict(
        vnpay_tmn_code="TMNTHU01",
        vnpay_hash_secret="CHUOIBIMAT",
        stripe_secret_key=SK,
        stripe_webhook_secret=WHSEC,
        momo_partner_code="MOMOTHU01",
        momo_access_key="ACCESSTHU",
        momo_secret_key=MOMO_SECRET,
    )

    gateways, problems = build(payment_gateways=("stripe", "momo", "vnpay", "sandbox"), **keys)

    assert list(gateways) == ["stripe", "momo", "vnpay", "sandbox"]
    assert problems == []
    assert not any(g.live for g in gateways.values())
    # Nothing set but the names: each one missing says what is missing.
    gateways, problems = build(payment_gateways=("stripe", "momo", "vnpay", "paypal", "stripe"))
    assert gateways == {}
    assert any("AICEFR_STRIPE_SECRET_KEY" in p for p in problems)
    assert any("AICEFR_MOMO_PARTNER_CODE" in p for p in problems)
    assert any("AICEFR_VNPAY_TMN_CODE" in p for p in problems)
    assert any("paypal" in p for p in problems)
    assert len(problems) == 4  # the second "stripe" is not reported twice
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
    # Next to a gateway that takes real money, no test environment runs: a
    # Stripe test key beside VNPay's real page would sell a plan for a test card.
    gateways, problems = build(
        payments_live=True,
        payment_gateways=("vnpay", "stripe"),
        vnpay_tmn_code="TMNTHU01",
        vnpay_hash_secret="CHUOIBIMAT",
        vnpay_url="https://pay.vnpay.vn/vpcpay.html",
        stripe_secret_key=SK,
    )
    assert list(gateways) == ["vnpay"]
    assert any(p.startswith("Stripe đã tắt") for p in problems)
    gateways, _ = build(
        payment_gateways=("momo",),
        momo_partner_code="P",
        momo_access_key="A",
        momo_secret_key="S",
        momo_endpoint="https://payment.momo.vn/v2/gateway/api/create",
    )
    assert gateways == {}  # MoMo's real address, without the switch
