"""Layer 3 -- E2E for buying a pack of runs (D053, D075), in a real browser.

A server of its own with payments and the metered channel on, and the sandbox
gateway: a learner buys runs the way a person would -- the "Lượt của tôi"
page, the gateway's page, the return page, the receipt -- and a cancelled
payment credits nothing. D075 removed the institution's plans this layer used
to buy.

Test case ids (TC-TL-Exx) are listed in `docs/test/TEST_PLAN_D075.md`.

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
    """A server of its own, payments and runs on, `settings` on top; stopped when done."""
    db = e2e_store("billing")
    port = _free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICEFR_")}
    env.update(
        AICEFR_DB=str(db),
        AICEFR_UPLOADS=str(root / "uploads"),
        AICEFR_JOB_MODE="inline",
        # The synthetic scoring artifacts tests/conftest.py points at (W7-S01).
        AICEFR_MODEL_DIR=os.environ["AICEFR_MODEL_DIR"],
        AICEFR_MODEL_PINS=os.environ["AICEFR_MODEL_PINS"],
        AICEFR_LOGIN_RATE="1000",
        AICEFR_BILLING="on",
        AICEFR_METERING="on",
        AICEFR_CREDIT_PACKS="10:49000,30:129000",
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


def runs_page(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account("student"), "/credits")
    expect(page.locator("#packs-card")).to_be_visible()
    return page


def test_a_learner_buys_a_pack_and_gets_a_receipt(context, live_server):
    page = runs_page(context, live_server)
    expect(page.locator("#packs-note")).to_contain_text("Môi trường thử")
    expect(page.locator(".pack")).to_have_count(2)

    page.locator(".pack", has_text="49.000").get_by_role("button", name="Mua gói này").click()

    page.wait_for_url(re.compile(r"/billing/sandbox/DL\w+\?t="))
    expect(page.locator(".pay-amount")).to_contain_text("49.000")
    page.get_by_role("button", name="Thanh toán thành công").click()
    page.wait_for_url(re.compile(r"/billing/return/sandbox\?"))
    expect(page.get_by_role("heading", name="Thanh toán thành công")).to_be_visible()
    expect(page.locator(".pay-lede")).to_contain_text("10 lượt")
    page.get_by_role("link", name="Xem biên nhận").click()
    page.wait_for_url(re.compile(r"/receipt$"))
    expect(page.locator(".receipt-lines tfoot")).to_contain_text("49.000")
    expect(page.locator(".receipt-note")).to_contain_text("không phải hoá đơn")
    page.get_by_role("link", name="← Lượt của tôi").click()
    expect(page.locator("#orders")).to_contain_text("Đã thanh toán")


def test_a_cancelled_payment_credits_nothing(context, live_server):
    page = runs_page(context, live_server)
    page.locator(".pack", has_text="129.000").get_by_role("button", name="Mua gói này").click()
    page.wait_for_url(re.compile(r"/billing/sandbox/"))

    page.get_by_role("button", name="Huỷ giao dịch").click()

    page.wait_for_url(re.compile(r"/billing/return/sandbox\?"))
    expect(page.get_by_role("heading", name="Đã huỷ giao dịch")).to_be_visible()
    expect(page.locator(".pay-card")).to_contain_text("Ví lượt không thay đổi")


def test_the_runs_page_fits_a_phone(context, live_server):
    page = runs_page(context, live_server)
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    expect(page.locator(".pack").first).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
