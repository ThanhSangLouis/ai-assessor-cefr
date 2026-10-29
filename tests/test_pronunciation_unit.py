"""Pure pronunciation classification and evidence-profile checks."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aicefr.pronunciation.vietnamese import (
    MAX_EXAMPLES,
    MIN_OPPORTUNITIES,
    Pattern,
    classify,
    opportunities,
    profile,
)


@pytest.mark.parametrize(
    ("expected", "said", "pattern"),
    [
        ("worked", "work", Pattern.ED_ENDING),
        ("played", "playe", Pattern.ED_ENDING),
        ("cats", "cat", Pattern.S_ENDING),
        ("watches", "watch", Pattern.S_ENDING),
        ("think", "tink", Pattern.TH_SOUND),
        ("this", "dis", Pattern.TH_SOUND),
        ("with", "wit", Pattern.TH_SOUND),
        ("street", "sreet", Pattern.CLUSTER),
        ("play", "pay", Pattern.CLUSTER),
        ("night", "nigh", Pattern.FINAL_CONSONANT),
        ("help", "hel", Pattern.FINAL_CONSONANT),
        ("because", "becau", Pattern.FINAL_CONSONANT),
    ],
)
def test_classifier_maps_word_gaps_to_the_contract_patterns(expected, said, pattern):
    assert classify(expected, said) is pattern


@pytest.mark.parametrize(
    ("expected", "said"),
    [
        ("friendly", "friendly"),
        ("like", "lie"),
        ("people", "purple"),
        ("dog", None),
        ("a", "the"),
    ],
)
def test_classifier_silently_ignores_unexplained_word_gaps(expected, said):
    assert classify(expected, said) is None


def test_contract_pattern_ids_match_the_m13_specification():
    # W7-S03: the IDs the lessons, plans and pages already store and display
    # (M13 Specification updated to match, pending review).
    assert [pattern.value for pattern in Pattern] == [
        "ed_ending",
        "s_ending",
        "final_consonant",
        "th_sound",
        "cluster",
    ]


def test_opportunities_count_words_that_can_show_each_pattern():
    assert opportunities("worked") == {Pattern.ED_ENDING, Pattern.FINAL_CONSONANT}
    assert opportunities("street") == {Pattern.CLUSTER, Pattern.FINAL_CONSONANT}
    assert opportunities("think") == {Pattern.TH_SOUND, Pattern.FINAL_CONSONANT}
    assert Pattern.FINAL_CONSONANT in opportunities("make")
    assert Pattern.S_ENDING not in opportunities("bus")
    assert opportunities("a") == set()


def _attempt(
    expected: str,
    said: str | None,
    *,
    measured: bool = True,
    teacher: str | None = None,
) -> dict:
    mark = SimpleNamespace(
        text=expected,
        said=said,
        status=SimpleNamespace(value="missed" if said else "heard"),
        teacher=SimpleNamespace(value=teacher) if teacher else None,
        start_s=None,
    )
    result = SimpleNamespace(measured=measured, words=[mark], step_id="step-1")
    return {
        "result": result,
        "lesson_id": "lesson-1",
        "attempt_id": "attempt-1",
        "created_at": "2026-10-01T10:00:00+07:00",
    }


def test_profile_requires_eight_opportunities_and_caps_examples_at_five():
    one = _attempt("worked", "work")
    profile_at_seven = profile([one] * (MIN_OPPORTUNITIES - 1))
    pattern_at_seven = next(
        item for item in profile_at_seven["patterns"] if item["pattern"] == "ed_ending"
    )
    assert pattern_at_seven["rate"] is None

    profile_at_eight = profile([one] * MIN_OPPORTUNITIES)
    pattern_at_eight = next(
        item for item in profile_at_eight["patterns"] if item["pattern"] == "ed_ending"
    )
    assert pattern_at_eight["rate"] == 1.0
    assert len(pattern_at_eight["examples"]) == MAX_EXAMPLES


def test_profile_respects_teacher_corrections_and_ignores_unmeasured_steps():
    corrected = _attempt("worked", "work", teacher="heard")
    unmeasured = _attempt("worked", "work", measured=False)

    result = profile([corrected, unmeasured])
    pattern = next(item for item in result["patterns"] if item["pattern"] == "ed_ending")

    assert pattern["errors"] == 0
    assert result["steps"] == 1
