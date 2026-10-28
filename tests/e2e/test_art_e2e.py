"""Layer 3 -- E2E for the background art (D037): on the screen, moving, and out of the way.

A stylesheet test can say a rule exists. Only a browser shows that the hills
are on the screen in both themes, that the ridges draw themselves in and hold
still for someone who asked for less motion, that a wide screen gets the
whole far hill and a round sun, that a phone gets no sideways scroll and every
tap still lands on what is under it, that paper gets none of it, and --
W-NFR-4 -- that no word standing on the art loses the contrast it needs. Test
case ids (TC-ART-Exx) are listed in `docs/test/TEST_PLAN_D037.md`.

Server, browser and helpers come from `test_practice_e2e.py`, as in the other
E2E modules.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import base64

import pytest

pytest.importorskip("playwright.sync_api")

from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    browser,
    live_server,
    login,
    wait_until,
)

pytestmark = pytest.mark.e2e

ART = ".ground, .lp-terraces, .auth-terraces"
NEAR_RIDGE = "document.querySelector('.lp-terraces .b3 .art-wave')"
ART_ANIMATIONS = (
    "document.getAnimations().map(a => a.animationName || '').filter(n => n.startsWith('art-'))"
)


def new_context(browser, live_server, width=1280, height=820, **extra):
    ctx = browser.new_context(
        base_url=live_server.base_url,
        locale="vi-VN",
        viewport={"width": width, "height": height},
        **extra,
    )
    ctx.set_default_timeout(15_000)
    return ctx


def test_the_ground_is_drawn_in_both_themes(browser, live_server):
    colours = {}
    for scheme in ("light", "dark"):
        ctx = new_context(browser, live_server, color_scheme=scheme)
        fetched: dict[str, int] = {}

        def seen(response, fetched=fetched):
            if "/static/art/" in response.url:
                fetched[response.url.rsplit("/", 1)[-1]] = response.status

        try:
            page = ctx.new_page()
            page.on("response", seen)
            page.goto("/bands")
            page.wait_for_load_state("networkidle")
            assert fetched == {"contours.svg": 200, "hills.svg": 200}, fetched
            pieces = page.evaluate(
                """() => ['.ground-lines', '.ground-hills'].map(sel => {
                  const e = document.querySelector(sel), s = getComputedStyle(e);
                  const r = e.getBoundingClientRect();
                  return {mask: s.maskImage || s.webkitMaskImage, colour: s.backgroundColor,
                          w: r.width, h: r.height, top: r.top, right: r.right, bottom: r.bottom};
                })"""
            )
            lines, hills = pieces
            assert "art/contours.svg" in lines["mask"] and "art/hills.svg" in hills["mask"]
            # Lines high on the right, hills low on the right, both a fair size.
            assert lines["top"] == 0 and lines["right"] == 1280
            assert hills["bottom"] == 820 and hills["right"] == 1280
            for piece in pieces:
                assert piece["w"] > 400 and piece["h"] > 200, piece
                assert piece["colour"] not in ("", "transparent", "rgba(0, 0, 0, 0)"), piece
            colours[scheme] = hills["colour"]
        finally:
            ctx.close()
    # Each theme inks it in its own colour.
    assert colours["light"] != colours["dark"]


def test_the_ridges_draw_themselves_in_when_motion_is_welcome(browser, live_server):
    ctx = new_context(browser, live_server, reduced_motion="no-preference")
    try:
        page = ctx.new_page()
        page.goto("/")
        names = page.evaluate(ART_ANIMATIONS)
        # Four bands rise, four ridges draw in, the sun comes up, the nearest band breathes.
        assert names.count("art-rise") == 4 and names.count("art-draw") == 4, names
        assert names.count("art-sunrise") == 1 and names.count("art-breathe") == 1, names
        wait_until(
            page,
            "document.getAnimations().filter(a => a.animationName === 'art-draw'"
            " && a.playState !== 'finished').length === 0",
        )
        # Drawn in, a ridge stays drawn; the breathing goes on.
        offset = page.evaluate(f"getComputedStyle({NEAR_RIDGE}).strokeDashoffset")
        assert float(offset.removesuffix("px")) == 0
        assert page.evaluate(
            "document.getAnimations().some(a => a.animationName === 'art-breathe'"
            " && a.playState === 'running' && a.effect.getComputedTiming().iterations === Infinity)"
        )
    finally:
        ctx.close()


def test_with_reduced_motion_the_scene_is_simply_there(browser, live_server):
    ctx = new_context(browser, live_server, reduced_motion="reduce")
    try:
        page = ctx.new_page()
        page.goto("/")
        state = page.evaluate(
            f"""() => ({{
              running: {ART_ANIMATIONS}.length,
              dashes: getComputedStyle({NEAR_RIDGE}).strokeDasharray,
              band: getComputedStyle(document.querySelector('.lp-terraces .b3')).animationName,
              sun: getComputedStyle(document.querySelector('.lp-terraces .art-sun')).animationName,
            }})"""
        )
        assert state == {"running": 0, "dashes": "none", "band": "none", "sun": "none"}
        # Nor does the pointer move the hills.
        hero = page.locator(".lp-hero").bounding_box()
        page.mouse.move(hero["x"] + hero["width"] * 0.95, hero["y"] + hero["height"] * 0.2, steps=6)
        page.wait_for_timeout(400)
        drift = page.evaluate("getComputedStyle(document.querySelector('.lp-terraces')).translate")
        assert drift in ("none", "0px", "0px 0px"), drift
    finally:
        ctx.close()


def test_the_terraces_drift_against_the_scene(browser, live_server):
    ctx = new_context(browser, live_server)
    try:
        page = ctx.new_page()
        page.goto("/")
        hero = page.locator(".lp-hero").bounding_box()
        page.mouse.move(hero["x"] + hero["width"] * 0.95, hero["y"] + hero["height"] * 0.2, steps=6)
        wait_until(
            page, "Number(document.querySelector('.lp-hero').style.getPropertyValue('--px')) > 0.3"
        )
        # The scene turns toward the pointer on the right; the hills slide the other way.
        drift = page.evaluate("getComputedStyle(document.querySelector('.lp-terraces')).translate")
        assert float(drift.split()[0].removesuffix("px")) < 0, drift
    finally:
        ctx.close()


def test_any_width_gets_the_whole_far_hill_and_a_round_sun(browser, live_server):
    measure = """(cls) => {
      const box = document.querySelector(cls).getBoundingClientRect();
      const fills = [...document.querySelectorAll(cls + ' .art-fill')]
        .map(p => p.getBoundingClientRect().top - box.top);
      const sun = document.querySelector(cls + ' .art-sun');
      const s = sun.getBoundingClientRect();
      return {fills, shown: getComputedStyle(sun).display !== 'none',
              sun: [s.width, s.height, s.top - box.top, box.right - s.right]};
    }"""
    for width in (390, 1280, 1920, 2560):
        ctx = new_context(browser, live_server, width=width, height=900, reduced_motion="reduce")
        try:
            page = ctx.new_page()
            for url, cls in (("/", ".lp-terraces"), ("/login", ".auth-terraces")):
                page.goto(url)
                got = page.evaluate(measure, cls)
                # No band is cut along the top of its box, however wide the screen.
                assert len(got["fills"]) == 4 and min(got["fills"]) >= -0.5, (width, url, got)
                if url == "/":
                    w, h, top, right = got["sun"]
                    assert got["shown"] and w > 20 and abs(w - h) < 0.5, (width, got)
                    assert top >= 0 and right >= 0, (width, got)
                else:
                    # The form stands where the sun would peek out: no sun there.
                    assert not got["shown"], width
        finally:
            ctx.close()


def test_on_a_phone_the_art_takes_no_tap_and_no_room(browser, live_server):
    ctx = new_context(
        browser,
        live_server,
        width=390,
        height=844,
        is_mobile=True,
        has_touch=True,
        reduced_motion="reduce",
    )
    hit = f"""() => {{
      const hits = [];
      for (let y = 2; y < innerHeight; y += 23)
        for (let x = 2; x < innerWidth; x += 23) {{
          const e = document.elementFromPoint(x, y);
          if (e && e.closest('{ART}')) hits.push([x, y, e.className.baseVal ?? e.className]);
        }}
      return hits;
    }}"""
    try:
        page = ctx.new_page()
        for url, target in (
            ("/", page.get_by_role("link", name="Đăng nhập").first),
            ("/login", page.get_by_role("button", name="Đăng nhập")),
            ("/bands", None),
        ):
            page.goto(url)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), url
            for _ in range(2):  # the first screen, then the foot of the page
                assert page.evaluate(hit) == [], url
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            if target is not None:
                # Playwright's own check that nothing else would take the tap.
                target.scroll_into_view_if_needed()
                target.tap(trial=True)
    finally:
        ctx.close()


def test_printing_leaves_the_art_out(browser, live_server):
    ctx = new_context(browser, live_server)
    try:
        page = ctx.new_page()
        login(page, live_server, live_server.account(), "/my-progress")
        # Drawn by my_progress.js once the page has asked for the results.
        page.locator(".empty-state").first.wait_for()
        horizon = "getComputedStyle(document.querySelector('.empty-state'), '::after')"
        assert page.evaluate(f"{horizon}.display") == "block"
        page.emulate_media(media="print")
        assert page.evaluate(f"{horizon}.display") == "none"
        assert (
            page.evaluate("getComputedStyle(document.querySelector('.ground')).display") == "none"
        )
        page.context.clear_cookies()
        for url, pieces in (
            ("/", (".ground", ".lp-terraces")),
            ("/login", (".ground", ".auth-terraces")),
        ):
            page.goto(url)
            for piece in pieces:
                display = page.evaluate(
                    f"getComputedStyle(document.querySelector('{piece}')).display"
                )
                assert display == "none", (url, piece)
    finally:
        ctx.close()


# --- W-NFR-4: the words standing on the art keep the contrast they need.
#
# Measured on the pixels, as a reader sees them: the page is shot with its words
# made transparent -- once with the art, once without -- and each run of text is
# set against every pixel behind it. AA asks 4.5:1 of body text and 3:1 of large
# text (24px, or 18.66px bold). The art may darken or lighten a background, but
# never so far that a word drops below what it needs; and where the page without
# the art already falls short, the art must not make it worse.

TEXTS = """(roots) => {
  const paint = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const rgba = (colour) => {  // any CSS colour, as the canvas reads it back
    paint.clearRect(0, 0, 1, 1);
    paint.fillStyle = '#000';
    paint.fillStyle = colour;
    paint.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = paint.getImageData(0, 0, 1, 1).data;
    return [r, g, b, a / 255];
  };
  const out = [];
  for (const root of document.querySelectorAll(roots)) {
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walk.nextNode(); node; node = walk.nextNode()) {
      const el = node.parentElement;
      if (!node.textContent.trim() || el.closest('[aria-hidden="true"]')) continue;
      // Words a reader cannot see -- the inside of a closed <details>, say --
      // have boxes all the same; they are not on the screen to be read.
      if (!el.checkVisibility({contentVisibilityAuto: true, opacityProperty: true,
                               visibilityProperty: true})) continue;
      const style = getComputedStyle(el);
      let opacity = 1;
      // What clips the words: every ancestor that does not let its content overflow.
      let clip = [0, 0, innerWidth, innerHeight];
      for (let e = el; e; e = e.parentElement) {
        const s = getComputedStyle(e);
        opacity *= Number(s.opacity);
        if (e !== el && (s.overflowX !== 'visible' || s.overflowY !== 'visible')) {
          const q = e.getBoundingClientRect();
          clip = [Math.max(clip[0], q.left), Math.max(clip[1], q.top),
                  Math.min(clip[2], q.right), Math.min(clip[3], q.bottom)];
        }
      }
      const [r, g, b, a] = rgba(style.color);
      if (a * opacity === 0) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const rects = [...range.getClientRects()]
        .map(q => [Math.max(q.left, clip[0]), Math.max(q.top, clip[1]),
                   Math.min(q.right, clip[2]), Math.min(q.bottom, clip[3])])
        .filter(([x0, y0, x1, y1]) => x1 - x0 >= 1 && y1 - y0 >= 1)
        .map(([x0, y0, x1, y1]) => [x0, y0, x1 - x0, y1 - y0]);
      if (!rects.length) continue;
      const size = parseFloat(style.fontSize), weight = Number(style.fontWeight);
      const large = size >= 24 || (size >= 18.66 && weight >= 700);
      out.push({text: node.textContent.trim().slice(0, 48), rects, fg: [r, g, b],
                alpha: a * opacity, need: large ? 3 : 4.5});
    }
  }
  return out;
}"""

WORST = """async ([shots, items]) => {
  const read = (b64) => new Promise((ok, fail) => {
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = img.width;
      c.height = img.height;
      const g = c.getContext('2d', {willReadFrequently: true});
      g.drawImage(img, 0, 0);
      ok(g.getImageData(0, 0, c.width, c.height));
    };
    img.onerror = fail;
    img.src = 'data:image/png;base64,' + b64;
  });
  const [art, plain] = await Promise.all(shots.map(read));
  const channel = (v) => {
    v /= 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (r, g, b) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  const worst = (img, item) => {
    const [fr, fg, fb] = item.fg, a = item.alpha;
    let low = Infinity;
    for (const [x0, y0, w, h] of item.rects)
      for (let y = Math.ceil(y0); y < Math.floor(y0 + h); y++)
        for (let x = Math.ceil(x0); x < Math.floor(x0 + w); x++) {
          const i = (y * img.width + x) * 4;
          const [br, bg, bb] = [img.data[i], img.data[i + 1], img.data[i + 2]];
          const back = luminance(br, bg, bb);
          const mix = (f, b) => f * a + b * (1 - a);
          const fore = luminance(mix(fr, br), mix(fg, bg), mix(fb, bb));
          low = Math.min(low, (Math.max(back, fore) + 0.05) / (Math.min(back, fore) + 0.05));
        }
    return low;
  };
  return items.map(item => ({text: item.text, need: item.need,
                             art: worst(art, item), plain: worst(plain, item)}));
}"""

NO_WORDS = (
    "*, *::before, *::after, ::marker { color: transparent !important;"
    " -webkit-text-fill-color: transparent !important; text-shadow: none !important;"
    " caret-color: transparent !important; }"
)
NO_ART = (
    f"{ART} {{ visibility: hidden !important; }}"
    " .empty-state::after { content: none !important; }"
)


def shoot(page, css: str) -> str:
    tag = page.add_style_tag(content=css)
    page.wait_for_timeout(50)
    shot = base64.b64encode(page.screenshot()).decode()
    tag.evaluate("e => e.remove()")
    return shot


def test_the_words_on_the_art_keep_their_contrast(browser, live_server):
    student = live_server.account()
    pages = (
        ("/", ".lp-hero-copy"),
        ("/login", ".auth-intro, .auth-card"),
        ("/bands", "main"),
        ("/my-progress", "main"),
    )
    failures, measured = [], 0
    for width, height in ((1280, 820), (390, 844)):
        for scheme in ("light", "dark"):
            ctx = new_context(
                browser,
                live_server,
                width=width,
                height=height,
                color_scheme=scheme,
                reduced_motion="reduce",
            )
            try:
                page = ctx.new_page()
                for url, roots in pages:
                    if url == "/my-progress":
                        login(page, live_server, student, url)
                        page.locator(".empty-state").first.wait_for()
                    else:
                        page.goto(url)
                    page.wait_for_load_state("networkidle")
                    page.evaluate("document.activeElement && document.activeElement.blur()")
                    items = page.evaluate(TEXTS, roots)
                    assert items, (url, width, scheme)
                    shots = [shoot(page, NO_WORDS), shoot(page, NO_WORDS + NO_ART)]
                    for row in page.evaluate(WORST, [shots, items]):
                        measured += 1
                        if row["art"] < row["need"] and row["art"] < row["plain"] - 0.01:
                            failures.append((url, width, scheme, row))
            finally:
                ctx.close()
    assert measured > 100, measured
    assert failures == [], failures
