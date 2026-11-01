"""The teacher's side of the assessment service: queue, lock, decide, statistics.

FR-29..FR-31 and FR-79 (D041). Only a teacher's decision through this router
can set `teacher_verified`; the reviewer is taken from the session, never from
the request, so the audit log can prove who changed a score.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from aicefr.api.deps import STAFF_ONLY
from aicefr.api.schemas import QueueItem, ReviewClose, ReviewDecision
from aicefr.contracts import ResponseStatus, Review
from aicefr.research.teacher_time import kpi as teacher_time_kpi
from aicefr.research.teacher_time import session_minutes
from aicefr.services.core.assessment.context import (
    blind,
    in_view,
    saw,
    students_in_view,
    svc,
)
from aicefr.storage.auth_repository import Account
from aicefr.storage.repository import InvalidStateError

router = APIRouter()


@router.get("/api/v1/review/queue", response_model=list[QueueItem], tags=["teacher"])
def review_queue(
    limit: int = Query(50, ge=1, le=200), account: Account = STAFF_ONLY
) -> list[QueueItem]:
    """The review queue, including who is currently looking at each response.

    D071: a teacher's queue holds the work of their classes' students, by
    name; an administrator's holds everyone's, students in no class included.
    Responses this teacher still has to rate blind are left out (D030): the
    queue shows the machine's band, which is what the blind rating must not see.
    """
    s = svc()
    hidden = s.ratings.blinded_responses(account.account_id)
    rows = s.repo.queue_with_locks(
        ResponseStatus.REVIEW_REQUIRED, limit + len(hidden), owners=students_in_view(account)
    )
    rows = [r for r in rows if r["response_id"] not in hidden][:limit]
    owners = [r["account_id"] for r in rows if r.get("account_id")]
    names = s.peers.identity.display_names(account_ids=owners) if owners else {}
    return [QueueItem(**r, student_name=names.get(r.get("account_id") or "")) for r in rows]


@router.post("/api/v1/review/{response_id}/lock", tags=["teacher"])
def lock_review(response_id: str, account: Account = STAFF_ONLY) -> dict:
    """Claim the right to review one response for 15 minutes. FR-29.

    Without this step, two teachers opening the same response would overwrite
    each other's decision and neither would know.
    """
    repo = svc().repo
    if repo.status_of(response_id) is None:
        raise HTTPException(404, "không tìm thấy bài này")
    in_view(account, response_id)
    blind(account, response_id)
    granted, holder = repo.lock_response(response_id, account.account_id, account.pseudonym)
    if not granted:
        raise HTTPException(409, f"bài đang được {holder} xem")
    saw(account, response_id, "review")
    repo.open_review_session(response_id, account.account_id)  # D041: when review began
    return {"status": "ok"}


@router.delete("/api/v1/review/{response_id}/lock", tags=["teacher"])
def unlock_review(response_id: str, account: Account = STAFF_ONLY) -> dict:
    repo = svc().repo
    repo.unlock_response(response_id, account.account_id)
    # D041: leaving without a decision ends the session; coming back starts a
    # new one, so a decision is timed from when the teacher came back to it.
    repo.close_review_session(response_id, account.account_id, "released")
    return {"status": "ok"}


@router.get("/api/v1/responses/{response_id}/history", tags=["teacher"])
def history(response_id: str, account: Account = STAFF_ONLY) -> list[Review]:
    """Edit history of a result: value before, value after, reason, and who did it. FR-31."""
    in_view(account, response_id)
    blind(account, response_id)
    saw(account, response_id, "history")
    return svc().repo.review_history(response_id)


@router.post("/api/v1/review/{response_id}", tags=["teacher"])
def submit_review(
    response_id: str, decision: ReviewDecision, account: Account = STAFF_ONLY
) -> JSONResponse:
    """A teacher approves or changes a score. Only this path can set teacher_verified."""
    repo = svc().repo
    in_view(account, response_id)
    blind(account, response_id)
    holder = repo.locked_by(response_id)
    if holder is not None and holder != account.pseudonym:
        raise HTTPException(409, f"bài đang được {holder} xem, chưa lưu được")
    try:
        out = repo.apply_review(
            response_id,
            account.account_id,
            decision.new_score,
            decision.new_band,
            decision.reason,
        )
    except InvalidStateError as e:
        # 409, not 422: the request is well formed, the response is simply not
        # in a state that accepts a decision.
        raise HTTPException(409, str(e)) from e
    if out is None:
        raise HTTPException(404, "không tìm thấy bài")
    repo.close_review_session(response_id, account.account_id, "decision")
    repo.unlock_response(response_id, account.account_id)
    return JSONResponse(out.model_dump(mode="json"))


@router.post("/api/v1/review/{response_id}/close", tags=["teacher"])
def close_review(
    response_id: str, decision: ReviewClose, account: Account = STAFF_ONLY
) -> JSONResponse:
    """Close a response the machine could not score, without a score: it becomes REJECTED."""
    repo = svc().repo
    in_view(account, response_id)
    blind(account, response_id)
    holder = repo.locked_by(response_id)
    if holder is not None and holder != account.pseudonym:
        raise HTTPException(409, f"bài đang được {holder} xem, chưa lưu được")
    try:
        out = repo.close_unscorable(response_id, account.account_id, decision.reason)
    except InvalidStateError as e:
        raise HTTPException(409, str(e)) from e
    if out is None:
        raise HTTPException(404, "không tìm thấy bài")
    repo.close_review_session(response_id, account.account_id, "closed")
    repo.unlock_response(response_id, account.account_id)
    return JSONResponse(out.model_dump(mode="json"))


@router.get("/api/v1/review/kpi", tags=["teacher"])
def teacher_kpi(account: Account = STAFF_ONLY) -> dict:
    """Teacher time with and without the machine, and what the machine settles alone. FR-79."""
    s = svc()
    review_minutes, idle = session_minutes(s.repo.review_sessions())
    rating_minutes = [t / 60 for t in s.ratings.all_times_to_rate()]
    alone, reached = s.repo.settled_counts()
    agreement = s.repo.cohort_stats().get("agreement") or {}
    return teacher_time_kpi(
        review_minutes,
        idle,
        rating_minutes,
        alone,
        reached,
        int(agreement.get("band_kept") or 0),
        int(agreement.get("decisions") or 0),
    )


@router.get("/api/v1/review/stats", tags=["teacher"])
def cohort_stats(account: Account = STAFF_ONLY) -> dict:
    """Class-level statistics. FR-29.

    Teacher-only rather than admin-only on purpose: this is the screen that
    tells a teacher whether the machine is worth trusting on their own class.
    """
    return svc().repo.cohort_stats(owners=students_in_view(account))
