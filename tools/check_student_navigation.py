"""Check shared navigation and locked rewards with read-only learning fixtures."""

import copy
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path("/tmp/navigation-review")
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    c = b.new_context(base_url="http://localhost:8000", viewport={"width": 1440, "height": 900})
    assert c.request.post(
        "/api/v1/auth/login",
        data={"identifier": "sv-001@demo.speakup.fit", "password": "matkhau123"},
    ).ok
    page = c.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    original = c.request.get("/api/v1/learn").json()
    bands = c.request.get("/api/v1/learn/bands").json()
    fixture = copy.deepcopy(original)
    t = original["path"]["units"][0]["lessons"][0]
    fixture["path"]["units"] = [
        {
            "unit_id": band,
            "band": band,
            "title": band,
            "lessons": [
                {
                    **t,
                    "lesson_id": f"{band}-{i}",
                    "band": band,
                    "status": "new" if i == 0 else "locked",
                }
                for i in range(5)
            ],
        }
        for band in ["A1", "A2", "B1", "B2", "C1", "C2"]
    ]
    bands["plan"] = {
        "goal": {"band_from": "A1", "band_to": "C2"},
        "units": fixture["path"]["units"],
        "lessons_total": 30,
        "lessons_completed": 0,
    }
    page.route(re.compile(r"/api/v1/learn(?:\?.*)?$"), lambda r: r.fulfill(json=fixture))
    page.route("**/api/v1/learn/bands", lambda r: r.fulfill(json=bands))
    results = []
    for mode in ["light", "dark"]:
        page.goto("/practice")
        page.evaluate(
            """mode => {localStorage.setItem('aicefr-theme',mode);
              document.documentElement.dataset.theme=mode}""",
            mode,
        )
        for width in [320, 390, 700, 768, 900, 1024, 1440, 1920]:
            page.set_viewport_size({"width": width, "height": 900})
            styles = []
            for route in ["/practice", "/my-progress", "/account", "/"]:
                page.goto(route)
                page.wait_for_timeout(250)
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                    mode,
                    width,
                    route,
                    "overflow",
                )
                styles.append(
                    page.locator(".app-sidebar .site-nav a").first.evaluate(
                        """e=>{const s=getComputedStyle(e);
                        return [s.height,s.fontSize,s.padding,s.gap]}"""
                    )
                )
                if width <= 900:
                    assert page.locator(".app-tabbar").is_visible()
                    assert page.locator('.app-tabbar [aria-current="page"]').count() == 1, (
                        route,
                        "active",
                    )
                    page.locator("#drawer-toggle").click()
                    assert page.locator("#drawer-toggle").get_attribute("aria-expanded") == "true"
                    page.keyboard.press("Escape")
                if route == "/practice":
                    page.wait_for_selector(".rm-victory .rm-coin")
                    assert page.locator(".rm-victory").count() == 6
                    assert page.locator(".rm-adventure-finish").count() == 0
                    assert page.locator(".rm-victory.locked").count() == 6
                    assert page.locator(".rm-victory-lock").count() == 0
                    if width <= 700:
                        assert page.locator(".bp-heading").evaluate(
                            "e=>e.getBoundingClientRect().right"
                        ) <= page.locator(".bp-status").evaluate(
                            "e=>e.getBoundingClientRect().left"
                        )
                    coin = page.locator(".rm-victory .rm-coin").first
                    coin.click()
                    assert page.locator("#node-card .rm-lesson-link").count() == 0
                    assert "Hoàn thành bài trước" in page.locator("#node-card").inner_text()
                    page.keyboard.press("Escape")
                    page.evaluate("scrollTo(0,0)")
                    if width in [390, 1440]:
                        page.screenshot(path=str(out / f"{mode}-{width}.png"), full_page=True)
            assert all(s == styles[0] for s in styles), (mode, width, styles)
            results.append({"theme": mode, "width": width, "pages": 4})
    assert not errors, errors
    (out / "results.json").write_text(json.dumps(results, indent=2))
    print("64 page/theme/viewport checks passed; six locked trophy markers verified")
    b.close()
