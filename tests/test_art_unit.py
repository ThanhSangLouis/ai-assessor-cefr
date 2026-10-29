"""Layer 1 -- UNIT: the geometry of the background art (D037).

The art is drawn by `tools/make_art.py`, and what makes it a picture rather
than a scribble is held here: the curve passes through the points it is given,
every ridge and terrace wall stays inside the frame, a band's walls run below
its ridge and only the ridge speaks, the far bands are the high pale ones. The
last test keeps `docs/test/TEST_PLAN_D037.md` and the three test modules
naming the same cases (TC-ART-Uxx, -Ixx, -Exx).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("make_art", ROOT / "tools" / "make_art.py")
art = importlib.util.module_from_spec(_SPEC)
# Registered before it runs: a dataclass looks its own module up while it is built.
sys.modules[_SPEC.name] = art
_SPEC.loader.exec_module(art)

# Fine enough to land between the syllables as well as on them.
XS = [i / 2000 for i in range(2001)]


def endpoints(d: str) -> list[tuple[float, float]]:
    """The point each command of a path ends on: the last two numbers of it."""
    out = []
    for command in re.findall(r"[MCS][^MCS]*", d):
        numbers = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", command)]
        out.append((numbers[-2], numbers[-1]))
    return out


def test_the_curve_passes_through_every_point_it_was_given():
    points = [(0, 10), (20, 4), (40, 12), (60, 2), (80, 9), (100, 9)]
    d = art.curve(points)
    # One full cubic, then the shorthand for every smooth join after it.
    assert re.fullmatch(r"M[^MCS]+C[^MCS]+(S[^MCS]+){4}", d), d
    assert endpoints(d) == [(float(x), float(y)) for x, y in points]
    # Two decimals where they are asked for, and never a "-0".
    assert art.curve([(0, 0), (1.234, -0.001), (2, 1)], places=2).startswith("M0 0C")
    assert not re.search(r"-0(?![.\d])", art.curve([(0, -0.0001), (1, -0.2), (2, 0)]))


def test_every_ridge_and_wall_stays_inside_the_picture():
    for band in art.BANDS:
        for lower in range(art.STEPS + 1):
            ys = [art.ridge(band, x, lower) for x in XS]
            # Clear of the top, where a cropped or stretched frame would cut
            # it, and above the foot, where the band's fill closes.
            assert 0.1 < min(ys) and max(ys) < 1.0, (band.base, lower, min(ys), max(ys))


def test_the_walls_run_below_the_ridge_and_only_the_ridge_speaks():
    for band in art.BANDS:
        start, end, loudness, seed = band.phrase
        silent = replace(band, phrase=(start, end, 0.0, seed))
        spoken = art.syllables(start, end, seed)
        assert spoken and all(start < c <= end for c, _w, _a in spoken)
        for x in XS:
            top, *walls = (art.ridge(band, x, k) for k in range(art.STEPS + 1))
            assert top < walls[0] < walls[1]
            # The walls are the hill without the voice, wherever it speaks.
            assert walls == [art.ridge(silent, x, k) for k in range(1, art.STEPS + 1)]
            if x < start - 0.15 or x > end + 0.15:
                assert abs(top - art.ridge(silent, x)) < 1e-9
        # Each syllable lifts the ridge by at least its own loudness.
        for centre, _width, amplitude in spoken:
            lift = art.ridge(silent, centre) - art.ridge(band, centre)
            assert lift >= loudness * amplitude - 1e-12, (band.base, centre)
    # The same seed says the same phrase; another seed, another phrase.
    assert art.syllables(0.1, 0.5, 3) == art.syllables(0.1, 0.5, 3)
    assert art.syllables(0.1, 0.5, 3) != art.syllables(0.1, 0.5, 4)


def test_far_bands_sit_higher_and_paler_than_near_ones():
    bases = [band.base for band in art.BANDS]
    alphas = [band.alpha for band in art.BANDS]
    assert bases == sorted(bases) and len(set(bases)) == len(bases)
    assert alphas == sorted(alphas) and alphas[-1] == 1.0
    # Each band keeps its own seed, so no two ridges say the same phrase.
    assert len({band.phrase[3] for band in art.BANDS}) == len(art.BANDS)


PLAN = ROOT / "docs" / "test" / "TEST_PLAN_D037.md"
LAYERS = {
    "TC-ART-U": ROOT / "tests" / "test_art_unit.py",
    "TC-ART-I": ROOT / "tests" / "test_art.py",
    "TC-ART-E": ROOT / "tests" / "e2e" / "test_art_e2e.py",
}


def test_the_plan_and_the_code_name_the_same_cases():
    rows = re.findall(
        r"^\| (TC-ART-[UIE])(\d{2}) \| `(test_\w+)` \|", PLAN.read_text("utf-8"), re.M
    )
    assert rows
    ids = [prefix + number for prefix, number, _name in rows]
    assert len(ids) == len(set(ids)), "a case id is used twice"
    for prefix, path in LAYERS.items():
        planned = {name for p, _n, name in rows if p == prefix}
        code = set(re.findall(r"^def (test_\w+)\(", path.read_text("utf-8"), re.M))
        assert code - planned == set(), f"{path.name}: tests missing from the plan"
        assert planned - code == set(), f"{path.name}: planned tests missing from the code"
