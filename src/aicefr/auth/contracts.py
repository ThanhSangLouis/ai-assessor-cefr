"""Typed, credential-safe DTOs for M11 account services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from aicefr.contracts import Actor, ActorRole, ConsentRecord

_UNSET = object()

PROFILE_ICONS = frozenset(
    {
        "book",
        "leaf",
        "star",
        "moon",
        "sun",
        "cloud",
        "wave",
        "mountain",
        "flower",
        "bird",
        "cat",
        "fox",
        "owl",
        "rocket",
        "pencil",
    }
)
PROFILE_COLORS = frozenset(
    {"blue", "teal", "green", "yellow", "orange", "red", "pink", "purple", "indigo", "gray"}
)


@dataclass(frozen=True, slots=True)
class AccountCreate:
    actor_id: str
    role: ActorRole
    goal: int | None = None


@dataclass(frozen=True, slots=True, init=False)
class ProfileUpdate:
    goal: int | None = None
    icon: str | None = None
    color: str | None = None
    provided_fields: frozenset[str] = field(default_factory=frozenset, repr=False, compare=False)

    def __init__(self, goal=_UNSET, icon=_UNSET, color=_UNSET) -> None:
        provided = frozenset(
            name
            for name, value in (("goal", goal), ("icon", icon), ("color", color))
            if value is not _UNSET
        )
        object.__setattr__(self, "goal", None if goal is _UNSET else goal)
        object.__setattr__(self, "icon", None if icon is _UNSET else icon)
        object.__setattr__(self, "color", None if color is _UNSET else color)
        object.__setattr__(self, "provided_fields", provided)


@dataclass(frozen=True, slots=True)
class AccountProfile:
    actor_id: str
    role: ActorRole
    goal: int | None
    icon: str | None
    color: str | None
    temporary_password_required: bool
    revision: int


@dataclass(frozen=True, slots=True)
class AdminAccount:
    actor_id: str
    role: ActorRole
    goal: int | None
    icon: str | None
    color: str | None
    temporary_password_required: bool
    revision: int
    disabled: bool
    locked_until: datetime | None


@dataclass(frozen=True, slots=True)
class PublicSession:
    session_id: str
    actor_id: str
    method: str
    device: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


@dataclass(frozen=True, slots=True)
class ActivityItem:
    kind: str
    object_id: str | None
    recorded_at: datetime
    detail_code: str | None


@dataclass(frozen=True, slots=True)
class CreatedAccount:
    actor: Actor
    temporary_password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ConsentInput:
    consent: ConsentRecord | None
