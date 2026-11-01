"""Layer 2 -- INTEGRATION: payments through the real API and database (D035, D075).

One centre, no service plans (D075): what takes money is a pack of runs, bought
by the person who will use it through a payment gateway. The application is
reloaded per test; the sandbox gateway runs exactly as the app wires it, and
VNPay with a test merchant code and secret, its messages built and signed here
the way VNPay signs them. Nothing leaves the machine.

`boot` is shared by the other integration tests that need settings of their own.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
from test_lessons_integration import KEYWORD_TEXT, login_as

from aicefr import config
from aicefr.asr.vad import EnergyVad

pytestmark = pytest.mark.integration

PACKS = "10:49000,30:129000"


def boot(tmp_path, monkeypatch, **env):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", KEYWORD_TEXT)
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    return main


@pytest.fixture
def m(tmp_path, monkeypatch):
    """Payments and the metered channel on, the sandbox gateway, two packs."""
    return boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_METERING="on",
        AICEFR_CREDIT_PACKS=PACKS,
    )


# ================================================================= one centre, no plans


def test_every_staff_tool_is_open_without_a_plan(m):
    """D075: writing paths, class statistics and blind rating are never locked."""
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình riêng"}).status_code == 200
    assert teacher.get("/api/v1/review/stats").status_code == 200
    assert teacher.get("/api/v1/teach/insights").status_code in (200, 404)


def test_accounts_are_not_limited_by_seats(m):
    admin = login_as(m, "QT-01", "admin")
    made = admin.post("/api/v1/admin/accounts", json={"role": "student", "count": 60})
    assert made.status_code == 200, made.text


def test_the_plan_routes_are_gone(m):
    admin = login_as(m, "QT-01", "admin")
    for method, path in (
        ("GET", "/api/v1/plan"),
        ("GET", "/api/v1/admin/billing"),
        ("POST", "/api/v1/admin/billing/orders"),
        ("POST", "/api/v1/admin/billing/license"),
    ):
        assert admin.request(method, path, json={}).status_code in (404, 405), path


# ================================================================= signed results


def test_a_forged_or_altered_result_is_refused(m):
    student = login_as(m, "SV-001")
    placed = student.post("/api/v1/me/credit-orders", json={"runs": 10}).json()
    order_id = placed["order"]["order_id"]
    gw = m.billing.gateways["sandbox"]
    good = gw.result(order_id, 49_000, "paid", datetime.now(UTC))

    forged = good | {"sig": "0" * 64}
    page = student.get("/billing/return/sandbox?" + urlencode(forged))
    assert "Không xác nhận được kết quả thanh toán" in page.text
    notify = "/api/v1/billing/notify/sandbox?"
    assert student.get(notify + urlencode(forged)).json()["RspCode"] == "97"
    cheaper = gw.result(order_id, 1_000, "paid", datetime.now(UTC))  # signed, wrong amount
    assert student.get(notify + urlencode(cheaper)).json()["RspCode"] == "04"
    stranger = gw.result("DL000000000000", 49_000, "paid", datetime.now(UTC))
    assert student.get(notify + urlencode(stranger)).json()["RspCode"] == "01"
    assert m.billing_store.order(order_id)["status"] == "pending"
    assert student.get(f"/billing/sandbox/{order_id}?t=sai").status_code == 404
    assert student.get("/api/v1/billing/notify/vnpay?x=1").status_code == 404  # D075: removed


def test_payments_are_audited(m):
    student = login_as(m, "SV-001")
    order_id = student.post("/api/v1/me/credit-orders", json={"runs": 10}).json()["order"][
        "order_id"
    ]
    admin = login_as(m, "QT-01", "admin")
    actions = [(a["action"], a["target_id"]) for a in admin.get("/api/v1/audit").json()]
    assert ("billing.credit_order", order_id) in actions
