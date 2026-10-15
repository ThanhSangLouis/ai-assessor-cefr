from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from aicefr.contracts import AsrStatus, Band, Transcript, Word
from aicefr.lessons.align import AlignmentOp, align
from aicefr.lessons.checks import evaluate_step
from aicefr.lessons.lint import lint_lesson
from aicefr.lessons.model import (
    FreePayload,
    FreeRound,
    GapPayload,
    KeywordsPayload,
    Lesson,
    LessonStage,
    LessonStep,
    LookUpPayload,
    OutlinePayload,
    PictureChoice,
    PicturePayload,
    PublishedLessonVersion,
    ReadAloudPayload,
    RepeatPayload,
    StarterPayload,
    StepAttemptStatus,
    StepCompletion,
    StepEvidenceState,
    StepKind,
)
from aicefr.lessons.progress import lesson_completion
from aicefr.lessons.review import first_review, review_again
from aicefr.lessons.text import find_phrase, lemma, normalize_text, same_word
from aicefr.practice.contracts import TimeSpan

NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)


def transcript(
    text: str = "", words: tuple[Word, ...] = (), status: AsrStatus = AsrStatus.OK
) -> Transcript:
    return Transcript(
        response_id="response-1",
        status=status,
        text=text,
        words=words,
        engine="fixture",
        engine_version="1",
        decode_config_version="1",
        audio_sha256="b" * 64,
    )


def word(text: str, start: float, end: float, confidence: float | None = 0.9) -> Word:
    return Word(text=text, start_s=start, end_s=end, prob=confidence)


def make_step(
    kind: StepKind,
    payload,
    *,
    ordinal: int = 1,
    stage: LessonStage | None = None,
    step_id: str | None = None,
) -> LessonStep:
    return LessonStep(
        step_id=step_id or f"s{ordinal}",
        ordinal=ordinal,
        stage=stage
        or {
            StepKind.READ_ALOUD: LessonStage.MODEL,
            StepKind.REPEAT: LessonStage.MODEL,
            StepKind.LOOK_UP: LessonStage.CONTROLLED,
            StepKind.GAP: LessonStage.CONTROLLED,
            StepKind.KEYWORDS: LessonStage.GUIDED,
            StepKind.STARTER: LessonStage.GUIDED,
            StepKind.PICTURE: LessonStage.GUIDED,
            StepKind.OUTLINE: LessonStage.GUIDED,
            StepKind.FREE: LessonStage.FREE,
        }[kind],
        kind=kind,
        instruction="Luyện tập.",
        payload=payload,
        rules_version="lesson-rules-v1",
    )


def full_lesson() -> Lesson:
    steps = (
        make_step(
            StepKind.READ_ALOUD,
            ReadAloudPayload(kind=StepKind.READ_ALOUD, text="hello world", max_seconds=10),
            ordinal=1,
        ),
        make_step(
            StepKind.GAP,
            GapPayload(
                kind=StepKind.GAP, text="Turn ___ the light.", answers=("off",), max_seconds=10
            ),
            ordinal=2,
        ),
        make_step(
            StepKind.KEYWORDS,
            KeywordsPayload(kind=StepKind.KEYWORDS, keywords=("first",), max_seconds=10),
            ordinal=3,
        ),
        make_step(
            StepKind.FREE,
            FreePayload(
                kind=StepKind.FREE,
                rounds=(
                    FreeRound(duration_seconds=60, prompt="Say it."),
                    FreeRound(duration_seconds=40, prompt="Say it again."),
                ),
                max_seconds=60,
            ),
            ordinal=4,
        ),
    )
    return Lesson(
        lesson_id="lesson-1",
        title="Sample",
        summary="",
        band=Band.A2,
        steps=steps,
        revision=2,
        content_version="content-v1",
    )


