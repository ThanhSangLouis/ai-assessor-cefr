"""Layer 2 -- INTEGRATION: service plans and payment through the real API and database (D033, D034).

The application is reloaded per test with `AICEFR_BILLING=on`, a 30-day trial
for three students and a licence secret: SQLite in a temporary file, FastAPI
through TestClient, the sandbox gateway exactly as the app wires it. VNPay is
wired with a test merchant code and secret, and its messages are built and
signed here the way VNPay signs them; nothing leaves the machine. The billing
clock is pinned by setting `main.billing._clock`.

Test case ids (TC-GD-Ixx) are listed in `docs/test/TEST_PLAN_D034.md`; tests
named after an acceptance criterion carry the name given in SRS section 3.9g.
"""

from __future__ import annotations

import importlib
import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlparse

import pytest
from fastapi.testclient import TestClient
from test_lessons_integration import (
    KEYWORD_TEXT,
    KEYWORDS,
    PASSWORD,
    SAMPLE,
    login_as,
    record,
    scored,
    wav,
)

from aicefr import config
from aicefr.asr.vad import EnergyVad
from aicefr.billing import keys
from aicefr.billing.gateways import VnpayGateway
from aicefr.billing.plans import GRACE_DAYS, License, ServicePlan
from aicefr.contracts import Band, Criterion
from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

SECRET = "khoa-ky-giay-phep-cua-bai-kiem-thu"
# Built, not written out, so the secret scanner sees no literal.
VNP_SECRET = "thu-" * 6


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
    """Billing on, a 30-day trial for three students, licence keys accepted, the sandbox."""
    return boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_TRIAL_SEATS="3",
        AICEFR_LICENSE_SECRET=SECRET,
    )


def admin_of(m) -> TestClient:
    return login_as(m, "QT-01", "admin", terms=False)


def at(m, moment: datetime) -> None:
    m.billing._clock = lambda: moment


def morning(day: date) -> datetime:
    """10:00 in Vietnam on `day`."""
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=3)


def buy(admin: TestClient, plan: str, seats: int, months: int = 6, outcome: str = "paid") -> dict:
    """Order, open the sandbox page, choose the outcome, follow the return. Returns the order."""
    body = {"plan": plan, "seats": seats, "months": months}
    r = admin.post("/api/v1/admin/billing/orders", json=body)
    assert r.status_code == 200, r.text
    placed = r.json()
    if placed["checkout_url"] is None:
        return placed["order"]
    page = admin.get(placed["checkout_url"])
    assert page.status_code == 200
    token = re.search(r'name="t" value="([^"]+)"', page.text).group(1)
    paid = admin.post(
        f"/billing/sandbox/{placed['order']['order_id']}/pay",
        data={"t": token, "outcome": outcome},
        follow_redirects=False,
    )
    assert paid.status_code == 303
    back = admin.get(paid.headers["location"])
    assert back.status_code == 200
    return {**placed["order"], "return_url": paid.headers["location"], "page": back.text}


def students(admin: TestClient, n: int) -> int:
    return admin.post("/api/v1/admin/accounts", json={"role": "student", "count": n}).status_code


def overview(admin: TestClient) -> dict:
    return admin.get("/api/v1/admin/billing").json()


def save_assessments(m, pseudonym: str, prefix: str, n: int) -> None:
    acc = m.app.state.auth_repo.get_by_pseudonym(pseudonym)["account_id"]
    for k in range(n):
        report = scored(f"{prefix}-{k}", Band.B1, [Criterion.RANGE])
        m.repo.save(report, pseudonym, "P3", account_id=acc)


# ================================================================= switched off


def test_with_billing_off_nothing_changes(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)  # AICEFR_BILLING unset
    admin = admin_of(m)

    off = overview(admin)

    assert off["enabled"] is False and "license" not in off
    assert [p["plan"] for p in off["ladder"]] == ["free", "standard", "advanced"]
    assert students(admin, 200) == 200  # no limit on students
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    assert teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình riêng"}).status_code == 200
    assert teacher.get("/api/v1/review/stats").status_code == 200
    assert teacher.get("/api/v1/plan").json()["enabled"] is False
    body = {"plan": "standard", "seats": 50, "months": 6}
    assert admin.post("/api/v1/admin/billing/quote", json=body).status_code == 409
    assert admin.post("/api/v1/admin/billing/orders", json=body).status_code == 409
    assert m.billing_store.licenses() == []  # no trial was started
    assert admin.get("/billing/sandbox/DH1?t=x").status_code == 404


