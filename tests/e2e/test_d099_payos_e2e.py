"""Layer 3 -- E2E: a run pack paid through payOS, in a real browser (D099).

payOS is a fake HTTP server on this machine (`AICEFR_PAYOS_API_URL`): it opens
a payment link, shows a page with a "transferred" button, sends the browser
back the way payOS does and answers the read-back. The application under test
is the real one, with real money switched on. No request reaches payOS.

Test case ids (TC-PG-Exx) are listed in `docs/test/TEST_PLAN_D099.md`.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_billing_e2e import serve  # noqa: E402
from test_practice_e2e import LiveServer, browser, login  # noqa: E402, F401

pytestmark = pytest.mark.e2e


class FakePayos(BaseHTTPRequestHandler):
    """payOS's API and its payment page, as far as SpeakUp uses them, on 127.0.0.1.

    POST /v2/payment-requests opens a link; GET /v2/payment-requests/{id} reads
    it back; /web/{id} is the page where the payer "transfers".
    """

    links: dict[str, dict] = {}

    def log_message(self, *args) -> None:  # quiet
        pass

    def _send(self, status: int, body: bytes, kind: str = "application/json", **headers) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, data: dict) -> None:
        self._send(200, json.dumps({"code": "00", "desc": "success", "data": data}).encode())

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        sent = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/v2/payment-requests":
            assert self.headers["x-client-id"] == "client-e2e"
            link_id = f"{len(self.links) + 1:032x}"
            self.links[link_id] = {
                "id": link_id, "orderCode": sent["orderCode"], "amount": sent["amount"],
                "amountPaid": 0, "status": "PENDING", "returnUrl": sent["returnUrl"],
            }  # fmt: skip
            base = f"http://127.0.0.1:{self.server.server_port}"
            return self._ok({"checkoutUrl": f"{base}/web/{link_id}", "paymentLinkId": link_id})
        if self.path.startswith("/web/") and self.path.endswith("/pay"):
            link = self.links[self.path.split("/")[2]]
            link.update(status="PAID", amountPaid=link["amount"])
            query = {"code": "00", "id": link["id"], "cancel": "false", "status": "PAID",
                     "orderCode": link["orderCode"]}  # fmt: skip
            return self._send(303, b"", Location=f"{link['returnUrl']}?{urlencode(query)}")
        return self._send(404, b"{}")

    def do_GET(self) -> None:
        if self.path.startswith("/v2/payment-requests/"):
            link = self.links.get(self.path.rsplit("/", 1)[1])
            return self._ok(link) if link else self._send(200, b'{"code":"101"}')
        if self.path.startswith("/web/"):
            link = self.links[self.path.split("/")[2]]
            page = (
                f"<!doctype html><meta charset=utf-8><title>payOS</title>"
                f"<h1>Quét mã VietQR</h1><p class=amount>{link['amount']}</p>"
                f"<form method=post action=/web/{link['id']}/pay>"
                f"<button>Đã chuyển khoản</button></form>"
            )
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        return self._send(404, b"{}")


@pytest.fixture(scope="module")
def payos_server(tmp_path_factory) -> Iterator[LiveServer]:
    fake = ThreadingHTTPServer(("127.0.0.1", 0), FakePayos)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    try:
        yield from serve(
            tmp_path_factory.mktemp("e2e-payos"),
            AICEFR_PAYMENT_GATEWAYS="payos",
            AICEFR_PAYMENTS_LIVE="on",
            AICEFR_PAYOS_CLIENT_ID="client-e2e",
            AICEFR_PAYOS_API_KEY="api-key-e2e",
            AICEFR_PAYOS_CHECKSUM_KEY="checksum-e2e",
            AICEFR_PAYOS_API_URL=f"http://127.0.0.1:{fake.server_port}",
        )
    finally:
        fake.shutdown()


def test_a_learner_pays_through_payos_and_gets_a_receipt(browser, payos_server):  # noqa: F811
    """TC-PG-E01: buy -> payOS's page -> the success page -> the receipt -> the runs."""
    ctx = browser.new_context(
        base_url=payos_server.base_url, locale="vi-VN", service_workers="block"
    )
    ctx.set_default_timeout(20_000)
    page = ctx.new_page()
    login(page, payos_server, payos_server.account("student"), "/credits")
    expect(page.locator("#packs-note")).to_have_text("Không hết hạn")
    expect(page.locator(".pack-terms a")).to_have_attribute("href", "/payment-terms")

    page.locator(".pack", has_text="49.000").get_by_role("button", name="Mua gói này").click()

    page.wait_for_url(re.compile(r"/web/[0-9a-f]{32}$"))
    expect(page.locator(".amount")).to_have_text("49000")
    page.get_by_role("button", name="Đã chuyển khoản").click()
    page.wait_for_url(re.compile(r"/billing/return/payos\?"))
    expect(page.get_by_role("heading", name="Thanh toán thành công")).to_be_visible()
    expect(page.locator(".pay-lede")).to_contain_text("10 lượt")
    page.get_by_role("link", name="Xem biên nhận").click()
    page.wait_for_url(re.compile(r"/receipt$"))
    expect(page.locator(".receipt-lines tfoot")).to_contain_text("49.000")
    page.locator(".receipt-tools").get_by_role("link", name="Lượt của tôi").click()
    expect(page.locator("#orders")).to_contain_text("Đã thanh toán")
    expect(page.locator(".wallet-split")).to_contain_text("10")
    ctx.close()
