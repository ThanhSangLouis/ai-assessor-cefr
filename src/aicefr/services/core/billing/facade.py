"""What other services may ask the billing service (D043).

D075: one centre, no plans -- nothing is ever refused for a plan, so all that
is left to ask is the audit trail of payments.
"""

from __future__ import annotations

from aicefr.billing.service import BillingService
from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog


class BillingFacade:
    def __init__(self, service: BillingService, audit: AuditLog) -> None:
        self.service = service
        self.audit = audit

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
