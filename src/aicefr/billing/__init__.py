"""Billing domain and application services."""

from aicefr.billing.errors import BillingError

__all__ = ["BillingError", "BillingService"]


def __getattr__(name: str):
    if name == "BillingService":
        from aicefr.billing.service import BillingService

        return BillingService
    raise AttributeError(name)
