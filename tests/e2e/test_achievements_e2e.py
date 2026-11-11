"""Layer 3 -- E2E for achievements and the week (D032), in a real browser.

Runs on the lesson path's own server (`test_lessons_e2e.py`): the energy voice
detector and a fake recogniser that hears the first sample lesson's passage,
so a step recorded here is measured like a spoken one.

Test case ids (TC-TT-Exx) are listed in `docs/test/TEST_PLAN_D032.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_lessons_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    LESSON,
    answer,
    browser,
    context,
    live_server,
    student,
)

pytestmark = pytest.mark.e2e


def test_a_first_recording_is_congratulated_then_listed_as_reached(student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    answer(student, live_server)
    expect(student.locator(".toast").last).to_contain_text("Thành tựu mới: Lượt nói đầu tiên")

    # D092: the roadmap lists achievements only beside reviews that are due;
    # the full list stays on the results page.
    student.goto("/my-progress#achievements")

    tile = student.locator(".ach", has_text="Lượt nói đầu tiên")
    expect(tile).to_have_class(re.compile(r"\bis-unlocked\b"))
    # D105: no "new" mark; the toast above said it once.
    expect(student.locator(".ach-fresh")).to_have_count(0)
    locked = student.locator(".ach", has_text="Ba ngày liền")
    expect(locked).to_have_class(re.compile(r"\bis-locked\b"))
    expect(locked.get_by_role("progressbar")).to_have_attribute("aria-valuemax", "3")
    assert "band" not in student.locator("#achievements").inner_text().lower()


def test_the_week_shows_the_streak_and_the_rest_day(student, live_server):
    from aicefr.lessons.model import StepKind, StepResult
    from aicefr.storage.lesson_repository import LessonRepository

    # A history on chosen days, stored the way the integration tests arrange one.
    acc = student.request.get("/api/v1/me").json()["account_id"]
    lessons = LessonRepository(live_server.db_path, seed=False)
    now = datetime.now(UTC)
    for ago in (12, 11, 10, 9, 8, 3, 1, 0):  # five days long ago; now three across a rest day
        at = (now - timedelta(days=ago)).isoformat(timespec="seconds")
        result = StepResult(
            step_id=f"{LESSON}-s1", kind=StepKind.READ_ALOUD, passed=True, speaking_s=40.0
        )
        lessons.add_attempt(acc, LESSON, 1, result, created_at=at)

    student.goto("/practice")

    today = student.locator(".today-card")
    expect(today.locator(".rm-streak")).to_contain_text("3 ngày liên tiếp")
    expect(today.locator(".week-dots li.rest")).to_have_count(1)
    expect(today.locator(".week-dots li.rest")).to_have_attribute(
        "title", re.compile("nghỉ, chuỗi vẫn giữ")
    )
    # D092 dropped the best streak, the 7-day total and the next achievement
    # from this card (owner, 07/11/2026). The column still scrolls with the page
    # when its cards are taller than the window.
    expect(student.locator("#path-side")).to_have_class(re.compile(r"\bis-tall\b"))
