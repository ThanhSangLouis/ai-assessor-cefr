"""Layer 1 -- UNIT: agreement statistics for the blind double rating.

No database, no HTTP, no audio: hand-written ratings in, exact numbers out.
The statistics are checked against a published worked example (Shrout and
Fleiss 1979) or an independent implementation (scikit-learn), not against
themselves; the protocol rules are checked on both sides of each boundary.
"""

from __future__ import annotations

import itertools
import json
from collections import Counter
from collections.abc import Callable, Iterator

import numpy as np
import pytest

from aicefr.contracts import Band, Criterion
from aicefr.research.agreement import (
    BANDS,
    CRITERIA,
    RatedResponse,
    Rating,
    agreement_report,
    cluster_bootstrap_ci,
    confusion,
    half_point_categories,
    icc_1_1,
    icc_2_1,
    needs_adjudication,
    pearson,
    per_band,
    quadratic_weighted_kappa,
    reference,
    rmse,
)


def rate(rater: str, overall: float, band: str, *, adjudication: bool = False) -> Rating:
    return Rating(rater, overall, band, dict.fromkeys(CRITERIA, overall), adjudication=adjudication)


def unscorable(rater: str, *, adjudication: bool = False) -> Rating:
    return Rating(rater, None, None, {}, unscorable=True, adjudication=adjudication)


def response(
    response_id: str,
    speaker_id: str,
    *ratings: Rating,
    ai: float | None = None,
    ai_band: str | None = None,
    flagged: bool | None = None,
) -> RatedResponse:
    return RatedResponse(response_id, speaker_id, ratings, ai, ai_band, flagged)


# ------------------------------------------------------------------ constants


def test_bands_and_criteria_match_the_contracts():
    assert BANDS == tuple(band.value for band in Band)
    assert CRITERIA == tuple(criterion.value for criterion in Criterion)


def test_half_point_categories_cover_the_0_to_6_scale():
    categories = half_point_categories()
    assert (categories[0], categories[-1], len(categories)) == (0.0, 6.0, 13)
    assert all(b - a == 0.5 for a, b in itertools.pairwise(categories))


# ---------------------------------------------------------------------- kappa


def test_qwk_is_one_for_perfect_agreement():
    bands = ["A2", "B1", "B2", "B1"]
    assert quadratic_weighted_kappa(bands, bands, BANDS) == pytest.approx(1.0)


def test_qwk_matches_scikit_learn_on_bands():
    cohen_kappa_score = pytest.importorskip("sklearn.metrics").cohen_kappa_score

    a = ["A2", "B1", "B2", "B1", "A2", "B2", "B1", "B1", "A2", "B2"]
    b = ["A2", "B1", "B1", "B2", "B1", "B2", "B1", "A2", "A2", "B1"]
    expected = cohen_kappa_score(a, b, labels=list(BANDS), weights="quadratic")
    assert quadratic_weighted_kappa(a, b, BANDS) == pytest.approx(expected, abs=1e-12)


def test_qwk_matches_scikit_learn_on_half_points_with_unused_categories():
    cohen_kappa_score = pytest.importorskip("sklearn.metrics").cohen_kappa_score

    a = [2.0, 2.5, 3.0, 3.5, 4.0, 3.0, 2.5]
    b = [2.5, 2.5, 3.5, 3.0, 4.0, 2.0, 3.0]
    # scikit-learn refuses float labels, so it gets the same scale as codes 0..12.
    expected = cohen_kappa_score(
        [int(x * 2) for x in a],
        [int(y * 2) for y in b],
        labels=list(range(13)),
        weights="quadratic",
    )
    assert quadratic_weighted_kappa(a, b, half_point_categories()) == pytest.approx(
        expected, abs=1e-12
    )


def test_qwk_is_none_when_undefined_or_too_small():
    assert quadratic_weighted_kappa(["B1"] * 4, ["B1"] * 4, BANDS) is None
    assert quadratic_weighted_kappa(["B1"], ["B2"], BANDS) is None
    assert quadratic_weighted_kappa([], [], BANDS) is None


