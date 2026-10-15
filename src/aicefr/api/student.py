"""Thin, typed student boundary for M01.

This module deliberately receives the authenticated session token rather than an
owner ID from the caller.  The owner is always resolved by M08's AuthService.
"""

from __future__ import annotations

from pathlib import PurePath
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aicefr.auth.service import AuthService
from aicefr.contracts import (
    Actor,
    ActorRole,
    ReasonCode,
    ResponseRecord,
    ResponseStatus,
)
from aicefr.trust.contracts import TrustAssessment, TrustDisposition


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# Compatibility name for the public M01 boundary.  The lifecycle itself is a
# shared M08/M01 contract so the storage record and UI cannot drift.
StudentResponseStatus = ResponseStatus


class UploadPolicy(_Frozen):
    """Explicit upload constraints supplied by the application configuration."""

    allowed_media_types: frozenset[str] = Field(min_length=1)
    max_bytes: int = Field(gt=0)

    @field_validator("allowed_media_types")
    @classmethod
    def _normalise_types(cls, values: frozenset[str]) -> frozenset[str]:
        normalised = frozenset(value.lower().strip() for value in values)
        if not normalised or any(not value.startswith("audio/") for value in normalised):
            raise ValueError("allowed_media_types must contain audio media types")
        return normalised


class SubmitRequest(_Frozen):
    task_id: str = Field(min_length=1)
    task_version: str = Field(min_length=1)
    consent_version: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    audio_bytes: bytes

    @field_validator("filename")
    @classmethod
    def _leaf_filename(cls, value: str) -> str:
        if "/" in value or "\\" in value or PurePath(value).name != value:
            raise ValueError("filename must not contain a path")
        return value

    @field_validator("content_type")
    @classmethod
    def _normalise_content_type(cls, value: str) -> str:
        return value.lower().split(";", maxsplit=1)[0].strip()


