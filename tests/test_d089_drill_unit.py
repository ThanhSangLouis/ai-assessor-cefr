"""D089 unit layer: which words are said again, how a take is judged, how it is kept.

* the words offered are the transcript's unsure words, plain ones only, one per
  spelling, the least clear first, at most MAX_WORDS, in speaking order;
* the phrase is the word with one before and two after, never across a long
  pause, and knows where the word sits in it;
* a take passes when the read-aloud check heard the word clearly; two in a row
  close it, and a closed word stays closed;
* the share of unsure words is None when the recogniser gave no probabilities.
"""

from __future__ import annotations

from datetime import date

import pytest
from dbutil import store

from aicefr.contracts import Word
from aicefr.lessons.drill import (
    MAX_TAKES,
    MAX_WORDS,
    PAD_S,
    PASS_STREAK,
    judge,
    next_streak,
    pattern_of,
    pick,
    step_for,
    unsure_share,
)
from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
from aicefr.pronunciation.vietnamese import Pattern
from aicefr.report.habits import clarity_series
from aicefr.storage.drill_repository import DrillRepository
from aicefr.storage.lesson_repository import LessonRepository


def words(spec: str, gap: float = 0.1) -> list[Word]:
    """'I:.9 worked:.2 hard:.8' -> words 0.4 s long, `gap` apart."""
    out, t = [], 0.0
    for item in spec.split():
        text, prob = item.rsplit(":", 1)
        out.append(Word(text=text, start_s=t, end_s=t + 0.4, prob=float(prob) if prob else None))
        t += 0.4 + gap
    return out


# ================================================================= pick


def test_unsure_plain_words_are_offered_least_clear_first_in_speaking_order():
    got = pick(words("I:.9 worked:.3 very:.9 hard,:.1 um:.1 at:.95 15:.1 three:.4 worked:.2"))
    # um and 15 left out; "worked" once, where it was least clear (0.2, not 0.3)
    assert [(d.word, d.index) for d in got] == [("hard", 3), ("three", 7), ("worked", 8)]
    assert got[-1].prob == 0.2


def test_at_most_max_words_and_the_least_clear_win():
    spec = " ".join(f"word{chr(97 + i)}:{0.05 * (i + 1):.2f}" for i in range(MAX_WORDS + 3))
    got = pick(words(spec))
    assert len(got) == MAX_WORDS
    assert {d.word for d in got} == {f"word{chr(97 + i)}" for i in range(MAX_WORDS)}


def test_a_sure_or_unscored_word_is_never_offered():
    assert pick(words("hello:.9 there:.5 friend:")) == []


def test_the_phrase_is_one_before_two_after_and_the_word_is_located_in_it():
    d = pick(words("so:.9 I:.9 worked:.2 very,:.9 hard:.9 today:.9"))[0]
    assert d.phrase == "I worked very hard" and d.target == 1
    assert (d.phrase_start_s, d.phrase_end_s) == (0.5, 2.4)
    view = d.view()
    assert view["start_s"] == round(d.start_s - PAD_S, 2)
    assert view["end_s"] == round(d.end_s + PAD_S, 2)
    # A filler is skipped, not counted: the phrase still has two words after.
    d = pick(words("in:.9 three:.3 cities:.9 um:.9 last:.9 year:.9"))[0]
    assert d.phrase == "in three cities last" and d.target == 1


def test_the_phrase_stops_at_a_long_pause():
    w = words("first:.9 worked:.2 then:.9 more:.9")
    w[2] = Word(text="then", start_s=w[1].end_s + 2.0, end_s=w[1].end_s + 2.4, prob=0.9)
    d = pick(w)[0]
    assert d.phrase == "first worked" and d.target == 1


def test_the_first_word_has_no_word_before_it():
    d = pick(words("three:.1 people:.9 came:.9 late:.9"))[0]
    assert d.phrase == "three people came" and d.target == 0


# ================================================================= tips and the step


@pytest.mark.parametrize(
    ("word", "pattern"),
    [
        ("worked", Pattern.ED_ENDING),
        ("cats", Pattern.S_ENDING),
        ("three", Pattern.TH_SOUND),
        ("street", Pattern.CLUSTER),
        ("night", Pattern.FINAL_CONSONANT),
        ("hello", None),
    ],
)
def test_the_tip_is_the_most_specific_pattern_the_spelling_allows(word, pattern):
    assert pattern_of(word) is pattern
    view = pick(words(f"{word}:.1"))[0].view()
    assert (view["pattern"], bool(view["tip"])) == (
        pattern.value if pattern else None,
        pattern is not None,
    )