def test_qwk_rejects_a_value_outside_the_categories():
    with pytest.raises(ValueError, match="C1"):
        quadratic_weighted_kappa(["B1", "C1"], ["B1", "B1"], BANDS)


# --------------------------------------------------------- pearson, rmse, icc


def test_pearson_and_rmse_on_a_small_example():
    x, y = [1.0, 2.0, 3.0, 4.0], [1.5, 1.5, 3.5, 3.5]
    assert pearson(x, y) == pytest.approx(float(np.corrcoef(x, y)[0, 1]))
    assert rmse(x, y) == pytest.approx(0.5)


def test_pearson_and_rmse_are_none_when_undefined():
    assert pearson([1.0, 2.0], [2.0, 3.0]) is None
    assert pearson([3.0, 3.0, 3.0], [1.0, 2.0, 3.0]) is None
    assert rmse([], []) is None


SHROUT_FLEISS = [
    [9, 2, 5, 8],
    [6, 1, 3, 2],
    [8, 4, 6, 8],
    [7, 1, 2, 6],
    [10, 5, 6, 9],
    [6, 2, 4, 7],
]


def test_icc_reproduces_shrout_and_fleiss_1979():
    assert icc_1_1(SHROUT_FLEISS) == pytest.approx(0.17, abs=0.01)
    assert icc_2_1(SHROUT_FLEISS) == pytest.approx(0.29, abs=0.01)


def test_icc_is_none_when_too_small_or_undefined():
    assert icc_2_1([[3.0, 3.5]]) is None
    assert icc_1_1([[3.0], [4.0]]) is None
    assert icc_2_1([[3.0, 3.0], [3.0, 3.0]]) is None
    assert icc_1_1([[3.0, 3.0], [3.0, 3.0]]) is None


# ------------------------------------------------------- confusion, per band


def test_confusion_rows_follow_the_first_sequence():
    assert confusion(["A2", "B1", "B1"], ["B1", "B1", "B2"], BANDS) == [
        [0, 1, 0],
        [0, 1, 1],
        [0, 0, 0],
    ]


def test_per_band_recall_and_precision_on_a_hand_made_example():
    reference_bands = ["A2", "A2", "B1", "B1", "B1", "B2"]
    machine_bands = ["A2", "B1", "B1", "B1", "A2", "B1"]
    assert per_band(reference_bands, machine_bands) == {
        "A2": {"support": 2, "recall": 0.5, "precision": 0.5},
        "B1": {"support": 3, "recall": pytest.approx(2 / 3), "precision": 0.5},
        "B2": {"support": 1, "recall": 0.0, "precision": None},
    }


# ------------------------------------------------------------- protocol rules


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (rate("R1", 3.0, "B1"), rate("R2", 4.0, "B1"), True),
        (rate("R1", 3.1, "B1"), rate("R2", 4.1, "B1"), True),
        (rate("R1", 3.0, "B1"), rate("R2", 3.5, "B1"), False),
        (rate("R1", 3.25, "A2"), rate("R2", 3.5, "B1"), True),
        (unscorable("R1"), rate("R2", 3.0, "B1"), True),
        (rate("R1", 3.0, "B1"), unscorable("R2"), True),
        (unscorable("R1"), unscorable("R2"), False),
    ],
    ids=[
        "gap-exactly-1.0",
        "gap-1.0-with-float-noise",
        "gap-0.5-same-band",
        "gap-0.25-band-differs",
        "first-unscorable",
        "second-unscorable",
        "both-unscorable",
    ],
)
def test_needs_adjudication(first: Rating, second: Rating, expected: bool):
    assert needs_adjudication(first, second) is expected


def test_reference_is_the_mean_of_two_without_adjudication():
    item = response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 3.5, "B1"))
    assert reference(item) == (3.25, "B1", "mean_of_two")


