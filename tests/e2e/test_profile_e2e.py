"""Layer 3 -- E2E for the profile, sessions and account administration (D029).

A learner picks an avatar and a daily goal and the path page follows; a
session on another device is ended from the account page; an administrator
opens an account and changes its role. Test case ids (TC-PF-Exx) are listed in
`docs/test/TEST_PLAN_D029.md`. Sign-in with Google is covered at layer 2 with a
stand-in for Google's token endpoint: a browser test would need Google itself.

Server, browser and login helpers come from `test_practice_e2e.py`, as in the
other E2E modules (its docstring says why there is no conftest.py here).

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    browser,
    context,
    live_server,
    login,
)

pytestmark = pytest.mark.e2e


def fresh_context(browser, live_server):
    """A second device: separate cookies."""
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(15_000)
    return ctx


def test_a_learner_picks_an_avatar_and_a_daily_goal_and_the_path_follows(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/account")
    page.get_by_label("Biểu tượng chiếc lá").check()
    page.get_by_label("Màu xanh mực").check()
    page.get_by_role("button", name="Lưu ảnh đại diện").click()
    small = page.locator(".account-button .avatar")
    expect(small).to_have_class(re.compile(r"avatar-education"))
    expect(small.locator("use")).to_have_attribute("href", re.compile(r"#i-leaf$"))

    # D068: the goal is picked on the practice page's Today card.
    page.goto("/practice")
    page.locator("#goal-select").select_option("300")
    expect(page.locator(".toast").last).to_contain_text("5 phút")
    expect(page.locator(".today-card")).to_contain_text("/300")
    page.reload()
    expect(page.locator(".today-card")).to_contain_text("/300")


def test_a_session_on_another_device_is_ended_from_the_account_page(context, browser, live_server):
    pseudonym = live_server.account()
    here = context.new_page()
    login(here, live_server, pseudonym, "/account")
    ctx = fresh_context(browser, live_server)
    try:
        there = ctx.new_page()
        login(there, live_server, pseudonym, "/practice")
        here.goto("/account#security")
        rows = here.locator("#session-list .session")
        expect(rows).to_have_count(2)
        rows.filter(has_not=here.locator(".badge")).get_by_role("button").click()
        expect(rows).to_have_count(1)
        there.goto("/my-responses")
        there.wait_for_url(lambda url: urlparse(url).path == "/login")
    finally:
        ctx.close()
    here.goto("/account#activity")
    expect(here.locator("#activity-list")).to_contain_text("Đăng xuất một phiên")


def test_an_administrator_opens_an_account_and_changes_its_role(context, live_server):
    target = live_server.account()
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    admin.get_by_label("Tìm bút danh").fill(target)
    admin.get_by_role("button", name=f"Xem chi tiết {target}").click()
    dialog = admin.locator("#account-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("heading", name=target)).to_be_visible()
    dialog.get_by_label("Vai trò").select_option("teacher")
    admin.once("dialog", lambda d: d.accept())
    dialog.get_by_role("button", name="Đổi vai trò").click()
    expect(dialog).to_contain_text("Giảng viên")
    expect(dialog.locator(".activity-list")).to_contain_text("Đổi vai trò")
