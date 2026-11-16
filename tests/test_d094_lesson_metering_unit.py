"""D094 unit layer: what a recording on the lesson path costs, as the project owner chose it.

Option D (07/11/2026): the first five recordings of a Vietnam day are free;
no more than 30 are measured in a day. D106 (16/11/2026): past the five a
recording is free too by default; a seller may still set whole runs per
started minute of speech.
"""

from __future__ import annotations

import pytest

from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    PriceList,
    as_idpoint,
    as_runs,
    lesson_units,
)

pytestmark = pytest.mark.unit


def test_the_defaults_are_the_owners_choice():
    # D106 (16/11/2026): free, held back by the day's cap alone.
    assert (
        DEFAULT_PRICES.lesson_minute_runs,
        DEFAULT_PRICES.lesson_free_per_day,
        DEFAULT_PRICES.lesson_daily_cap,
    ) == (0.0, 5, 30)
    assert lesson_units(DEFAULT_PRICES, 120) == 0


def test_a_priced_recording_pays_per_started_minute_of_speech_at_least_one():
    priced = PriceList(lesson_minute_runs=1)
    costs = [lesson_units(priced, s) for s in (0, 4.5, 60, 60.5, 120, 150, 299, 900)]
    assert costs == [1000, 1000, 1000, 2000, 2000, 3000, 5000, 5000]  # five minutes at most
    units = lesson_units(priced, 30)
    assert (as_runs(units), as_idpoint(priced, units)) == (1.0, 2000)


def test_the_seller_sets_the_lesson_price_in_whole_runs():
    assert lesson_units(PriceList(lesson_minute_runs=2), 61) == 4000
    assert lesson_units(PriceList(lesson_minute_runs=0), 61) == 0
    assert lesson_units(PriceList(lesson_minute_runs=0.25), 61) == 0  # D106: whole part


@pytest.mark.parametrize(
    "fields",
    [
        {"lesson_minute_runs": -0.1},
        {"lesson_daily_cap": 0},
        {"lesson_free_per_day": -1},
        {"lesson_free_per_day": 31, "lesson_daily_cap": 30},
    ],
)
def test_impossible_lesson_numbers_are_refused(fields):
    with pytest.raises(ValueError):
        PriceList(**fields)


def test_the_price_list_shows_the_lesson_numbers():
    shown = DEFAULT_PRICES.as_dict()
    assert (
        shown["lesson_minute_runs"],
        shown["lesson_free_per_day"],
        shown["lesson_daily_cap"],
    ) == (
        0.0,
        5,
        30,
    )
