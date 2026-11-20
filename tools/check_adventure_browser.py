"""Exercise the adaptive roadmap with API fixtures, without writing learner data.

Run against ./demo.sh: .venv/bin/python tools/check_adventure_browser.py
Uses the local demo account and intercepts only GET learning responses.
"""

from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default="/tmp/adventure-checks")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            base_url=args.base_url, viewport={"width": 1440, "height": 1000}
        )
        auth = context.request.post(
            "/api/v1/auth/login",
            data={"identifier": "sv-001@demo.speakup.fit", "password": "matkhau123"},
        )
        assert auth.ok, "Local demo account is required"
        original = context.request.get("/api/v1/learn").json()
        bands = context.request.get("/api/v1/learn/bands").json()
        bands["plan"] = None
        fixture = copy.deepcopy(original)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route(
            re.compile(r"/api/v1/learn(?:\?.*)?$"), lambda route: route.fulfill(json=fixture)
        )
        page.route("**/api/v1/learn/bands", lambda route: route.fulfill(json=bands))
        template = original["path"]["units"][0]["lessons"][0]

        def set_count(count):
            units = []
            for band in ["A1", "A2", "B1", "B2", "C1", "C2"]:
                lessons = [
                    {
                        **template,
                        "lesson_id": f"{band}-lesson-{i}",
                        "band": band,
                        "title": f"Bài {i + 1} · {band} — Tiêu đề dài để kiểm tra cách hiển thị khi teacher bổ sung nội dung",
                        "status": "completed" if i == 0 and count > 2 else "new",
                    }
                    for i in range(count)
                ]
                units.append(
                    {
                        "unit_id": f"test-{band}",
                        "band": band,
                        "title": band,
                        "topic": "daily_life",
                        "lessons": lessons,
                    }
                )
            fixture["path"]["units"] = units
            fixture["path"]["lessons_total"] = count * 6
            fixture["path"]["lessons_completed"] = 6 if count > 2 else 0
            fixture["next"] = (
                {
                    "lesson_id": f"A1-lesson-{1 if count > 2 else 0}",
                    "title": "Bài tiếp theo",
                    "basis": "path_order",
                }
                if count
                else None
            )

        def load():
            page.goto("/practice")
            page.wait_for_function(
                "() => document.querySelector('#path-page').getAttribute('aria-busy') !== 'true'"
            )

        # Decode the actual environment files: each world must be a distinct long strip.
        set_count(5)
        load()
        landscapes = page.locator(".rm-adventure-path").evaluate_all(r"""async paths => Promise.all(paths.map(async p => {
          const css=getComputedStyle(p.querySelector('.rm-terrain-tile'));
          const url=css.backgroundImage.match(/url\(["']?([^"')]+)/)[1];
          const response=await fetch(url);
          if(!response.ok) throw new Error('Landscape failed: '+url);
          const bitmap=await createImageBitmap(await response.blob());
          const result={url,width:bitmap.width,height:bitmap.height,ratio:Number(getComputedStyle(p).getPropertyValue('--scene-ratio')),size:css.backgroundSize};
          bitmap.close(); return result;
        }))""")
        assert len({v["url"] for v in landscapes}) == 6
        for scene in landscapes:
            assert scene["height"] / scene["width"] > 0.66, scene
            assert abs(scene["ratio"] - scene["height"] / scene["width"]) < 0.001, scene
            assert scene["size"] == "100% 100%", (
                scene
            )  # Tile dimensions preserve the source aspect ratio.
        for count in [0, 1, 2, 5, 12, 13, 30, 100]:
            set_count(count)
            load()
            expected = count * 6
            assert page.locator(".lesson-node").count() == expected
            assert page.locator("#node-card").count() == 0
            assert page.locator(".rm-chapter-label").count() == (
                6 * ((count + 11) // 12) if count > 12 else 0
            )
            for width in [1440, 1024, 700, 390, 320]:
                page.set_viewport_size({"width": width, "height": 1000})
                page.wait_for_timeout(250)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                    count,
                    width,
                    "horizontal overflow",
                )
                assert page.locator("footer.site-footer").count() == 0, "No application footer"
                if width <= 700:
                    mobile = page.evaluate("""() => {
                      const map=document.querySelector('.rm-roadmap').getBoundingClientRect();
                      const content=document.querySelector('.rm-content').getBoundingClientRect();
                      const nav=document.querySelector('.rm-tabbar').getBoundingClientRect();
                      return {fullWidth:Math.abs(map.width-content.width)<1, bottom:nav.bottom,
                              left:nav.left,right:nav.right,height:innerHeight,width:innerWidth};
                    }""")
                    assert mobile["fullWidth"], (count, width, "roadmap must fill available width")
                    assert (
                        abs(mobile["bottom"] - mobile["height"]) < 1
                        and mobile["left"] == 0
                        and mobile["right"] == width
                    ), (count, width, "navigation must be fixed to viewport", mobile)
                if not count:
                    assert page.locator(".rm-empty").is_visible()
                    continue
                # Every coin remains inside its path and companions stay inside the clearing without covering lessons.
                checks = page.locator(".rm-adventure-path").evaluate_all("""paths => paths.map(p => {
                  const b = p.getBoundingClientRect(), nodes = [...p.querySelectorAll('.node-coin')];
                  const m = p.querySelector('.rm-mascot').getBoundingClientRect();
                  return {contained:nodes.every(n=>{const r=n.getBoundingClientRect();return r.left>=b.left-1 && r.right<=b.right+1 && r.top>=b.top-1 && r.bottom<=b.bottom+1}),clearing:m.left>=b.left+8 && m.right<=b.right-8 && m.top>=b.top && m.bottom<=b.bottom && nodes.every(n=>{const r=n.getBoundingClientRect();return Math.min(m.right,r.right)<=Math.max(m.left,r.left) || Math.min(m.bottom,r.bottom)<=Math.max(m.top,r.top)})};
                })""")
                assert all(v["contained"] and v["clearing"] for v in checks), (count, width, checks)
                coin = page.locator(".node-coin").first
                before = page.locator(".rm-adventure-path").first.evaluate(
                    "(p)=>p.getBoundingClientRect().height"
                )
                coin.click()
                assert page.locator("#node-card").is_visible()
                card = page.locator("#node-card").bounding_box()
                assert card["x"] >= 0 and card["x"] + card["width"] <= width + 1, (
                    count,
                    width,
                    "card overflow",
                )
                assert (
                    abs(
                        page.locator(".rm-adventure-path").first.evaluate(
                            "(p)=>p.getBoundingClientRect().height"
                        )
                        - before
                    )
                    < 0.5
                ), (
                    count,
                    width,
                    before,
                    page.locator(".rm-adventure-path").first.evaluate(
                        '(p)=>({height:p.getBoundingClientRect().height,style:p.getAttribute("style")})'
                    ),
                )
                page.keyboard.press("Escape")
                assert page.locator("#node-card").count() == 0
            print(f"{count} lessons/band: desktop, tablet, mobile, cards and chapter count passed")
        # A rendered six-region overview for visual review, using 5 lessons per region.
        set_count(5)
        page.set_viewport_size({"width": 1440, "height": 1000})
        load()
        for mascot in page.locator(".rm-mascot").all():
            mascot.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        page.screenshot(path=str(output / "six-regions-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 1000})
        page.wait_for_timeout(200)
        page.screenshot(path=str(output / "six-regions-mobile.png"), full_page=True)
        # Check a learner's actual data as well, without fixtures.
        page.unroute_all(behavior="wait")
        page.goto("/practice")
        page.wait_for_function(
            "() => document.querySelector('#path-page').getAttribute('aria-busy') !== 'true'"
        )
        page.screenshot(path=str(output / "actual-plan.png"), full_page=True)
        assert not errors, errors
        print("No JavaScript errors. No learner data changed. Screenshots:", output)
        browser.close()


if __name__ == "__main__":
    main()
