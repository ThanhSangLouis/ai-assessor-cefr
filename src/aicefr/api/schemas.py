"""Data types for the API layer. Kept apart from contracts so that changing the
API does not ripple into the domain logic."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from aicefr.auth.pseudonyms import validate_pseudonym  # noqa: F401 - re-export
from aicefr.contracts import Band


class SubmitResponse(BaseModel):
    response_id: str
    status: str
    message: str


class ReviewDecision(BaseModel):
    """A teacher's decision. The reason is mandatory so the change stays traceable.

    There is deliberately NO reviewer_id field. The reviewer's identity comes
    from the login session, not from data the caller declares about itself.
    Before iteration 2 the client sent this field, so the audit log only
    recorded an arbitrary string and could not prove who changed a score.
    """

    new_score: float | None = Field(default=None, ge=1.0, le=6.0)
    new_band: str | None = None
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("new_band")
    @classmethod
    def band_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in {b.value for b in Band}:
            raise ValueError("band chỉ nhận A1, A2, B1, B2, C1 hoặc C2")
        return v


class LoginRequest(BaseModel):
    """Login payload. The password is never written to the log."""

    pseudonym: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class EraseRequest(BaseModel):
    """Erasure request. The id is sent twice on purpose.

    This deletes audio from disk and cannot be undone, so the second field is
    the only thing between a mistyped id and somebody else's data. FR-35.
    """

    speaker_id: str = Field(min_length=1, max_length=64)
    confirm_speaker_id: str = Field(min_length=1, max_length=64)


class QueueItem(BaseModel):
    response_id: str
    speaker_id: str
    task_id: str
    status: str
    overall_0_6: float | None
    overall_band: str | None
    teacher_verified: bool
    created_at: str
    locked_by: str | None = None
    # D023. 'practice' for a practice attempt; the "my responses" screen then
    # links to the practice result page instead of the scored report.
    purpose: str = "assessment"
    # D028. Time of the latest teacher decision, on the owner's own list only.
    reviewed_at: str | None = None


class ReviewClose(BaseModel):
    """Dong mot bai may khong cham duoc. Ly do bat buoc, nhu moi quyet dinh duyet."""

    reason: str = Field(min_length=5, max_length=1000)
