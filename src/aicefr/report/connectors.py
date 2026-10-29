"""Which linking words a response uses: the one cohesion signal a transcript carries (D061).

Coherence in the CEFR is about linking ideas into a connected text. Of all of
that, the machine can see exactly one thing: the connectors that appear in the
transcript. It cannot see whether they join the right ideas, how the response
is organised, or whether the listener could follow it.

What it counts is the number of DIFFERENT connectors. Checked against
held-out responses rated by examiners, the variety of connectors moves with
the rating while their sheer frequency does not: "and ... and ... and" is
many connectors and one kind. So a report shows the kinds used, never a rate.

The list is grouped by how common the connectors are in learner speech; the
grouping is a teaching aid, not a CEFR level, and waits for review by the
Foreign Languages teachers like the band descriptors (A-03).
"""

from __future__ import annotations

import re

from aicefr.contracts import Word

# Single words and fixed phrases, lower case. A phrase is matched as whole
# words in order, so "so" does not match inside "also" and "as well" does not
# match "as well as" twice.
BASIC: tuple[str, ...] = ("and", "but", "or", "so", "because", "then", "also")
COMMON: tuple[str, ...] = (
    "first",
    "firstly",
    "secondly",
    "finally",
    "after that",
    "for example",
    "for instance",
    "however",
    "although",
    "if",
    "when",
    "while",
    "as well",
    "actually",
    "in my opinion",
)
ADVANCED: tuple[str, ...] = (
    "on the other hand",
    "in addition",
    "therefore",
    "whereas",
    "despite",
    "in spite of",
    "as a result",
    "moreover",
    "furthermore",
    "even though",
    "in contrast",
    "instead",
    "otherwise",
    "unless",
    "nevertheless",
    "nonetheless",
    "consequently",
    "thus",
    "hence",
    "provided that",
    "in conclusion",
    "to sum up",
    "meanwhile",
)

GROUP_NAMES = {"basic": "cơ bản", "common": "thông dụng", "advanced": "nâng cao"}
_GROUPS = (("advanced", ADVANCED), ("common", COMMON), ("basic", BASIC))


def _tokens(words: list[Word]) -> list[str]:
    out = []
    for w in words:
        out.extend(re.findall(r"[a-z']+", w.text.lower()))
    return out


def connectors_used(words: list[Word]) -> dict[str, str]:
    """Each connector the response uses, in order of first use, with its group.

    Longer phrases are matched first and their words consumed, so "on the
    other hand" is one connector and does not also count as "on".
    """
    toks = _tokens(words)
    phrases = sorted(
        ((tuple(p.split()), group) for group, items in _GROUPS for p in items),
        key=lambda pg: -len(pg[0]),
    )
    found: dict[int, tuple[str, str]] = {}
    taken = [False] * len(toks)
    for phrase, group in phrases:
        n = len(phrase)
        for i in range(len(toks) - n + 1):
            if not any(taken[i : i + n]) and tuple(toks[i : i + n]) == phrase:
                found[i] = (" ".join(phrase), group)
                taken[i : i + n] = [True] * n
    out: dict[str, str] = {}
    for _, (text, group) in sorted(found.items()):
        out.setdefault(text, group)
    return out
