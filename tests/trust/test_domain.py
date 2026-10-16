from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from aicefr.contracts import Band, Criterion, ReasonCode
from aicefr.trust.contracts import (
    ConformalSet,
    CriterionIndicator,
    EvidenceSpan,
    GuardDecision,
    GuardEvidence,
    GuardKind,
    LanguageDecision,
    LanguageEvidence,
    TrustAssessment,
    TrustDecision,
    TrustDisposition,
)
from aicefr.trust.policy import TrustPolicy

_SHA = "a" * 64


def test_language_and_guard_contracts_are_immutable_and_reject_bool_or_nan() -> None:
    language = LanguageEvidence(
        method="fixture",
        version="1",
        confidence=0.91,
        language="en",
        decision=LanguageDecision.ENGLISH,
    )
    with pytest.raises(ValidationError):
        language.confidence = 0.1
    with pytest.raises(ValidationError):
        LanguageEvidence(
            method="fixture",
            version="1",
            confidence=True,
            language="en",
            decision=LanguageDecision.ENGLISH,
        )
    with pytest.raises(ValidationError):
        LanguageEvidence(
            method="fixture",
            version="1",
            confidence=None,
            language="en",
            decision=LanguageDecision.NON_ENGLISH,
        )
    with pytest.raises(ValidationError):
        LanguageEvidence(
            method="fixture",
            version="1",
            confidence=0.99,
            language="vi",
            decision=LanguageDecision.ENGLISH,
        )
    with pytest.raises(ValidationError):
        GuardEvidence(
            kind=GuardKind.OFF_TOPIC,
            value=math.nan,
            threshold_version="v1",
            decision=GuardDecision.CLEAR,
        )
    with pytest.raises(ValidationError):
        GuardEvidence(
            kind=GuardKind.OFF_TOPIC,
            value=True,
            threshold_version="v1",
            decision=GuardDecision.CLEAR,
        )


def test_evidence_span_is_index_only_and_bounded() -> None:
    assert EvidenceSpan(start_word=3, end_word=7).model_dump() == {
        "start_word": 3,
        "end_word": 7,
    }
    with pytest.raises(ValidationError):
        EvidenceSpan(start_word=7, end_word=7)
    with pytest.raises(ValidationError):
        EvidenceSpan(start_word=0, end_word=5001)


def test_conformal_set_and_criterion_indicator_have_only_band_and_coverage_data() -> None:
    prediction = ConformalSet(
        alpha=0.1,
        bands=(Band.B1,),
        calibration_id="fixture-v1",
        checksum=_SHA,
        low=3.0,
        high=4.0,
    )
    indicator = CriterionIndicator(name=Criterion.RANGE, coverage=0.8)
    assert prediction.bands == (Band.B1,)
    assert indicator.label == "chỉ báo"
    assert "criterion_score" not in indicator.model_dump()
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=True,
            bands=(),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=math.nan,
            bands=(Band.B1,),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=0.5,
            bands=(Band.B1,),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=0.1,
            bands=(),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )
    with pytest.raises(ValidationError):
        CriterionIndicator(name=Criterion.RANGE, coverage=True)
    with pytest.raises(ValidationError):
        CriterionIndicator(name=Criterion.RANGE, label="score")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=0.1,
            bands=(Band.B1, Band.A2),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )
    with pytest.raises(ValidationError):
        ConformalSet(
            alpha=0.1,
            bands=(Band.B1, Band.B1),
            calibration_id="fixture-v1",
            checksum=_SHA,
            low=1.0,
            high=2.0,
        )


def test_policy_routes_uncertainty_guards_and_multiple_bands_without_score_penalty() -> None:
    policy = TrustPolicy()
    english = LanguageEvidence(
        method="fixture",
        version="1",
        confidence=0.91,
        language="en",
        decision=LanguageDecision.ENGLISH,
    )
    set_one = ConformalSet(
        alpha=0.1,
        bands=(Band.B1,),
        calibration_id="fixture-v1",
        checksum=_SHA,
        low=3.0,
        high=4.0,
    )
    multiple = set_one.model_copy(update={"bands": (Band.A2, Band.B1)})
    suspected = GuardEvidence(
        kind=GuardKind.OFF_TOPIC,
        value=0.0,
        threshold_version="v1",
        decision=GuardDecision.SUSPECTED,
    )
    assert policy.decide(english, (), set_one).disposition is TrustDisposition.CONTINUE
    assert policy.decide(None, (), set_one).reasons == (ReasonCode.LANGUAGE_UNCERTAIN,)
    assert policy.decide(english, (suspected,), set_one).reasons == (
        ReasonCode.OFF_TOPIC_SUSPECTED,
    )
    assert policy.decide(english, (), multiple).reasons == (ReasonCode.SCORE_NEAR_BOUNDARY,)
    missing = policy.decide(english, (), None)
    assert missing.disposition is TrustDisposition.NOT_EVALUATED
    assert missing.reasons == (ReasonCode.CALIBRATION_MISSING,)
    missing_with_evidence = policy.decide(
        None,
        (suspected,),
        None,
        prerequisite_reason=ReasonCode.CALIBRATION_HASH_MISMATCH,
    )
    assert missing_with_evidence.disposition is TrustDisposition.NOT_EVALUATED
    assert missing_with_evidence.reasons == (
        ReasonCode.LANGUAGE_UNCERTAIN,
        ReasonCode.OFF_TOPIC_SUSPECTED,
        ReasonCode.CALIBRATION_HASH_MISMATCH,
    )


