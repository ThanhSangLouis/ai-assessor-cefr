"""Inter-rater agreement for the blind double rating of the field study.

Why this module exists. The study compares the machine with human raters
(docs/plan/KE_HOACH_KHAO_SAT.md, sections 6-7), and that comparison means
nothing unless the humans first agree with each other. So the report puts
human-human agreement BEFORE machine-human agreement, and every metric says how
many responses it rests on.

What it takes from the protocol:

* two raters score every response blind; a third rater adjudicates when the
  overall scores differ by 1.0 or more, the bands differ, or exactly one of the
  two found the response unscorable (`needs_adjudication`);
* the machine is compared with the mean of the two ratings, or with the median
  of three after adjudication (`reference`); a response still waiting for its
  third rating is "pending" and stays out of every machine-human metric;
* confidence intervals resample SPEAKERS, not responses
  (`cluster_bootstrap_ci`): the two responses of one student are not
  independent, and resampling them one by one gives an interval narrower than
  the evidence allows.

Pure functions on plain values, numpy only. A metric that is undefined, or has
too few items to mean anything, is None: never NaN, never a placeholder number.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

import numpy as np

BANDS: tuple[str, ...] = ("A2", "B1", "B2")
CRITERIA: tuple[str, ...] = ("range", "accuracy", "fluency", "coherence", "phonology")
ADJUDICATION_GAP = 1.0
SCORE_MIN, SCORE_MAX = 0.0, 6.0
DEFAULT_N_BOOT = 2000
DEFAULT_SEED = 20261007
MIN_CLUSTERS = 3

# A gap of exactly 1.0 must trigger adjudication even when the subtraction comes
# out just short of it (4.1 - 3.1 gives 0.9999999999999996).
_GAP_TOLERANCE = 1e-9

T = TypeVar("T")


def _check_score(value: float, what: str) -> None:
    if not (math.isfinite(value) and SCORE_MIN <= value <= SCORE_MAX):
        raise ValueError(f"{what} must be within {SCORE_MIN}-{SCORE_MAX}, got {value!r}")


@dataclass(frozen=True)
class Rating:
    """One rater's judgement of one response, as the rating form records it (appendix B).

    Scorable: an overall score and a band, plus criterion scores, all on 0-6.
    Unscorable (broken recording, inaudible, off task): no score of any kind.
    """

    rater_id: str
    overall: float | None
    band: str | None
    criteria: dict[str, float | None]  # keys from CRITERIA; may be empty when unscorable
    unscorable: bool = False
    adjudication: bool = False  # True only for the third (adjudicating) rating

    def __post_init__(self) -> None:
        who = f"rating by {self.rater_id!r}"
        if self.unscorable:
            if self.overall is not None or self.band is not None:
                raise ValueError(f"{who} is unscorable but has an overall score or a band")
            if any(value is not None for value in self.criteria.values()):
                raise ValueError(f"{who} is unscorable but has criterion scores")
        elif self.overall is None or self.band is None:
            raise ValueError(f"{who} needs an overall score and a band, or unscorable=True")
        if self.band is not None and self.band not in BANDS:
            raise ValueError(f"{who}: unknown band {self.band!r}, expected one of {BANDS}")
        unknown = sorted(set(self.criteria) - set(CRITERIA))
        if unknown:
            raise ValueError(f"{who}: unknown criteria {unknown}, expected keys from {CRITERIA}")
        for name, value in [("overall", self.overall), *self.criteria.items()]:
            if value is not None:
                _check_score(value, f"{who}: {name}")


@dataclass(frozen=True)
class RatedResponse:
    """One spoken response with its human ratings and what the machine made of it."""

    response_id: str
    speaker_id: str  # cluster unit for the bootstrap
    ratings: tuple[Rating, ...]  # the two primary ratings in slot order, then the adjudication
    ai_overall: float | None = None
    ai_band: str | None = None
    flagged: bool | None = None  # True when the machine routed it to teacher review

    def __post_init__(self) -> None:
        who = f"response {self.response_id!r}"
        object.__setattr__(self, "ratings", tuple(self.ratings))
        if len(self.ratings) > 3:
            raise ValueError(f"{who}: at most two primary ratings and one adjudication")
        for slot, rating in enumerate(self.ratings):
            if rating.adjudication != (slot == 2):
                raise ValueError(
                    f"{who}: the third rating, and only the third, is the adjudication"
                )
        raters = [rating.rater_id for rating in self.ratings]
        if len(set(raters)) != len(raters):
            # Two ratings by one person are not two independent judgements.
            raise ValueError(f"{who}: the same rater appears twice")
        if self.ai_band is not None and self.ai_band not in BANDS:
            raise ValueError(f"{who}: unknown machine band {self.ai_band!r}")
        if self.ai_overall is not None:
            _check_score(self.ai_overall, f"{who}: machine overall")


# ------------------------------------------------------------------ statistics


def confusion(
    a: Sequence[str | int | float],
    b: Sequence[str | int | float],
    categories: Sequence[str | int | float],
) -> list[list[int]]:
    """Counts of the pairs (a[i], b[i]): rows follow `a`, columns follow `b`, in category order."""
    if len(a) != len(b):
        raise ValueError(f"the two sequences differ in length ({len(a)} != {len(b)})")
    index = {category: i for i, category in enumerate(categories)}
    if len(index) != len(categories):
        raise ValueError(f"duplicate categories in {tuple(categories)}")
    matrix = [[0] * len(categories) for _ in categories]
    for x, y in zip(a, b, strict=True):
        for value in (x, y):
            if value not in index:
                raise ValueError(f"{value!r} is not one of {tuple(categories)}")
        matrix[index[x]][index[y]] += 1
    return matrix


def quadratic_weighted_kappa(
    a: Sequence[str | int | float],
    b: Sequence[str | int | float],
    categories: Sequence[str | int | float],
) -> float | None:
    """Cohen's kappa with quadratic weights over the ordered `categories`.

    None with fewer than two pairs, or when kappa is undefined: the expected
    disagreement is zero because both sides used one and the same category.
    """
    observed = np.array(confusion(a, b, categories), dtype=float)
    n = observed.sum()
    if n < 2:
        return None
    # Weights are not divided by (k - 1)^2: the factor cancels in the ratio.
    position = np.arange(len(categories))
    weights = (position[:, None] - position[None, :]) ** 2
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / n
    disagreement = (weights * expected).sum()
    if disagreement == 0:
        return None
    return float(1.0 - (weights * observed).sum() / disagreement)


def half_point_categories() -> tuple[float, ...]:
    """0.0, 0.5, ..., 6.0: the categories for kappa on 0-6 scores rounded to half points."""
    return tuple(step / 2 for step in range(int(SCORE_MAX * 2) + 1))


def _half_point(score: float) -> float:
    # Ties go up. Python's round() is banker's rounding: 3.25 would go down to
    # 3.0 while 3.75 goes up to 4.0, an asymmetry that means nothing here.
    return math.floor(score * 2 + 0.5) / 2


def _paired(x: Sequence[float], y: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if xs.ndim != 1 or xs.shape != ys.shape:
        raise ValueError(f"expected two flat sequences of equal length, got {xs.shape}, {ys.shape}")
    if not (np.isfinite(xs).all() and np.isfinite(ys).all()):
        raise ValueError("scores contain a missing or non-finite value; filter them out first")
    return xs, ys


def pearson(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Pearson correlation; None with fewer than three pairs or when one side is constant.

    Two points always correlate at +1 or -1, so three is the least that says anything.
    """
    xs, ys = _paired(x, y)
    if len(xs) < 3 or np.ptp(xs) == 0 or np.ptp(ys) == 0:
        return None
    dx, dy = xs - xs.mean(), ys - ys.mean()
    r = float((dx * dy).sum() / math.sqrt((dx * dx).sum() * (dy * dy).sum()))
    return max(-1.0, min(1.0, r))


