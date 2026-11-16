"""D057, D106: the price list of the metered channel: whole runs, one per scored recording."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    RUN_PRICES,
    PriceList,
    as_idpoint,
    as_runs,
    hold_for,
    is_whole,
    minutes,
    units_for,
    whole_runs,
)
from aicefr.storage.metering_repository import cycle

pytestmark = pytest.mark.unit


def test_a_recording_up_to_a_minute_is_one_run():
    for seconds in (1, 35, 60):
        units = units_for(DEFAULT_PRICES, seconds)
        assert (as_runs(units), as_idpoint(DEFAULT_PRICES, units)) == (1.0, 2000)


def test_a_scored_recording_is_one_run_whatever_it_lasted():
    # D106: whole runs; no task is longer than a minute, and none pays more for it.
    idp = [as_idpoint(DEFAULT_PRICES, units_for(DEFAULT_PRICES, s))
           for s in (5, 61, 120, 121, 300, 900)]  # fmt: skip
    assert idp == [2000] * 6
    assert minutes(0) == 1 and minutes(-3) == 1 and minutes(900) == 5


def test_a_seller_may_still_charge_whole_runs_per_further_minute():
    longer = PriceList(extra_minute_runs=1)
    idp = [as_idpoint(longer, units_for(longer, s)) for s in (61, 120, 121, 300, 900)]
    assert idp == [4000, 4000, 6000, 10000, 10000]


def test_a_hold_is_the_longest_the_task_allows():
    assert hold_for(DEFAULT_PRICES, 90) == units_for(DEFAULT_PRICES, 90) == 1000
    assert hold_for(PriceList(extra_minute_runs=1), 90) == 2000


def test_the_seller_sets_the_prices():
    dearer = PriceList(first_minute_runs=2, extra_minute_runs=1.0, idpoint_per_run=1000)
    units = units_for(dearer, 100)
    assert (units, as_idpoint(dearer, units)) == (3000, 3000)
    with pytest.raises(ValueError):
        PriceList(first_minute_runs=-1)


def test_every_price_is_a_whole_run_and_a_fraction_rounds_down():
    # D106: a fraction from older settings or an older price list counts as its
    # whole part, in the learner's favour; nothing is ever 0.3 or 0.7 of a run.
    old = PriceList(first_minute_runs=1.5, extra_minute_runs=0.7, upgrade_runs=0.3,
                    passage_runs=0.1, lesson_minute_runs=0.1)  # fmt: skip
    assert [getattr(old, f) for f in RUN_PRICES] == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert whole_runs(0.9999999) == 1 and whole_runs(2.4) == 2
    assert is_whole(0) and is_whole(3.0) and not is_whole(0.3) and not is_whole(-1)


def test_a_cycle_starts_on_the_sixteenth():
    assert cycle(datetime(2026, 10, 16, 0, 0, tzinfo=UTC)) == "2026-10"
    assert cycle(datetime(2026, 10, 15, 23, 59, tzinfo=UTC)) == "2026-09"
    assert cycle(datetime(2026, 1, 3, tzinfo=UTC)) == "2025-12"
