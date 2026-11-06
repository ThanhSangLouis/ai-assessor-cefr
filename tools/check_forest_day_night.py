"""Read-only forest pilot checks: scale, seams, theme and density (local demo)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    output = Path("/tmp/forest-day-night-checks")
    output.mkdir(exist_ok=True)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for density in [1, 2]:
            context = browser.new_context(
                base_url="http://localhost:8000", device_scale_factor=density
            )
            assert context.request.post(
                "/api/v1/auth/login", data={"identifier": "SV-001", "password": "matkhau123"}
            ).ok
            original = context.request.get("/api/v1/learn").json()
            bands = context.request.get("/api/v1/learn/bands").json()
            bands["plan"] = None
            fixture = copy.deepcopy(original)
            unit = copy.deepcopy(original["path"]["units"][0])
            template = unit["lessons"][0]
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route(
                re.compile(r"/api/v1/learn(?:\?.*)?$"),
                lambda r, request, data=fixture: r.fulfill(json=data),
            )
            page.route("**/api/v1/learn/bands", lambda r, request, data=bands: r.fulfill(json=data))
            scales = {}
            for width in [390, 1440, 1920]:
                page.set_viewport_size({"width": width, "height": 1000})
                for count in [1, 3, 5, 15, 50]:
                    unit["band"] = "A1"
                    unit["lessons"] = [
                        {
                            **template,
                            "lesson_id": f"forest-{i}",
                            "band": "A1",
                            "status": "new" if i == 0 else "locked",
                        }
                        for i in range(count)
                    ]
                    fixture["path"]["units"] = [unit]
                    fixture["path"]["lessons_total"] = count
                    fixture["path"]["lessons_completed"] = 0
                    fixture["next"] = {
                        "lesson_id": "forest-0",
                        "title": "Bài đầu tiên",
                        "basis": "path_order",
                    }
                    page.goto("/practice")
                    page.wait_for_function('() => document.querySelector(".rm-terrain-tile")')
                    for theme in ["light", "dark"]:
                        page.evaluate(
                            "theme => document.documentElement.dataset.theme = theme", theme
                        )
                        page.emulate_media(reduced_motion="reduce")
                        page.wait_for_timeout(120)
                        result = page.evaluate("""() => {
                          const path = document.querySelector('.rm-adventure-path');
                          const scene = path.querySelector('.rm-adventure-scenery');
                          const tiles = [...scene.children], first=tiles[0], last=tiles.at(-1);
                          const rect=path.getBoundingClientRect();
                          const a=first.getBoundingClientRect(), z=last.getBoundingClientRect();
                          const gap=tiles.some((t,i)=>i && t.getBoundingClientRect().top >
                            tiles[i-1].getBoundingClientRect().bottom);
                          return {width:rect.width,height:rect.height,
                            tileHeight:a.height,count:tiles.length,
                            firstTop:a.top-rect.top,lastBottom:z.bottom-rect.bottom,gap,
                            firstMask:getComputedStyle(first).maskImage,filter:getComputedStyle(scene).filter,
                            image:getComputedStyle(first).backgroundImage,
                            overflow:document.documentElement.scrollWidth>innerWidth};
                        }""")
                        mode = "night" if theme == "dark" else "day"
                        assert f"forest-{mode}-a-v3-" in result["image"], result
                        assert not result["gap"] and not result["overflow"], result
                        assert abs(result["firstTop"]) < 1 and result["lastBottom"] >= -1, result
                        assert result["firstMask"] == "none" and result["filter"] == "none", result
                        assert abs(result["tileHeight"] / result["width"] - 2 / 3) < 0.001, result
                        key = (density, width)
                        if key in scales:
                            assert abs(scales[key] - result["tileHeight"]) < 1, (key, result)
                        scales[key] = result["tileHeight"]
                        small, large = (
                            (480, 960)
                            if width <= 480
                            else (768, 1536)
                            if width <= 700
                            else (1280, 1536)
                        )
                        native = large if density == 2 else small
                        resource = f"/static/art/adventure/forest-{mode}-a-v3-{native}.webp"
                        page.wait_for_function(
                            'url => performance.getEntriesByType("resource").some('
                            "r => r.name.endsWith(url) && r.responseEnd > 0)",
                            arg=resource,
                        )
                        result.update(
                            viewport=width,
                            lessons=count,
                            density=density,
                            theme=theme,
                            resource=resource,
                            sourcePixelsPerDevicePixel=round(native / result["width"] / density, 3),
                        )
                        checks.append(result)
                        if count in [3, 15] and width in [390, 1440] and density == 2:
                            path = page.locator(".rm-adventure-path")
                            path.scroll_into_view_if_needed()
                            page.screenshot(path=str(output / f"{mode}-{width}-{count}-dpr2.png"))
            # System dark and explicit light override the operating-system preference.
            page.emulate_media(color_scheme="dark")
            page.evaluate('() => document.documentElement.removeAttribute("data-theme")')
            assert "forest-night-a-" in page.locator(".rm-terrain-tile").first.evaluate(
                "(e)=>getComputedStyle(e).backgroundImage"
            )
            page.evaluate('() => document.documentElement.dataset.theme="light"')
            assert "forest-day-a-" in page.locator(".rm-terrain-tile").first.evaluate(
                "(e)=>getComputedStyle(e).backgroundImage"
            )
            context.close()
        browser.close()
    assert not errors, errors
    report = {"checks": checks, "javascript_errors": errors, "learner_data_writes": False}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(f"{len(checks)} checks passed; screenshots/report: {output}")


if __name__ == "__main__":
    main()
