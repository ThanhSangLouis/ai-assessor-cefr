"""The billing service: run-pack orders and the payment gateways (D043, D075).

The payment pages a gateway returns to are drawn here, where the order is.
"""

from __future__ import annotations

import logging
import threading
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
from aicefr.storage.billing_repository import BillingRepository

logger = logging.getLogger(__name__)

# D099: how often open orders are reconciled with their gateway.
RECONCILE_TICK_S = 120.0


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
        # D078: the packs an administrator put on sale, from the metering service.
        packs=(
            (lambda: tuple(tuple(p) for p in peers.metering.run_packs()))
            if settings.metering_enabled else None
        ),
        # D096: a settled order is an event; the identity service emails the buyer.
        publish=bus.publish,
    )  # fmt: skip
    stop = threading.Event()

    def reconcile_loop() -> None:
        while not stop.wait(RECONCILE_TICK_S):
            try:
                moved = service.reconcile()
                if moved:
                    logger.info("billing: reconciled %s", ", ".join(moved))
            except Exception:  # noqa: BLE001 - the loop must not die of one error
                logger.exception("billing: reconcile failed")

    def startup() -> None:
        if service.enabled and settings.job_mode != "inline":
            threading.Thread(target=reconcile_loop, name="billing-reconcile", daemon=True).start()

    facade = BillingFacade(service, audit_log)
    billing_api.configure(
        billing_api.Services(
            billing=service,
            pseudonyms=lambda ids: peers.identity.pseudonyms(account_ids=ids),
        )
    )
    return Parts(
        name="billing",
        routers=[billing_api.router, internal_router("billing", facade, settings.internal_token)],
        facade=facade,
        state={
            "billing": service,
            "startup": startup,
            "ready": lambda: {"payments": service.enabled},
        },
    )
