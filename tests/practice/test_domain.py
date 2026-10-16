from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aicefr.contracts import (
    AsrStatus,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Transcript,
    Word,
)
from aicefr.practice.bank import (
    PRACTICE_MISSIONS,
    get_mission,
    list_missions,
    mission_catalogue_hash,
)
from aicefr.practice.contracts import (
    MissionGoal,
    MissionKind,
    MissionMeasurement,
    PracticeMission,
    PracticePurpose,
    PracticeReason,
    PracticeResult,
    PracticeStatus,
    TimeSpan,
    WordEvidence,
)
from aicefr.practice.missions import MissionChecker
from aicefr.practice.recommend import recommend_next


def transcript(
    text: str = "", *, words: tuple[Word, ...] = (), status: AsrStatus = AsrStatus.OK
) -> Transcript:
    return Transcript(
        response_id="resp-1",
        status=status,
        text=text,
        words=words,
        engine="fixture",
        engine_version="1",
        decode_config_version="1",
        audio_sha256="a" * 64,
    )


def word(text: str, start: float, end: float, prob: float | None = 0.9) -> Word:
    return Word(text=text, start_s=start, end_s=end, prob=prob)


def test_catalogue_is_frozen_complete_and_stable() -> None:
    assert len(PRACTICE_MISSIONS) == len(list_missions()) == 15
    assert [item.mission_id for item in PRACTICE_MISSIONS] == [
        f"PR-{prefix}-{band}"
        for prefix in ("FLU", "COH", "RAN", "ACC", "PHO")
        for band in ("A2", "B1", "B2")
    ]
    assert len({item.criterion for item in PRACTICE_MISSIONS}) == 5
    assert len({item.target_band for item in PRACTICE_MISSIONS}) == 3
    assert mission_catalogue_hash() == mission_catalogue_hash()
    with pytest.raises(ValidationError):
        PRACTICE_MISSIONS[0].title = "mutable"
    with pytest.raises(KeyError):
        get_mission("not-a-mission")


def test_mission_metadata_and_result_have_no_assessment_fields() -> None:
    mission = get_mission("PR-FLU-A2")
    assert mission.target_band is Band.A2
    result = MissionChecker().check(
        mission, transcript(), (TimeSpan(start_s=0, end_s=32),), purpose=PracticePurpose.LEARNING
    )
    assert result.purpose is PracticePurpose.LEARNING
    assert result.status is PracticeStatus.PASS  # VAD effort measures do not depend on ASR text.
    assert not {"overall_score", "overall_band", "band", "teacher_verified"} & set(
        type(result).model_fields
    )
    assert result.rules_version == "mission-rules-v1"


def test_mission_checker_rejects_unsupported_rules_without_claiming_execution() -> None:
    mission = get_mission("PR-FLU-A2").model_copy(update={"rules_version": "mission-rules-v99"})
    with pytest.raises(ValueError, match="unsupported mission rules version: mission-rules-v99"):
        MissionChecker().check(mission, transcript(), (TimeSpan(start_s=0, end_s=1),))


def test_result_speech_effort_is_vad_union_not_elapsed_span_or_audio_length() -> None:
    mission = get_mission("PR-FLU-A2")
    result = MissionChecker().check(
        mission,
        transcript(),
        (TimeSpan(start_s=0, end_s=10), TimeSpan(start_s=13, end_s=32)),
    )
    assert result.audio_duration_s == 32
    assert result.speaking_s == 29
    assert result.measurements[0].measured_value == 32  # Preserve SPEAK_SECONDS rule.


def test_silence_is_unmeasured_and_low_confidence_is_unsure() -> None:
    mission = get_mission("PR-COH-A2")
    checker = MissionChecker()
    silent = checker.check(mission, transcript("and but because"), ())
    assert silent.status is PracticeStatus.UNMEASURED
    assert silent.reasons == (PracticeReason.NO_SPEECH,)
    uncertain = checker.check(
        mission,
        transcript(words=(word("and", 0.0, 0.2, None), word("but", 0.3, 0.5, 0.9))),
        (TimeSpan(start_s=0, end_s=1),),
    )
    assert uncertain.measurements[0].status is PracticeStatus.UNSURE
    assert uncertain.measurements[0].measured_value is None
    assert PracticeReason.LOW_ASR_CONFIDENCE in uncertain.reasons


