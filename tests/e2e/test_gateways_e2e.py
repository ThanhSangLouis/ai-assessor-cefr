"""Layer 3 -- E2E for the choice of payment gateway (D035, D075), in a real browser.

A server of its own offering Stripe in test mode and the sandbox. Stripe's key
is not a real one, so no test here presses "pay" with Stripe picked -- that
round trip is covered without a network by `tests/test_gateways.py`. What a
browser shows here is the choice on the learner's runs page, a purchase
through the gateway picked, and the page for a payer who left Stripe's page.

Test case ids (TC-CT-Exx) are listed in `docs/test/TEST_PLAN_D035.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_billing_e2e import runs_page, serve  # noqa: E402
from test_practice_e2e import LiveServer, browser, login  # noqa: E402, F401

pytestmark = pytest.mark.e2e

# Shaped like a Stripe test key so the adapter accepts it; Stripe never sees it.
STRIPE_KEY = "sk_test_" + "e2e" * 8


@pytest.fixture(scope="module")
def live_server(tmp_path_factory) -> Iterator[LiveServer]:
    yield from serve(
        tmp_path_factory.mktemp("e2e-gateways"),
        AICEFR_PAYMENT_GATEWAYS="stripe,sandbox",
        AICEFR_STRIPE_SECRET_KEY=STRIPE_KEY,
    )


@pytest.fixture
def context(browser, live_server):
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(20_000)
    yield ctx
    ctx.close()


def test_the_buyer_picks_the_gateway_and_pays_through_it(context, live_server):
    page = runs_page(context, live_server)
    choice = page.locator("#gateway")
    expect(page.locator("#gateway-field")).to_be_visible()
    expect(choice.locator("option")).to_have_count(2)
    expect(choice).to_have_value("stripe")  # the first offered

    choice.select_option("sandbox")
    page.locator(".pack").first.get_by_role("button", name="Mua gói này").click()

    page.wait_for_url(re.compile(r"/billing/sandbox/DL\w+\?t="))
    page.get_by_role("button", name="Thanh toán thành công").click()
    page.wait_for_url(re.compile(r"/billing/return/sandbox\?"))
    expect(page.get_by_role("heading", name="Thanh toán thành công")).to_be_visible()


def test_coming_back_without_paying_says_nothing_was_charged(context, live_server):
    page = context.new_page()

    page.goto("/billing/return/stripe?left=1")

    expect(page.get_by_role("heading", name="Bạn đã rời trang thanh toán")).to_be_visible()
    expect(page.locator(".pay-banner")).to_contain_text("Môi trường thử của Stripe")
    expect(page.get_by_role("link", name="Về trang Lượt của tôi")).to_be_visible()


def test_the_gateway_choice_fits_a_phone(context, live_server):
    page = runs_page(context, live_server)
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    expect(page.locator("#gateway")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
