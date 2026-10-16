"""How much teacher time the machine saves, measured rather than claimed (D041).

Three numbers, each with the count it rests on:

- **minutes per review with the machine**: from the moment a teacher opens a
  response for review (the review lock) to their decision on it;
- **minutes per rating without the machine**: the blind double rating of D030,
  where the rater hears the recording with no machine score in sight, from
  opening the sheet to submitting it. It is the same teacher work, done the
  old way, on the same kind of response;
- **the share the machine settles alone**: scored assessments whose machine
  result stood without a teacher, against all that reached a result.

A session open longer than IDLE_CAP_MINUTES is a teacher who walked away, not
one who worked that long; it is left out and counted as such. No figure is
reported from fewer than MIN_SAMPLES observations.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import datetime
from statistics import median

TEACHER_TIME_VERSION = "teacher-time-v1"
IDLE_CAP_MINUTES = 30.0
MIN_SAMPLES = 5


def _minutes(opened: str, decided: str) -> float:
    a = datetime.fromisoformat(opened.replace("Z", "+00:00"))
    b = datetime.fromisoformat(decided.replace("Z", "+00:00"))
    return max(0.0, (b - a).total_seconds() / 60)


def capped(minutes: Iterable[float]) -> tuple[list[float], int]:
    """The minutes within IDLE_CAP_MINUTES, and how many were left out as idle.

    The same cap on both sides of the comparison: a rater who left a sheet open
    over lunch is no more "rating for an hour" than a reviewer who did.
    """
    kept = [m for m in minutes if m <= IDLE_CAP_MINUTES]
    return kept, sum(1 for m in minutes if m > IDLE_CAP_MINUTES)


def session_minutes(sessions: Iterable[Mapping]) -> tuple[list[float], int]:
    """Minutes of each review that ended in a decision, and how many were idle.

    Only decisions: a review released without one (the teacher left the page)
    is not a review done, and closing an unscorable response is not a review
    with the machine's score -- there was none.
    """
    return capped(
        [
            _minutes(s["opened_at"], s["decided_at"])
            for s in sessions
            if s.get("decided_at") and s.get("action") == "decision"
        ]
    )


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95 % Wilson interval for a proportion; None for n = 0."""
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def _summary(values: list[float]) -> dict:
    return {
        "n": len(values),
        "median_minutes": round(median(values), 2) if len(values) >= MIN_SAMPLES else None,
    }


def kpi(
    review_minutes: list[float],
    idle_reviews: int,
    rating_minutes: list[float],
    settled_alone: int,
    reached_result: int,
    band_kept: int,
    band_decisions: int,
) -> dict:
    rating_minutes, idle_ratings = capped(rating_minutes)
    assisted, manual = _summary(review_minutes), _summary(rating_minutes)
    saved = None
    if assisted["median_minutes"] is not None and manual["median_minutes"]:
        saved = round(1 - assisted["median_minutes"] / manual["median_minutes"], 3)
    alone_ci = wilson(settled_alone, reached_result)
    kept_ci = wilson(band_kept, band_decisions)
    return {
        "version": TEACHER_TIME_VERSION,
        "min_samples": MIN_SAMPLES,
        "idle_cap_minutes": IDLE_CAP_MINUTES,
        "review_with_machine": {**assisted, "idle_left_out": idle_reviews},
        "rating_without_machine": {**manual, "idle_left_out": idle_ratings},
        "time_saved": saved,
        "settled_alone": {
            "k": settled_alone,
            "n": reached_result,
            "rate": round(settled_alone / reached_result, 4) if reached_result else None,
            "ci95": [round(v, 4) for v in alone_ci] if alone_ci else None,
        },
        "band_kept": {
            "k": band_kept,
            "n": band_decisions,
            "rate": round(band_kept / band_decisions, 4) if band_decisions else None,
            "ci95": [round(v, 4) for v in kept_ci] if kept_ci else None,
        },
    }
