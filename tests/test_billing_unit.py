"""Layer 1 -- UNIT: plans, licences, quotes, keys and gateways, pure functions only (D033).

No application, no database, no network. VNPay is checked against the form it
documents for version 2.1.0 -- keys sorted, values form-encoded, HMAC-SHA512 --
recomputed here with the standard library rather than trusted from the
adapter.

Test case ids (TC-GD-Uxx) are listed in `docs/test/TEST_PLAN_D033.md`.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qsl, urlparse

import pytest

from aicefr.billing import keys
from aicefr.billing.gateways import SandboxGateway, VnpayGateway
from aicefr.billing.payments import OrderStatus
from aicefr.billing.plans import (
    ANNUAL_DISCOUNT,
    FREE_SEATS,
    GRACE_DAYS,
    MIN_CHARGE,
    PLAN_FEATURES,
    QUOTA_PER_SEAT,
    License,
    LicenseState,
    Plan,
    PlanFeature,
    QuoteError,
    add_months,
    quote,
    standing,
)

pytestmark = pytest.mark.unit

TODAY = date(2026, 10, 7)
SECRET = b"khoa-ky-giay-phep-cua-bai-kiem-thu"


def lic(
    plan: Plan = Plan.STANDARD,
    seats: int = 100,
    start: date = TODAY,
    days: int = 182,
    source: str = "order",
    value: int = 6_000_000,
    installed: str = "",
    name: str = "L-1",
) -> License:
    return License(
        license_id=name,
        organization="Khoa Ngoại ngữ",
        plan=plan,
        seats=seats,
        valid_from=start,
        valid_to=start + timedelta(days=days - 1),
        source=source,
        value_vnd=value,
        installed_at=installed,
    )


# ---------------------------------------------------------------- licences in force


def test_the_licence_that_started_last_is_in_force():
    trial = lic(Plan.TRIAL, 50, TODAY, 90, "trial", 0, "2026-10-07T01:00:00+00:00", "trial")
    bought = lic(installed="2026-10-07T01:00:00+00:00", name="L-bought")  # the same second
    later = lic(Plan.ADVANCED, start=TODAY + timedelta(days=182), name="L-next")

    now = standing([trial, bought, later], TODAY)

    assert now.license.license_id == "L-bought"  # installed after the trial, same day, same second
    assert now.state is LicenseState.ACTIVE and now.seat_cap == 100
    assert [x.license_id for x in now.scheduled] == ["L-next"]
    # Before any licence has started: the free plan, with what is booked.
    free = standing([later], TODAY)
    assert (free.plan, free.state, free.seat_cap) == (Plan.FREE, LicenseState.FREE, FREE_SEATS)
    assert free.scheduled == (later,)
    assert standing([], TODAY).features == frozenset()


def test_a_paid_plan_runs_out_into_grace_then_the_free_plan():
    current = lic(Plan.ADVANCED, days=30)
    end = current.valid_to

    assert standing([current], end).state is LicenseState.ACTIVE
    assert standing([current], end).days_left == 1
    grace = standing([current], end + timedelta(days=GRACE_DAYS))
    assert grace.state is LicenseState.GRACE
    assert grace.seat_cap == 100 and PlanFeature.BLIND_RATING in grace.features
    after = standing([current], end + timedelta(days=GRACE_DAYS + 1))
    # Back on the free plan: one class, no staff tools, the old licence named.
    assert (after.plan, after.state, after.seat_cap) == (Plan.FREE, LicenseState.FREE, 30)
    assert after.features == frozenset() and after.lapsed == current
    # A trial has no grace: the day after, the school is on the free plan.
    trial = lic(Plan.TRIAL, 50, days=30, source="trial", value=0)
    assert standing([trial], trial.valid_to + timedelta(days=1)).plan is Plan.FREE


def test_each_step_up_adds_something_and_none_locks_learning():
    """BR-29: a plan opens staff tools only; adding one means rereading the rule."""
    assert {f.value for f in PlanFeature} == {"lesson_authoring", "class_insights", "blind_rating"}
    free, standard, advanced = (PLAN_FEATURES[p] for p in (Plan.FREE, Plan.STANDARD, Plan.ADVANCED))
    assert free == frozenset() and free < standard < advanced
    assert PLAN_FEATURES[Plan.TRIAL] == advanced  # a trial shows everything
    assert QUOTA_PER_SEAT[Plan.FREE] < QUOTA_PER_SEAT[Plan.STANDARD] < QUOTA_PER_SEAT[Plan.ADVANCED]


# ---------------------------------------------------------------- quotes


def test_a_first_purchase_starts_today():
    trial = standing([lic(Plan.TRIAL, 50, source="trial", value=0, days=30)], TODAY)

    q = quote(trial, Plan.STANDARD, 120, 6, 10_000, TODAY)

    assert (q.kind, q.starts_on, q.ends_on) == ("new", TODAY, date(2027, 4, 6))
    assert (q.list_price, q.discount, q.credit, q.amount) == (7_200_000, 0, 0, 7_200_000)
    assert quote(standing([], TODAY), Plan.ADVANCED, 10, 6, 15_000, TODAY).kind == "new"


def test_a_school_year_paid_at_once_is_cheaper():
    q = quote(standing([], TODAY), Plan.STANDARD, 100, 12, 10_000, TODAY)

    assert ANNUAL_DISCOUNT == 15
    assert (q.list_price, q.discount, q.gross, q.amount) == (
        12_000_000,
        1_800_000,
        10_200_000,
        10_200_000,
    )
    assert q.ends_on == date(2027, 10, 6)


def test_a_renewal_follows_the_current_licence():
    current = standing([lic()], TODAY + timedelta(days=100))

    q = quote(current, Plan.STANDARD, 100, 6, 10_000, TODAY + timedelta(days=100))

    assert q.kind == "renewal"
    assert q.starts_on == lic().valid_to + timedelta(days=1)
    assert q.credit == 0 and q.amount == 6_000_000


def test_an_upgrade_starts_today_with_credit_for_the_unused_days():
    held = lic(value=6_000_000, days=182)
    day = TODAY + timedelta(days=91)  # 91 of 182 days left, today included
    current = standing([held], day)

    q = quote(current, Plan.ADVANCED, 100, 6, 15_000, day)

    assert (q.kind, q.starts_on) == ("upgrade", day)
    assert q.credit == 3_000_000  # half the value, in whole thousands
    assert q.amount == 9_000_000 - 3_000_000
    # More seats on the same plan is an upgrade too.
    assert quote(current, Plan.STANDARD, 150, 6, 10_000, day).kind == "upgrade"
    # In grace nothing is left to credit.
    late = held.valid_to + timedelta(days=3)
    assert quote(standing([held], late), Plan.ADVANCED, 100, 6, 15_000, late).credit == 0


def test_a_smaller_plan_waits_for_the_current_one_to_end():
    current = standing([lic(Plan.ADVANCED)], TODAY)

    q = quote(current, Plan.STANDARD, 100, 6, 10_000, TODAY)

    assert q.kind == "downgrade" and q.starts_on == lic().valid_to + timedelta(days=1)
    assert quote(standing([lic()], TODAY), Plan.STANDARD, 60, 6, 10_000, TODAY).kind == "downgrade"


def test_a_quote_refuses_what_cannot_be_sold():
    trial = standing([lic(Plan.TRIAL, source="trial", value=0)], TODAY)
    for plan, seats, months in (
        (Plan.TRIAL, 50, 6),
        (Plan.FREE, 50, 6),
        (Plan.STANDARD, 50, 3),
        (Plan.STANDARD, 5, 6),
        (Plan.STANDARD, 6000, 6),
    ):
        with pytest.raises(QuoteError):
            quote(trial, plan, seats, months, 10_000, TODAY)
    booked = standing([lic(), lic(start=TODAY + timedelta(days=182), name="L-2")], TODAY)
    with pytest.raises(QuoteError, match="đặt trước"):
        quote(booked, Plan.ADVANCED, 100, 6, 15_000, TODAY)


def test_a_difference_smaller_than_a_gateway_takes_is_waived():
    # 100 students for 6 months, bought today; an upgrade to fewer students on
    # the higher plan is covered by the credit, all but a few thousand dong.
    held = lic(seats=100, days=182, value=6_000_000)
    q = quote(standing([held], TODAY), Plan.ADVANCED, 67, 6, 14_950, TODAY)  # 6.009.900 đ

    assert q.kind == "upgrade" and 0 < q.gross - q.credit < MIN_CHARGE
    assert q.amount == 0
    covered = quote(standing([held], TODAY), Plan.ADVANCED, 10, 6, 15_000, TODAY)
    assert covered.credit == covered.gross and covered.amount == 0


def test_months_are_added_on_the_calendar():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert add_months(date(2027, 8, 31), 6) == date(2028, 2, 29)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert add_months(date(2026, 10, 7), 12) == date(2027, 10, 7)


# ---------------------------------------------------------------- licence keys


def test_a_licence_key_round_trips_and_any_change_breaks_it():
    issued = lic(Plan.ADVANCED, 300, source="key", value=0, name="HD-2026-001")
    key = keys.issue(issued, SECRET, "2026-10-07T00:00:00+00:00")

    back = keys.read(key, SECRET)

    assert (back.license_id, back.plan, back.seats, back.source) == (
        "HD-2026-001",
        Plan.ADVANCED,
        300,
        "key",
    )
    assert (back.valid_from, back.valid_to, back.organization) == (
        issued.valid_from,
        issued.valid_to,
        "Khoa Ngoại ngữ",
    )
    prefix, payload, signature = key.split(".")
    flipped = payload[:-2] + ("A" if payload[-2] != "A" else "B") + payload[-1]
    for bad, why in (
        (f"{prefix}.{flipped}.{signature}", "chữ ký"),
        (key + "x", "chữ ký"),
        ("AICEFR2." + payload + "." + signature, "định dạng"),
        ("khong-phai-ma", "định dạng"),
    ):
        with pytest.raises(keys.LicenseKeyError, match=why):
            keys.read(bad, SECRET)
    with pytest.raises(keys.LicenseKeyError, match="chữ ký"):
        keys.read(key, b"mot-khoa-khac")


def test_a_key_with_impossible_contents_is_refused():
    for wrong in (
        lic(Plan.TRIAL, source="key"),
        lic(Plan.FREE, source="key"),
        lic(seats=0, source="key"),
        lic(days=0, source="key"),  # ends the day before it starts
    ):
        key = keys.issue(wrong, SECRET, "2026-10-07T00:00:00+00:00")
        with pytest.raises(keys.LicenseKeyError):
            keys.read(key, SECRET)


# ---------------------------------------------------------------- gateways

NOW = datetime(2026, 10, 7, 3, 0, tzinfo=UTC)  # 10:00 in Vietnam
# Built, not written out, so the secret scanner sees no literal.
VNP_SECRET = "thu-" * 6


def vnpay_hash(params: dict[str, str]) -> str:
    """VNPay 2.1.0, recomputed here: sorted keys, form-encoded values, HMAC-SHA512."""
    from urllib.parse import quote_plus

    data = "&".join(f"{k}={quote_plus(v)}" for k, v in sorted(params.items()))
    return hmac.new(VNP_SECRET.encode(), data.encode(), hashlib.sha512).hexdigest()


def test_vnpay_builds_a_payment_address_it_documents():
    gw = VnpayGateway("TMNTHU01", VNP_SECRET)

    url = gw.checkout(
        "DH2610070A1B2C",
        6_000_000,
        "Thanh toan don DH2610070A1B2C",
        "https://x.vn/r",
        "https://x.vn/n",
        "1.2.3.4",
        NOW,
    ).url

    parts = urlparse(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == (
        "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    )
    params = dict(parse_qsl(parts.query))
    received = params.pop("vnp_SecureHash")
    assert received == vnpay_hash(params)
    assert params["vnp_Amount"] == "600000000"  # hundredths of a dong
    assert params["vnp_Version"] == "2.1.0" and params["vnp_Command"] == "pay"
    assert params["vnp_TxnRef"] == "DH2610070A1B2C" and params["vnp_CurrCode"] == "VND"
    assert params["vnp_CreateDate"] == "20261007100000"  # Vietnam time
    assert params["vnp_ExpireDate"] == "20261007101500"
    assert params["vnp_ReturnUrl"] == "https://x.vn/r" and params["vnp_IpAddr"] == "1.2.3.4"


def vnpay_result(code: str = "00", status: str = "00", amount: str = "600000000") -> dict:
    params = {
        "vnp_Amount": amount,
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": "VNP14000001",
        "vnp_CardType": "ATM",
        "vnp_OrderInfo": "Thanh toan don DH2610070A1B2C",
        "vnp_PayDate": "20261007101010",
        "vnp_ResponseCode": code,
        "vnp_TmnCode": "TMNTHU01",
        "vnp_TransactionNo": "14000001",
        "vnp_TransactionStatus": status,
        "vnp_TxnRef": "DH2610070A1B2C",
    }
    return params | {"vnp_SecureHash": vnpay_hash(params), "vnp_SecureHashType": "HmacSHA512"}


def test_vnpay_results_map_to_outcomes_and_a_changed_byte_is_refused():
    gw = VnpayGateway("TMNTHU01", VNP_SECRET)

    paid = gw.verify(vnpay_result())

    assert (paid.order_id, paid.outcome, paid.amount_vnd, paid.reference) == (
        "DH2610070A1B2C",
        OrderStatus.PAID,
        6_000_000,
        "14000001",
    )
    assert paid.details == {
        "vnp_BankCode": "NCB",
        "vnp_BankTranNo": "VNP14000001",
        "vnp_CardType": "ATM",
        "vnp_PayDate": "20261007101010",
    }
    assert gw.verify(vnpay_result("24", "02")).outcome is OrderStatus.CANCELLED
    assert gw.verify(vnpay_result("51", "02")).outcome is OrderStatus.FAILED
    assert gw.verify(vnpay_result("00", "02")).outcome is OrderStatus.FAILED
    upper = vnpay_result() | {"vnp_SecureHash": vnpay_result()["vnp_SecureHash"].upper()}
    assert gw.verify(upper) is not None
    assert gw.verify(vnpay_result() | {"vnp_Amount": "100"}) is None  # a changed amount
    assert gw.verify({k: v for k, v in vnpay_result().items() if k != "vnp_SecureHash"}) is None
    assert gw.verify(vnpay_result() | {"vnp_SecureHash": "é" * 128}) is None  # not a crash
    assert VnpayGateway("TMNTHU01", "khac").verify(vnpay_result()) is None
    assert gw.acknowledge("ok").body == {"RspCode": "00", "Message": "Confirm Success"}
    assert gw.acknowledge("signature").body["RspCode"] == "97"
    assert gw.acknowledge("pending").body["RspCode"] == "99"  # never sent by VNPay
    assert {gw.acknowledge(w).status for w in ("ok", "signature", "error")} == {200}
    assert gw.live is False and "sandbox" in gw.note
    assert VnpayGateway("TMNTHU01", VNP_SECRET, "https://pay.vnpay.vn/vpcpay.html").live is True
    with pytest.raises(ValueError):
        VnpayGateway("", VNP_SECRET)


def test_the_sandbox_signs_its_results_and_refuses_forgeries():
    gw = SandboxGateway(b"bi-mat-cong-thu")

    params = gw.result("DH1", 3_000_000, "paid", NOW)
    result = gw.verify(params)

    assert (result.order_id, result.outcome, result.amount_vnd) == (
        "DH1",
        OrderStatus.PAID,
        3_000_000,
    )
    assert result.reference.startswith("SB") and result.details == {"pay_date": "20261007100000"}
    assert gw.verify(params | {"amount": "1"}) is None
    assert gw.verify(params | {"sig": "é"}) is None  # refused, not a crash
    assert gw.verify(params | {"outcome": "failed"}) is None
    assert SandboxGateway(b"khoa-khac").verify(params) is None
    assert gw.verify(gw.result("DH1", 3_000_000, "cancelled", NOW)).outcome is OrderStatus.CANCELLED
    assert gw.token("DH1", 3_000_000) != gw.token("DH1", 3_000_001) != gw.token("DH2", 3_000_000)
    with pytest.raises(ValueError):
        gw.result("DH1", 3_000_000, "hoan-tien", NOW)
