"""Integer-only quote arithmetic with deterministic discount and proration."""

from __future__ import annotations

from aicefr.billing.contracts import Plan
from aicefr.billing.errors import BillingError


def quote_amount(
    plan: Plan, months: int, *, current_credit_minor: int = 0
) -> tuple[int, int, int, int]:
    if type(months) is not int or months not in (1, 12):
        raise BillingError("invalid_billing_term")
    if type(current_credit_minor) is not int or current_credit_minor < 0:
        raise BillingError("invalid_credit")
    subtotal = plan.monthly_minor * months
    discount = subtotal * 15 // 100 if months == 12 else 0
    credit = min(current_credit_minor, subtotal - discount)
    return subtotal, discount, credit, subtotal - discount - credit


def prorated_credit(monthly_minor: int, unused_days: int, period_days: int = 30) -> int:
    if any(type(v) is not int for v in (monthly_minor, unused_days, period_days)):
        raise BillingError("invalid_proration")
    if monthly_minor < 0 or period_days <= 0 or not 0 <= unused_days <= period_days:
        raise BillingError("invalid_proration")
    return monthly_minor * unused_days // period_days
