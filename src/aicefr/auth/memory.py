"""In-memory repositories for synthetic unit fixtures."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from aicefr.auth.service import IDLE_TTL, AccountRecord
from aicefr.contracts import ConsentRecord, SessionRecord


class MemoryIdentityRepository:
    def __init__(self) -> None:
        self.accounts: dict[str, AccountRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}
        self.consents: dict[str, ConsentRecord] = {}

    def get_account(self, actor_id: str) -> AccountRecord | None:
        return self.accounts.get(actor_id)

    def add_account(self, account: AccountRecord) -> None:
        if account.actor.actor_id in self.accounts:
            raise ValueError("account already exists")
        self.accounts[account.actor.actor_id] = account

    def record_login(self, actor_id: str, *, success: bool, now: datetime) -> None:
        account = self.accounts[actor_id]
        attempts = (
            0
            if success or (account.locked_until and now >= account.locked_until)
            else (account.failed_attempts)
        )
        if not success:
            attempts += 1
        self.accounts[actor_id] = replace(
            account,
            failed_attempts=attempts,
            locked_until=now + timedelta(minutes=15) if attempts >= 5 else None,
        )

    def get_session(self, digest: str) -> SessionRecord | None:
        return self.sessions.get(digest)

    def put_session(self, session: SessionRecord) -> None:
        self.sessions[session.token_digest] = session

    def touch_session(self, session: SessionRecord, *, now: datetime) -> bool:
        current = self.sessions.get(session.token_digest)
        if (
            current is None
            or current.actor_id != session.actor_id
            or current.role is not session.role
            or current.created_at != session.created_at
            or current.absolute_expires_at != session.absolute_expires_at
            or now >= current.idle_expires_at
            or now >= current.absolute_expires_at
        ):
            return False
        self.sessions[session.token_digest] = current.model_copy(
            update={
                "last_seen_at": now,
                "idle_expires_at": min(now + IDLE_TTL, current.absolute_expires_at),
            }
        )
        return True

    def delete_session(self, digest: str) -> None:
        self.sessions.pop(digest, None)

    def get_consent(self, participant_id: str) -> ConsentRecord | None:
        return self.consents.get(participant_id)

    def put_consent(self, consent: ConsentRecord) -> None:
        self.consents[consent.participant_id] = consent
