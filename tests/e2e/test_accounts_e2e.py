"""Layer 3 -- E2E for accounts, sidebar counts, preparation and the band page (D028).

Each test walks a path as its user would: an administrator hands out accounts
on printed slips, a new user's first login asks for a password of their own, a
teacher's decision shows up as a count in the student's sidebar, a student
prepares for thirty seconds before answering. Test case ids (TC-PC-Exx) are
listed in `docs/test/TEST_PLAN_D028.md`.

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
    PASSWORD,
    browser,
    context,
    live_server,
    login,
    sign_consent,
    wait_until,
)

pytestmark = pytest.mark.e2e

# Built from the fixture password so the secret scanner sees no new literal.
NEW_PASSWORD = PASSWORD + "-moi"
SLIP_CODE = re.compile(r"^[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}$")


def fresh_context(browser, live_server):
    """A second person at another computer: separate cookies."""
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.grant_permissions(["microphone"], origin=live_server.base_url)
    ctx.set_default_timeout(15_000)
    return ctx


def test_an_administrator_hands_out_an_account_and_its_first_login_sets_a_password(
    context, browser, live_server
):
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    expect(admin.get_by_role("tab", name="Tài khoản")).to_have_attribute("aria-selected", "true")
    admin.get_by_label("Vai trò", exact=True).select_option("teacher")
    admin.get_by_label("Cách tạo").select_option("one")
    admin.get_by_label("Bút danh", exact=True).fill("E2E-GV-NEW")
    admin.get_by_role("button", name="Tạo tài khoản").click()

    slip = admin.locator(".slip").filter(has_text="E2E-GV-NEW")
    expect(slip).to_be_visible()
    temporary = slip.locator(".slip-code").nth(1).inner_text().strip()
    assert SLIP_CODE.match(temporary), temporary
    row = admin.locator("#accounts-body tr").filter(has_text="E2E-GV-NEW")
    expect(row).to_contain_text("Chờ đổi mật khẩu tạm")
    # Hiding the slips asks first: the passwords cannot be shown again.
    admin.once("dialog", lambda d: d.accept())
    admin.get_by_role("button", name="Ẩn phiếu").click()
    expect(admin.locator("#slips")).to_be_hidden()

    ctx = fresh_context(browser, live_server)
    try:
        page = ctx.new_page()
        page.goto("/login?next=/review/stats")
        page.get_by_label("Mã bút danh").fill("E2E-GV-NEW")
        page.get_by_label("Mật khẩu").fill(temporary)
        page.get_by_role("button", name="Đăng nhập").click()
        # Wherever it was heading, a temporary password goes to the account page.
        page.wait_for_url(lambda url: urlparse(url).path == "/account")
        expect(page.locator("#first-time")).to_be_visible()
        page.goto("/review")
        page.wait_for_url(lambda url: urlparse(url).path == "/account")

        page.get_by_label("Mật khẩu hiện tại").fill(temporary)
        page.get_by_label("Mật khẩu mới", exact=True).fill(NEW_PASSWORD)
        expect(page.locator('#pw-rules [data-rule="length"]')).to_have_class("met")
        page.get_by_label("Nhập lại mật khẩu mới").fill(NEW_PASSWORD)
        page.get_by_role("button", name="Lưu mật khẩu mới").click()
        page.wait_for_url(lambda url: urlparse(url).path == "/review")
    finally:
        ctx.close()

    admin.reload()
    row = admin.locator("#accounts-body tr").filter(has_text="E2E-GV-NEW")
    expect(row).not_to_contain_text("Chờ đổi mật khẩu tạm")


def test_a_teacher_decision_is_a_count_until_the_student_opens_their_list(
    context, browser, live_server
):
    student = context.new_page()
    login(student, live_server, live_server.account(), "/")
    sign_consent(student)
    student.goto("/")
    expect(student.locator(".task")).not_to_have_count(0)
    student.set_input_files("#audio", str(live_server.files / "full-35s.wav"))
    student.get_by_role("button", name="Nộp bài và chấm").click()
    student.wait_for_url(re.compile(r"/report/[0-9a-f]+$"), timeout=30_000)
    response_id = urlparse(student.url).path.rsplit("/", 1)[1]

    ctx = fresh_context(browser, live_server)
    try:
        teacher = ctx.new_page()
        login(teacher, live_server, live_server.account("teacher"), "/review")
        expect(teacher.locator('.nav-badge[data-badge="queue"]')).to_be_visible()
        r = teacher.request.post(
            f"/api/v1/review/{response_id}", data={"reason": "Đã nghe lại toàn bài."}
        )
        assert r.ok, r.text()
    finally:
        ctx.close()

    student.goto("/practice")
    badge = student.locator('.nav-badge[data-badge="results"]')
    expect(badge).to_be_visible()
    expect(badge).to_contain_text("1")
    student.goto("/my-responses")
    expect(student.locator(".new-chip")).to_have_count(1)
    expect(badge).to_be_hidden()


def test_thirty_seconds_of_preparation_then_the_answer_is_recorded(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/")
    sign_consent(page)
    page.goto("/")
    prep = page.locator("#prep")
    expect(prep).to_be_visible()
    expect(page.locator("#prep-left")).to_have_text("30")

    page.get_by_role("button", name="Bắt đầu chuẩn bị").click()
    wait_until(page, "Number(document.getElementById('prep-left').textContent) < 30")
    expect(prep).to_have_attribute("data-state", "running")
    page.get_by_role("button", name="Huỷ").click()
    expect(page.locator("#prep-left")).to_have_text("30")

    page.get_by_role("button", name="Bắt đầu chuẩn bị").click()
    page.get_by_role("button", name="Nói ngay").click()
    expect(page.locator("#rec")).to_have_attribute("data-state", "recording")
    expect(prep).to_have_attribute("data-state", "ready")
    page.wait_for_timeout(1200)
    page.get_by_role("button", name="Dừng ghi âm").click()
    expect(page.locator("#rec")).to_have_attribute("data-state", "review")


def test_the_band_page_says_what_the_machine_does_not_measure(context, live_server):
    page = context.new_page()
    page.goto("/bands")
    expect(page.get_by_role("heading", name="Band A2, B1, B2 nghĩa là gì")).to_be_visible()
    expect(page.locator('.aspect-card[data-provenance="not_measured"]')).to_have_count(2)
    expect(page.locator(".band-ladder li")).to_have_count(3)
    # Reached from every page, guests included.
    expect(page.locator(".site-footer a[href='/bands']")).to_be_visible()
