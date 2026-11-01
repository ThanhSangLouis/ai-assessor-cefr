"""Layer 2 -- the look of D031: Roboto, the new mark, depth and motion.

Most of D031 is a stylesheet, and a stylesheet fails quietly: a font file left
out of the wheel falls back to Arial without a word, a preload that does not
match the @font-face URL downloads the font twice, a class name that collides
squashes the logo, a backdrop filter in the wrong media query pulls the phone's
tab bar off the bottom of the screen. Each of those is pinned here. Test case
ids (TC-UI-Ixx) are listed in `docs/test/TEST_PLAN_D031.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aicefr.api.main import app

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "aicefr" / "api" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
client = TestClient(app)


def font_urls() -> list[str]:
    return re.findall(r'url\("(fonts/[^"]+\.woff2)"\)', CSS)


def rule_bodies(selector_fragment: str) -> list[tuple[int, str]]:
    """(position, body) of every rule whose selector mentions the fragment."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", CSS):
        if selector_fragment in m.group(1):
            out.append((m.start(), m.group(2)))
    return out


def enclosing_media(position: int) -> str | None:
    """The @media condition a position sits in, if any (one level is enough here)."""
    depth, media = 0, None
    for m in re.finditer(r"@media([^{]*)\{|\{|\}", CSS[:position]):
        if m.group(0).startswith("@media"):
            depth += 1
            media = m.group(1).strip()
        elif m.group(0) == "{":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                media = None
    return media


def test_roboto_is_served_by_the_app_itself() -> None:
    urls = font_urls()
    # Upright and italic, three subsets each: latin, latin-ext, vietnamese.
    assert len(urls) == 6
    for url in urls:
        assert (STATIC / url).is_file(), url
        r = client.get(f"/static/{url}")
        assert r.status_code == 200, url
        assert r.headers["content-type"] == "font/woff2"
    assert "googleapis" not in CSS and "gstatic" not in CSS
    assert "font-display: swap" in CSS


def test_the_wheel_carries_the_fonts_and_their_licence() -> None:
    # Read as text: tomllib only arrives in Python 3.11, and the project still runs on 3.10.
    meta = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    data = meta[meta.index("[tool.setuptools.package-data]") :]
    data = data[: data.index("]", data.index("aicefr = ["))]
    assert '"api/static/fonts/*.woff2"' in data
    assert '"api/static/fonts/*.txt"' in data
    licence = (STATIC / "fonts" / "ROBOTO-OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in licence.upper()


def test_the_preloaded_fonts_are_the_ones_the_stylesheet_asks_for() -> None:
    page = client.get("/").text
    preloads = re.findall(r'<link rel="preload" href="([^"]+)" as="font"', page)
    assert len(preloads) == 2
    wanted = {f"/static/{url}" for url in font_urls()}
    for href in preloads:
        # Same URL as the @font-face rule, no version query: anything else is
        # a second download of the same file.
        assert href in wanted, href
    assert any("vietnamese" in href for href in preloads)


def test_the_mark_is_drawn_inline_with_names_of_its_own() -> None:
    page = client.get("/").text
    mark = page[page.index('<svg class="brand-mark"') :]
    mark = mark[: mark.index("</svg>")]
    assert mark.count('class="logo-bubble"') == 1
    assert mark.count('<rect class="logo-bar') == 3
    # A bare `.bar` is the progress bar's class; on the mark it squashed the
    # three bars to dots (TEST_PLAN_D031, D031-B1).
    assert 'class="bar' not in mark
    favicon = (STATIC / "favicon.svg").read_text(encoding="utf-8")
    assert favicon.count('class="logo-bar"') == 3
    assert "prefers-color-scheme: dark" in favicon


def test_the_product_page_keeps_its_words_out_of_the_3d_scene() -> None:
    page = client.get("/").text
    # D078: the hero's illustrated scene is gone; the words stand on their own.
    assert 'class="lp-stage"' not in page and "data-scene" not in page
    assert re.search(r"<h1[^>]*>.*Tiến bộ", page, re.S)
    assert 'id="how-it-works"' in page
    assert "/static/landing.js?v=" in page


def test_the_blocks_on_other_screens_are_hidden_from_screen_readers() -> None:
    for url in ("/login", "/bands"):
        page = client.get(url).text
        stages = re.findall(r'<div class="cube-stage[^"]*"([^>]*)>', page)
        assert stages, url
        assert all('aria-hidden="true"' in attrs for attrs in stages), url


def test_reduced_motion_stops_the_motion() -> None:
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)") :]
    assert "animation-duration: 0.01ms !important" in reduced[:400]
    assert "transition-duration: 0.01ms !important" in reduced[:400]
    assert re.search(
        r"@media \(prefers-reduced-motion: reduce\) \{\s*@view-transition \{ navigation: none; \}",
        CSS,
    )
    # What moves by itself on scroll or on arrival only does so when motion is welcome.
    for marker in ("animation-timeline: view();", "main > * { animation: rise-in"):
        assert enclosing_media(CSS.index(marker)) == "(prefers-reduced-motion: no-preference)"
    script = (STATIC / "landing.js").read_text(encoding="utf-8")
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in script
    assert re.search(r"if \(reduced\.matches \|\| !finePointer\.matches\) return;", script)


def test_the_sidebar_is_frosted_only_where_it_holds_no_fixed_tab_bar() -> None:
    frosted = [
        (pos, body) for pos, body in rule_bodies(".app-sidebar") if "backdrop-filter" in body
    ]
    assert frosted
    for pos, _body in frosted:
        assert enclosing_media(pos) == "(min-width: 901px)"