def test_normalization_contractions_numbers_ordinals_hyphens_and_spellings() -> None:
    assert normalize_text("I can't visit the 1st-year centre; my favourite colour is gray.") == (
        "i",
        "can",
        "not",
        "visit",
        "the",
        "first",
        "year",
        "center",
        "my",
        "favorite",
        "color",
        "is",
        "gray",
    )
    assert normalize_text("We are in 2026") == (
        "we",
        "are",
        "in",
        "two",
        "thousand",
        "twenty",
        "six",
    )
    assert same_word("went", "go")
    assert same_word("played", "play")
    assert same_word("colour", "color")
    assert lemma("children") == "child"
    assert normalize_text("101st, 1000th") == (
        "one",
        "hundred",
        "first",
        "one",
        "thousandth",
    )
    assert same_word("colour", "color")
    assert same_word("turn off", "turn off")
    assert lemma("!!!") == ""
    assert find_phrase("turn off", ("we", "turn", "off")) == (1, 2)
    assert find_phrase("", ("turn", "off")) is None
    assert find_phrase("turn on", ("turn", "off")) is None


def test_alignment_is_minimal_deterministic_and_tracks_insertions() -> None:
    result = align(("I", "went", "home"), ("I", "go", "to", "home"))
    assert result.edit_distance == 1
    assert [item.operation for item in result.pairs] == [
        AlignmentOp.MATCH,
        AlignmentOp.SUBSTITUTE,
        AlignmentOp.MATCH,
    ]
    assert result.inserted_indices == (2,)
    assert result == align(("I", "went", "home"), ("I", "go", "to", "home"))
    deleted = align(("we", "go", "home"), ("we", "home"))
    assert [item.operation for item in deleted.pairs] == [
        AlignmentOp.MATCH,
        AlignmentOp.DELETE,
        AlignmentOp.MATCH,
    ]
    with pytest.raises(ValueError, match="limited to 512 tokens"):
        align(("word",) * 513, ())
    with pytest.raises(ValueError, match="limited to 512 tokens"):
        align(("reference",), ("heard",) * 513)


def test_oversized_lesson_references_and_asr_hypotheses_are_rejected_without_truncation() -> None:
    with pytest.raises(ValidationError, match="limited to 512 tokens"):
        RepeatPayload(
            kind=StepKind.REPEAT,
            text="a " * 513,
            max_seconds=10,
        )
    with pytest.raises(ValidationError):
        Lesson(
            lesson_id="too-many-steps",
            title="Bounded content",
            band=Band.A2,
            steps=(
                make_step(
                    StepKind.READ_ALOUD,
                    ReadAloudPayload(kind=StepKind.READ_ALOUD, text="Hi", max_seconds=5),
                ),
            )
            * 41,
        )

    repeat = make_step(
        StepKind.REPEAT,
        RepeatPayload(kind=StepKind.REPEAT, text="word", max_seconds=10),
    )
    too_many_words = transcript(
        words=tuple(word("word", index, index + 0.1) for index in range(513))
    )
    with pytest.raises(ValueError, match="limited to 512 words"):
        evaluate_step(
            repeat,
            too_many_words,
            (TimeSpan(start_s=0, end_s=514),),
        )
    too_much_text = transcript("word " * 6_554)
    with pytest.raises(ValueError, match="limited to 32768 characters"):
        evaluate_step(
            repeat,
            too_much_text,
            (TimeSpan(start_s=0, end_s=1),),
        )


