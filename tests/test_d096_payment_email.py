"""Email for a run-pack payment (D096): a receipt when it is paid, word when it failed.

The billing service publishes `billing.order_settled` on the bus once per order
that ends paid or failed; the identity service, where the addresses are, emails
the buyer. Payments go through the sandbox gateway, the way `test_billing.py`
pays; emails land in the in-memory outbox (`AICEFR_EMAIL_PROVIDER=outbox`).

Test case ids (TC-PE-Ixx) are listed in `docs/test/TEST_PLAN_D096.md`;
tests named after an acceptance criterion carry the name given in SRS FR-101.
"""

from __future__ import annotations

import re
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
