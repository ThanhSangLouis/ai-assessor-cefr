"""Layer 1 for the learning-evidence feature D039: pure functions only.

D039 names the Vietnamese-learner pattern behind a misheard word. It is a claim
about learners, so it is tested where it must stay quiet as much as where it
must speak. (D040-D042 were removed with D078.)
"""

from __future__ import annotations

import pytest

from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
from aicefr.pronunciation.vietnamese import (
    MIN_OPPORTUNITIES,
    Pattern,
    classify,
    opportunities,
    profile,
)

pytestmark = pytest.mark.unit

# ================================================================= D039


@pytest.mark.parametrize(
    ("expected", "said", "pattern"),
    [
        ("worked", "work", Pattern.ED_ENDING),
        ("played", "playe", Pattern.ED_ENDING),
        ("cats", "cat", Pattern.S_ENDING),
        ("watches", "watch", Pattern.S_ENDING),
        ("think", "tink", Pattern.TH_SOUND),
        ("this", "dis", Pattern.TH_SOUND),
        ("street", "sreet", Pattern.CLUSTER),
        ("play", "pay", Pattern.CLUSTER),
        ("night", "nigh", Pattern.FINAL_CONSONANT),
        ("help", "hel", Pattern.FINAL_CONSONANT),
        ("because", "becau", Pattern.FINAL_CONSONANT),
    ],
)
def test_classify_names_the_pattern_behind_a_spelling_gap(expected, said, pattern):
    assert classify(expected, said) is pattern


@pytest.mark.parametrize(
    ("expected", "said"),
    [
        ("friendly", "friendly"),  # heard as written
        ("like", "lie"),  # a different word, not a dropped ending
        ("people", "purple"),
        ("dog", None),  # nothing heard at all: "missed", never a pattern
        ("a", "the"),
    ],
)
def test_classify_stays_silent_when_no_pattern_explains_the_gap(expected, said):
    assert classify(expected, said) is None


def test_opportunities_count_what_a_word_lets_the_speaker_show():
    assert opportunities("worked") == {Pattern.ED_ENDING, Pattern.FINAL_CONSONANT}
    assert opportunities("street") == {Pattern.CLUSTER, Pattern.FINAL_CONSONANT}
    assert opportunities("think") == {Pattern.TH_SOUND, Pattern.FINAL_CONSONANT}
    # Silent e is not a final sound; "bus" is not a plural.
    assert Pattern.FINAL_CONSONANT in opportunities("make")
    assert Pattern.S_ENDING not in opportunities("bus")
    assert opportunities("a") == set()


def _attempt(marks: list[tuple[str, str | None, WordStatus]], measured: bool = True, **extra):
    words = [
        WordMark(index=i, text=t, said=s, status=st, **extra) for i, (t, s, st) in enumerate(marks)
    ]
    result = StepResult(
        step_id="s1", kind=StepKind.REPEAT, passed=True, measured=measured, words=words
    )
    return {"result": result, "lesson_id": "L1", "attempt_id": "a1", "created_at": "2026-10-01"}


def test_profile_reports_a_rate_only_from_enough_opportunities():
    missed = WordStatus.MISSED
    one = _attempt([("worked", "work", missed), ("cats", "cats", WordStatus.HEARD)])
    p = profile([one])
    ed = next(f for f in p["patterns"] if f["pattern"] == "ed_ending")
    assert (ed["errors"], ed["opportunities"], ed["enough"], ed["rate"]) == (1, 1, False, None)

    p = profile([one] * MIN_OPPORTUNITIES)
    ed = next(f for f in p["patterns"] if f["pattern"] == "ed_ending")
    assert ed["enough"] and ed["rate"] == 1.0
    assert len(ed["examples"]) == 5  # capped
    assert p["patterns"][0]["pattern"] == "ed_ending"  # enough evidence sorts first


def test_profile_respects_teacher_corrections_and_skips_unmeasured_steps():
    heard_by_teacher = _attempt([("worked", "work", WordStatus.MISSED)], teacher=WordStatus.HEARD)
    unmeasured = _attempt([("worked", "work", WordStatus.MISSED)], measured=False)
    p = profile([heard_by_teacher, unmeasured])
    ed = next(f for f in p["patterns"] if f["pattern"] == "ed_ending")
    assert ed["errors"] == 0
    assert p["steps"] == 1