def rmse(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Root mean squared difference between paired scores; None without pairs."""
    xs, ys = _paired(x, y)
    if len(xs) == 0:
        return None
    return math.sqrt(float(((xs - ys) ** 2).mean()))


def _complete_matrix(matrix: Sequence[Sequence[float]]) -> np.ndarray | None:
    m = np.asarray(matrix, dtype=float)
    if m.size == 0:
        return None
    if m.ndim != 2:
        raise ValueError("expected an n x k matrix: rows are responses, columns are raters")
    if not np.isfinite(m).all():
        raise ValueError("the matrix has a missing or non-finite cell; ICC needs complete rows")
    if m.shape[0] < 2 or m.shape[1] < 2:
        return None
    return m


def _ratio(numerator: float, denominator: float) -> float | None:
    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        return None
    return float(numerator / denominator)


def icc_2_1(matrix: Sequence[Sequence[float]]) -> float | None:
    """Shrout & Fleiss (1979) ICC(2,1): two-way random effects, absolute agreement, one rater.

    Rows are responses and columns raters, with the SAME rater in a column on
    every row: the model crosses raters with responses, so a rater who scores
    everyone half a point higher lowers it. No missing cells. None with fewer
    than two rows or columns, or when undefined.
    """
    m = _complete_matrix(matrix)
    if m is None:
        return None
    n, k = m.shape
    grand = m.mean()
    row_means, col_means = m.mean(axis=1), m.mean(axis=0)
    ms_rows = k * ((row_means - grand) ** 2).sum() / (n - 1)
    ms_cols = n * ((col_means - grand) ** 2).sum() / (k - 1)
    residual = m - row_means[:, None] - col_means[None, :] + grand
    ms_error = (residual**2).sum() / ((n - 1) * (k - 1))
    return _ratio(ms_rows - ms_error, ms_rows + (k - 1) * ms_error + k * (ms_cols - ms_error) / n)


def icc_1_1(matrix: Sequence[Sequence[float]]) -> float | None:
    """Shrout & Fleiss (1979) ICC(1,1): one-way random effects, one rater.

    For designs where each response may have its own raters, so a column is
    not one person. Rows are responses, no missing cells. None with fewer than
    two rows or columns, or when undefined.
    """
    m = _complete_matrix(matrix)
    if m is None:
        return None
    n, k = m.shape
    row_means = m.mean(axis=1)
    ms_rows = k * ((row_means - m.mean()) ** 2).sum() / (n - 1)
    ms_within = ((m - row_means[:, None]) ** 2).sum() / (n * (k - 1))
    return _ratio(ms_rows - ms_within, ms_rows + (k - 1) * ms_within)


def per_band(reference: Sequence[str], predicted: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Support, recall and precision of each band, `predicted` judged against `reference`.

    Recall is None for a band no reference response has; precision is None for
    a band that was never predicted.
    """
    matrix = confusion(reference, predicted, BANDS)
    out: dict[str, dict[str, Any]] = {}
    for i, band in enumerate(BANDS):
        support = sum(matrix[i])
        predicted_as = sum(row[i] for row in matrix)
        hits = matrix[i][i]
        out[band] = {
            "support": support,
            "recall": hits / support if support else None,
            "precision": hits / predicted_as if predicted_as else None,
        }
    return out


# -------------------------------------------------------------------- protocol


def needs_adjudication(first: Rating, second: Rating) -> bool:
    """Whether a third rater must adjudicate between the two primary ratings (section 6.4).

    Yes when the overall scores differ by ADJUDICATION_GAP or more, the bands
    differ, or exactly one of the two found the response unscorable. Two
    unscorable ratings agree with each other: the response is unscorable and
    no third rater is needed.
    """
    if first.unscorable or second.unscorable:
        return first.unscorable != second.unscorable
    gap = abs(first.overall - second.overall)
    return gap >= ADJUDICATION_GAP - _GAP_TOLERANCE or first.band != second.band


def reference(item: RatedResponse) -> tuple[float | None, str | None, str]:
    """The human score the machine is compared with: (score, band, kind).

    `kind` says where the reference comes from, which section 6.5 asks the
    report to state:

    * "mean_of_two" -- no adjudication needed: the mean of the two overall
      scores, and the band both raters gave;
    * "median_of_three" -- adjudicated: the median of the three overall scores
      and the ordinal median of the three bands (A2 < B1 < B2);
    * "pending" -- adjudication needed, the third rating is not in yet;
    * "unscorable" -- both primary raters found the response unscorable, or
      fewer than two of the three ratings are scorable after adjudication;
    * "incomplete" -- fewer than two primary ratings so far.

    Score and band are None for the last three kinds.

    Two scorable ratings out of three (one rater found the response
    unscorable): the score is their mean, which is also their median, and the
    band is the band of the rater whose score is closest to that mean, ties to
    the lower band. Both scores are always equally far from their mean, so
    this is the lower of the two bands: the reference band is never higher
    than either rater's.

    A third rating on a response that did not need one is ignored: section 6.5
    uses the mean of two for every response that needs no adjudication.
    """
    if len(item.ratings) < 2:
        return None, None, "incomplete"
    first, second = item.ratings[0], item.ratings[1]
    if first.unscorable and second.unscorable:
        return None, None, "unscorable"
    if not needs_adjudication(first, second):
        return (first.overall + second.overall) / 2, first.band, "mean_of_two"
    if len(item.ratings) < 3:
        return None, None, "pending"
    scorable = [rating for rating in item.ratings if not rating.unscorable]
    if len(scorable) < 2:
        return None, None, "unscorable"
    scores = sorted(rating.overall for rating in scorable)
    bands = sorted((rating.band for rating in scorable), key=BANDS.index)
    if len(scorable) == 3:
        return scores[1], bands[1], "median_of_three"
    # Comparing the two distances in floating point could break their tie by
    # rounding noise; the rule always resolves to the lower band, so take it.
    return (scores[0] + scores[1]) / 2, bands[0], "median_of_three"


# ------------------------------------------------------------------- bootstrap


def cluster_bootstrap_ci(
    items: Sequence[T],
    clusters: Sequence[str],
    statistic: Callable[[list[T]], float | None],
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float] | None:
    """Percentile (1 - alpha) interval of `statistic`, resampling whole clusters.

    Each resample draws as many clusters as there are, with replacement, and
    takes every item of each drawn cluster: the responses of one speaker leave
    and enter the sample together. Resamples on which the statistic is
    undefined (None or NaN) are skipped. None with fewer than MIN_CLUSTERS
    clusters, or when more than half of the resamples are undefined: an
    interval built from the few resamples that happened to work would look
    precise and mean nothing.
    """
    if len(items) != len(clusters):
        raise ValueError(f"{len(items)} items but {len(clusters)} cluster labels")
    if n_boot < 1:
        raise ValueError(f"n_boot must be at least 1, got {n_boot}")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be within (0, 1), got {alpha}")
    groups: dict[str, list[T]] = {}
    for item, cluster in zip(items, clusters, strict=True):
        groups.setdefault(cluster, []).append(item)
    if len(groups) < MIN_CLUSTERS:
        return None
    # Sorted, so the same data listed in another order gives the same interval.
    members = [groups[cluster] for cluster in sorted(groups)]
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(n_boot):
        drawn = rng.integers(0, len(members), size=len(members))
        value = statistic([item for g in drawn for item in members[g]])
        if value is not None and math.isfinite(value):
            values.append(float(value))
    if 2 * len(values) < n_boot:
        return None
    low, high = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


# ---------------------------------------------------------------------- report


@dataclass(frozen=True)
class _Compared:
    """A response the machine can be compared on: a human reference and a machine score."""

    speaker_id: str
    kind: str
    reference_score: float
    reference_band: str
    ai_score: float
    ai_band: str
    flagged: bool | None


def _band_kappa(rated: list[RatedResponse]) -> float | None:
    return quadratic_weighted_kappa(
        [item.ratings[0].band for item in rated], [item.ratings[1].band for item in rated], BANDS
    )


def _exact_band(rated: list[RatedResponse]) -> float | None:
    if not rated:
        return None
    return sum(item.ratings[0].band == item.ratings[1].band for item in rated) / len(rated)


def _half_point_kappa(rated: list[RatedResponse]) -> float | None:
    return quadratic_weighted_kappa(
        [_half_point(item.ratings[0].overall) for item in rated],
        [_half_point(item.ratings[1].overall) for item in rated],
        half_point_categories(),
    )


def _machine_pearson(rows: list[_Compared]) -> float | None:
    return pearson([row.reference_score for row in rows], [row.ai_score for row in rows])


def _machine_rmse(rows: list[_Compared]) -> float | None:
    return rmse([row.reference_score for row in rows], [row.ai_score for row in rows])


def _machine_kappa(rows: list[_Compared]) -> float | None:
    return quadratic_weighted_kappa(
        [row.reference_band for row in rows], [row.ai_band for row in rows], BANDS
    )


def _note_none(notes: list[str], name: str, value: Any, n: int, minimum: int) -> None:
    if value is not None:
        return
    if n == 0:
        notes.append(f"{name}: no items")
    elif n < minimum:
        notes.append(f"{name}: fewer than {minimum} items")
    else:
        notes.append(f"{name}: undefined, the scores do not vary enough")


def _with_ci(
    name: str,
    rows: list[Any],
    statistic: Callable[[list[Any]], float | None],
    minimum: int,
    n_boot: int,
    seed: int,
    notes: list[str],
) -> dict[str, Any]:
    value = statistic(rows)
    _note_none(notes, name, value, len(rows), minimum)
    if value is None:
        return {"value": None, "ci": None}
    clusters = [row.speaker_id for row in rows]
    ci = cluster_bootstrap_ci(rows, clusters, statistic, n_boot=n_boot, seed=seed)
    if ci is None and len(set(clusters)) < MIN_CLUSTERS:
        notes.append(f"{name}.ci: fewer than {MIN_CLUSTERS} speakers")
    elif ci is None:
        notes.append(f"{name}.ci: more than half of the bootstrap resamples are undefined")
    return {"value": value, "ci": ci}


def _counts(
    items: Sequence[RatedResponse], references: list[tuple[float | None, str | None, str]]
) -> dict[str, int]:
    rated_twice = [item for item in items if len(item.ratings) >= 2]
    needed = [item for item in rated_twice if needs_adjudication(*item.ratings[:2])]
    return {
        "responses": len(items),
        "rated_twice": len(rated_twice),
        "both_scorable": sum(
            1 for item in rated_twice if not any(r.unscorable for r in item.ratings[:2])
        ),
        "adjudication_needed": len(needed),
        "adjudicated": sum(1 for item in needed if len(item.ratings) == 3),
        "pending": sum(1 for item in needed if len(item.ratings) < 3),
        "unscorable": sum(1 for _, _, kind in references if kind == "unscorable"),
        "speakers": len({item.speaker_id for item in items}),
    }


def _overall_of(item: RatedResponse, rater_id: str) -> float | None:
    return next(r.overall for r in item.ratings[:2] if r.rater_id == rater_id)


def _icc_overall(rated: list[RatedResponse]) -> dict[str, Any]:
    if not rated:
        return {"value": None, "kind": None}
    pairs = {frozenset(r.rater_id for r in item.ratings[:2]) for item in rated}
    if len(pairs) > 1:
        matrix = [[item.ratings[0].overall, item.ratings[1].overall] for item in rated]
        return {"value": icc_1_1(matrix), "kind": "ICC(1,1)"}
    # The same two raters on every response: a crossed design. ICC(2,1) reads a
    # column as one person, so columns follow rater_id, not the slot a rating
    # happened to land in.
    raters = sorted(next(iter(pairs)))
    matrix = [[_overall_of(item, rater) for rater in raters] for item in rated]
    return {"value": icc_2_1(matrix), "kind": "ICC(2,1)"}


def _human_human(
    items: Sequence[RatedResponse], n_boot: int, seed: int, notes: list[str]
) -> dict[str, Any]:
    rated = [
        item
        for item in items
        if len(item.ratings) >= 2 and not any(r.unscorable for r in item.ratings[:2])
    ]
    first = [item.ratings[0] for item in rated]
    second = [item.ratings[1] for item in rated]
    n = len(rated)

    def with_ci(
        name: str, statistic: Callable[[list[Any]], float | None], minimum: int
    ) -> dict[str, Any]:
        return _with_ci(f"human_human.{name}", rated, statistic, minimum, n_boot, seed, notes)

    per_criterion: dict[str, dict[str, Any]] = {}
    for criterion in CRITERIA:
        pairs = [
            (a.criteria.get(criterion), b.criteria.get(criterion))
            for a, b in zip(first, second, strict=True)
        ]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        per_criterion[criterion] = {
            "pearson": pearson([x for x, _ in pairs], [y for _, y in pairs]),
            "n": len(pairs),
        }
    gaps = [abs(a.overall - b.overall) for a, b in zip(first, second, strict=True)]
    out = {
        "n": n,
        "speakers": len({item.speaker_id for item in rated}),
        "qwk_band": with_ci("qwk_band", _band_kappa, 2),
        "exact_band_agreement": with_ci("exact_band_agreement", _exact_band, 1),
        "qwk_overall_half_points": with_ci("qwk_overall_half_points", _half_point_kappa, 2),
        "icc_overall": _icc_overall(rated),
        "pearson_overall": pearson([r.overall for r in first], [r.overall for r in second]),
        "mean_abs_diff": sum(gaps) / n if n else None,
        "per_criterion": per_criterion,
        "confusion_band": confusion([r.band for r in first], [r.band for r in second], BANDS),
    }
    _note_none(notes, "human_human.icc_overall", out["icc_overall"]["value"], n, 2)
    _note_none(notes, "human_human.pearson_overall", out["pearson_overall"], n, 3)
    _note_none(notes, "human_human.mean_abs_diff", out["mean_abs_diff"], n, 1)
    for criterion, entry in per_criterion.items():
        name = f"human_human.per_criterion.{criterion}.pearson"
        _note_none(notes, name, entry["pearson"], entry["n"], 3)
    return out


def _compared(
    items: Sequence[RatedResponse],
    references: list[tuple[float | None, str | None, str]],
    notes: list[str],
) -> list[_Compared]:
    rows: list[_Compared] = []
    no_machine = 0
    for item, (score, band, kind) in zip(items, references, strict=True):
        if score is None or band is None:
            continue
        if item.ai_overall is None or item.ai_band is None:
            no_machine += 1
            continue
        rows.append(
            _Compared(
                item.speaker_id, kind, score, band, item.ai_overall, item.ai_band, item.flagged
            )
        )
    ignored = sum(
        1 for item in items if len(item.ratings) == 3 and not needs_adjudication(*item.ratings[:2])
    )
    pending = sum(1 for _, _, kind in references if kind == "pending")
    if ignored:
        notes.append(f"reference: {ignored} response(s) had an unneeded third rating, ignored")
    if pending:
        notes.append(f"machine_human: {pending} response(s) pending adjudication left out")
    if no_machine:
        notes.append(f"machine_human: {no_machine} response(s) without a machine score left out")
    return rows


def _machine_human(
    rows: list[_Compared], n_boot: int, seed: int, notes: list[str]
) -> dict[str, Any]:
    def with_ci(
        name: str, statistic: Callable[[list[Any]], float | None], minimum: int
    ) -> dict[str, Any]:
        return _with_ci(f"machine_human.{name}", rows, statistic, minimum, n_boot, seed, notes)

    reference_bands = [row.reference_band for row in rows]
    machine_bands = [row.ai_band for row in rows]
    bands = per_band(reference_bands, machine_bands)
    kinds = Counter(row.kind for row in rows)
    out = {
        "n": len(rows),
        "speakers": len({row.speaker_id for row in rows}),
        "pearson": with_ci("pearson", _machine_pearson, 3),
        "rmse": with_ci("rmse", _machine_rmse, 1),
        "qwk_band": with_ci("qwk_band", _machine_kappa, 2),
        "confusion_band": confusion(reference_bands, machine_bands, BANDS),
        "per_band": bands,
        "reference_kinds": {kind: kinds[kind] for kind in ("mean_of_two", "median_of_three")},
    }
    for band, entry in bands.items():
        if entry["recall"] is None:
            notes.append(f"machine_human.per_band.{band}.recall: no reference response in band")
        if entry["precision"] is None:
            notes.append(f"machine_human.per_band.{band}.precision: machine never gave this band")
    return out


def _routing(rows: list[_Compared], notes: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, flagged in (("flagged", True), ("not_flagged", False)):
        errors = [
            abs(row.ai_score - row.reference_score)
            for row in rows
            if row.flagged is not None and bool(row.flagged) == flagged
        ]
        mean_abs_error = sum(errors) / len(errors) if errors else None
        out[name] = {"n": len(errors), "mean_abs_error": mean_abs_error}
        _note_none(notes, f"routing.{name}.mean_abs_error", mean_abs_error, len(errors), 1)
    unknown = sum(1 for row in rows if row.flagged is None)
    if unknown:
        notes.append(f"routing: {unknown} response(s) without a routing flag left out")
    return out


def _jsonable(value: Any) -> Any:
    """Plain JSON types only (lists, not tuples), floats rounded to 4 decimals."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return round(float(value), 4)
    return value


def agreement_report(
    items: Sequence[RatedResponse],
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """The study's agreement report: a JSON-ready dict, floats rounded to 4 decimals.

    Keys come in this order, and human_human comes before machine_human on
    purpose: agreement with the machine is only as meaningful as the agreement
    between the humans it is measured against.

    * "counts" -- responses, rated_twice, both_scorable, adjudication_needed,
      adjudicated, pending, unscorable, speakers. Not a partition:
      adjudication_needed = adjudicated + pending, and an adjudicated response
      can still end up unscorable.
    * "human_human" -- responses whose two primary ratings are both scorable,
      pending ones included. Pairwise metrics compare slot 1 with slot 2.
      icc_overall is ICC(2,1) when the same two raters rated every response
      (whatever the slot order) and ICC(1,1) when the pairs vary.
    * "machine_human" -- responses with a human reference and a machine score
      and band; pending, unscorable and incomplete responses are left out.
    * "routing" -- RQ4: mean |machine - reference| for the responses the
      machine sent to teacher review and for the others.
    * "notes" -- why a metric is None, and which responses were left out.
    * "bootstrap" -- n_boot, seed and alpha, so a saved report says how to
      reproduce its intervals.

    Intervals are 95% percentile bootstraps over speakers (`n_boot`, `seed`).
    """
    notes: list[str] = []
    references = [reference(item) for item in items]
    report: dict[str, Any] = {
        "counts": _counts(items, references),
        "human_human": _human_human(items, n_boot, seed, notes),
    }
    compared = _compared(items, references, notes)
    report["machine_human"] = _machine_human(compared, n_boot, seed, notes)
    report["routing"] = _routing(compared, notes)
    report["notes"] = notes
    report["bootstrap"] = {"n_boot": n_boot, "seed": seed, "alpha": 0.05}
    return _jsonable(report)
