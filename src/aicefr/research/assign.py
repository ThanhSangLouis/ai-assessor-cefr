"""Who rates what, and in which order, for a blind double-rating batch (D030).

The protocol (docs/plan/KE_HOACH_KHAO_SAT.md §6.1) asks for two independent
raters per response and a separate random order for each rater, so fatigue
does not fall on the same responses for everybody. With two raters both rate
every response; with more, responses go round the pairs of raters in turn, so
every rater carries about the same load and every pair meets about as often.

Everything is drawn from one seed, recorded with the batch: the same eligible
responses, raters and seed always give the same plan, which is what lets the
study say how its sample and its orders were made.

A rater who has already seen the machine's result for a response is not blind
to it any more, so the plan never gives them that response (`exclude`).
"""

from __future__ import annotations

import itertools
import random
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Planned:
    response_id: str
    rater_id: str
    slot: int  # 1 or 2 for the primary raters, 3 for the adjudicator
    position: int  # 1-based place in this rater's own order


def sample(response_ids: list[str], limit: int | None, seed: int) -> list[str]:
    """Up to `limit` responses drawn at random (all of them when limit is None)."""
    pool = sorted(set(response_ids))
    if limit is None or limit >= len(pool):
        return pool
    return sorted(random.Random(seed).sample(pool, limit))


def plan(
    response_ids: list[str],
    rater_ids: list[str],
    seed: int,
    exclude: Mapping[str, set[str]] | None = None,
) -> list[Planned]:
    """Two distinct raters for every response, loads balanced, an order per rater.

    `exclude` names, per response, the raters who may not rate it. Such a
    response goes to the next pair in turn with neither of them in it; a
    response no pair can take is left out of the plan, for the caller to report.
    Without exclusions the plan is exactly the one the seed always gave.
    """
    raters = sorted(set(rater_ids))
    if len(raters) < 2:
        raise ValueError("cần ít nhất hai giám khảo")
    exclude = exclude or {}
    rng = random.Random(seed)
    responses = sorted(set(response_ids))
    rng.shuffle(responses)
    pairs = list(itertools.combinations(raters, 2))
    rng.shuffle(pairs)
    drawn: list[tuple[str, str, int]] = []
    for i, response_id in enumerate(responses):
        barred = exclude.get(response_id, set())
        turn = [pairs[(i + k) % len(pairs)] for k in range(len(pairs))]
        pair = next((p for p in turn if not barred.intersection(p)), None)
        if pair is None:
            continue
        first, second = pair
        # Which of the two is "rater 1" is drawn too: slot order is not a
        # property of the person.
        if rng.random() < 0.5:
            first, second = second, first
        drawn += [(response_id, first, 1), (response_id, second, 2)]
    return _ordered(drawn, rng, start={})


def adjudication(
    response_ids: list[str], adjudicator_id: str, seed: int, start: int = 0
) -> list[Planned]:
    """Third ratings by one adjudicator, in their own random order after `start`."""
    rng = random.Random(seed)
    drawn = [(response_id, adjudicator_id, 3) for response_id in sorted(set(response_ids))]
    return _ordered(drawn, rng, start={adjudicator_id: start})


def reassignment(
    slots: list[tuple[str, int]], rater_id: str, seed: int, start: int = 0
) -> list[Planned]:
    """Sheets handed to another rater in the slots they had, in that rater's own
    random order after `start` -- for sheets that went void because their first
    rater saw the machine's result."""
    rng = random.Random(seed)
    drawn = [(response_id, rater_id, slot) for response_id, slot in sorted(set(slots))]
    return _ordered(drawn, rng, start={rater_id: start})


def _ordered(
    drawn: list[tuple[str, str, int]], rng: random.Random, start: dict[str, int]
) -> list[Planned]:
    by_rater: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for item in drawn:
        by_rater[item[1]].append(item)
    out: list[Planned] = []
    for rater in sorted(by_rater):
        items = by_rater[rater]
        rng.shuffle(items)
        first = start.get(rater, 0)
        out += [
            Planned(response_id, rater_id, slot, first + i)
            for i, (response_id, rater_id, slot) in enumerate(items, start=1)
        ]
    return out