class SubmissionError(ValueError):
    """A controlled client-facing upload denial with a stable reason code."""

    def __init__(self, code: ReasonCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class PipelineStarter(Protocol):
    def enqueue(self, response: ResponseRecord) -> None: ...


class TaskAccess(Protocol):
    """M01 task availability boundary; task state is never client asserted."""

    def require_open(self, task_id: str, task_version: str) -> None: ...


class AllowlistedTaskAccess:
    """Small configuration-backed task gate for the current vertical slice."""

    def __init__(self, open_tasks: frozenset[tuple[str, str]]) -> None:
        if not open_tasks or any(not task_id or not version for task_id, version in open_tasks):
            raise ValueError("open_tasks must contain explicit task/version pairs")
        self._open_tasks = open_tasks

    def require_open(self, task_id: str, task_version: str) -> None:
        if (task_id, task_version) not in self._open_tasks:
            raise SubmissionError(ReasonCode.TASK_NOT_OPEN, "Task is not open for submission")


class ResponsePort(Protocol):
    """M08 response boundary used by M01, kept independent of a storage backend."""

    def submit(
        self,
        actor: Actor,
        *,
        task_id: str,
        task_version: str,
        consent_version: str,
        audio_bytes: bytes,
        initial_status: ResponseStatus = ResponseStatus.QUEUED,
    ) -> ResponseRecord: ...

    def get_response(self, actor: Actor, response_id: str) -> ResponseRecord: ...

    def transition_status(
        self,
        *,
        response_id: str,
        expected_revision: int,
        status: ResponseStatus,
        actor_id: str,
        action: str,
        reason: ReasonCode | None = None,
    ) -> ResponseRecord: ...


class ReportLookup(Protocol):
    def get(self, response_id: str) -> object | None: ...


class StudentStatus(_Frozen):
    response_id: str
    status: StudentResponseStatus
    revision: int = Field(ge=1)
    report_available: bool
    reason: ReasonCode | None = None


class StudentTrustSummary(_Frozen):
    """Small recovery-focused Trust view for the response owner."""

    disposition: TrustDisposition
    reasons: tuple[ReasonCode, ...]
    recovery: str | None = None


class StudentReportView(_Frozen):
    status: StudentStatus
    report: object | None = None
    trust: StudentTrustSummary | None = None


class StudentService:
    """M01 submit/status/report use cases over typed M08 and M06 ports."""

    def __init__(
        self,
        auth: AuthService,
        responses: ResponsePort,
        reports: ReportLookup,
        policy: UploadPolicy,
        task_access: TaskAccess,
        pipeline: PipelineStarter | None = None,
    ) -> None:
        self._auth = auth
        self._responses = responses
        self._reports = reports
        self._policy = policy
        self._task_access = task_access
        self._pipeline = pipeline

    def submit(self, session_token: str, request: SubmitRequest) -> StudentStatus:
        actor = self._auth.resolve(session_token, allowed_roles=frozenset({ActorRole.STUDENT}))
        self._task_access.require_open(request.task_id, request.task_version)
        self._validate_upload(request)
        response = self._responses.submit(
            actor,
            task_id=request.task_id,
            task_version=request.task_version,
            consent_version=request.consent_version,
            audio_bytes=request.audio_bytes,
            initial_status=StudentResponseStatus.QUEUED,
        )
        if self._pipeline is not None:
            try:
                self._pipeline.enqueue(response)
            except Exception:
                response = self._responses.transition_status(
                    response_id=response.response_id,
                    expected_revision=response.revision,
                    status=StudentResponseStatus.FAILED,
                    actor_id="system-pipeline",
                    action="pipeline_enqueue_failed",
                    reason=ReasonCode.PIPELINE_ENQUEUE_FAILED,
                )
            else:
                # Synchronous local pipelines can finish during enqueue.
                persisted = self._responses.get_response(actor, response.response_id)
                if persisted.revision >= response.revision:
                    response = persisted
        return self._status(response)

    def status(self, session_token: str, response_id: str) -> StudentStatus:
        actor = self._auth.resolve(session_token, allowed_roles=frozenset({ActorRole.STUDENT}))
        return self._status(self._responses.get_response(actor, response_id))

    def report(self, session_token: str, response_id: str) -> StudentReportView:
        actor = self._auth.resolve(session_token, allowed_roles=frozenset({ActorRole.STUDENT}))
        response = self._responses.get_response(actor, response_id)
        report = self._reports.get(response_id)
        trust = (
            student_trust_summary(report.trust)
            if report is not None and hasattr(report, "trust") and report.trust is not None
            else None
        )
        return StudentReportView(
            status=self._status(response, report is not None), report=report, trust=trust
        )

    def _validate_upload(self, request: SubmitRequest) -> None:
        if request.content_type not in self._policy.allowed_media_types:
            raise SubmissionError(
                ReasonCode.UNSUPPORTED_AUDIO_FORMAT,
                "Audio format is not accepted",
            )
        if len(request.audio_bytes) > self._policy.max_bytes:
            raise SubmissionError(
                ReasonCode.AUDIO_TOO_LARGE,
                "Audio file exceeds the configured limit",
            )
        if not request.audio_bytes:
            raise SubmissionError(ReasonCode.EMPTY_AUDIO, "Audio file is empty")

    def _status(
        self, response: ResponseRecord, report_available: bool | None = None
    ) -> StudentStatus:
        status = response.status
        if report_available is None:
            report_available = self._reports.get(response.response_id) is not None
        reason = response.status_reason
        if not report_available and status is StudentResponseStatus.COMPLETED:
            # A pipeline may persist its last technical step before the M06
            # report transaction is visible.  Never expose that gap as a
            # completed assessment or synthesize a score for the student.
            status = StudentResponseStatus.RUNNING
            reason = ReasonCode.REPORT_NOT_AVAILABLE
        return StudentStatus(
            response_id=response.response_id,
            status=status,
            revision=response.revision,
            report_available=report_available,
            reason=reason,
        )


class StudentApi:
    """Named API adapter, kept framework-independent for the current Python stack."""

    def __init__(self, service: StudentService) -> None:
        self._service = service

    def submit(self, session_token: str, request: SubmitRequest) -> StudentStatus:
        return self._service.submit(session_token, request)

    def get_status(self, session_token: str, response_id: str) -> StudentStatus:
        return self._service.status(session_token, response_id)

    def get_report(self, session_token: str, response_id: str) -> StudentReportView:
        return self._service.report(session_token, response_id)


def student_trust_summary(trust: TrustAssessment) -> StudentTrustSummary:
    values = {reason.value for reason in trust.reasons}
    recovery = None
    if values & {"CALIBRATION_MISSING", "CALIBRATION_INVALID", "CALIBRATION_HASH_MISMATCH"}:
        recovery = "Kết quả đang chờ kiểm tra; hãy xem lại sau hoặc hỏi giảng viên."
    elif "LANGUAGE_NOT_ENGLISH" in values:
        recovery = "Hãy ghi lại câu trả lời bằng tiếng Anh."
    elif "LANGUAGE_UNCERTAIN" in values:
        recovery = "Hãy ghi lại câu trả lời rõ tiếng Anh hơn."
    elif values & {"OFF_TOPIC_SUSPECTED", "PROMPT_READING_SUSPECTED", "SCORE_NEAR_BOUNDARY"}:
        recovery = "Giảng viên cần xem lại kết quả trước khi sử dụng."
    return StudentTrustSummary(
        disposition=trust.disposition,
        reasons=trust.reasons,
        recovery=recovery,
    )
