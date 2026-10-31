"""The assessment service: tasks, responses, review, blind rating, the feedback study (D043).

It receives recordings and keeps them in the blob store the speech service
reads, sends each one to be scored over the bus and takes the result back.
"""

from __future__ import annotations

import logging
import threading

from aicefr.config import Settings
from aicefr.infra.blobs import blob_store
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.assessment import (
    admin_api,
    classes_api,
    coach_api,
    context,
    rating_api,
    replay_api,
    responses_api,
    review_api,
    scoring,
    study_api,
)
from aicefr.services.core.assessment.facade import AssessmentFacade
from aicefr.storage.classroom_repository import ClassroomRepository
from aicefr.storage.rating_repository import RatingRepository
from aicefr.storage.replay_repository import ReplayRepository
from aicefr.storage.repository import Repository
from aicefr.storage.study_repository import StudyRepository
from aicefr.storage.task_repository import TaskRepository

logger = logging.getLogger(__name__)


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = settings.store("core")
    blobs = blob_store(settings)
    repo = Repository(store, blobs=blobs)
    tasks = TaskRepository(store)
    ratings = RatingRepository(store, blobs=blobs)
    studies = StudyRepository(store)
    context.configure(
        context.Services(
            settings=settings,
            repo=repo,
            tasks=tasks,
            ratings=ratings,
            studies=studies,
            blobs=blobs,
            bus=bus,
            peers=peers,
            classrooms=ClassroomRepository(store),
            replays=ReplayRepository(store),
        )
    )
    rating_api.configure(
        rating_api.Services(
            ratings=ratings, repo=repo, task_lookup=tasks.get, peers=peers, blobs=blobs
        )
    )
    study_api.configure(study_api.Services(studies=studies, repo=repo, peers=peers))

    bus.consume(scoring.RESULT_QUEUE, scoring.on_scoring)

    stop = threading.Event()

    def startup() -> None:
        # With an in-process bus, whatever was queued or running died with the
        # last process: close it now rather than leave the submitter waiting.
        # A broker keeps the jobs, so they are left to finish.
        if not bus.durable:
            stuck = repo.fail_stuck(minutes=0)
            if stuck:
                logger.warning(
                    "đánh dấu FAILED cho %d bài treo khi khởi động: %s", len(stuck), stuck
                )
        if settings.job_mode != "inline":
            threading.Thread(
                target=scoring.sweep_forever, args=(stop,), name="job-timeout-sweep", daemon=True
            ).start()

    facade = AssessmentFacade(repo, ratings)
    return Parts(
        name="assessment",
        routers=[
            responses_api.router,
            review_api.router,
            admin_api.router,
            rating_api.router,
            study_api.router,
            classes_api.router,
            replay_api.router,
            coach_api.router,
            internal_router("assessment", facade, settings.internal_token),
        ],
        facade=facade,
        state={"repo": repo, "studies": studies, "startup": startup, "ready": repo.stats},
    )