def test_vad_filter_preserves_original_word_indices_and_boundary_slack() -> None:
    base = get_mission("PR-COH-A2")
    goal = MissionGoal(goal_id="hit", kind=MissionKind.USE_WORDS, target=1, words=("because",))
    mission = base.model_copy(update={"goals": (goal,)})
    heard = transcript(
        words=(word("and", 0.0, 0.2), word("but", 0.5, 0.7), word("because", 1.0, 1.2))
    )
    result = MissionChecker().check(mission, heard, (TimeSpan(start_s=1.25, end_s=2.0),))
    evidence = result.measurements[0].evidence
    assert [(item.start_word_index, item.end_word_index) for item in evidence] == [(2, 3)]
    assert result.word_count == 3


def test_speaking_and_pause_rules_use_vad_not_transcript_timestamps() -> None:
    mission = get_mission("PR-FLU-A2")
    result = MissionChecker().check(
        mission,
        transcript(words=(word("hello", 0, 0.1),)),
        (TimeSpan(start_s=0, end_s=10), TimeSpan(start_s=13, end_s=32)),
    )
    assert [item.measured_value for item in result.measurements] == [32.0, 3.0]
    assert all(item.status is PracticeStatus.PASS for item in result.measurements)
    assert result.measurements[1].time_evidence[0].start_s == 10


def test_all_text_mission_rules_and_read_aloud_lemma() -> None:
    checker = MissionChecker()
    coherence = checker.check(
        get_mission("PR-COH-A2"),
        transcript(words=(word("and", 0, 0.2), word("but", 0.3, 0.5), word("because", 0.6, 0.8))),
        (TimeSpan(start_s=0, end_s=32),),
    )
    assert coherence.measurements[0].measured_value == 3
    assert coherence.measurements[0].status is PracticeStatus.PASS

    range_mission = get_mission("PR-RAN-A2")
    range_result = checker.check(
        range_mission,
        transcript(
            words=tuple(
                word(t, i, i + 0.1)
                for i, t in enumerate(
                    ("bed", "desk", "window", "chair", "lamp", "uh", "quiet", "quiet")
                )
            )
        ),
        (TimeSpan(start_s=0, end_s=8),),
    )
    assert range_result.measurements[0].measured_value == 6
    assert range_result.measurements[1].measured_value == 6

    accuracy = checker.check(
        get_mission("PR-ACC-B1"),
        transcript("If I had time I would travel. If it rains I could stay."),
        (TimeSpan(start_s=0, end_s=45),),
    )
    assert accuracy.measurements[0].status is PracticeStatus.UNSURE  # no ASR word confidence
    confident = checker.check(
        get_mission("PR-ACC-A2"),
        transcript(
            words=(
                word("went", 0, 0.2),
                word("played", 0.3, 0.6),
                word("interested", 0.7, 1),
                word("bed", 1.1, 1.3),
            )
        ),
        (TimeSpan(start_s=0, end_s=35),),
    )
    assert confident.measurements[0].measured_value == 2

    read = get_mission("PR-PHO-A2").model_copy(
        update={
            "goals": (
                MissionGoal(
                    goal_id="read",
                    kind=MissionKind.READ_ALOUD,
                    target=0.8,
                    reference_text="I went home",
                ),
            )
        }
    )
    read_result = checker.check(
        read,
        transcript(words=(word("I", 0, 0.1), word("go", 0.2, 0.4), word("home", 0.5, 0.7))),
        (TimeSpan(start_s=0, end_s=1),),
    )
    assert read_result.measurements[0].status is PracticeStatus.UNSURE
    assert read_result.measurements[0].measured_value is None
    assert read_result.measurements[0].reason is PracticeReason.LEMMA_EQUIVALENT


