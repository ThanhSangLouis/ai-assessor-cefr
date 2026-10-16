"""Deterministic minimum-edit alignment of reference and recognized tokens."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import Field

from aicefr.lessons.text import normalize_text, same_word
from aicefr.practice.contracts import FrozenModel

MAX_ALIGNMENT_TOKENS = 512


class AlignmentOp(StrEnum):
    MATCH = "MATCH"
    SUBSTITUTE = "SUBSTITUTE"
    DELETE = "DELETE"


class AlignmentPair(FrozenModel):
    ref_index: int = Field(ge=0)
    operation: AlignmentOp
    hyp_index: int | None = Field(default=None, ge=0)


class Alignment(FrozenModel):
    pairs: tuple[AlignmentPair, ...]
    inserted_indices: tuple[int, ...]
    edit_distance: int = Field(ge=0)


def align(reference: Sequence[str], heard: Sequence[str]) -> Alignment:
    """Levenshtein alignment; ties prefer diagonal, then delete, then insert."""
    n, m = len(reference), len(heard)
    if n > MAX_ALIGNMENT_TOKENS or m > MAX_ALIGNMENT_TOKENS:
        raise ValueError(f"alignment inputs are limited to {MAX_ALIGNMENT_TOKENS} tokens each")
    distance = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        distance[i][0] = i
    for j in range(1, m + 1):
        distance[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diagonal = distance[i - 1][j - 1] + (
                0 if same_word(reference[i - 1], heard[j - 1]) else 1
            )
            distance[i][j] = min(diagonal, distance[i - 1][j] + 1, distance[i][j - 1] + 1)
    i, j = n, m
    reverse_pairs: list[AlignmentPair] = []
    inserted: list[int] = []
    while i or j:
        if i and j:
            cost = 0 if same_word(reference[i - 1], heard[j - 1]) else 1
            if distance[i][j] == distance[i - 1][j - 1] + cost:
                reverse_pairs.append(
                    AlignmentPair(
                        ref_index=i - 1,
                        operation=(
                            AlignmentOp.MATCH
                            if cost == 0
                            and normalize_text(reference[i - 1]) == normalize_text(heard[j - 1])
                            else AlignmentOp.SUBSTITUTE
                        ),
                        hyp_index=j - 1,
                    )
                )
                i -= 1
                j -= 1
                continue
        if i and distance[i][j] == distance[i - 1][j] + 1:
            reverse_pairs.append(AlignmentPair(ref_index=i - 1, operation=AlignmentOp.DELETE))
            i -= 1
            continue
        if j:
            inserted.append(j - 1)
            j -= 1
    return Alignment(
        pairs=tuple(reversed(reverse_pairs)),
        inserted_indices=tuple(sorted(inserted)),
        edit_distance=distance[n][m],
    )