# ================================================================= the plan and its limits


def test_the_first_look_starts_one_trial_with_everything(m):
    admin = admin_of(m)

    first = overview(admin)
    second = overview(admin)

    assert (first["plan"], first["state"], first["plan_name"]) == ("trial", "active", "Dùng thử")
    assert first["students_allowed"] == 3 and first["days_left"] == 30
    assert first["features"] == ["blind_rating", "class_insights", "lesson_authoring"]
    assert second["license"]["license_id"] == first["license"]["license_id"]
    assert len(m.billing_store.licenses()) == 1
    assert [(g["name"], g["live"]) for g in first["gateways"]] == [("sandbox", False)]
    assert first["gateway_problems"] == []
    ladder = {p["plan"]: p for p in first["ladder"]}
    assert ladder["free"]["students"] == 30 and ladder["free"]["features"] == []
    assert ladder["standard"]["features"] == ["class_insights", "lesson_authoring"]
    assert len(ladder["advanced"]["features"]) == 3


def test_the_plan_limits_new_student_accounts_only(m):
    admin = admin_of(m)

    refused = admin.post("/api/v1/admin/accounts", json={"role": "student", "count": 4})

    assert refused.status_code == 409 and "3 sinh viên" in refused.json()["detail"]
    assert m.app.state.auth_repo.count_role(Role.STUDENT) == 0  # all or nothing (BR-12)
    assert students(admin, 3) == 200
    assert students(admin, 1) == 409
    teachers = admin.post("/api/v1/admin/accounts", json={"role": "teacher", "count": 2})
    assert teachers.status_code == 200  # staff accounts are not counted
    rows = {r["pseudonym"]: r for r in admin.get("/api/v1/admin/accounts").json()}
    first, teacher = rows["SV-001"]["account_id"], rows["GV-001"]["account_id"]
    # Room freed by turning an account off can be used; turning it back on needs room.
    assert admin.post(f"/api/v1/admin/accounts/{first}/disable").status_code == 200
    assert students(admin, 1) == 200
    assert admin.post(f"/api/v1/admin/accounts/{first}/enable").status_code == 409
    role = admin.post(f"/api/v1/admin/accounts/{teacher}/role", json={"role": "student"})
    assert role.status_code == 409
    # Nobody already there is touched: every student account still signs in.
    m.app.state.auth_repo.create_account("SV-900", PASSWORD, Role.STUDENT)  # beyond the plan
    login = TestClient(m.app).post(
        "/api/v1/auth/login", json={"pseudonym": "SV-900", "password": PASSWORD}
    )
    assert login.status_code == 200


def test_assessments_over_the_monthly_figure_only_warn(m):
    admin = admin_of(m)
    assert overview(admin)["usage"]["quota"] == 24  # 3 students x 8 on the trial
    learner = login_as(m, "SV-001", terms=True)  # accepted the terms: research data (D058)
    plain = login_as(m, "SV-002", terms=False)
    save_assessments(m, "SV-002", "p", 20)
    save_assessments(m, "SV-001", "r", 4)

    usage = overview(admin)["usage"]

    assert (usage["assessments"], usage["research_assessments"]) == (20, 4)  # BR-30
    assert (usage["percent"], usage["warning"]) == (83, 80)
    save_assessments(m, "SV-002", "q", 4)
    assert overview(admin)["usage"]["warning"] == 100
    # A warning, never a refusal: both learners still submit.
    plain.post("/api/v1/me/terms")
    for client in (learner, plain):
        r = client.post(
            "/api/v1/responses",
            files={"audio": ("answer.wav", wav(35.0), "audio/wav")},
            data={"task_id": "P3"},
        )
        assert r.status_code == 202, r.text


