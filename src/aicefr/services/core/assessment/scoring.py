"""Handing a recording to the speech service, and taking its answer back (D043).

`dispatch` sends one job to `speech.score` with everything the worker needs:
the recording's key in the blob store, the task, the QC thresholds in force and
the scoring model's name -- the worker keeps no store of its own.

`on_scoring` takes the worker's two reports on `assessment.scoring`: "started"
moves a QUEUED response to RUNNING, and the result is saved only onto a
response that still exists and still waits (`must_exist`): a response the
student deleted while it was being scored is not brought back, and a teacher's
decision is never overwritten by a late machine result.

A job can still be lost for good -- a worker killed mid-way with no broker to
hand the message on. `sweep_overdue` closes, as FAILED, every response RUNNING
for longer than AICEFR_JOB_TIMEOUT, read from the database so that any
instance of the service can do it.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from aicefr.contracts import ProcessingRequest, ReasonCode, Response, Status
from aicefr.services.core.assessment.context import active_model_name, active_qc, svc
from aicefr.storage.task_repository import Task, task_message

logger = logging.getLogger(__name__)

WAITING = (Status.QUEUED, Status.RUNNING)
SCORE_QUEUE = "speech.score"
RESULT_QUEUE = "assessment.scoring"


def dispatch(request: ProcessingRequest, audio_key: str, task: Task, account_id: str) -> None:
    thresholds, qc_version = active_qc()
    svc().bus.send(
        SCORE_QUEUE,
        {
            "response_id": request.response_id,
            "audio_key": audio_key,
            "request": request.model_dump(mode="json"),
            "task": task_message(task),
            "qc": {"thresholds": asdict(thresholds), "version": qc_version},
            "model": active_model_name(),
            "speaker_id": request.speaker_id,
            "task_id": request.task_id,
            "account_id": account_id,
        },
    )


def on_scoring(message: dict) -> None:
    """One report of the speech service about one response."""
    repo = svc().repo
    rid = message["response_id"]
    if message.get("status") == Status.RUNNING.value:
        repo.mark_running(rid)
        return
    if "failed" in message:
        repo.set_status(rid, Status.FAILED, [ReasonCode(message["failed"])], only_from=WAITING)
        return
    try:
        report = Response.model_validate(message["report"])
        # must_exist: a response deleted while it was scored is not re-created.
        repo.save(
            report,
            message["speaker_id"],
            message["task_id"],
            account_id=message["account_id"],
            must_exist=True,
        )
    except Exception:  # noqa: BLE001 - whatever failed, the response must not stay waiting
        logger.exception("could not save the result of %s", rid)
        repo.set_status(rid, Status.FAILED, [ReasonCode.PROCESSING_INTERRUPTED], only_from=WAITING)


# A response still QUEUED this many timeouts after it was submitted was lost
# before the speech service ever started it.
QUEUED_TIMEOUTS = 6


def sweep_overdue(now: datetime | None = None) -> list[str]:
    """Close as FAILED every response RUNNING for longer than AICEFR_JOB_TIMEOUT,
    and every one still QUEUED after QUEUED_TIMEOUTS of them.

    A recogniser call that hangs keeps the student waiting on a page that never
    changes. The worker cannot be stopped from here; the response is closed for
    the person, and if the worker answers at last, the result is dropped because
    the response no longer waits.
    """
    s = svc()
    now = now or datetime.now(UTC)
    limit = s.settings.job_timeout_s
    cutoff = (now - timedelta(seconds=limit)).isoformat(timespec="seconds")
    queued_cutoff = (now - timedelta(seconds=limit * QUEUED_TIMEOUTS)).isoformat(timespec="seconds")
    candidates = [(rid, Status.RUNNING) for rid in s.repo.running_since(cutoff)]
    candidates += [(rid, Status.QUEUED) for rid in s.repo.queued_since(queued_cutoff)]
    failed = [
        rid
        for rid, state in candidates
        if s.repo.set_status(
            rid, Status.FAILED, [ReasonCode.PROCESSING_INTERRUPTED], only_from=(state,)
        )
    ]
    if failed:
        logger.warning("job quá hạn %ss, đánh dấu FAILED: %s", limit, failed)
    return failed


def sweep_forever(stop: threading.Event, every_s: float = 30.0) -> None:
    while not stop.wait(every_s):
        try:
            sweep_overdue()
        except Exception:  # noqa: BLE001 - the sweep thread must not die of one error
            logger.exception("job-timeout sweep failed")
