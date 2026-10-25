"""Layer 1 -- UNIT: achievements and the streak record, pure functions only (D032).

No application, no database. Days are Vietnam calendar days; the timestamps
are written in UTC as the database stores them, at 03:00 UTC (10:00 in
Vietnam) so no test sits on a day boundary.

Test case ids (TC-TT-Uxx) are listed in `docs/test/TEST_PLAN_D032.md`.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
from datetime import date, timedelta

import pytest

from aicefr.practice.achievements import (
    ASSESSMENTS_FOR_TREND,
    BY_CODE,
    CATALOG,
    GROUPS,
    PAUSE_DAYS,
    Facts,
    Take,
    count,
    nearest,
    reached,
    standings,
)
from aicefr.practice.streak import longest_streak, rest_days, streak_length

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 7)


def days(*ago: int) -> set[date]:
    return {TODAY - timedelta(days=k) for k in ago}


def take(
    ago: int,
    seconds: float = 30.0,
    passed: bool = True,
    step: str = "s1",
    lesson: str = "l1",
    **kind,
) -> Take:
    day = TODAY - timedelta(days=ago)
    return Take(
        lesson_id=lesson,
        step_id=step,
        created_at=f"{day.isoformat()}T03:00:00+00:00",
        speaking_s=seconds,
        passed=passed,
        **kind,
    )


# ---------------------------------------------------------------- the streak record


def test_the_longest_streak_is_the_best_the_learner_was_ever_shown():
    # 20..16 days ago: five days, with a rest day at 18 -> four practice days.
    # 10..4 days ago: seven days in a row. Then a gap, then today.
    practice = days(20, 19, 17, 16, *range(4, 11), 0)
    assert longest_streak(practice) == 7
    # Each value is one the learner saw on that day.
    assert longest_streak(practice) == max(streak_length(practice, d) for d in practice)
    assert streak_length(days(20, 19, 17, 16), TODAY - timedelta(days=16)) == 4
    assert longest_streak(set()) == 0


def test_the_rest_days_of_the_current_streak_are_named():
    # Practice today, 1, 3 and 4 days ago: day 2 was the rest day that kept it.
    practice = days(0, 1, 3, 4)
    assert streak_length(practice, TODAY) == 4
    assert rest_days(practice, TODAY) == [TODAY - timedelta(days=2)]
    # Two rest days less than seven days apart: the older one breaks the streak.
    assert rest_days(days(0, 2, 4), TODAY) == [TODAY - timedelta(days=1)]
    assert streak_length(days(0, 2, 4), TODAY) == 2
    assert rest_days(days(5, 6), TODAY) == []


# ---------------------------------------------------------------- counting facts


def test_only_measured_speech_counts():
    facts = count([take(0, 40.0), take(0, 0.0), take(1, 0.0), take(3, 20.0)], goal_seconds=30)
    assert facts.takes == 2
    assert facts.speaking_s == 60.0
    # The day with only an unmeasured clip is not a practice day: counted, it
    # would join today to three days ago across one rest day, a streak of 3.
    assert facts.best_streak == 1
    assert facts.goal_days == 1  # 40 s today against a 30 s goal; 20 s is short of it


def test_goal_days_use_the_learners_own_goal():
    takes = [take(0, 100.0), take(1, 70.0), take(1, 50.0), take(3, 60.0)]
    assert count(takes, goal_seconds=60).goal_days == 3
    assert count(takes, goal_seconds=120).goal_days == 1
    assert count(takes, goal_seconds=600).goal_days == 0


def test_a_step_counts_as_retried_once_a_pass_follows_a_miss():
    takes = [
        take(3, passed=False, step="a"),
        take(3, passed=True, step="a"),  # a miss, then a pass: one
        take(2, passed=True, step="a"),  # the same step again: still one
        take(2, passed=True, step="b"),
        take(1, passed=False, step="b"),  # a pass BEFORE the miss: not a retry
        take(1, passed=False, step="c", seconds=0.0),  # silence is not a miss
        take(0, passed=True, step="c"),
        take(1, passed=False, step="d", lesson="l2"),
        take(0, passed=True, step="d", lesson="l2", review=True),  # a review is a new sentence
    ]
    assert count(takes, goal_seconds=180).retried_steps == 1


def test_a_comeback_needs_three_days_without_practice():
    assert PAUSE_DAYS == 3
    # Practice on day 10 ago, then 6 ago: days 9, 8 and 7 without practice.
    assert count([take(10), take(6)], goal_seconds=180).comebacks == 1
    # Two days off (9 and 8) is a pause, not yet a comeback.
    assert count([take(10), take(7)], goal_seconds=180).comebacks == 0
    assert count([take(20), take(15), take(10), take(0)], goal_seconds=180).comebacks == 3


def test_free_steps_and_reviews_are_counted_apart():
    takes = [
        take(0, free=True),
        take(0, free=True, review=True),  # reviewing a free talk is free speech too
        take(0, review=True),
        take(0, free=True, seconds=0.0),
    ]
    facts = count(takes, goal_seconds=180)
    assert (facts.free_takes, facts.reviews) == (2, 2)


# ---------------------------------------------------------------- the catalogue


def test_no_achievement_reads_a_score_a_band_or_anyone_else():
    """BR-28: effort only. The facts are the only thing an achievement can read."""
    names = {f.name for f in dataclasses.fields(Facts)}
    assert names == {
        "takes",
        "speaking_s",
        "best_streak",
        "goal_days",
        "comebacks",
        "lessons_completed",
        "units_completed",
        "free_takes",
        "retried_steps",
        "reviews",
        "assessments",
    }
    for word in ("score", "band", "overall", "rank", "pass_rate", "others"):
        assert not any(word in name for name in names)
    source = (ROOT / "src" / "aicefr" / "practice" / "achievements.py").read_text("utf-8")
    assert "overall_0_6" not in source and "Band" not in source
    # Every measure reads Facts and nothing else: a measure on empty facts is 0.
    assert all(a.measure(Facts()) == 0 for a in CATALOG)


def test_the_catalogue_is_well_formed():
    codes = [a.code for a in CATALOG]
    assert len(codes) == len(set(codes)) == 17
    assert set(BY_CODE) == set(codes)
    assert {a.group for a in CATALOG} == set(GROUPS)
    assert all(a.target >= 1 and a.title and a.description and a.unit for a in CATALOG)
    sprite = (ROOT / "src" / "aicefr" / "api" / "static" / "icons.svg").read_text("utf-8")
    drawn = set(re.findall(r'symbol id="i-([a-z-]+)"', sprite))
    assert {a.icon for a in CATALOG} <= drawn


def test_the_trend_achievement_matches_the_progress_page():
    api = ROOT / "src" / "aicefr" / "services" / "core" / "assessment" / "responses_api.py"
    source = api.read_text("utf-8")
    assert int(re.search(r"^MIN_RESULTS_FOR_TREND = (\d+)$", source, re.M).group(1)) == (
        ASSESSMENTS_FOR_TREND
    )
    assert BY_CODE["assessment_5"].target == ASSESSMENTS_FOR_TREND


def test_reached_achievements_follow_the_facts():
    facts = Facts(
        takes=1,
        speaking_s=659.0,  # ten minutes and change
        best_streak=7,
        goal_days=1,
        lessons_completed=1,
        free_takes=1,
        assessments=4,
    )
    assert reached(facts) == {
        "streak_3",
        "streak_7",
        "goal_1",
        "take_1",
        "minutes_10",
        "lesson_1",
        "free_1",
        "assessment_1",
    }
    by_code = {s.achievement.code: s for s in standings(facts)}
    assert by_code["minutes_60"].value == 10  # minutes, not seconds
    assert by_code["streak_30"].value == 7
    assert by_code["streak_3"].value == 3  # capped at the target


def test_the_nearest_achievement_is_the_closest_one_started():
    facts = Facts(best_streak=5, goal_days=2, assessments=4, speaking_s=300.0)
    near = nearest(facts, unlocked={"streak_3", "goal_1"})
    assert near is not None
    assert (near.achievement.code, near.value) == ("assessment_5", 4)  # 4/5 beats 5/7
    # Nothing started: nothing is near, rather than a 0/30.
    assert nearest(Facts(), unlocked=set()) is None
    # A reached one is never shown as near, stored yet or not.
    assert nearest(Facts(takes=1), unlocked=set()) is None