def test_all_nine_step_types_and_stage_mapping_are_typed() -> None:
    steps = (
        make_step(
            StepKind.READ_ALOUD,
            ReadAloudPayload(kind=StepKind.READ_ALOUD, text="Hi", max_seconds=5),
        ),
        make_step(
            StepKind.REPEAT,
            RepeatPayload(kind=StepKind.REPEAT, text="Hi", max_seconds=5),
            ordinal=2,
        ),
        make_step(
            StepKind.LOOK_UP,
            LookUpPayload(kind=StepKind.LOOK_UP, text="Hi", show_seconds=2, max_seconds=5),
            ordinal=3,
        ),
        make_step(
            StepKind.GAP,
            GapPayload(kind=StepKind.GAP, text="Hi ___", answers=("there",), max_seconds=5),
            ordinal=4,
        ),
        make_step(
            StepKind.KEYWORDS,
            KeywordsPayload(kind=StepKind.KEYWORDS, keywords=("hi",), max_seconds=5),
            ordinal=5,
        ),
        make_step(
            StepKind.STARTER,
            StarterPayload(kind=StepKind.STARTER, text="Say hi", starter="I am", max_seconds=5),
            ordinal=6,
        ),
        make_step(
            StepKind.PICTURE,
            PicturePayload(
                kind=StepKind.PICTURE,
                prompt="Describe",
                pictures=(PictureChoice(choice_id="1", description="cat"),),
                max_seconds=5,
            ),
            ordinal=7,
        ),
        make_step(
            StepKind.OUTLINE,
            OutlinePayload(kind=StepKind.OUTLINE, text="Talk", points=("first",), max_seconds=5),
            ordinal=8,
        ),
        make_step(
            StepKind.FREE,
            FreePayload(
                kind=StepKind.FREE,
                rounds=(
                    FreeRound(duration_seconds=10, prompt="a"),
                    FreeRound(duration_seconds=5, prompt="b"),
                ),
                max_seconds=10,
            ),
            ordinal=9,
        ),
    )
    assert len({step.kind for step in steps}) == 9
    assert [step.stage for step in steps] == [
        LessonStage.MODEL,
        LessonStage.MODEL,
        LessonStage.CONTROLLED,
        LessonStage.CONTROLLED,
        LessonStage.GUIDED,
        LessonStage.GUIDED,
        LessonStage.GUIDED,
        LessonStage.GUIDED,
        LessonStage.FREE,
    ]
    with pytest.raises(ValidationError):
        make_step(StepKind.GAP, RepeatPayload(kind=StepKind.REPEAT, text="wrong", max_seconds=2))
    with pytest.raises(ValidationError):
        FreePayload(
            kind=StepKind.FREE,
            rounds=(
                FreeRound(duration_seconds=5, prompt="a"),
                FreeRound(duration_seconds=5, prompt="b"),
            ),
            max_seconds=5,
        )


def test_draft_can_be_incomplete_but_publish_requires_full_stages_and_free() -> None:
    draft = Lesson(
        lesson_id="draft",
        title="Draft",
        band=Band.A2,
        steps=(
            make_step(
                StepKind.REPEAT, RepeatPayload(kind=StepKind.REPEAT, text="hello", max_seconds=5)
            ),
        ),
    )
    assert lint_lesson(draft).valid
    assert not lint_lesson(draft, for_publish=True).valid
    assert {issue.code for issue in lint_lesson(draft, for_publish=True).errors} >= {
        "MISSING_STAGE",
        "NO_FREE_STEP",
    }
    valid = full_lesson()
    assert lint_lesson(valid, for_publish=True).valid
    published = PublishedLessonVersion.from_lesson(valid, version=1, published_at=NOW)
    assert published.content_hash and published.version == 1
    with pytest.raises(ValidationError):
        published.version = 2
    with pytest.raises(ValueError, match="must pass publication lint"):
        PublishedLessonVersion.from_lesson(draft, version=1, published_at=NOW)


def test_content_hierarchy_and_publication_snapshot_reject_conflicts() -> None:
    from aicefr.lessons.model import LearningPath, LearningUnit

    unit = LearningUnit(
        unit_id="unit-1",
        path_id="path-1",
        ordinal=1,
        title="Unit",
        band=Band.A2,
        lesson_ids=("lesson-1",),
    )
    path = LearningPath(
        path_id="path-1",
        title="Path",
        band_from=Band.A2,
        band_to=Band.B1,
        units=(unit,),
        content_version="v1",
    )
    assert path.units[0].lesson_ids == ("lesson-1",)
    with pytest.raises(ValidationError):
        LearningUnit(
            unit_id="unit-1",
            path_id="path-1",
            ordinal=1,
            title="Duplicate lessons",
            band=Band.A2,
            lesson_ids=("lesson-1", "lesson-1"),
        )
    with pytest.raises(ValidationError):
        LearningPath(
            path_id="path-1",
            title="Wrong parent",
            band_from=Band.A2,
            band_to=Band.B1,
            units=(unit.model_copy(update={"path_id": "other"}),),
            content_version="v1",
        )
    valid = full_lesson()
    unknown_rules = valid.model_copy(
        update={
            "steps": (
                *(
                    step.model_copy(update={"rules_version": "lesson-rules-v2"})
                    for step in valid.steps
                ),
            )
        }
    )
    assert lint_lesson(unknown_rules).valid  # Unknown rules may remain editable drafts.
    validation = lint_lesson(unknown_rules, for_publish=True)
    assert not validation.valid
    assert "RULES_VERSION_UNSUPPORTED" in {issue.code for issue in validation.errors}
    with pytest.raises(ValueError, match="must pass publication lint"):
        PublishedLessonVersion.from_lesson(unknown_rules, version=1, published_at=NOW)
    with pytest.raises(ValidationError):
        PublishedLessonVersion.from_lesson(valid, version=1, published_at=datetime(2026, 10, 15))


