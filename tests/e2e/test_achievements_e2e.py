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


def test_a_first_recording_is_congratulated_then_listed_as_new_once(student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    answer(student, live_server)
    expect(student.locator(".toast").last).to_contain_text("Thành tựu mới: Lượt nói đầu tiên")

    student.goto("/practice")
    card = student.locator(".ach-card")
    expect(card.locator(".ach-tally")).to_contain_text("/17")
    expect(card.locator(".ach-fresh")).to_have_text("1 mới")
    card.get_by_role("link", name="Xem tất cả").click()
    student.wait_for_url(re.compile(r"/my-progress#achievements$"))

    tile = student.locator(".ach", has_text="Lượt nói đầu tiên")
    expect(tile).to_have_class(re.compile(r"\bis-unlocked\b.*\bis-new\b"))
    expect(tile.locator(".ach-fresh")).to_have_text("Mới")
    locked = student.locator(".ach", has_text="Ba ngày liền")
    expect(locked).to_have_class(re.compile(r"\bis-locked\b"))
    expect(locked.get_by_role("progressbar")).to_have_attribute("aria-valuemax", "3")
    # Seen once: the next visit shows it reached, no longer new.
    student.reload()
    expect(tile).to_have_class(re.compile(r"\bis-unlocked\b"))
    expect(student.locator(".ach.is-new")).to_have_count(0)
    assert "band" not in student.locator("#achievements").inner_text().lower()


def test_the_week_shows_the_record_and_the_rest_day(student, live_server):
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
    expect(today.locator(".streak")).to_contain_text("3 ngày liên tiếp")
    expect(today.locator(".streak-best")).to_contain_text("Kỷ lục của bạn: 5 ngày")
    expect(today.locator(".week-dots li.rest")).to_have_count(1)
    expect(today.locator(".week-dots li.rest")).to_have_attribute(
        "title", re.compile("nghỉ, chuỗi vẫn giữ")
    )
    expect(today.locator(".week-sum")).to_contain_text("7 ngày qua: 2 phút")
    expect(student.locator(".ach-card .ach-next")).to_contain_text("Tròn một tuần")
    # Four cards are taller than this window: the column scrolls with the page
    # instead of sticking and hiding the last card until the end of the trail.
    expect(student.locator("#path-side")).to_have_class(re.compile(r"\bis-tall\b"))
    student.locator(".ach-card").scroll_into_view_if_needed()
    expect(student.locator(".ach-card")).to_be_in_viewport()
