"""Orchestrates one assessment run. See SDD sections 2 and 4.

Flow: quality check -> speech recognition -> voice activity detection ->
feature extraction -> scoring -> evidence -> routing decision -> report.

A practice task (D023) leaves the flow after feature extraction: its missions
are measured by fixed rules, it is never scored and never routed to a teacher.

A failure at any step still produces a Response carrying a status and
reason codes. Nothing escapes as an exception: the caller is a web request that
must answer the student either way.
"""

from __future__ import annotations

import logging
import statistics
from collections.abc import Callable

import numpy as np

from aicefr.asr.base import AsrError
from aicefr.asr.hallucination import detect_repetition
from aicefr.asr.vad import default_vad
from aicefr.contracts import (
    AnalysisWindow,
    Assessment,
    FeatureSet,
    ProcessingRequest,
    QcResult,
    ReasonCode,
    Response,
    ResponseStatus,
    TaskPurpose,
    Transcript,
)
from aicefr.features.extract import FeatureExtractor
from aicefr.features.relevance import TaskLike, validity_flags
from aicefr.observability import timed
from aicefr.ports import AsrEngine, Scorer, VoiceActivityDetector
from aicefr.practice.missions import MissionChecker
from aicefr.qc.audio_qc import AudioQualityChecker
from aicefr.report.comments import CommentBuilder
from aicefr.report.evidence import EvidenceBuilder
from aicefr.review.router import ReviewRouter
from aicefr.scoring.band_map import thresholds_of, to_band
from aicefr.scoring.scorer import ModelNotFoundError, RidgeScorer
from aicefr.scoring.windows import clip_segments, plan_windows


def trim_to_speech(
    pcm: np.ndarray, sr: int, segments: list[tuple[float, float]], pad_s: float = 0.5
) -> tuple[np.ndarray, float]:
    """Drop silence before the first word and after the last one.

    Only the ends. Pauses *inside* the response are the fluency signal the whole
    model rests on, so removing them would delete the measurement.

    Returns the trimmed audio and how many seconds were cut from the front, so
    the caller can shift the segment timings to match.
    """
    if not segments or pcm.size == 0:
        return pcm, 0.0

    first = max(0.0, min(s for s, _ in segments) - pad_s)
    last = min(pcm.size / sr, max(e for _, e in segments) + pad_s)
    if last <= first:
        return pcm, 0.0

    start, end = int(first * sr), int(last * sr)
    return pcm[start:end], first


logger = logging.getLogger(__name__)

# LID (D022): chi chan khi bo nhan dang KHA CHAC do khong phai tieng Anh. Giong
# Viet noi tieng Anh van thuong duoc doan la "en"; nguong 0,5 tranh chan nham
# bai co giong nang chi vi may phan van.
LID_MIN_PROB = 0.5


