"""Chromium QA for the local SCRUM-67 billing and data-control APIs.

Use only with a disposable clean-wheel server bound to loopback. The script
performs a sandbox purchase and creates one verified backup/restore snapshot.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Route, sync_playwright


def _allow_loopback(route: Route, hostname: str, counter: list[int]) -> None:
    if urlsplit(route.request.url).hostname in {hostname, "localhost", "127.0.0.1"}:
        route.continue_()
    else:
        counter[0] += 1
        route.abort()


def _sign_in(context: BrowserContext, base_url: str, hostname: str, actor_id: str, password: str):
    page = context.new_page()
    outbound = [0]
    login_statuses: list[int] = []
    page_errors: list[str] = []
    console_errors: list[str] = []
    page.route("**/*", lambda route: _allow_loopback(route, hostname, outbound))
    page.on(
        "response",
        lambda response: (
            login_statuses.append(response.status)
            if urlsplit(response.url).path == "/login"
            else None
        ),
    )
    page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
    page.on(
        "console",
        lambda message: console_errors.append(message.type) if message.type == "error" else None,
    )
    page.goto(base_url + "/login", wait_until="domcontentloaded")
    page.get_by_label("Tài khoản").fill(actor_id)
    page.get_by_label("Mật khẩu").fill(password)
    page.get_by_role("button", name="Đăng nhập").click()
    page.wait_for_load_state("domcontentloaded")
    if urlsplit(page.url).hostname not in {hostname, "localhost", "127.0.0.1"}:
        raise AssertionError("login navigated away from the configured loopback server")
    if not login_statuses or 200 not in login_statuses:
        raise AssertionError("login page did not load successfully")
    if page_errors:
        raise AssertionError("browser page reported a JavaScript exception")
    if console_errors:
        raise AssertionError("browser page reported a console error")
    return page, outbound, login_statuses, page_errors, console_errors


def _expect(response, statuses: set[int], label: str):
    if response.status not in statuses:
        raise AssertionError(f"{label}: unexpected HTTP {response.status}")
    return (
        response.json()
        if response.headers.get("content-type", "").startswith("application/json")
        else {}
    )


def run(
    base_url: str,
    data_dir: Path,
    admin_id: str,
    admin_password: str,
    student_id: str,
    student_password: str,
) -> dict[str, object]:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or parts.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("browser QA is restricted to a local loopback server")
    if not data_dir.is_dir() or not (data_dir / "billing-hmac.key").is_file():
        raise ValueError("data directory must belong to the initialized disposable server")
    base_url = base_url.rstrip("/")
    evidence: dict[str, object] = {
        "base_url": base_url,
        "journey": [],
        "external_requests_blocked": 0,
    }
    from aicefr.billing.gateways import GatewayRegistry

    # Empty config creates only the local signed sandbox callback adapter.
    gateways = GatewayRegistry({}, data_dir)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin = browser.new_context()
        (
            admin_page,
            admin_outbound,
            admin_statuses,
            admin_page_errors,
            admin_console_errors,
        ) = _sign_in(admin, base_url, parts.hostname, admin_id, admin_password)
        headers = {"Origin": base_url}

        overview = _expect(
            admin.request.get(base_url + "/api/v1/admin/billing"), {200}, "billing overview"
        )
        if overview.get("overview", {}).get("sandbox") is not True:
            raise AssertionError("billing overview did not identify sandbox mode")
        quote = _expect(
            admin.request.post(
                base_url + "/api/v1/admin/billing/quotes",
                data=json.dumps(
                    {"plan_code": "STANDARD", "months": 1, "idempotency_key": secrets.token_hex(12)}
                ),
                headers={**headers, "Content-Type": "application/json"},
            ),
            {201},
            "sandbox quote",
        )
        order = _expect(
            admin.request.post(
                base_url + "/api/v1/admin/billing/orders",
                data=json.dumps(
                    {
                        "quote_id": quote["quote_id"],
                        "gateway": "sandbox",
                        "idempotency_key": secrets.token_hex(12),
                    }
                ),
                headers={**headers, "Content-Type": "application/json"},
            ),
            {201},
            "sandbox order",
        )
        event = {
            "event_id": "qa-" + secrets.token_hex(12),
            "order_id": order["order_id"],
            "checkout_id": order.get("checkout_ref"),
            "amount": order["amount_minor"],
            "currency": order["currency"],
            "status": "paid",
        }
        raw, signature = gateways.sign_sandbox_event(event)
        callback_headers = {"X-Sandbox-Signature": signature["X-Sandbox-Signature"]}
        settled = _expect(
            admin.request.post(
                base_url + "/api/v1/billing/webhooks/sandbox",
                data=raw,
                headers={**headers, **callback_headers, "Content-Type": "application/json"},
            ),
            {200},
            "signed sandbox settlement",
        )
        replay = _expect(
            admin.request.post(
                base_url + "/api/v1/billing/webhooks/sandbox",
                data=raw,
                headers={**headers, **callback_headers, "Content-Type": "application/json"},
            ),
            {200},
            "duplicate signed sandbox settlement",
        )
        receipt = _expect(
            admin.request.get(
                base_url + f"/api/v1/admin/billing/orders/{order['order_id']}/receipt"
            ),
            {200},
            "receipt",
        )
        if settled.get("state") != "PAID" or replay.get("state") != "PAID":
            raise AssertionError("signed sandbox callback did not settle idempotently")
        if receipt.get("order_id") != order["order_id"]:
            raise AssertionError("receipt was not linked to the sandbox order")
        evidence["journey"].append(
            "admin quoted, ordered, signed-settled, replayed and fetched receipt"
        )

        retention = _expect(
            admin.request.get(base_url + "/api/v1/admin/data/retention?days=180"),
            {200},
            "retention preview",
        )
        if retention.get("dry_run") is not True:
            raise AssertionError("retention GET must remain preview-only")
        backup = _expect(
            admin.request.post(
                base_url + "/api/v1/admin/data/backups",
                data="{}",
                headers={**headers, "Content-Type": "application/json"},
            ),
            {201},
            "data backup",
        )
        restored = _expect(
            admin.request.post(
                base_url + "/api/v1/admin/data/restore",
                data=json.dumps({"backup_id": backup["backup_id"]}),
                headers={**headers, "Content-Type": "application/json"},
            ),
            {201},
            "fresh-directory restore",
        )
        if restored.get("verified") is not True:
            raise AssertionError("restore did not report verified")
        preview = _expect(
            admin.request.post(
                base_url + "/api/v1/admin/data/erasure/preview",
                data=json.dumps({"actor_id": student_id}),
                headers={**headers, "Content-Type": "application/json"},
            ),
            {200},
            "admin erasure preview",
        )
        if not isinstance(preview.get("fingerprint"), str):
            raise AssertionError("admin erasure preview omitted its fingerprint")
        evidence["journey"].append(
            "admin exercised retention preview, backup, fresh restore and erasure preview"
        )

        student = browser.new_context()
        (
            student_page,
            student_outbound,
            student_statuses,
            student_page_errors,
            student_console_errors,
        ) = _sign_in(student, base_url, parts.hostname, student_id, student_password)
        _expect(
            student.request.get(base_url + "/api/v1/admin/billing"), {403}, "student billing denial"
        )
        _expect(
            student.request.post(
                base_url + "/api/v1/admin/data/backups",
                data="{}",
                headers={**headers, "Content-Type": "application/json"},
            ),
            {403},
            "student backup denial",
        )
        _expect(
            admin.request.post(
                base_url + "/api/v1/admin/data/backups",
                data="{}",
                headers={
                    "Origin": "https://invalid.example",
                    "Content-Type": "application/json",
                },
            ),
            {403},
            "cross-origin admin mutation denial",
        )
        own_export = _expect(
            student.request.get(base_url + "/api/v1/me/export"), {200}, "student own export"
        )
        if own_export.get("actor_id") != student_id:
            raise AssertionError("student personal export returned a different actor")
        evidence["journey"].append("student and cross-origin request were denied admin mutations")
        evidence["login_statuses"] = {"admin": admin_statuses, "student": student_statuses}
        evidence["page_errors"] = admin_page_errors + student_page_errors
        evidence["console_error_count"] = len(admin_console_errors) + len(student_console_errors)
        evidence["external_requests_blocked"] = admin_outbound[0] + student_outbound[0]
        student_page.close()
        student.close()
        admin_page.close()
        admin.close()
        browser.close()
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--admin-id", default=os.environ.get("AICEFR_QA_ADMIN_ID"))
    parser.add_argument("--student-id", default=os.environ.get("AICEFR_QA_STUDENT_ID"))
    args = parser.parse_args()
    admin_id = args.admin_id or input("Fixture admin ID: ").strip()
    admin_password = getpass.getpass("Fixture admin password: ")
    student_id = args.student_id or input("Fixture student ID: ").strip()
    student_password = getpass.getpass("Fixture student password: ")
    result = run(
        args.base_url,
        args.data_dir.expanduser().absolute(),
        admin_id,
        admin_password,
        student_id,
        student_password,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