def test_reference_is_the_median_of_three_after_adjudication():
    third = rate("R3", 3.5, "B2", adjudication=True)
    item = response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 4.5, "B2"), third)
    # The mean would be 3.67; the median is not pulled by the outlying rater.
    assert reference(item) == (3.5, "B2", "median_of_three")


def test_reference_is_pending_until_the_third_rating_arrives():
    item = response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 4.0, "B2"))
    assert reference(item) == (None, None, "pending")


def test_reference_is_unscorable_when_both_raters_say_so():
    item = response("r", "s", unscorable("R1"), unscorable("R2"))
    assert reference(item) == (None, None, "unscorable")


@pytest.mark.parametrize(
    "ratings",
    [
        (unscorable("R1"), rate("R2", 3.0, "B1"), rate("R3", 4.0, "B2", adjudication=True)),
        (unscorable("R1"), rate("R2", 4.0, "B2"), rate("R3", 3.0, "B1", adjudication=True)),
        (rate("R1", 4.0, "B2"), unscorable("R2"), rate("R3", 3.0, "B1", adjudication=True)),
    ],
    ids=["low-then-high", "high-then-low", "unscorable-in-second-slot"],
)
def test_reference_with_two_scorable_of_three_is_their_mean_and_the_lower_band(ratings):
    assert reference(response("r", "s", *ratings)) == (3.5, "B1", "median_of_three")


def test_reference_is_unscorable_when_fewer_than_two_of_three_are_scorable():
    third = unscorable("R3", adjudication=True)
    item = response("r", "s", unscorable("R1"), rate("R2", 3.0, "B1"), third)
    assert reference(item) == (None, None, "unscorable")


def test_reference_is_incomplete_before_both_primary_ratings():
    assert reference(response("r", "s")) == (None, None, "incomplete")
    assert reference(response("r", "s", rate("R1", 3.0, "B1"))) == (None, None, "incomplete")


def test_a_third_rating_that_was_not_needed_is_ignored():
    third = rate("R3", 5.5, "B2", adjudication=True)
    item = response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 3.5, "B1"), third)
    assert reference(item) == (3.25, "B1", "mean_of_two")


def test_rating_rejects_inconsistent_input():
    with pytest.raises(ValueError, match="unscorable"):
        Rating("R1", 3.0, None, {}, unscorable=True)
    with pytest.raises(ValueError, match="band"):
        Rating("R1", 3.0, None, {})
    with pytest.raises(ValueError, match="unknown band"):
        Rating("R1", 3.0, "C1", {})
    with pytest.raises(ValueError, match="within"):
        Rating("R1", 6.5, "B2", {})
    with pytest.raises(ValueError, match="unknown criteria"):
        Rating("R1", 3.0, "B1", {"interaction": 3.0})


def test_rated_response_rejects_a_repeated_rater_or_a_misplaced_adjudication():
    with pytest.raises(ValueError, match="twice"):
        response("r", "s", rate("R1", 3.0, "B1"), rate("R1", 3.5, "B1"))
    with pytest.raises(ValueError, match="third"):
        response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 4.0, "B2", adjudication=True))
    with pytest.raises(ValueError, match="third"):
        response("r", "s", rate("R1", 3.0, "B1"), rate("R2", 4.0, "B2"), rate("R3", 3.5, "B1"))


# ------------------------------------------------------------------ bootstrap


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


VALUES = [1.0, 2.0, 2.5, 4.0, 3.0, 5.0, 3.5]
SPEAKERS = ["a", "a", "b", "c", "c", "d", "e"]


def test_cluster_bootstrap_is_reproducible_for_a_fixed_seed():
    ci = cluster_bootstrap_ci(VALUES, SPEAKERS, mean, n_boot=500, seed=7)
    assert ci is not None
    assert ci == cluster_bootstrap_ci(VALUES, SPEAKERS, mean, n_boot=500, seed=7)
    assert ci != cluster_bootstrap_ci(VALUES, SPEAKERS, mean, n_boot=500, seed=8)
    assert ci[0] <= mean(VALUES) <= ci[1]


