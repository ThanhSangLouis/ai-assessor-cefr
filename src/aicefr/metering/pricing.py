"""The price list of the metered channel: priced by the recording, measured in tokens (D057).

What the learner pays is fixed by the recording, as every worker on NetID is
priced (team decision, 24/10/2026): the first minute is one run (2,000 IDPoint
at the agreed 1 IDPoint = 1 VND), every further started minute 0.7 run, up to
five minutes, and a practice attempt half of that. The seller sets all four
numbers (`AICEFR_PRICE_*`, `AICEFR_IDPOINT_PER_RUN`).

What a recording really used is measured in tokens and kept with each charge,
for the cost per request and the reconciliation with NetID -- the recogniser is
a token model too:

* **input tokens** are Whisper's audio tokens: 1500 per started 30-second
  window, and one more window for the language check (D022);
* **output tokens** are the text tokens the decoder produced, counted by the
  recogniser (`Transcript.output_tokens`), or estimated from the words where
  it cannot count them, and marked so.

Charges are kept in thousandths of a run, integers so no sum ever rounds. A hold
is taken for the longest recording a task allows and settled on what the
recording really lasted.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

PRICE_VERSION = "price-v3-per-recording"
UNITS_PER_RUN = 1000
# Three runs a month for everyone before anything is charged.
FREE_UNITS_PER_CYCLE = 3 * UNITS_PER_RUN

WINDOW_S = 30.0
AUDIO_TOKENS_PER_WINDOW = 1500
LANGUAGE_CHECK_WINDOWS = 1
# English text in Whisper's tokenizer: about four tokens for every three words.
TOKENS_PER_WORD = 4 / 3
# The longest recording the price covers; QC refuses anything longer anyway.
MAX_MINUTES = 5
MAX_SECONDS = MAX_MINUTES * 60.0


class Action(str, Enum):
    ASSESS = "assess"
    PRACTICE = "practice"


@dataclass(frozen=True)
class PriceList:
    """What the seller charges, in runs. Read from the settings (`AICEFR_PRICE_*`)."""

    first_minute_runs: float = 1.0  # a recording up to one minute
    extra_minute_runs: float = 0.7  # every further started minute
    practice_factor: float = 0.5  # practice is cheaper, to encourage it
    idpoint_per_run: int = 2000  # what one run is on NetID (1 IDPoint = 1 VND)
    version: str = PRICE_VERSION

    def __post_init__(self) -> None:
        if min(self.first_minute_runs, self.extra_minute_runs) < 0 or self.idpoint_per_run < 0:
            raise ValueError("giá không được âm")
        if not 0 < self.practice_factor <= 1:
            raise ValueError("hệ số bài luyện tập phải trong (0; 1]")

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "first_minute_runs": self.first_minute_runs,
            "extra_minute_runs": self.extra_minute_runs,
            "practice_factor": self.practice_factor,
            "idpoint_per_run": self.idpoint_per_run,
            "max_minutes": MAX_MINUTES,
        }


DEFAULT_PRICES = PriceList()


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    estimated: bool = False  # the output count came from words, not the recogniser


def windows(seconds: float) -> int:
    """Started 30-second windows, at least one, up to the longest priced recording."""
    return max(1, math.ceil(min(max(0.0, seconds), MAX_SECONDS) / WINDOW_S))


def input_tokens(seconds: float) -> int:
    return AUDIO_TOKENS_PER_WINDOW * (windows(seconds) + LANGUAGE_CHECK_WINDOWS)


def usage_of(seconds: float, output_tokens: int | None, words: int | None = None) -> TokenUsage:
    """What one recording used: counted output tokens, or an estimate from its words."""
    if output_tokens is not None:
        return TokenUsage(input_tokens(seconds), max(0, int(output_tokens)))
    estimate = math.ceil(max(0, words or 0) * TOKENS_PER_WORD)
    return TokenUsage(input_tokens(seconds), estimate, estimated=True)


def minutes(seconds: float) -> int:
    """Started minutes, at least one, at most MAX_MINUTES."""
    return max(1, min(MAX_MINUTES, math.ceil(max(0.0, seconds) / 60)))


def units_for(prices: PriceList, action: Action, seconds: float) -> int:
    """The charge for a recording of `seconds`, in thousandths of a run."""
    runs = prices.first_minute_runs + prices.extra_minute_runs * (minutes(seconds) - 1)
    if action is Action.PRACTICE:
        runs *= prices.practice_factor
    # A hair under the next thousandth is float noise, not a reason to round up.
    return math.ceil(round(runs * UNITS_PER_RUN, 6))


def hold_for(prices: PriceList, action: Action, max_seconds: float) -> int:
    """What to hold when a recording is submitted: the longest its task allows."""
    return units_for(prices, action, max_seconds)


def as_idpoint(prices: PriceList, units: int) -> int:
    """Units as IDPoint, for the NetID channel."""
    return round(units * prices.idpoint_per_run / UNITS_PER_RUN)


def as_runs(units: int) -> float:
    """Units as runs, for people to read."""
    return round(units / UNITS_PER_RUN, 3)
