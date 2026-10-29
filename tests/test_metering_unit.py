"""D057: the price list of the metered channel, as the team agreed it (24/10/2026)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aicefr.contracts import TaskPurpose
from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    PriceList,
    TokenUsage,
    as_idpoint,
    as_runs,
    hold_for,
    input_tokens,
    minutes,
    units_for,
    usage_of,
    windows,
)
from aicefr.storage.metering_repository import cycle

pytestmark = pytest.mark.unit


def test_a_recording_up_to_a_minute_is_one_run():
    for seconds in (1, 35, 60):
        units = units_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, seconds)
        assert (as_runs(units), as_idpoint(DEFAULT_PRICES, units)) == (1.0, 2000)


def test_every_further_minute_adds_seven_tenths_of_a_run_up_to_five():
    idp = [as_idpoint(DEFAULT_PRICES, units_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, s))
           for s in (61, 120, 121, 300, 900)]  # fmt: skip
    assert idp == [3400, 3400, 4800, 7600, 7600]
    assert minutes(0) == 1 and minutes(-3) == 1 and minutes(900) == 5


def test_practice_pays_half():
    units = units_for(DEFAULT_PRICES, TaskPurpose.PRACTICE, 40)
    assert (as_runs(units), as_idpoint(DEFAULT_PRICES, units)) == (0.5, 1000)


def test_a_hold_is_the_longest_the_task_allows():
    assert hold_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, 90) == units_for(
        DEFAULT_PRICES, TaskPurpose.ASSESSMENT, 90
    )
    assert hold_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, 90) == 1700


def test_the_seller_sets_the_prices():
    dearer = PriceList(first_minute_runs=1.5, extra_minute_runs=1.0, idpoint_per_run=1000)
    units = units_for(dearer, TaskPurpose.ASSESSMENT, 100)
    assert (units, as_idpoint(dearer, units)) == (2500, 2500)
    with pytest.raises(ValueError):
        PriceList(first_minute_runs=-1)
    with pytest.raises(ValueError):
        PriceList(practice_factor=0)


def test_audio_tokens_are_whispers_windows_plus_the_language_check():
    # Kept with each charge for the cost per request, not to price it.
    assert [windows(s) for s in (0, 1, 30, 31, 60, 61)] == [1, 1, 1, 2, 2, 3]
    assert input_tokens(35) == 1500 * 3
    assert input_tokens(10_000) == input_tokens(300)


def test_counted_output_tokens_win_over_the_estimate_from_words():
    assert usage_of(60, 170, words=999) == TokenUsage(4500, 170)
    assert usage_of(60, None, words=120) == TokenUsage(4500, 160, estimated=True)


def test_a_cycle_starts_on_the_sixteenth():
    assert cycle(datetime(2026, 10, 16, 0, 0, tzinfo=UTC)) == "2026-10"
    assert cycle(datetime(2026, 10, 15, 23, 59, tzinfo=UTC)) == "2026-09"
    assert cycle(datetime(2026, 1, 3, tzinfo=UTC)) == "2025-12"