def test_cluster_bootstrap_does_not_depend_on_the_order_of_the_items():
    order = [5, 0, 3, 6, 1, 4, 2]
    shuffled = cluster_bootstrap_ci(
        [VALUES[i] for i in order], [SPEAKERS[i] for i in order], mean, n_boot=300
    )
    assert shuffled == pytest.approx(cluster_bootstrap_ci(VALUES, SPEAKERS, mean, n_boot=300))


def test_cluster_bootstrap_resamples_speakers_not_responses():
    # Speaker "a" has three responses, the others one each.
    items = [("a", 1), ("a", 2), ("a", 3), ("b", 1), ("c", 1), ("d", 1)]
    samples: list[list[tuple[str, int]]] = []

    def record(sample: list[tuple[str, int]]) -> float:
        samples.append(sample)
        return float(len(sample))

    cluster_bootstrap_ci(items, [speaker for speaker, _ in items], record, n_boot=200)
    assert len(samples) == 200
    for sample in samples:
        counts = Counter(sample)
        # A drawn speaker brings ALL of their responses, each as many times as drawn.
        assert counts[("a", 1)] == counts[("a", 2)] == counts[("a", 3)]
        assert sum(counts[(speaker, 1)] for speaker in "abcd") == 4
    # Resampling responses would keep every sample at 6 items; drawing speakers does not.
    assert len({len(sample) for sample in samples}) > 1


def test_cluster_bootstrap_needs_three_speakers():
    assert cluster_bootstrap_ci([1.0, 2.0, 3.0, 4.0], ["a", "a", "b", "b"], mean) is None


def undefined_on(share: tuple[int, int]) -> Callable[[list[float]], float | None]:
    """A statistic that is undefined on `share[0]` of every `share[1]` resamples, else 1.0."""
    calls = itertools.count()
    undefined, out_of = share
    return lambda sample: None if next(calls) % out_of < undefined else 1.0


@pytest.mark.parametrize(
    ("share", "expected"),
    [((2, 5), (1.0, 1.0)), ((1, 2), (1.0, 1.0)), ((3, 5), None)],
    ids=["two-fifths-undefined", "exactly-half-undefined", "three-fifths-undefined"],
)
def test_cluster_bootstrap_skips_undefined_resamples_unless_most_are(share, expected):
    assert cluster_bootstrap_ci(VALUES, SPEAKERS, undefined_on(share), n_boot=100) == expected


# --------------------------------------------------------------------- report

# 8 responses, 6 speakers, raters R1 and R2 on everything, R3 adjudicates.
# r4 is adjudicated, r5 is pending (bands differ), r7 is unscorable for both.
NO_PHONOLOGY = {**dict.fromkeys(CRITERIA, 3.0), "phonology": None}
STUDY = [
    response(
        "r1",
        "s1",
        rate("R1", 3.0, "B1"),
        rate("R2", 3.5, "B1"),
        ai=3.4,
        ai_band="B1",
        flagged=False,
    ),
    response(
        "r2",
        "s1",
        rate("R1", 2.0, "A2"),
        rate("R2", 2.5, "A2"),
        ai=2.6,
        ai_band="A2",
        flagged=False,
    ),
    response(
        "r3", "s2", rate("R1", 4.0, "B2"), rate("R2", 4.5, "B2"), ai=3.9, ai_band="B1", flagged=True
    ),
    response(
        "r4",
        "s3",
        rate("R1", 3.0, "B1"),
        rate("R2", 4.0, "B2"),
        rate("R3", 3.5, "B1", adjudication=True),
        ai=3.6,
        ai_band="B1",
        flagged=True,
    ),
    response(
        "r5", "s4", rate("R1", 2.5, "A2"), rate("R2", 3.0, "B1"), ai=2.8, ai_band="A2", flagged=True
    ),
    response(
        "r6",
        "s5",
        rate("R1", 5.0, "B2"),
        rate("R2", 5.0, "B2"),
        ai=4.7,
        ai_band="B2",
        flagged=False,
    ),
    response("r7", "s6", unscorable("R1"), unscorable("R2")),
    response(
        "r8",
        "s6",
        rate("R1", 3.5, "B1"),
        Rating("R2", 3.0, "B1", NO_PHONOLOGY),
        ai=3.0,
        ai_band="B1",
        flagged=False,
    ),
]

