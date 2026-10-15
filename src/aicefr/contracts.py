"""Hợp đồng dữ liệu dùng chung giữa các module.

Hợp đồng M02/M03/M04/M05/M08: M02 giao PCM float32 mono 16 kHz cùng QC
measurement/reason; M08 bổ sung actor, consent và session. Owner M01/M06/M07
bổ sung kiểu và reason code của module mình vào đây.

Nguyên tắc: thiếu dữ liệu là `None` kèm reason, không bao giờ là 0 hay giá trị
trung bình.
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# M02 xuất 16 kHz mono cho M03/M04; Sang review shared contract còn pending.
EXPECTED_SAMPLE_RATE_HZ = 16_000


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- M08 — Identity and consent ----------------------------------------------


class ActorRole(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class Actor(_Frozen):
    actor_id: str = Field(min_length=1)
    role: ActorRole


class ConsentState(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class ConsentRecord(_Frozen):
    participant_id: str = Field(min_length=1)
    consent_version: str = Field(min_length=1)
    state: ConsentState
    recorded_at: datetime
    research_allowed: bool = False


class SessionRecord(_Frozen):
    token_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    actor_id: str = Field(min_length=1)
    role: ActorRole
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime


class ReasonCode(StrEnum):
    # M01 — Submission and presentation boundary
    EMPTY_AUDIO = "EMPTY_AUDIO"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    UNSUPPORTED_AUDIO_FORMAT = "UNSUPPORTED_AUDIO_FORMAT"
    TASK_NOT_OPEN = "TASK_NOT_OPEN"
    PIPELINE_ENQUEUE_FAILED = "PIPELINE_ENQUEUE_FAILED"
    REPORT_NOT_AVAILABLE = "REPORT_NOT_AVAILABLE"
    # M02 — Audio QC
    QC_EMPTY_AUDIO = "QC_EMPTY_AUDIO"
    QC_INPUT_TOO_LARGE = "QC_INPUT_TOO_LARGE"
    QC_UNSUPPORTED_FORMAT = "QC_UNSUPPORTED_FORMAT"
    QC_FORMAT_MISMATCH = "QC_FORMAT_MISMATCH"
    QC_DECODE_FAILED = "QC_DECODE_FAILED"
    QC_TOO_MANY_CHANNELS = "QC_TOO_MANY_CHANNELS"
    QC_SAMPLE_RATE_LIMIT = "QC_SAMPLE_RATE_LIMIT"
    QC_DURATION_LIMIT = "QC_DURATION_LIMIT"
    QC_TOO_SHORT = "QC_TOO_SHORT"
    QC_SILENCE_REVIEW = "QC_SILENCE_REVIEW"
    QC_SILENCE_REJECT = "QC_SILENCE_REJECT"
    QC_CLIPPING_REVIEW = "QC_CLIPPING_REVIEW"
    QC_CLIPPING_REJECT = "QC_CLIPPING_REJECT"
    QC_MEASUREMENT_MISSING = "QC_MEASUREMENT_MISSING"
    # M03 — ASR
    ASR_FAILED = "ASR_FAILED"
    ASR_EMPTY_TRANSCRIPT = "ASR_EMPTY_TRANSCRIPT"
    ASR_HALLUCINATION = "ASR_HALLUCINATION"
    ASR_VERSION_MISMATCH = "ASR_VERSION_MISMATCH"
    # M04 — Features
    VAD_VERSION_MISMATCH = "VAD_VERSION_MISMATCH"
    FEATURE_NOT_COMPUTABLE = "FEATURE_NOT_COMPUTABLE"
    TOO_FEW_WORDS = "TOO_FEW_WORDS"
    FEATURE_VERSION_MISMATCH = "FEATURE_VERSION_MISMATCH"
    # M05 — Scoring
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
    SCORE_NEAR_BOUNDARY = "SCORE_NEAR_BOUNDARY"
    SCORE_AGGREGATED = "SCORE_AGGREGATED"
    PIPELINE_INTERRUPTED = "PIPELINE_INTERRUPTED"
    MANUAL_REVIEW_REQUESTED = "MANUAL_REVIEW_REQUESTED"
    MODEL_VERSION_MISSING = "MODEL_VERSION_MISSING"
    MODEL_ARTIFACT_INVALID = "MODEL_ARTIFACT_INVALID"
    # M09 — Trust layer
    LANGUAGE_NOT_ENGLISH = "LANGUAGE_NOT_ENGLISH"
    LANGUAGE_UNCERTAIN = "LANGUAGE_UNCERTAIN"
    OFF_TOPIC_SUSPECTED = "OFF_TOPIC_SUSPECTED"
    PROMPT_READING_SUSPECTED = "PROMPT_READING_SUSPECTED"
    CALIBRATION_MISSING = "CALIBRATION_MISSING"
    CALIBRATION_HASH_MISMATCH = "CALIBRATION_HASH_MISMATCH"
    CALIBRATION_INVALID = "CALIBRATION_INVALID"
    LONG_RESPONSE_REVIEW = "LONG_RESPONSE_REVIEW"


# --- M02 → M03/M04 -----------------------------------------------------------


class QCStatus(StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class QCMeasurement(_Frozen):
    """Một phép đo QC; giá trị thiếu phải có reason rõ ràng."""

    name: str = Field(min_length=1)
    value: float | None
    unit: str = Field(min_length=1)
    missing_reason: ReasonCode | None = None

    @model_validator(mode="after")
    def _value_or_reason(self) -> QCMeasurement:
        if self.value is None and self.missing_reason is None:
            raise ValueError("giá trị thiếu cần missing_reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("giá trị đo không được có missing_reason")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("giá trị đo phải hữu hạn")
        return self


class QCResult(_Frozen):
    status: QCStatus
    reasons: tuple[ReasonCode, ...] = ()
    qc_config_version: str = Field(min_length=1)
    measurements: tuple[QCMeasurement, ...] = ()


class DecodedAudio(_Frozen):
    """PCM float32 mono đã giải mã. Không ghi đè bản gốc."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    samples: np.ndarray
    sample_rate_hz: Literal[16_000]
    duration_s: float = Field(ge=0)
    audio_sha256: str

    @field_validator("samples")
    @classmethod
    def _mono_float32(cls, v: np.ndarray) -> np.ndarray:
        if v.ndim != 1:
            raise ValueError("samples phải là mảng 1 chiều (mono)")
        if v.dtype != np.float32:
            raise ValueError("samples phải có dtype float32")
        if not np.isfinite(v).all():
            raise ValueError("samples phải hữu hạn")
        return v


