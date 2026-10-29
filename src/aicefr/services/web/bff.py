"""What the pages ask that no single service owns: the sidebar's counts (D028, D029, D043).

A student: teacher decisions on their responses since they last opened their
list (assessment), and words or talks due for review today (learning). A
teacher: responses waiting in the review queue, less those they rate blind, and
their open blind-rating sheets (assessment). Counts only -- the pages
themselves say what the items are.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends

from aicefr.api.deps import require_login
from aicefr.services.web import pages
from aicefr.storage.auth_repository import Account, Role

router = APIRouter()


@router.get("/api/v1/me/badges", tags=["auth"])
def my_badges(account: Account = Depends(require_login)) -> dict:
    peers = pages.svc().peers
    if account.role == Role.STUDENT:
        return {
            **peers.assessment.student_badges(account_id=account.account_id),
            "reviews_due": peers.learning.reviews_due(account_id=account.account_id),
        }
    return peers.assessment.staff_badges(account_id=account.account_id)


@router.post("/api/v1/me/badges/{marker}/seen", tags=["auth"])
def mark_badge_seen(marker: Literal["results"], account: Account = Depends(require_login)) -> dict:
    """The person has looked: what was new until now no longer is."""
    seen_at = pages.svc().peers.assessment.mark_seen(account_id=account.account_id, marker=marker)
    return {"seen_at": seen_at}
