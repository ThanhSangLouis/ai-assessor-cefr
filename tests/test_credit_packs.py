"""Run packs (D053): a learner pays through a billing gateway, the runs reach the wallet once."""

from __future__ import annotations

import re

import pytest
from test_billing import boot
from test_lessons_integration import account_id, login_as

from aicefr.billing.payments import OrderStatus

pytestmark = pytest.mark.integration


@pytest.fixture
def m(tmp_path, monkeypatch):
    return boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_METERING="on",
        AICEFR_CREDIT_PACKS="10:49000,30:129000",
    )


def pay(client, runs: int, outcome: str = "paid") -> dict:
    placed = client.post("/api/v1/me/credit-orders", json={"runs": runs})
    assert placed.status_code == 200, placed.text
    order_id = placed.json()["order"]["order_id"]
    page = client.get(placed.json()["checkout_url"])
    token = re.search(r'name="t" value="([^"]+)"', page.text).group(1)
    paid = client.post(
        f"/billing/sandbox/{order_id}/pay",
        data={"t": token, "outcome": outcome},
        follow_redirects=False,
    )
    back = client.get(paid.headers["location"])
    assert back.status_code == 200
    return {"order_id": order_id, "page": back.text}


def test_the_packs_on_sale_are_the_configured_ones(m):
    student = login_as(m, "SV-001")
    body = student.get("/api/v1/me/credit-packs").json()
    assert body["on_sale"] is True
    assert [(p["runs"], p["price_vnd"]) for p in body["packs"]] == [(10, 49000), (30, 129000)]


def test_a_paid_pack_reaches_the_buyers_wallet_once(m):
    student = login_as(m, "SV-001")
    done = pay(student, 10)
    assert "10 lượt" in done["page"] and "/credits" in done["page"]
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 10
    # The gateway says it again: nothing more is credited.
    order = m.billing.store.order(done["order_id"])
    m.billing.credit_order(order)
    assert m.billing.credit_pending() == []
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 10
    mine = student.get("/api/v1/me/credit-packs").json()["orders"]
    assert mine[0]["credited"] is True and mine[0]["plan_name"] == "Gói 10 lượt"


def test_a_failed_payment_credits_nothing(m):
    student = login_as(m, "SV-001")
    pay(student, 10, outcome="failed")
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 0


def test_a_pack_not_on_the_list_is_refused(m):
    student = login_as(m, "SV-001")
    assert student.post("/api/v1/me/credit-orders", json={"runs": 7}).status_code == 422


def test_runs_go_to_the_buyer_only(m):
    buyer, other = login_as(m, "SV-001"), login_as(m, "SV-002")
    pay(buyer, 30)
    assert buyer.get("/api/v1/me/credits").json()["wallet_runs"] == 30
    assert other.get("/api/v1/me/credits").json()["wallet_runs"] == 0
    assert other.get("/api/v1/me/credit-packs").json()["orders"] == []


def test_a_pack_paid_while_metering_was_away_is_credited_later(m, monkeypatch):
    student = login_as(m, "SV-001")
    real = m.billing._credit

    def away(*_a, **_k):
        raise ConnectionError("metering is down")

    monkeypatch.setattr(m.billing, "_credit", away)
    done = pay(student, 10)
    assert m.billing.store.order(done["order_id"])["status"] == OrderStatus.PAID.value
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 0
    monkeypatch.setattr(m.billing, "_credit", real)
    assert m.billing.credit_pending() == [done["order_id"]]
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 10


def test_a_learner_reads_their_own_receipt_but_not_anothers(m):
    buyer, other = login_as(m, "SV-001"), login_as(m, "SV-002")
    order_id = pay(buyer, 10)["order_id"]
    assert buyer.get(f"/billing/orders/{order_id}/receipt").status_code == 200
    assert other.get(f"/billing/orders/{order_id}/receipt").status_code == 403


def test_learner_packs_stay_off_the_administrators_order_list(m):
    pay(login_as(m, "SV-001"), 10)
    admin = login_as(m, "QT-01", "admin", terms=False)
    orders = admin.get("/api/v1/admin/billing").json()["orders"]
    assert all(o["kind"] != "credits" for o in orders)


def test_no_packs_where_runs_are_not_counted(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_BILLING="on")
    student = login_as(m, "SV-001")
    assert student.get("/api/v1/me/credit-packs").json() == {"on_sale": False}
    assert student.post("/api/v1/me/credit-orders", json={"runs": 10}).status_code == 409


def test_the_runs_page_is_listed_only_on_a_metered_deployment(m):
    student = login_as(m, "SV-001")
    assert 'href="/credits"' in student.get("/my-progress").text
    assert account_id(m, "SV-001")
