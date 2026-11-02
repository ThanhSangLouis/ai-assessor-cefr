"""Reminders on the learner's home (D055): the rules, and the endpoint that gathers them.

D075: classes set no assessments, so no reminder is about an assignment.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aicefr.practice.nudges import MAX_NUDGES, nudges

# 10:00 and 19:00 in Vietnam on 24/10/2026.
MORNING = datetime(2026, 10, 24, 3, 0, tzinfo=UTC)
EVENING = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
QUIET = {
    "streak": 0,
    "practiced_today": False,
    "seconds": 0,
    "goal_seconds": 300,
    "goal_met": False,
}


@pytest.mark.unit
def test_nothing_to_do_means_no_reminder():
    assert nudges(MORNING, QUIET, 0, None) == []


@pytest.mark.unit
def test_reviews_due_are_said():
    found = nudges(MORNING, QUIET, 3, None)
    assert [(n.kind, n.href) for n in found] == [("reviews", "/practice/review")]


@pytest.mark.unit
def test_a_streak_not_kept_today_is_said_kindly_and_more_firmly_in_the_evening():
    daily = {**QUIET, "streak": 4}
    morning = nudges(MORNING, daily, 0, None)[0]
    evening = nudges(EVENING, daily, 0, None)[0]
    assert morning.kind == "streak" and "ngày nghỉ" in morning.text
    assert (morning.urgent, evening.urgent) == (False, True)
    kept = {**daily, "practiced_today": True, "seconds": 300, "goal_met": True}
    assert nudges(EVENING, kept, 0, None) == []


@pytest.mark.unit
def test_a_goal_begun_says_what_is_left():
    found = nudges(MORNING, {**QUIET, "seconds": 130, "practiced_today": True}, 0, None)
    assert [(n.kind, n.text) for n in found] == [
        ("goal", "Còn 3 phút nói nữa là đạt mục tiêu hôm nay.")
    ]


@pytest.mark.unit
def test_running_out_of_runs_is_said_only_where_runs_count():
    assert nudges(MORNING, QUIET, 0, None) == []
    assert nudges(MORNING, QUIET, 0, 2.0) == []
    assert nudges(MORNING, QUIET, 0, 0.0)[0].href == "/credits"


@pytest.mark.unit
def test_never_more_than_three():
    found = nudges(EVENING, {**QUIET, "streak": 5, "seconds": 60, "practiced_today": False}, 4, 0.0)
    assert len(found) <= MAX_NUDGES


@pytest.mark.integration
def test_the_endpoint_gathers_the_learners_reminders(tmp_path, monkeypatch):
    from test_billing import boot
    from test_lessons_integration import login_as

    m = boot(tmp_path, monkeypatch)
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    assert student.get("/api/v1/me/nudges").json() == {"nudges": []}
    assert "assignments" not in student.get("/api/v1/me/badges").json()
    assert teacher.get("/api/v1/me/nudges").json() == {"nudges": []}