class ResponseProcessor:
    """Runs one spoken response through the whole assessment pipeline.

    Every collaborator is injected rather than constructed inside. That is what
    makes the pipeline testable without a model or a GPU: the tests pass a fake
    recogniser and an energy-based detector, and exercise the real control flow.

        "Depend upon Abstractions. Do not depend upon concretions."
        -- Robert C. Martin, Design Principles and Design Patterns, 2000

    The two collaborators declared as ports rather than concrete classes are the
    ones that reach outside the business layer: `AsrEngine` and
    `VoiceActivityDetector` both wrap a model, and `Scorer` wraps a trained
    artifact. The processor names none of Whisper, Silero or Ridge.

    One collaborator deserves a warning. The detector must be the same one used
    when the scoring model was trained: an energy detector and Silero disagree
    by an order of magnitude on segments per minute, and the model was fitted on
    Silero's numbers. Injecting it makes that choice visible at the call site
    instead of hiding it behind a default deep in the module.
    """

    def __init__(
        self,
        asr_engine: AsrEngine,
        vad: VoiceActivityDetector | None = None,
        quality_checker: AudioQualityChecker | None = None,
        extractor: FeatureExtractor | None = None,
        scorer: Scorer | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        comment_builder: CommentBuilder | None = None,
        router: ReviewRouter | None = None,
        task_lookup: Callable[[str], TaskLike | None] | None = None,
        lid_min_prob: float = LID_MIN_PROB,
        mission_checker: MissionChecker | None = None,
    ) -> None:
        self.asr_engine = asr_engine
        self.vad = vad or default_vad()
        self.quality_checker = quality_checker or AudioQualityChecker()
        self.extractor = extractor or FeatureExtractor()
        self.scorer = scorer or RidgeScorer()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.comment_builder = comment_builder or CommentBuilder()
        self.router = router or ReviewRouter()
        # Tra de bai theo task_id cho la chan lac de / doc lai de. None thi bo
        # qua la chan, khong doan de.
        self.task_lookup = task_lookup
        self.lid_min_prob = lid_min_prob
        self.mission_checker = mission_checker or MissionChecker()

    def _version_mismatches(self, asr) -> list[ReasonCode]:
        """Flag when the recogniser or detector differs from the trained-with pair."""
        trained = getattr(self.scorer, "trained_with", None) or {}
        found: list[ReasonCode] = []

        expected_asr = trained.get("asr_model")
        if expected_asr and expected_asr not in (asr.model_version or ""):
            found.append(ReasonCode.ASR_VERSION_MISMATCH)

        expected_vad = trained.get("vad_name")
        if expected_vad and expected_vad != getattr(self.vad, "name", None):
            found.append(ReasonCode.VAD_VERSION_MISMATCH)
        return found

    def _score_windows(
        self,
        asr,
        segments: list[tuple[float, float]],
        windows: list[AnalysisWindow],
        whole: FeatureSet,
    ) -> Assessment:
        """Score each window, then combine. Used only for long recordings.

        The combined score is the MEDIAN of the windows, not the mean: one
        window where the recogniser struggled should not drag the whole
        recording down, and a median ignores it while a mean does not.

        Whatever comes out carries `SCORE_AGGREGATED`, which routes the response
        to a teacher. That is not caution for its own sake -- combining window
        scores has never been validated against human ratings, and until the
        study in `docs/plan/KE_HOACH_KHAO_SAT.md` says otherwise, a number
        produced this way is a hypothesis, not a measurement.
        """
        scored: list[AnalysisWindow] = []
        values: list[float] = []

        for w in windows:
            words = [x for x in asr.words if w.start_s <= x.start_s < w.end_s]
            feats = self.extractor.extract(
                [
                    x.model_copy(
                        update={
                            "start_s": round(x.start_s - w.start_s, 3),
                            "end_s": round(x.end_s - w.start_s, 3),
                        }
                    )
                    for x in words
                ],
                clip_segments(segments, w),
                w.duration_s,
            )
            try:
                part = self.scorer.score(feats)
            except ModelNotFoundError:
                raise
            except Exception:  # noqa: BLE001 - one bad window must not lose the rest
                logger.exception("window %s failed to score", w.index)
                scored.append(
                    AnalysisWindow(
                        index=w.index,
                        start_s=round(w.start_s, 2),
                        end_s=round(w.end_s, 2),
                        overall_0_6=None,
                        band=None,
                        reasons=[ReasonCode.FEATURE_NOT_COMPUTABLE],
                    )
                )
                continue

            scored.append(
                AnalysisWindow(
                    index=w.index,
                    start_s=round(w.start_s, 2),
                    end_s=round(w.end_s, 2),
                    overall_0_6=part.overall_0_6,
                    band=part.overall_band,
                    reasons=part.reasons,
                )
            )
            if part.overall_0_6 is not None:
                values.append(part.overall_0_6)

        # Provenance comes from a real scoring run, so the report cannot end up
        # claiming a model version that never touched this audio.
        base = self.scorer.score(whole) if not values else None
        if base is not None:
            base.windows = scored
            base.reasons = [*base.reasons, ReasonCode.SCORE_AGGREGATED]
            return base

        median = statistics.median(values)
        spread = max(values) - min(values)
        thresholds = thresholds_of(getattr(self.scorer, "band_thresholds", None))

        merged = self.scorer.score(whole)
        merged.overall_0_6 = round(median, 2)
        merged.overall_band = to_band(median, thresholds)
        merged.windows = scored
        merged.window_spread = round(spread, 2)
        # Khoang CV+ duoc hieu chinh cho diem cua MOT bai noi qua mo hinh, khong
        # phai cho trung vi cua nhieu cua so. Gan no cho diem gop la hua mot muc
        # phu chua ai do; SCORE_AGGREGATED da dua bai nay toi giang vien.
        merged.interval = None
        for c in merged.criteria:
            # Khong con chep diem vao tung tieu chi: CriterionCoverage chi mang
            # do phu phep do, va do phu do khong doi khi ta lay trung vi.
            #
            # Same correction as below, applied per criterion. Missing it left
            # OUT_OF_DISTRIBUTION on all five rows even though the assessment
            # no longer carried it, and the review screen -- which reads the
            # criteria as well -- went on showing the flag next to a score.
            c.reasons = [r for r in c.reasons if r is not ReasonCode.OUT_OF_DISTRIBUTION]

        # The whole-recording pass was only for provenance, and it naturally
        # reports OUT_OF_DISTRIBUTION -- being too long is why we are here.
        # Carrying that reason forward would put "bài dài quá nên không chấm
        # được" next to a score, which is the report contradicting itself. Each
        # window WAS inside the trained range, so the finding no longer holds.
        window_reasons = {r for w in scored for r in w.reasons}
        window_reasons.discard(ReasonCode.OUT_OF_DISTRIBUTION)
        merged.out_of_range = []
        merged.reasons = [
            *sorted(window_reasons, key=lambda r: r.value),
            ReasonCode.SCORE_AGGREGATED,
        ]
        return merged

    def _practice(
        self,
        base: dict,
        task,
        qc: QcResult,
        asr: Transcript,
        features: FeatureSet,
        segments: list[tuple[float, float]],
        extra_reasons: list[ReasonCode],
    ) -> Response:
        """Finish a practice attempt: measure its missions, no scoring, no routing (D023).

        The scoring model is not called. A practice task is a short constrained
        exercise -- use given words, read a passage aloud -- that lies outside the
        exam responses the model learned from, so a band here would be a number from
        outside the region the model can be trusted in. And even where it were valid,
        the model's error is larger than the real progress between two attempts:
        printing a band each time teaches the learner to read noise as progress.

        QC reasons (for example a recording with a lot of silence) are kept so the
        result page can say so.
        """
        result = self.mission_checker.check(task, asr, segments)
        return Response(
            **base,
            status=ResponseStatus.COMPLETED,
            qc=qc,
            asr=asr,
            features=features,
            practice=result,
            reasons=[*qc.reasons, *extra_reasons],
        )

    def process(
        self,
        request: ProcessingRequest,
        pcm: np.ndarray,
        sr: int,
        channels: int = 1,
        size_bytes: int | None = None,
    ) -> Response:
        """Run the full flow for one response."""
        task = self.task_lookup(request.task_id) if self.task_lookup else None
        # D023. A practice attempt never waits for a teacher: wherever an
        # assessment would go to a teacher, a practice attempt is rejected with
        # its reason, so the learner knows why and can try again instead of
        # waiting for someone who will never come.
        is_practice = getattr(task, "purpose", None) is TaskPurpose.PRACTICE
        needs_teacher = ResponseStatus.REJECTED if is_practice else ResponseStatus.REVIEW_REQUIRED
        base = {
            "response_id": request.response_id,
            "config_version": request.config_version,
            "prompt_version": request.prompt_version,
        }

        # Pass the real channel count and byte size: without them the report
        # claimed every recording was mono, and the AUDIO_TOO_LARGE branch was
        # unreachable from the pipeline.
        with timed("pipeline_stage_seconds", stage="qc"):
            qc = self.quality_checker.check(pcm, sr, channels=channels, size_bytes=size_bytes)
        if not qc.passed:
            return Response(**base, status=ResponseStatus.REJECTED, qc=qc, reasons=qc.reasons)

        # Voice activity detection runs BEFORE recognition, not after.
        #
        # Whisper does not stay quiet when handed silence: it emits a token and
        # repeats it. A real submission here -- 95 seconds containing about 186
        # spoken words -- came back with 398, of which one token appeared 212
        # times, because the speaker stopped talking around the seventy-second
        # mark and the recorder kept going. Trimming the silence away removes
        # the input that causes it.
        # Everything downstream stays on the ORIGINAL recording's clock. Only the
        # recogniser sees the trimmed audio, and its word timestamps are shifted
        # back afterwards.
        #
        # Getting this wrong is not cosmetic. Trimmed-frame timestamps drove two
        # separate faults at once: the transcript highlighted each word early by
        # exactly the amount of leading silence removed, so the karaoke ran ahead
        # of the sound and "nghe đoạn này" jumped to the wrong place; and
        # `vad_onset_delay` -- how long the speaker waited before starting --
        # collapsed to the 0.5 second pad for every response, because the pad is
        # all that was left in front of the first word. The model was trained on
        # delays spanning 0.3 to 5.5 seconds, so it received the same wrong
        # number every time and shifted every score by the same amount.
        total_dur_s = pcm.size / sr
        with timed("pipeline_stage_seconds", stage="vad"):
            segments = self.vad.segments(pcm, sr)
        trimmed, offset_s = trim_to_speech(pcm, sr, segments)

        try:
            with timed("pipeline_stage_seconds", stage="asr"):
                asr = self.asr_engine.transcribe(trimmed, sr)
        except AsrError as e:
            # The reason code alone tells the learner nothing went right; the
            # log has to say why, or a missing package looks like a bad model.
            logger.warning("recogniser failed: %s", e)
            return Response(
                **base, status=ResponseStatus.FAILED, qc=qc, reasons=[ReasonCode.ASR_FAILED]
            )
        if not asr.text.strip():
            return Response(
                **base,
                status=needs_teacher,
                qc=qc,
                asr=asr,
                reasons=[ReasonCode.ASR_EMPTY_TRANSCRIPT],
            )

        # La chan ngon ngu (D022). Whisper bi ep tieng Anh se "dich" loi tieng
        # Viet thanh chu tieng Anh; cham ban chep do la cham mot bai khong ton
        # tai. Khong cham, khong tu choi: chuyen giang vien nghe lai.
        if asr.is_foreign(self.lid_min_prob):
            return Response(
                **base,
                status=needs_teacher,
                qc=qc,
                asr=asr,
                reasons=[ReasonCode.LANGUAGE_NOT_ENGLISH],
            )

        # Second line of defence: trimming removes the usual cause, but noise in
        # the middle of a recording can trigger the same loop. Cut the loop off
        # and say so, rather than letting it poison every count-based feature
        # and then blaming the speaker for an unusual recording.
        extra_reasons: list[ReasonCode] = []
        finding = detect_repetition(asr.words)
        if finding.detected:
            logger.warning("repetition loop in %s: %s", request.response_id, finding.log_summary())
            asr = asr.cut_at(finding.keep_until_index)
            extra_reasons.append(ReasonCode.ASR_HALLUCINATION)

        # Put the recogniser's timings back on the original recording's clock,
        # so a word at 12.4 s in the report is at 12.4 s in the audio player.
        asr = asr.shifted(offset_s)

        with timed("pipeline_stage_seconds", stage="features"):
            features = self.extractor.extract(asr.words, segments, total_dur_s)
        if is_practice:
            return self._practice(base, task, qc, asr, features, segments, extra_reasons)

        # A recording longer than the model can take is cut into windows that
        # each sit inside the trained range, scored separately, and combined.
        # The alternative -- refusing outright -- was what a student met after
        # speaking for 94 seconds: a full report whose only content was "không
        # chấm được vì bài dài 94 giây".
        windows = plan_windows(total_dur_s, segments)

        try:
            if len(windows) > 1:
                with timed("pipeline_stage_seconds", stage="scoring"):
                    assessment = self._score_windows(asr, segments, windows, features)
            else:
                with timed("pipeline_stage_seconds", stage="scoring"):
                    assessment = self.scorer.score(features)
        except ModelNotFoundError:
            return Response(
                **base,
                status=ResponseStatus.REVIEW_REQUIRED,
                qc=qc,
                asr=asr,
                features=features,
                reasons=[ReasonCode.MODEL_VERSION_MISSING],
            )

        # The model was fitted on features derived from one recogniser. Running a
        # different one shifts `asr_conf_mean` -- the single largest coefficient
        # in the model -- so the score moves for reasons that have nothing to do
        # with the speaker.
        #
        # Measured on this artifact: it was trained on features from Whisper
        # small, and switching to large-v3-turbo shifted mean confidence by
        # +0.0198 (paired t = 4.64, p = 1e-5). That is about +0.07 points on
        # average, and more than 0.25 points -- the entire old boundary margin --
        # on 15% of responses. Invisible unless something checks.
        assessment.reasons += self._version_mismatches(asr) + extra_reasons

        # La chan lac de / doc lai de (D022): giu diem, chi gan co.
        if task is not None:
            assessment.reasons += [ReasonCode(f) for f in validity_flags(asr.text, task)]

        assessment.evidence = self.evidence_builder.build(asr, features, segments)

        # FR-25 and FR-26. The same number the router uses to decide whether a
        # teacher must look at this, so the report cannot claim confidence the
        # routing does not share.
        confidence = features.value_of("asr_conf_mean")
        assessment.comments = self.comment_builder.comments(
            features, assessment.evidence, confidence, assessment.reasons
        )
        # "Dang lam giam X diem" la coef*z cua mo hinh. Khi may da tu choi cham
        # (ngoai phan bo, thieu phep do) thi con so do la ngoai suy ra ngoai mien
        # tin cay -- mot diem bia dung o cho he thong vua noi "khong du can cu".
        contributions = getattr(self.scorer, "contributions", None)
        assessment.priorities = (
            self.comment_builder.priorities(
                contributions(features) if callable(contributions) else {}, confidence
            )
            if assessment.was_scored
            else []
        )

        decision = self.router.route(qc, assessment, features)
        return Response(
            **base,
            status=decision.status,
            qc=qc,
            asr=asr,
            features=features,
            assessment=assessment,
            reasons=decision.reasons,
        )
