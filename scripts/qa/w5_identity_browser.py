"""Local Playwright/API journey for the SCRUM-66 identity handoff."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import secrets
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def _json_post(request, url: str, payload: dict, base_url: str):
    return request.post(
        url,
        data=json.dumps(payload),
        headers={
            "Content-Type": "application/json",
            "Origin": base_url.rstrip("/"),
        },
    )


def run(base_url: str, admin_id: str, admin_password: str) -> dict[str, object]:
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or parts.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("browser QA is restricted to a local loopback server")
    base_url = base_url.rstrip("/")
    actor_id = f"fixture-scrum66-{secrets.token_hex(5)}"
    evidence: dict[str, object] = {
        "base_url": base_url,
        "journey": [],
        "external_requests_blocked": 0,
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        admin = browser.new_context()
        admin_page = admin.new_page()
        admin.route(
            "**/*",
            lambda route: (
                route.continue_()
                if urlsplit(route.request.url).hostname in {"localhost", "127.0.0.1"}
                else route.abort()
            ),
        )
        admin_page.goto(base_url + "/login", wait_until="domcontentloaded")
        admin_page.get_by_label("Tài khoản").fill(admin_id)
        admin_page.get_by_label("Mật khẩu").fill(admin_password)
        admin_page.get_by_role("button", name="Đăng nhập").click()
        admin_page.wait_for_load_state("domcontentloaded")
        assert urlsplit(admin_page.url).hostname in {"localhost", "127.0.0.1"}
        evidence["journey"].append("existing admin signed in through /login")

        created = _json_post(
            admin.request,
            base_url + "/api/v1/admin/accounts",
            {"accounts": [{"actor_id": actor_id, "role": "student", "goal": 3}]},
            base_url,
        )
        assert created.status == 201, created.status
        temporary_password = created.json()["accounts"][0]["temporary_password"]
        assert isinstance(temporary_password, str) and len(temporary_password) >= 8
        evidence["journey"].append("admin created one temporary-password account")

        student = browser.new_context()
        page = student.new_page()
        page.route(
            "**/*",
            lambda route: (
                route.continue_()
                if urlsplit(route.request.url).hostname in {"localhost", "127.0.0.1"}
                else route.abort()
            ),
        )
        password_page_statuses: list[int] = []
        page.on(
            "response",
            lambda response: (
                password_page_statuses.append(response.status)
                if response.url.split("?", 1)[0] == base_url + "/password-change"
                else None
            ),
        )
        page.goto(base_url + "/login", wait_until="domcontentloaded")
        page.get_by_label("Tài khoản").fill(actor_id)
        page.get_by_label("Mật khẩu").fill(temporary_password)
        page.get_by_role("button", name="Đăng nhập").click()
        page.wait_for_load_state("domcontentloaded")
        assert page.url.endswith("/password-change"), page.url
        assert password_page_statuses and password_page_statuses[-1] == 200
        assert page.locator('input[name="current_password"]').count() == 1
        assert page.locator('input[name="new_password"]').count() == 1
        assert page.locator('input[name="confirm_password"]').count() == 1
        safe_state = student.request.get(base_url + "/api/v1/me")
        assert safe_state.status == 200
        assert safe_state.json()["profile"]["temporary_password_required"] is True
        denied = student.request.get(base_url + "/api/v1/me/activity")
        assert denied.status == 403 and denied.json()["error"] == "PASSWORD_CHANGE_REQUIRED"
        evidence["journey"].append(
            "temporary account was gated and redirected to password guidance"
        )

        changed = _json_post(
            student.request,
            base_url + "/api/v1/me/password",
            {
                "current_password": temporary_password,
                "new_password": secrets.token_urlsafe(16),
            },
            base_url,
        )
        assert changed.status == 200, changed.status
        me = student.request.get(base_url + "/api/v1/me")
        assert me.status == 200
        assert me.json()["profile"]["actor_id"] == actor_id
        evidence["journey"].append("password rotated through same-origin API and access resumed")

        csrf = student.request.post(
            base_url + "/api/v1/me/consent",
            data=json.dumps({"version": "browser-v1", "research_allowed": False}),
            headers={"Content-Type": "application/json", "Origin": "https://evil.invalid"},
        )
        assert csrf.status == 403
        evidence["journey"].append("cross-origin cookie mutation was denied")
        student.close()
        admin.close()
        browser.close()
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-id", default=os.environ.get("AICEFR_QA_ADMIN_ID"))
    args = parser.parse_args()
    admin_id = args.admin_id or input("Fixture admin ID: ").strip()
    admin_password = getpass.getpass("Fixture admin password: ")
    result = run(args.base_url, admin_id, admin_password)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
