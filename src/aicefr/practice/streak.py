"""Daily goal and practice streak. D023.

Two habit mechanisms of language-learning apps, kept as small as possible and
stripped of the harmful parts:

* **The daily goal** counts attempts that were FULLY PROCESSED that day. A
  rejected attempt (silence, not English) does not count: counting it would
  reward pressing the button, not speaking.
* **The streak** is the number of consecutive practice days. If the learner
  has not practised yet today, the streak still runs up to yesterday -- they
  have the rest of the day to keep it.
* **ONE rest day per week does not break the streak.** A hard streak that
  breaks on the first missed day is what makes learners give up: Sharif and
  Shu (UCLA Anderson Review, "Emergency reserves") found that allowing a
  "reserve" day makes people come back after a slip far more often than a
  strict rule. A rest day only counts when it sits BETWEEN two practice days,
  and two rest days must be at least 7 days apart.
* **No leaderboard.** Comparing with classmates turns a practice tool into a
  race, and the people at the bottom lose heart (Hanus and Fox 2015);
  `cohort_stats` refuses to rank for the same reason.

Days follow Vietnam time (UTC+7, no daylight saving), not UTC: practising at
6 a.m. in Vietnam is 11 p.m. the previous day in UTC, and a streak broken by a
time zone is a bug nobody can understand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta, timezone

LOCAL_TZ = timezone(timedelta(hours=7))
DAILY_GOAL = 2
WEEK_DAYS = 7


def local_day(iso: str) -> date:
    """The Vietnam calendar day of an ISO-8601 moment (the database stores UTC)."""
    moment = datetime.fromisoformat(iso)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(LOCAL_TZ).date()


FREE_SKIP_EVERY_DAYS = 7


def streak_length(days: set[date], today: date) -> int:
    """Number of practice days in the streak that ends today or yesterday.

    A day without practice does NOT break the streak when both the day before
    and the day after it have practice, and no other rest day was used within
    7 days of it. A rest day does not add to the length: it keeps the streak
    alive, it does not reward anything.
    """
    return _walk(days, today)[0]


def rest_days(days: set[date], today: date) -> list[date]:
    """The days without practice the current streak was kept alive across, oldest first.

    Shown on the week dots (D032) so the rule is seen rather than guessed: a
    learner who skipped Tuesday and still has a streak should be able to see
    why.
    """
    return sorted(_walk(days, today)[1])


def longest_streak(days: set[date]) -> int:
    """The longest streak ever reached: the best `streak_length` on any practice day.

    The streak on a given day only looks back from it, so this is exactly the
    largest number the learner was ever shown, rest days included.
    """
    return max((_walk(days, day)[0] for day in days), default=0)


def _walk(days: set[date], today: date) -> tuple[int, list[date]]:
    """Walk back from today: the streak length and the rest days it used."""
    one = timedelta(days=1)
    open_today = today not in days
    day = today - one if open_today else today
    n = 0
    skips: list[date] = []
    while True:
        if day in days:
            n += 1
            day -= one
            continue
        # A rest day needs a practice day AFTER it: either the streak has
        # already counted at least one day, or it is yesterday and today is
        # still open.
        after = n > 0 or (open_today and day == today - one)
        rested = all(abs((s - day).days) >= FREE_SKIP_EVERY_DAYS for s in skips)
        if after and (day - one) in days and rested:
            skips.append(day)
            day -= one
            continue
        return n, skips


@dataclass(frozen=True)
class DailySummary:
    today: int
    goal: int
    streak: int
    practiced_today: bool
    week: list[tuple[date, int]] = field(default_factory=list)

    @property
    def goal_met(self) -> bool:
        return self.today >= self.goal


def summarize(attempt_times: list[str], now: datetime, goal: int = DAILY_GOAL) -> DailySummary:
    """Summarise practice habits from the timestamps of fully processed attempts."""
    today = now.astimezone(LOCAL_TZ).date()
    counts: dict[date, int] = {}
    for t in attempt_times:
        d = local_day(t)
        counts[d] = counts.get(d, 0) + 1
    week = [
        (today - timedelta(days=k), counts.get(today - timedelta(days=k), 0))
        for k in reversed(range(WEEK_DAYS))
    ]
    return DailySummary(
        today=counts.get(today, 0),
        goal=goal,
        streak=streak_length(set(counts), today),
        practiced_today=today in counts,
        week=week,
    )
