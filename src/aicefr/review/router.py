"""Decides which responses need a teacher's review. Implements FR-28 to FR-31."""

from __future__ import annotations

from dataclasses import dataclass

from aicefr.contracts import Assessment, FeatureSet, QcResult, QcStatus, ReasonCode, Status

LOW_ASR_CONF = 0.65


@dataclass(frozen=True)
class ReviewDecision:
    """The outcome of one routing call. A value object, not a service."""

    status: Status
    reasons: list[ReasonCode]

    @property
    def needs_teacher(self) -> bool:
        return self.status is Status.REVIEW_REQUIRED


class ReviewRouter:
    """Routes one scored response to COMPLETED, REVIEW_REQUIRED or REJECTED.

    The philosophy: the machine only scores provisionally. When it is unsure it
    hands the response to a human together with a specific reason, rather than
    silently lowering the score.

    A class rather than a bare function because the routing thresholds are
    policy, not logic. Policy has to be changeable — a stricter confidence bar
    for a high-stakes exam, a looser one for practice — without editing the
    business code that decides what the thresholds mean.
    """

    def __init__(self, low_asr_conf: float = LOW_ASR_CONF) -> None:
        self.low_asr_conf = low_asr_conf

    def route(
        self,
        qc: QcResult | None,
        assessment: Assessment | None,
        features: FeatureSet | None,
    ) -> ReviewDecision:
        reasons: list[ReasonCode] = []

        if qc is None or qc.qc_status is QcStatus.REJECT:
            return ReviewDecision(Status.REJECTED, list(qc.reasons) if qc else [])

        # QC at the REVIEW level still gets scored, but the result must pass through
        # a teacher. This is exactly why QcResult needs three levels: folding the
        # middle ground into PASS would lose this layer.
        qc_needs_human = qc.qc_status is QcStatus.REVIEW
        reasons += [r for r in qc.reasons if r not in reasons]

        if assessment is None or assessment.overall_0_6 is None:
            # Carry every flag through, including the ones raised about the
            # assessment as a whole. This branch used to read only the
            # per-criterion lists, so anything the scorer or the pipeline said
            # about the run itself -- a recogniser that does not match the one
            # the model was trained on, for instance -- was dropped exactly when
            # the result was least trustworthy.
            extra = list(assessment.reasons) if assessment else []
            extra += [r for c in (assessment.criteria if assessment else []) for r in c.reasons]
            seen = [r for r in extra if r not in reasons]
            reasons += seen or [ReasonCode.FEATURE_NOT_COMPUTABLE]
            reasons = list(dict.fromkeys(reasons))
            return ReviewDecision(Status.REVIEW_REQUIRED, reasons)

        if features is not None:
            conf = features.value_of("asr_conf_mean")
            if conf is not None and conf < self.low_asr_conf:
                reasons.append(ReasonCode.ASR_LOW_CONFIDENCE)

        # Read the flags the scorer actually set: those on the assessment as a
        # whole, and those on each criterion.
        #
        # This used to look only at the criteria, where SCORE_NEAR_BOUNDARY
        # could never appear -- the scorer raised it about the overall score,
        # into a list that was then discarded. Every response sitting exactly on
        # a band boundary therefore went straight to COMPLETED: precisely the
        # responses the model is least sure about, and precisely the case a
        # teacher is supposed to see.
        for reason in assessment.reasons:
            if reason not in reasons:
                reasons.append(reason)
        for criterion in assessment.criteria:
            for reason in criterion.reasons:
                if reason not in reasons:
                    reasons.append(reason)

        trigger = {
            ReasonCode.ASR_LOW_CONFIDENCE,
            ReasonCode.SCORE_NEAR_BOUNDARY,
            ReasonCode.HIGH_SILENCE_RATIO,
            ReasonCode.CLIPPING_DETECTED,
            ReasonCode.FEATURE_NOT_COMPUTABLE,
            ReasonCode.OUT_OF_DISTRIBUTION,
            # A different recogniser or detector moves the score for reasons
            # unrelated to the speaker, so a human decides.
            # The transcript is not trustworthy, so neither is anything counted
            # from it.
            ReasonCode.ASR_HALLUCINATION,
            ReasonCode.ASR_VERSION_MISMATCH,
            ReasonCode.VAD_VERSION_MISMATCH,
            # A median across windows is a number the model never produced for
            # a recording of this length, because no such recording was in its
            # training data. The aggregation rule is a reasoned guess, not a
            # measured one, so every long recording goes to a teacher until the
            # survey in weeks 10-11 says what the combination is worth. This
            # stays in the trigger set even when no single window complained.
            ReasonCode.SCORE_AGGREGATED,
            # La chan hop le (D022): diem giu nguyen nhung nguoi phai nghe lai.
            ReasonCode.OFF_TOPIC_SUSPECTED,
            ReasonCode.PROMPT_COPY_SUSPECTED,
        }
        needs_human = qc_needs_human or bool(set(reasons) & trigger)
        status = Status.REVIEW_REQUIRED if needs_human else Status.COMPLETED
        return ReviewDecision(status, reasons)
