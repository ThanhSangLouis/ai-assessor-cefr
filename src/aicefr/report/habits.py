"""How the learner's speaking habits moved across their assessments (D070).

The same measurements the next-band targets are read from (`next_band.LEVERS`),
one line per habit over time, so a learner who was asked for "from 9 stops a
minute to 6" can see whether it happened.

The care is the same as for the overall score (FR-27, D042): one recording is
one day and one task, so a single point says little. The movement is named
only from MIN_POINTS assessments on, as the mean of the latest third against
the first third, and the screen calls it a direction, never progress.
"""

from __future__ import annotations

from aicefr.report.next_band import LEVERS

# The habits shown, and which way is better. Fixed rather than read from the
# scoring model's coefficients: the advice must not flip with a retrained model.
BETTER = {
    "words_per_sec": "up",
    "vad_pause_per_min": "down",
    "vad_long_pause_ratio": "down",
    "log_uniq": "up",
}
NAMES = tuple(BETTER)
MIN_POINTS = 3


def habit_series(rows: list[dict]) -> list[dict]:
    """One entry per habit with its points; rows come from `feature_series`, oldest first."""
    out = []
    for name, better in BETTER.items():
        lever = LEVERS[name]
        points = [
            {
                "at": r["created_at"],
                "response_id": r["response_id"],
                "value": round(lever.shown(r["values"][name]), lever.digits),
            }
            for r in rows
            if name in r["values"]
        ]
        out.append(
            {
                "feature": name,
                "label": lever.label,
                "unit": lever.unit,
                "better": better,
                "points": points,
                "movement": _movement([p["value"] for p in points], better),
            }
        )
    return out


def _movement(values: list[float], better: str) -> dict | None:
    """First third against last third; None below MIN_POINTS."""
    if len(values) < MIN_POINTS:
        return None
    cut = max(1, len(values) // 3)
    first = sum(values[:cut]) / cut
    last = sum(values[-cut:]) / cut
    delta = last - first
    went = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {
        "first": round(first, 1),
        "last": round(last, 1),
        "delta": round(delta, 1),
        "toward_better": went == better,
        "n": cut,
    }
