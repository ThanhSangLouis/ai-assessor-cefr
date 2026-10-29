"""Layer 2 -- INTEGRATION: the background art of every page (D037).

Decoration fails in two directions. It goes missing without a word: a file
left out of the wheel, a page that forgot the ground, a drawing edited by hand
and then overwritten by the script. Or it gets in the way: a script inside an
SVG, an element that takes clicks, motion for someone who asked for none, ink
on a printed page. Both directions are pinned here. What only a browser can
tell -- the picture on the screen, the animation running, the words standing
on it still readable -- is in `tests/e2e/test_art_e2e.py`. Test case ids
(TC-ART-Ixx) are listed in `docs/test/TEST_PLAN_D037.md`.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest
from fastapi.testclient import TestClient
from test_ui_depth import enclosing_media, rule_bodies

from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "aicefr" / "api" / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
PASSWORD = "matkhau-kiem-thu"
GROUND = '<div class="ground" aria-hidden="true">'

_SPEC = importlib.util.spec_from_file_location("make_art", ROOT / "tools" / "make_art.py")
art = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = art
_SPEC.loader.exec_module(art)


@pytest.fixture
def m(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    importlib.reload(main)
    return main


def signed_in(m, pseudonym: str, role: str) -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    client = TestClient(m.app)
    r = client.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client


def scene(page: str, cls: str) -> str:
    """The markup of the scene: from its opening tag to the end of its drawing."""
    start = page.index(f'<div class="{cls}" aria-hidden="true">')
    return page[start : page.index("</svg>", start) + len("</svg>")]


def test_the_committed_art_is_what_the_script_draws():
    for path, draw in art.OUTPUTS.items():
        assert path.read_text(encoding="utf-8") == draw(), (
            f"{path.name} differs from what tools/make_art.py draws: run it, do not edit by hand"
        )


def test_the_drawings_are_inert_and_small():
    svg = "{http://www.w3.org/2000/svg}"
    for name, budget in (("hills.svg", 12_000), ("contours.svg", 12_000)):
        text = (STATIC / "art" / name).read_text(encoding="utf-8")
        assert len(text.encode()) < budget, name
        assert "<!DOCTYPE" not in text and "<!ENTITY" not in text
        root = ElementTree.fromstring(text)
        assert root.tag == svg + "svg" and root.get("viewBox"), name
        for element in root.iter():
            # Shapes and a gradient: nothing that runs, loads or embeds.
            tag = element.tag.removeprefix(svg)
            assert tag in {"svg", "defs", "linearGradient", "stop", "g", "path"}, (name, tag)
            for attribute in element.attrib:
                assert not attribute.lower().startswith("on"), (name, attribute)
                assert "href" not in attribute.lower(), (name, attribute)


def test_every_page_stands_on_the_ground(m):
    guest = TestClient(m.app)
    student = signed_in(m, "SV-ART", "student")
    student.post(
        "/api/v1/me/consent",
        data={"audio_storage_allowed": "true", "research_use_allowed": "true"},
    )
    pages = [
        (guest, "/bands", "guest"),
        (student, "/practice", "student"),
        (student, "/my-responses", "student"),
        (student, "/my-progress", "student"),
        (student, "/account", "student"),
        (signed_in(m, "GV-ART", "teacher"), "/review", "teacher"),
        (signed_in(m, "QT-ART", "admin"), "/admin", "admin"),
    ]
    for client, url, role in pages:
        r = client.get(url)
        assert r.status_code == 200, url
        page = r.text
        assert page.count(GROUND) == 1, url
        ground = page[page.index(GROUND) : page.index("</div>", page.index(GROUND))]
        assert '<i class="ground-lines"></i><i class="ground-hills"></i>' in ground, url
        # Staff pages are quieter: the stylesheet keys that on the body's role.
        assert f'<body class="role-{role}' in page, url
    # The product and sign-in pages keep the lines and draw the hills themselves.
    for url in ("/", "/login"):
        page = guest.get(url).text
        assert page.count(GROUND) == 1 and "ground-hills" not in page, url


def test_the_product_and_sign_in_pages_carry_the_scene():
    from aicefr.api.main import app

    client = TestClient(app)
    for url, holder, cls in (
        ("/", "lp-hero", "lp-terraces"),
        ("/login", "auth-split", "auth-terraces"),
    ):
        page = client.get(url).text
        drawing = scene(page, cls)
        # Inside the part of the page it belongs to, before its words.
        opened = page.index(f'class="{holder}"')
        assert opened < page.index(drawing) < page.index("<h", opened + 1), url
        assert drawing.count('<i class="art-sun"></i>') == 1
        assert '<svg class="art-terraces"' in drawing
        assert 'preserveAspectRatio="none"' in drawing
        assert 'aria-hidden="true" focusable="false"' in drawing
        assert drawing.count('<g class="art-band b') == len(art.BANDS)
        assert drawing.count('<path class="art-wave" pathLength="1"') == len(art.BANDS)
        assert drawing.count('<path class="art-wall"') == len(art.BANDS) * art.STEPS
        # Drawn inline, sent with the page: nothing to fetch, focus or run.
        for absent in ("<a ", "<button", "<input", "tabindex", "<img", "<script", "url(", " on"):
            assert absent not in drawing, (url, absent)
        assert len(drawing.encode()) < 16_000, url


def test_the_art_is_served_as_svg_and_carried_in_the_wheel():
    from aicefr.api.main import app

    client = TestClient(app)
    for name in re.findall(r'url\("art/([\w-]+\.svg)"\)', CSS):
        assert (STATIC / "art" / name).is_file(), name
        r = client.get(f"/static/art/{name}")
        assert r.status_code == 200, name
        assert r.headers["content-type"].startswith("image/svg+xml"), name
    # Read as text: tomllib only arrives in Python 3.11, and the project still runs on 3.10.
    meta = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    data = meta[meta.index("[tool.setuptools.package-data]") :]
    data = data[: data.index("]", data.index("aicefr = ["))]
    assert '"api/static/art/*.svg"' in data
    assert '"api/templates/*.html"' in data  # _art.html, the scene's macro


def test_motion_plays_only_when_welcome():
    names = ("art-rise", "art-draw", "art-breathe", "art-sunrise")
    for name in names:
        assert f"@keyframes {name} " in CSS, name
        uses = [m.start() for m in re.finditer(rf"animation:[^;]*\b{name}\b", CSS)]
        assert uses, name
        for position in uses:
            assert enclosing_media(position) == "(prefers-reduced-motion: no-preference)", name
    # A ridge waits undrawn only where it is going to be drawn in.
    dashed = [m.start() for m in re.finditer(r"stroke-dasharray: 1;", CSS)]
    assert dashed
    for position in dashed:
        assert enclosing_media(position) == "(prefers-reduced-motion: no-preference)"


def test_the_art_stays_out_of_the_way():
    def body(selector: str) -> str:
        bodies = [b for _pos, b in rule_bodies(selector) if "pointer-events" in b]
        assert len(bodies) == 1, selector
        return bodies[0]

    for selector in (".ground {", ".auth-terraces {", ".empty-state::after"):
        assert "pointer-events: none" in body(selector.rstrip(" {")), selector
    assert "z-index: -1" in body(".ground")
    assert "position: fixed" in body(".ground")
    # The ground holds still while a view transition swaps the page in front of it.
    assert "view-transition-name: ground" in body(".ground")
    assert "::view-transition-old(ground) { display: none; }" in CSS
    assert "::view-transition-new(ground) { animation: none; }" in CSS
    # Nothing of it on paper.
    printed = [(pos, b) for pos, b in rule_bodies(".ground") if "display: none" in b]
    assert printed and all(enclosing_media(pos) == "print" for pos, _b in printed)
    rule = CSS[CSS.rindex("@media print") :]
    rule = rule[: rule.index("}")]
    for selector in (".ground", ".lp-terraces", ".auth-terraces", ".empty-state::after"):
        assert selector in rule, selector


def test_each_theme_colours_the_art():
    tokens = ("--art-ink", "--art-hills", "--art-lines", "--art-sun", "--art-sun-mix")
    light = CSS[
        CSS.index("/* ===================================================== 7. the ground") :
    ]
    light = light[light.index(":root {") : light.index("}", light.index(":root {"))]
    for token in (*tokens, "--art-strength"):
        assert f"{token}:" in light, token
    for guard in (':root:not([data-theme="light"]) {', ':root[data-theme="dark"] {'):
        dark = CSS[CSS.rindex(guard) :]
        dark = dark[: dark.index("}")]
        for token in tokens:
            assert f"{token}:" in dark, (guard, token)
    assert re.search(r"\.role-teacher,\s*\.role-admin \{ --art-strength: 0\.\d+; \}", CSS)
    assert "opacity: var(--art-strength);" in CSS