def test_content_models_reject_invalid_rounds_steps_and_hierarchy_order() -> None:
    from aicefr.lessons.model import LearningPath, LearningUnit, OutlinePayload

    with pytest.raises(ValidationError, match="min_seconds cannot exceed"):
        OutlinePayload(
            kind=StepKind.OUTLINE,
            text="Explain",
            points=("one",),
            min_seconds=11,
            max_seconds=10,
        )
    with pytest.raises(ValidationError, match="first free round"):
        FreePayload(
            kind=StepKind.FREE,
            rounds=(
                FreeRound(duration_seconds=20, prompt="first"),
                FreeRound(duration_seconds=10, prompt="second"),
            ),
            max_seconds=10,
        )

    first = LearningUnit(unit_id="unit-1", path_id="path", ordinal=1, title="One", band=Band.A2)
    second = LearningUnit(unit_id="unit-2", path_id="path", ordinal=2, title="Two", band=Band.A2)
    with pytest.raises(ValidationError, match="ordered by ordinal"):
        LearningPath(
            path_id="path",
            title="Path",
            band_from=Band.A2,
            band_to=Band.B1,
            units=(second, first),
            content_version="v1",
        )
    valid_step = make_step(
        StepKind.READ_ALOUD,
        ReadAloudPayload(kind=StepKind.READ_ALOUD, text="Hi", max_seconds=5),
    )
    with pytest.raises(ValidationError, match="step ordinals must be unique"):
        Lesson(
            lesson_id="duplicate-ordinal",
            title="Lesson",
            band=Band.A2,
            steps=(valid_step, valid_step.model_copy(update={"step_id": "s2"})),
        )


def test_attempt_models_enforce_time_and_round_shapes() -> None:
    from aicefr.lessons.model import StepResult

    with pytest.raises(ValidationError):
        StepCompletion(
            attempt_id="a1",
            step_id="s1",
            kind=StepKind.FREE,
            status=StepAttemptStatus.COMPLETE,
            attempted_at=NOW,
        )
    with pytest.raises(ValidationError):
        StepCompletion(
            attempt_id="a2",
            step_id="s1",
            kind=StepKind.REPEAT,
            status=StepAttemptStatus.COMPLETE,
            attempted_at=NOW,
            round_index=0,
        )
    with pytest.raises(ValidationError, match="must be finite"):
        StepResult(
            step_id="s1",
            kind=StepKind.FREE,
            status="PASS",
            elapsed_seconds=float("inf"),
            feedback="Finished",
        )


def test_step_evidence_and_lesson_progress_validate_source_bounds_and_finiteness() -> None:
    from aicefr.lessons.model import LessonProgress, StepResult, StepTokenEvidence

    evidence = StepTokenEvidence(
        reference_index=0,
        source_word_index=2,
        expected_token="hello",
        heard_token="hello",
        operation="MATCH",
        confidence=0.9,
        state="HEARD",
    )
    with pytest.raises(ValidationError, match="exceeds source transcript"):
        StepResult(
            step_id="s1",
            kind=StepKind.READ_ALOUD,
            status="PASS",
            evidence=(evidence,),
            word_count=2,
            feedback="Matched.",
        )
    with pytest.raises(ValidationError):
        LessonProgress(
            completed_step_ids=(),
            required_step_count=1,
            completion_fraction=float("nan"),
            completed_free_rounds=0,
            required_free_rounds=2,
            complete=False,
        )


