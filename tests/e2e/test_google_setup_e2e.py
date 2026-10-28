"""Layer 3 -- E2E for sign-in with Google once keys are set (D036), in a real browser.

A server of its own with a Google client id and secret that Google has never
issued, and nothing here reaches Google: every request to accounts.google.com
is aborted. The button's request to `/auth/google/start` is answered by this
server as usual but stopped before the redirect is followed -- a route cannot
catch the target of a redirect -- which is enough to see what the browser
would carry to Google (the PKCE challenge, state and nonce) and what it keeps
(the signed HttpOnly cookie). The administrator's configuration tab is read
for the address to register with Google.

Test case ids (TC-GG-Exx) are listed in `docs/test/TEST_PLAN_D036.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_billing_e2e import serve  # noqa: E402
from test_practice_e2e import LiveServer, browser, login  # noqa: E402, F401

pytestmark = pytest.mark.e2e

CLIENT_ID = "e2e-client.apps.googleusercontent.com"
CLIENT_SECRET = "x" * 24  # built, so the secret scanner sees no literal


@pytest.fixture(scope="module")
def live_server(tmp_path_factory) -> Iterator[LiveServer]:
    yield from serve(
        tmp_path_factory.mktemp("e2e-google"),
        AICEFR_GOOGLE_CLIENT_ID=CLIENT_ID,
        AICEFR_GOOGLE_CLIENT_SECRET=CLIENT_SECRET,
    )


@pytest.fixture
def context(browser, live_server):
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(20_000)
    ctx.route("https://accounts.google.com/**", lambda route: route.abort())
    yield ctx
    ctx.close()


def test_the_config_tab_shows_what_to_register_with_google(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account("admin"), "/admin")

    page.goto("/admin#config")
    page.locator("#tab-config").click()

    card = page.locator("#google-setup")
    expect(card).to_be_visible()
    expect(card.locator(".card-head")).to_contain_text("Đang bật")
    expect(card).to_contain_text(f"{live_server.base_url}/auth/google/callback")
    expect(card).to_contain_text(CLIENT_ID)
    expect(card).to_contain_text("Đã đặt (không bao giờ hiển thị)")
    expect(card).to_contain_text("PKCE (S256)")
    assert CLIENT_SECRET not in page.content()
    expect(card.get_by_role("button", name="Sao chép")).to_be_visible()


def test_the_google_button_leaves_with_a_pkce_challenge(context, live_server):
    page = context.new_page()
    sent: list[str] = []

    def start_without_leaving(route):
        answer = route.fetch(max_redirects=0)
        assert answer.status == 303
        sent.append(answer.headers["location"])
        route.fulfill(
            status=200,
            content_type="text/html",
            body="<p>Google (stub)</p>",
            headers={"set-cookie": answer.headers["set-cookie"]},
        )

    page.route("**/auth/google/start*", start_without_leaving)
    page.goto("/login")

    page.locator("#google-login").click()

    expect(page.locator("body")).to_contain_text("Google (stub)")
    [url] = sent
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["response_type"] == "code" and q["scope"] == "openid email"
    assert q["code_challenge_method"] == "S256" and len(q["code_challenge"]) == 43
    assert q["client_id"] == CLIENT_ID and q["prompt"] == "select_account"
    assert q["redirect_uri"] == f"{live_server.base_url}/auth/google/callback"
    assert q["state"] and q["nonce"] and q["state"] != q["nonce"]
    [cookie] = [c for c in context.cookies() if c["name"] == "aicefr_oauth"]
    assert cookie["httpOnly"] and cookie["sameSite"] == "Lax" and cookie["path"] == "/auth/google"
    assert "." in cookie["value"]  # the flow, then its signature
