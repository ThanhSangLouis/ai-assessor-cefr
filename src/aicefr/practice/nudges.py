"""What to remind a learner of when they open the app (D055).

Accounts are pseudonymous and carry no e-mail address or phone number (BR-02),
so a reminder cannot travel outside the app; it waits on the learner's home
screen instead, at most three at a time, the most pressing first. The rules
are fixed and readable here, like the practice suggestion:

* an assignment overdue, or due within two days;
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
from datetime import date, datetime, timedelta

from aicefr.practice.streak import LOCAL_TZ

MAX_NUDGES = 3
DUE_SOON_DAYS = 2
EVENING_HOUR = 17  # from here on, a streak not kept today is said more firmly


@dataclass(frozen=True)
class Nudge:
    kind: str
    text: str
    href: str
    urgent: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _dmy(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m")


def nudges(
    now: datetime,
    daily: dict | None,
    reviews_due: int,
    assignments: list[dict],
    runs_left: float | None,
) -> list[Nudge]:
    """The reminders for one learner at `now`, most pressing first.

    `daily` is the practice summary (`streak`, `practiced_today`, `today`,
    `goal`, `goal_met`); `assignments` the open ones (`state`, `due_on`,
    `task_id`, `task_title`); `runs_left` None where runs are not counted.
    """
    local = now.astimezone(LOCAL_TZ)
    today = local.date()
    out: list[Nudge] = []

    for a in sorted(assignments, key=lambda a: a["due_on"]):
        due = date.fromisoformat(a["due_on"])
        href = f"/?task={a['task_id']}"
        if a["state"] == "missing":
            text = (
                f"Bài “{a['task_title']}” đã quá hạn ngày {_dmy(a['due_on'])}."
                " Nộp muộn vẫn được ghi nhận."
            )
            out.append(Nudge("assignment", text, href, urgent=True))
        elif a["state"] == "open" and due - today <= timedelta(days=DUE_SOON_DAYS):
            days = (due - today).days
            when = {0: "hôm nay", 1: "ngày mai"}.get(days, f"ngày {_dmy(a['due_on'])}")
            out.append(
                Nudge(
                    "assignment", f"Bài “{a['task_title']}” hạn {when}.", href, urgent=due == today
                )
            )

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
