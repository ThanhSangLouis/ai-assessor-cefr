"""Reliable change: call a rise progress only when it is larger than the instrument's error (D042).

Two recordings of the same learner differ even when nothing was learned: a
different day, a different topic, a different microphone, and the model's own
error. The standard error of measurement (SEM) puts a number on that spread,
and the reliable change index (Jacobson & Truax, 1991) asks whether a
difference is larger than two such errors would make by chance:

    RCI = (x2 − x1) / (√2 · SEM)            |RCI| > 1.96  →  reliable at 95 %

Comparing the mean of k1 early scores with the mean of k2 late ones, the
standard error of the difference is SEM · √(1/k1 + 1/k2).

The SEM comes from test–retest pairs: two scored responses of the same learner
on the same task, close enough in time that no real learning happened between
them. With d the differences, SEM = SD(d) / √2. Until there are MIN_PAIRS such
pairs, there is no SEM and no claim either way. The model's cross-validated
RMSE is not an SEM -- it measures error against human labels, not the spread of
one learner's repeated scores -- and is not used here.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta

RELIABLE_CHANGE_VERSION = "rci-v1"
MIN_PAIRS = 10
RETEST_WINDOW = timedelta(hours=48)
Z_95 = 1.96
WINDOW_SCORES = 3  # scores averaged at each end of a learner's series


def _when(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def retest_pairs(
    rows: Iterable[Mapping], window: timedelta = RETEST_WINDOW
) -> list[tuple[float, float]]:
    """Consecutive scores of one learner on one task within `window` of each other.

    `rows`: scored assessment responses with `account_id`, `task_id`,
    `overall_0_6` and `created_at`. Each response is used in at most one pair,
    so a learner who recorded five times in a day does not count four times.
    """
    by_key: dict[tuple[str, str, str | None], list[tuple[datetime, float]]] = {}
    for r in rows:
        if r.get("overall_0_6") is None or not r.get("account_id"):
            continue
        # One learner, one task, one scoring model: a pair across two models
        # measures the change of model, not the noise of the instrument.
        by_key.setdefault((r["account_id"], r["task_id"], r.get("model_version")), []).append(
            (_when(r["created_at"]), float(r["overall_0_6"]))
        )
    pairs: list[tuple[float, float]] = []
    for series in by_key.values():
        series.sort()
        i = 0
        while i + 1 < len(series):
            (t1, s1), (t2, s2) = series[i], series[i + 1]
            if t2 - t1 <= window:
                pairs.append((s1, s2))
                i += 2
            else:
                i += 1
    return pairs


def sem_from_pairs(pairs: list[tuple[float, float]]) -> float | None:
    """SD of the differences over √2; None below MIN_PAIRS pairs."""
    if len(pairs) < MIN_PAIRS:
        return None
    diffs = [b - a for a, b in pairs]
    mean = sum(diffs) / len(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1)
    return math.sqrt(var) / math.sqrt(2)


def reliable_change(scores: list[float], sem: float | None) -> dict:
    """Early against late scores of one learner, against the measurement error.

    Verdicts: `tien_bo` (reliably higher), `giam` (reliably lower),
    `chua_vuot_sai_so` (inside the error), `chua_du_du_lieu` (fewer than two
    scores) and `chua_co_sai_so` (no SEM measured yet).
    """
    base = {"version": RELIABLE_CHANGE_VERSION, "sem": sem, "baseline": None, "latest": None,
            "difference": None, "threshold": None, "rci": None}  # fmt: skip
    if len(scores) < 2:
        return {**base, "verdict": "chua_du_du_lieu"}
    k = max(1, min(WINDOW_SCORES, len(scores) // 2))
    early, late = scores[:k], scores[-k:]
    baseline, latest = sum(early) / k, sum(late) / k
    diff = latest - baseline
    out = {**base, "baseline": round(baseline, 3), "latest": round(latest, 3),
           "difference": round(diff, 3), "k": k}  # fmt: skip
    if not sem:
        return {**out, "verdict": "chua_co_sai_so"}
    se = sem * math.sqrt(2 / k)
    threshold = Z_95 * se
    rci = diff / se
    verdict = "tien_bo" if rci > Z_95 else "giam" if rci < -Z_95 else "chua_vuot_sai_so"
    return {**out, "threshold": round(threshold, 3), "rci": round(rci, 2), "verdict": verdict}
