import json

from aicefr.contracts import (
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    FeatureSet,
    FeatureValue,
    Interaction,
    Provenance,
    ReasonCode,
    Transcript,
    Word,
)
from aicefr.report.contracts import (
    CommentRequest,
    CommentTemplate,
    DiagnosticReport,
    EvidenceRef,
    EvidenceSource,
    ReportStatus,
)
from aicefr.report.service import DiagnosticReportBuilder, ReportInput
from aicefr.trust.contracts import CriterionIndicator, TrustAssessment, TrustDisposition


def _assessment(status=AssessmentStatus.REVIEW_REQUIRED) -> Assessment:
    return Assessment(
        response_id="fixture-response",
        status=status,
        overall_score=3.4 if status is not AssessmentStatus.NOT_EVALUATED else None,
        overall_band=Band.B1 if status is not AssessmentStatus.NOT_EVALUATED else None,
        criteria=tuple(
            CriterionCoverage(criterion=criterion, coverage=1.0, features=("fixture",))
            for criterion in Criterion
        ),
        interaction=Interaction(),
        reasons=(ReasonCode.SCORE_NEAR_BOUNDARY,)
        if status is AssessmentStatus.REVIEW_REQUIRED
        else (ReasonCode.FEATURE_NOT_COMPUTABLE,),
        provenance=Provenance(
            model_version="ridge-v2",
            model_sha256="0" * 64,
            feature_version="features-v3",
            band_map_version="bands-v1",
            calibration_version=None,
            unit_of_inference="một bài nói",
            scored_at="2026-09-28T00:00:00+00:00",
        ),
    )


def _transcript() -> Transcript:
    return Transcript(
        response_id="fixture-response",
        status="OK",
        text="hello world",
        words=(Word(text="hello", start_s=0.1, end_s=0.3),),
        asr_model="whisper-small",
        engine="fake",
        engine_version="1",
        decode_config_version="decode-v1",
        audio_sha256="1" * 64,
        test_only=True,
    )


def _features() -> FeatureSet:
    return FeatureSet(
        response_id="fixture-response",
        values=(FeatureValue(name="n_words", value=2.0, unit="words"),),
        feature_version="features-v3",
        vad_name="fake-vad",
        vad_version="1",
        vad_threshold=0.5,
        vad_min_silence_ms=100,
        asr_model="whisper-small",
        transcript_ref="fixture-response",
        audio_sha256="1" * 64,
    )


def _input(**changes) -> ReportInput:
    values = {
        "response_id": "fixture-response",
        "audio_duration_s": 2.0,
        "assessment": _assessment(),
        "transcript": _transcript(),
        "features": _features(),
        "evidence_refs": (),
        "comment_requests": (),
    }
    values.update(changes)
    return ReportInput(**values)


def test_m06_test_001_no_valid_evidence_means_no_assertive_comments():
    report = DiagnosticReportBuilder().build(
        _input(
            comment_requests=(
                CommentRequest(
                    criterion=Criterion.FLUENCY,
                    template=CommentTemplate.WORD_TIMING_OBSERVED,
                    evidence_id="missing",
                ),
            )
        )
    )

    assert report.comments == ()
    assert report.evidence_issues[0].reason == "COMMENT_EVIDENCE_MISSING"
    assert "thiếu hoặc sai evidence" in report.limitations[-1]


def test_m06_test_002_valid_word_ref_has_matching_response_version_and_timestamp():
    reference = EvidenceRef(
        evidence_id="word-0",
        response_id="fixture-response",
        source=EvidenceSource.TRANSCRIPT,
        source_version="decode-v1",
        criterion=Criterion.FLUENCY,
        start_s=0.1,
        end_s=0.3,
        word_index=0,
    )
    report = DiagnosticReportBuilder().build(
        _input(
            evidence_refs=(reference,),
            comment_requests=(
                CommentRequest(
                    criterion=Criterion.FLUENCY,
                    template=CommentTemplate.WORD_TIMING_OBSERVED,
                    evidence_id="word-0",
                ),
            ),
        )
    )

    assert len(report.comments) == 1
    assert report.comments[0].evidence_id == "word-0"
    assert report.evidence_issues == ()


