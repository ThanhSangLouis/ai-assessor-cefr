import pytest

from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS
from aicefr.billing.quotes import prorated_credit, quote_amount


def test_monthly_and_annual_quotes_use_deterministic_integer_minor_units():
    monthly = quote_amount(PLANS["STANDARD"], 1)
    annual = quote_amount(PLANS["STANDARD"], 12)
    assert monthly == (99_000, 0, 0, 99_000)
    assert annual == (1_188_000, 178_200, 0, 1_009_800)


def test_credit_is_capped_and_proration_floors_integer_amounts():
    assert quote_amount(PLANS["STANDARD"], 1, current_credit_minor=150_000) == (
        99_000,
        0,
        99_000,
        0,
    )
    assert prorated_credit(99_000, 15) == 49_500
    assert prorated_credit(99_001, 1) == 3_300


@pytest.mark.parametrize("months", [True, 0, 2, 12.0, "12"])
def test_quote_rejects_noncanonical_term_types(months):
    with pytest.raises(BillingError, match="invalid_billing_term"):
        quote_amount(PLANS["STANDARD"], months)


@pytest.mark.parametrize("credit", [True, -1, 1.0])
def test_quote_rejects_invalid_credit(credit):
    with pytest.raises(BillingError, match="invalid_credit"):
        quote_amount(PLANS["STANDARD"], 1, current_credit_minor=credit)


@pytest.mark.parametrize(
    "amount,unused,period",
    [(True, 1, 30), (-1, 1, 30), (99, -1, 30), (99, 31, 30), (99, 0, 0)],
)
def test_proration_rejects_invalid_ranges_and_types(amount, unused, period):
    with pytest.raises(BillingError, match="invalid_proration"):
        prorated_credit(amount, unused, period)
