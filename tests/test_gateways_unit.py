"""Layer 1 -- UNIT: the gateway registry and the HTTPS caller (D035, D075, D097).

No application, no database, no network. Stripe was removed in D097 and its
adapter's tests with it; payOS's own adapter is tested in
`test_d095_payos_unit.py`. What stays here holds for any gateway: which ones a
deployment's settings build, that real money is never a default, and that the
caller never carries a gateway's keys to wherever a redirect points.

Test case ids (TC-CT-Uxx) are listed in `docs/test/TEST_PLAN_D035.md`.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aicefr.billing import registry, transport
from aicefr.config import Settings

pytestmark = pytest.mark.unit

CLIENT, API_KEY, CHECKSUM = "client-thu-123", "api-key-thu-456", "checksum-thu-789"


def settings(**changes) -> Settings:
    base = replace(
        Settings(),
        payment_gateways=("sandbox",),
        payments_live=False,
        payos_client_id="",
        payos_api_key="",
        payos_checksum_key="",
    )
    return replace(base, **changes)


def build(**changes):
    return registry.build_gateways(settings(**changes), lambda: b"bi-mat-cong-thu")


def test_the_registry_builds_what_the_settings_ask_for(monkeypatch):
    # The list as written in .env: a blank line means the default, not "none".
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", "  ")
    assert Settings().payment_gateways == ("sandbox",)
    monkeypatch.setenv("AICEFR_PAYMENT_GATEWAYS", " payOS , sandbox,,")
    assert Settings().payment_gateways == ("payos", "sandbox")

    gateways, problems = build(payment_gateways=("sandbox",))

    assert list(gateways) == ["sandbox"] and problems == []
    # Nothing set but the names: each one missing says what is missing; D075
    # removed VNPay and MoMo, D097 Stripe, which are now names like any unknown one.
    gateways, problems = build(payment_gateways=("payos", "stripe", "momo", "vnpay", "payos"))
    assert gateways == {}
    assert any("AICEFR_PAYOS_CLIENT_ID" in p for p in problems)
    for gone in ("stripe", "momo", "vnpay"):
        assert any(gone in p for p in problems), gone
    assert len(problems) == 4  # the second "payos" is not reported twice


def test_real_money_is_never_a_default():
    live = dict(
        payment_gateways=("sandbox", "payos"),
        payos_client_id=CLIENT,
        payos_api_key=API_KEY,
        payos_checksum_key=CHECKSUM,
    )

    gateways, problems = build(**live)

    assert list(gateways) == ["sandbox"]
    assert any("AICEFR_PAYMENTS_LIVE" in p for p in problems)
    # Switched on, the live gateway runs and the sandbox goes: next to a
    # gateway that takes real money no test environment runs, or anyone could
    # buy real runs on the sandbox's page.
    gateways, problems = build(payments_live=True, **live)
    assert list(gateways) == ["payos"] and gateways["payos"].live
    assert any("Cổng thử đã tắt" in p for p in problems)


def test_a_gateway_call_never_follows_a_redirect():
    # urllib would follow it carrying every header -- the gateway's API key
    # included -- to whatever host it names; a redirect is handed back instead.
    assert transport._NoRedirect().redirect_request(None, None, 302, "", {}, "https://x") is None
    with pytest.raises(ValueError):
        transport.https("GET", "http://khong-ma-hoa.example", {}, None)
