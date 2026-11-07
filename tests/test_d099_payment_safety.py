"""Layer 2 -- INTEGRATION: the safety net around real payments (D099).

Reconciliation asks payOS about orders still open, so a transfer whose
webhook never came and whose payer never came back is still credited; a buyer
cannot open payment links without end; the administrator sees every order.
payOS is the fake of `test_d095_payos.py`: nothing leaves the machine.

Test case ids (TC-PG-Ixx) are listed in `docs/test/TEST_PLAN_D099.md`.
"""

from __future__ import annotations

import pytest
from test_billing import m  # noqa: F401
from test_d095_payos import BODY, PRICE, path_of, payos, place, wallet  # noqa: F401
from test_lessons_integration import login_as

from aicefr.billing.service import OPEN_ORDER_LIMIT

pytestmark = pytest.mark.integration


def test_reconcile_credits_a_payment_nobody_reported(payos):  # noqa: F811
    """TC-PG-I01: paid at payOS, no webhook, no return: reconciliation credits it once."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    before = wallet(buyer)
    order = place(buyer)["order"]
    [link_id] = fake.links
    fake.pay(link_id)  # the payer transfers, then closes the tab

    assert app.billing.reconcile() == [order["order_id"]]
    assert app.billing.reconcile() == []  # settled: never asked again, never credited twice

    assert wallet(buyer) == before + 10
    events = [e["kind"] for e in app.billing.store.events(order["order_id"])]
    assert "reconcile" in events and "credited" in events


def test_reconcile_leaves_an_unpaid_link_waiting(payos):  # noqa: F811
    """TC-PG-I02: payOS has no final word yet: the order stays pending and nothing is kept."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    order = place(buyer)["order"]

    assert app.billing.reconcile() == []

    kept = app.billing.store.order(order["order_id"])
    assert kept["status"] == "pending"
    assert [e["kind"] for e in app.billing.store.events(order["order_id"])] == ["created"]


def test_reconcile_skips_a_gateway_that_cannot_be_asked(m):  # noqa: F811
    """TC-PG-I03: the sandbox has no link to read back: its orders wait as they were."""
    buyer = login_as(m, "SV-001")
    r = buyer.post("/api/v1/me/credit-orders", json={"runs": 10})
    assert r.status_code == 200, r.text

    assert m.billing.reconcile() == []
    assert m.billing.store.order(r.json()["order"]["order_id"])["status"] == "pending"


def test_too_many_waiting_orders_are_refused(payos):  # noqa: F811
    """TC-PG-I04: the sixth order still waiting within ten minutes opens no link: 429."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    for _ in range(OPEN_ORDER_LIMIT):
        place(buyer)

    r = buyer.post("/api/v1/me/credit-orders", json=BODY)

    assert r.status_code == 429
    assert "đơn chờ thanh toán" in r.json()["detail"]
    assert len(fake.links) == OPEN_ORDER_LIMIT
    # Another buyer is not held back by this one.
    assert place(login_as(app, "SV-002"))["order"]["amount_vnd"] == PRICE


def test_a_paid_order_frees_its_place(payos):  # noqa: F811
    """TC-PG-I05: only orders still waiting count: one paid makes room for another."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    for _ in range(OPEN_ORDER_LIMIT):
        place(buyer)
    first = next(iter(fake.links))
    buyer.get(path_of(fake.pay(first)))

    assert buyer.post("/api/v1/me/credit-orders", json=BODY).status_code == 200


def test_the_administrator_sees_every_order_and_the_money_of_each_day(payos):  # noqa: F811
    """TC-PG-I06: newest first with the buyer's code, counts by status, today's money, events."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    paid = place(buyer)["order"]
    waiting = place(buyer)["order"]
    buyer.get(path_of(fake.pay(next(iter(fake.links)))))
    admin = login_as(app, "QT-01", "admin")

    d = admin.get("/api/v1/admin/credit-orders").json()

    assert [o["order_id"] for o in d["orders"]] == [waiting["order_id"], paid["order_id"]]
    assert {o["buyer"] for o in d["orders"]} == {"SV-001"}
    assert d["counts"] == {"paid": 1, "pending": 1} and d["live"] is True
    assert len(d["days"]) == 14 and d["days"][-1] == {
        "date": app.billing.today().isoformat(), "paid": 1, "revenue_vnd": PRICE,
    }  # fmt: skip
    only_paid = admin.get("/api/v1/admin/credit-orders?status=paid").json()["orders"]
    assert [o["order_id"] for o in only_paid] == [paid["order_id"]]
    events = admin.get(f"/api/v1/admin/credit-orders/{paid['order_id']}/events").json()
    assert [e["kind"] for e in events["events"]][:2] == ["created", "return"]
    assert admin.get("/api/v1/admin/credit-orders?status=nope").status_code == 422


def test_only_the_administrator_reads_the_orders(payos):  # noqa: F811
    """TC-PG-I07: a learner or a teacher is refused the list and the events of an order."""
    app, fake = payos
    buyer = login_as(app, "SV-001")
    order = place(buyer)["order"]
    teacher = login_as(app, "GV-01", "teacher")

    for who in (buyer, teacher):
        assert who.get("/api/v1/admin/credit-orders").status_code == 403
        assert who.get(f"/api/v1/admin/credit-orders/{order['order_id']}/events").status_code == 403


def test_the_terms_are_open_and_linked_from_the_buy_page(payos, monkeypatch):  # noqa: F811
    """TC-PG-I08: the terms open to all, say the refund rule and name the contact."""
    app, fake = payos
    monkeypatch.setenv("AICEFR_SUPPORT_EMAIL", "hotro@speakup.fit")
    from aicefr import config

    config.get_settings.cache_clear()
    from fastapi.testclient import TestClient

    page = TestClient(app.app).get("/payment-terms")

    assert page.status_code == 200
    assert "Hoàn tiền 7 ngày" in page.text and "hotro@speakup.fit" in page.text
    assert "không phải hoá đơn VAT" in page.text
    credits = login_as(app, "SV-001").get("/credits").text
    assert 'href="/payment-terms"' in credits