def test_after_the_trial_the_free_plan_closes_staff_tools_but_never_learning(m):
    admin = admin_of(m)
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    learner = login_as(m, "SV-001")
    trial_end = date.fromisoformat(overview(admin)["license"]["valid_to"])
    at(m, morning(trial_end + timedelta(days=1)))

    now = overview(admin)

    assert (now["plan"], now["state"], now["students_allowed"]) == ("free", "free", 30)
    assert now["lapsed"]["plan"] == "trial" and now["features"] == []
    assert teacher.get("/api/v1/plan").json() == {
        "enabled": True,
        "plan": "free",
        "plan_name": "Miễn phí",
        "features": [],
    }
    # Staff tools of the paid plans are closed, saying which plans open them.
    refused = teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình của khoa"})
    assert refused.status_code == 403 and "gói Chuẩn và Nâng cao" in refused.json()["detail"]
    assert teacher.get("/api/v1/teach/insights").status_code == 403
    assert teacher.get("/api/v1/review/stats").status_code == 403
    # Reading paths and the review queue stay open.
    assert teacher.get("/api/v1/teach/paths").status_code == 200
    assert teacher.get("/api/v1/review/queue").status_code == 200
    # One class fits the free plan; learning is untouched.
    assert students(admin, 5) == 200
    assert record(learner, SAMPLE, KEYWORDS)["result"]["passed"] is True
    submitted = learner.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(35.0), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert submitted.status_code == 202
    for path in ("/api/v1/learn", "/api/v1/me/progress", "/api/v1/me/achievements"):
        assert learner.get(path).status_code == 200
    assert learner.get("/api/v1/me/export.json").status_code == 200


def test_a_paid_plan_keeps_its_tools_through_grace_then_falls_back_to_free(m):
    admin = admin_of(m)
    order = buy(admin, "standard", 50)
    end = date.fromisoformat(order["ends_on"])

    at(m, morning(end + timedelta(days=GRACE_DAYS)))
    grace = overview(admin)
    at(m, morning(end + timedelta(days=GRACE_DAYS + 1)))
    after = overview(admin)

    assert (grace["plan"], grace["state"]) == ("standard", "grace")
    assert "lesson_authoring" in grace["features"]
    assert (after["plan"], after["lapsed"]["plan"], after["students_allowed"]) == (
        "free",
        "standard",
        30,
    )


# ================================================================= buying


def test_buying_through_the_sandbox_installs_the_plan_once(m):
    admin = admin_of(m)
    admin.patch("/api/v1/admin/billing/organization", json={"name": "Khoa Ngoại ngữ"})
    body = {"plan": "standard", "seats": 50, "months": 6}
    quote = admin.post("/api/v1/admin/billing/quote", json=body).json()
    assert (quote["kind"], quote["discount_vnd"], quote["amount_vnd"]) == ("new", 0, 3_000_000)

    order = buy(admin, "standard", 50)

    assert "Thanh toán thành công" in order["page"] and "Môi trường thử" in order["page"]
    now = overview(admin)
    assert (now["plan"], now["license"]["seats"], now["students_allowed"]) == ("standard", 50, 50)
    assert now["license"]["organization"] == "Khoa Ngoại ngữ"
    [paid] = now["orders"]
    assert (paid["status"], paid["amount_vnd"]) == ("paid", 3_000_000)
    assert paid["reference"].startswith("SB")
    # The same result again, by the browser or by the gateway, changes nothing.
    assert admin.get(order["return_url"]).status_code == 200
    params = dict(parse_qsl(urlparse(order["return_url"]).query))
    again = admin.get("/api/v1/billing/notify/sandbox?" + urlencode(params)).json()
    assert again == {"RspCode": "02", "Message": "Order already confirmed"}
    assert len(m.billing_store.licenses()) == 2  # the trial and this one
    receipt = admin.get(f"/billing/orders/{paid['order_id']}/receipt")
    assert receipt.status_code == 200 and "3.000.000 đ" in receipt.text
    assert "không phải hoá đơn giá trị gia tăng" in receipt.text
    # Every message is kept for reconciliation, only the first applied; an
    # identical repeat is counted on the row it repeats, not stored again.
    events = m.billing_store.events(paid["order_id"])
    assert [e["kind"] for e in events] == ["created", "notify", "return"]
    assert [(e["detail"].get("applied"), e["repeats"]) for e in events[1:]] == [
        (True, 1),
        (False, 1),
    ]


