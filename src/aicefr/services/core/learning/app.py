"""The learning service: lesson paths, attempts, spaced review, achievements (D043)."""

from __future__ import annotations

from aicefr.config import Settings
from aicefr.infra.blobs import blob_store
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.qc import audio_qc
from aicefr.services import Parts, Peers
from aicefr.services.core.learning import drill_api, lessons_api, plans_api
from aicefr.services.core.learning.facade import LearningFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.drill_repository import DrillRepository
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.plan_repository import PlanRepository


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    # D051: a database of its own when AICEFR_LEARNING_DB is set.
    store = settings.store("learning")
    lessons = LessonRepository(store)
    plans = PlanRepository(store)
    drills = DrillRepository(store)
    blobs = blob_store(settings)
    audit_log = AuditLog(store, "learning")
    lessons_api.configure(
        lessons_api.Services(
            lessons=lessons,
            blobs=blobs,
            bus=bus,
            audit_log=audit_log,
            max_bytes=audio_qc.MAX_BYTES,
            peers=peers,
            drills=drills,
            passage_daily=settings.passage_daily,
        )
    )
    plans_api.configure(plans)
    facade = LearningFacade(lessons, blobs, audit_log, plans, drills)
    return Parts(
        name="learning",
        routers=[
            lessons_api.router,
            drill_api.router,
            plans_api.router,
            internal_router("learning", facade, settings.internal_token),
        ],
        facade=facade,
        state={
            "lessons": lessons,
            "plans": plans,
            "drills": drills,
            "blobs": blobs,
            "ready": lambda: {"paths": len(lessons.paths())},
        },
    )
