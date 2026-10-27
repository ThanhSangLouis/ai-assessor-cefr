"""Align what was heard with what was expected, word by word (D025).

A Levenshtein alignment, not `difflib`: difflib finds long matching blocks and
does not yield a minimal edit sequence, so it cannot say how many words were
left out, added or replaced. Here every reference word ends up either matched
to one heard word, replaced by one, or not heard at all; heard words left over
are insertions.

About 30 lines of dynamic programming, no dependency. Texts in a lesson are
short (a few hundred words at most), so the quadratic table stays small.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class Op(str, Enum):
    MATCH = "match"
    SUBSTITUTE = "substitute"
    DELETE = "delete"  # a reference word nobody heard


@dataclass(frozen=True)
class Pair:
    """One reference word and the heard word aligned with it, if any."""

    ref_index: int
    op: Op
    hyp_index: int | None


def align(
    reference: list[str],
    heard: list[str],
    equal: Callable[[str, str], bool] | None = None,
) -> tuple[list[Pair], list[int]]:
    """Minimal-edit alignment of `heard` against `reference`.

    Returns one Pair per reference word, in order, and the indices of heard
    words that were inserted. Ties prefer a match, then a substitution, so a
    word heard in a slightly different form is still attached to its place.
    """
    eq = equal or (lambda a, b: a == b)
    n, m = len(reference), len(heard)
    # cost[i][j]: edits to turn reference[:i] into heard[:j]
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        ri = reference[i - 1]
        row, prev = cost[i], cost[i - 1]
        for j in range(1, m + 1):
            sub = prev[j - 1] + (0 if eq(ri, heard[j - 1]) else 1)
            row[j] = min(sub, prev[j] + 1, row[j - 1] + 1)

    pairs: list[Pair] = []
    inserted: list[int] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            same = eq(reference[i - 1], heard[j - 1])
            if cost[i][j] == cost[i - 1][j - 1] + (0 if same else 1):
                pairs.append(Pair(i - 1, Op.MATCH if same else Op.SUBSTITUTE, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            pairs.append(Pair(i - 1, Op.DELETE, None))
            i -= 1
            continue
        inserted.append(j - 1)
        j -= 1
    pairs.reverse()
    inserted.reverse()
    return pairs, inserted