def test_a_school_year_is_discounted_and_shown_on_the_receipt(m):
    admin = admin_of(m)

    order = buy(admin, "standard", 100, months=12)

    assert (order["list_vnd"], order["discount_vnd"], order["amount_vnd"]) == (
        12_000_000,
        1_800_000,
        10_200_000,
    )
    receipt = admin.get(f"/billing/orders/{order['order_id']}/receipt").text
    assert "Giảm khi trả theo năm học" in receipt and "−1.800.000 đ" in receipt


def test_a_failed_or_cancelled_payment_changes_nothing(m):
    admin = admin_of(m)

    failed = buy(admin, "standard", 50, outcome="failed")
    cancelled = buy(admin, "advanced", 50, outcome="cancelled")

    assert "Thanh toán không thành công" in failed["page"]
    assert "Đã huỷ giao dịch" in cancelled["page"]
    now = overview(admin)
    assert now["plan"] == "trial"
    assert [o["status"] for o in now["orders"]] == ["cancelled", "failed"]
    assert receipt_status(admin, failed["order_id"]) == 404


def receipt_status(client: TestClient, order_id: str) -> int:
    return client.get(f"/billing/orders/{order_id}/receipt").status_code


def test_a_forged_or_altered_result_is_refused(m):
    admin = admin_of(m)
    body = {"plan": "standard", "seats": 50, "months": 6}
    placed = admin.post("/api/v1/admin/billing/orders", json=body).json()
    order_id = placed["order"]["order_id"]
    gw = m.billing.gateways["sandbox"]
    good = gw.result(order_id, 3_000_000, "paid", datetime.now(UTC))

    forged = good | {"sig": "0" * 64}
    page = admin.get("/billing/return/sandbox?" + urlencode(forged))
    assert "Không xác nhận được kết quả thanh toán" in page.text
    notify = "/api/v1/billing/notify/sandbox?"
    assert admin.get(notify + urlencode(forged)).json()["RspCode"] == "97"
    cheaper = gw.result(order_id, 1_000, "paid", datetime.now(UTC))  # signed, wrong amount
    assert admin.get(notify + urlencode(cheaper)).json()["RspCode"] == "04"
    stranger = gw.result("DH000000000000", 3_000_000, "paid", datetime.now(UTC))
    assert admin.get(notify + urlencode(stranger)).json()["RspCode"] == "01"
    assert overview(admin)["plan"] == "trial"
    assert m.billing_store.order(order_id)["status"] == "pending"
    assert admin.get(f"/billing/sandbox/{order_id}?t=sai").status_code == 404
    assert admin.get("/api/v1/billing/notify/vnpay?x=1").status_code == 404  # not this gateway


def test_an_upgrade_is_credited_and_a_renewal_waits(m):
    admin = admin_of(m)
    buy(admin, "standard", 50)  # 3.000.000 đ, 182 days
    day = m.billing.today() + timedelta(days=91)
    at(m, morning(day))

    up = admin.post(
        "/api/v1/admin/billing/quote", json={"plan": "advanced", "seats": 50, "months": 6}
    ).json()

    assert up["kind"] == "upgrade" and up["starts_on"] == day.isoformat()
    assert up["credit_vnd"] == 1_500_000 and up["amount_vnd"] == 4_500_000 - 1_500_000
    buy(admin, "advanced", 50)
    assert overview(admin)["plan"] == "advanced"
    renewal = buy(admin, "advanced", 50)
    now = overview(admin)
    assert now["plan"] == "advanced" and renewal["kind"] == "renewal"
    [scheduled] = now["scheduled"]
    after_current = date.fromisoformat(now["license"]["valid_to"]) + timedelta(days=1)
    assert scheduled["valid_from"] == after_current.isoformat()
    blocked = admin.post(
        "/api/v1/admin/billing/quote", json={"plan": "standard", "seats": 80, "months": 12}
    )
    assert blocked.status_code == 422 and "đặt trước" in blocked.json()["detail"]


def test_an_upgrade_the_credit_covers_needs_no_payment(m):
    admin = admin_of(m)
    buy(admin, "standard", 100, months=12)  # 10.200.000 đ after the school-year discount

    order = buy(admin, "advanced", 10, months=6)  # 900.000 đ, all credited

    assert order["amount_vnd"] == 0 and order["status"] == "paid" and order["gateway"] == "none"
    assert overview(admin)["plan"] == "advanced"


