"""The price list of the metered channel: whole runs only (D106, D107).

A learner buys runs in whole packs (1, 10, 30, 100), so every price is a whole
number of runs too: one scored recording is one run, and nothing is ever
charged as 0.3 or 0.7 of a run. Every task is at most a minute, so a recording
costs its one run whatever it lasted.

D107: what a paid language model writes for a learner is paid for by a run,
so the model's bill is always covered. One run scores a recording and brings
its AI rewrite (one per recording, kept) and one reading passage (D090);
beyond that a rewrite or a passage is one run each. A teacher's lesson draft
(D075) is free, five a day. The recordings on the lesson path (D094) are
measured on our own server, with no language model, and stay free within
their daily limit. The seller still sets these
numbers (`AICEFR_PRICE_*`, `AICEFR_IDPOINT_PER_RUN`), and since D078 an
administrator on the dashboard, but only as whole runs: a fraction saved
before D106 counts as its whole part, rounded down, in the learner's favour.

D057 (team decision, 24/10/2026) set the first minute at one run, 2,000
IDPoint at the agreed 1 IDPoint = 1 VND. D105: the tokens a recording or a
model call used are not kept with each charge any more; nothing read them.

Charges are kept in thousandths of a run (the ledger's unit since D049), so a
charge made before D106 still reads as it was; every charge since is a whole
thousand. A hold is taken for the longest recording a task allows and settled
on what the recording really lasted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PRICE_VERSION = "price-v5-ai-runs"
UNITS_PER_RUN = 1000
# Three runs a month for everyone before anything is charged.
FREE_UNITS_PER_CYCLE = 3 * UNITS_PER_RUN

# The longest recording the price covers; QC refuses anything longer anyway.
MAX_MINUTES = 5
MAX_SECONDS = MAX_MINUTES * 60.0


def whole_runs(runs: float) -> int:
    """`runs` rounded down to a whole run; a hair under one is float noise, not less."""
    return math.floor(round(runs, 6))


def is_whole(runs: float) -> bool:
    """True for 0, 1, 2...: the only prices a learner can count with (D106)."""
    return runs >= 0 and round(runs, 6) == whole_runs(runs)


# The prices in runs (D106: each a whole number of runs).
RUN_PRICES = (
    "first_minute_runs",
    "extra_minute_runs",
    "upgrade_runs",
    "passage_runs",
    "lesson_minute_runs",
)


@dataclass(frozen=True)
class PriceList:
    """What the seller charges, in runs. Read from the settings (`AICEFR_PRICE_*`)."""

    first_minute_runs: float = 1.0  # a scored recording up to one minute
    extra_minute_runs: float = 0.0  # every further started minute (no task is longer)
    idpoint_per_run: int = 2000  # what one run is on NetID (1 IDPoint = 1 VND)
    # D072: an upgraded answer (D069) to a recording no run paid for. D107:
    # the upgrade of a recording scored for a run is part of that run.
    upgrade_runs: float = 1.0
    # D090: one reading passage written around the learner's unclear words,
    # past the one each paid run brings (D107).
    passage_runs: float = 1.0
    # D094: a recording on the lesson path (a step, a review, a retelling, a
    # word or a passage said again), per started minute of speech; the first
    # `lesson_free_per_day` recordings of a Vietnam day are free, and no more
    # than `lesson_daily_cap` are measured in a day. Free since D106.
    lesson_minute_runs: float = 0.0
    lesson_free_per_day: int = 5
    lesson_daily_cap: int = 30
    version: str = PRICE_VERSION

    def __post_init__(self) -> None:
        lowest = min(
            self.first_minute_runs,
            self.extra_minute_runs,
            self.upgrade_runs,
            self.passage_runs,
            self.lesson_minute_runs,
        )
        if lowest < 0 or self.idpoint_per_run < 0:
            raise ValueError("giá không được âm")
        # D106: whole runs only. A fraction from an older price list or the
        # settings counts as its whole part, in the learner's favour.
        for name in RUN_PRICES:
            object.__setattr__(self, name, float(whole_runs(getattr(self, name))))
        if self.lesson_daily_cap < 1:
            raise ValueError("trần bản ghi bài học mỗi ngày phải từ 1 trở lên")
        if not 0 <= self.lesson_free_per_day <= self.lesson_daily_cap:
            raise ValueError("số bản ghi miễn phí mỗi ngày phải từ 0 tới trần mỗi ngày")

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "first_minute_runs": self.first_minute_runs,
            "extra_minute_runs": self.extra_minute_runs,
            "idpoint_per_run": self.idpoint_per_run,
            "upgrade_runs": self.upgrade_runs,
            "passage_runs": self.passage_runs,
            "lesson_minute_runs": self.lesson_minute_runs,
            "lesson_free_per_day": self.lesson_free_per_day,
            "lesson_daily_cap": self.lesson_daily_cap,
            "max_minutes": MAX_MINUTES,
        }


DEFAULT_PRICES = PriceList()


def minutes(seconds: float) -> int:
    """Started minutes, at least one, at most MAX_MINUTES."""
    return max(1, min(MAX_MINUTES, math.ceil(max(0.0, seconds) / 60)))


def units_for(prices: PriceList, seconds: float) -> int:
    """The charge for a recording of `seconds`, in thousandths of a run."""
    runs = prices.first_minute_runs + prices.extra_minute_runs * (minutes(seconds) - 1)
    # A hair under the next thousandth is float noise, not a reason to round up.
    return math.ceil(round(runs * UNITS_PER_RUN, 6))


def upgrade_units(prices: PriceList) -> int:
    """The charge for one upgraded answer (D072), in thousandths of a run."""
    return math.ceil(round(prices.upgrade_runs * UNITS_PER_RUN, 6))


def passage_units(prices: PriceList) -> int:
    """The charge for one reading passage (D090), in thousandths of a run."""
    return math.ceil(round(prices.passage_runs * UNITS_PER_RUN, 6))


def lesson_units(prices: PriceList, seconds: float) -> int:
    """The charge for one recording on the lesson path (D094), in thousandths of a run.

    Priced by the started minutes of SPEECH the recording held (`StepResult.speaking_s`,
    measured by VAD), at least one: a five-second step is one minute's price.
    """
    return math.ceil(round(prices.lesson_minute_runs * minutes(seconds) * UNITS_PER_RUN, 6))


def hold_for(prices: PriceList, max_seconds: float) -> int:
    """What to hold when a recording is submitted: the longest its task allows."""
    return units_for(prices, max_seconds)


def as_idpoint(prices: PriceList, units: int) -> int:
    """Units as IDPoint, for the NetID channel."""
    return round(units * prices.idpoint_per_run / UNITS_PER_RUN)


def as_runs(units: int) -> float:
    """Units as runs, for people to read."""
    return round(units / UNITS_PER_RUN, 3)
