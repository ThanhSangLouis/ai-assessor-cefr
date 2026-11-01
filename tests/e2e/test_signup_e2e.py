"""Layer 3 -- E2E for self sign-up and the forgotten password (D065, D081).

A visitor opens an account from the login page and goes straight on to
practise: no recovery code is handed out any more (D081). The forgotten
password page, with email off on this server, says whom to ask. Resetting by
a code sent by email is covered by `tests/test_d079_email.py`. Server, browser
and login helpers come from `test_practice_e2e.py`, as in the other E2E modules.

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


def test_a_visitor_signs_up_and_a_forgotten_password_names_whom_to_ask(context, live_server):
    page = context.new_page()
    page.goto("/login")
    page.locator("#signup-link").click()
    expect(page).to_have_url(re.compile(r"/signup$"))
    # D071: the email to sign in with and the name a teacher reads.
    page.locator("#email").fill("hoc.vien.e2e@example.edu.vn")
    page.locator("#full-name").fill("Nguyễn Văn An")
    page.locator("#password").fill(PASSWORD)
    page.locator("#again").fill(PASSWORD)
    page.get_by_role("button", name="Tạo tài khoản").click()

    expect(page.locator("#done")).to_be_visible()
    page.locator("#go").click()
    expect(page).to_have_url(re.compile(r"/practice"))

    # Forgotten, with email off: no form, only whom to ask.
    context.clear_cookies()
    page.goto("/login")
    page.locator("#forgot-link").click()
    expect(page.locator(".auth-card")).to_contain_text("mật khẩu tạm")
    expect(page.locator("#code")).to_have_count(0)
