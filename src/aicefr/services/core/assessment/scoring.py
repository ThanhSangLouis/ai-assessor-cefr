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
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from aicefr.contracts import ProcessingRequest, ReasonCode, Response, ResponseStatus
from aicefr.services.core.assessment.context import active_model_name, active_qc, svc
from aicefr.storage.task_repository import Task, task_message

logger = logging.getLogger(__name__)

WAITING = (ResponseStatus.QUEUED, ResponseStatus.RUNNING)
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
            # D050: with Redis, an assessment is scored before a practice
            # attempt waiting in the same queue (BullMQ: lower runs first).
            "priority": 5 if task.is_practice else 1,
            # D051: for the time the job waits in the queue.
            "enqueued_at": time.time(),
        },
    )


def settle_charge(rid: str) -> None:
    """Tell the metering service how a response ended (D049): a result is charged
    for what the recording lasted, anything else releases the hold.

    A result is a score or an estimate waiting for a teacher, or a practice
    attempt's outcome. Never raises: a charge that could not be settled is
    released by the metering sweep, and the person's result must not wait on it.
    """
    s = svc()
    metering = getattr(s.peers, "metering", None)
    if metering is None:
        return
    try:
        report = s.repo.get(rid)
        status = s.repo.status_of(rid)
        if report is None or status is None:
            return
        result = report.status in (ResponseStatus.COMPLETED, ResponseStatus.REVIEW_REQUIRED) and (
            report.assessment is not None or report.practice is not None
        )
        seconds = report.qc.duration_ms / 1000 if report.qc else None
        action = "practice" if status["purpose"] == "practice" else "assess"
        # D057: the tokens the recogniser used, counted by it where it can.
        asr = report.asr
        metering.settle(
            key=rid,
            action=action,
            result=result,
            seconds=seconds,
            output_tokens=asr.output_tokens if asr else None,
            words=len(asr.words) if asr else None,
        )
    except Exception:  # noqa: BLE001 - see the docstring
        logger.exception("could not settle the charge of %s", rid)


def on_scoring(message: dict) -> None:
    """One report of the speech service about one response."""
    repo = svc().repo
    rid = message["response_id"]
    if message.get("status") == ResponseStatus.RUNNING.value:
        repo.mark_running(rid)
        return
    if "failed" in message:
        repo.set_status(
            rid, ResponseStatus.FAILED, [ReasonCode(message["failed"])], only_from=WAITING
        )
        settle_charge(rid)
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
        repo.set_status(
            rid, ResponseStatus.FAILED, [ReasonCode.PROCESSING_INTERRUPTED], only_from=WAITING
        )
    settle_charge(rid)


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
    candidates = [(rid, ResponseStatus.RUNNING) for rid in s.repo.running_since(cutoff)]
    candidates += [(rid, ResponseStatus.QUEUED) for rid in s.repo.queued_since(queued_cutoff)]
    failed = [
        rid
        for rid, state in candidates
        if s.repo.set_status(
            rid, ResponseStatus.FAILED, [ReasonCode.PROCESSING_INTERRUPTED], only_from=(state,)
        )
    ]
    if failed:
        logger.warning("job quá hạn %ss, đánh dấu FAILED: %s", limit, failed)
    for rid in failed:
        settle_charge(rid)
    return failed


def sweep_forever(stop: threading.Event, every_s: float = 30.0) -> None:
    while not stop.wait(every_s):
        try:
            sweep_overdue()
        except Exception:  # noqa: BLE001 - the sweep thread must not die of one error
            logger.exception("job-timeout sweep failed")
