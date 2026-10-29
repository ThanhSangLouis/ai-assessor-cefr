"""Guided listening in the app (D056): the moments, the learner's answers, the analysis.

Only the learner who recorded a response listens to it this way, only once it
has a result, and only where `AICEFR_GUIDED_REPLAY` is on. A learner whose
feedback is held back by the feedback study (D040) is not offered it: the
moments come from the evidence that study withholds. The moments are sent
without saying which are the machine's (`report/replay.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, STUDENT_ONLY, require_login
from aicefr.contracts import ResponseStatus
from aicefr.report.replay import CHOICES, analyse, moments
from aicefr.services.core.assessment import study_api
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account
from aicefr.storage.replay_repository import ReplayRepository

router = APIRouter()

SCORED = (ResponseStatus.COMPLETED, ResponseStatus.REVIEW_REQUIRED)


def labels() -> ReplayRepository:
    return svc().replays  # type: ignore[return-value]


class AnswerIn(BaseModel):
    choice: str = Field(min_length=1, max_length=20)
    # What the learner meant to say there: their own words, kept for them.
    intended: str = Field(default="", max_length=300)


def _own_moments(response_id: str, account: Account):
    s = svc()
    if not s.settings.guided_replay:
        raise HTTPException(404, "bản triển khai này chưa bật nghe lại có dẫn đường")
    if s.repo.owner_of(response_id) != account.account_id:
        raise HTTPException(404, "không có bài này")
    if study_api.withholds(account.account_id):
        raise HTTPException(409, "trong thời gian thực nghiệm, bài nghe lại chưa mở với bạn")
    report = s.repo.get(response_id)
    if report is None or report.status not in SCORED or report.practice is not None:
        raise HTTPException(409, "bài chưa có kết quả đánh giá")
    return moments(report)


@router.get("/api/v1/responses/{response_id}/replay", tags=["student"])
def replay(response_id: str, account: Account = STUDENT_ONLY) -> dict:
    """The moments to listen to, in their fixed shuffled order, with the answers given so far."""
    found = _own_moments(response_id, account)
    given = {x["moment_id"]: x for x in labels().of_response(response_id)}
    return {
        "choices": CHOICES,
        "moments": [
            {
                **m.public(),
                "choice": given.get(m.moment_id, {}).get("choice"),
                "intended": given.get(m.moment_id, {}).get("intended") or "",
            }
            for m in found
        ],
    }


@router.post("/api/v1/responses/{response_id}/replay/{moment_id}", tags=["student"])
def answer(response_id: str, moment_id: str, body: AnswerIn, account: Account = STUDENT_ONLY):
    if body.choice not in CHOICES:
        raise HTTPException(422, "lựa chọn không hợp lệ")
    by_id = {m.moment_id: m for m in _own_moments(response_id, account)}
    m = by_id.get(moment_id)
    if m is None:
        raise HTTPException(404, "không có đoạn này")
    saved = labels().save(
        {
            "response_id": response_id,
            "moment_id": moment_id,
            "account_id": account.account_id,
            "source": m.source,
            "kind": m.kind,
            "start_s": m.start_s,
            "end_s": m.end_s,
            "choice": body.choice,
            "intended": body.intended.strip(),
        }
    )
    return {"moment_id": moment_id, "choice": saved["choice"]}


def my_labels(account_id: str) -> list[dict]:
    """A learner's own answers, as they read them back: no source, no kind."""
    return [
        {
            "response_id": x["response_id"],
            "start_s": x["start_s"],
            "end_s": x["end_s"],
            "answer": CHOICES.get(x["choice"], x["choice"]),
            "intended": x["intended"] or "",
            "created_at": x["created_at"],
        }
        for x in labels().of_account(account_id)
    ]


@router.get("/api/v1/me/replay-labels", tags=["student"])
def my_replay_labels(account: Account = Depends(require_login)) -> list[dict]:
    """What I said about my own recordings, to read back on my progress page."""
    return my_labels(account.account_id)


@router.get("/api/v1/admin/replay/report", tags=["admin"])
def replay_report(account: Account = ADMIN_ONLY) -> dict:
    """Machine moments against random ones, over learners who allowed research use."""
    allowed = set(svc().peers.identity.research_allowed())
    return analyse([x for x in labels().all() if x["account_id"] in allowed])
