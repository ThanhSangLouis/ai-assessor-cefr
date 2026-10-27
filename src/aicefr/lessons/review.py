"""Spaced review in Leitner boxes (D025).

A word the machine did not hear, or a free talk the learner gave, comes back
after 1 day; a good review moves it on to 3 days, then 7, then it is done; a
poor one sends it back to 1 day. Gaps of 1 to 7 days help fluency as much as
each other (Kakitani & Kormos 2024), and spacing beats massing (Cepeda et al.
2006). A rule this simple is one a teacher can explain to a class, which a
fitted forgetting curve is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

BOX_DAYS = {1: 1, 2: 3, 3: 7}
LAST_BOX = max(BOX_DAYS)
# Reviews offered in one session at most; the rest wait for the next day.
SESSION_WORDS = 6
SESSION_TALKS = 1


@dataclass(frozen=True)
class Schedule:
    box: int
    due: date | None  # None once the item is done

    @property
    def done(self) -> bool:
        return self.due is None


def first_schedule(today: date) -> Schedule:
    return Schedule(1, today + timedelta(days=BOX_DAYS[1]))


def after_review(box: int, passed: bool, today: date) -> Schedule:
    """Where an item goes after one review."""
    if not passed:
        return Schedule(1, today + timedelta(days=BOX_DAYS[1]))
    if box >= LAST_BOX:
        return Schedule(LAST_BOX + 1, None)
    nxt = box + 1
    return Schedule(nxt, today + timedelta(days=BOX_DAYS[nxt]))