def test_repeat_alignment_exposes_expected_heard_confidence_and_unsure_lemma() -> None:
    step = make_step(
        StepKind.REPEAT, RepeatPayload(kind=StepKind.REPEAT, text="we go home", max_seconds=10)
    )
    result = evaluate_step(
        step,
        transcript(
            words=(
                word("outside", 0, 0.2),
                word("we", 1, 1.2),
                word("went", 1.3, 1.5),
                word("home", 1.6, 1.8),
            )
        ),
        (TimeSpan(start_s=1, end_s=2),),
    )
    assert result.status.value == "UNSURE"
    assert [row.state for row in result.evidence] == [
        StepEvidenceState.HEARD,
        StepEvidenceState.UNSURE,
        StepEvidenceState.HEARD,
    ]
    assert [row.source_word_index for row in result.evidence] == [1, 2, 3]
    assert result.word_count == 4
    assert result.evidence[1].expected_token == "go"
    assert result.evidence[1].heard_token == "went"


def test_missing_confidence_and_silence_do_not_claim_wrong() -> None:
    step = make_step(
        StepKind.READ_ALOUD,
        ReadAloudPayload(kind=StepKind.READ_ALOUD, text="hello", max_seconds=10),
    )
    silence = evaluate_step(step, transcript("wrong"), ())
    assert silence.status.value == "UNMEASURED"
    uncertain = evaluate_step(
        step, transcript(words=(word("hello", 0, 0.4, None),)), (TimeSpan(start_s=0, end_s=1),)
    )
    assert uncertain.status.value == "UNSURE"
    assert uncertain.evidence[0].state is StepEvidenceState.UNSURE
    failed = evaluate_step(
        step, transcript(words=(word("yellow", 0, 0.4, 0.99),)), (TimeSpan(start_s=0, end_s=1),)
    )
    assert failed.status.value == "FAIL"
    assert failed.evidence[0].state is StepEvidenceState.MISSED


def test_vad_prunes_words_without_renumbering_source_indices() -> None:
    step = make_step(
        StepKind.REPEAT, RepeatPayload(kind=StepKind.REPEAT, text="hello", max_seconds=10)
    )
    result = evaluate_step(
        step,
        transcript(words=(word("noise", 0, 0.1), word("hello", 1, 1.2))),
        (TimeSpan(start_s=1, end_s=2),),
    )
    assert result.evidence[0].source_word_index == 1


def test_gap_requires_complete_expected_phrase() -> None:
    step = make_step(
        StepKind.GAP,
        GapPayload(
            kind=StepKind.GAP, text="Turn ___ the light", answers=("turn off",), max_seconds=10
        ),
    )
    partial = evaluate_step(
        step, transcript(words=(word("turn", 0, 0.2),)), (TimeSpan(start_s=0, end_s=1),)
    )
    separated = evaluate_step(
        step,
        transcript(words=(word("turn", 0, 0.2), word("it", 0.3, 0.4), word("off", 0.5, 0.7))),
        (TimeSpan(start_s=0, end_s=1),),
    )
    exact = evaluate_step(
        step,
        transcript(words=(word("turn", 0, 0.2), word("off", 0.3, 0.5))),
        (TimeSpan(start_s=0, end_s=1),),
    )
    assert partial.status.value == "UNSURE"  # a deleted transcript word has no ASR confidence.
    assert separated.status.value == "FAIL"
    assert exact.status.value == "PASS"


