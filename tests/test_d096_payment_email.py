"""Email for a run-pack payment (D096): a receipt when it is paid, word when it failed.

The billing service publishes `billing.order_settled` on the bus once per order
that ends paid or failed; the identity service, where the addresses are, emails
the buyer. Payments go through the sandbox gateway, the way `test_billing.py`
pays; emails land in the in-memory outbox (`AICEFR_EMAIL_PROVIDER=outbox`).

Test case ids (TC-PE-Ixx) are listed in `docs/test/TEST_PLAN_D096.md`;
tests named after an acceptance criterion carry the name given in SRS FR-101.
"""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from test_billing import PACKS, boot
from test_lessons_integration import login_as

from aicefr.contracts import ORDER_SETTLED
from aicefr.notify import payments
from aicefr.notify.email import outbox
from aicefr.notify.messages import payment_email

pytestmark = pytest.mark.integration

PASSWORD = "-".join(["mot", "cau", "dai", "de", "nho", "123"])
EMAIL = "nguoi.mua@example.edu.vn"
SITE = "https://speakup.example.vn"
PAYMENTS = {
    "AICEFR_BILLING": "on",
    "AICEFR_METERING": "on",
    "AICEFR_CREDIT_PACKS": PACKS,  # 10 runs for 49,000 dong
    "AICEFR_EMAIL_PROVIDER": "outbox",
    "AICEFR_PUBLIC_URL": SITE,
}


@pytest.fixture
def m(tmp_path, monkeypatch):
    outbox().sent.clear()
    return boot(tmp_path, monkeypatch, **PAYMENTS)


