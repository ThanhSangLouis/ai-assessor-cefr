"""Layer 3 -- E2E for service plans and payment (D033, D034), in a real browser.

A server of its own, with `AICEFR_BILLING=on` and the sandbox gateway: the
administrator buys a plan the way a person would -- the tab, the quote, the
gateway's page, the return page, the receipt -- and a cancelled payment leaves
the plan as it was. Students are shown nothing of it.

Test case ids (TC-GD-Exx) are listed in `docs/test/TEST_PLAN_D034.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    LiveServer,
    _free_port,
    browser,
    e2e_store,
    login,
)

pytestmark = pytest.mark.e2e


def serve(root, **settings: str) -> Iterator[LiveServer]:
    """A server of its own, billing on and `settings` on top; stopped when the caller is done."""
    db = e2e_store("billing")
    port = _free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICEFR_")}
    env.update(
        AICEFR_DB=str(db),
        AICEFR_UPLOADS=str(root / "uploads"),
        AICEFR_MODEL_DIR=os.environ["AICEFR_MODEL_DIR"],
        AICEFR_MODEL_PINS=os.environ["AICEFR_MODEL_PINS"],
        AICEFR_JOB_MODE="inline",
        AICEFR_LOGIN_RATE="1000",
        AICEFR_BILLING="on",
        AICEFR_TRIAL_SEATS="40",
    )
    env.update(settings)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "aicefr.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"E2E server exited early: {proc.stderr.read().decode()[-2000:]}")
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=1) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("E2E server not ready after 60 seconds")
    files = root / "files"
    files.mkdir()
    try:
        yield LiveServer(base, db, files)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="module")
def live_server(tmp_path_factory) -> Iterator[LiveServer]:
    yield from serve(tmp_path_factory.mktemp("e2e-billing"))


@pytest.fixture
def context(browser, live_server):
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(20_000)
    yield ctx
    ctx.close()


def billing_tab(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account("admin"), "/admin")
    page.goto("/admin#billing")
    expect(page.locator("#bill-pay")).to_be_enabled()
    return page


def test_an_administrator_buys_a_plan_and_gets_a_receipt(context, live_server):
    page = billing_tab(context, live_server)
    expect(page.locator(".bill-plan-name")).to_have_text("Dùng thử")
    expect(page.locator("#billing-body .notice-warn").first).to_contain_text("Môi trường thử")
    # The plans side by side: what each step up adds.
    ladder = page.locator("table.ladder")
    expect(ladder.locator("thead")).to_contain_text("Miễn phí")
    expect(ladder.locator("thead")).to_contain_text("Chuẩn")
    expect(ladder.locator("thead")).to_contain_text("Nâng cao")
    expect(
        ladder.locator("tr", has_text="Soạn lộ trình riêng").locator(".ladder-yes")
    ).to_have_count(2)
    expect(ladder.locator("tr", has_text="Chấm mù kép").locator(".ladder-yes")).to_have_count(1)
    page.get_by_role("button", name="Chọn gói Chuẩn").click()

    page.locator("#bill-seats").fill("60")
    expect(page.locator("#bill-quote")).to_contain_text("60 sinh viên × 6 tháng")
    expect(page.locator("#bill-pay")).to_contain_text("Thanh toán 3.600.000")
    page.locator("#bill-pay").click()

    page.wait_for_url(re.compile(r"/billing/sandbox/DH\w+\?t="))
    expect(page.locator(".pay-amount")).to_contain_text("3.600.000")
    page.get_by_role("button", name="Thanh toán thành công").click()
    page.wait_for_url(re.compile(r"/billing/return/sandbox\?"))
    expect(page.get_by_role("heading", name="Thanh toán thành công")).to_be_visible()
    page.get_by_role("link", name="Xem biên nhận").click()
    page.wait_for_url(re.compile(r"/receipt$"))
    expect(page.locator(".receipt-lines tfoot")).to_contain_text("3.600.000")
    expect(page.locator(".receipt-note")).to_contain_text("không phải hoá đơn")

    page.goto("/admin#billing")
    expect(page.locator(".bill-plan-name")).to_have_text("Chuẩn")
    expect(page.locator(".ladder-col.is-current")).to_contain_text("Đang dùng")
    orders = page.locator('section[aria-labelledby="bill-orders-h"]')
    expect(orders.locator("tbody tr").first).to_contain_text("Đã thanh toán")


def test_a_cancelled_payment_leaves_the_plan_as_it_was(context, live_server):
    page = billing_tab(context, live_server)
    before = page.locator(".bill-plan-name").inner_text()
    page.locator('input[name="bill-plan"][value="advanced"]').check()
    expect(page.locator("#bill-quote")).to_contain_text("15.000")
    page.locator("#bill-pay").click()
    page.wait_for_url(re.compile(r"/billing/sandbox/"))

    page.get_by_role("button", name="Huỷ giao dịch").click()

    page.wait_for_url(re.compile(r"/billing/return/sandbox\?"))
    expect(page.get_by_role("heading", name="Đã huỷ giao dịch")).to_be_visible()
    page.get_by_role("link", name="Về trang Gói dịch vụ").click()
    expect(page.locator(".bill-plan-name")).to_have_text(before)
    orders = page.locator('section[aria-labelledby="bill-orders-h"]')
    expect(orders.locator("tbody tr").first).to_contain_text("Đã huỷ")


def test_the_tab_fits_a_phone_and_students_see_no_plan(context, live_server):
    page = billing_tab(context, live_server)
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    expect(page.locator("#bill-pay")).to_be_enabled()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390

    student = context.browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    learner = student.new_page()
    login(learner, live_server, live_server.account())
    for path in ("/practice", "/my-progress", "/account"):
        learner.goto(path)
        text = learner.locator("body").inner_text().lower()
        assert "gói dịch vụ" not in text and "thanh toán" not in text
    student.close()