# --- M08 — Stored response and audit -----------------------------------------


class BlobRef(_Frozen):
    blob_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class ResponseStatus(StrEnum):
    """Public lifecycle state of one submitted response.

    ``COMPLETED`` is only shown after M06 has made a report available.  A
    technical failure carries a stable ``ReasonCode`` instead of an invented
    score or a free-form implementation detail.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ResponseRecord(_Frozen):
    response_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    owner_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    task_version: str = Field(min_length=1)
    blob: BlobRef
    status: ResponseStatus = ResponseStatus.QUEUED
    status_reason: ReasonCode | None = None
    revision: int = Field(default=1, ge=1)
    created_at: datetime
    audio_available: bool = True


class AuditEvent(_Frozen):
    event_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    actor_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    recorded_at: datetime
    reason: str | None = None


# --- M03 — ASR ---------------------------------------------------------------


class AsrStatus(StrEnum):
    OK = "OK"
    UNRELIABLE = "UNRELIABLE"
    ASR_FAILED = "ASR_FAILED"
    NOT_RUN = "NOT_RUN"


class Word(_Frozen):
    text: str
    start_s: float
    end_s: float
    prob: float | None = Field(default=None, ge=0.0, le=1.0)


class Transcript(_Frozen):
    response_id: str
    status: AsrStatus
    text: str = ""
    words: tuple[Word, ...] = ()
    asr_model: str | None = None
    engine: str
    engine_version: str
    decode_config_version: str
    audio_sha256: str
    reasons: tuple[ReasonCode, ...] = ()
    test_only: bool = False
    # Independent audio language detection metadata; optional for old reports.
    language: str | None = None
    language_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    language_method: str | None = None
    language_version: str | None = None

    @field_validator("language_probability", mode="before")
    @classmethod
    def _language_probability_not_bool(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("language probability must be numeric, not bool")
        return value


# --- M04 — Features ----------------------------------------------------------


class FeatureValue(_Frozen):
    name: str
    value: float | None
    unit: str
    missing_reason: ReasonCode | None = None


class FeatureSet(_Frozen):
    response_id: str
    values: tuple[FeatureValue, ...]
    feature_version: str
    vad_name: str | None
    vad_version: str | None
    vad_threshold: float | None
    vad_min_silence_ms: int | None
    asr_model: str | None
    transcript_ref: str | None
    audio_sha256: str
    reasons: tuple[ReasonCode, ...] = ()

    def names(self) -> tuple[str, ...]:
        return tuple(v.name for v in self.values)

    def value_of(self, name: str) -> float | None:
        for v in self.values:
            if v.name == name:
                return v.value
        raise KeyError(name)


# --- M05 — Scoring -----------------------------------------------------------


class Criterion(StrEnum):
    RANGE = "range"
    ACCURACY = "accuracy"
    FLUENCY = "fluency"
    COHERENCE = "coherence"
    PHONOLOGY = "phonology"


class Band(StrEnum):
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"


class AssessmentStatus(StrEnum):
    ESTIMATED = "ESTIMATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_EVALUATED = "NOT_EVALUATED"


class CriterionCoverage(_Frozen):
    """Chỉ mang coverage của một tiêu chí; không có điểm hay band riêng."""

    criterion: Criterion
    coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    features: tuple[str, ...] = ()
    reasons: tuple[ReasonCode, ...] = ()


class Interaction(_Frozen):
    """Bài độc thoại không có bằng chứng tương tác."""

    level: None = None
    score_status: str = "insufficient_evidence"


class Provenance(_Frozen):
    model_version: str | None
    model_sha256: str | None
    feature_version: str | None
    band_map_version: str | None
    calibration_version: str | None
    trained_with: dict[str, Any] = Field(default_factory=dict)
    unit_of_inference: str | None
    scored_at: str


class OutOfRangeFeature(_Frozen):
    """Đặc trưng nằm ngoài khoảng chấp nhận của model, để báo lý do cho người học."""

    feature: str
    value: float
    accepted_low: float
    accepted_high: float
    too: str  # "low" | "high"


class Assessment(_Frozen):
    response_id: str
    status: AssessmentStatus
    overall_score: float | None = Field(default=None, ge=1.0, le=6.0)
    overall_band: Band | None = None
    criteria: tuple[CriterionCoverage, ...]
    interaction: Interaction = Interaction()
    reasons: tuple[ReasonCode, ...] = ()
    out_of_range: tuple[OutOfRangeFeature, ...] = ()
    provenance: Provenance
    teacher_verified: bool = False


# --- M07 — Teacher review ----------------------------------------------------


class ReviewState(StrEnum):
    """Trạng thái xử lý của một ca cần giảng viên xem xét."""

    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    OVERRIDDEN = "OVERRIDDEN"
    REJECTED = "REJECTED"


class ReviewAction(StrEnum):
    """Hành động cuối cùng của giảng viên trên một ReviewCandidate."""

    APPROVE = "APPROVE"
    OVERRIDE = "OVERRIDE"
    REJECT = "REJECT"


class ReviewCandidate(_Frozen):
    """Ca được đưa vào hàng đợi từ reason code và kết quả M05.

    ``revision`` là optimistic-lock token: mọi thao tác ghi phải gửi lại giá trị
    mà người dùng đã đọc để tránh hai giảng viên ghi đè im lặng.
    """

    response_id: str = Field(min_length=1)
    response_revision: int = Field(ge=1)
    assessment_status: AssessmentStatus
    proposed_band: Band | None = None
    reasons: tuple[ReasonCode, ...] = Field(min_length=1)
    source_versions: dict[str, str] = Field(default_factory=dict)
    state: ReviewState = ReviewState.PENDING
    revision: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime
    claimed_by: str | None = None

    @field_validator("source_versions")
    @classmethod
    def _source_versions_are_explicit(cls, value: dict[str, str]) -> dict[str, str]:
        if not value or any(not key or not item for key, item in value.items()):
            raise ValueError("source_versions phải có giá trị rõ ràng")
        return value


class ReviewDecision(_Frozen):
    """Quyết định có audit ref thật; không suy ``teacher_verified`` từ score."""

    decision_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    response_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    action: ReviewAction
    old_state: ReviewState
    new_state: ReviewState
    candidate_revision: int = Field(ge=1)
    proposed_band: Band | None = None
    final_band: Band | None = None
    reason: str | None = None
    audit_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    recorded_at: datetime

    @model_validator(mode="after")
    def _action_shape_is_consistent(self) -> ReviewDecision:
        if self.action is ReviewAction.APPROVE:
            if self.new_state is not ReviewState.APPROVED or self.final_band is None:
                raise ValueError("APPROVE cần band cuối và trạng thái APPROVED")
        elif self.action is ReviewAction.OVERRIDE:
            if (
                self.new_state is not ReviewState.OVERRIDDEN
                or self.final_band is None
                or not self.reason
            ):
                raise ValueError("OVERRIDE cần band cuối, reason và trạng thái OVERRIDDEN")
        elif self.action is ReviewAction.REJECT:
            if self.new_state is not ReviewState.REJECTED or self.final_band is not None:
                raise ValueError("REJECT không có band cuối và dùng trạng thái REJECTED")
        return self