def test_non_ok_asr_does_not_claim_text_result_but_vad_can_measure_time() -> None:
    result = MissionChecker().check(
        get_mission("PR-FLU-A2"),
        transcript(status=AsrStatus.ASR_FAILED),
        (TimeSpan(start_s=0, end_s=35),),
    )
    assert result.measurements[0].status is PracticeStatus.PASS
    assert result.measurements[1].status is PracticeStatus.PASS


def _coverage(criterion: Criterion, value: float | None) -> CriterionCoverage:
    return CriterionCoverage(criterion=criterion, coverage=value)


def test_recommendation_fallback_weakest_coverage_nearest_band_and_latest_tie() -> None:
    fallback = recommend_next(assessments=())
    assert fallback.mission_id == "PR-FLU-A2"
    assert fallback.reason_code == "NO_ELIGIBLE_ASSESSMENT_FALLBACK_A2"
    t = datetime(2026, 10, 15, tzinfo=UTC)
    older = {
        "response_id": "a",
        "created_at": t,
        "status": AssessmentStatus.ESTIMATED,
        "overall_score": 3.2,
        "overall_band": Band.B1,
        "criteria": tuple(
            _coverage(criterion, value)
            for criterion, value in (
                (Criterion.FLUENCY, 0.2),
                (Criterion.COHERENCE, 0.9),
                (Criterion.RANGE, 0.9),
                (Criterion.ACCURACY, 0.9),
                (Criterion.PHONOLOGY, 0.9),
            )
        ),
    }
    latest = {
        **older,
        "response_id": "z",
        "created_at": t,
        "criteria": tuple(
            _coverage(criterion, value)
            for criterion, value in (
                (Criterion.FLUENCY, 0.8),
                (Criterion.COHERENCE, 0.1),
                (Criterion.RANGE, 0.9),
                (Criterion.ACCURACY, 0.9),
                (Criterion.PHONOLOGY, 0.9),
            )
        ),
    }
    from aicefr.practice.contracts import RecommendationEvidence

    recommendation = recommend_next(
        assessments=(RecommendationEvidence(**older), RecommendationEvidence(**latest))
    )
    assert recommendation.criterion is Criterion.COHERENCE
    assert recommendation.target_band is Band.B1
    assert recommendation.mission_id == "PR-COH-B1"
    assert "coverage" in recommendation.explanation
    exhausted = recommend_next(
        assessments=(RecommendationEvidence(**latest),),
        completed_mission_ids={"PR-COH-A2", "PR-COH-B1", "PR-COH-B2"},
    )
    assert exhausted.mission_id == "PR-COH-B1"


def test_recommendation_ignores_ineligible_and_completed_band_uses_nearest() -> None:
    from aicefr.practice.contracts import RecommendationEvidence

    evidence = RecommendationEvidence(
        response_id="x",
        created_at=datetime(2026, 10, 14, tzinfo=UTC),
        status=AssessmentStatus.NOT_EVALUATED,
        overall_score=None,
        overall_band=None,
        criteria=(_coverage(Criterion.RANGE, 0.01),),
    )
    assert recommend_next(assessments=(evidence,)).mission_id == "PR-FLU-A2"
    valid = evidence.model_copy(
        update={
            "status": AssessmentStatus.REVIEW_REQUIRED,
            "overall_score": 4.1,
            "overall_band": Band.B2,
        }
    )
    out = recommend_next(assessments=(valid,), completed_mission_ids={"PR-FLU-B2"})
    assert out.mission_id == "PR-FLU-B1"


