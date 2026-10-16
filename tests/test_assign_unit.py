"""Layer 1 -- UNIT: who rates what, and in which order (D030, research/assign.py).

The plan decides the study's sample and every rater's order, so it is pinned
here: two distinct raters per response, every rater's positions a clean 1..n,
the same seed giving the same plan, loads that stay balanced with more raters.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import pytest

from aicefr.research import assign

RESPONSES = [f"r{i:02d}" for i in range(12)]


def by_rater(plan):
    out = defaultdict(list)
    for p in plan:
        out[p.rater_id].append(p)
    return out


def test_two_raters_both_rate_everything_each_in_their_own_order():
    plan = assign.plan(RESPONSES, ["gv-a", "gv-b"], seed=7)
    assert len(plan) == 2 * len(RESPONSES)
    for response in RESPONSES:
        mine = [p for p in plan if p.response_id == response]
        assert sorted(p.slot for p in mine) == [1, 2]
        assert {p.rater_id for p in mine} == {"gv-a", "gv-b"}
    orders = {}
    for rater, items in by_rater(plan).items():
        assert sorted(p.position for p in items) == list(range(1, len(RESPONSES) + 1))
        orders[rater] = [p.response_id for p in sorted(items, key=lambda p: p.position)]
    assert orders["gv-a"] != orders["gv-b"]


def test_the_same_seed_gives_the_same_plan_and_another_seed_another():
    a = assign.plan(RESPONSES, ["gv-a", "gv-b", "gv-c"], seed=11)
    assert a == assign.plan(list(reversed(RESPONSES)), ["gv-c", "gv-a", "gv-b"], seed=11)
    assert a != assign.plan(RESPONSES, ["gv-a", "gv-b", "gv-c"], seed=12)


def test_with_more_raters_loads_stay_balanced_and_every_pair_meets():
    raters = ["gv-a", "gv-b", "gv-c", "gv-d"]
    plan = assign.plan(RESPONSES, raters, seed=3)
    load = Counter(p.rater_id for p in plan)
    assert set(load) == set(raters)
    assert max(load.values()) - min(load.values()) <= 2
    pairs = Counter()
    for response in RESPONSES:
        mine = sorted(p.rater_id for p in plan if p.response_id == response)
        assert len(set(mine)) == 2
        pairs[tuple(mine)] += 1
    assert len(pairs) == 6


def test_a_rater_who_has_seen_the_machine_result_never_gets_that_response():
    raters = ["gv-a", "gv-b", "gv-c"]
    seen = {"r00": {"gv-a"}, "r01": {"gv-b", "gv-c"}}
    plan = assign.plan(RESPONSES, raters, seed=9, exclude=seen)
    given = defaultdict(set)
    for p in plan:
        given[p.response_id].add(p.rater_id)
    assert given["r00"] == {"gv-b", "gv-c"}
    # Every pair holds gv-b or gv-c: r01 has no blind pair left and is not planned.
    assert set(given) == set(RESPONSES) - {"r01"}
    assert all(len(v) == 2 for v in given.values())
    for items in by_rater(plan).values():
        assert sorted(p.position for p in items) == list(range(1, len(items) + 1))
    assert plan == assign.plan(RESPONSES, raters, seed=9, exclude=seen)


def test_one_rater_is_not_a_double_rating():
    with pytest.raises(ValueError):
        assign.plan(RESPONSES, ["gv-a", "gv-a"], seed=1)


def test_adjudication_continues_the_adjudicators_own_order():
    extra = assign.adjudication(["r03", "r01", "r07"], "gv-c", seed=5, start=12)
    assert sorted(p.position for p in extra) == [13, 14, 15]
    assert {p.slot for p in extra} == {3}


def test_a_sample_is_a_reproducible_subset():
    picked = assign.sample(RESPONSES, 5, seed=9)
    assert len(picked) == 5 and set(picked) <= set(RESPONSES)
    assert picked == assign.sample(RESPONSES, 5, seed=9)
    assert assign.sample(RESPONSES, None, seed=9) == sorted(RESPONSES)
    assert assign.sample(RESPONSES, 50, seed=9) == sorted(RESPONSES)
