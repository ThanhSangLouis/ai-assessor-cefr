"""Connect M01/M02 through M07 using injected, typed domain services."""

from __future__ import annotations

import io
import logging
import math
from collections.abc import Callable
from datetime import UTC, datetime

import soundfile as sf

from aicefr.audio.config import AudioFormat, QCConfig
from aicefr.audio.pipeline import AsrPort, process_audio
from aicefr.contracts import (
    AsrStatus,
    Assessment,
    AssessmentStatus,
    Criterion,
    CriterionCoverage,
    FeatureSet,
    Interaction,
    Provenance,
    QCStatus,
    ReasonCode,
    ResponseRecord,
    ResponseStatus,
    ReviewCandidate,
    ReviewState,
    Transcript,
)
from aicefr.features.extractor import FeatureExtractor
from aicefr.report.contracts import (
    CommentRequest,
    CommentTemplate,
    EvidenceRef,
    EvidenceSource,
)
from aicefr.report.service import ReportInput, ReportService
from aicefr.review.routing import review_candidate_from_assessment
from aicefr.review.service import ReviewService
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.jobs import LeaseLost
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import ConcurrentResponseUpdate

log = logging.getLogger(__name__)


class PipelineCoordinator:
    def __init__(
        self,
        *,
        responses: ResponseService,
        reports: ReportService,
        reviews: ReviewService,
        qc_config: QCConfig,
        asr: AsrPort,
        extractor: FeatureExtractor,
        scorer: RidgeScorer,
        long_response_windows: bool = False,
    ) -> None:
        self._responses = responses
        self._reports = reports
        self._reviews = reviews
        self._qc_config = qc_config
        self._asr = asr
        self._extractor = extractor
        self._scorer = scorer
        self._long_response_windows = long_response_windows
        self._commit_guard: Callable[[str, int], None] | None = None

    def set_commit_guard(self, guard: Callable[[str, int], None] | None) -> None:
        """Install a durable-worker fence, called inside each response write transaction."""
        self._commit_guard = guard

    def enqueue(self, response: ResponseRecord) -> None:
        if response.status is not ResponseStatus.QUEUED:
            return
        try:
            with self._responses.metadata.transaction():
                self._guard(response.response_id, response.revision)
                current = self._responses.metadata.claim_queued_response(response)
        except ConcurrentResponseUpdate:
            # Another worker or an earlier call already claimed this revision.
            return
        except LeaseLost:
            return

        failure_reason = ReasonCode.PIPELINE_ENQUEUE_FAILED
        try:
            data = self._responses.blobs.read(response.blob)
            extension = self._container_extension(data)
            result = process_audio(
                response_id=response.response_id,
                data=data,
                declared_extension=extension,
                config=self._qc_config,
                asr=self._asr,
            )
            if result.qc.status is QCStatus.REJECT:
                reason = result.qc.reasons[0] if result.qc.reasons else ReasonCode.QC_DECODE_FAILED
                self._transition(
                    response, current, ResponseStatus.REJECTED, "pipeline_rejected", reason
                )
                return
            if result.qc.status is QCStatus.REVIEW:
                qc_reasons = result.qc.reasons or (ReasonCode.QC_MEASUREMENT_MISSING,)
                assessment = self._not_evaluated(response.response_id, qc_reasons)
                self._persist_final(
                    response,
                    current,
                    assessment,
                    ReportInput(
                        response_id=response.response_id,
                        audio_duration_s=result.audio.duration_s if result.audio else 0.0,
                        assessment=assessment,
                        source_versions={"qc_config": self._qc_config.version},
                    ),
                    ResponseStatus.REVIEW_REQUIRED,
                    "pipeline_review_required",
                    qc_reasons[0],
                    qc_candidate=True,
                )
                return

            transcript = result.transcript
            if transcript is None:
                raise RuntimeError("ASR result missing")
            features = self._extractor.extract(transcript, result.audio)
            assessment = self._scorer.score(features, transcript)
            window_versions = {}
            artifact = getattr(self._scorer, "artifact", None)
            if (
                self._long_response_windows
                and transcript.status is AsrStatus.OK
                and artifact is not None
                and "total_dur" in artifact.feature_order
                and result.audio.duration_s
                > artifact.feature_hi[artifact.feature_order.index("total_dur")]
            ):
                from aicefr.scoring.windows import score_windows

                assessment, window_versions = score_windows(
                    result.audio, transcript, self._extractor, self._scorer
                )
            if transcript.status is not AsrStatus.OK:
                reasons = tuple(dict.fromkeys((*transcript.reasons, *assessment.reasons)))
                assessment = assessment.model_copy(
                    update={
                        "status": AssessmentStatus.NOT_EVALUATED,
                        "overall_score": None,
                        "overall_band": None,
                        "reasons": reasons or (ReasonCode.ASR_FAILED,),
                        "teacher_verified": False,
                    }
                )
            needs_review = assessment.status is not AssessmentStatus.ESTIMATED
            final_reason = (
                transcript.reasons[0]
                if transcript.status is not AsrStatus.OK and transcript.reasons
                else self._assessment_reason(assessment)
            )
            report_input = self._report_input(
                response.response_id, result.audio.duration_s, assessment, transcript, features
            )
            if window_versions:
                report_input = report_input.model_copy(
                    update={"source_versions": report_input.source_versions | window_versions}
                )
            self._persist_final(
                response,
                current,
                assessment,
                report_input,
                ResponseStatus.REVIEW_REQUIRED if needs_review else ResponseStatus.COMPLETED,
                "pipeline_review_required" if needs_review else "pipeline_completed",
                final_reason,
                qc_candidate=False,
            )
        except LeaseLost:
            # Expired or replaced work must never alter the response owned by its successor.
            return
        except Exception:
            log.error("pipeline failed response_id=%s", response.response_id)
            if self._commit_guard is not None:
                # Durable workers own retry policy and terminal failure. Check the fence before
                # propagating so stale work cannot cause a retry/failure against a successor.
                try:
                    self._guard(response.response_id, current.revision)
                except LeaseLost:
                    return
                raise
            # Report/status/candidate writes above share one transaction. If that
            # work failed, the row is still at current.revision and can be marked
            # FAILED with the actual pipeline boundary reason.
            try:
                self._mark_failed(response, current.revision, failure_reason)
            except ConcurrentResponseUpdate:
                # A newer revision belongs to another operation. Never follow it and
                # mutate a response that this invocation did not claim.
                return

    def _mark_failed(
        self, response: ResponseRecord, expected_revision: int, reason: ReasonCode
    ) -> ResponseRecord:
        with self._responses.metadata.transaction():
            self._guard(response.response_id, expected_revision)
            return self._responses.transition_status(
                response_id=response.response_id,
                expected_revision=expected_revision,
                status=ResponseStatus.FAILED,
                actor_id="system-pipeline",
                action="pipeline_failed",
                reason=reason,
            )

    def _persist_final(
        self,
        response: ResponseRecord,
        current: ResponseRecord,
        assessment: Assessment,
        report_input: ReportInput,
        status: ResponseStatus,
        action: str,
        reason: ReasonCode | None,
        *,
        qc_candidate: bool,
    ) -> None:
        with self._responses.metadata.transaction():
            self._guard(response.response_id, current.revision)
            self._reports.build_and_store(report_input)
            final = self._transition(response, current, status, action, reason)
            if status is ResponseStatus.REVIEW_REQUIRED:
                candidate = (
                    self._qc_candidate(assessment, final.revision, self._qc_config.version)
                    if qc_candidate
                    else review_candidate_from_assessment(
                        assessment, response_revision=final.revision
                    )
                )
                self._reviews.add_candidate(candidate)

    def _transition(
        self,
        response: ResponseRecord,
        current: ResponseRecord,
        status: ResponseStatus,
        action: str,
        reason: ReasonCode | None,
    ) -> ResponseRecord:
        with self._responses.metadata.transaction():
            self._guard(response.response_id, current.revision)
            return self._responses.transition_status(
                response_id=response.response_id,
                expected_revision=current.revision,
                status=status,
                actor_id="system-pipeline",
                action=action,
                reason=reason,
            )

    def _guard(self, response_id: str, expected_revision: int) -> None:
        if self._commit_guard is not None:
            self._commit_guard(response_id, expected_revision)

    @staticmethod
    def _qc_candidate(assessment: Assessment, revision: int, qc_version: str) -> ReviewCandidate:
        now = datetime.now(UTC)
        return ReviewCandidate(
            response_id=assessment.response_id,
            response_revision=revision,
            assessment_status=assessment.status,
            proposed_band=None,
            reasons=assessment.reasons or (ReasonCode.QC_MEASUREMENT_MISSING,),
            source_versions={"qc": qc_version},
            state=ReviewState.PENDING,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _assessment_reason(assessment: Assessment) -> ReasonCode | None:
        return assessment.reasons[0] if assessment.reasons else None

    def _report_input(
        self,
        response_id: str,
        duration_s: float,
        assessment: Assessment,
        transcript: Transcript,
        features: FeatureSet,
    ) -> ReportInput:
        refs: list[EvidenceRef] = []
        requests: list[CommentRequest] = []
        if transcript.status is AsrStatus.OK and not transcript.test_only:
            for index, word in enumerate(transcript.words):
                if not (
                    math.isfinite(word.start_s)
                    and math.isfinite(word.end_s)
                    and 0 <= word.start_s <= word.end_s <= duration_s
                ):
                    continue
                evidence_id = f"word:{index}"
                refs.append(
                    EvidenceRef(
                        evidence_id=evidence_id,
                        response_id=response_id,
                        source=EvidenceSource.TRANSCRIPT,
                        source_version=transcript.decode_config_version,
                        criterion=Criterion.FLUENCY,
                        start_s=word.start_s,
                        end_s=word.end_s,
                        word_index=index,
                    )
                )
                requests.append(
                    CommentRequest(
                        criterion=Criterion.FLUENCY,
                        template=CommentTemplate.WORD_TIMING_OBSERVED,
                        evidence_id=evidence_id,
                    )
                )
            feature_criteria = {
                name: row.criterion for row in assessment.criteria for name in row.features
            }
            for value in features.values:
                criterion = feature_criteria.get(value.name)
                if criterion is None or value.value is None or not math.isfinite(value.value):
                    continue
                evidence_id = f"feature:{value.name}:{value.value.hex()}"
                refs.append(
                    EvidenceRef(
                        evidence_id=evidence_id,
                        response_id=response_id,
                        source=EvidenceSource.FEATURE_SET,
                        source_version=features.feature_version,
                        criterion=criterion,
                    )
                )
                requests.append(
                    CommentRequest(
                        criterion=criterion,
                        template=CommentTemplate.FEATURE_VALUE_AVAILABLE,
                        evidence_id=evidence_id,
                    )
                )
        return ReportInput(
            response_id=response_id,
            audio_duration_s=duration_s,
            assessment=assessment,
            transcript=transcript,
            features=features,
            evidence_refs=tuple(refs),
            comment_requests=tuple(requests),
            source_versions={"qc_config": self._qc_config.version},
        )

    @staticmethod
    def _container_extension(data: bytes) -> str:
        from aicefr.audio.recordings import recording_format

        recording = recording_format(data)
        if recording is not None:
            return recording
        try:
            with sf.SoundFile(io.BytesIO(data)) as handle:
                fmt, subtype = handle.format.upper(), handle.subtype.upper()
        except Exception:
            return "unsupported"
        if fmt == "WAV" and subtype.startswith("PCM_"):
            return AudioFormat.WAV_PCM.value
        if fmt == "FLAC" and subtype.startswith("PCM_"):
            return AudioFormat.FLAC.value
        if fmt == "OGG" and subtype == "VORBIS":
            return AudioFormat.OGG_VORBIS.value
        if fmt == "MPEG_LAYER_III" or subtype == "MPEG_LAYER_III":
            return AudioFormat.MP3.value
        return "unsupported"

    @staticmethod
    def _not_evaluated(response_id: str, reasons: tuple[ReasonCode, ...]) -> Assessment:
        safe_reasons = reasons or (ReasonCode.QC_MEASUREMENT_MISSING,)
        return Assessment(
            response_id=response_id,
            status=AssessmentStatus.NOT_EVALUATED,
            criteria=tuple(
                CriterionCoverage(criterion=item, reasons=safe_reasons) for item in Criterion
            ),
            interaction=Interaction(),
            reasons=safe_reasons,
            provenance=Provenance(
                model_version=None,
                model_sha256=None,
                feature_version=None,
                band_map_version=None,
                calibration_version=None,
                trained_with={},
                unit_of_inference=None,
                scored_at=datetime.now(UTC).isoformat(),
            ),
        )
