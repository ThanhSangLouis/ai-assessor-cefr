"""The metering service (D049): the ledger of the metered channel, its facade, its pages.

Its own store setting (`AICEFR_METERING_DB`), which falls back to the core's:
on one machine the ledger sits beside everything else, in a deployment it can
have a database of its own that no other service writes to. A sweep releases
holds whose result never came.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta

from aicefr.config import Settings
from aicefr.metering.pricing import PriceList
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.metering import metering_api
from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.metering_repository import MeteringRepository

logger = logging.getLogger(__name__)


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    target = settings.store("metering")
    store = MeteringRepository(target)
    audit_log = AuditLog(target, "metering")
    enabled = settings.metering_enabled
    prices = PriceList(
        first_minute_runs=settings.price_first_minute_runs,
        extra_minute_runs=settings.price_extra_minute_runs,
        practice_factor=settings.price_practice_factor,
        idpoint_per_run=settings.idpoint_per_run,
    )
    facade = MeteringFacade(store, audit_log, enabled, prices)
    metering_api.configure(
        metering_api.Services(
            store=store, audit=audit_log, peers=peers, enabled=enabled, prices=prices
        )
    )
    stop = threading.Event()

    def release_stale() -> list[str]:
        # Twice the longest a job may run: by then its result is not coming.
        cutoff = datetime.now(UTC) - timedelta(seconds=2 * settings.job_timeout_s)
        released = store.release_stale(cutoff.isoformat(timespec="seconds"))
        if released:
            logger.warning("released %d holds whose result never came", len(released))
        return released

    def sweep() -> None:
        while not stop.wait(60.0):
            try:
                release_stale()
            except Exception:  # noqa: BLE001 - the sweep thread must not die of one error
                logger.exception("metering sweep failed")

    def startup() -> None:
        if enabled and settings.job_mode != "inline":
            threading.Thread(target=sweep, name="metering-sweep", daemon=True).start()

    return Parts(
        name="metering",
        routers=[metering_api.router, internal_router("metering", facade, settings.internal_token)],
        facade=facade,
        state={
            "metering": store,
            "release_stale": release_stale,
            "startup": startup,
            "ready": lambda: {"metering": enabled},
        },
    )
