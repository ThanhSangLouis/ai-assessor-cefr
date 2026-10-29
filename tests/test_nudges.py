"""Reminders on the learner's home (D055): the rules, and the endpoint that gathers them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aicefr.practice.nudges import MAX_NUDGES, nudges

# 10:00 and 19:00 in Vietnam on 24/10/2026.
MORNING = datetime(2026, 10, 24, 3, 0, tzinfo=UTC)
EVENING = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
QUIET = {"streak": 0, "practiced_today": False, "today": 0, "goal": 2, "goal_met": False}


def task(state: str, due_on: str) -> dict:
    return {"state": state, "due_on": due_on, "task_id": "P3", "task_title": "Kể về một chuyến đi"}


@pytest.mark.unit
def test_nothing_to_do_means_no_reminder():
    assert nudges(MORNING, QUIET, 0, [], None) == []


@pytest.mark.unit
def test_an_overdue_assignment_comes_first_and_is_urgent():
    found = nudges(MORNING, QUIET, 3, [task("missing", "2026-10-20")], None)
    assert [n.kind for n in found] == ["assignment", "reviews"]
    assert found[0].urgent and found[0].href == "/?task=P3" and "20/10" in found[0].text


@pytest.mark.unit
def test_only_assignments_due_within_two_days_are_mentioned():
    found = nudges(
        MORNING,
        QUIET,
        0,
        [task("open", "2026-10-24"), task("open", "2026-10-25"), task("open", "2026-10-30")],
        None,
    )
    assert [n.text.split("hạn ")[1] for n in found] == ["hôm nay.", "ngày mai."]
    assert [n.urgent for n in found] == [True, False]


@pytest.mark.unit
def test_a_streak_not_kept_today_is_said_kindly_and_more_firmly_in_the_evening():
    daily = {**QUIET, "streak": 4}
    morning = nudges(MORNING, daily, 0, [], None)[0]
    evening = nudges(EVENING, daily, 0, [], None)[0]
    assert morning.kind == "streak" and "ngày nghỉ" in morning.text
    assert (morning.urgent, evening.urgent) == (False, True)
    kept = {**daily, "practiced_today": True, "today": 2, "goal_met": True}
    assert nudges(EVENING, kept, 0, [], None) == []


@pytest.mark.unit
def test_a_goal_begun_says_what_is_left():
    found = nudges(MORNING, {**QUIET, "today": 1, "practiced_today": True}, 0, [], None)
    assert [(n.kind, n.text) for n in found] == [("goal", "Còn 1 bài nữa là đạt mục tiêu hôm nay.")]


@pytest.mark.unit
def test_running_out_of_runs_is_said_only_where_runs_count():
    assert nudges(MORNING, QUIET, 0, [], None) == []
    assert nudges(MORNING, QUIET, 0, [], 2.0) == []
    assert nudges(MORNING, QUIET, 0, [], 0.0)[0].href == "/credits"


@pytest.mark.unit
def test_never_more_than_three():
    found = nudges(
        EVENING,
        {**QUIET, "streak": 5, "today": 0},
        4,
        [task("missing", "2026-10-20"), task("open", "2026-10-24")],
        0.0,
    )
    assert len(found) == MAX_NUDGES and all(n.urgent for n in found)


@pytest.mark.integration
def test_the_endpoint_gathers_an_assignment_due_today(tmp_path, monkeypatch):
    from test_billing import boot
    from test_classes import today
    from test_lessons_integration import login_as

    m = boot(tmp_path, monkeypatch)
    teacher = login_as(m, "GV-01", "teacher", terms=False)
    student = login_as(m, "SV-001")
    c = teacher.post("/api/v1/classes", json={"name": "Lớp thử"}).json()
    student.post("/api/v1/me/classes/join", json={"code": c["code"]})
    soon = (today() + timedelta(days=1)).isoformat()
    teacher.post(
        f"/api/v1/classes/{c['class_id']}/assignments", json={"task_id": "P3", "due_on": soon}
    )
    found = student.get("/api/v1/me/nudges").json()["nudges"]
    assert [n["kind"] for n in found] == ["assignment"]
    assert student.get("/api/v1/me/badges").json()["assignments"] == 1
    assert teacher.get("/api/v1/me/nudges").json() == {"nudges": []}
