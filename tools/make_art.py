"""Draw the background art of every page (D037): "terraces of speech".

Terraced hills -- the image of patient, step-by-step work every Vietnamese
student knows from the rice terraces -- whose ridges are the loudness envelopes
of spoken phrases: a hill for the climb from A2 to B2, a ripple per syllable for
the speaking. Three pieces come out of the same geometry:

* ``static/art/hills.svg``: the hills, four bands from far to near, used as a
  CSS mask behind every page and every empty state. A mask has no colour of its
  own: each band carries an alpha, so one colour from the theme gives four
  tones, in the light theme and the dark one alike;
* ``static/art/contours.svg``: contour lines that are slower waves of the same
  kind, fading toward the left, also a mask;
* ``templates/_art.html``: the hero scene of the product and sign-in pages,
  inline so the stylesheet can colour each band and draw each ridge in.

Deterministic: the same code writes the same bytes, and ``tests/test_art.py``
fails when the committed files differ from what this writes. After changing
it, run from the repository root::

    python tools/make_art.py
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "src" / "aicefr" / "api" / "static" / "art"
TEMPLATES = ROOT / "src" / "aicefr" / "api" / "templates"


@dataclass(frozen=True)
class Band:
    """One terrace, from the ridge down to the foot of the picture."""

    base: float  # where the ridge sits where the hill is flat, 0..1 of the height
    humps: tuple[tuple[float, float, float], ...]  # (centre, width, height), x and h in 0..1
    phrase: tuple[float, float, float, int]  # where the phrase is spoken, its loudness, seed
    alpha: float  # its tone in the mask: far bands fade into the sky


# Far to near. The far bands are higher and paler, the near ones lower and
# darker; the phrases sit where each ridge is long enough to carry them.
BANDS = (
    Band(0.52, ((0.72, 0.22, 0.31), (0.24, 0.30, 0.12)), (0.50, 0.93, 0.018, 3), 0.30),
    Band(0.66, ((0.30, 0.20, 0.25), (0.88, 0.18, 0.19)), (0.10, 0.48, 0.023, 7), 0.50),
    Band(0.79, ((0.58, 0.24, 0.20),), (0.38, 0.80, 0.026, 11), 0.72),
    Band(0.92, ((0.12, 0.20, 0.15), (0.80, 0.26, 0.17)), (0.58, 0.98, 0.030, 5), 1.0),
)
STEPS = 2  # terrace walls drawn inside each band, below its ridge
COARSE = 20  # points along a curve where it only carries the hill
FINE = 0.0075  # spacing where it carries a phrase: a few points per syllable


def syllables(start: float, end: float, seed: int) -> list[tuple[float, float, float]]:
    """A spoken phrase as syllables: (centre, width, loudness), louder in the middle."""
    rnd = random.Random(seed)
    out = []
    x = start
    while x < end:
        width = rnd.uniform(0.016, 0.03)
        centre = x + width
        if centre > end:
            break
        middle = 1 - abs((centre - start) / (end - start) * 2 - 1)
        out.append((centre, width, rnd.uniform(0.45, 1.0) * (0.55 + 0.45 * middle)))
        x = centre + width * rnd.uniform(0.9, 1.6)
    return out


def ridge(band: Band, x: float, lower: int = 0) -> float:
    """Height of the band's top edge at x, as a fraction of the picture (0 top, 1 foot).

    `lower` > 0 gives a terrace wall below the ridge: further down, with the hill
    a little flatter so the walls fan out the way terrace walls do, and without
    the phrase -- only the ridge speaks.
    """
    flatten = 1 - 0.13 * lower
    hill = sum(h * math.exp(-(((x - c) / w) ** 2)) for c, w, h in band.humps) * flatten
    if lower:
        return band.base - hill + lower * (0.022 + 0.006 * lower)
    start, end, loudness, seed = band.phrase
    voice = sum(a * math.exp(-(((x - c) / w) ** 2)) for c, w, a in syllables(start, end, seed))
    return band.base - hill - loudness * voice


def number(v: float, places: int) -> str:
    text = f"{v:.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def curve(points: list[tuple[float, float]], places: int = 0) -> str:
    """A smooth open path through the points: Catmull-Rom, written as cubic Béziers.

    A Catmull-Rom curve is smooth at every point, so each segment's first
    control point mirrors the previous segment's second one: after the first
    segment, SVG's `S` command says the same with one point less.
    """

    def pt(p):
        return f"{number(p[0], places)} {number(p[1], places)}"

    d = [f"M{pt(points[0])}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else points[i + 1]
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        if i:
            d.append(f"S{pt(c2)} {pt(p2)}")
        else:
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            d.append(f"C{pt(c1)} {pt(c2)} {pt(p2)}")
    return "".join(d)


def stations(spoken: tuple[float, float] | None = None, fine: float = FINE) -> list[float]:
    """Where to sample a curve: evenly for the hill, closely where a phrase is spoken."""
    xs = {round(i / (COARSE - 1), 4) for i in range(COARSE)}
    if spoken:
        start, end = max(0.0, spoken[0] - 0.02), min(1.0, spoken[1] + 0.02)
        steps = int((end - start) / fine)
        xs |= {round(start + i * (end - start) / steps, 4) for i in range(steps + 1)}
    return sorted(xs)


def sample(fn, width: float, height: float, xs: list[float]) -> list[tuple[float, float]]:
    return [(x * width, fn(x) * height) for x in xs]


def band_paths(width: float, height: float, places: int) -> list[tuple[str, list[str], str]]:
    """For each band: its filled shape, its terrace walls, and its ridge as an open curve."""
    out = []
    for band in BANDS:
        xs = stations(band.phrase[:2])
        top = curve(sample(lambda x, b=band: ridge(b, x), width, height, xs), places)
        fill = f"{top}V{number(height, places)}H0Z"
        walls = [
            curve(sample(lambda x, b=band, k=k: ridge(b, x, k), width, height, stations()), places)
            for k in range(1, STEPS + 1)
        ]
        out.append((fill, walls, top))
    return out


HEADER = "<!-- Drawn by tools/make_art.py (D037). Edit the script, not this file. -->\n"


def hills_svg() -> str:
    """The mask behind every page: bands as tones, walls as darker grooves."""
    width, height = 1200, 480
    parts = [
        HEADER,
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'preserveAspectRatio="none">\n',
    ]
    for (fill, walls, _top), band in zip(band_paths(width, height, 0), BANDS, strict=True):
        parts.append(f'<path fill-opacity="{number(band.alpha, 2)}" d="{fill}"/>\n')
        for wall in walls:
            parts.append(
                f'<path fill="none" stroke="#000" stroke-opacity="{number(band.alpha * 0.55, 2)}"'
                f' stroke-width="1.6" d="{wall}"/>\n'
            )
    parts.append("</svg>\n")
    return "".join(parts)


def contours_svg() -> str:
    """Contour lines, slower waves of the same kind, fading out toward the left."""
    width, height = 900, 560
    lines = 8
    parts = [
        HEADER,
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'preserveAspectRatio="none">\n',
        '<defs><linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" '
        f'x2="{width}" y2="0"><stop offset="0" stop-opacity="0"/>'
        '<stop offset="0.55" stop-opacity="0.7"/><stop offset="1" stop-opacity="1"/>'
        "</linearGradient></defs>\n",
        '<g fill="none" stroke="url(#fade)" stroke-width="1.3">\n',
    ]
    for i in range(lines):
        spoken = syllables(0.40, 0.96, 20 + i)
        fade = 1 - i / lines

        def y(x, i=i, spoken=spoken, fade=fade):
            swell = 0.024 * math.sin(2 * math.pi * (0.9 * x + 0.11 * i)) * fade
            voice = sum(a * math.exp(-(((x - c) / w) ** 2)) for c, w, a in spoken)
            return (34 + 64 * i) / height + swell - 0.018 * fade * voice

        path = curve(sample(y, width, height, stations((0.40, 0.96), fine=0.014)))
        parts.append(f'<path stroke-opacity="{number(1 - 0.07 * i, 2)}" d="{path}"/>\n')
    parts.append("</g>\n</svg>\n")
    return "".join(parts)


def hero_template() -> str:
    """The product and sign-in pages' scene: the same hills, each band its own colour.

    Each ridge is drawn twice: once as the top of its band, once as a line
    (`pathLength="1"`) the stylesheet draws in.

    The hills stretch to whatever box holds them (`preserveAspectRatio="none"`):
    cropping instead would cut the far hill flat along the top on a wide
    screen. A stretched circle would be an egg, so the sun is not in the
    drawing: it is the element before it, round by CSS, behind the hills.
    """
    width, height = 1440, 400
    bands = band_paths(width, height, 0)
    out = [
        "{#- Drawn by tools/make_art.py (D037). Edit the script, not this file.\n"
        "    Decoration: hidden from screen readers, nothing is said only here. -#}\n",
        '{% macro terraces(cls="art-terraces") -%}\n',
        '<i class="art-sun"></i>',
        f'<svg class="{{{{ cls }}}}" viewBox="0 0 {width} {height}" '
        'preserveAspectRatio="none" aria-hidden="true" focusable="false">',
    ]
    # Each ridge line sits in its own band's group: a nearer band hides it where
    # a nearer hill rises in front, and it breathes with its band.
    for k, (fill, walls, top) in enumerate(bands):
        out.append(f'<g class="art-band b{k}"><path class="art-fill" d="{fill}"/>')
        out.extend(f'<path class="art-wall" d="{wall}"/>' for wall in walls)
        out.append(f'<path class="art-wave" pathLength="1" d="{top}"/></g>')
    out.append("</svg>\n{%- endmacro %}\n")
    return "".join(out)


OUTPUTS = {
    ART / "hills.svg": hills_svg,
    ART / "contours.svg": contours_svg,
    TEMPLATES / "_art.html": hero_template,
}


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    for path, draw in OUTPUTS.items():
        path.write_text(draw(), encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
