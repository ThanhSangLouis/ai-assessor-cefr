"""Layer 3 -- E2E for self sign-up and the forgotten password (D065).

A visitor opens an account from the login page, keeps the pseudonym and the
recovery code shown once, signs out, forgets the password and sets a new one
with the code. Server, browser and login helpers come from
`test_practice_e2e.py`, as in the other E2E modules.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re

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

PASSWORD = "mot-cau-de-nho-123"
NEW_PASSWORD = "mot-cau-khac-456"


def test_a_visitor_signs_up_then_resets_a_forgotten_password(context, live_server):
    page = context.new_page()
    page.goto("/login")
    page.locator("#signup-link").click()
    expect(page).to_have_url(re.compile(r"/signup$"))
    # D071: the email to sign in with, the name a teacher reads, consent.
    page.locator("#email").fill("hoc.vien.e2e@example.edu.vn")
    page.locator("#full-name").fill("Nguyễn Văn An")
    page.locator("#password").fill(PASSWORD)
    page.locator("#again").fill(PASSWORD)
    page.get_by_role("button", name="Tạo tài khoản").click()
    expect(page.locator("#tb")).to_contain_text("đồng ý")  # consent is required
    page.locator("#consent").check()
    page.get_by_role("button", name="Tạo tài khoản").click()

    slip = page.locator("#recovery-slip")
    expect(slip).to_be_visible()
    pseudonym = page.locator("#slip-pseudonym").inner_text()
    code = page.locator("#slip-code").inner_text()
    assert pseudonym == "hoc.vien.e2e@example.edu.vn"  # the slip names the sign-in email
    assert re.fullmatch(r"[a-z2-9]{4}(-[a-z2-9]{4}){3}", code)

    # The way on waits until the code is kept.
    go = page.locator("#go")
    expect(go).to_have_attribute("aria-disabled", "true")
    page.locator("#kept").check()
    go.click()
    expect(page).to_have_url(re.compile(r"/practice"))

    # Forgotten: a fresh browser, the login page, the code.
    context.clear_cookies()
    page.goto("/login")
    page.locator("#forgot-link").click()
    page.locator("#pseudonym").fill(pseudonym)
    page.locator("#code").fill(code.upper().replace("-", ""))
    page.locator("#password").fill(NEW_PASSWORD)
    page.locator("#again").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Đặt mật khẩu mới").click()
    expect(page.locator("#recovery-slip")).to_be_visible()
    fresh = page.locator("#slip-code").inner_text()
    assert fresh != code

    # The new password signs in; the spent code is refused.
    context.clear_cookies()
    page.goto("/login")
    page.locator("#pseudonym").fill(pseudonym)
    page.locator("#password").fill(NEW_PASSWORD)
    page.get_by_role("button", name="Đăng nhập").click()
    expect(page).to_have_url(re.compile(r"/practice"))

    context.clear_cookies()
    page.goto("/forgot")
    page.locator("#pseudonym").fill(pseudonym)
    page.locator("#code").fill(code)
    page.locator("#password").fill("lan-thu-ba-789")
    page.locator("#again").fill("lan-thu-ba-789")
    page.get_by_role("button", name="Đặt mật khẩu mới").click()
    expect(page.locator("#tb")).to_contain_text("mã khôi phục không đúng")


def test_a_signed_in_learner_makes_a_recovery_code_on_the_account_page(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/account")
    page.get_by_role("tab", name=re.compile("Bảo mật")).click()
    expect(page.locator("#recovery-state")).to_contain_text("Chưa có mã")
    page.get_by_role("button", name="Tạo mã khôi phục mới").click()
    expect(page.locator("#recovery-slip")).to_be_visible()
    expect(page.locator("#slip-code")).to_have_text(re.compile(r"^[a-z2-9]{4}(-[a-z2-9]{4}){3}$"))
    expect(page.locator("#recovery-state")).to_contain_text("Đang có mã")
