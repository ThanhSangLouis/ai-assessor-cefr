"""Bounded, typed contracts for the portal and administration surfaces."""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from aicefr.contracts import ActorRole


class PortalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaskRecord(PortalModel):
    task_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    task_version: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    title: str = Field(min_length=1, max_length=200)
    prompt_text: str = Field(default="", max_length=4000)
    topic_keywords: tuple[str, ...] = Field(default=(), max_length=32)
    min_seconds: float = Field(default=40, ge=1, le=300)
    max_seconds: float = Field(default=60, ge=1, le=300)
    active: bool = True
    revision: int = Field(default=1, ge=1)

    @field_validator("topic_keywords", mode="before")
    @classmethod
    def _topic_keywords(cls, value: object) -> object:
        if isinstance(value, str):
            value = tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("topic_keywords")
    @classmethod
    def _validate_topic_keywords(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip().casefold() for value in values)
        if any(
            not value
            or len(value) > 64
            or any(not char.isalpha() and char not in " '-" for char in value)
            for value in normalized
        ) or len(set(normalized)) != len(normalized):
            raise ValueError("topic_keywords must be unique bounded words or phrases")
        return normalized

    @model_validator(mode="after")
    def duration_order(self) -> TaskRecord:
        if self.min_seconds > self.max_seconds:
            raise ValueError("min_seconds must not exceed max_seconds")
        return self


class AccountCreate(PortalModel):
    actor_id: str = Field(pattern=r"^fixture-[A-Za-z0-9_-]+$", max_length=80)
    role: ActorRole
    password: SecretStr = Field(min_length=8, max_length=256)


class AccountChange(PortalModel):
    disabled: bool | None = None
    unlock: bool = False


class DeleteRequest(PortalModel):
    confirm_id: str = Field(min_length=1, max_length=80)
    expected_revision: int = Field(ge=1)


class ReviewReopen(PortalModel):
    expected_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)


class QCChange(PortalModel):
    changes: dict[str, float] = Field(min_length=1)
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def finite_values(self) -> QCChange:
        if any(not math.isfinite(value) for value in self.changes.values()):
            raise ValueError("QC values must be finite")
        return self


class PageQuery(PortalModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=1_000_000)
    task_id: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=40)
    since: datetime | None = None
    until: datetime | None = None

    @model_validator(mode="after")
    def dates_order(self) -> PageQuery:
        if self.since is not None and self.since.utcoffset() is None:
            raise ValueError("since must include a timezone")
        if self.until is not None and self.until.utcoffset() is None:
            raise ValueError("until must include a timezone")
        if self.since and self.until and self.since > self.until:
            raise ValueError("since must not follow until")
        return self