def verified_buyer(m) -> TestClient:
    """A learner who signed up with an email and proved it with the code."""
    c = TestClient(m.app)
    r = c.post(
        "/api/v1/auth/signup", json={"email": EMAIL, "full_name": "Trần Bình", "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    code = re.search(r"\b(\d{6})\b", outbox().sent[-1].text).group(1)
    assert c.post("/api/v1/me/email/verify", json={"code": code}).status_code == 200
    outbox().sent.clear()
    return c


def pay(buyer, outcome: str) -> str:
    """Order 10 runs through the sandbox and pick the outcome on its page; the order id."""
    placed = buyer.post("/api/v1/me/credit-orders", json={"runs": 10}).json()
    url = urlparse(placed["checkout_url"])
    token = parse_qs(url.query)["t"][0]
    order_id = placed["order"]["order_id"]
    page = buyer.post(f"/billing/sandbox/{order_id}/pay", data={"t": token, "outcome": outcome})
    assert page.status_code == 200
    return order_id


def test_a_paid_order_emails_its_buyer_a_receipt_once(m):
    buyer = verified_buyer(m)

    order_id = pay(buyer, "paid")

    [email] = outbox().sent
    assert email.to == EMAIL
    assert email.subject == f"Đã thanh toán gói 10 lượt · {order_id}"
    for words in ("Chào Trần Bình", "49.000 đ", "Cổng thử", "đã được cộng vào ví", order_id):
        assert words in email.text, words
    assert f"{SITE}/billing/orders/{order_id}/receipt" in email.text
    assert f'href="{SITE}/billing/orders/{order_id}/receipt"' in email.html
    assert "môi trường thử" in email.text  # the sandbox moves no money, and says so
    # The browser's return and the gateway's notification both report it; the
    # order is settled once, so the buyer hears it once.
    buyer.get(f"/billing/orders/{order_id}/receipt")
    assert len(outbox().sent) == 1
    assert buyer.get("/api/v1/me/credits").json()["wallet_runs"] == 10


def test_a_failed_payment_says_so_and_nothing_was_taken(m):
    buyer = verified_buyer(m)

    order_id = pay(buyer, "failed")

    [email] = outbox().sent
    assert email.subject == f"Thanh toán chưa thành công · {order_id}"
    assert "Không có lượt nào bị trừ hay được cộng" in email.text
    assert f"{SITE}/credits" in email.text and "/receipt" not in email.text
    assert buyer.get("/api/v1/me/credits").json()["wallet_runs"] == 0


def test_only_a_verified_address_hears_and_a_cancel_says_nothing(m):
    buyer = verified_buyer(m)
    pay(buyer, "cancelled")  # the buyer left on purpose: nothing to tell
    assert outbox().sent == []
    # No address at all (the seeded learner), or one never verified: no email,
    # and the payment itself goes through untouched.
    plain = login_as(m, "SV-001")
    pay(plain, "paid")
    assert outbox().sent == []
    assert plain.get("/api/v1/me/credits").json()["wallet_runs"] == 10


def test_a_second_delivery_of_the_event_sends_no_second_email(m):
    buyer = verified_buyer(m)
    order_id = pay(buyer, "paid")
    account_id = buyer.get("/api/v1/me").json()["account_id"]
    order = m.billing_store.order(order_id)
    payload = {
        "order_id": order_id,
        "account_id": account_id,
        "status": "paid",
        "runs": 10,
        "amount_vnd": 49_000,
        "gateway_title": "Cổng thử",
        "reference": order["reference"],
        "live": False,
        "settled_at": order["settled_at"],
    }

    # Redis Streams may hand the same event over again (at least once).
    again = payments.on_order_settled(payload, m.app.state.auth_repo, outbox(), SITE)

    assert again is False and len(outbox().sent) == 1
    assert ORDER_SETTLED == "billing.order_settled"


def test_the_payment_email_says_what_was_bought_and_nothing_secret():
    order = {
        "order_id": "DL26110788C3E0",
        "status": "paid",
        "runs": 30,
        "amount_vnd": 129_000,
        "gateway_title": "payOS",
        "reference": "FT2611070001",
        "live": True,
    }

    email = payment_email(EMAIL, "Bình", order, SITE)

    assert "129.000 đ" in email.text and "payOS" in email.text and "FT2611070001" in email.text
    assert "môi trường thử" not in email.text  # real money: no test note
    assert "quản trị viên" in email.text  # what to do if it was not you
    for secret in ("mật khẩu", "số thẻ", "Checksum", "x-api-key"):
        assert secret not in email.text
    bare = payment_email(EMAIL, "Bình", order | {"status": "failed"}, "")
    assert "http" not in bare.text  # no public address set: no link rather than a broken one


def test_with_email_off_a_payment_still_settles(tmp_path, monkeypatch):
    outbox().sent.clear()
    m = boot(tmp_path, monkeypatch, **(PAYMENTS | {"AICEFR_EMAIL_PROVIDER": "off"}))
    buyer = login_as(m, "SV-001")

    order_id = pay(buyer, "paid")

    assert m.billing_store.order(order_id)["status"] == "paid"
    assert buyer.get("/api/v1/me/credits").json()["wallet_runs"] == 10
    assert outbox().sent == []


@pytest.mark.skipif(not os.getenv("AICEFR_TEST_REDIS"), reason="AICEFR_TEST_REDIS is not set")
def test_the_order_event_crosses_redis_and_one_email_goes_out():
    """The production path: Redis Streams with a consumer group, which delivers
    at least once. The same event sent twice still makes one email."""
    from aicefr.platform.redis_bus import RedisBus
    from aicefr.storage.auth_repository import AuthRepository, Role

    url = os.environ["AICEFR_TEST_REDIS"]
    auth = AuthRepository(f"mongomock://redis-email-{uuid.uuid4().hex[:8]}")
    account_id = auth.create_account("SV-R01", PASSWORD, Role.STUDENT)
    auth.col("account").update_one(
        {"account_id": account_id}, {"$set": {"email": EMAIL, "email_verified": 1}}
    )
    outbox().sent.clear()
    handled, both = [], threading.Event()

    def on_event(payload: dict) -> None:
        handled.append(payments.on_order_settled(payload, auth, outbox(), SITE))
        if len(handled) == 2:
            both.set()

    subscriber = RedisBus(url)
    subscriber.subscribe(ORDER_SETTLED, f"test-{uuid.uuid4().hex[:8]}-payment-email", on_event)
    subscriber.start()
    try:
        time.sleep(1.0)  # the consumer group exists once its reader has declared it
        order_id = "DL261107" + uuid.uuid4().hex[:6].upper()
        payload = {
            "order_id": order_id,
            "account_id": account_id,
            "status": "paid",
            "runs": 10,
            "amount_vnd": 49_000,
            "gateway_title": "payOS",
            "reference": "FT2611070001",
            "live": True,
            "settled_at": "2026-11-07T10:05:00+00:00",
        }
        publisher = RedisBus(url)
        publisher.publish(ORDER_SETTLED, payload)
        publisher.publish(ORDER_SETTLED, payload)  # a second delivery of the same event

        assert both.wait(15), "the events did not come back through Redis"
        assert sorted(handled) == [False, True]
        [email] = outbox().sent
        assert email.to == EMAIL and order_id in email.subject
    finally:
        subscriber.close()


@pytest.mark.unit
def test_the_receipt_email_is_a_branded_card_mail_clients_can_draw():
    order = {
        "order_id": "DL26110788C3E0",
        "status": "paid",
        "runs": 30,
        "amount_vnd": 129_000,
        "gateway_title": "payOS",
        "reference": "FT2611070001",
        "live": True,
        "settled_at": "2026-11-07T10:40:00+00:00",
    }

    html = payment_email(EMAIL, "<b>Bình</b>", order, SITE).html

    # Tables and inline styles only: Gmail and Outlook drop <style> and classes.
    assert "<style" not in html and "class=" not in html and "<table" in html
    assert "Đã nhận 129.000 đ · +30 lượt vào ví" in html  # the inbox preview line
    assert "+30" in html and "07/11/2026 17:40" in html  # the number, the Vietnam time
    assert f'src="{SITE}/static/favicon.png"' in html  # the logo is linked, not attached
    assert f'href="{SITE}/billing/orders/DL26110788C3E0/receipt"' in html
    assert f'href="{SITE}/practice"' in html
    assert "<b>Bình</b>" not in html and "&lt;b&gt;Bình&lt;/b&gt;" in html  # names are escaped
    failed = payment_email(EMAIL, "Bình", order | {"status": "failed"}, SITE).html
    assert "Thanh toán chưa thành công" in failed and "+30" not in failed
    assert f'href="{SITE}/credits"' in failed
