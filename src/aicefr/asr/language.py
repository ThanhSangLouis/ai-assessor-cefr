"""Independent language identification for local ASR output."""

from __future__ import annotations

from typing import Protocol

from aicefr.contracts import DecodedAudio, ReasonCode
from aicefr.trust.contracts import LanguageDecision, LanguageEvidence
from aicefr.trust.policy import TrustPolicy


class LanguageDetector(Protocol):
    def detect_language(self, audio: DecodedAudio) -> tuple[str | None, float | None]: ...


class LanguageIdentifier:
    """Turns detector output into auditable language evidence.

    A failed or unavailable detector is explicitly uncertain. It never infers
    language from forced-English transcript text.
    """

    METHOD = "faster-whisper-detect-v1"
    VERSION = "1"

    def evaluate_language(
        self,
        language: str | None,
        confidence: float | None,
        *,
        method: str = METHOD,
        version: str = VERSION,
    ) -> LanguageEvidence:
        language = language.strip().lower() if isinstance(language, str) else None
        valid_confidence = (
            confidence
            if isinstance(confidence, (int, float))
            and not isinstance(confidence, bool)
            and 0.0 <= confidence <= 1.0
            else None
        )
        if language is None or not language or valid_confidence is None:
            return LanguageEvidence(
                method=method,
                version=version,
                confidence=valid_confidence,
                language=language or None,
                decision=LanguageDecision.UNCERTAIN,
                reason_code=ReasonCode.LANGUAGE_UNCERTAIN,
            )
        if valid_confidence <= TrustPolicy.LANGUAGE_CONFIDENCE_THRESHOLD:
            decision = LanguageDecision.UNCERTAIN
        elif language == "en":
            decision = LanguageDecision.ENGLISH
        else:
            decision = LanguageDecision.NON_ENGLISH
        return LanguageEvidence(
            method=method,
            version=version,
            confidence=float(valid_confidence),
            language=language,
            decision=decision,
            reason_code=(
                ReasonCode.LANGUAGE_NOT_ENGLISH
                if decision is LanguageDecision.NON_ENGLISH
                else (
                    ReasonCode.LANGUAGE_UNCERTAIN
                    if decision is LanguageDecision.UNCERTAIN
                    else None
                )
            ),
        )

    def evaluate(self, audio: DecodedAudio, detector: LanguageDetector) -> LanguageEvidence:
        try:
            language, confidence = detector.detect_language(audio)
        except Exception:
            return self.evaluate_language(None, None)
        return self.evaluate_language(language, confidence)


__all__ = ["LanguageIdentifier", "LanguageDetector"]
