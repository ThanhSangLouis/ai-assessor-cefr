"""Builds the metering service parts for core app composition."""

from __future__ import annotations

from fastapi import APIRouter

from aicefr.config import Settings
from aicefr.metering.service import MeteringService
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.metering_repository import MeteringRepository


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = MeteringRepository(settings.store("metering"))
    service = MeteringService(store, enabled=settings.metering_enabled)
    facade = MeteringFacade(service)
    router = APIRouter(prefix="/api/v1/credits", tags=["metering"])

    @router.get("/balance")
    def get_balance() -> dict:
        return {"enabled": service.is_enabled()}

    return Parts(
        name="metering",
        routers=[router, internal_router("metering", facade, settings.internal_token)],
        facade=facade,
        state={"metering": service, "ready": lambda: {"enabled": service.is_enabled()}},
    )
