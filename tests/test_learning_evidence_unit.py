"""Layer 1 for the learning-evidence features D039-D042: pure functions only.

D039 names the Vietnamese-learner pattern behind a misheard word; D041 turns
review sessions into teacher minutes; D042
decides whether a change is larger than the instrument's error. Each is a
claim about learners or teachers, so each is tested where it must stay quiet
as much as where it must speak.
"""

from __future__ import annotations

import math

import pytest

from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
from aicefr.pronunciation.vietnamese import (
    MIN_OPPORTUNITIES,
    Pattern,
    classify,
    opportunities,
    profile,
)
from aicefr.research.reliable_change import (
    MIN_PAIRS,
    reliable_change,
    retest_pairs,
    sem_from_pairs,
)
from aicefr.research.teacher_time import (
    IDLE_CAP_MINUTES,
    MIN_SAMPLES,
    kpi,
    session_minutes,
    wilson,
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


# ================================================================= D040

# ================================================================= D041


def test_idle_review_sessions_are_left_out_and_counted():
    sessions = [
        {"opened_at": "2026-10-01T10:00:00+00:00", "decided_at": "2026-10-01T10:04:00+00:00",
         "action": "decision"},
        {"opened_at": "2026-10-01T10:00:00+00:00", "decided_at": "2026-10-01T11:00:00+00:00",
         "action": "decision"},
        {"opened_at": "2026-10-01T10:00:00+00:00", "decided_at": None},
    ]  # fmt: skip
    kept, idle = session_minutes(sessions)
    assert kept == [4.0] and idle == 1
    assert IDLE_CAP_MINUTES == 30


def test_wilson_interval_matches_the_textbook_value():
    lo, hi = wilson(8, 10)
    assert math.isclose(lo, 0.4902, abs_tol=1e-3) and math.isclose(hi, 0.9433, abs_tol=1e-3)
    assert wilson(0, 0) is None


def test_kpi_reports_time_saved_only_from_enough_samples():
    few = kpi([2.0] * (MIN_SAMPLES - 1), 0, [8.0] * 10, 3, 4, 5, 6)
    assert few["review_with_machine"]["median_minutes"] is None
    assert few["time_saved"] is None
    enough = kpi([2.0] * MIN_SAMPLES, 1, [8.0] * MIN_SAMPLES, 3, 4, 0, 0)
    assert enough["time_saved"] == 0.75
    assert enough["review_with_machine"]["idle_left_out"] == 1
    assert enough["settled_alone"]["rate"] == 0.75
    assert enough["band_kept"]["rate"] is None and enough["band_kept"]["ci95"] is None


# ================================================================= D042


def _rows(pairs: list[tuple[float, float]], hours: int = 2) -> list[dict]:
    out = []
    for i, (a, b) in enumerate(pairs):
        out.append({"account_id": f"u{i}", "task_id": "P3", "overall_0_6": a,
                    "created_at": "2026-10-01T08:00:00+00:00"})  # fmt: skip
        out.append({"account_id": f"u{i}", "task_id": "P3", "overall_0_6": b,
                    "created_at": f"2026-10-01T{8 + hours:02d}:00:00+00:00"})  # fmt: skip
    return out


def test_retest_pairs_use_each_response_once_and_respect_the_window():
    three = [
        {"account_id": "u", "task_id": "P3", "overall_0_6": s, "created_at": t}
        for s, t in [
            (3.0, "2026-10-01T08:00:00+00:00"),
            (3.2, "2026-10-01T09:00:00+00:00"),
            (3.4, "2026-10-01T10:00:00+00:00"),
        ]
    ]
    assert retest_pairs(three) == [(3.0, 3.2)]
    far = _rows([(3.0, 3.5)], hours=0)
    far[1]["created_at"] = "2026-10-05T08:00:00+00:00"
    assert retest_pairs(far) == []


def test_sem_is_sd_of_differences_over_root_two_and_needs_enough_pairs():
    pairs = [(3.0, 3.0 + d) for d in (0.2, -0.2) * (MIN_PAIRS // 2)]
    sem = sem_from_pairs(retest_pairs(_rows(pairs)))
    sd = math.sqrt(sum(0.2**2 for _ in pairs) / (len(pairs) - 1))
    assert math.isclose(sem, sd / math.sqrt(2))
    assert sem_from_pairs(pairs[: MIN_PAIRS - 1]) is None


def test_reliable_change_verdicts():
    assert reliable_change([3.0], 0.2)["verdict"] == "chua_du_du_lieu"
    assert reliable_change([3.0, 4.0], None)["verdict"] == "chua_co_sai_so"
    up = reliable_change([3.0, 3.0, 3.0, 4.0, 4.0, 4.0], 0.2)
    assert up["verdict"] == "tien_bo" and up["k"] == 3 and up["difference"] == 1.0
    assert reliable_change([4.0, 4.0, 3.0, 3.0], 0.2)["verdict"] == "giam"
    small = reliable_change([3.0, 3.0, 3.1, 3.1], 0.3)
    assert small["verdict"] == "chua_vuot_sai_so"
    assert small["threshold"] == round(1.96 * 0.3 * math.sqrt(2 / 2), 3)