def test_free_round_is_bounded_and_persists_elapsed_evidence() -> None:
    step = full_lesson().steps[-1]
    transcript_words = transcript(words=(word("hello", 0, 0.8),))
    ok = evaluate_step(
        step, transcript_words, (TimeSpan(start_s=0, end_s=0.8),), round_index=0, elapsed_seconds=50
    )
    assert ok.status.value == "UNMEASURED"  # practice QC floor remains one second
    ok = evaluate_step(
        step, transcript_words, (TimeSpan(start_s=0, end_s=1.2),), round_index=0, elapsed_seconds=50
    )
    assert ok.status.value == "PASS" and ok.round_count == 2
    assert ok.rules_version == "lesson-rules-v1"
    late = evaluate_step(
        step, transcript_words, (TimeSpan(start_s=0, end_s=1.2),), round_index=0, elapsed_seconds=61
    )
    assert late.status.value == "FAIL" and late.elapsed_seconds == 61
    assert ok.speaking_s == late.speaking_s == 1.2
    assert late.time_evidence == (TimeSpan(start_s=0, end_s=1.2),)
    overlapped = evaluate_step(
        step,
        transcript_words,
        (TimeSpan(start_s=0, end_s=0.9), TimeSpan(start_s=0.5, end_s=1.4)),
        round_index=0,
        elapsed_seconds=2,
    )
    assert overlapped.speaking_s == pytest.approx(1.4)
    with pytest.raises(ValueError):
        evaluate_step(step, transcript_words, (TimeSpan(start_s=0, end_s=1.2),))
    with pytest.raises(ValueError):
        evaluate_step(
            step,
            transcript_words,
            (TimeSpan(start_s=0, end_s=1.2),),
            round_index=2,
            elapsed_seconds=1,
        )


def test_unsupported_lesson_rules_version_cannot_execute_or_claim_current_rules() -> None:
    step = full_lesson().steps[0].model_copy(update={"rules_version": "lesson-rules-v99"})
    with pytest.raises(ValueError, match="unsupported lesson rules version: lesson-rules-v99"):
        evaluate_step(step, transcript("hello"), (TimeSpan(start_s=0, end_s=1),))


def completion(
    attempt_id: str,
    step_id: str,
    kind: StepKind,
    status: StepAttemptStatus,
    at: datetime,
    round_index: int | None = None,
    speaking_s: float = 0.0,
) -> StepCompletion:
    return StepCompletion(
        attempt_id=attempt_id,
        step_id=step_id,
        kind=kind,
        status=status,
        attempted_at=at,
        round_index=round_index,
        speaking_s=speaking_s,
    )


def test_progress_preserves_pass_and_counts_distinct_free_speaking_rounds() -> None:
    lesson = full_lesson()
    attempts = [
        completion("a", "s1", StepKind.READ_ALOUD, StepAttemptStatus.COMPLETE, NOW),
        completion(
            "a-retry",
            "s1",
            StepKind.READ_ALOUD,
            StepAttemptStatus.RETRY,
            NOW + timedelta(seconds=4),
        ),
        completion("b", "s2", StepKind.GAP, StepAttemptStatus.COMPLETE, NOW),
        completion("c", "s3", StepKind.KEYWORDS, StepAttemptStatus.COMPLETE, NOW),
        completion("r0-old", "s4", StepKind.FREE, StepAttemptStatus.COMPLETE, NOW, 0, 1.2),
        completion(
            "r0-retry",
            "s4",
            StepKind.FREE,
            StepAttemptStatus.RETRY,
            NOW + timedelta(seconds=1),
            0,
        ),
    ]
    incomplete = lesson_completion(steps=lesson.steps, attempts=attempts)
    assert not incomplete.complete
    assert incomplete.completed_step_ids == ("s1", "s2", "s3")
    assert incomplete.completed_free_rounds == 1
    attempts.extend(
        [
            completion(
                "r1",
                "s4",
                StepKind.FREE,
                StepAttemptStatus.RETRY,
                NOW + timedelta(seconds=2),
                1,
                2.5,
            ),
        ]
    )
    complete = lesson_completion(steps=lesson.steps, attempts=attempts)
    assert complete.complete
    assert complete.completed_free_rounds == 2
    assert complete.completed_step_ids == ("s1", "s2", "s3", "s4")
    wrong_kind = completion(
        "bad", "s2", StepKind.FREE, StepAttemptStatus.COMPLETE, NOW + timedelta(days=1), 0
    )
    ignored = lesson_completion(steps=lesson.steps, attempts=(*attempts, wrong_kind))
    assert ignored.complete
    with pytest.raises(ValueError):
        lesson_completion(steps=lesson.steps, attempts=attempts, required_fraction=0)


