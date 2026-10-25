"""Authentication and consent services for explicit synthetic fixture accounts."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from aicefr.auth.errors import AuthorizationError, LockoutError, ResourceNotFound
from aicefr.contracts import Actor, ActorRole, ConsentRecord, ConsentState, SessionRecord

IDLE_TTL = timedelta(minutes=30)
ABSOLUTE_TTL = timedelta(hours=8)


@dataclass(frozen=True)
class AccountRecord:
    actor: Actor
    password_hash: str = field(repr=False)
    disabled: bool = False
    failed_attempts: int = 0
    locked_until: datetime | None = None


class AccountRepository(Protocol):
    def get_account(self, actor_id: str) -> AccountRecord | None: ...
    def add_account(self, account: AccountRecord) -> None: ...
    def record_login(self, actor_id: str, *, success: bool, now: datetime) -> None: ...


class SessionRepository(Protocol):
    def get_session(self, digest: str) -> SessionRecord | None: ...
    def put_session(self, session: SessionRecord) -> None: ...
    def touch_session(self, session: SessionRecord, *, now: datetime) -> bool: ...
    def delete_session(self, digest: str) -> None: ...


class ConsentRepository(Protocol):
    def get_consent(self, participant_id: str) -> ConsentRecord | None: ...
    def put_consent(self, consent: ConsentRecord) -> None: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def authorize_owner(actor: Actor, owner_id: str | None) -> None:
    """Fail identically for missing and foreign-owned records."""
    if owner_id is None or actor.actor_id != owner_id:
        raise ResourceNotFound("resource unavailable")


class AuthService:
    def __init__(
        self,
        accounts: AccountRepository,
        sessions: SessionRepository,
        *,
        clock: Callable[[], datetime] = utc_now,
        identity_repository: object | None = None,
    ) -> None:
        self._accounts = accounts
        self._sessions = sessions
        self._clock = clock
        self.identity_repository = identity_repository
        self._hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19456,
            parallelism=1,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(24))

    def bootstrap_fixture_account(self, actor_id: str, role: ActorRole, password: str) -> Actor:
        """Provision a synthetic account explicitly; no public signup or role claim."""
        if (
            not actor_id.startswith("fixture-")
            or len(actor_id) > 80
            or any(not (c.isalnum() or c in "-_") for c in actor_id)
            or not password
        ):
            raise ValueError("fixture account required")
        actor = Actor(actor_id=actor_id, role=role)
        self._accounts.add_account(AccountRecord(actor, self._hasher.hash(password)))
        return actor

    def login(self, actor_id: str, password: str, *, device: str = "unknown") -> str:
        account = self._accounts.get_account(actor_id)
        now = self._clock()
        try:
            valid = self._hasher.verify(
                account.password_hash if account is not None else self._dummy_hash, password
            )
        except (InvalidHashError, VerificationError):
            valid = False
        if account is None:
            raise AuthorizationError("invalid credentials")
        if account.disabled:
            self._record_activity(actor_id, "login_failed", now)
            raise AuthorizationError("invalid credentials")
        if account.locked_until is not None and now < account.locked_until:
            self._record_activity(actor_id, "login_failed", now, "locked")
            raise LockoutError(max(1, int((account.locked_until - now).total_seconds())))
        if (
            valid
            and self.identity_repository is not None
            and self.identity_repository.temporary_password_expired(actor_id, now)
        ):
            self._record_activity(actor_id, "login_failed", now, "temporary_password_expired")
            raise AuthorizationError("temporary_password_expired")
        self._accounts.record_login(actor_id, success=valid, now=now)
        self._record_activity(actor_id, "login_succeeded" if valid else "login_failed", now)
        if not valid:
            refreshed = self._accounts.get_account(actor_id)
            if refreshed and refreshed.locked_until and now < refreshed.locked_until:
                raise LockoutError(max(1, int((refreshed.locked_until - now).total_seconds())))
            raise AuthorizationError("invalid credentials")
        return self._issue(account.actor, "password", device=device)

    def logout(self, token: str) -> None:
        """Revoke one opaque session token without retaining the raw token."""
        try:
            digest = _digest(token)
        except UnicodeEncodeError:
            return
        session = self._sessions.get_session(digest)
        self._sessions.delete_session(digest)
        if session is not None:
            now = self._clock()
            self._record_activity(session.actor_id, "logout", now)
            if self.identity_repository is not None:
                self.identity_repository.audit(session.actor_id, "logout", session.actor_id, now)

    def resolve(
        self,
        token: str,
        *,
        allowed_roles: frozenset[ActorRole] | None = None,
        allow_temporary: bool = False,
    ) -> Actor:
        try:
            session = self._sessions.get_session(_digest(token))
        except UnicodeEncodeError:
            session = None
        now = self._clock()
        if session is None or now >= session.idle_expires_at or now >= session.absolute_expires_at:
            raise AuthorizationError("session unavailable")
        account = self._accounts.get_account(session.actor_id)
        if account is None or account.disabled or account.actor.role != session.role:
            raise AuthorizationError("session unavailable")
        if (
            not allow_temporary
            and self.identity_repository is not None
            and self.identity_repository.has_temporary_password(session.actor_id, now=now)
        ):
            raise AuthorizationError("password_change_required")
        if allowed_roles is not None and session.role not in allowed_roles:
            raise AuthorizationError("access denied")
        actor = Actor(actor_id=session.actor_id, role=session.role)
        if not self._sessions.touch_session(session, now=now):
            raise AuthorizationError("session unavailable")
        return actor

    def issue_session(self, actor_id: str, method: str = "google") -> str:
        account = self._accounts.get_account(actor_id)
        if account is None or account.disabled:
            raise AuthorizationError("account unavailable")
        now = self._clock()
        if account.locked_until is not None and now < account.locked_until:
            raise LockoutError(max(1, int((account.locked_until - now).total_seconds())))
        if (
            self.identity_repository is not None
            and self.identity_repository.temporary_password_expired(actor_id, now)
        ):
            raise AuthorizationError("temporary_password_expired")
        if self.identity_repository is not None and self.identity_repository.has_temporary_password(
            actor_id, now=now
        ):
            raise AuthorizationError("password_change_required")
        return self._issue(account.actor, method)

    def _issue(self, actor: Actor, method: str, *, device: str = "unknown") -> str:
        now = self._clock()
        if not isinstance(device, str) or device not in {"desktop", "mobile", "tablet", "unknown"}:
            device = "unknown"
        token = secrets.token_urlsafe(32)
        session = SessionRecord(
            token_digest=_digest(token),
            actor_id=actor.actor_id,
            role=actor.role,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + IDLE_TTL,
            absolute_expires_at=now + ABSOLUTE_TTL,
        )
        self._sessions.put_session(session)
        if self.identity_repository is not None:
            self.identity_repository.set_session_metadata(
                session.token_digest, method, device, session.absolute_expires_at, now
            )
            self._record_activity(actor.actor_id, "session_created", now, method)
            self.identity_repository.audit(
                actor.actor_id, "session_created", actor.actor_id, now, method
            )
        return token

    def _record_activity(
        self, actor_id: str, kind: str, now: datetime, detail: str | None = None
    ) -> None:
        if self.identity_repository is not None:
            self.identity_repository.record_activity(actor_id, kind, actor_id, now, detail)


class ConsentService:
    def __init__(
        self, consents: ConsentRepository, *, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self._consents = consents
        self._clock = clock

    def activate(
        self,
        actor: Actor,
        consent_version: str,
        *,
        research_allowed: bool = False,
        audio_storage_allowed: bool = False,
    ) -> ConsentRecord:
        if actor.role != ActorRole.STUDENT:
            raise AuthorizationError("access denied")
        identity = self._identity_repository()
        if identity is not None:
            return identity.set_consent(
                actor,
                consent_version,
                research_allowed,
                True,
                self._clock(),
                audio_storage_allowed=audio_storage_allowed,
            )
        record = ConsentRecord(
            participant_id=actor.actor_id,
            consent_version=consent_version,
            state=ConsentState.ACTIVE,
            recorded_at=self._clock(),
            research_allowed=research_allowed,
            audio_storage_allowed=audio_storage_allowed,
        )
        self._consents.put_consent(record)
        return record

    def current(self, actor: Actor) -> ConsentRecord | None:
        if actor.role != ActorRole.STUDENT:
            raise AuthorizationError("access denied")
        identity = self._identity_repository()
        return (
            identity.consent(actor.actor_id)
            if identity is not None
            else self._consents.get_consent(actor.actor_id)
        )

    def withdraw(self, actor: Actor) -> ConsentRecord:
        identity = self._identity_repository()
        current = (
            identity.consent(actor.actor_id)
            if identity is not None
            else self._consents.get_consent(actor.actor_id)
        )
        if actor.role != ActorRole.STUDENT or current is None:
            raise AuthorizationError("consent unavailable")
        if identity is not None:
            return identity.set_consent(
                actor,
                current.consent_version,
                False,
                False,
                self._clock(),
                audio_storage_allowed=False,
            )
        record = current.model_copy(
            update={
                "state": ConsentState.WITHDRAWN,
                "recorded_at": self._clock(),
                "research_allowed": False,
                "audio_storage_allowed": False,
            }
        )
        self._consents.put_consent(record)
        return record

    def _identity_repository(self):
        if hasattr(self._consents, "set_consent") and hasattr(self._consents, "consent"):
            return self._consents
        if hasattr(self._consents, "connection"):
            from aicefr.storage.identity import IdentityRepository

            identity = IdentityRepository(self._consents)
            self._consents = identity
            return identity
        return None

    def require_active(self, actor: Actor, consent_version: str) -> ConsentRecord:
        current = self._consents.get_consent(actor.actor_id)
        if (
            actor.role != ActorRole.STUDENT
            or current is None
            or current.state != ConsentState.ACTIVE
            or current.consent_version != consent_version
        ):
            raise AuthorizationError("active consent required")
        return current

    def require_audio_storage(self, actor: Actor, consent_version: str) -> ConsentRecord:
        current = self.require_active(actor, consent_version)
        if not current.audio_storage_allowed:
            raise AuthorizationError("audio storage consent required")
        return current
