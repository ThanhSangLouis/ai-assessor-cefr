"""The billing service: plans, orders, licences, payment gateways (D043).

What a plan counts -- student accounts, assessments this month, research
participants -- is asked of identity and assessment when it is needed; the
payment pages a gateway returns to are drawn here, where the order is.
"""

from __future__ import annotations

import logging
import uuid

from aicefr.billing.registry import build_gateways
from aicefr.billing.service import BillingService
from aicefr.config import Settings
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.billing import billing_api
from aicefr.services.core.billing.facade import BillingFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import Role
from aicefr.storage.billing_repository import BillingRepository

logger = logging.getLogger(__name__)


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = BillingRepository(settings.store("core"))
    audit_log = AuditLog(settings.store("core"), "billing")

    def sandbox_secret() -> bytes:
        """The sandbox signs with a secret of this deployment, made once and kept."""
        return bytes.fromhex(store.setting_once("sandbox_secret", uuid.uuid4().hex))

    gateways, problems = build_gateways(settings, sandbox_secret)
    for problem in problems:
        logger.warning("billing: %s", problem)
    service = BillingService(
        store,
        students=lambda: peers.identity.count_role(role=Role.STUDENT.value),
        assessments=lambda since, until: peers.assessment.assessments_by_account(
            since=since, until=until
        ),
        settings=settings,
        gateways=gateways,
        audit=audit_log.write,
        gateway_problems=problems,
        # D053: run packs are sold only where runs are counted.
        credit=(
            (lambda account_id, runs, order_id: peers.metering.credit(
                account_id=account_id, runs=runs, order_id=order_id))
            if settings.metering_enabled else None
        ),
    )  # fmt: skip
    facade = BillingFacade(service, audit_log)
    billing_api.configure(billing_api.Services(billing=service))
    return Parts(
        name="billing",
        routers=[billing_api.router, internal_router("billing", facade, settings.internal_token)],
        facade=facade,
        state={"billing": service, "ready": lambda: {"plan": service.standing().plan.value}},
    )
