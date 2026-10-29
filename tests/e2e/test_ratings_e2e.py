"""Layer 3 -- E2E for the blind double rating (D030).

An administrator creates a batch from the admin screen; a teacher opens their
sheets, listens, fills the form and moves on to the next sheet without ever
seeing whose response it is or what the machine made of it; the administrator
reads the agreement report, humans first. Test case ids (TC-BR-Exx) are listed
in `docs/test/TEST_PLAN_D030.md`.

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
    browser,
    context,
    live_server,
    login,
    sign_consent,
)

pytestmark = pytest.mark.e2e

CRITERIA = ("range", "accuracy", "fluency", "coherence", "phonology")
SCORES = {"range": "3", "accuracy": "3", "fluency": "3.5", "coherence": "3", "phonology": "3"}


def new_context(browser, live_server):
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(15_000)
    return ctx


def students_with_recordings(browser, live_server, count: int = 2) -> list[str]:
    """Students who consent to research use, each with one submitted recording."""
    names = []
    for _ in range(count):
        ctx = new_context(browser, live_server)
        try:
            page = ctx.new_page()
            name = live_server.account()
            login(page, live_server, name, "/practice")
            sign_consent(page)
            audio = (live_server.files / "full-35s.wav").read_bytes()
            r = page.request.post(
                "/api/v1/responses",
                multipart={
                    "task_id": "P3",
                    "audio": {"name": "answer.wav", "mimeType": "audio/wav", "buffer": audio},
                },
            )
            assert r.status == 202, r.text()
            names.append(name)
        finally:
            ctx.close()
    return names


def account_id_of(page, pseudonym: str) -> str:
    rows = page.request.get("/api/v1/admin/accounts").json()
    return next(a["account_id"] for a in rows if a["pseudonym"] == pseudonym)


def test_a_rater_rates_a_sheet_blind_and_moves_on_to_the_next(context, browser, live_server):
    students = students_with_recordings(browser, live_server)
    rater, other = live_server.account("teacher"), live_server.account("teacher")
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    made = admin.request.post(
        "/api/v1/admin/ratings/batches",
        data={
            "name": "Đợt E2E",
            "rater_ids": [account_id_of(admin, rater), account_id_of(admin, other)],
            "limit": 2,
        },
    )
    assert made.ok, made.text()

    ctx = new_context(browser, live_server)
    try:
        page = ctx.new_page()
        login(page, live_server, rater, "/rate")
        expect(page.locator('.nav-badge[data-badge="ratings"]')).to_contain_text("2")
        card = page.locator(".rate-batch").filter(has_text="Đợt E2E")
        expect(card).to_contain_text("0/2 bài")
        card.get_by_role("link", name=re.compile("Bắt đầu chấm")).click()
        page.wait_for_url(re.compile(r"/rate/[0-9a-f]+$"))
        expect(page.locator("#sheet-h")).to_contain_text("Bài 1/2")
        expect(page.locator("#task-prompt")).not_to_be_empty()
        expect(page.locator("#sheet-audio")).to_have_attribute(
            "src", re.compile(r"^/api/v1/rate/assignments/[0-9a-f]+/audio$")
        )
        body = page.locator("main").inner_text()
        for name in students:
            assert name not in body

        for key, value in SCORES.items():
            page.locator(f"#score-{key}").fill(value)
        page.locator("#score-overall").fill("3")
        page.locator(".chip-radio").filter(has_text="B1").click()
        page.get_by_label("Lý do, một dòng").fill("Ý rõ, ngập ngừng ở nửa sau.")
        first = urlparse(page.url).path
        page.get_by_role("button", name="Nộp phiếu").click()
        page.wait_for_url(lambda url: urlparse(url).path not in (first,))
        expect(page.locator("#sheet-h")).to_contain_text("Bài 2/2")

        page.goto(first)
        expect(page.locator("#sheet-message")).to_contain_text("Đã nộp")
        expect(page.locator("#score-overall")).to_be_disabled()
        page.goto("/rate")
        expect(page.locator(".rate-batch").filter(has_text="Đợt E2E")).to_contain_text("1/2 bài")
    finally:
        ctx.close()


def test_an_administrator_creates_a_batch_and_reads_the_report(context, browser, live_server):
    students_with_recordings(browser, live_server)
    first, second = live_server.account("teacher"), live_server.account("teacher")
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    admin.get_by_role("tab", name="Chấm mù").click()
    expect(admin.locator("#batch-eligible")).to_contain_text("Bài đủ điều kiện")
    admin.get_by_label("Tên đợt").fill("Đợt báo cáo E2E")
    admin.locator("#batch-raters label").filter(has_text=first).locator("input").check()
    admin.locator("#batch-raters label").filter(has_text=second).locator("input").check()
    admin.get_by_label("Số bài (để trống là tất cả)").fill("2")
    admin.get_by_role("button", name="Tạo đợt").click()
    row = admin.locator("#batches-body tr").filter(has_text="Đợt báo cáo E2E")
    expect(row).to_contain_text("2 bài")

    for name in (first, second):
        ctx = new_context(browser, live_server)
        try:
            page = ctx.new_page()
            login(page, live_server, name, "/rate")
            batches = page.request.get("/api/v1/rate/assignments").json()["batches"]
            mine = next(b for b in batches if b["name"] == "Đợt báo cáo E2E")
            for item in mine["items"]:
                page.request.get(f"/api/v1/rate/assignments/{item['assignment_id']}")
                r = page.request.post(
                    f"/api/v1/rate/assignments/{item['assignment_id']}",
                    data={
                        "criteria": dict.fromkeys(CRITERIA, 3),
                        "overall": 3.0 if name == first else 3.5,
                        "band": "B1",
                        "reason": "Chấm thử E2E.",
                    },
                )
                assert r.ok, r.text()
        finally:
            ctx.close()

    admin.reload()
    admin.get_by_role("tab", name="Chấm mù").click()
    row = admin.locator("#batches-body tr").filter(has_text="Đợt báo cáo E2E")
    expect(row).to_contain_text("4/4 phiếu")
    row.get_by_role("button", name="Báo cáo").click()
    dialog = admin.locator("#report-dialog")
    expect(dialog).to_be_visible()
    text = dialog.inner_text()
    assert text.index("1. Hai giám khảo với nhau") < text.index("2. Máy so với")
    expect(dialog).to_contain_text("chưa ký")
    expect(dialog.locator("table.confusion")).to_have_count(2)
