"""Authenticated account, session, activity and consent use cases."""

from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Any

from argon2.exceptions import InvalidHashError, VerificationError

from aicefr.auth.contracts import AccountCreate, CreatedAccount, ProfileUpdate
from aicefr.auth.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from aicefr.auth.service import AuthService, _digest
from aicefr.contracts import Actor, ActorRole


class AccountService:
    def __init__(self, auth: AuthService, repository: Any) -> None:
        self.auth = auth
        self.repository = repository
        # Optional organization seat policy injected by the local composition root.
        # The repository invokes it inside the same transaction as account inserts.
        self.student_seat_check = None
        if self.auth.identity_repository is None:
            self.auth.identity_repository = repository

    def get_profile(self, token: str):
        actor = self.auth.resolve(token, allow_temporary=True)
        profile = self.repository.get_profile(actor.actor_id)
        if profile is None:
            raise NotFoundError("account_not_found")
        return profile

    def update_profile(self, token: str, update: ProfileUpdate | None = None, **fields: Any):
        actor = self.auth.resolve(token)
        if update is not None:
            if fields or not isinstance(update, ProfileUpdate):
                raise ValidationError("invalid_profile_fields")
            fields = {key: getattr(update, key) for key in update.provided_fields}
        return self.repository.update_profile(actor.actor_id, fields, self._now())

    def change_password(self, token: str, current_password: str, new_password: str) -> str:
        actor = self.auth.resolve(token, allow_temporary=True)
        self._validate_password(new_password)
        if new_password.casefold() == actor.actor_id.casefold():
            raise ValidationError("password_reuse")
        account = self.auth._accounts.get_account(actor.actor_id)
        if account is None or not self._verify(account.password_hash, current_password):
            raise AuthorizationError("invalid_credentials")
        if self._verify(account.password_hash, new_password):
            raise ValidationError("password_reuse")
        raw = secrets.token_urlsafe(32)
        digest = _digest(raw)
        from aicefr.contracts import SessionRecord

        now = self._now()
        prior_sessions = self.repository.list_sessions(actor.actor_id, _digest(token), now)
        device = next((view.device for view, _ in prior_sessions if view.current), "unknown")
        session = SessionRecord(
            token_digest=digest,
            actor_id=actor.actor_id,
            role=actor.role,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + self._idle_ttl(),
            absolute_expires_at=now + self._absolute_ttl(),
        )
        password_hash = self.auth._hasher.hash(new_password)
        self.repository.replace_password(
            actor.actor_id,
            password_hash,
            now,
            current_digest=_digest(token),
            expected_password_hash=account.password_hash,
            new_session=session,
        )
        self.repository.set_session_metadata(
            digest, "password", device, session.absolute_expires_at, now
        )
        return raw

    def list_sessions(self, token: str):
        actor = self.auth.resolve(token)
        current_digest = _digest(token)
        return [
            view
            for view, _ in self.repository.list_sessions(
                actor.actor_id, current_digest, self._now()
            )
        ]

    def revoke_session(self, token: str, session_id: str) -> bool:
        actor = self.auth.resolve(token)
        digest = self.repository.revoke_session(actor.actor_id, session_id, self._now())
        return digest == _digest(token)

    def revoke_other_sessions(self, token: str) -> int:
        actor = self.auth.resolve(token)
        current = _digest(token)
        before = self.repository.list_sessions(actor.actor_id, now=self._now())
        self.repository.revoke_all_sessions(
            actor.actor_id, self._now(), "revoke_other_sessions", except_digest=current
        )
        return sum(digest != current for _, digest in before)

    def activity(self, token: str, limit: int = 50, offset: int = 0):
        actor = self.auth.resolve(token)
        return self.repository.activity(actor.actor_id, limit, offset)

    def create_accounts(self, token: str, accounts: list[AccountCreate]) -> list[CreatedAccount]:
        actor = self._require_admin(token)
        if not isinstance(accounts, list) or not 1 <= len(accounts) <= 200:
            raise ValidationError("batch_size")
        if any(not isinstance(entry, AccountCreate) for entry in accounts):
            raise ValidationError("invalid_account")
        ids = [entry.actor_id for entry in accounts]
        if len(ids) != len(set(ids)):
            raise ConflictError("duplicate_account")
        passwords = [self._temporary_password() for _ in accounts]
        values = [
            (entry, self.auth._hasher.hash(password), self.auth._hasher.hash(password))
            for entry, password in zip(accounts, passwords, strict=True)
        ]
        created = self.repository.create_accounts(
            actor,
            values,
            self._now(),
            current_digest=_digest(token),
            student_seat_check=self.student_seat_check,
        )
        return [
            CreatedAccount(row.actor, password)
            for row, password in zip(created, passwords, strict=True)
        ]

    def create_legacy_account(self, token: str, actor_id: str, role: ActorRole, password: str):
        """Preserve the legacy admin form while requiring a first-login rotation."""
        actor = self._require_admin(token)
        self._validate_password(password)
        if password.casefold() == actor_id.casefold():
            raise ValidationError("password_reuse")
        return self.repository.create_legacy_account(
            actor,
            actor_id,
            role,
            self.auth._hasher.hash(password),
            self._now(),
            current_digest=_digest(token),
            student_seat_check=self.student_seat_check,
        )

    def change_legacy_account(
        self, token: str, target_id: str, disabled: bool | None, unlock: bool
    ) -> dict[str, Any]:
        actor = self._require_admin(token)
        updated = self.repository.change_legacy_account(
            actor,
            target_id,
            disabled,
            unlock,
            self._now(),
            current_digest=_digest(token),
        )
        return {
            "actor_id": updated.actor_id,
            "role": updated.role.value,
            "disabled": updated.disabled,
            "locked_until": updated.locked_until.isoformat() if updated.locked_until else None,
            "temporary_password_required": updated.temporary_password_required,
            "unlocked": unlock,
        }

    def admin_action(self, token: str, target_id: str, action: str, role: ActorRole | None = None):
        actor = self._require_admin(token)
        now = self._now()
        if action == "reset":
            if actor.actor_id == target_id:
                raise ConflictError("self_action_prohibited")
            password = self._temporary_password()
            self.repository.reset_temporary_password(
                actor,
                target_id,
                self.auth._hasher.hash(password),
                self.auth._hasher.hash(password),
                now,
                current_digest=_digest(token),
            )
            return CreatedAccount(
                Actor(actor_id=target_id, role=self._target_role(target_id)), password
            )
        self.repository.admin_action(
            actor, target_id, action, now, role, current_digest=_digest(token)
        )
        return None

    def consent(self, token: str):
        actor = self.auth.resolve(token)
        if actor.role is not ActorRole.STUDENT:
            raise AuthorizationError("access_denied")
        return self.repository.consent(actor.actor_id)

    def set_consent(
        self,
        token: str,
        version: str,
        research_allowed: bool,
        active: bool = True,
        audio_storage_allowed: bool = False,
    ):
        actor = self.auth.resolve(token)
        if actor.role is not ActorRole.STUDENT:
            raise AuthorizationError("access_denied")
        result = self.repository.set_consent(
            actor,
            version,
            research_allowed,
            active,
            self._now(),
            audio_storage_allowed=audio_storage_allowed,
        )
        return result

    def _require_admin(self, token: str) -> Actor:
        return self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))

    def _target_role(self, actor_id: str) -> ActorRole:
        account = self.auth._accounts.get_account(actor_id)
        if account is None:
            raise NotFoundError("account_not_found")
        return account.actor.role

    def _now(self) -> datetime:
        return self.auth._clock()

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or len(password) < 8 or len(password.encode("utf-8")) > 72:
            raise ValidationError("password_policy")

    def _verify(self, password_hash: str, password: str) -> bool:
        try:
            return self.auth._hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, TypeError):
            return False

    @staticmethod
    def _temporary_password() -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        while True:
            value = "".join(secrets.choice(alphabet) for _ in range(20))
            if (
                any(c.islower() for c in value)
                and any(c.isupper() for c in value)
                and any(c.isdigit() for c in value)
            ):
                return value

    @staticmethod
    def _idle_ttl():
        from aicefr.auth.service import IDLE_TTL

        return IDLE_TTL

    @staticmethod
    def _absolute_ttl():
        from aicefr.auth.service import ABSOLUTE_TTL

        return ABSOLUTE_TTL