def test_m06_test_003_rejects_foreign_stale_and_out_of_range_evidence():
    references = (
        EvidenceRef(
            evidence_id="foreign",
            response_id="another-response",
            source=EvidenceSource.TRANSCRIPT,
            source_version="decode-v1",
            criterion=Criterion.FLUENCY,
        ),
        EvidenceRef(
            evidence_id="stale",
            response_id="fixture-response",
            source=EvidenceSource.FEATURE_SET,
            source_version="features-v2",
            criterion=Criterion.FLUENCY,
        ),
        EvidenceRef(
            evidence_id="late",
            response_id="fixture-response",
            source=EvidenceSource.TRANSCRIPT,
            source_version="decode-v1",
            criterion=Criterion.FLUENCY,
            start_s=1.9,
            end_s=2.1,
        ),
    )
    report = DiagnosticReportBuilder().build(_input(evidence_refs=references))

    assert {issue.reason for issue in report.evidence_issues} == {
        "EVIDENCE_RESPONSE_MISMATCH",
        "EVIDENCE_SOURCE_VERSION_MISMATCH",
        "EVIDENCE_TIMESTAMP_OUT_OF_RANGE",
    }
    assert report.comments == ()


def test_m06_test_004_not_evaluated_never_exposes_band_and_stays_provisional():
    report_input = _input(assessment=_assessment(AssessmentStatus.NOT_EVALUATED))
    report = DiagnosticReportBuilder().build(report_input)

    assert report.status is ReportStatus.PROVISIONAL
    assert report.overall_score is None and report.overall_band is None
    assert report.teacher_verified is False
    assert report.teacher_final is None


def test_m06_test_006_report_has_one_overall_and_five_coverage_rows_without_criterion_scores():
    report = DiagnosticReportBuilder().build(_input())

    assert report.overall_score == 3.4
    assert report.overall_band is Band.B1
    assert tuple(row.criterion for row in report.criteria) == tuple(Criterion)
    assert all("score" not in type(row).model_fields for row in report.criteria)
    assert report.interaction.level is None
    assert report.interaction.score_status == "insufficient_evidence"


def test_old_long_window_results_source_version_round_trips_unchanged():
    window_results = json.dumps(
        [
            {"start_s": index * 10, "end_s": (index + 1) * 10, "score": 3.4, "band": "B1"}
            for index in range(20)
        ],
        separators=(",", ":"),
    )
    assert len(window_results) > 160
    report = DiagnosticReportBuilder().build(
        _input(source_versions={"window_results": window_results})
    )

    legacy_json = report.model_dump(mode="json")
    legacy_json.pop("trust")
    legacy_json.pop("prediction_set")
    legacy_json.pop("criterion_indicators")
    legacy_json.pop("provenance")
    restored = DiagnosticReport.model_validate_json(json.dumps(legacy_json))

    assert restored.source_versions["window_results"] == window_results


def test_trust_indicators_reference_only_validated_matching_criterion_evidence():
    valid_id = f"feature:n_words:{(2.0).hex()}"
    invalid_id = "foreign-word"
    trust = TrustAssessment(
        criterion_indicators=tuple(
            CriterionIndicator(name=criterion, coverage=0.5) for criterion in Criterion
        ),
        disposition=TrustDisposition.NOT_EVALUATED,
    )
    report = DiagnosticReportBuilder().build(
        _input(
            trust=trust,
            evidence_refs=(
                EvidenceRef(
                    evidence_id=valid_id,
                    response_id="fixture-response",
                    source=EvidenceSource.FEATURE_SET,
                    source_version="features-v3",
                    criterion=Criterion.FLUENCY,
                ),
                EvidenceRef(
                    evidence_id=invalid_id,
                    response_id="another-response",
                    source=EvidenceSource.TRANSCRIPT,
                    source_version="decode-v1",
                    criterion=Criterion.FLUENCY,
                    word_index=0,
                    start_s=0.1,
                    end_s=0.3,
                ),
            ),
        )
    )

    assert report.trust.criterion_indicators == report.criterion_indicators
    references = {ref.evidence_id: ref for ref in report.evidence_refs}
    fluency = next(item for item in report.criterion_indicators if item.name is Criterion.FLUENCY)
    assert fluency.evidence_refs == (valid_id,)
    for indicator in report.criterion_indicators:
        assert all(
            reference_id in references and references[reference_id].criterion is indicator.name
            for reference_id in indicator.evidence_refs
        )
    assert invalid_id not in {
        reference_id
        for indicator in report.criterion_indicators
        for reference_id in indicator.evidence_refs
    }
    assert any(issue.evidence_id == invalid_id for issue in report.evidence_issues)
