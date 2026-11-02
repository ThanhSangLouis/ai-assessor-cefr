"""Live events of the assessment service (D086): the stream, and what is told on it.

`GET /api/v1/me/events` keeps one `text/event-stream` response open per tab.
Three kinds of event go down it, each with ids only -- the page asks the usual
API for the rest, under the usual access rules (D071):

* `response.finished` to the student, when their response leaves the queue
  (scored, flagged for a teacher, or failed);
* `review.done` to the student, when a teacher decides or closes it;
* `queue.changed` to the teachers of the student's classes and to every
  administrator, when the review queue gains, loses or locks a response.

Every page that listens still works without the stream: the progress page
keeps asking for the status, the queue keeps its refresh button.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from aicefr.api.deps import require_login
from aicefr.contracts import ResponseStatus
from aicefr.platform.live import TooManyConnections, stream
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account, Role

logger = logging.getLogger(__name__)
router = APIRouter()

RESPONSE_FINISHED = "response.finished"
REVIEW_DONE = "review.done"
QUEUE_CHANGED = "queue.changed"


@router.get("/api/v1/me/events", tags=["me"])
async def events(account: Account = Depends(require_login)) -> StreamingResponse:
    """The signed-in account's live events, as Server-Sent Events. D086."""
    s = svc()
    if s.live is None:
        raise HTTPException(404, "không có luồng sự kiện")
    try:
        sub = s.live.hub.open(account.account_id, account.role.value)
    except TooManyConnections:
        raise HTTPException(429, "đang mở quá nhiều tab cùng lúc") from None
    return StreamingResponse(
        stream(
            s.live.hub,
            sub,
            heartbeat_s=s.settings.live_heartbeat_s,
            lifetime_s=s.settings.live_max_s,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            # nginx: pass each frame on at once instead of buffering the response.
            "X-Accel-Buffering": "no",
        },
    )


# ================================================================= what is told


def _quietly(tell: Callable[..., None]) -> Callable[..., None]:
    """Telling is never the action's failure: a scored response must not be
    re-scored (the bus retries a handler that raised), nor a saved decision
    answered with 500, because looking up whom to tell failed."""

    @functools.wraps(tell)
    def run(*args, **kwargs) -> None:
        try:
            tell(*args, **kwargs)
        except Exception:  # noqa: BLE001 - see the docstring
            logger.exception("could not tell %s", tell.__name__)

    return run


@_quietly
def queue_changed(owner_id: str | None) -> None:
    """The review queue of whoever reviews this student's work changed."""
    s = svc()
    if s.live is None:
        return
    teachers = s.classrooms.teachers_of(owner_id) if s.classrooms and owner_id else set()
    s.live.notify(QUEUE_CHANGED, accounts=teachers, roles=(Role.ADMIN.value,))


@_quietly
def response_finished(response_id: str, owner_id: str | None = None) -> None:
    """The response left the scoring queue: tell its owner, and its reviewers if flagged."""
    s = svc()
    if s.live is None:
        return
    owner_id = owner_id or s.repo.owner_of(response_id)
    status = (s.repo.status_of(response_id) or {}).get("status")
    if status in (None, ResponseStatus.QUEUED.value, ResponseStatus.RUNNING.value):
        return
    s.live.notify(
        RESPONSE_FINISHED, {"response_id": response_id, "status": status}, accounts=[owner_id]
    )
    if status == ResponseStatus.REVIEW_REQUIRED.value:
        queue_changed(owner_id)


@_quietly
def review_done(response_id: str) -> None:
    """A teacher decided or closed the response: tell its owner, and the other reviewers."""
    s = svc()
    if s.live is None:
        return
    owner_id = s.repo.owner_of(response_id)
    status = (s.repo.status_of(response_id) or {}).get("status")
    s.live.notify(REVIEW_DONE, {"response_id": response_id, "status": status}, accounts=[owner_id])
    queue_changed(owner_id)
