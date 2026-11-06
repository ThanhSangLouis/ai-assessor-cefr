"""D094 unit layer: what a recording on the lesson path costs, as the project owner chose it.

Option D (07/11/2026): the first five recordings of a Vietnam day are free;
past them a recording pays 0.1 run (200 IDPoint) per started minute of speech;
no more than 30 are measured in a day.
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
    assert (
        DEFAULT_PRICES.lesson_minute_runs,
        DEFAULT_PRICES.lesson_free_per_day,
        DEFAULT_PRICES.lesson_daily_cap,
    ) == (0.1, 5, 30)


def test_a_recording_pays_per_started_minute_of_speech_at_least_one():
    costs = [lesson_units(DEFAULT_PRICES, s) for s in (0, 4.5, 60, 60.5, 120, 150, 299, 900)]
    assert costs == [100, 100, 100, 200, 200, 300, 500, 500]  # five minutes at most
    units = lesson_units(DEFAULT_PRICES, 30)
    assert (as_runs(units), as_idpoint(DEFAULT_PRICES, units)) == (0.1, 200)


def test_a_typical_lesson_costs_less_than_one_assessment():
    # The sample lessons hold 4 recordings at the median, each under a minute of speech.
    lesson = sum(lesson_units(DEFAULT_PRICES, s) for s in (12, 20, 35, 50))
    assert as_idpoint(DEFAULT_PRICES, lesson) == 800 < 2000


def test_the_seller_sets_the_lesson_price():
    dearer = PriceList(lesson_minute_runs=0.25)
    assert lesson_units(dearer, 61) == 500
    assert lesson_units(PriceList(lesson_minute_runs=0), 61) == 0


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
        0.1,
        5,
        30,
    )
