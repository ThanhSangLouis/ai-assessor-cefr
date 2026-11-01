"""Layer 3 -- E2E for the learning-evidence features D039-D042, in a real browser.

Runs on the lesson path's own server (`test_lessons_e2e.py`), whose database
this module can arrange directly, the way the achievement tests arrange a week.

Test case ids (TC-LE-Exx) are listed in `docs/test/TEST_PLAN_D039_D042.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_lessons_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    LESSON,
    browser,
    context,
    live_server,
    student,
)
from test_practice_e2e import login  # noqa: E402

pytestmark = pytest.mark.e2e


def _page(browser, live_server, next_path: str, role: str = "student", pseudonym: str = ""):
    """A signed-in page in a context of its own, confirming every dialog."""
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(20_000)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    login(page, live_server, pseudonym or live_server.account(role), next_path)
    return page


def test_progress_page_names_the_pronunciation_patterns(student, live_server):
    from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
    from aicefr.storage.lesson_repository import LessonRepository

    acc = student.request.get("/api/v1/me").json()["account_id"]
    lessons = LessonRepository(live_server.db_path, seed=False)
    words = [
        WordMark(index=i, text=t, said=s, status=WordStatus.MISSED if s else WordStatus.HEARD)
        for i, (t, s) in enumerate(
            [("worked", "work"), ("night", "nigh"), ("help", None), ("cat", None)]
        )
    ]
    for _ in range(3):
        result = StepResult(step_id=f"{LESSON}-s2", kind=StepKind.REPEAT, passed=False, words=words)
        lessons.add_attempt(acc, LESSON, 1, result)

    student.goto("/my-progress")
    final = student.locator("#pronunciation .pron-item", has_text="Âm cuối")
    expect(final.locator(".badge")).to_contain_text("3/12 lần · 25%")
    expect(final.locator(".pron-examples")).to_contain_text("«night» → máy nghe «nigh»")
    expect(final.locator(".pron-tip")).to_contain_text("Bật nhẹ phụ âm cuối")
    ed = student.locator("#pronunciation .pron-item", has_text="Đuôi -ed")
    expect(ed.locator(".badge")).to_contain_text("Chưa đủ dữ liệu · 3/8")


def test_class_page_shows_class_pronunciation(browser, live_server):
    teacher = _page(browser, live_server, "/teach", "teacher")
    teacher.goto("/review/stats")
    expect(teacher.locator("#class-pronunciation-body")).not_to_contain_text("Không tải được")
    # D078: the teacher-time measurement is gone, for everyone.
    expect(teacher.locator("#teacher-time")).to_have_count(0)