def test_free_progress_requires_distinct_spoken_rounds_not_pass_status() -> None:
    lesson = full_lesson()
    attempts = (
        completion("round0-a", "s4", StepKind.FREE, StepAttemptStatus.RETRY, NOW, 0, 1.0),
        completion("round0-b", "s4", StepKind.FREE, StepAttemptStatus.RETRY, NOW, 0, 3.0),
        completion("round1-silent", "s4", StepKind.FREE, StepAttemptStatus.COMPLETE, NOW, 1, 0.0),
    )
    progress = lesson_completion(steps=lesson.steps, attempts=attempts)
    assert progress.completed_free_rounds == 1
    assert "s4" not in progress.completed_step_ids
    assert not progress.complete


def test_review_schedule_localizes_and_advances_1_3_7_days() -> None:
    local_start = datetime(2026, 10, 15, 23, 30, tzinfo=UTC)
    first = first_review(due_from=local_start)
    assert first.due_at is not None and first.due_at.tzinfo.key == "Asia/Ho_Chi_Minh"
    assert first.due_at.date().isoformat() == "2026-10-17"
    box2 = review_again(box=1, passed=True, reviewed_at=first.due_at)
    assert box2.box == 2 and box2.due_at.date() == first.due_at.date() + timedelta(days=3)
    box3 = review_again(box=2, passed=True, reviewed_at=box2.due_at)
    assert box3.box == 3 and box3.due_at.date() == box2.due_at.date() + timedelta(days=7)
    done = review_again(box=3, passed=True, reviewed_at=box3.due_at)
    assert done.box == 4 and done.done and done.due_at is None
    reset = review_again(box=3, passed=False, reviewed_at=box3.due_at)
    assert reset.box == 1 and reset.due_at.date() == box3.due_at.date() + timedelta(days=1)
    with pytest.raises(ValueError):
        first_review(due_from=datetime(2026, 10, 15))


def test_lookup_keywords_starter_picture_and_outline_evidence_rules() -> None:
    spoken = transcript(
        words=(
            word("first", 0.0, 0.2),
            word("we", 0.3, 0.4),
            word("turn", 0.5, 0.6),
            word("off", 0.7, 0.8),
            word("finally", 0.9, 1.1),
        )
    )
    spans = (TimeSpan(start_s=0, end_s=1.2),)
    lookup = make_step(
        StepKind.LOOK_UP,
        LookUpPayload(
            kind=StepKind.LOOK_UP, text="first we turn off", show_seconds=2, max_seconds=10
        ),
    )
    assert evaluate_step(lookup, spoken, spans).status.value == "PASS"
    assert len(evaluate_step(lookup, spoken, spans).evidence) >= 4

    keywords = make_step(
        StepKind.KEYWORDS,
        KeywordsPayload(
            kind=StepKind.KEYWORDS, keywords=("first", "turn off"), min_words=4, max_seconds=10
        ),
    )
    keyword_result = evaluate_step(keywords, spoken, spans)
    assert keyword_result.status.value == "PASS"
    assert keyword_result.target_count == 2

    starter = make_step(
        StepKind.STARTER,
        StarterPayload(
            kind=StepKind.STARTER, text="Answer", starter="first we", min_words=3, max_seconds=10
        ),
    )
    assert evaluate_step(starter, spoken, spans).status.value == "PASS"
    wrong_starter = transcript(words=(word("we", 0, 0.2, 0.9), word("first", 0.3, 0.5, 0.9)))
    assert evaluate_step(starter, wrong_starter, spans).status.value == "FAIL"

    picture = make_step(
        StepKind.PICTURE,
        PicturePayload(
            kind=StepKind.PICTURE,
            prompt="Describe the picture",
            pictures=(PictureChoice(choice_id="a", description="a market"),),
            min_words=3,
            max_seconds=10,
        ),
    )
    assert evaluate_step(picture, spoken, spans).status.value == "PASS"
    uncertain = transcript(words=(word("a", 0, 0.1, None), word("cat", 0.1, 0.2, 0.9)))
    assert evaluate_step(picture, uncertain, spans).status.value == "UNSURE"

    outline = make_step(
        StepKind.OUTLINE,
        OutlinePayload(
            kind=StepKind.OUTLINE,
            text="Tell a story",
            points=("begin",),
            markers=("first", "finally"),
            min_seconds=1,
            max_seconds=10,
        ),
    )
    assert evaluate_step(outline, spoken, spans).status.value == "PASS"
    missing_marker = make_step(
        StepKind.OUTLINE,
        OutlinePayload(
            kind=StepKind.OUTLINE,
            text="Tell a story",
            points=("begin",),
            markers=("first", "however"),
            min_seconds=1,
            max_seconds=10,
        ),
    )
    assert evaluate_step(missing_marker, spoken, spans).status.value == "FAIL"