COUNT_KEYS = [
    "responses",
    "rated_twice",
    "both_scorable",
    "adjudication_needed",
    "adjudicated",
    "pending",
    "unscorable",
    "speakers",
]


@pytest.fixture(scope="module")
def report() -> dict:
    return agreement_report(STUDY, n_boot=200)


def floats_in(value: object) -> Iterator[float]:
    if isinstance(value, dict):
        for item in value.values():
            yield from floats_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from floats_in(item)
    elif isinstance(value, float):
        yield value


def test_report_counts(report: dict):
    assert report["counts"] == dict(zip(COUNT_KEYS, [8, 8, 7, 2, 1, 1, 1, 6], strict=True))


def test_report_keys_come_in_the_specified_order_humans_first(report: dict):
    assert list(report) == [
        "counts",
        "human_human",
        "machine_human",
        "routing",
        "notes",
        "bootstrap",
    ]
    assert report["bootstrap"] == {"n_boot": 200, "seed": 20261007, "alpha": 0.05}
    assert list(report["counts"]) == COUNT_KEYS
    assert list(report["human_human"]) == [
        "n",
        "speakers",
        "qwk_band",
        "exact_band_agreement",
        "qwk_overall_half_points",
        "icc_overall",
        "pearson_overall",
        "mean_abs_diff",
        "per_criterion",
        "confusion_band",
    ]
    assert list(report["machine_human"]) == [
        "n",
        "speakers",
        "pearson",
        "rmse",
        "qwk_band",
        "confusion_band",
        "per_band",
        "reference_kinds",
    ]
    text = json.dumps(report)
    assert text.index('"human_human"') < text.index('"machine_human"')


def test_report_is_json_ready_with_floats_rounded_to_4_decimals(report: dict):
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert all(value == round(value, 4) for value in floats_in(report))


def test_report_is_reproducible_with_the_default_bootstrap():
    assert agreement_report(STUDY) == agreement_report(STUDY)


def test_report_human_human_block(report: dict):
    humans = report["human_human"]
    assert (humans["n"], humans["speakers"]) == (7, 6)
    assert humans["confusion_band"] == [[1, 1, 0], [0, 2, 1], [0, 0, 2]]
    assert humans["exact_band_agreement"]["value"] == round(5 / 7, 4)
    assert humans["mean_abs_diff"] == 0.5
    assert humans["icc_overall"]["kind"] == "ICC(2,1)"
    ci = humans["qwk_band"]["ci"]
    assert ci is not None and ci[0] <= ci[1]
    assert humans["per_criterion"]["phonology"]["n"] == 6
    assert humans["per_criterion"]["range"]["n"] == 7


def test_report_leaves_pending_responses_out_of_machine_human(report: dict):
    machine = report["machine_human"]
    assert (machine["n"], machine["speakers"]) == (6, 5)
    assert machine["reference_kinds"] == {"mean_of_two": 5, "median_of_three": 1}
    assert machine["confusion_band"] == [[1, 0, 0], [0, 3, 0], [0, 1, 1]]
    assert machine["per_band"]["B2"] == {"support": 2, "recall": 0.5, "precision": 1.0}
    assert any("pending" in note for note in report["notes"])
    without_pending = [item for item in STUDY if item.response_id != "r5"]
    assert agreement_report(without_pending, n_boot=200)["machine_human"] == machine


