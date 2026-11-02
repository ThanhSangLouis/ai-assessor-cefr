"""Layer 3 -- E2E for the path model (D046), in a real browser.

Runs on the lesson path's own server (`test_lessons_e2e.py`). Test case ids
(TC-LP-Exx) are listed in `docs/test/TEST_PLAN_D045_D047.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_lessons_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    browser,
    context,
    live_server,
    student,
    teacher_page,
)

pytestmark = pytest.mark.e2e


def test_a_learner_follows_the_published_path_without_composing_one(student):
    """D068: learners follow the path teachers publish; composing is the teacher's (below)."""
    expect(student.locator(".path-trail")).to_be_visible()
    expect(student.locator("#my-plan")).to_have_count(0)
    expect(student.get_by_role("button", name="Ghép lộ trình")).to_have_count(0)


def test_a_teacher_keeps_part_of_a_proposal_as_a_draft_path(browser, live_server):
    page = teacher_page(browser, live_server)
    page.get_by_role("button", name="Ghép từ bài có sẵn").click()
    dialog = page.locator("#compose-dialog")
    dialog.get_by_label("Muốn luyện gì?").fill("ẩm thực và du lịch")
    dialog.get_by_label("Từ band").select_option("A2")
    dialog.get_by_label("Đến band").select_option("B1")
    dialog.get_by_label("Số bài").select_option("5")
    dialog.get_by_role("button", name="Xem đề xuất").click()

    items = dialog.locator("#compose-result .plan-item")
    expect(items).to_have_count(5)
    expect(dialog.locator("#compose-result")).to_contain_text("Chủ đề Ẩm thực")
    items.last.locator('input[name="keep"]').uncheck()
    dialog.get_by_label("Tên lộ trình").fill("Ẩm thực và du lịch (ghép)")
    dialog.get_by_role("button", name="Lưu thành lộ trình nháp").click()

    expect(page.locator(".toast").last).to_contain_text("gồm 4 bài")
    expect(page.locator("#teach-paths")).to_contain_text("Ẩm thực và du lịch (ghép)")