def test_text_only_transcript_has_no_confidence_and_non_ok_asr_is_unmeasured() -> None:
    repeat = make_step(
        StepKind.REPEAT,
        RepeatPayload(kind=StepKind.REPEAT, text="hello world", max_seconds=10),
    )
    text_only = evaluate_step(repeat, transcript("hello world"), (TimeSpan(start_s=0, end_s=1),))
    assert text_only.status.value == "UNSURE"
    assert text_only.evidence
    assert all(item.source_word_index is None for item in text_only.evidence)
    failed = evaluate_step(
        repeat,
        transcript("hello world", status=AsrStatus.ASR_FAILED),
        (TimeSpan(start_s=0, end_s=1),),
    )
    assert failed.status.value == "UNMEASURED"


def test_token_evidence_includes_substitution_deletion_and_insertion() -> None:
    step = make_step(
        StepKind.REPEAT,
        RepeatPayload(kind=StepKind.REPEAT, text="we like home", max_seconds=10),
    )
    result = evaluate_step(
        step,
        transcript(
            words=(
                word("we", 0, 0.1),
                word("love", 0.2, 0.3),
                word("home", 0.4, 0.5),
                word("today", 0.6, 0.7),
            )
        ),
        (TimeSpan(start_s=0, end_s=1),),
    )
    assert result.status.value == "FAIL"
    assert {item.operation.value for item in result.evidence} >= {"MATCH", "SUBSTITUTE", "INSERT"}
    assert any(item.state is StepEvidenceState.MISSED for item in result.evidence)


def test_lint_checks_order_and_free_payload() -> None:
    good = full_lesson()
    reversed_stages = Lesson(
        lesson_id="bad-order",
        title="Bad",
        band=Band.A2,
        steps=(
            good.steps[0],
            make_step(
                StepKind.KEYWORDS,
                KeywordsPayload(kind=StepKind.KEYWORDS, keywords=("first",), max_seconds=10),
                ordinal=2,
            ),
            make_step(
                StepKind.GAP,
                GapPayload(kind=StepKind.GAP, text="___", answers=("off",), max_seconds=10),
                ordinal=3,
            ),
            good.steps[3],
        ),
    )
    result = lint_lesson(reversed_stages, for_publish=True)
    assert not result.valid
    assert "STAGE_ORDER" in {item.code for item in result.errors}
    with pytest.raises(ValidationError):
        FreePayload(
            kind=StepKind.FREE,
            rounds=(
                FreeRound(duration_seconds=20, prompt="one"),
                FreeRound(duration_seconds=30, prompt="two"),
            ),
            max_seconds=30,
        )


def test_review_rejects_bad_box_and_completion_ignores_mismatched_step_kind() -> None:
    with pytest.raises(ValueError):
        review_again(box=0, passed=True, reviewed_at=NOW)
    lesson = full_lesson()
    mismatched = completion("bad-kind", "s1", StepKind.REPEAT, StepAttemptStatus.COMPLETE, NOW)
    progress = lesson_completion(steps=lesson.steps, attempts=(mismatched,))
    assert not progress.completed_step_ids