def test_report_routing_compares_flagged_and_unflagged_errors(report: dict):
    assert report["routing"] == {
        "flagged": {"n": 2, "mean_abs_error": pytest.approx(0.225)},
        "not_flagged": {"n": 4, "mean_abs_error": pytest.approx(0.2625)},
    }


def test_report_rounds_overall_scores_to_half_points_with_ties_up():
    # 3.25 -> 3.5 matches the other rater; banker's rounding would send it to 3.0.
    items = [
        response("r1", "s1", rate("R1", 3.25, "B1"), rate("R2", 3.5, "B1")),
        response("r2", "s2", rate("R1", 2.0, "A2"), rate("R2", 2.0, "A2")),
        response("r3", "s3", rate("R1", 5.0, "B2"), rate("R2", 5.0, "B2")),
    ]
    result = agreement_report(items, n_boot=50)["human_human"]["qwk_overall_half_points"]
    assert result["value"] == 1.0


# Rater 2 always scores half a point above rater 1.
BIASED = [(2.0, 2.5), (3.0, 3.5), (3.5, 4.0), (4.5, 5.0), (5.0, 5.5), (2.5, 3.0)]


def icc_of(items: list[RatedResponse]) -> dict:
    return agreement_report(items, n_boot=50)["human_human"]["icc_overall"]


def test_icc_is_two_way_for_a_fixed_pair_whatever_the_slot_order():
    in_order = [
        response(f"r{i}", f"s{i}", rate("R1", low, "B1"), rate("R2", high, "B1"))
        for i, (low, high) in enumerate(BIASED)
    ]
    swapped = [
        response(f"r{i}", f"s{i}", rate("R2", high, "B1"), rate("R1", low, "B1")) if i % 2 else item
        for i, ((low, high), item) in enumerate(zip(BIASED, in_order, strict=True))
    ]
    expected = {"value": round(icc_2_1(BIASED), 4), "kind": "ICC(2,1)"}
    assert icc_of(in_order) == icc_of(swapped) == expected
    # Built by slot, the swapped design gives another value: the check above has teeth.
    by_slot = [[item.ratings[0].overall, item.ratings[1].overall] for item in swapped]
    assert round(icc_2_1(by_slot), 4) != expected["value"]


def test_icc_is_one_way_when_rater_pairs_rotate():
    pairs = [("R1", "R2"), ("R3", "R4"), ("R1", "R3"), ("R2", "R4"), ("R1", "R4"), ("R2", "R3")]
    rotating = [
        response(f"r{i}", f"s{i}", rate(first, low, "B1"), rate(second, high, "B1"))
        for i, ((first, second), (low, high)) in enumerate(zip(pairs, BIASED, strict=True))
    ]
    assert icc_of(rotating) == {"value": round(icc_1_1(BIASED), 4), "kind": "ICC(1,1)"}


def test_report_notes_explain_metrics_left_empty():
    item = response("r1", "s1", rate("R1", 3.0, "B1"), rate("R2", 3.5, "B1"), ai=3.2, ai_band="B1")
    result = agreement_report([item], n_boot=50)
    assert result["human_human"]["qwk_band"] == {"value": None, "ci": None}
    assert "human_human.qwk_band: fewer than 2 items" in result["notes"]
    assert "machine_human.pearson: fewer than 3 items" in result["notes"]
    assert "machine_human.rmse.ci: fewer than 3 speakers" in result["notes"]
    assert "routing.not_flagged.mean_abs_error: no items" in result["notes"]


def test_report_on_no_responses_is_empty_but_well_formed():
    empty = agreement_report([])
    assert empty["counts"] == dict.fromkeys(COUNT_KEYS, 0)
    assert empty["human_human"]["icc_overall"] == {"value": None, "kind": None}
    assert empty["machine_human"]["reference_kinds"] == {"mean_of_two": 0, "median_of_three": 0}
    assert "human_human.qwk_band: no items" in empty["notes"]
    json.dumps(empty, allow_nan=False)
