"""Achievements: milestones of the learner's own effort. D032.

What earns one, and what never does:

* **Effort only.** Seconds spoken, days practised, lessons finished, a step
  tried again until it passed, a review done, an assessment taken. Never a
  score, a band or a pass rate: those are estimates whose error is about half
  a band on a 0-6 scale, and a medal for a number the learner does not
  control teaches that the number is the goal. Praise for the process keeps
  learners trying after a setback; praise for ability does the opposite
  (Mueller and Dweck 1998).
* **Private.** Only the learner sees them: no leaderboard, nothing a classmate
  or a teacher can rank. In Hanus and Fox (2015) a semester of badges WITH a
  leaderboard left students less motivated than the same course without them;
  the comparison is the part left out here.
* **Informing, not controlling.** Each one says plainly what was done and how
  far the next one is. None expires, none counts down, none warns of a loss:
  rewards felt as controlling undermine interest, rewards that inform about
  competence tend not to (Deci, Koestner and Ryan 1999).
* **Never taken back.** Once reached an achievement stays, even if the
  attempts behind it are deleted or a teacher corrects a result -- losing a
  medal for an act of honesty would punish the wrong thing. Erasing the
  account erases them (the storage layer does that, not this module).

This module is pure: the API counts `Facts` from stored attempts and the
storage layer keeps what was reached and when.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from aicefr.practice.streak import local_day, longest_streak

# A return after this many days or more without practice counts as a comeback.
PAUSE_DAYS = 3
# Scored assessments the progress page needs before it speaks of a trend
# (MIN_RESULTS_FOR_TREND in api/main.py; a test keeps the two equal).
ASSESSMENTS_FOR_TREND = 5


@dataclass(frozen=True)
class Take:
    """One stored attempt, as far as achievements care."""

    lesson_id: str
    step_id: str
    created_at: str
    speaking_s: float
    passed: bool
    free: bool = False  # a free-speaking step, or a review of one
    review: bool = False  # made in the review session


@dataclass(frozen=True)
class Facts:
    """What the learner has done, counted from what is stored."""

    takes: int = 0  # attempts the machine measured speech in
    speaking_s: float = 0.0
    best_streak: int = 0
    goal_days: int = 0
    comebacks: int = 0
    lessons_completed: int = 0
    units_completed: int = 0
    free_takes: int = 0
    retried_steps: int = 0
    reviews: int = 0
    assessments: int = 0  # assessments that came back with a result


def count(
    takes: Iterable[Take],
    goal_seconds: float,
    lessons_completed: int = 0,
    units_completed: int = 0,
    assessments: int = 0,
) -> Facts:
    """Count the facts from attempts given oldest first.

    Only attempts the machine measured speech in count: a clip of silence or of
    another language is stored with no speaking time, and counting it would
    reward pressing the button rather than speaking.
    """
    spoken = [t for t in takes if t.speaking_s > 0]
    per_day: dict[date, float] = {}
    for t in spoken:
        d = local_day(t.created_at)
        per_day[d] = per_day.get(d, 0.0) + t.speaking_s
    ordered = sorted(per_day)

    # A step counts once when a pass follows a miss on it. Review attempts are
    # left out: a review is a new sentence each time, not another try at the
    # same step.
    missed: set[tuple[str, str]] = set()
    retried: set[tuple[str, str]] = set()
    for t in spoken:
        if t.review:
            continue
        key = (t.lesson_id, t.step_id)
        if not t.passed:
            missed.add(key)
        elif key in missed:
            retried.add(key)

    return Facts(
        takes=len(spoken),
        speaking_s=round(sum(t.speaking_s for t in spoken), 1),
        best_streak=longest_streak(set(per_day)),
        goal_days=sum(1 for s in per_day.values() if s >= goal_seconds),
        comebacks=sum(1 for a, b in pairwise(ordered) if (b - a).days > PAUSE_DAYS),
        lessons_completed=lessons_completed,
        units_completed=units_completed,
        free_takes=sum(1 for t in spoken if t.free),
        retried_steps=len(retried),
        reviews=sum(1 for t in spoken if t.review),
        assessments=assessments,
    )


@dataclass(frozen=True)
class Achievement:
    code: str
    group: str
    title: str
    description: str
    icon: str  # a symbol of static/icons.svg
    target: int
    unit: str  # how the progress is written: "2/3 ngày"
    measure: Callable[[Facts], float]


GROUPS = {
    "habit": "Đều đặn",
    "voice": "Thời gian nói",
    "path": "Lộ trình",
    "persistence": "Kiên trì",
    "assessment": "Đánh giá",
}

CATALOG: tuple[Achievement, ...] = (
    Achievement(
        "streak_3",
        "habit",
        "Ba ngày liền",
        "Luyện nói ba ngày liên tiếp.",
        "flame",
        3,
        "ngày",
        lambda f: f.best_streak,
    ),
    Achievement(
        "streak_7",
        "habit",
        "Tròn một tuần",
        "Giữ chuỗi bảy ngày. Mỗi tuần được nghỉ một ngày mà chuỗi không đứt.",
        "flame",
        7,
        "ngày",
        lambda f: f.best_streak,
    ),
    Achievement(
        "streak_30",
        "habit",
        "Ba mươi ngày",
        "Giữ chuỗi ba mươi ngày.",
        "flame",
        30,
        "ngày",
        lambda f: f.best_streak,
    ),
    Achievement(
        "goal_1",
        "habit",
        "Đủ mục tiêu ngày",
        "Nói đủ mục tiêu của một ngày.",
        "target",
        1,
        "ngày",
        lambda f: f.goal_days,
    ),
    Achievement(
        "goal_10",
        "habit",
        "Mười ngày đủ mục tiêu",
        "Mười ngày nói đủ mục tiêu, không cần liên tiếp.",
        "target",
        10,
        "ngày",
        lambda f: f.goal_days,
    ),
    Achievement(
        "comeback",
        "habit",
        "Quay lại",
        "Luyện tiếp sau ba ngày trở lên không luyện. Nghỉ rồi quay lại vẫn là giữ nhịp.",
        "sun",
        1,
        "lần",
        lambda f: f.comebacks,
    ),
    Achievement(
        "take_1",
        "voice",
        "Lượt nói đầu tiên",
        "Ghi một lượt nói mà máy nghe được tiếng nói.",
        "mic",
        1,
        "lượt",
        lambda f: f.takes,
    ),
    Achievement(
        "minutes_10",
        "voice",
        "Mười phút",
        "Tổng cộng mười phút nói trong bài học và phần ôn.",
        "clock",
        10,
        "phút",
        lambda f: f.speaking_s // 60,
    ),
    Achievement(
        "minutes_60",
        "voice",
        "Một giờ",
        "Tổng cộng sáu mươi phút nói.",
        "clock",
        60,
        "phút",
        lambda f: f.speaking_s // 60,
    ),
    Achievement(
        "lesson_1",
        "path",
        "Bài học đầu tiên",
        "Hoàn thành một bài học.",
        "book-open",
        1,
        "bài",
        lambda f: f.lessons_completed,
    ),
    Achievement(
        "lesson_10",
        "path",
        "Mười bài học",
        "Hoàn thành mười bài học.",
        "book-open",
        10,
        "bài",
        lambda f: f.lessons_completed,
    ),
    Achievement(
        "unit_1",
        "path",
        "Xong một chặng",
        "Hoàn thành mọi bài học của một chặng.",
        "path",
        1,
        "chặng",
        lambda f: f.units_completed,
    ),
    Achievement(
        "free_1",
        "persistence",
        "Nói tự do",
        "Nói một lượt ở bước nói tự do, không có văn bản để dựa vào.",
        "chat",
        1,
        "lượt",
        lambda f: f.free_takes,
    ),
    Achievement(
        "retry_1",
        "persistence",
        "Thử lại và qua",
        "Qua một bước mà lần trước chưa qua.",
        "check-circle",
        1,
        "bước",
        lambda f: f.retried_steps,
    ),
    Achievement(
        "review_10",
        "persistence",
        "Mười lượt ôn",
        "Nói mười lượt trong phần Ôn tập.",
        "refresh",
        10,
        "lượt",
        lambda f: f.reviews,
    ),
    Achievement(
        "assessment_1",
        "assessment",
        "Bài đánh giá đầu tiên",
        "Nộp một bài đánh giá và nhận kết quả.",
        "file-check",
        1,
        "bài",
        lambda f: f.assessments,
    ),
    Achievement(
        "assessment_5",
        "assessment",
        "Đủ để thấy xu hướng",
        "Năm bài đánh giá có kết quả: từ đây trang Tiến độ mới nói về xu hướng.",
        "trend",
        ASSESSMENTS_FOR_TREND,
        "bài",
        lambda f: f.assessments,
    ),
)

BY_CODE = {a.code: a for a in CATALOG}


@dataclass(frozen=True)
class Standing:
    """How far the learner is towards one achievement, by the facts of today."""

    achievement: Achievement
    value: int  # capped at the target: "45/30 ngày" says nothing more than "30/30"

    @property
    def reached(self) -> bool:
        return self.value >= self.achievement.target

    @property
    def share(self) -> float:
        return self.value / self.achievement.target


def standings(facts: Facts) -> list[Standing]:
    return [Standing(a, min(int(a.measure(facts)), a.target)) for a in CATALOG]


def reached(facts: Facts) -> set[str]:
    return {s.achievement.code for s in standings(facts) if s.reached}


def nearest(facts: Facts, unlocked: Iterable[str]) -> Standing | None:
    """The locked achievement the learner is closest to, if they have started on any.

    Shown as "sắp đạt": people speed up as a goal comes into sight (the
    goal-gradient effect, Kivetz, Urminsky and Zheng 2006). An achievement
    with nothing done yet is not near, so a new learner is shown none rather
    than a 0/30. Ties go to the first in the catalogue.
    """
    done = set(unlocked)
    open_ = [
        s
        for s in standings(facts)
        if s.achievement.code not in done and s.value > 0 and not s.reached
    ]
    return max(open_, key=lambda s: s.share, default=None)