def test_trust_contracts_deduplicate_reasons_in_first_seen_order() -> None:
    reasons = (
        ReasonCode.LANGUAGE_UNCERTAIN,
        ReasonCode.OFF_TOPIC_SUSPECTED,
        ReasonCode.LANGUAGE_UNCERTAIN,
    )
    decision = TrustDecision(disposition=TrustDisposition.REVIEW_REQUIRED, reasons=reasons)
    assessment = TrustAssessment(
        disposition=TrustDisposition.REVIEW_REQUIRED,
        reasons=reasons,
    )
    assert (
        decision.reasons
        == assessment.reasons
        == (
            ReasonCode.LANGUAGE_UNCERTAIN,
            ReasonCode.OFF_TOPIC_SUSPECTED,
        )
    )


def test_policy_rejects_non_english_and_preserves_prompt_copy_reason() -> None:
    language = LanguageEvidence(
        method="fixture",
        version="1",
        confidence=0.93,
        language="vi",
        decision=LanguageDecision.NON_ENGLISH,
        reason_code=ReasonCode.LANGUAGE_NOT_ENGLISH,
    )
    prompt_copy = GuardEvidence(
        kind=GuardKind.PROMPT_READING,
        value=0.8,
        threshold_version="v1",
        decision=GuardDecision.SUSPECTED,
    )
    prediction = ConformalSet(
        alpha=0.1,
        bands=(Band.A2, Band.B1),
        calibration_id="fixture-v1",
        checksum=_SHA,
        low=2.0,
        high=4.0,
    )
    decision = TrustPolicy().decide(language, (prompt_copy,), prediction)
    assert decision.disposition is TrustDisposition.REJECTED
    assert decision.reasons == (
        ReasonCode.LANGUAGE_NOT_ENGLISH,
        ReasonCode.PROMPT_READING_SUSPECTED,
        ReasonCode.SCORE_NEAR_BOUNDARY,
    )


def test_policy_routes_uncertain_language_and_explicit_prerequisite_failure() -> None:
    low_confidence = LanguageEvidence(
        method="fixture",
        version="1",
        confidence=0.8,
        language="en",
        decision=LanguageDecision.UNCERTAIN,
        reason_code=ReasonCode.LANGUAGE_UNCERTAIN,
    )
    prediction = ConformalSet(
        alpha=0.1,
        bands=(Band.B1,),
        calibration_id="fixture-v1",
        checksum=_SHA,
        low=3.0,
        high=4.0,
    )
    policy = TrustPolicy()
    uncertain = policy.decide(low_confidence, (), prediction)
    assert uncertain.disposition is TrustDisposition.REVIEW_REQUIRED
    assert uncertain.reasons == (ReasonCode.LANGUAGE_UNCERTAIN,)
    failed = policy.decide(
        low_confidence,
        (),
        prediction,
        prerequisites=False,
        prerequisite_reason=ReasonCode.CALIBRATION_INVALID,
    )
    assert failed.disposition is TrustDisposition.NOT_EVALUATED
    assert failed.reasons == (ReasonCode.LANGUAGE_UNCERTAIN, ReasonCode.CALIBRATION_INVALID)


def test_policy_downgrades_missing_or_boundary_confidence_even_if_decision_says_english() -> None:
    valid_english = LanguageEvidence(
        method="fixture",
        version="1",
        confidence=0.91,
        language="en",
        decision=LanguageDecision.ENGLISH,
    )
    prediction = ConformalSet(
        alpha=0.1,
        bands=(Band.B1,),
        calibration_id="fixture-v1",
        checksum=_SHA,
        low=3.0,
        high=4.0,
    )
    policy = TrustPolicy()
    for confidence in (None, 0.80):
        inconsistent = valid_english.model_copy(update={"confidence": confidence})
        decision = policy.decide(inconsistent, (), prediction)
        assert decision.disposition is TrustDisposition.REVIEW_REQUIRED
        assert decision.reasons == (ReasonCode.LANGUAGE_UNCERTAIN,)
