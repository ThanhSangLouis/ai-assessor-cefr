"""Where a learner stands in a path, and which lesson to take next (D025).

A lesson is complete when enough of its steps passed AND its free step was
done: scripted practice rarely carries over to free speech on its own, so the
free step is the part a lesson cannot be completed without.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import Lesson
from aicefr.practice.bank import CRITERION_NAMES
from aicefr.practice.streak import (
    LOCAL_TZ,
    WEEK_DAYS,
    local_day,
    longest_streak,
    rest_days,
    streak_length,
)

# Daily goal in seconds of actual speech: about one lesson. Speaking time is
# the honest unit for a speaking course -- an attempt count rewards pressing
# the button, a lesson count rewards hurrying.
DAILY_GOAL_SECONDS = 180


@dataclass(frozen=True)
class AttemptInfo:
    """What progress needs from a stored attempt."""

    lesson_id: str
    step_id: str
    passed: bool
    created_at: str
    speaking_s: float = 0.0


@dataclass(frozen=True)
class LessonState:
    lesson_id: str
    total: int
    passed: int
    free_done: bool
    started: bool

    def completed_with(self, ratio: float) -> bool:
        if self.total == 0:
            return False
        enough = self.passed >= ratio * self.total - 1e-9
        return enough and self.free_done

    @property
    def status(self) -> str:
        return "started" if self.started else "new"


def lesson_state(lesson: Lesson, attempts: Iterable[AttemptInfo]) -> LessonState:
    ids = {s.step_id for s in lesson.steps}
    free = set(lesson.free_step_ids)
    passed: set[str] = set()
    tried: set[str] = set()
    spoken: set[str] = set()
    for a in attempts:
        if a.lesson_id != lesson.lesson_id or a.step_id not in ids:
            continue
        tried.add(a.step_id)
        if a.speaking_s > 0:
            spoken.add(a.step_id)
        if a.passed:
            passed.add(a.step_id)
    return LessonState(
        lesson_id=lesson.lesson_id,
        total=len(ids),
        passed=len(passed),
        # A free step counts as done once it was attempted WITH speech, passed or
        # not: the point is to have spoken freely, not to clear a bar. An attempt
        # nothing could be measured in (silence, a rejected clip, another
        # language) is stored with no speaking time and does not count.
        free_done=free <= spoken if free else True,
        started=bool(tried),
    )


def is_complete(lesson: Lesson, state: LessonState) -> bool:
    return state.completed_with(lesson.pass_ratio)


@dataclass(frozen=True)
class NextLesson:
    lesson_id: str
    basis: str  # "weakest_criterion", "path_order", "review_all"
    reason: str


def next_lesson(
    ordered: Sequence[tuple[Lesson, Criterion | None]],
    states: dict[str, LessonState],
    weakest: Sequence[Criterion],
    band: Band | None,
) -> NextLesson | None:
    """The lesson to take next, with a reason that can be said out loud.

    `ordered` is every lesson of the path in path order, with the criterion of
    its unit or its own. The first unfinished lesson of the weakest criterion at
    the band of the latest assessment comes first; then the path order.
    """
    if not ordered:
        return None

    def unfinished(lesson: Lesson) -> bool:
        st = states.get(lesson.lesson_id)
        return st is None or not is_complete(lesson, st)

    if weakest and band is not None:
        focus = weakest[0]
        for lesson, crit in ordered:
            if crit is focus and lesson.band is band and unfinished(lesson):
                name = CRITERION_NAMES[focus].lower()
                return NextLesson(
                    lesson.lesson_id,
                    "weakest_criterion",
                    f"Bài đánh giá gần nhất cho thấy {name} là tiêu chí nên luyện trước, "
                    f"nên học bài {name} ở mức {band.value}.",
                )
    for lesson, _ in ordered:
        if unfinished(lesson):
            started = states.get(lesson.lesson_id)
            reason = (
                "Bạn đang học dở bài này."
                if started and started.started
                else "Bài tiếp theo trong lộ trình."
            )
            return NextLesson(lesson.lesson_id, "path_order", reason)
    first = ordered[0][0]
    return NextLesson(
        first.lesson_id,
        "review_all",
        "Bạn đã hoàn thành cả lộ trình. Học lại từ đầu để giữ kỹ năng, hoặc làm phần Ôn tập.",
    )


@dataclass(frozen=True)
class Today:
    seconds: float
    goal_seconds: int
    streak: int
    week: list[tuple[date, float]] = field(default_factory=list)
    # D032: the longest streak so far, the rest days the current streak used
    # within the week shown, and the seconds of the seven days before it.
    best_streak: int = 0
    rest_days: list[date] = field(default_factory=list)
    last_week_seconds: float = 0.0

    @property
    def goal_met(self) -> bool:
        return self.seconds >= self.goal_seconds

    @property
    def week_seconds(self) -> float:
        return round(sum(s for _d, s in self.week), 1)


def seconds_per_day(attempts: Iterable[AttemptInfo]) -> dict[date, float]:
    """Seconds of speech per Vietnam calendar day; attempts nothing was measured in add nothing."""
    per_day: dict[date, float] = {}
    for a in attempts:
        if a.speaking_s <= 0:
            continue
        d = local_day(a.created_at)
        per_day[d] = per_day.get(d, 0.0) + a.speaking_s
    return per_day


def today_summary(
    attempts: Iterable[AttemptInfo], now: datetime, goal_seconds: int = DAILY_GOAL_SECONDS
) -> Today:
    """Seconds spoken today (Vietnam time), the streak and the last seven days.

    The week is compared with the seven days before it, never with anyone
    else: the only fair yardstick for one learner's effort is that learner.
    """
    today = now.astimezone(LOCAL_TZ).date()
    per_day = seconds_per_day(attempts)
    days = set(per_day)
    week = [
        (today - timedelta(days=k), round(per_day.get(today - timedelta(days=k), 0.0), 1))
        for k in reversed(range(WEEK_DAYS))
    ]
    first = week[0][0]
    return Today(
        seconds=round(per_day.get(today, 0.0), 1),
        goal_seconds=goal_seconds,
        streak=streak_length(days, today),
        week=week,
        best_streak=longest_streak(days),
        rest_days=[d for d in rest_days(days, today) if d >= first],
        last_week_seconds=round(
            sum(per_day.get(first - timedelta(days=k), 0.0) for k in range(1, WEEK_DAYS + 1)), 1
        ),
    )
