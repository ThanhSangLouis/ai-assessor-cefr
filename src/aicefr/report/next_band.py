"""What to change, in numbers the learner can check, to reach the next band (D069).

The scoring model is linear: every feature moves the score by `coef * z`, with
z = (value - mean) / scale. So for the few features a speaker can act on --
how fast they speak, how often and how long they stop, how many different
words they use, how much they say -- the model itself says how far each one
would have to move to close the gap to the next band's threshold.

What this is, and is not:

* targets are relative to THIS recording: "from 9 stops a minute to 6", never
  "a B2 speaker stops 6 times a minute" -- the second would publish averages
  of the training corpus, which its licence does not allow;
* a target never leaves the range the model was trained on; when even the edge
  of that range does not close the gap, the plan says so instead of inventing
  a bigger number;
* the features move together in real speech (talk longer and you use more
  different words), so the gain is an estimate of direction, not a promise.
  The teacher still decides the band.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from aicefr.contracts import FeatureSet
from aicefr.scoring.band_map import thresholds_of

# Features a learner can change on purpose, how to say them, and how to turn a
# feature value into the number shown.


@dataclass(frozen=True)
class Lever:
    label: str
    unit: str
    shown: Callable[[float], float]  # feature value -> number on screen
    digits: int = 0


LEVERS: dict[str, Lever] = {
    "words_per_sec": Lever("Tốc độ nói", "từ/phút", lambda v: v * 60),
    "vad_pause_per_min": Lever("Số lần ngừng", "lần/phút", lambda v: v, 1),
    "vad_long_pause_ratio": Lever("Chỗ ngừng dài hơn 1 giây", "% số lần ngừng", lambda v: v * 100),
    "log_uniq": Lever("Số từ khác nhau", "từ", lambda v: math.exp(v) - 1),
    "n_words": Lever("Số từ nói được", "từ", lambda v: v),
}

MAX_TARGETS = 3
# How far one recording is asked to move a habit, in standard deviations.
MAX_STEP_SD = 1.0
# Close the gap with a little to spare: a score exactly on a threshold is the
# least certain place on the scale.
MARGIN = 0.05


def next_band_plan(model: dict, features: FeatureSet, score: float | None) -> dict | None:
    """The next band and up to three targets to reach it; None at C2 or without a score."""
    if score is None:
        return None
    thresholds = thresholds_of(model.get("band_thresholds"))
    above = [(name, value) for name, value in thresholds.items() if value > score]
    if not above:
        return None
    boundary, threshold = min(above, key=lambda x: x[1])
    gap = threshold - score + MARGIN

    order = model["feature_order"]
    rows = []
    for name, lever in LEVERS.items():
        if name not in order:
            continue
        i = order.index(name)
        coef, mean, scale = model["coef"][i], model["mean"][i], model["scale"][i]
        value = features.value_of(name)
        if value is None or coef == 0 or scale <= 0:
            continue
        lo, hi = model["feature_lo"][i], model["feature_hi"][i]
        rows.append((coef * (value - mean) / scale, name, lever, coef, scale, value, lo, hi))
    if not rows:
        return None

    # Where the recording loses the most points first.
    rows.sort(key=lambda r: r[0])
    chosen = rows[:MAX_TARGETS]
    # Every chosen feature moves by the same number of standard deviations, the
    # smallest that closes the gap: no single habit carries the whole change.
    # One recording asks for at most one standard deviation each; past that,
    # the plan is a direction for the next few recordings.
    step = min(gap / sum(abs(r[3]) for r in chosen), MAX_STEP_SD)
    targets, gained = [], 0.0
    for _, name, lever, coef, scale, value, lo, hi in chosen:
        wanted = value + math.copysign(step, coef) * scale
        target = min(max(wanted, lo), hi)
        if abs(target - value) < 1e-9:
            continue
        gained += coef * (target - value) / scale
        now, then = lever.shown(value), lever.shown(target)
        targets.append(
            {
                "feature": name,
                "label": lever.label,
                "unit": lever.unit,
                "now": round(now, lever.digits),
                "target": round(then, lever.digits),
                "direction": "up" if then > now else "down",
            }
        )
    if not targets:
        return None
    lower, upper = boundary.split("_")
    return {
        "from_band": lower,
        "to_band": upper,
        "threshold": round(threshold, 2),
        "gap": round(threshold - score, 2),
        "targets": targets,
        # Whether the targets together close the gap, in the model's own terms.
        "enough": gained >= threshold - score,
        "boundary": boundary,
    }
