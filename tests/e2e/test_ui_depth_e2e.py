"""Layer 3 -- E2E for the look of D031: the 3D that follows the pointer, and stops when asked.

The pointer effects, the report's band podium and the font are only real in a
browser: a stylesheet test can say a rule exists, not that the scene turns, the
card settles back or Roboto is the face on the screen. Test case ids
(TC-UI-Exx) are listed in `docs/test/TEST_PLAN_D031.md`.

Server, browser and helpers come from `test_practice_e2e.py`, as in the other
E2E modules.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re
import sqlite3

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    browser,
    context,
    live_server,
    login,
    sign_consent,
    wait_until,
)

pytestmark = pytest.mark.e2e

SCENE_X = "Number(document.querySelector('[data-scene]').style.getPropertyValue('--px') || 0)"


def desktop(browser, live_server, **extra):
    ctx = browser.new_context(
        base_url=live_server.base_url,
        locale="vi-VN",
        viewport={"width": 1280, "height": 820},
        **extra,
    )
    ctx.set_default_timeout(15_000)
    return ctx


def test_the_scene_turns_toward_the_pointer_and_back(browser, live_server):
    ctx = desktop(browser, live_server)
    try:
        page = ctx.new_page()
        page.goto("/")
        hero = page.locator(".lp-hero").bounding_box()
        page.mouse.move(hero["x"] + hero["width"] * 0.95, hero["y"] + hero["height"] * 0.2, steps=6)
        wait_until(page, f"{SCENE_X} > 0.3")
        # Leaving the hero eases the scene back to its resting angle.
        page.mouse.move(hero["x"] + 10, hero["y"] + hero["height"] + 400, steps=6)
        wait_until(page, f"Math.abs({SCENE_X}) < 0.05")
    finally:
        ctx.close()


def test_a_step_card_leans_toward_the_pointer_and_settles(browser, live_server):
    ctx = desktop(browser, live_server)
    try:
        page = ctx.new_page()
        page.goto("/")
        card = page.locator(".lp-step").first
        card.scroll_into_view_if_needed()
        box = card.bounding_box()
        page.mouse.move(box["x"] + box["width"] * 0.85, box["y"] + box["height"] * 0.2, steps=4)
        expect(card).to_have_class(re.compile(r"\bis-tilting\b"))
        # The edge under the pointer comes forward: right side, so a negative turn.
        assert card.evaluate("e => e.style.getPropertyValue('--tilt-y')").startswith("-")
        page.mouse.move(5, 5)
        expect(card).not_to_have_class(re.compile(r"\bis-tilting\b"))
        assert card.evaluate("e => e.style.getPropertyValue('--tilt-y')") == ""
    finally:
        ctx.close()


def test_with_reduced_motion_nothing_follows_the_pointer(browser, live_server):
    ctx = desktop(browser, live_server, reduced_motion="reduce")
    try:
        page = ctx.new_page()
        page.goto("/")
        hero = page.locator(".lp-hero").bounding_box()
        page.mouse.move(hero["x"] + hero["width"] * 0.95, hero["y"] + hero["height"] * 0.2, steps=6)
        card = page.locator(".lp-step").first
        card.hover()
        page.wait_for_timeout(400)
        assert page.evaluate(SCENE_X) == 0
        assert "is-tilting" not in (card.get_attribute("class") or "")
    finally:
        ctx.close()


def scored(live_server, response_id: str) -> None:
    """Arrange the machine's output as the integration tests do: the fake
    recogniser's transcript is never scored."""
    from aicefr.contracts import Assessment, Band, ScoreInterval
    from aicefr.storage.repository import Repository

    report = Repository(live_server.db_path).get(response_id)
    assessment = report.assessment or Assessment(model_version="test")
    report.assessment = assessment.model_copy(
        update={
            "overall_0_6": 3.62,
            "overall_band": Band("B1"),
            "interval": ScoreInterval(
                low=3.3,
                high=3.95,
                band_set=[Band("B1"), Band("B2")],
                coverage=0.9,
                method="test",
                calibration_version="test",
            ),
        }
    )
    with sqlite3.connect(live_server.db_path) as c:
        c.execute(
            "UPDATE response SET overall_0_6=?, overall_band=?, report_json=? WHERE response_id=?",
            (3.62, "B1", report.model_dump_json(), response_id),
        )


def test_the_report_marks_the_estimated_band_among_the_three(context, live_server):
    page = context.new_page()
    login(page, live_server, live_server.account(), "/practice")
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
    response_id = r.json()["response_id"]
    scored(live_server, response_id)

    page.goto(f"/report/{response_id}")
    podium = page.locator(".band-podium")
    expect(podium).to_have_attribute("aria-hidden", "true")
    expect(podium.locator(".cube")).to_have_count(3)
    expect(podium.locator(".cube.is-band")).to_have_text("B1")
    expect(podium.locator(".cube.is-possible")).to_have_text("B2")
    expect(podium.locator(".cube.is-dim")).to_have_text("A2")
    # The band itself is written beside the blocks, for every reader.
    expect(page.locator(".score-band")).to_have_text("B1")


def test_roboto_is_the_face_on_the_screen(browser, live_server):
    ctx = desktop(browser, live_server)
    fonts: list[str] = []
    try:
        page = ctx.new_page()
        page.on("request", lambda req: fonts.append(req.url))
        page.goto("/login")
        wait_until(page, "document.fonts.status === 'loaded'")
        loaded = page.evaluate(
            "[...document.fonts].filter(f => f.family === 'Roboto' && f.status === 'loaded').length"
        )
        assert loaded >= 2  # latin and vietnamese: every Vietnamese page needs both
        family = page.evaluate("getComputedStyle(document.body).fontFamily")
        assert family.startswith("Roboto")
        woff2 = [url for url in fonts if url.endswith(".woff2")]
        assert woff2
        assert all(url.startswith(live_server.base_url + "/static/fonts/") for url in woff2)
    finally:
        ctx.close()
