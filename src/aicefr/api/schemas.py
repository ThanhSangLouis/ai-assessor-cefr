"""Data types for the API layer. Kept apart from contracts so that changing the
API does not ripple into the domain logic."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, Field, field_validator

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


# D071: people sign in with their email.
SIGN_IN_NAME = AliasChoices("email", "identifier")


class LoginRequest(BaseModel):
    """Login payload. The password is never written to the log."""

    identifier: str = Field(min_length=1, max_length=254, validation_alias=SIGN_IN_NAME)
    password: str = Field(min_length=1, max_length=256)


class SignupRequest(BaseModel):
    """Self sign-up (D065, D071): the email to sign in with, the full name a
    teacher reads, a password."""

    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class EraseRequest(BaseModel):
    """Erasure request. The email is sent twice on purpose.

    This deletes audio from disk and cannot be undone, so the second field is
    the only thing between a mistyped email and somebody else's data. FR-35.
    """

    email: str = Field(min_length=3, max_length=254)
    confirm_email: str = Field(min_length=3, max_length=254)


class QueueItem(BaseModel):
    response_id: str
    account_id: str | None
    task_id: str
    status: str
    overall_0_6: float | None
    overall_band: str | None
    teacher_verified: bool
    created_at: str
    locked_by: str | None = None
    # D071. The student's full name, on a teacher's queue.
    student_name: str | None = None
    # How long the recording is, in seconds: the week view draws each waiting
    # response as tall as it is long. None before audio checks ran.
    duration_s: float | None = None


class ReviewClose(BaseModel):
    """Dong mot bai may khong cham duoc. Ly do bat buoc, nhu moi quyet dinh duyet."""

    reason: str = Field(min_length=5, max_length=1000)
