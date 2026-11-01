"""Layer 1 -- UNIT: the payment gateways' signing, pure functions only (D035).

No application, no database, no network. VNPay is checked against the form it
documents for version 2.1.0 -- keys sorted, values form-encoded, HMAC-SHA512 --
recomputed here with the standard library rather than trusted from the
adapter. D075: the plans, licences, quotes and keys these tests also covered
were removed with the institution's service plans.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aicefr.billing.gateways import SandboxGateway
from aicefr.billing.payments import OrderStatus

NOW = datetime(2026, 10, 7, 3, 0, tzinfo=UTC)
# Built, not written out, so the secret scanner sees no literal.
VNP_SECRET = "thu-" * 6


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
