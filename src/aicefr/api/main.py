"""Every service in one process: the tests, and a single machine (D043, D044).

The system is three services (`aicefr.services`) -- core, speech, web -- each
its own container in a deployment, talking over HTTP and Redis. This module
builds all three into one FastAPI application instead: the web service gets
the core's facades as plain objects, and the bus delivers in this process.
The routes, the rules and the store are the same code; only the wiring differs.

Run with:  uvicorn aicefr.api.main:app --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Response as HttpResponse
from fastapi.responses import JSONResponse

from aicefr.api.middleware import (
    LoginRateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from aicefr.api.web import mount_static, templates
from aicefr.config import get_settings
from aicefr.infra.queues import InlineJobQueue, InProcessJobQueue
from aicefr.observability import render_metrics, setup_logging
from aicefr.platform.bus import InlineBus
from aicefr.services import PARTS, Peers
from aicefr.services.core import app as core_service
from aicefr.services.speech import app as speech_service
from aicefr.services.web import app as web_service

logger = logging.getLogger(__name__)

settings = get_settings()
bus = InlineBus(
    InlineJobQueue()
    if settings.job_mode == "inline"
    else InProcessJobQueue(settings.max_concurrent_jobs)
)
peers = Peers()  # filled with the core's facades as core is built
core_parts = core_service.build(settings, peers, bus)
speech_parts = speech_service.build(settings, peers, bus)
web_parts = web_service.build(settings, peers, bus)

# What the tests reach for by name.
repo = core_parts.state["repo"]
billing = core_parts.state["billing"]
billing_store = billing.store
blobs = core_parts.state["blobs"]
lessons = core_parts.state["lessons"]
speech = speech_parts.state["speech"]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(json_output=settings.is_production)
    logger.info("starting", extra={"event": "startup"})
    core_parts.state["startup"]()
    yield


app = FastAPI(
    title="SpeakUp",
    description=(
        "AI-assisted assessment of English speaking against CEFR A1-C2.\n\n"
        "A study aid, not a certification service: the system produces an "
        "**estimate**, and a teacher makes the final decision. Every report "
        "carries the versions of the model, features and thresholds that "
        "produced it.\n\n"
        "Interface text is Vietnamese by requirement (SRS); this API "
        "documentation and all identifiers are English."
    ),
    version=settings.version,
    lifespan=lifespan,
    # In production the schema is not public: /docs and /openapi.json hand an
    # attacker every route, parameter and model without needing an account.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)
# Order matters: the outermost middleware is added last, so the request id is
# established before anything else runs and is still set when the response
# leaves.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
mount_static(app)
# The administrator's account menu links to /docs only where the docs are served.
templates.env.globals["api_docs"] = app.docs_url is not None

for key in ("auth_repo", "callers", "plans"):
    setattr(app.state, key, core_parts.state[key])
for parts in (core_parts, speech_parts, web_parts):
    for router in parts.routers:
        # Internal routes are for services in separate processes; here every
        # facade is a plain object.
        if not router.prefix.startswith("/internal"):
            app.include_router(router)


@app.get("/healthz", tags=["admin"], include_in_schema=False)
def liveness() -> dict:
    """Is the process alive? Nothing more: a restart will not fix a missing model."""
    return {"status": "alive"}


@app.get("/readyz", tags=["admin"], include_in_schema=False)
def readiness() -> JSONResponse:
    """Can this instance actually serve traffic?

    Checks the three things that silently make the system useless: the database
    is writable, the scoring artifact loads, and the recogniser is reachable.
    Returns 503 when any of them fails, so a load balancer stops sending work.
    """
    from aicefr.scoring.scorer import RidgeScorer
    from aicefr.services.core.assessment.context import active_model_name

    checks: dict[str, object] = {}
    ok = True
    try:
        repo.stats()
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001 - report the failure, never raise here
        checks["database"] = f"failed: {e}"
        ok = False
    try:
        checks["scoring_model"] = RidgeScorer(active_model_name()).model_version
    except Exception as e:  # noqa: BLE001
        checks["scoring_model"] = f"failed: {e}"
        ok = False
    health = speech.health()
    checks["asr_engine"] = health["asr_engine"]
    checks["asr_is_real"] = health["asr_is_real"]
    checks["recording_enabled"] = health["recording_enabled"]
    return JSONResponse(
        {"status": "ready" if ok else "degraded", "checks": checks},
        status_code=200 if ok else 503,
    )


@app.get("/metrics", tags=["admin"], include_in_schema=False)
def metrics() -> HttpResponse:
    """Counters in Prometheus text format."""
    return HttpResponse(render_metrics(), media_type="text/plain; version=0.0.4")


def audit(limit: int = 100):
    """Every part's audit log merged by time, as the administrator's screen reads it."""
    from aicefr.storage.audit_repository import merge

    return merge([getattr(peers, part).audit_recent(limit=limit) for part in PARTS], limit)
