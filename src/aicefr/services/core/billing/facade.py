"""What other services may ask the billing service (D043): may the school use this?

Each answer is a refusal -- the sentence to show, with the plans that include the
feature -- or None for "allowed". With service plans switched off nothing is
ever refused.
"""

from __future__ import annotations

from aicefr.billing.plans import PlanFeature
from aicefr.billing.service import BillingService, FeatureLocked, SeatLimit
from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog


class BillingFacade:
    def __init__(self, service: BillingService, audit: AuditLog) -> None:
        self.service = service
        self.audit = audit

    @exposed
    def plan_refusal(self, feature: str) -> str | None:
        """Why the plan in force does not include `feature` (D034), or None."""
        try:
            self.service.require(PlanFeature(feature))
        except FeatureLocked as e:
            return str(e)
        return None

    @exposed
    def seat_refusal(self, n: int) -> str | None:
        """Why `n` more enabled student accounts do not fit the plan (D033, BR-31), or None."""
        try:
            self.service.check_new_students(n)
        except SeatLimit as e:
            return str(e)
        return None

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
