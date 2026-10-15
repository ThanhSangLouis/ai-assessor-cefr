"""Pure timezone-aware 1/3/7-day spaced review schedule."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aicefr.practice.contracts import FrozenModel

LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
BOX_DAYS = {1: 1, 2: 3, 3: 7}
LAST_BOX = 3


class ReviewSchedule(FrozenModel):
    box: int
    due_at: datetime | None
    done: bool

    @classmethod
    def create(cls, box: int, due_at: datetime | None) -> ReviewSchedule:
        return cls(box=box, due_at=due_at, done=due_at is None)


def _local_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("review timestamps must be timezone-aware")
    return value.astimezone(LOCAL_ZONE)


def first_review(*, due_from: datetime) -> ReviewSchedule:
    local = _local_aware(due_from)
    return ReviewSchedule.create(1, local + timedelta(days=1))


def review_again(*, box: int, passed: bool, reviewed_at: datetime) -> ReviewSchedule:
    if box < 1:
        raise ValueError("review box must be positive")
    local = _local_aware(reviewed_at)
    if not passed:
        return ReviewSchedule.create(1, local + timedelta(days=1))
    if box >= LAST_BOX:
        return ReviewSchedule.create(LAST_BOX + 1, None)
    next_box = box + 1
    return ReviewSchedule.create(next_box, local + timedelta(days=BOX_DAYS[next_box]))
