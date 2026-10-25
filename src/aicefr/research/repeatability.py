"""How much the same recording's result moves from one run to the next (§2.2).

Named for what it is: **repeatability** in the sense of ISO 5725, the spread of
results when the same item is measured again under the same conditions -- not
a standard error of measurement, which is a statement about true scores and
needs several raters or items to estimate (HUONG_PHAT_TRIEN_TIEP §2.2).

Pure functions; `tools/repeatability_bench.py` runs the pipeline and calls them.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Run:
    """One run of the pipeline on one recording."""

    score: float | None  # overall 0-6; None when the run was not scored
    band: str | None
    hallucination: bool = False  # the repetition detector cut a loop out


def summarise(runs_by_file: dict[str, list[Run]]) -> dict:
    """sigma_r, band changes between runs, the widest spread, and what was left out.

    - `sigma_r`: square root of the mean within-file variance (sample variance,
      n - 1), over files with at least two scored runs. None when there are none.
    - `band_change_rate`: over every pair of scored runs of the same file, the
      share whose bands differ. None when there is no pair.
    - `largest_range` and `median_range`: max - min of a file's scores.
    """
    variances, ranges = [], []
    pairs = changed = runs = unscored = hallucinated = 0
    for file_runs in runs_by_file.values():
        runs += len(file_runs)
        unscored += sum(r.score is None for r in file_runs)
        hallucinated += sum(r.hallucination for r in file_runs)
        scored = [r for r in file_runs if r.score is not None]
        if len(scored) < 2:
            continue
        values = [r.score for r in scored]
        variances.append(statistics.variance(values))
        ranges.append(max(values) - min(values))
        for a, b in combinations(scored, 2):
            pairs += 1
            changed += a.band != b.band
    return {
        "files": len(runs_by_file),
        "runs": runs,
        "files_with_two_scores": len(variances),
        "unscored_runs": unscored,
        "hallucination_runs": hallucinated,
        "sigma_r": statistics.fmean(variances) ** 0.5 if variances else None,
        "band_change_rate": changed / pairs if pairs else None,
        "largest_range": max(ranges) if ranges else None,
        "median_range": statistics.median(ranges) if ranges else None,
    }
