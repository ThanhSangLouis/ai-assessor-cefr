"""Personal effort summaries for learning practice."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from aicefr.practice.streak import LOCAL_TZ, local_day, longest_streak, rest_days, streak_length


@dataclass(frozen=True)
class Effort:
    created_at: str
    speaking_s: float


@dataclass(frozen=True)
class ProgressSummary:
    today_seconds: float
    goal_seconds: int
    streak_days: int
    record_days: int
    practiced_today: bool
    rest_days: tuple[str, ...]
    week: tuple[dict[str, int | float], ...]
    previous_week_seconds: float

    @property
    def week_seconds(self) -> float:
        return round(sum(float(item["seconds"]) for item in self.week), 1)

    @property
    def week_change_seconds(self) -> float:
        return round(self.week_seconds - self.previous_week_seconds, 1)

    def as_dict(self) -> dict:
        return {
            "timezone": "Asia/Ho_Chi_Minh",
            "today_seconds": self.today_seconds,
            "goal_seconds": self.goal_seconds,
            "goal_met": self.today_seconds >= self.goal_seconds,
            "streak_days": self.streak_days,
            "record_days": self.record_days,
            "practiced_today": self.practiced_today,
            "rest_days": list(self.rest_days),
            "week": list(self.week),
            "week_seconds": self.week_seconds,
            "previous_week_seconds": self.previous_week_seconds,
            "week_change_seconds": self.week_change_seconds,
        }


def summarize(efforts: Iterable[Effort], now: datetime, goal_seconds: int = 180) -> ProgressSummary:
    if goal_seconds <= 0:
        raise ValueError("goal_seconds must be positive")
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    today = now.astimezone(LOCAL_TZ).date()
    per_day: dict[date, float] = defaultdict(float)
    for effort in efforts:
        if effort.speaking_s > 0:
            per_day[local_day(effort.created_at)] += effort.speaking_s

    week_dates = [today - timedelta(days=offset) for offset in reversed(range(7))]
    first = week_dates[0]
    previous_dates = [first - timedelta(days=offset) for offset in range(7, 0, -1)]
    return ProgressSummary(
        today_seconds=round(per_day[today], 1),
        goal_seconds=goal_seconds,
        streak_days=streak_length(set(per_day), today),
        record_days=longest_streak(set(per_day)),
        practiced_today=today in per_day,
        rest_days=tuple(day.isoformat() for day in rest_days(set(per_day), today) if day >= first),
        week=tuple(
            {"date": day.isoformat(), "seconds": round(per_day[day], 1)} for day in week_dates
        ),
        previous_week_seconds=round(sum(per_day[day] for day in previous_dates), 1),
    )