def test_domain_contracts_reject_invalid_evidence_and_claimed_measurements() -> None:
    with pytest.raises(ValidationError):
        TimeSpan(start_s=1.0, end_s=1.0)
    with pytest.raises(ValidationError):
        WordEvidence(start_word_index=2, end_word_index=2)
    with pytest.raises(ValidationError):
        MissionGoal(goal_id="empty", kind=MissionKind.USE_WORDS, target=1, words=())
    with pytest.raises(ValidationError):
        MissionGoal(
            goal_id="wrong-fields",
            kind=MissionKind.SPEAK_SECONDS,
            target=1,
            words=("extra",),
        )
    with pytest.raises(ValidationError):
        MissionGoal(goal_id="no-reference", kind=MissionKind.READ_ALOUD, target=1)
    with pytest.raises(ValidationError):
        MissionGoal(
            goal_id="wrong-reference",
            kind=MissionKind.USE_WORDS,
            target=1,
            words=("hello",),
            reference_text="hello",
        )
    with pytest.raises(ValidationError):
        MissionMeasurement(goal_id="pass-without-value", target=1, status=PracticeStatus.PASS)
    with pytest.raises(ValidationError):
        MissionMeasurement(
            goal_id="unsure-with-value",
            target=1,
            measured_value=1,
            status=PracticeStatus.UNSURE,
        )
    with pytest.raises(ValidationError):
        MissionMeasurement(
            goal_id="infinite",
            target=1,
            measured_value=float("inf"),
            status=PracticeStatus.PASS,
        )

    base = get_mission("PR-FLU-A2")
    with pytest.raises(ValidationError):
        PracticeMission(**{**base.model_dump(), "criterion": Criterion.RANGE})
    with pytest.raises(ValidationError):
        PracticeMission(**{**base.model_dump(), "goals": (base.goals[0], base.goals[0])})


def test_practice_result_derives_status_and_bounds_source_evidence() -> None:
    measurement = MissionMeasurement(
        goal_id="words",
        target=1,
        measured_value=1,
        status=PracticeStatus.PASS,
        evidence=(WordEvidence(start_word_index=0, end_word_index=2),),
        time_evidence=(TimeSpan(start_s=0, end_s=1),),
    )
    base = {
        "mission_id": "PR-FLU-A2",
        "purpose": PracticePurpose.PRACTICE,
        "status": PracticeStatus.PASS,
        "measurements": (measurement,),
        "rules_version": "v1",
        "word_count": 1,
        "audio_duration_s": 1,
    }
    with pytest.raises(ValidationError, match="word evidence exceeds"):
        PracticeResult(**base)
    with pytest.raises(ValidationError, match="status must match"):
        PracticeResult(**{**base, "word_count": 2, "status": PracticeStatus.FAIL})
    with pytest.raises(ValidationError, match="time evidence exceeds"):
        PracticeResult(
            **{
                **base,
                "word_count": 2,
                "measurements": (
                    measurement.model_copy(
                        update={"evidence": (), "time_evidence": (TimeSpan(start_s=0, end_s=2),)}
                    ),
                ),
            }
        )
    with pytest.raises(ValidationError, match="goal ids must be unique"):
        PracticeResult(
            **{
                **base,
                "word_count": 2,
                "measurements": (measurement, measurement),
            }
        )


def test_time_and_recommendation_evidence_require_finite_aware_values() -> None:
    from aicefr.practice.contracts import RecommendationEvidence

    with pytest.raises(ValidationError):
        TimeSpan(start_s=float("inf"), end_s=float("inf"))
    with pytest.raises(ValidationError, match="timezone-aware"):
        RecommendationEvidence(
            response_id="naive",
            created_at=datetime(2026, 10, 15),
            status=AssessmentStatus.ESTIMATED,
            overall_score=3,
            overall_band=Band.B1,
            criteria=(),
        )
    with pytest.raises(ValidationError):
        RecommendationEvidence(
            response_id="infinite",
            created_at=datetime(2026, 10, 15, tzinfo=UTC),
            status=AssessmentStatus.ESTIMATED,
            overall_score=float("inf"),
            overall_band=Band.B1,
            criteria=(),
        )
