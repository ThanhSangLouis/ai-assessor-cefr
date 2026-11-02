"""How one service runs on its own, as its container starts it (D043).

`standalone` builds the service's parts with its peers reached over HTTP and the
bus from the settings (Redis in a deployment), wraps them in a FastAPI
application with the same middleware as everywhere, and starts the bus's
consumers when the application starts. Every service answers `/healthz`
(alive) and `/readyz` (its store answers).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

from aicefr.api.middleware import (
    LoginRateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from aicefr.config import Settings
from aicefr.infra.queues import InProcessJobQueue
from aicefr.observability import render_metrics, setup_logging
from aicefr.platform.bus import MessageBus, bus_from_url
from aicefr.platform.callers import GatewayCallers
from aicefr.services import Parts, Peers

logger = logging.getLogger(__name__)

Builder = Callable[[Settings, Peers, MessageBus], Parts]


def make_bus(settings: Settings) -> MessageBus:
    return bus_from_url(settings.bus_url, InProcessJobQueue(settings.max_concurrent_jobs))


def standalone(
    name: str,
    build: Builder,
    settings: Settings,
    *,
    login_rate_limit: bool = False,
    static: bool = False,
    peers: Peers | None = None,
    bus: MessageBus | None = None,
) -> FastAPI:
    """The service `name` as an application of its own.

    `peers` and `bus` default to what the settings say -- the other services
    over HTTP, Redis -- and are given by the tests that run the services
    apart in one process.
    """
    # The speech service answers no request from a browser and calls no facade:
    # it holds neither key. Every other service needs both.
    if name != "speech":
        for key, value in (
            ("AICEFR_INTERNAL_TOKEN", settings.internal_token),
            ("AICEFR_GATEWAY_TOKEN", settings.gateway_token),
        ):
            if not value:
                raise RuntimeError(f"{name}: {key} is not set; the services cannot trust requests")
    peers = peers or Peers.from_settings(settings)
    bus = bus or make_bus(settings)
    parts = build(settings, peers, bus)
    startup = parts.state.pop("startup", None)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        setup_logging(json_output=settings.is_production)
        logger.info("starting %s", name, extra={"event": "startup"})
        if startup:
            startup()
        bus.start()
        yield
        bus.close()

    app = FastAPI(
        title=f"SpeakUp — {name}",
        version=settings.version,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(SecurityHeadersMiddleware)
    if login_rate_limit:
        app.add_middleware(LoginRateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    if static:
        from aicefr.api.web import mount_static

        mount_static(app)
    app.state.callers = GatewayCallers(settings.gateway_token)
    for key, value in parts.state.items():
        setattr(app.state, key, value)
    for router in parts.routers:
        app.include_router(router)
    ready = parts.state.get("ready")

    @app.get("/healthz", include_in_schema=False)
    def liveness() -> dict:
        return {"status": "alive", "service": name}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> PlainTextResponse:
        """Counters and histograms for Prometheus (D051); the gateway never forwards it."""
        return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")

    @app.get("/readyz", include_in_schema=False)
    def readiness() -> JSONResponse:
        try:
            checks = ready() if ready else {}
        except Exception as e:  # noqa: BLE001 - report the failure, never raise here
            return JSONResponse(
                {"status": "degraded", "service": name, "error": str(e)}, status_code=503
            )
        return JSONResponse({"status": "ready", "service": name, "checks": checks})

    return app
