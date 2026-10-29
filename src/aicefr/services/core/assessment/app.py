"""The assessment service: tasks, responses, review, blind rating, the feedback study (D043).

It receives recordings and keeps them in the blob store the speech service
reads, sends each one to be scored over the bus and takes the result back. A
change of consent announced by identity takes a learner out of the feedback
study at once.
"""

from __future__ import annotations

import logging
import threading

from aicefr.config import Settings
from aicefr.infra.blobs import LocalBlobStore
from aicefr.platform.bus import MessageBus
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.assessment import (
    admin_api,
    context,
    rating_api,
    responses_api,
    review_api,
    scoring,
    study_api,
)
from aicefr.services.core.assessment.facade import AssessmentFacade
from aicefr.storage.rating_repository import RatingRepository
from aicefr.storage.repository import Repository
from aicefr.storage.study_repository import StudyRepository
from aicefr.storage.task_repository import TaskRepository

logger = logging.getLogger(__name__)

CONSENT_CHANGED = "consent.changed"


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = settings.store("core")
    repo = Repository(store)
    tasks = TaskRepository(store)
    ratings = RatingRepository(store)  # after `repo`: its tables reference `response`
    studies = StudyRepository(store)
    context.configure(
        context.Services(
            settings=settings,
            repo=repo,
            tasks=tasks,
            ratings=ratings,
            studies=studies,
            blobs=LocalBlobStore(settings.upload_dir),
            bus=bus,
            peers=peers,
        )
    )
    rating_api.configure(
        rating_api.Services(ratings=ratings, repo=repo, task_lookup=tasks.get, peers=peers)
    )
    study_api.configure(study_api.Services(studies=studies, repo=repo, peers=peers))

    bus.consume(scoring.RESULT_QUEUE, scoring.on_scoring)

    def on_consent(event: dict) -> None:
        # D040: no research use, no study arm -- and full feedback again at once.
        if not event.get("research_use_allowed"):
            studies.withdraw(event["account_id"])

    bus.subscribe(CONSENT_CHANGED, "assessment", on_consent)

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
            internal_router("assessment", facade, settings.internal_token),
        ],
        facade=facade,
        state={"repo": repo, "studies": studies, "startup": startup, "ready": repo.stats},
    )