def test_the_take_is_measured_as_a_read_aloud_step_with_the_word_highlighted():
    step = step_for(pick(words("I:.9 worked:.2 hard:.9"))[0])
    assert step.kind is StepKind.READ_ALOUD
    assert step.text == "I worked hard" and step.hint_words == ["worked"]


# ================================================================= judging a take


def result(marks: list[tuple[str, WordStatus, str | None]], measured: bool = True) -> StepResult:
    return StepResult(
        step_id="drill",
        kind=StepKind.READ_ALOUD,
        passed=True,
        measured=measured,
        words=[
            WordMark(index=i, text=t, status=s, said=said, pattern="ed_ending" if said else None)
            for i, (t, s, said) in enumerate(marks)
        ],
    )


def test_heard_clearly_passes_unsure_or_missed_does_not():
    heard = result([("I", WordStatus.HEARD, None), ("worked", WordStatus.HEARD, None)])
    assert judge(heard, 1).passed is True
    unsure = result([("I", WordStatus.HEARD, None), ("worked", WordStatus.UNSURE, "work")])
    j = judge(unsure, 1)
    assert (j.passed, j.said, j.pattern) == (False, "work", Pattern.ED_ENDING)
    missed = result([("I", WordStatus.HEARD, None), ("worked", WordStatus.MISSED, None)])
    assert judge(missed, 1).passed is False


def test_a_take_with_nothing_measured_does_not_count():
    j = judge(result([], measured=False), 0)
    assert (j.measured, j.passed) == (False, False)


def test_two_clear_takes_in_a_row_and_a_miss_starts_again():
    s = 0
    for passed in (True, False, True):
        s = next_streak(s, passed)
    assert s == 1 and next_streak(s, True) == PASS_STREAK


def test_the_unsure_share_counts_plain_words_with_a_probability():
    assert unsure_share(words("I:.9 worked:.2 um:.1 hard:.9 15:.1")) == pytest.approx(1 / 3)
    assert unsure_share(words("I: worked:")) is None


def test_the_clarity_line_reads_lower_as_better():
    rows = [{"created_at": f"2026-11-0{i}", "response_id": f"r{i}", "value": v} for i, v in
            enumerate([20.0, 18.0, 12.0], 1)]  # fmt: skip
    line = clarity_series(rows)
    assert line["better"] == "down" and [p["value"] for p in line["points"]] == [20.0, 18.0, 12.0]
    assert line["movement"]["toward_better"] is True


# ================================================================= storage


def test_takes_are_kept_on_the_drill_and_a_closed_word_stays_closed():
    repo = DrillRepository(store())
    args = ("acc-1", "resp-1", "worked", 3, "I worked hard")
    assert repo.of_response("acc-1", "resp-1") == {}
    assert repo.record(*args, passed=True, said=None).streak == 1
    assert repo.record(*args, passed=False, said="work").streak == 0
    repo.record(*args, passed=True, said=None)
    done = repo.record(*args, passed=True, said=None)
    assert (done.streak, done.passed, len(done.takes)) == (2, True, 4)
    assert repo.record(*args, passed=False, said="work").passed is True
    assert repo.counts("acc-1") == {"practised": 1, "passed": 1}
    assert repo.open_words("acc-1") == []
    for _ in range(MAX_TAKES + 5):
        repo.record(*args, passed=True, said=None)
    assert len(repo.of_response("acc-1", "resp-1")["worked"].takes) == MAX_TAKES
    assert repo.erase_account("acc-1") == 1 and repo.of_response("acc-1", "resp-1") == {}


def test_a_word_sent_to_review_points_back_to_its_drill():
    lessons = LessonRepository(store(), seed=False)
    lessons.schedule("acc-2", "word", "", "", "worked", date(2026, 11, 3), drill_id="d1")
    lessons.schedule("acc-2", "word", "", "", "worked", date(2026, 11, 3), drill_id="d2")
    (item,) = lessons.open_reviews("acc-2")
    assert (item["word"], item["lesson_id"], item["drill_id"]) == ("worked", "", "d1")
