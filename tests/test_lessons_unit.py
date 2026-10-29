"""Layer 1 -- UNIT: pure logic of the teacher-authored lesson path (D025).

No database, no HTTP, no audio. Each test calls one module of
`aicefr.lessons` with hand-built transcripts, word timings and VAD segments,
so every count is exact and every result can be checked by hand.

Tests named after an acceptance criterion carry the exact name given in SRS
section 3.9b (FR-45..FR-50). Defects found while writing this suite were fixed
and their tests kept as regression tests; `docs/test/TEST_PLAN_D025.md`
section 8 lists them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from aicefr.contracts import Band, Criterion, MissionKind, ReasonCode, Transcript, Word
from aicefr.lessons.align import Op, Pair, align
from aicefr.lessons.checks import THRESHOLDS, UNSURE_PROB, StepChecker, compare_rounds
from aicefr.lessons.generate import FREE_ROUNDS, build_lesson, build_word_lesson
from aicefr.lessons.lint import lint_lesson
from aicefr.lessons.model import (
    STAGE_ORDER,
    GapMark,
    GapStatus,
    Lesson,
    Stage,
    Step,
    StepKind,
    StepResult,
    Strictness,
    WordStatus,
)
from aicefr.lessons.progress import (
    DAILY_GOAL_SECONDS,
    AttemptInfo,
    is_complete,
    lesson_state,
    next_lesson,
    today_summary,
)
from aicefr.lessons.review import BOX_DAYS, Schedule, after_review, first_schedule
from aicefr.lessons.seed import SAMPLE_UNITS, sample_lessons
from aicefr.lessons.seed_topics import topic_lessons
from aicefr.lessons.text import same_word, tokens
from aicefr.practice.bank import PRACTICE_TASKS

pytestmark = pytest.mark.unit

CHECKER = StepChecker()
# One stretch of speech covering every word of the short transcripts below.
SPEECH = [(0.0, 30.0)]
NOW = "2026-10-06T03:00:00+00:00"

# The model text of the A2 sample lesson: no digits, American spelling.
MODEL_TEXT = (
    "I live in a small apartment near the city center. My street is quiet, but there are "
    "many shops and a park nearby. Every morning, I walk to the bus stop. I like my "
    "neighborhood because the people are friendly and the food is cheap. The only problem "
    "is the traffic in the evening."
)
KEYWORDS = ["apartment", "quiet", "nearby", "neighborhood", "friendly", "traffic"]
PROMPT = "Tả một nơi bạn hay đến: nó ở đâu, có gì, vì sao bạn thích?"


def transcript(text: str, step: float = 0.5, probs: list[float] | None = None) -> Transcript:
    """A recogniser output with evenly spaced words, like the fake engine gives."""
    words = [
        Word(
            text=w,
            start_s=round(i * step, 3),
            end_s=round(i * step + step * 0.8, 3),
            prob=probs[i] if probs else 0.9,
        )
        for i, w in enumerate(text.split())
    ]
    return Transcript(text=text, words=words, engine="test", model_version="test-v1")


def timed(*words: tuple[str, float, float]) -> Transcript:
    """A recogniser output with explicit word timings."""
    return Transcript(
        text=" ".join(w for w, _, _ in words),
        words=[Word(text=w, start_s=s, end_s=e, prob=0.9) for w, s, e in words],
        engine="test",
        model_version="test-v1",
    )


def signal(result: StepResult, key: str):
    return next(s for s in result.signals if s.key == key)


def marks(result: StepResult) -> list[tuple[str, WordStatus]]:
    return [(m.text, m.status) for m in result.words]


# ================================================================= model (FR-45, FR-47)


def test_student_view_of_a_lesson_never_carries_gap_answers():
    gap = Step(
        kind=StepKind.GAP,
        text="My street is ___, but there is a park ___.",
        answers=["quiet", "nearby"],
        hint_words=["quiet", "nearby", "busy", "far"],
    )
    lesson = Lesson(title="Khu phố", steps=[gap, Step(kind=StepKind.FREE, text="Tả khu phố.")])

    view = lesson.for_student()

    assert all("answers" not in step for step in view["steps"])
    shown = view["steps"][0]
    assert shown["blank_count"] == 2 and shown["stage"] == Stage.CONTROLLED.value
    # The word bank is shown on purpose: answers mixed with distractors.
    assert shown["hint_words"] == ["quiet", "nearby", "busy", "far"]
    assert lesson.steps[0].answers == ["quiet", "nearby"]  # still held on the server


def test_step_and_lesson_reject_inconsistent_configuration():
    with pytest.raises(ValidationError):
        Step(kind=StepKind.FREE, min_seconds=50, max_seconds=40)
    with pytest.raises(ValidationError):
        Step(kind=StepKind.FREE, rounds=[45, 5])  # a round must last 10..180 seconds
    twin = Step(kind=StepKind.FREE, step_id="s1")
    with pytest.raises(ValidationError):
        Lesson(title="t", steps=[twin, twin.model_copy()])
    # Teacher lists are trimmed and de-duplicated, keeping the teacher's order.
    step = Step(kind=StepKind.KEYWORDS, keywords=[" go ", "Go", "", "bus   stop"])
    assert step.keywords == ["go", "bus stop"]


def test_missed_words_collect_unheard_items_and_wrong_gaps_once():
    result = StepResult(
        step_id="s",
        kind=StepKind.GAP,
        passed=False,
        missing=["walk"],
        gaps=[
            GapMark(index=0, expected="quiet", said="quiet", status=GapStatus.CORRECT),
            GapMark(index=1, expected="nearby", said="far", status=GapStatus.DISTRACTOR),
            GapMark(index=2, expected="Walk", status=GapStatus.MISSING),
        ],
    )
    assert result.missed_words() == ["walk", "nearby"]


# ================================================================= text and alignment (FR-46)


@pytest.mark.parametrize(
    ("written", "recognised"),
    [
        ("three", "3"),
        ("twenty-one", "21"),
        ("third", "3rd"),
        ("I am", "I'm"),
        ("do not", "don't"),
        ("my favourite colour", "my favorite color"),
        ("travelled", "traveled"),
    ],
)
def test_tokens_unify_numbers_contractions_and_spelling(written, recognised):
    assert tokens(written) == tokens(recognised)


@pytest.mark.parametrize(
    ("written", "recognised"), [("one thousand", "1,000"), ("twenty-first", "21st")]
)
def test_recogniser_number_formats_match_spelled_out_numbers(written, recognised):
    assert tokens(written) == tokens(recognised)


def test_same_word_accepts_other_forms_and_spellings_only():
    for a, b in [("went", "go"), ("walks", "walk"), ("colour", "color"), ("children", "child")]:
        assert same_word(a, b), (a, b)
    for a, b in [("walk", "work"), ("quiet", "quite"), ("go", "come")]:
        assert not same_word(a, b), (a, b)


def test_alignment_is_a_minimal_edit_sequence():
    pairs, inserted = align(["a", "b", "c", "d"], ["a", "c", "d", "e"])
    assert pairs == [
        Pair(0, Op.MATCH, 0),
        Pair(1, Op.DELETE, None),
        Pair(2, Op.MATCH, 1),
        Pair(3, Op.MATCH, 2),
    ]
    assert inserted == [3]

    pairs, inserted = align(["the", "people", "are", "kind"], ["the", "people", "is", "kind"])
    assert [p.op for p in pairs] == [Op.MATCH, Op.MATCH, Op.SUBSTITUTE, Op.MATCH]
    assert pairs[2].hyp_index == 2 and inserted == []


# ================================================================= step checker (FR-46)


def test_read_aloud_marks_each_reference_word_heard_missed_or_unsure():
    step = Step(kind=StepKind.READ_ALOUD, text="the people are friendly")

    result = CHECKER.check(step, transcript("the people friendly"), SPEECH)

    assert marks(result) == [
        ("the", WordStatus.HEARD),
        ("people", WordStatus.HEARD),
        ("are", WordStatus.MISSED),
        ("friendly", WordStatus.HEARD),
    ]
    are = result.words[2]
    assert are.start_s is None and are.said is None  # not heard: no place in the recording
    assert result.words[3].start_s == 1.0  # a heard word points at its second
    assert result.measured is True


def test_passed_reading_with_a_missed_word_names_it_in_the_tip():
    step = Step(kind=StepKind.READ_ALOUD, text="I like my neighborhood because the people are kind")

    result = CHECKER.check(step, transcript("I like my because the people are kind"), SPEECH)

    assert result.passed is True  # eight words of nine is over the 75% mark
    assert "«neighborhood»" in result.tip


def test_low_confidence_or_another_form_is_unsure_not_missed():
    step = Step(kind=StepKind.READ_ALOUD, text="the people are friendly")
    probs = [0.9, UNSURE_PROB - 0.01, 0.9, UNSURE_PROB]

    result = CHECKER.check(step, transcript("the people are friendly", probs=probs), SPEECH)

    assert [s for _, s in marks(result)] == [
        WordStatus.HEARD,
        WordStatus.UNSURE,  # just under the threshold
        WordStatus.HEARD,
        WordStatus.HEARD,  # exactly at the threshold
    ]
    assert result.passed  # "unsure" never counts against the learner

    other_form = CHECKER.check(
        Step(kind=StepKind.READ_ALOUD, text="She walks to school."),
        transcript("she walk to school"),
        SPEECH,
    )
    walks = other_form.words[1]
    assert walks.status is WordStatus.UNSURE and walks.said == "walk"


def test_read_aloud_ignores_spelling_convention_numbers_and_contractions():
    step = Step(kind=StepKind.READ_ALOUD, text="My favourite colour is grey, and I'm twenty-one.")

    result = CHECKER.check(step, transcript("my favorite color is gray and I am 21"), SPEECH)

    assert all(status is WordStatus.HEARD for _, status in marks(result)), marks(result)
    assert signal(result, "coverage").value == 1.0


def test_keyword_counts_any_form_of_the_word():
    step = Step(kind=StepKind.KEYWORDS, keywords=["go"], min_words=4)

    result = CHECKER.check(step, transcript("I went to school"), SPEECH)

    assert [(h.text, h.start_s) for h in result.found] == [("go", 0.5)]  # "went" at 0.5 s
    assert result.missing == []
    assert result.passed


def test_gap_classifies_each_blank():
    step = Step(
        kind=StepKind.GAP,
        text="My street is ___, but there are many shops and a park ___.",
        answers=["quiet", "nearby"],
        hint_words=["quiet", "nearby", "busy", "far"],
    )
    said = transcript("my street is quiet but there are many shops and a park far")

    result = CHECKER.check(step, said, SPEECH, answers=step.answers)

    assert [(g.index, g.expected, g.said, g.status) for g in result.gaps] == [
        (0, "quiet", "quiet", GapStatus.CORRECT),
        (1, "nearby", "far", GapStatus.DISTRACTOR),
    ]
    assert not result.passed  # 1 of 2 blanks under the normal pass mark
    assert result.missed_words() == ["nearby"]  # the answer comes back in a review


def test_gap_marks_a_word_outside_the_bank_and_an_unsaid_opening_blank():
    step = Step(
        kind=StepKind.GAP,
        text="___ is my favorite color, and my room is ___.",
        answers=["blue", "small"],
        hint_words=["blue", "small", "red", "big"],
    )

    result = CHECKER.check(
        step, transcript("is my favorite color and my room is tiny"), SPEECH, answers=step.answers
    )

    assert [(g.index, g.said, g.status) for g in result.gaps] == [
        (0, None, GapStatus.MISSING),
        (1, "tiny", GapStatus.OTHER),
    ]
    assert "Chỗ trống 2" in result.tip and "tiny" in result.tip


SAMPLE_GAP = Step(
    kind=StepKind.GAP,
    text="My street is ___, but there are many shops and a park ___.",
    answers=["quiet", "nearby"],
    hint_words=["quiet", "nearby", "busy", "far"],
)


def test_gap_left_unsaid_is_missing_and_keeps_the_word_before_it():
    # Regression: a blank used to align for free with ANY word, so a blank the
    # learner skipped took the word spoken before it ("is", "park"): the blank
    # read "other" and a word the learner did say read "not heard".
    step = Step(
        kind=StepKind.GAP,
        text="My street is ___, but there are many shops.",
        answers=["quiet"],
        hint_words=["quiet", "busy"],
    )

    middle = CHECKER.check(
        step, transcript("my street is but there are many shops"), SPEECH, answers=step.answers
    )
    end = CHECKER.check(
        SAMPLE_GAP,
        transcript("my street is quiet but there are many shops and a park"),
        SPEECH,
        answers=SAMPLE_GAP.answers,
    )

    assert [(g.said, g.status) for g in middle.gaps] == [(None, GapStatus.MISSING)]
    assert all(status is WordStatus.HEARD for _, status in marks(middle)), marks(middle)
    assert [(g.said, g.status) for g in end.gaps] == [
        ("quiet", GapStatus.CORRECT),
        (None, GapStatus.MISSING),
    ]
    assert all(status is WordStatus.HEARD for _, status in marks(end)), marks(end)


def test_speech_after_the_sentence_is_not_pulled_into_the_last_blank():
    # Regression: "okay" after the sentence used to tie with the right reading
    # and, resolved from the end, land in the last blank.
    ran_on = CHECKER.check(
        SAMPLE_GAP,
        transcript("my street is quiet but there are many shops and a park nearby okay"),
        SPEECH,
        answers=SAMPLE_GAP.answers,
    )
    other = CHECKER.check(
        SAMPLE_GAP,
        transcript("my street is pretty but there are many shops and a park nearby okay"),
        SPEECH,
        answers=SAMPLE_GAP.answers,
    )

    assert [(g.said, g.status) for g in ran_on.gaps] == [
        ("quiet", GapStatus.CORRECT),
        ("nearby", GapStatus.CORRECT),
    ]
    assert ran_on.passed
    # A word outside the bank, said where the blank is, still fills it as "other".
    assert [(g.said, g.status) for g in other.gaps] == [
        ("pretty", GapStatus.OTHER),
        ("nearby", GapStatus.CORRECT),
    ]
    assert all(status is WordStatus.HEARD for _, status in marks(other))


def test_words_outside_speech_are_not_counted():
    step = Step(kind=StepKind.KEYWORDS, keywords=["coffee", "tea"], min_words=2)
    # Speech only in the first two seconds; "and tea" sits in a silent stretch
    # where a recogniser may invent words.
    said = timed(
        ("I", 0.2, 0.4),
        ("like", 0.5, 0.8),
        ("coffee", 0.9, 1.4),
        ("and", 4.0, 4.2),
        ("tea", 4.3, 4.7),
    )

    result = CHECKER.check(step, said, [(0.0, 2.0)])

    assert [h.text for h in result.found] == ["coffee"]
    assert result.missing == ["tea"]
    assert signal(result, "words").value == 3

    read = CHECKER.check(
        Step(kind=StepKind.READ_ALOUD, text="I like coffee and tea"), said, [(0.0, 2.0)]
    )
    assert marks(read)[-2:] == [("and", WordStatus.MISSED), ("tea", WordStatus.MISSED)]


@pytest.mark.parametrize("said", ["", "um uh erm"])
def test_nothing_heard_is_unmeasured_never_marked_wrong(said):
    step = Step(kind=StepKind.READ_ALOUD, text="the people are friendly")

    result = CHECKER.check(step, transcript(said), SPEECH)

    assert result.measured is False and result.passed is False
    assert result.reasons == [ReasonCode.ASR_EMPTY_TRANSCRIPT]
    assert result.words == [] and result.tip


def test_strictness_moves_the_pass_mark():
    heard = transcript("my street is quiet")  # 4 of the 5 words: 80%

    results = {
        s: CHECKER.check(
            Step(kind=StepKind.READ_ALOUD, text="my street is very quiet", strictness=s),
            heard,
            SPEECH,
        )
        for s in Strictness
    }

    assert [results[s].passed for s in Strictness] == [True, True, False]
    assert [signal(results[s], "coverage").target for s in Strictness] == [
        THRESHOLDS["coverage"][s] for s in Strictness
    ]


def test_look_up_counts_only_content_words():
    step = Step(kind=StepKind.LOOK_UP, text="The only problem is the traffic in the evening.")

    result = CHECKER.check(step, transcript("only problem traffic evening"), SPEECH)

    assert result.passed and signal(result, "content").value == 1.0
    missed = [m for m in result.words if m.status is WordStatus.MISSED]
    assert missed and not any(m.content for m in missed)  # only "the", "is", "in" missed


def test_starter_needs_the_frame_at_the_start_and_enough_words_after_it():
    step = Step(
        kind=StepKind.STARTER,
        text="What did you do last weekend?",
        starter="Last weekend, I",
        min_words=6,
    )

    opened = CHECKER.check(
        step, transcript("well last weekend I visited my grandparents in the countryside"), SPEECH
    )
    late = CHECKER.check(
        step, transcript("I visited my grandparents in the countryside last weekend"), SPEECH
    )

    assert opened.passed and signal(opened, "words_after").value == 6
    assert not late.passed and signal(late, "starter").met is False
    assert "Last weekend, I" in late.tip


def test_outline_counts_linking_words_in_outline_order():
    step = Step(
        kind=StepKind.OUTLINE,
        text="Describe your home.",
        markers=[["first", "firstly"], ["then", "next"], ["finally", "in the end"]],
        min_seconds=20,
    )
    ordered = transcript(
        "first I live in a small flat then there is a park near it and in the end I like it",
        step=1.0,
    )
    shuffled = transcript(
        "in the end I like it then there is a park first I live in a small flat", step=1.0
    )

    good = CHECKER.check(step, ordered, SPEECH)
    bad = CHECKER.check(step, shuffled, SPEECH)

    assert good.passed and [h.text for h in good.found] == ["first", "then", "in the end"]
    assert signal(good, "markers").value == 3
    assert not bad.passed and signal(bad, "markers").value == 1


def test_picture_step_does_not_pass_a_recited_word_bank():
    step = Step(
        kind=StepKind.PICTURE,
        text="Describe the picture.",
        hint_words=["market", "busy", "fruit", "seller"],
        min_seconds=10,
    )

    recited = CHECKER.check(step, transcript("market busy fruit seller", step=3.0), [(0, 12)])
    described = CHECKER.check(
        step,
        transcript("this is a busy market and a seller is selling fresh fruit to people", 0.8),
        [(0, 12)],
    )

    assert signal(recited, "bank").value == 4 and not recited.passed
    assert "danh sách từ" in recited.tip
    assert described.passed


def test_free_step_compares_rounds():
    step = Step(kind=StepKind.FREE, text="Kể về cuối tuần của bạn.", rounds=[45, 35, 25])
    talk = "last weekend I went to the market with my friends and we bought some fresh fruit"

    first = CHECKER.check(step, transcript(talk, 1.0), [(0.0, 8.0), (12.0, 16.0)], round_index=1)
    third = CHECKER.check(step, transcript(talk, 0.6), [(0.0, 5.0), (6.5, 9.5)], round_index=3)

    assert signal(first, "longest_pause").value == 4.0
    assert signal(third, "longest_pause").value == 1.5
    assert first.round == 1 and third.round == 3
    changes = compare_rounds(first, third)
    assert "Quãng ngừng dài nhất giảm từ 4,0 giây còn 1,5 giây, tốt hơn lượt đầu" in changes
    assert compare_rounds(first, first) == []  # nothing changed, nothing said


# ================================================================= generator and linter (FR-47)


@pytest.mark.parametrize(
    ("band", "kinds"),
    [
        (Band.A2, ["read_aloud", "repeat", "gap", "look_up", "keywords", "outline", "free"]),
        (Band.B1, ["read_aloud", "gap", "look_up", "keywords", "outline", "free"]),
        (Band.B2, ["read_aloud", "look_up", "keywords", "outline", "free"]),
    ],
)
def test_generator_builds_the_four_stage_ladder_from_one_text(band, kinds):
    lesson = build_lesson("Khu phố của tôi", band, MODEL_TEXT, KEYWORDS, PROMPT)

    stages = [s.stage for s in lesson.steps]
    assert set(stages) == set(STAGE_ORDER)  # all four rungs
    assert stages == sorted(stages, key=STAGE_ORDER.index)  # never a step back down
    assert [s.kind.value for s in lesson.steps] == kinds  # support fades with the band
    free = lesson.steps[-1]
    assert free.kind is StepKind.FREE and free.text == PROMPT
    rounds = free.round_limits()
    assert len(rounds) == 3 and rounds == sorted(rounds, reverse=True)  # 4/3/2
    assert lesson.model_text == MODEL_TEXT and lesson.keywords == KEYWORDS


def test_generated_gap_blanks_key_words_and_mixes_in_distractors():
    lesson = build_lesson("Khu phố của tôi", Band.A2, MODEL_TEXT, KEYWORDS, PROMPT)

    gap = next(s for s in lesson.steps if s.kind is StepKind.GAP)

    assert gap.blank_count == len(gap.answers) >= 1
    assert set(gap.answers) <= set(KEYWORDS)
    assert set(gap.answers) < set(gap.hint_words)  # at least one distractor in the bank
    # A lesson generated from a clean text gives the teacher nothing to fix.
    assert [i for i in lint_lesson(lesson) if i.level == "warn"] == []


def _source(step: Step) -> str:
    """The sentence of a text step as written, with the answers back in its gaps."""
    text = step.text
    for answer in step.answers:
        text = text.replace("___", answer, 1)
    return text


@pytest.mark.parametrize("band", [Band.A2, Band.B1])
def test_generator_gives_each_controlled_step_its_own_sentence(band):
    text = (
        "Last weekend I went to the beach with my friends. We took the bus early in the "
        "morning. The weather was sunny and the water was warm. In the evening we watched the "
        "sunset together. It was a wonderful trip."
    )
    lesson = build_lesson(
        "Trip", band, text, ["beach", "weather", "sunset", "wonderful"], "Kể về một chuyến đi."
    )
    kinds = (StepKind.REPEAT, StepKind.GAP, StepKind.LOOK_UP)
    sentences = [_source(s) for s in lesson.steps if s.kind in kinds]

    assert len(sentences) == (3 if band is Band.A2 else 2)
    assert len(set(sentences)) == len(sentences), sentences


def test_word_lesson_practises_keywords_in_threes_then_reuses_them_in_free_speech():
    words = ["traffic", "nearby", "quiet", "friendly", "cheap", "apartment", "market"]

    lesson = build_word_lesson("Từ lớp hay bỏ", Band.B1, words, "Tả khu phố của bạn.")

    *drills, free = lesson.steps
    assert [s.keywords for s in drills] == [words[0:3], words[3:6], words[6:]]
    assert all(s.kind is StepKind.KEYWORDS for s in drills)
    assert [s.min_words for s in drills] == [7, 7, 5]
    assert free.kind is StepKind.FREE and free.text == "Tả khu phố của bạn."
    assert free.round_limits() == FREE_ROUNDS[Band.B1][:2]
    [mission] = free.missions
    assert (mission.kind, mission.target, mission.words) == (
        MissionKind.USE_WORDS,
        3,
        tuple(words[:6]),
    )
    assert mission.label == "Dùng lại ít nhất 3 từ vừa luyện"
    assert lesson.model_text == "" and lesson.keywords == words
    assert [i for i in lint_lesson(lesson) if i.level == "warn"] == []

    # The promise in the label is measured: reusing the words meets it.
    reused = CHECKER.check(
        free,
        transcript("the traffic near my apartment is bad but the market nearby is quiet", 3.0),
        [(0.0, 44.0)],
        round_index=1,
    )
    ignored = CHECKER.check(
        free,
        transcript("I like my home and I live there with my family every day", 3.0),
        [(0.0, 44.0)],
        round_index=1,
    )
    assert signal(reused, "mission_use_words").met is True and reused.passed
    assert signal(ignored, "mission_use_words").met is False and not ignored.passed

    two = build_word_lesson("Hai từ", Band.A2, ["go", "eat"], "Kể về bữa sáng.")
    assert [s.kind for s in two.steps] == [StepKind.KEYWORDS, StepKind.FREE]
    assert two.steps[-1].missions[0].target == 2  # never more words than were practised


def test_linter_warns_about_asr_traps():
    text = "I have 3 cats, and my room is a nice colour."
    lesson = Lesson(
        title="Phòng của tôi",
        model_text=text,
        steps=[
            Step(kind=StepKind.READ_ALOUD, text=text),
            Step(kind=StepKind.FREE, text="Tả phòng của bạn."),
        ],
    )

    issues = lint_lesson(lesson)

    digits = [i for i in issues if "chữ số" in i.message]
    british = [i for i in issues if "colour → color" in i.message]
    assert len(digits) == 1 and digits[0].level == "warn" and digits[0].field == "model_text"
    assert len(british) == 1 and british[0].field == "model_text"

    # Once the model text is fixed, the step that still holds the old text is
    # reported on its own, so the teacher knows which step to edit.
    fixed = "I have three cats, and my room is nice."
    edited = lesson.model_copy(update={"model_text": fixed})
    traps = [i for i in lint_lesson(edited) if "chữ số" in i.message or "→" in i.message]
    assert len(traps) == 2
    assert {(i.step_id, i.field) for i in traps} == {(lesson.steps[0].step_id, "text")}
    clean = edited.model_copy(
        update={"steps": [lesson.steps[0].model_copy(update={"text": fixed}), lesson.steps[1]]}
    )
    assert not [i for i in lint_lesson(clean) if "chữ số" in i.message or "→" in i.message]


def test_linter_flags_gap_answers_that_cannot_be_told_apart_by_ear():
    gap = Step(
        kind=StepKind.GAP,
        text="I ___ to school with ___ friends.",
        answers=["walked", "two"],
        hint_words=["walked", "walks", "two", "far"],
    )
    lesson = Lesson(title="t", steps=[gap, Step(kind=StepKind.FREE, text="Kể chuyện.")])

    warnings = [i for i in lint_lesson(lesson) if i.level == "warn" and i.step_id == gap.step_id]

    assert any("walked / walks" in i.message for i in warnings)  # differ only by ending
    assert any("«two»" in i.message and "to, too" in i.message for i in warnings)  # homophone


def test_linter_warns_about_a_missing_free_step_and_absent_keywords():
    lesson = Lesson(
        title="t",
        model_text="I live near a quiet park.",
        keywords=["quiet", "traffic"],
        steps=[Step(kind=StepKind.READ_ALOUD, text="I live near a quiet park.")],
    )

    messages = [i.message for i in lint_lesson(lesson) if i.level == "warn"]

    assert any("chưa có bước Nói tự do" in msg for msg in messages)
    assert any(msg.endswith(": traffic.") for msg in messages)


# ================================================================= spaced review (FR-48)


def test_review_boxes_follow_leitner_intervals():
    today = date(2026, 10, 6)

    assert first_schedule(today) == Schedule(1, today + timedelta(days=1))
    assert after_review(1, True, today) == Schedule(2, today + timedelta(days=3))
    assert after_review(1, False, today) == Schedule(1, today + timedelta(days=1))
    assert after_review(2, True, today) == Schedule(3, today + timedelta(days=7))
    finished = after_review(3, True, today)
    assert finished.done and finished.due is None
    assert after_review(3, False, today) == Schedule(1, today + timedelta(days=1))
    assert BOX_DAYS == {1: 1, 2: 3, 3: 7}


# ================================================================= progress (FR-45, FR-50)


def _five_steps() -> Lesson:
    return Lesson(
        title="Năm bước",
        steps=[
            Step(kind=StepKind.READ_ALOUD, text="the people are friendly"),
            Step(kind=StepKind.GAP, text="My street is ___.", answers=["quiet"]),
            Step(kind=StepKind.KEYWORDS, keywords=["walk"]),
            Step(kind=StepKind.OUTLINE, text="Describe it.", markers=[["first"]]),
            Step(kind=StepKind.FREE, text="Tả khu phố."),
        ],
    )


def _attempt(lesson: Lesson, step_id: str, passed: bool, seconds: float = 8.0) -> AttemptInfo:
    return AttemptInfo(lesson.lesson_id, step_id, passed, NOW, seconds)


def test_lesson_completes_only_with_enough_passed_steps_and_the_free_step():
    lesson = _five_steps()
    *guided, free = [s.step_id for s in lesson.steps]
    four_passed = [_attempt(lesson, sid, True) for sid in guided]

    before = lesson_state(lesson, four_passed)
    assert (before.passed, before.total, before.free_done) == (4, 5, False)
    assert not is_complete(lesson, before)  # 80% passed, but no free speech yet

    after = lesson_state(lesson, [*four_passed, _attempt(lesson, free, passed=False)])
    assert after.free_done and is_complete(lesson, after)  # done, passed or not

    three_and_free = [*four_passed[:3], _attempt(lesson, free, passed=True)]
    assert is_complete(lesson, lesson_state(lesson, three_and_free))  # 4 of 5 again
    assert not is_complete(
        lesson, lesson_state(lesson, [*four_passed[:2], _attempt(lesson, free, passed=True)])
    )  # 3 of 5 is under the 80% mark


def test_free_step_is_done_only_when_speech_was_measured():
    lesson = _five_steps()
    *guided, free = [s.step_id for s in lesson.steps]
    silent = _attempt(lesson, free, passed=False, seconds=0.0)  # how an unmeasured one is stored

    state = lesson_state(lesson, [*(_attempt(lesson, sid, True) for sid in guided), silent])

    assert state.free_done is False
    assert not is_complete(lesson, state)


def test_today_counts_seconds_spoken_per_vietnam_day():
    now = datetime(2026, 10, 6, 5, 0, tzinfo=UTC)  # noon in Vietnam
    attempts = [
        AttemptInfo("l", "s1", True, "2026-10-06T01:00:00+00:00", 40.0),
        # 00:30 on 6 October in Vietnam, still 5 October in UTC
        AttemptInfo("l", "s2", False, "2026-10-05T17:30:00+00:00", 55.0),
        AttemptInfo("l", "s1", True, "2026-10-05T16:30:00+00:00", 30.0),  # 23:30 the day before
        AttemptInfo("l", "s3", False, "2026-10-06T02:00:00+00:00", 0.0),  # nothing measured
    ]

    today = today_summary(attempts, now)

    assert today.seconds == 95.0 and today.goal_seconds == DAILY_GOAL_SECONDS == 180
    assert not today.goal_met
    assert len(today.week) == 7
    assert today.week[-2:] == [(date(2026, 10, 5), 30.0), (date(2026, 10, 6), 95.0)]
    assert today.streak == 2


def test_next_lesson_without_assessment_follows_path_order_and_says_why():
    done = Lesson(title="A", steps=[Step(kind=StepKind.FREE, text="x")])
    half = Lesson(
        title="B",
        steps=[Step(kind=StepKind.KEYWORDS, keywords=["go"]), Step(kind=StepKind.FREE, text="y")],
    )
    fresh = Lesson(title="C", steps=[Step(kind=StepKind.FREE, text="z")])
    ordered = [(done, None), (half, Criterion.RANGE), (fresh, Criterion.FLUENCY)]
    states = {
        done.lesson_id: lesson_state(done, [_attempt(done, done.steps[0].step_id, True)]),
        half.lesson_id: lesson_state(half, [_attempt(half, half.steps[0].step_id, True)]),
    }

    nxt = next_lesson(ordered, states, [], None)
    assert (nxt.lesson_id, nxt.basis) == (half.lesson_id, "path_order")
    assert nxt.reason == "Bạn đang học dở bài này."

    # A weakest criterion with no lesson at that band falls back to path order.
    nxt = next_lesson(ordered, states, [Criterion.FLUENCY], Band.B2)
    assert (nxt.lesson_id, nxt.basis) == (half.lesson_id, "path_order")

    states[half.lesson_id] = lesson_state(
        half, [_attempt(half, s.step_id, True) for s in half.steps]
    )
    states[fresh.lesson_id] = lesson_state(fresh, [_attempt(fresh, fresh.steps[0].step_id, True)])
    nxt = next_lesson(ordered, states, [], None)
    assert (nxt.lesson_id, nxt.basis) == (done.lesson_id, "review_all")
    assert next_lesson([], {}, [], None) is None


# ================================================================= sample path (FR-45)


def test_sample_path_runs_by_level_and_topic_with_one_lesson_per_practice_task():
    by_unit = sample_lessons()
    lessons = [lesson for unit in by_unit.values() for lesson in unit]

    assert list(by_unit) == [u["unit_id"] for u in SAMPLE_UNITS]
    assert len(lessons) == 46
    ids = {lesson.lesson_id for lesson in lessons}
    written = {"lesson-a2-neighborhood", "lesson-b1-trip", "lesson-b2-online", *topic_lessons()}
    assert len(written) == 16 and written <= ids
    assert {f"lesson-{t.task_id.lower()}" for t in PRACTICE_TASKS} <= ids
    # Six levels in order (D059), and within each level a different topic per unit.
    levels = [u["band"] for u in SAMPLE_UNITS]
    assert levels == sorted(levels, key=lambda b: b.rank) and set(levels) == set(Band)
    for band in Band:
        topics = [u["topic"] for u in SAMPLE_UNITS if u["band"] is band]
        assert len(topics) == len(set(topics)) >= 2
    for unit in SAMPLE_UNITS:
        assert all(lesson.band is unit["band"] for lesson in by_unit[unit["unit_id"]])
    for lesson in lessons:
        assert lesson.sample and lesson.steps[-1].kind is StepKind.FREE
        # Fixed step ids: re-seeding never orphans a stored attempt.
        assert [s.step_id for s in lesson.steps] == [
            f"{lesson.lesson_id}-s{i}" for i in range(1, len(lesson.steps) + 1)
        ]


def test_sample_lessons_raise_no_linter_warnings():
    for unit in sample_lessons().values():
        for lesson in unit:
            warnings = [i.message for i in lint_lesson(lesson) if i.level == "warn"]
            assert warnings == [], (lesson.lesson_id, warnings)
