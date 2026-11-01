"""What to remind a learner of when they open the app (D055).

A reminder never travels outside the app -- no e-mail, no message -- it
waits on the learner's home screen instead, at most three at a time, the most
pressing first. The rules are fixed and readable here, like the practice
suggestion:

* a streak of two days or more not yet kept today -- said once, kindly, with
  the rest day the streak allows (`streak.py`), never as a threat;
* reviews whose day has come;
* a daily goal begun and not yet met;
* no runs left, on a metered deployment.

Nothing here counts as a notification sent: the list is computed when asked,
stored nowhere, and empty when there is nothing to do.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from aicefr.practice.streak import LOCAL_TZ

MAX_NUDGES = 3
EVENING_HOUR = 17  # from here on, a streak not kept today is said more firmly


@dataclass(frozen=True)
class Nudge:
    kind: str
    text: str
    href: str
    urgent: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def nudges(
    now: datetime,
    daily: dict | None,
    reviews_due: int,
    runs_left: float | None,
) -> list[Nudge]:
    """The reminders for one learner at `now`, most pressing first.

    `daily` is the practice summary (`streak`, `practiced_today`, `today`,
    `goal`, `goal_met`); `runs_left` None where runs are not counted.
    """
    local = now.astimezone(LOCAL_TZ)
    out: list[Nudge] = []

    if daily and daily.get("streak", 0) >= 2 and not daily.get("practiced_today"):
        evening = local.hour >= EVENING_HOUR
        text = (
            f"Chuỗi {daily['streak']} ngày của bạn còn chờ hôm nay. Một bài ngắn là đủ; "
            "mỗi tuần bạn cũng có một ngày nghỉ mà không mất chuỗi."
        )
        out.append(Nudge("streak", text, "/practice", urgent=evening))

    if reviews_due > 0:
        out.append(Nudge("reviews", f"{reviews_due} mục ôn tập đã đến ngày.", "/practice/review"))

    if daily and daily.get("today", 0) > 0 and not daily.get("goal_met"):
        left = daily["goal"] - daily["today"]
        out.append(Nudge("goal", f"Còn {left} bài nữa là đạt mục tiêu hôm nay.", "/practice"))

    if runs_left is not None and runs_left < 1:
        out.append(
            Nudge(
                "credits",
                "Bạn đã hết lượt chấm. Lượt miễn phí làm mới vào ngày 16.",
                "/credits",
                urgent=True,
            )
        )

    out.sort(key=lambda n: not n.urgent)  # stable: urgent first, rule order kept
    return out[:MAX_NUDGES]