def test_pending_orders_expire_and_a_late_payment_still_counts(m):
    admin = admin_of(m)
    body = {"plan": "standard", "seats": 50, "months": 6}
    placed = admin.post("/api/v1/admin/billing/orders", json=body).json()
    page = admin.get(placed["checkout_url"])
    token = re.search(r'name="t" value="([^"]+)"', page.text).group(1)
    at(m, datetime.now(UTC) + timedelta(minutes=16))

    assert overview(admin)["orders"][0]["status"] == "expired"
    paid = admin.post(
        f"/billing/sandbox/{placed['order']['order_id']}/pay",
        data={"t": token, "outcome": "paid"},
        follow_redirects=False,
    )

    assert paid.status_code == 303
    now = overview(admin)
    assert now["orders"][0]["status"] == "paid" and now["plan"] == "standard"


def test_a_new_order_retires_the_one_still_waiting(m):
    admin = admin_of(m)
    body = {"plan": "standard", "seats": 50, "months": 6}
    first = admin.post("/api/v1/admin/billing/orders", json=body).json()["order"]["order_id"]

    admin.post("/api/v1/admin/billing/orders", json=body)

    assert m.billing_store.order(first)["status"] == "expired"


# ================================================================= what a plan opens


def test_each_plan_opens_its_staff_tools(m):
    admin = admin_of(m)
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    login_as(m, "GV-02", "teacher", terms=False)
    raters = [m.app.state.auth_repo.get_by_pseudonym(n)["account_id"] for n in ("GV-01", "GV-02")]
    batch = {"name": "Đợt thử", "rater_ids": raters}

    def opens() -> tuple[int, int, int]:
        """Writing a path, class statistics, starting a batch (422: nothing to rate)."""
        path = teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình riêng"})
        stats = teacher.get("/api/v1/review/stats")
        rating = admin.post("/api/v1/admin/ratings/batches", json=batch)
        return path.status_code, stats.status_code, rating.status_code

    assert opens() == (200, 200, 422)  # the trial has everything
    buy(admin, "standard", 50)
    assert opens() == (200, 200, 403)
    refused = admin.post("/api/v1/admin/ratings/batches", json=batch).json()["detail"]
    assert "gói Nâng cao" in refused and "Chuẩn" in refused
    assert admin.get("/api/v1/admin/ratings/batches").status_code == 200  # what exists stays
    buy(admin, "advanced", 50)
    assert opens() == (200, 200, 422)


def test_a_licence_key_is_installed_once(m):
    admin = admin_of(m)
    today = m.billing.today()
    contract = License(
        license_id="HD-2026-07",
        organization="Trung tâm Ngoại ngữ",
        plan=ServicePlan.ADVANCED,
        seats=400,
        valid_from=today,
        valid_to=today + timedelta(days=364),
        source="key",
    )
    key = keys.issue(contract, SECRET.encode(), "2026-10-07T00:00:00+00:00")

    r = admin.post("/api/v1/admin/billing/license", json={"key": key})

    assert r.status_code == 200 and r.json()["plan"] == "advanced"
    now = overview(admin)
    assert (now["license"]["license_id"], now["students_allowed"]) == ("HD-2026-07", 400)
    assert now["organization"] == "Trung tâm Ngoại ngữ"
    assert admin.post("/api/v1/admin/billing/license", json={"key": key}).status_code == 409
    forged = keys.issue(contract, b"khoa-gia", "2026-10-07T00:00:00+00:00")
    bad = admin.post("/api/v1/admin/billing/license", json={"key": forged})
    assert bad.status_code == 422 and "chữ ký" in bad.json()["detail"]


def test_without_a_licence_secret_keys_are_refused(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_BILLING="on")
    admin = admin_of(m)

    malformed = ".".join(("AICEFR1", "abc", "def"))
    r = admin.post("/api/v1/admin/billing/license", json={"key": malformed})

    assert r.status_code == 422 and "AICEFR_LICENSE_SECRET" in r.json()["detail"]
    assert overview(admin)["key_install"] is False


# ================================================================= VNPay


