"""Pure trust disposition policy. It never sees or changes score inputs."""

from __future__ import annotations

from collections.abc import Sequence

from aicefr.contracts import ReasonCode
from aicefr.trust.contracts import (
    LANGUAGE_CONFIDENCE_THRESHOLD as _LANGUAGE_CONFIDENCE_THRESHOLD,
)
from aicefr.trust.contracts import (
    ConformalSet,
    GuardDecision,
    GuardEvidence,
    LanguageDecision,
    LanguageEvidence,
    TrustDecision,
    TrustDisposition,
)


class TrustPolicy:
    """Conservative disposition policy with a pinned confidence boundary."""

    VERSION = "trust-policy-v1"
    LANGUAGE_CONFIDENCE_THRESHOLD = _LANGUAGE_CONFIDENCE_THRESHOLD

    def decide(
        self,
        language: LanguageEvidence | None,
        guards: Sequence[GuardEvidence],
        conformal: ConformalSet | None,
        *,
        prerequisites: bool = True,
        prerequisite_reason: ReasonCode | None = None,
    ) -> TrustDecision:
        reasons: list[ReasonCode] = []
        disposition = TrustDisposition.CONTINUE
        if language is None or language.decision is LanguageDecision.UNCERTAIN:
            reasons.append(ReasonCode.LANGUAGE_UNCERTAIN)
            disposition = TrustDisposition.REVIEW_REQUIRED
        elif language.decision is LanguageDecision.NON_ENGLISH:
            reasons.append(ReasonCode.LANGUAGE_NOT_ENGLISH)
            disposition = TrustDisposition.REJECTED
        elif (
            language.confidence is None or language.confidence <= self.LANGUAGE_CONFIDENCE_THRESHOLD
        ):
            reasons.append(ReasonCode.LANGUAGE_UNCERTAIN)
            disposition = TrustDisposition.REVIEW_REQUIRED
        else:
            disposition = TrustDisposition.CONTINUE

        for guard in guards:
            if guard.decision is GuardDecision.SUSPECTED:
                if guard.kind.value == "off_topic":
                    reasons.append(ReasonCode.OFF_TOPIC_SUSPECTED)
                elif guard.kind.value == "prompt_reading":
                    reasons.append(ReasonCode.PROMPT_READING_SUSPECTED)
                if disposition is TrustDisposition.CONTINUE:
                    disposition = TrustDisposition.REVIEW_REQUIRED

        if not prerequisites or conformal is None:
            reason = prerequisite_reason or ReasonCode.CALIBRATION_MISSING
            reasons.append(reason)
            return TrustDecision(
                disposition=TrustDisposition.NOT_EVALUATED,
                reasons=tuple(reasons),
            )

        if len(conformal.bands) > 1:
            reasons.append(ReasonCode.SCORE_NEAR_BOUNDARY)
            if disposition is TrustDisposition.CONTINUE:
                disposition = TrustDisposition.REVIEW_REQUIRED

        return TrustDecision(disposition=disposition, reasons=tuple(reasons))
