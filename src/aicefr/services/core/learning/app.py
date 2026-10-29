"""The learning service: lesson paths, attempts, spaced review, achievements (D043)."""

from __future__ import annotations

from aicefr.config import Settings
from aicefr.infra.blobs import LocalBlobStore
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.qc import audio_qc
from aicefr.services import Parts, Peers
from aicefr.services.core.learning import lessons_api
from aicefr.services.core.learning.facade import LearningFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.lesson_repository import LessonRepository


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = settings.store("core")
    lessons = LessonRepository(store)
    blobs = LocalBlobStore(settings.upload_dir)
    audit_log = AuditLog(store, "learning")
    lessons_api.configure(
        lessons_api.Services(
            lessons=lessons,
            blobs=blobs,
            bus=bus,
            audit_log=audit_log,
            max_bytes=audio_qc.MAX_BYTES,
            peers=peers,
        )
    )
    facade = LearningFacade(lessons, blobs, audit_log)
    return Parts(
        name="learning",
        routers=[lessons_api.router, internal_router("learning", facade, settings.internal_token)],
        facade=facade,
        state={
            "lessons": lessons,
            "blobs": blobs,
            "ready": lambda: {"paths": len(lessons.paths())},
        },
    )
