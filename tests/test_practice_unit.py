"""Layer 1 -- UNIT: the exercise bank and the mission rules of D023, which the path's
lessons are built from and checked with (D083: no practice task of its own any more).

No database, no HTTP, no audio. Each test calls one pure function with
hand-written data and checks the exact result. Test case ids (TC-PR-Uxx) and
the acceptance criteria they trace to (AC-4x.y) are listed in
`docs/test/TEST_PLAN_D023.md`.

What this layer guards:

* every "met" mission points at a place in the recording;
* what cannot be measured says "not measured", never "not met";
* every threshold is checked on both sides of the boundary.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from aicefr.contracts import (
    Mission,
    MissionCheck,
    MissionHit,
    MissionKind,
    PracticeResult,
    ReasonCode,
    Transcript,
    Word,
)
from aicefr.practice.bank import (
    BAND_ORDER,
    PATH_ORDER,
    PRACTICE_TASKS,
)
from aicefr.practice.missions import MAX_HITS, MissionChecker, describe_measure, normalize
from aicefr.practice.streak import local_day, streak_length, summarize
from aicefr.storage.task_repository import DEFAULT_TASKS

pytestmark = pytest.mark.unit


def transcript(text: str, step: float = 0.5) -> Transcript:
    words = [
        Word(text=w, start_s=round(i * step, 3), end_s=round(i * step + step * 0.8, 3), prob=0.9)
        for i, w in enumerate(text.split())
    ]
    return Transcript(text=text, words=words, engine="fake", model_version="fake-v1")


class _Task:
    """The least a practice task needs for the checker: id, missions, passage."""

    def __init__(self, *missions: Mission, reference_text: str | None = None) -> None:
        self.task_id = "PR-TEST"
        self.missions = missions
        self.reference_text = reference_text


def one(mission: Mission, text: str, segments=(), reference: str | None = None) -> MissionCheck:
    task = _Task(mission, reference_text=reference)
    return MissionChecker().check(task, transcript(text), segments).checks[0]


def speak(target: float = 30) -> Mission:
    return Mission(kind=MissionKind.SPEAK_SECONDS, target=target, label="speak long enough")


def pause(target: float = 3.0) -> Mission:
    return Mission(kind=MissionKind.MAX_PAUSE, target=target, label="no long silence")


def use(target: int, *words: str) -> Mission:
    return Mission(kind=MissionKind.USE_WORDS, target=target, label="use words", words=words)


def check(kind: MissionKind, measured: float | None, met: bool | None, **kw) -> MissionCheck:
    if measured is None:
        return MissionCheck(
            kind=kind, label="x", target=1, reason=ReasonCode.FEATURE_NOT_COMPUTABLE, **kw
        )
    return MissionCheck(kind=kind, label="x", target=1, measured=measured, met=met, **kw)


# ================================================================= task bank (FR-40)


def test_bank_has_one_task_per_criterion_and_band():
    cells = {(t.criterion, t.band) for t in PRACTICE_TASKS}
    # Five criteria by six bands, A1 to C2 (D059).
    assert len(PRACTICE_TASKS) == 30
    assert cells == {(c, b) for c in PATH_ORDER for b in BAND_ORDER}
    assert len({t.task_id for t in PRACTICE_TASKS}) == 30


def test_every_task_has_missions_tips_and_a_duration_above_the_qc_floor():
    for t in PRACTICE_TASKS:
        assert t.missions and t.tips, t.task_id
        # Below 30 seconds QC flags REVIEW; a practice task must not ask for that.
        assert 30 <= t.min_seconds < t.max_seconds, t.task_id
        for m in t.missions:
            assert all(w == w.lower() for w in m.words), t.task_id


def test_read_aloud_passages_have_no_digits_or_dual_spellings():
    """Digits and words with two spellings make the recogniser write something
    different from what the reader said correctly."""
    for t in PRACTICE_TASKS:
        has_read = any(m.kind is MissionKind.READ_ALOUD for m in t.missions)
        assert has_read == (t.reference_text is not None), t.task_id
        if t.reference_text:
            assert not re.search(r"\d", t.reference_text), t.task_id
            for word in ("favourite", "colour", "practise", "centre", "organise"):
                assert word not in t.reference_text.lower(), (t.task_id, word)


def test_no_practice_topic_overlaps_an_assessment_task():
    """Practising the exam prompt is rehearsal, not practice."""
    for t in PRACTICE_TASKS:
        assert "trực tuyến" not in t.prompt_text and "kỳ thi" not in t.prompt_text, t.task_id
    assert {d[0] for d in DEFAULT_TASKS}.isdisjoint({t.task_id for t in PRACTICE_TASKS})


def test_malformed_missions_are_rejected_at_construction():
    with pytest.raises(ValidationError):
        Mission(kind=MissionKind.USE_WORDS, target=2, label="x")  # no word list
    with pytest.raises(ValidationError):
        Mission(kind=MissionKind.SPEAK_SECONDS, target=30, label="x", words=("a",))
    with pytest.raises(ValidationError):
        Mission(kind=MissionKind.READ_ALOUD, target=80, label="x")  # a share, must be in (0, 1]
    with pytest.raises(ValidationError):
        Mission(kind=MissionKind.SPEAK_SECONDS, target=0, label="x")
    with pytest.raises(ValidationError):
        Mission(kind=MissionKind.SPEAK_SECONDS, target=30, label="")


# ================================================================= mission checker (FR-41)


def test_normalize_strips_punctuation_keeps_apostrophes_and_splits_hyphens():
    assert normalize("First, I'll go. Then “Finally!”") == [
        "first",
        "i'll",
        "go",
        "then",
        "finally",
    ]
    assert normalize("a first-year student") == ["a", "first", "year", "student"]
    assert normalize("don’t") == ["don't"]


def test_normalize_of_empty_or_punctuation_only_text_is_empty():
    assert normalize("") == []
    assert normalize(" ... !? “” ") == []


def test_speaking_time_ignores_silence_at_both_ends():
    c = one(speak(30), "hello there", segments=[(2.0, 20.0), (21.0, 34.5)])
    assert c.measured == pytest.approx(32.5) and c.met is True and c.hits == []


@pytest.mark.parametrize(("end", "met"), [(30.0, True), (29.99, False)])
def test_speaking_time_exactly_at_target_is_met(end, met):
    assert one(speak(30), "a", segments=[(0.0, end)]).met is met


def test_speaking_time_falls_back_to_word_timestamps_without_segments():
    c = one(speak(1), "one two three four", segments=[])
    assert c.measured == pytest.approx(1.9)  # from 0.0 to the end of the last word, 1.5 + 0.4


def test_speaking_time_is_unmeasured_without_segments_or_words():
    t = Transcript(text="", words=[], engine="fake", model_version="fake-v1")
    c = MissionChecker().check(_Task(speak()), t, []).checks[0]
    assert c.measured is None and c.met is None
    assert c.reason is ReasonCode.FEATURE_NOT_COMPUTABLE


def test_longest_pause_counts_only_inner_gaps_and_points_at_the_second():
    c = one(pause(3.0), "a b c", segments=[(0.5, 5.0), (6.0, 12.0), (15.5, 20.0)])
    assert c.measured == pytest.approx(3.5) and c.met is False
    assert c.hits == [MissionHit(text="Khoảng lặng dài nhất 3,5 giây", start_s=12.0)]


@pytest.mark.parametrize(("gap_end", "met"), [(8.0, True), (8.01, False)])
def test_pause_exactly_at_target_is_met(gap_end, met):
    assert one(pause(3.0), "a", segments=[(0.0, 5.0), (gap_end, 10.0)]).met is met


def test_single_segment_means_no_pause():
    c = one(pause(3.0), "a", segments=[(1.0, 30.0)])
    assert c.measured == 0.0 and c.met is True and c.hits == []


def test_pause_is_unmeasured_without_segments_rather_than_zero():
    c = one(pause(3.0), "a b", segments=[])
    assert c.measured is None and c.met is None
    assert c.reason is ReasonCode.FEATURE_NOT_COMPUTABLE


def test_use_words_counts_distinct_items_including_phrases_with_times():
    m = use(3, "first", "then", "after that", "finally")
    c = one(m, "First, wash the rice. Then boil it. After that, wait. Then eat.")
    assert c.measured == 3 and c.met is True
    assert [(h.text, h.start_s) for h in c.hits] == [
        ("first", 0.0),
        ("then", 2.0),
        ("after that", 3.5),
    ]


def test_a_word_used_many_times_counts_once():
    assert one(use(2, "then", "so"), "then then then then").measured == 1


def test_no_listed_word_means_zero_and_no_evidence():
    c = one(use(1, "however"), "I like it a lot")
    assert c.measured == 0 and c.met is False and c.hits == []


def test_unique_words_ignore_fillers_and_case():
    m = Mission(kind=MissionKind.UNIQUE_WORDS, target=5, label="x")
    c = one(m, "um I like uh I LIKE cats and dogs")
    assert c.measured == 5 and c.met is True  # i, like, cats, and, dogs


def test_past_verbs_count_irregular_and_ed_forms_but_not_adjectives_or_present_lookalikes():
    m = Mission(kind=MissionKind.PAST_VERBS, target=4, label="x")
    c = one(m, "I went home, watched films and played games. I need to read. I was interested.")
    assert {h.text for h in c.hits} == {"went", "watched", "played", "was"}
    assert c.met is True


def test_past_verbs_skip_short_words_and_excluded_words():
    m = Mission(kind=MissionKind.PAST_VERBS, target=1, label="x")
    c = one(m, "red bed fed used read need speed")
    assert [h.text for h in c.hits] == ["used"]


def test_evidence_per_mission_is_capped_at_max_hits():
    m = Mission(kind=MissionKind.PAST_VERBS, target=1, label="x")
    c = one(m, "went saw made came took got gave found thought told became left")
    assert c.measured == 12 and len(c.hits) == MAX_HITS


def test_conditionals_need_if_and_a_modal_in_the_same_sentence():
    m = Mission(kind=MissionKind.CONDITIONALS, target=2, label="x")
    c = one(m, "If I had money I would travel. I'd stay home if it rains. If so, fine.")
    assert c.measured == 2 and c.met is True
    assert c.hits[0].start_s == 0.0


@pytest.mark.parametrize(("filler", "counted"), [(11, True), (12, False)])
def test_conditional_modal_must_be_within_12_words_of_if(filler, counted):
    m = Mission(kind=MissionKind.CONDITIONALS, target=1, label="x")
    text = "if " + " ".join(["word"] * filler) + " would"
    assert one(m, text).measured == (1 if counted else 0)


def test_read_aloud_scores_matched_share_and_lists_unheard_words():
    ref = "I am a first-year student and I live near the market."
    m = Mission(kind=MissionKind.READ_ALOUD, target=0.8, label="x")
    full = one(m, "I am a first year student and I live near the market", reference=ref)
    assert full.measured == 1.0 and full.met is True and not full.hits
    partial = one(m, "I am a student and I live near the", reference=ref)
    assert partial.measured == pytest.approx(9 / 12, abs=1e-3)
    assert partial.met is False
    assert [h.text for h in partial.hits] == ["first", "year", "market"]
    assert all(h.start_s is None for h in partial.hits)


def test_read_aloud_without_reference_is_unmeasured():
    m = Mission(kind=MissionKind.READ_ALOUD, target=0.8, label="x")
    c = one(m, "anything at all", reference=None)
    assert c.measured is None and c.reason is ReasonCode.FEATURE_NOT_COMPUTABLE


def test_text_only_transcript_still_counts_but_evidence_has_no_time():
    t = Transcript(text="First, then finally.", words=[], engine="fake", model_version="fake-v1")
    c = MissionChecker().check(_Task(use(2, "first", "finally")), t, []).checks[0]
    assert c.measured == 2 and all(h.start_s is None for h in c.hits)


def test_result_keeps_task_id_and_rules_version():
    result = MissionChecker().check(_Task(speak(1)), transcript("a b"), [(0.0, 2.0)])
    assert result.task_id == "PR-TEST" and result.rules_version == "mission-v1"


def test_attempt_conclusion_is_derived_from_missions():
    met = check(MissionKind.SPEAK_SECONDS, 2, True)
    unmet = check(MissionKind.SPEAK_SECONDS, 0.5, False)
    unknown = check(MissionKind.MAX_PAUSE, None, None)
    assert PracticeResult(task_id="t", checks=[met, met]).completed is True
    assert PracticeResult(task_id="t", checks=[met, unmet, unknown]).completed is False
    assert PracticeResult(task_id="t", checks=[met, unknown]).completed is None
    assert PracticeResult(task_id="t", checks=[met, unknown]).met_count == 1


def test_practice_result_needs_at_least_one_mission():
    with pytest.raises(ValidationError):
        PracticeResult(task_id="t", checks=[])


def test_unmeasured_mission_needs_a_reason_and_no_conclusion():
    with pytest.raises(ValidationError):
        MissionCheck(kind=MissionKind.MAX_PAUSE, label="b", target=1)
    with pytest.raises(ValidationError):
        MissionCheck(kind=MissionKind.MAX_PAUSE, label="b", target=1, measured=2.0)
    with pytest.raises(ValidationError):
        MissionCheck(
            kind=MissionKind.MAX_PAUSE,
            label="b",
            target=1,
            measured=2.0,
            met=True,
            reason=ReasonCode.FEATURE_NOT_COMPUTABLE,
        )


def test_measure_description_per_mission_kind():
    assert describe_measure(check(MissionKind.SPEAK_SECONDS, 32.75, True)) == "Bạn nói 32,8 giây"
    assert describe_measure(check(MissionKind.MAX_PAUSE, 1.25, True)) == (
        "Khoảng lặng dài nhất 1,2 giây"
    )
    assert describe_measure(check(MissionKind.READ_ALOUD, 0.876, True)) == ("Máy nhận ra 88% số từ")
    assert describe_measure(check(MissionKind.UNIQUE_WORDS, 41, True)) == (
        "Bạn dùng 41 từ khác nhau"
    )
    assert describe_measure(check(MissionKind.USE_WORDS, 3, True)) == "Đếm được 3"
    assert describe_measure(check(MissionKind.MAX_PAUSE, None, None)) == "Chưa đo được"


# ================================================================= streak (FR-43)


def d(day: int) -> date:
    return date(2026, 10, day)


def test_streak_counts_consecutive_days_and_survives_until_today_ends():
    assert streak_length({d(4), d(5), d(6)}, d(6)) == 3
    assert streak_length({d(4), d(5)}, d(6)) == 2
    assert streak_length(set(), d(6)) == 0


def test_one_rest_day_per_week_keeps_streak_but_does_not_count():
    assert streak_length({d(1), d(2), d(4), d(5)}, d(5)) == 4
    # Two missed days in a row break it.
    assert streak_length({d(1), d(2), d(5), d(6)}, d(6)) == 2
    # Two rest days within 7 days: the second one breaks it.
    assert streak_length({d(1), d(3), d(5), d(6)}, d(6)) == 3


def test_rest_days_exactly_seven_days_apart_are_allowed():
    days = {d(n) for n in (1, 2, 4, 5, 6, 7, 8, 9, 11, 12)}  # rest on the 3rd and the 10th
    assert streak_length(days, d(12)) == 10
    days = {d(n) for n in (1, 2, 3, 5, 6, 7, 8, 9, 11, 12)}  # rest on the 4th and the 10th: 6 apart
    assert streak_length(days, d(12)) == 7


def test_rest_yesterday_while_today_is_open_keeps_streak():
    assert streak_length({d(3), d(4)}, d(6)) == 2
    assert streak_length({d(3)}, d(6)) == 0


@pytest.mark.parametrize(
    ("moment", "day"),
    [
        ("2026-10-05T16:59:59+00:00", 5),
        ("2026-10-05T17:00:00+00:00", 6),
        ("2026-10-05T17:00:00", 6),  # no time zone means UTC
    ],
)
def test_days_follow_vietnam_time(moment, day):
    assert local_day(moment) == d(day)


def test_summary_counts_today_and_seven_days():
    s = summarize(
        ["2026-10-06T01:00:00+00:00", "2026-10-06T02:00:00+00:00", "2026-10-04T01:00:00+00:00"],
        datetime(2026, 10, 6, 5, tzinfo=UTC),
        goal=2,
    )
    assert s.today == 2 and s.goal_met and s.practiced_today
    assert s.streak == 2  # the 4th and the 6th; the 5th is a rest day
    assert [day for day, _ in s.week] == [date(2026, 9, 30)] + [d(n) for n in range(1, 7)]
    assert s.week[-1] == (d(6), 2) and s.week[-3] == (d(4), 1)


def test_summary_before_practising_today():
    s = summarize(["2026-10-05T01:00:00+00:00"], datetime(2026, 10, 6, 5, tzinfo=UTC), goal=2)
    assert s.today == 0 and not s.goal_met and not s.practiced_today and s.streak == 1
