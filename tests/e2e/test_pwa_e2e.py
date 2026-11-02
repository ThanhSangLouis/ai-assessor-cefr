"""D088 in a real browser: the service worker, the offline page, a push message.

Chromium of Playwright has no push service of its own (no Google keys), so a
real subscription cannot be made here; the message is handed to the worker by
DevTools (`ServiceWorker.deliverPushMessage`) instead, which is the same event
a push service delivers. The server's half -- signing and encrypting for the
push service -- is tested in `tests/test_d088_push_unit.py`.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("playwright.sync_api")

from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    context,
    live_server,
    login,
    wait_until,
)

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def browser():
    """Chromium's new headless mode: the old one (headless shell) answers every
    notification permission with "denied", whatever the context grants."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chromium")
        yield b
        b.close()


def controlled(page) -> None:
    """Wait until the service worker controls the page (it claims open pages)."""
    page.evaluate("navigator.serviceWorker.ready.then(() => true)")
    wait_until(page, "!!navigator.serviceWorker.controller")


def test_the_worker_installs_and_an_offline_page_replaces_the_browsers_error(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/practice")
    controlled(page)
    assert page.evaluate("navigator.serviceWorker.controller.scriptURL").endswith("/sw.js")
    manifest = page.locator('link[rel="manifest"]').get_attribute("href")
    assert page.evaluate(f"fetch('{manifest}').then(r => r.json()).then(d => d.short_name)") == (
        "SpeakUp"
    )

    context.set_offline(True)
    try:
        page.goto("/my-responses")
        assert page.get_by_role("heading", name="Bạn đang mất kết nối mạng").is_visible()
    finally:
        context.set_offline(False)
    page.goto("/my-responses")  # back online: the real page, nothing cached
    assert page.title().endswith("SpeakUp") and "mất kết nối" not in page.title()


def test_a_push_message_becomes_a_notification_that_opens_the_report(context, live_server):
    context.grant_permissions(["notifications"], origin=live_server.base_url)
    page = context.new_page()
    login(page, live_server, live_server.account(), "/practice")
    controlled(page)

    cdp = context.new_cdp_session(page)
    registrations: list[str] = []
    cdp.on(
        "ServiceWorker.workerRegistrationUpdated",
        lambda e: registrations.extend(r["registrationId"] for r in e["registrations"]),
    )
    cdp.send("ServiceWorker.enable")
    page.wait_for_timeout(300)
    assert registrations, "no service worker registration reported"
    message = {
        "title": "Bài nói đã chấm xong",
        "body": "Mở để xem kết quả và nhận xét.",
        "url": "/report/r-e2e",
        "tag": "response-r-e2e",
    }
    cdp.send(
        "ServiceWorker.deliverPushMessage",
        {
            "origin": live_server.base_url,
            "registrationId": registrations[-1],
            "data": json.dumps(message, ensure_ascii=False),
        },
    )
    wait_until(
        page,
        "navigator.serviceWorker.ready.then(r => r.getNotifications())"
        ".then(n => (window.__shown = n.map(x => [x.title, x.body, x.data.url])).length > 0)",
    )
    shown = page.evaluate("window.__shown")
    assert shown == [
        [
            "Bài nói đã chấm xong",
            "Mở để xem kết quả và nhận xét.",
            f"{live_server.base_url}/report/r-e2e",
        ]
    ]


def test_a_message_cannot_send_the_learner_to_another_site(context, live_server):
    context.grant_permissions(["notifications"], origin=live_server.base_url)
    page = context.new_page()
    login(page, live_server, live_server.account(), "/practice")
    controlled(page)
    cdp = context.new_cdp_session(page)
    registrations: list[str] = []
    cdp.on(
        "ServiceWorker.workerRegistrationUpdated",
        lambda e: registrations.extend(r["registrationId"] for r in e["registrations"]),
    )
    cdp.send("ServiceWorker.enable")
    page.wait_for_timeout(300)
    cdp.send(
        "ServiceWorker.deliverPushMessage",
        {
            "origin": live_server.base_url,
            "registrationId": registrations[-1],
            "data": json.dumps({"title": "x", "url": "https://evil.example/login", "tag": "evil"}),
        },
    )
    wait_until(
        page,
        "navigator.serviceWorker.ready.then(r => r.getNotifications({tag: 'evil'}))"
        ".then(n => (window.__url = n.length && n[0].data.url) && true)",
    )
    assert page.evaluate("window.__url") == f"{live_server.base_url}/"


def test_without_server_keys_the_account_page_offers_no_switch(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/account")
    page.wait_for_load_state("networkidle")
    assert page.locator("#push-card").is_hidden()
