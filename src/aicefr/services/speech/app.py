"""The speech service: consumes recordings to score and lesson steps to measure (D043).

It has no store and no public routes. Its container runs this application for
the health checks and the bus consumers; the recogniser and the models live
only here, so only this image carries them.
"""

from __future__ import annotations

import threading

from aicefr.config import Settings, get_settings
from aicefr.infra.blobs import blob_store
from aicefr.platform.bus import MessageBus
from aicefr.services import Parts, Peers
from aicefr.services.speech.worker import (
    PROBE_QUEUE,
    RESULT_QUEUE,
    SCORE_QUEUE,
    STEP_QUEUE,
    SpeechWorker,
)

HEALTH_QUEUE = "speech.health"


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    worker = SpeechWorker(
        settings,
        blob_store(settings),
        report=lambda message: bus.send(RESULT_QUEUE, message),
    )
    # As many messages at once as the worker has recogniser slots.
    bus.consume(SCORE_QUEUE, worker.score, prefetch=settings.max_concurrent_jobs)
    bus.serve(STEP_QUEUE, worker.step, prefetch=settings.max_concurrent_jobs)
    bus.serve(PROBE_QUEUE, worker.probe)
    bus.serve(HEALTH_QUEUE, lambda _request: worker.health())
    if settings.asr_is_real:
        threading.Thread(target=worker.warm_up, name="asr-warm-up", daemon=True).start()
    return Parts(name="speech", routers=[], state={"speech": worker, "ready": worker.health})


def create_app():
    from aicefr.services.runtime import standalone

    return standalone("speech", build, get_settings())