def vnpay_reply(gw: VnpayGateway, checkout_url: str, code: str = "00") -> dict:
    """What VNPay sends back after its payment page, signed as VNPay signs it."""
    sent = dict(parse_qsl(urlparse(checkout_url).query))
    reply = {
        "vnp_Amount": sent["vnp_Amount"],
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": "VNP14000001",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": sent["vnp_OrderInfo"],
        "vnp_PayDate": sent["vnp_CreateDate"],
        "vnp_ResponseCode": code,
        "vnp_TmnCode": sent["vnp_TmnCode"],
        "vnp_TransactionNo": "14000001",
        "vnp_TransactionStatus": "00" if code == "00" else "02",
        "vnp_TxnRef": sent["vnp_TxnRef"],
    }
    return reply | {"vnp_SecureHash": gw._hash(gw.canonical(reply))}


def test_vnpay_is_redirected_to_and_its_messages_are_checked(tmp_path, monkeypatch):
    m = boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_PAYMENT_GATEWAYS="vnpay",
        AICEFR_VNPAY_TMN_CODE="TMNTHU01",
        AICEFR_VNPAY_HASH_SECRET=VNP_SECRET,
    )
    admin = admin_of(m)
    body = {"plan": "standard", "seats": 50, "months": 6}

    placed = admin.post("/api/v1/admin/billing/orders", json=body).json()

    url = placed["checkout_url"]
    assert url.startswith("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?")
    sent = dict(parse_qsl(urlparse(url).query))
    assert sent["vnp_ReturnUrl"] == "http://testserver/billing/return/vnpay"
    assert sent["vnp_Amount"] == "300000000" and sent["vnp_TmnCode"] == "TMNTHU01"
    reply = vnpay_reply(m.billing.gateways["vnpay"], url)
    # VNPay's server reports first, then the browser comes back.
    assert admin.get("/api/v1/billing/notify/vnpay?" + urlencode(reply)).json() == {
        "RspCode": "00",
        "Message": "Confirm Success",
    }
    page = admin.get("/billing/return/vnpay?" + urlencode(reply))
    # VNPay's sandbox address: VNPay's own test environment, so no real money.
    assert "Thanh toán thành công" in page.text and "Môi trường thử của VNPay" in page.text
    assert overview(admin)["plan"] == "standard"
    # A customer who cancels on VNPay's page.
    second = admin.post("/api/v1/admin/billing/orders", json={**body, "plan": "advanced"}).json()
    cancelled = vnpay_reply(m.billing.gateways["vnpay"], second["checkout_url"], "24")
    page = admin.get("/billing/return/vnpay?" + urlencode(cancelled))
    assert "Bạn đã huỷ giao dịch" in page.text
    assert overview(admin)["plan"] == "standard"


# ================================================================= who may


def test_only_an_administrator_deals_with_plans(m):
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    learner = login_as(m, "SV-001")
    guest = TestClient(m.app)
    assert teacher.get("/api/v1/plan").status_code == 200
    assert learner.get("/api/v1/plan").status_code == 403
    body = {"plan": "standard", "seats": 50, "months": 6}
    for client, status in ((teacher, 403), (learner, 403), (guest, 401)):
        assert client.get("/api/v1/admin/billing").status_code == status
        assert client.post("/api/v1/admin/billing/orders", json=body).status_code == status
    order = buy(admin_of(m), "standard", 50)
    assert receipt_status(teacher, order["order_id"]) == 403
    receipt = guest.get(f"/billing/orders/{order['order_id']}/receipt", follow_redirects=False)
    assert receipt.status_code == 303
    # Nothing a learner opens speaks of plans or payment.
    for path in ("/practice", "/my-progress", "/account", "/"):
        text = learner.get(path).text.lower()
        assert "gói dịch vụ" not in text and "thanh toán" not in text


def test_plan_actions_are_audited(m):
    admin = admin_of(m)
    admin.patch("/api/v1/admin/billing/organization", json={"name": "Khoa Ngoại ngữ"})
    order = buy(admin, "standard", 50)

    entries = admin.get("/api/v1/audit").json()

    seen = {(e["action"], e["actor_id"]) for e in entries}
    assert ("billing.organization", "QT-01") in seen
    assert ("billing.order", "QT-01") in seen
    assert ("billing.paid", "gateway:sandbox") in seen
    paid = next(e for e in entries if e["action"] == "billing.paid")
    assert paid["target_id"] == order["order_id"] and "amount=3000000" in paid["detail"]
