"""Read-only visual audit of roadmap themes, breakpoints, collisions and cards."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("/tmp/adventure-display-audit")
WIDTHS = [
    320,
    360,
    390,
    430,
    600,
    699,
    700,
    701,
    768,
    899,
    900,
    901,
    1024,
    1099,
    1100,
    1101,
    1200,
    1250,
    1280,
    1366,
    1440,
    1600,
    1920,
    2560,
]


def run():
    OUT.mkdir(exist_ok=True)
    findings = []
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            base_url="http://localhost:8000", viewport={"width": 1440, "height": 900}
        )
        assert ctx.request.post(
            "/api/v1/auth/login", data={"identifier": "SV-001", "password": "matkhau123"}
        ).ok
        original = ctx.request.get("/api/v1/learn").json()
        bands = ctx.request.get("/api/v1/learn/bands").json()
        bands["plan"] = None
        fixture = copy.deepcopy(original)
        template = original["path"]["units"][0]["lessons"][0]
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.route(re.compile(r"/api/v1/learn(?:\?.*)?$"), lambda r: r.fulfill(json=fixture))
        page.route("**/api/v1/learn/bands", lambda r: r.fulfill(json=bands))

        def data(count):
            units = []
            for band in ["A1", "A2", "B1", "B2", "C1", "C2"]:
                lessons = [
                    {
                        **template,
                        "band": band,
                        "lesson_id": f"{band}-{i}",
                        "title": (
                            f"Bài {i + 1}: Tiêu đề bài học dài "
                            "để kiểm tra hiển thị trên nhiều màn hình"
                        ),
                        "status": "completed"
                        if i == 0
                        else "unavailable"
                        if i == count - 1
                        else "new",
                    }
                    for i in range(count)
                ]
                units.append({"unit_id": band, "band": band, "title": band, "lessons": lessons})
            fixture["path"]["units"] = units
            fixture["path"]["lessons_total"] = count * 6
            fixture["path"]["lessons_completed"] = 6
            fixture["next"] = {"lesson_id": "A1-1", "title": "Bài tiếp theo", "basis": "path_order"}

        def theme(mode):
            page.emulate_media(
                color_scheme="dark" if "dark" in mode else "light", reduced_motion="reduce"
            )
            page.evaluate(
                """mode => {
                  localStorage.removeItem("aicefr-theme");
                  if(mode.startsWith("system"))
                    document.documentElement.removeAttribute("data-theme");
                  else document.documentElement.dataset.theme=mode;
                }""",
                mode,
            )

        def load():
            page.goto("/practice")
            page.wait_for_function(
                'document.querySelector("#path-page").getAttribute("aria-busy")!=="true"'
            )

        data(13)
        load()
        modes = [
            ("light", WIDTHS),
            ("dark", WIDTHS),
            ("system-dark", [390, 701, 1101, 1440, 1920]),
            ("system-light", [390, 701, 1101, 1440, 1920]),
        ]
        for mode, widths in modes:
            theme(mode)
            for width in widths:
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(300)
                result = page.evaluate("""() => {
                  const rect=e=>e.getBoundingClientRect();
                  const overlap=(a,b)=>
                    Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*
                    Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
                  const paths=[...document.querySelectorAll('.rm-adventure-path')];
                  const collisions=paths.flatMap((p,i)=>{
                    const m=rect(p.querySelector('.rm-mascot-art'));
                    return [...p.querySelectorAll('.node-coin')]
                      .filter(n=>overlap(rect(n),m)>100).map(n=>({band:i,node:n.dataset.lesson}));
                  });
                  const heads=[...document.querySelectorAll('.rm-level-head')]
                    .map(h=>overlap(rect(h.querySelector('h2')),
                      rect(h.querySelector('.rm-level-stat'))));
                  const landscape=getComputedStyle(paths[0].querySelector('.rm-adventure-scenery'));
                  const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');
                  const lum=color=>{
                    ctx.clearRect(0,0,1,1);ctx.fillStyle=color;ctx.fillRect(0,0,1,1);
                    const c=[...ctx.getImageData(0,0,1,1).data].slice(0,3).map(v=>{
                      v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;
                    });
                    return c[0]*.2126+c[1]*.7152+c[2]*.0722;
                  };
                  const contrast=(a,b)=>{
                    a=lum(a);b=lum(b);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                  };
                  const badgeContrast=[...document.querySelectorAll('.rm-pill')].map(e=>{
                    const c=getComputedStyle(e);
                    const colors=c.backgroundImage.match(
                      /color\\(srgb [^)]+\\)|rgba?\\([^)]+\\)/g)||[];
                    return Math.min(...colors.map(bg=>contrast(c.color,bg)));
                  });
                  return {overflow:document.documentElement.scrollWidth>innerWidth,
                    collisions,heads,badgeContrast,ground:getComputedStyle(paths[0]).backgroundColor,
                    opacity:landscape.opacity,filter:landscape.filter,
                    body:getComputedStyle(document.body).backgroundColor,pathWidth:rect(paths[0]).width};
                }""")
                for issue, value in [
                    ("overflow", result["overflow"]),
                    ("mascot overlaps node", result["collisions"]),
                    ("header overlaps", any(v > 1 for v in result["heads"])),
                ]:
                    if value:
                        findings.append(
                            {"mode": mode, "width": width, "issue": issue, "detail": value}
                        )
                assert all(v is not None and v >= 4.5 for v in result["badgeContrast"]), (
                    mode,
                    width,
                    "badge contrast",
                    result["badgeContrast"],
                )
                coin = page.locator(".lesson-node.current .node-coin").first
                coin.click()
                card = page.locator("#node-card")
                b = card.bounding_box()
                if b["x"] < 0 or b["x"] + b["width"] > width + 1:
                    findings.append(
                        {
                            "mode": mode,
                            "width": width,
                            "issue": "card outside viewport",
                            "detail": b,
                        }
                    )
                page.keyboard.press("Escape")
                checks.append({"mode": mode, "width": width, **result})
                if width in [390, 701, 1101, 1440, 1920]:
                    page.locator(".rm-level").first.screenshot(
                        path=str(OUT / f"{mode}-{width}.png")
                    )
            print(mode, "checked", len(widths), "widths", flush=True)
        # Large and small datasets at selected desktop/mobile sizes, both explicit themes.
        for count in [1, 5, 100]:
            data(count)
            load()
            for mode in ["light", "dark"]:
                theme(mode)
                for width in [320, 700, 701, 1101, 1440, 2560]:
                    # Allow the responsive redraw and 150ms sidebar resize debounce to settle.
                    page.set_viewport_size({"width": width, "height": 900})
                    page.wait_for_timeout(250)
                    assert page.locator(".node-coin").count() == count * 6
                    if page.evaluate("document.documentElement.scrollWidth>innerWidth"):
                        findings.append(
                            {"mode": mode, "width": width, "count": count, "issue": "overflow"}
                        )
                    if count == 1:
                        assert page.locator(".rm-adventure-path").first.evaluate(
                            "p=>p.clientHeight<p.clientWidth*3"
                        )
        # Inspect all six worlds and the expanded editor / confirmation without saving.
        data(5)
        bands["plan"] = {
            "goal": {"band_from": "A1", "band_to": "C2"},
            "units": fixture["path"]["units"],
            "lessons_total": 30,
            "lessons_completed": 6,
        }
        load()
        for mode in ["light", "dark", "system-dark"]:
            theme(mode)
            for width in [320, 390, 701, 1024, 1200, 1280, 1440, 1920, 2560]:
                page.set_viewport_size({"width": width, "height": 900})
                page.wait_for_timeout(300)
                details = page.locator("#band-plan details").first
                details.evaluate("(d)=>d.open=true")
                assert page.locator(".bp-submit").is_disabled()
                assert not page.evaluate("document.documentElement.scrollWidth>innerWidth"), (
                    mode,
                    width,
                    "editor overflow",
                )
                for control in page.locator(
                    ".bp-form .c-dropdown-trigger, .bp-submit, .bp-assessment-button"
                ).all():
                    b = control.bounding_box()
                    assert b and b["x"] >= 0 and b["x"] + b["width"] <= width + 1, (
                        mode,
                        width,
                        "editor control outside viewport",
                        b,
                    )
                page.locator("#band-close").click()
                dialog = page.locator("#bp-remove-dialog")
                assert dialog.is_visible()
                b = dialog.bounding_box()
                assert b["x"] >= 0 and b["x"] + b["width"] <= width + 1, (
                    mode,
                    width,
                    "dialog overflow",
                )
                assert dialog.evaluate("d=>d.scrollWidth<=d.clientWidth"), (
                    mode,
                    width,
                    "dialog content overflows",
                )
                for button in dialog.locator("button").all():
                    rect = button.bounding_box()
                    assert (
                        rect["x"] >= b["x"] and rect["x"] + rect["width"] <= b["x"] + b["width"] + 1
                    ), (mode, width, "dialog button clipped", rect, b)
                page.keyboard.press("Escape")
                page.wait_for_selector("#bp-remove-dialog", state="detached")
                details.evaluate("(d)=>d.open=false")
                if width in [390, 1280, 1920]:
                    for mascot in page.locator(".rm-mascot").all():
                        mascot.scroll_into_view_if_needed()
                    page.screenshot(
                        path=str(OUT / f"six-worlds-{mode}-{width}.png"), full_page=True
                    )
        # Short laptop windows and large text, plus actual preference persistence.
        for mode in ["light", "dark"]:
            theme(mode)
            page.evaluate('window.ui.prefs.setFont("large")')
            for width, height in [(1366, 600), (1366, 768), (1920, 1080), (390, 667), (683, 384)]:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(300)
                assert not page.evaluate("document.documentElement.scrollWidth>innerWidth"), (
                    mode,
                    width,
                    height,
                    "large text overflow",
                )
                page.locator("#band-close").evaluate('e=>e.closest("details").open=true')
                page.locator("#band-close").click()
                b = page.locator("#bp-remove-dialog").bounding_box()
                assert b["y"] >= 0 and b["y"] + b["height"] <= height + 1, (
                    mode,
                    width,
                    height,
                    "dialog vertical overflow",
                )
                assert page.locator("#bp-remove-dialog").evaluate(
                    "d=>d.scrollWidth<=d.clientWidth"
                ), (mode, width, height, "large font dialog content overflows")
                assert page.locator(".bp-dialog-cancel").evaluate("e=>e===document.activeElement")
                page.keyboard.press("Escape")
                page.wait_for_selector("#bp-remove-dialog", state="detached")
            page.evaluate('window.ui.prefs.setFont("normal")')
        for mode, os_mode in [
            ("dark", "light"),
            ("light", "dark"),
            ("system", "dark"),
            ("system", "light"),
        ]:
            page.emulate_media(color_scheme=os_mode)
            page.evaluate("(mode)=>window.ui.prefs.setTheme(mode)", mode)
            load()
            expected = os_mode if mode == "system" else mode
            assert page.locator("html").get_attribute("data-theme") == expected
            for band, world in zip(
                ["a1", "a2", "b1", "b2", "c1", "c2"],
                ["forest", "volcano", "snow", "river", "desert", "flowers"],
                strict=True,
            ):
                scene = page.locator(f".band-{band} .rm-adventure-scenery")
                assert scene.evaluate("(p)=>getComputedStyle(p).filter") == "none"
                image = scene.locator(".rm-terrain-tile").first.evaluate(
                    "(p)=>getComputedStyle(p).backgroundImage"
                )
                assert (f"{world}-night-a-" in image) == (expected == "dark"), (
                    mode,
                    os_mode,
                    world,
                    image,
                )
        report = {
            "checks": checks,
            "findings": findings,
            "javascript_errors": errors,
            "data_writes": False,
        }
        (OUT / "report.json").write_text(json.dumps(report, indent=2))
        print("FINDINGS", json.dumps(findings), flush=True)
        print("JS errors", errors, flush=True)
        browser.close()
        assert not findings and not errors, "See " + str(OUT / "report.json")


if __name__ == "__main__":
    run()
