from __future__ import annotations

import math

from aicefr.asr.language import LanguageIdentifier
from aicefr.contracts import ReasonCode
from aicefr.trust.contracts import LanguageDecision


def test_language_confidence_boundary_is_uncertain() -> None:
    identifier = LanguageIdentifier()
    assert identifier.evaluate_language("en", 0.81).decision is LanguageDecision.ENGLISH
    non_english = identifier.evaluate_language("vi", 0.81)
    assert non_english.decision is LanguageDecision.NON_ENGLISH
    assert non_english.reason_code is ReasonCode.LANGUAGE_NOT_ENGLISH
    uncertain = identifier.evaluate_language("en", 0.80)
    assert uncertain.decision is LanguageDecision.UNCERTAIN
    assert uncertain.reason_code is ReasonCode.LANGUAGE_UNCERTAIN
    assert identifier.evaluate_language("en", 0.79).decision is LanguageDecision.UNCERTAIN


def test_empty_unknown_invalid_or_missing_language_is_uncertain() -> None:
    identifier = LanguageIdentifier()
    for language, probability in (
        (None, None),
        ("", 0.99),
        ("en", None),
        ("vi", math.nan),
        ("en", True),
        ("vi", 1.01),
    ):
        assert (
            identifier.evaluate_language(language, probability).decision
            is LanguageDecision.UNCERTAIN
        )


def test_language_detector_failure_returns_unknown_evidence() -> None:
    class FailedDetector:
        def detect_language(self, _audio):
            raise RuntimeError("fixture detector failure")

    # evaluate() does not require reading or fabricating real audio on failure.
    evidence = LanguageIdentifier().evaluate(None, FailedDetector())  # type: ignore[arg-type]
    assert evidence.language is None
    assert evidence.confidence is None
    assert evidence.decision is LanguageDecision.UNCERTAIN
