"""From a 0-6 score to a CEFR band, A1 to C2 (D059).

The scorer has ONE output, an overall estimate on the 0-6 scale of the
training labels. Six bands need five boundaries on that scale. The two the
model was fitted around (A2/B1, B1/B2) come from its artifact -- the
calibrated variant (D052) moves them -- and the other three continue the same
half-point convention: a band is the score of its level give or take a half.

The outer boundaries are not calibrated. The training data hold few responses
below A2 or above C1, so the model's estimates there are the least reliable it
gives; the conformal interval (D022) widens accordingly and sends those
responses to a teacher more often. The report keeps its "not calibrated"
warning for every band.
"""

from __future__ import annotations

import math

from aicefr.contracts import Band

BAND_MAP_VERSION = "band-v2-a1-c2"

# Boundary names, in order: the band below and the band above.
BOUNDARIES: tuple[str, ...] = ("A1_A2", "A2_B1", "B1_B2", "B2_C1", "C1_C2")

DEFAULT_THRESHOLDS: dict[str, float] = {
    "A1_A2": 1.75,
    "A2_B1": 2.75,
    "B1_B2": 3.75,
    "B2_C1": 4.75,
    "C1_C2": 5.75,
}


def thresholds_of(model_thresholds: dict[str, float] | None) -> dict[str, float]:
    """All five boundaries: the model's own where it has them, the defaults elsewhere."""
    merged = {**DEFAULT_THRESHOLDS, **(model_thresholds or {})}
    values = [merged[name] for name in BOUNDARIES]
    if values != sorted(values) or len(set(values)) != len(values):
        raise ValueError(f"ngưỡng band phải tăng dần: {values}")
    return {name: merged[name] for name in BOUNDARIES}


def band_spans(thresholds: dict[str, float]) -> list[tuple[Band, float, float]]:
    """Each band with the half-open score range [low, high) it covers."""
    th = thresholds_of(thresholds)
    edges = [-math.inf, *(th[name] for name in BOUNDARIES), math.inf]
    return [(band, edges[i], edges[i + 1]) for i, band in enumerate(Band)]


def to_band(score: float, thresholds: dict[str, float]) -> Band:
    for band, _low, high in band_spans(thresholds):
        if score < high:
            return band
    return Band.C2


def near_boundary(score: float, thresholds: dict[str, float], margin: float) -> bool:
    """A score close to the boundary between two bands should go to a teacher."""
    return any(abs(score - t) <= margin for t in thresholds_of(thresholds).values())


def bands_between(low: float, high: float, thresholds: dict[str, float]) -> list[Band]:
    """Every band with a part inside [low, high], from A1 to C2."""
    return [b for b, lo, hi in band_spans(thresholds) if low < hi and high >= lo]
