"""M11 identity operations over the frozen v9 SQLite schema."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any

from aicefr.auth.contracts import (
    PROFILE_COLORS,
    PROFILE_ICONS,
    AccountCreate,
    AccountProfile,
    ActivityItem,
    AdminAccount,
    CreatedAccount,
    PublicSession,
)
from aicefr.auth.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from aicefr.contracts import Actor, ActorRole, AuditEvent, ConsentRecord, ConsentState


def public_session_id(token_digest: str) -> str:
    """Return a domain-separated opaque ID without exposing the session digest."""
    return hashlib.sha256(b"aicefr:public-session:v1:" + token_digest.encode("ascii")).hexdigest()


class IdentityRepository:
    """Identity repository sharing the caller's SQLiteStore transaction boundary."""

    def __init__(self, store: Any) -> None:
        self.storage = store
        self.connection: sqlite3.Connection = store.connection

    def get_profile(self, actor_id: str) -> AccountProfile | None:
        row = self.connection.execute(
            """SELECT a.actor_id,a.role,p.goal,p.icon,p.color,p.revision,
            EXISTS(SELECT 1 FROM temporary_passwords t WHERE t.account_id=a.actor_id)
            FROM accounts a LEFT JOIN account_profiles p ON p.account_id=a.actor_id
            WHERE a.actor_id=? AND a.disabled=0""",
            (actor_id,),
        ).fetchone()
        if row is None:
            return None
        return AccountProfile(
            str(row[0]), ActorRole(row[1]), row[2], row[3], row[4], bool(row[6]), int(row[5] or 0)
        )

    def update_profile(
        self, actor_id: str, fields: dict[str, Any], now: datetime
    ) -> AccountProfile:
        allowed = {"goal", "icon", "color"}
        if not fields or set(fields) - allowed:
            raise ValidationError("invalid_profile_fields")
        if (
            "goal" in fields
            and fields["goal"] is not None
            and (type(fields["goal"]) is not int or fields["goal"] not in (1, 2, 3, 5, 10))
        ):
            raise ValidationError("invalid_goal")
        icon, color = fields.get("icon"), fields.get("color")
        if icon is not None and (not isinstance(icon, str) or icon not in PROFILE_ICONS):
            raise ValidationError("invalid_profile_icon")
        if color is not None and (not isinstance(color, str) or color not in PROFILE_COLORS):
            raise ValidationError("invalid_profile_color")
        with self.storage.transaction() as connection:
            account = connection.execute(
                "SELECT role FROM accounts WHERE actor_id=? AND disabled=0", (actor_id,)
            ).fetchone()
            if account is None:
                raise NotFoundError()
            if ActorRole(account[0]) is not ActorRole.STUDENT and "goal" in fields:
                raise ValidationError("goal_not_applicable")
            connection.execute(
                "INSERT OR IGNORE INTO account_profiles(account_id,updated_at) VALUES (?,?)",
                (actor_id, now.isoformat()),
            )
            columns = ",".join(f"{key}=?" for key in fields)
            values = list(fields.values())
            connection.execute(
                f"UPDATE account_profiles SET {columns},revision=revision+1,updated_at=? "
                "WHERE account_id=?",
                (*values, now.isoformat(), actor_id),
            )
            self._audit(connection, actor_id, "profile_updated", actor_id, now, None)
            self._activity(connection, actor_id, "profile_updated", actor_id, now, None)
        profile = self.get_profile(actor_id)
        assert profile is not None
        return profile

    def list_sessions(
        self, actor_id: str, current_digest: str | None = None, now: datetime | None = None
    ) -> list[tuple[PublicSession, str]]:
        rows = self.connection.execute(
            """SELECT s.token_digest,s.actor_id,s.created_at,s.last_seen_at,s.idle_expires_at,
            s.absolute_expires_at,m.method,m.device,m.expires_at,m.revoked_at
            FROM sessions s LEFT JOIN session_metadata m ON m.token_digest=s.token_digest
            WHERE s.actor_id=? ORDER BY s.created_at DESC""",
            (actor_id,),
        ).fetchall()
        result = []
        for row in rows:
            if row[9] is not None:
                continue
            digest = str(row[0])
            expires = (
                min(
                    datetime.fromisoformat(row[8]),
                    datetime.fromisoformat(row[4]),
                    datetime.fromisoformat(row[5]),
                )
                if row[8]
                else min(datetime.fromisoformat(row[4]), datetime.fromisoformat(row[5]))
            )
            if now is not None and now >= expires:
                continue
            result.append(
                (
                    PublicSession(
                        public_session_id(digest),
                        str(row[1]),
                        str(row[6] or "password"),
                        str(row[7] or ""),
                        datetime.fromisoformat(row[2]),
                        datetime.fromisoformat(row[3]),
                        expires,
                        digest == current_digest,
                    ),
                    digest,
                )
            )
        return result

    def revoke_session(self, actor_id: str, session_id: str, now: datetime) -> str:
        for session, digest in self.list_sessions(actor_id, now=now):
            if session.session_id == session_id:
                with self.storage.transaction() as connection:
                    connection.execute(
                        "DELETE FROM sessions WHERE token_digest=? AND actor_id=?",
                        (digest, actor_id),
                    )
                    self._audit(connection, actor_id, "session_revoked", session_id, now, None)
                    self._activity(connection, actor_id, "session_revoked", session_id, now, None)
                return digest
        raise NotFoundError("session_not_found")

    def revoke_all_sessions(
        self,
        actor_id: str,
        now: datetime,
        reason: str = "security_change",
        *,
        except_digest: str | None = None,
    ) -> None:
        with self.storage.transaction() as connection:
            if except_digest:
                connection.execute(
                    "DELETE FROM sessions WHERE actor_id=? AND token_digest<>?",
                    (actor_id, except_digest),
                )
            else:
                connection.execute("DELETE FROM sessions WHERE actor_id=?", (actor_id,))
            self._audit(connection, actor_id, "sessions_revoked", actor_id, now, reason)
            self._activity(connection, actor_id, "sessions_revoked", actor_id, now, reason)

    def activity(self, actor_id: str, limit: int = 50, offset: int = 0) -> list[ActivityItem]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValidationError("invalid_pagination")
        rows = self.connection.execute(
            "SELECT kind,object_id,recorded_at,detail_code FROM activity_events "
            "WHERE account_id=? ORDER BY recorded_at DESC,rowid DESC LIMIT ? OFFSET ?",
            (actor_id, limit, offset),
        ).fetchall()
        return [ActivityItem(str(r[0]), r[1], datetime.fromisoformat(r[2]), r[3]) for r in rows]

    def create_accounts(
        self,
        creator: Actor,
        entries: list[tuple[AccountCreate, str, str]],
        now: datetime,
        *,
        current_digest: str | None = None,
    ) -> list[CreatedAccount]:
        if not 1 <= len(entries) <= 200:
            raise ValidationError("batch_size")
        ids = [entry.actor_id for entry, _, _ in entries]
        if len(set(ids)) != len(ids):
            raise ConflictError("duplicate_account")
        for entry, _, _ in entries:
            if not _valid_actor_id(entry.actor_id) or entry.role not in (
                ActorRole.STUDENT,
                ActorRole.TEACHER,
                ActorRole.ADMIN,
            ):
                raise ValidationError("invalid_account")
            if entry.role is not ActorRole.STUDENT and entry.goal is not None:
                raise ValidationError("goal_not_applicable")
            if entry.goal is not None and (
                type(entry.goal) is not int or entry.goal not in (1, 2, 3, 5, 10)
            ):
                raise ValidationError("invalid_goal")
        with self.storage.transaction() as connection:
            self._require_admin(connection, creator)
            if current_digest is not None:
                self._require_live_admin_session(connection, creator, current_digest, now)
            if any(
                connection.execute(
                    "SELECT 1 FROM accounts WHERE actor_id=?", (actor_id,)
                ).fetchone()
                for actor_id in ids
            ):
                raise ConflictError("duplicate_account")
            created = []
            for entry, password_hash, temp_hash in entries:
                connection.execute(
                    "INSERT INTO accounts(actor_id,role,password_hash) VALUES (?,?,?)",
                    (entry.actor_id, entry.role.value, password_hash),
                )
                connection.execute(
                    "INSERT INTO account_profiles(account_id,goal,updated_at) VALUES (?,?,?)",
                    (entry.actor_id, entry.goal, now.isoformat()),
                )
                connection.execute(
                    "INSERT INTO temporary_passwords "
                    "(account_id,password_hash,expires_at,created_at,created_by) "
                    "VALUES (?,?,?,?,?)",
                    (
                        entry.actor_id,
                        temp_hash,
                        (now + timedelta(hours=24)).isoformat(),
                        now.isoformat(),
                        creator.actor_id,
                    ),
                )
                self._audit(
                    connection, creator.actor_id, "account_created", entry.actor_id, now, None
                )
                self._activity(
                    connection, entry.actor_id, "account_created", entry.actor_id, now, None
                )
                created.append(CreatedAccount(Actor(actor_id=entry.actor_id, role=entry.role), ""))
            return created

    def admin_action(
        self,
        actor: Actor,
        target_id: str,
        action: str,
        now: datetime,
        role: ActorRole | None = None,
        *,
        current_digest: str | None = None,
    ) -> None:
        if actor.actor_id == target_id and action in {
            "disable",
            "reset",
            "role",
            "revoke_all",
            "unlink",
        }:
            raise ConflictError("self_action_prohibited")
        if action not in {"unlock", "disable", "enable", "reset", "role", "revoke_all", "unlink"}:
            raise ValidationError("invalid_admin_action")
        with self.storage.transaction() as connection:
            self._require_admin(connection, actor)
            if current_digest is not None:
                self._require_live_admin_session(connection, actor, current_digest, now)
            row = connection.execute(
                "SELECT role,disabled FROM accounts WHERE actor_id=?", (target_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError("account_not_found")
            if action == "unlock":
                connection.execute(
                    "UPDATE accounts SET failed_attempts=0,locked_until=NULL WHERE actor_id=?",
                    (target_id,),
                )
            elif action == "disable":
                connection.execute("UPDATE accounts SET disabled=1 WHERE actor_id=?", (target_id,))
                connection.execute("DELETE FROM sessions WHERE actor_id=?", (target_id,))
            elif action == "enable":
                connection.execute("UPDATE accounts SET disabled=0 WHERE actor_id=?", (target_id,))
            elif action == "role":
                if role is None or not isinstance(role, ActorRole):
                    raise ValidationError("invalid_role")
                connection.execute(
                    "UPDATE accounts SET role=? WHERE actor_id=?", (role.value, target_id)
                )
                connection.execute("DELETE FROM sessions WHERE actor_id=?", (target_id,))
            elif action == "revoke_all":
                connection.execute("DELETE FROM sessions WHERE actor_id=?", (target_id,))
            elif action == "unlink":
                connection.execute(
                    "DELETE FROM account_identities WHERE account_id=? AND provider='google'",
                    (target_id,),
                )
            elif action == "reset":
                raise ValidationError("reset_requires_temporary_password")
            self._audit(connection, actor.actor_id, f"account_{action}", target_id, now, None)
            self._activity(connection, target_id, f"account_{action}", target_id, now, None)

    def change_legacy_account(
        self,
        actor: Actor,
        target_id: str,
        disabled: bool | None,
        unlock: bool,
        now: datetime,
        *,
        current_digest: str | None = None,
    ) -> AdminAccount:
        if actor.role is not ActorRole.ADMIN:
            raise AuthorizationError("access denied")
        if actor.actor_id == target_id and disabled is True:
            raise ConflictError("self_action_prohibited")
        if disabled is not None and not isinstance(disabled, bool):
            raise ValidationError("invalid_disabled_state")
        with self.storage.transaction() as connection:
            self._require_admin(connection, actor)
            if current_digest is not None:
                self._require_live_admin_session(connection, actor, current_digest, now)
            if not connection.execute(
                "SELECT 1 FROM accounts WHERE actor_id=?", (target_id,)
            ).fetchone():
                raise NotFoundError("account_not_found")
            if disabled is not None:
                connection.execute(
                    "UPDATE accounts SET disabled=? WHERE actor_id=?",
                    (int(disabled), target_id),
                )
                if disabled:
                    connection.execute("DELETE FROM sessions WHERE actor_id=?", (target_id,))
                action = "account_disabled" if disabled else "account_enabled"
                self._audit(connection, actor.actor_id, action, target_id, now, None)
                self._activity(connection, target_id, action, target_id, now, None)
            if unlock:
                connection.execute(
                    "UPDATE accounts SET failed_attempts=0,locked_until=NULL WHERE actor_id=?",
                    (target_id,),
                )
                self._audit(connection, actor.actor_id, "account_unlocked", target_id, now, None)
                self._activity(connection, target_id, "account_unlocked", target_id, now, None)
        result = self.admin_account(actor, target_id)
        assert result is not None
        return result

    def admin_account(self, actor: Actor, target_id: str) -> AdminAccount | None:
        if actor.role is not ActorRole.ADMIN:
            raise AuthorizationError("access denied")
        row = self.connection.execute(
            "SELECT a.actor_id,a.role,p.goal,p.icon,p.color,p.revision, "
            "EXISTS(SELECT 1 FROM temporary_passwords t WHERE t.account_id=a.actor_id), "
            "a.disabled,a.locked_until FROM accounts a "
            "LEFT JOIN account_profiles p ON p.account_id=a.actor_id WHERE a.actor_id=?",
            (target_id,),
        ).fetchone()
        if row is None:
            return None
        return AdminAccount(
            str(row[0]),
            ActorRole(row[1]),
            row[2],
            row[3],
            row[4],
            bool(row[6]),
            int(row[5] or 0),
            bool(row[7]),
            datetime.fromisoformat(row[8]) if row[8] else None,
        )

    def consent(self, actor_id: str) -> ConsentRecord | None:
        row = self.connection.execute(
            "SELECT participant_id,consent_version,state,recorded_at,research_allowed "
            "FROM consents WHERE participant_id=?",
            (actor_id,),
        ).fetchone()
        if row is None:
            return None
        return ConsentRecord(
            participant_id=row[0],
            consent_version=row[1],
            state=ConsentState(row[2]),
            recorded_at=datetime.fromisoformat(row[3]),
            research_allowed=bool(row[4]),
        )

    def get_consent(self, participant_id: str) -> ConsentRecord | None:
        return self.consent(participant_id)

    def put_consent(self, consent: ConsentRecord) -> None:
        actor = self.storage.get_account(consent.participant_id)
        if actor is None:
            raise NotFoundError("account_not_found")
        self.set_consent(
            actor.actor,
            consent.consent_version,
            consent.research_allowed,
            consent.state is ConsentState.ACTIVE,
            consent.recorded_at,
        )

    def set_consent(
        self, actor: Actor, version: str, research_allowed: bool, active: bool, now: datetime
    ) -> ConsentRecord:
        if actor.role is not ActorRole.STUDENT:
            raise AuthorizationError("access denied")
        if not isinstance(version, str) or not version.strip() or len(version) > 64:
            raise ValidationError("invalid_consent_version")
        if not isinstance(research_allowed, bool) or not isinstance(active, bool):
            raise ValidationError("invalid_consent")
        state = ConsentState.ACTIVE if active else ConsentState.WITHDRAWN
        record = ConsentRecord(
            participant_id=actor.actor_id,
            consent_version=version,
            state=state,
            recorded_at=now,
            research_allowed=research_allowed if active else False,
        )
        with self.storage.transaction() as connection:
            self._require_active_student(connection, actor)
            connection.execute(
                "INSERT INTO consents "
                "(participant_id,consent_version,state,recorded_at,research_allowed) "
                "VALUES(?,?,?,?,?) ON CONFLICT(participant_id) DO UPDATE SET "
                "consent_version=excluded.consent_version,state=excluded.state,"
                "recorded_at=excluded.recorded_at,research_allowed=excluded.research_allowed",
                (
                    actor.actor_id,
                    version,
                    state.value,
                    now.isoformat(),
                    int(record.research_allowed),
                ),
            )
            connection.execute(
                "INSERT INTO consent_events VALUES(?,?,?,?,?,?,'self_service')",
                (
                    uuid.uuid4().hex,
                    actor.actor_id,
                    version,
                    state.value,
                    int(record.research_allowed),
                    now.isoformat(),
                ),
            )
            if not active or not research_allowed:
                connection.execute(
                    "UPDATE study_enrollments SET withdrawn_at=? "
                    "WHERE participant_id=? AND withdrawn_at IS NULL",
                    (now.isoformat(), actor.actor_id),
                )
                connection.execute(
                    "UPDATE rating_assignments SET state='VOID' "
                    "WHERE response_id IN (SELECT response_id FROM responses WHERE owner_id=?) "
                    "AND state IN ('OPEN','SUBMITTED')",
                    (actor.actor_id,),
                )
            self._audit(
                connection,
                actor.actor_id,
                f"consent_{state.value}",
                actor.actor_id,
                now,
                "research_allowed" if record.research_allowed else "research_denied",
            )
            self._activity(
                connection, actor.actor_id, "consent_updated", actor.actor_id, now, state.value
            )
        return record

    def has_temporary_password(self, actor_id: str, *, now: datetime | None = None) -> bool:
        return (
            self.connection.execute(
                "SELECT 1 FROM temporary_passwords WHERE account_id=?", (actor_id,)
            ).fetchone()
            is not None
        )

    def temporary_password_expired(self, actor_id: str, now: datetime) -> bool:
        row = self.connection.execute(
            "SELECT expires_at FROM temporary_passwords WHERE account_id=?", (actor_id,)
        ).fetchone()
        return row is not None and now >= datetime.fromisoformat(row[0])

    def list_accounts(self, actor: Actor, limit: int = 200, offset: int = 0) -> list[AdminAccount]:
        if actor.role is not ActorRole.ADMIN:
            raise AuthorizationError("access denied")
        if not 1 <= limit <= 200 or offset < 0:
            raise ValidationError("invalid_pagination")
        rows = self.connection.execute(
            "SELECT a.actor_id,a.role,p.goal,p.icon,p.color,p.revision, "
            "EXISTS(SELECT 1 FROM temporary_passwords t WHERE t.account_id=a.actor_id) "
            ",a.disabled,a.locked_until "
            "FROM accounts a LEFT JOIN account_profiles p ON p.account_id=a.actor_id "
            "ORDER BY a.actor_id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [
            AdminAccount(
                str(r[0]),
                ActorRole(r[1]),
                r[2],
                r[3],
                r[4],
                bool(r[6]),
                int(r[5] or 0),
                bool(r[7]),
                datetime.fromisoformat(r[8]) if r[8] else None,
            )
            for r in rows
        ]

    def record_activity(
        self,
        actor_id: str,
        kind: str,
        object_id: str | None,
        now: datetime,
        detail: str | None = None,
    ) -> None:
        with self.storage.transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM accounts WHERE actor_id=?", (actor_id,)
            ).fetchone():
                self._activity(connection, actor_id, kind, object_id, now, detail)

    def audit(
        self, actor_id: str, action: str, object_id: str, now: datetime, reason: str | None = None
    ) -> None:
        with self.storage.transaction() as connection:
            self._audit(connection, actor_id, action, object_id, now, reason)

    def reset_temporary_password(
        self,
        actor: Actor,
        target_id: str,
        password_hash: str,
        temp_hash: str,
        now: datetime,
        *,
        current_digest: str,
    ) -> None:
        if actor.actor_id == target_id:
            raise ConflictError("self_action_prohibited")
        with self.storage.transaction() as connection:
            self._require_admin(connection, actor)
            self._require_live_admin_session(connection, actor, current_digest, now)
            if not connection.execute(
                "SELECT 1 FROM accounts WHERE actor_id=?", (target_id,)
            ).fetchone():
                raise NotFoundError("account_not_found")
            connection.execute(
                "UPDATE accounts SET password_hash=?,failed_attempts=0,locked_until=NULL "
                "WHERE actor_id=?",
                (password_hash, target_id),
            )
            connection.execute(
                "INSERT INTO temporary_passwords "
                "(account_id,password_hash,expires_at,created_at,created_by) VALUES(?,?,?,?,?) "
                "ON CONFLICT(account_id) DO UPDATE SET password_hash=excluded.password_hash, "
                "expires_at=excluded.expires_at,created_at=excluded.created_at, "
                "created_by=excluded.created_by",
                (
                    target_id,
                    temp_hash,
                    (now + timedelta(hours=24)).isoformat(),
                    now.isoformat(),
                    actor.actor_id,
                ),
            )
            connection.execute("DELETE FROM sessions WHERE actor_id=?", (target_id,))
            self._audit(connection, actor.actor_id, "account_reset", target_id, now, None)
            self._activity(connection, target_id, "account_reset", target_id, now, None)

    def replace_password(
        self,
        actor_id: str,
        password_hash: str,
        now: datetime,
        *,
        current_digest: str | None = None,
        expected_password_hash: str | None = None,
        new_session: Any = None,
    ) -> None:
        with self.storage.transaction() as connection:
            account = connection.execute(
                "SELECT password_hash,role,disabled FROM accounts WHERE actor_id=?", (actor_id,)
            ).fetchone()
            if account is None:
                raise NotFoundError("account_not_found")
            if account[2]:
                raise AuthorizationError("account unavailable")
            if expected_password_hash is not None and not hmac.compare_digest(
                str(account[0]), expected_password_hash
            ):
                raise ConflictError("credential_changed")
            if current_digest is not None:
                session = connection.execute(
                    "SELECT role,idle_expires_at,absolute_expires_at FROM sessions "
                    "WHERE token_digest=? AND actor_id=?",
                    (current_digest, actor_id),
                ).fetchone()
                if (
                    session is None
                    or session[0] != account[1]
                    or now >= datetime.fromisoformat(session[1])
                    or now >= datetime.fromisoformat(session[2])
                ):
                    raise AuthorizationError("session unavailable")
            connection.execute(
                "UPDATE accounts SET password_hash=?,failed_attempts=0,locked_until=NULL "
                "WHERE actor_id=?",
                (password_hash, actor_id),
            )
            connection.execute("DELETE FROM temporary_passwords WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM sessions WHERE actor_id=?", (actor_id,))
            if new_session is not None:
                self.storage.put_session(new_session)
                self.set_session_metadata(
                    new_session.token_digest, "password", "", new_session.absolute_expires_at, now
                )
            self._audit(connection, actor_id, "password_changed", actor_id, now, None)
            self._activity(connection, actor_id, "password_changed", actor_id, now, None)

    def create_legacy_account(
        self,
        creator: Actor,
        actor_id: str,
        role: ActorRole,
        password_hash: str,
        now: datetime,
        *,
        current_digest: str | None = None,
    ) -> AccountProfile:
        if not _valid_actor_id(actor_id) or not isinstance(role, ActorRole):
            raise ValidationError("invalid_account")
        try:
            with self.storage.transaction() as connection:
                self._require_admin(connection, creator)
                if current_digest is not None:
                    self._require_live_admin_session(connection, creator, current_digest, now)
                if connection.execute(
                    "SELECT 1 FROM accounts WHERE actor_id=?", (actor_id,)
                ).fetchone():
                    raise ConflictError("duplicate_account")
                connection.execute(
                    "INSERT INTO accounts(actor_id,role,password_hash) VALUES(?,?,?)",
                    (actor_id, role.value, password_hash),
                )
                connection.execute(
                    "INSERT INTO temporary_passwords "
                    "(account_id,password_hash,expires_at,created_at,created_by) VALUES(?,?,?,?,?)",
                    (
                        actor_id,
                        password_hash,
                        (now + timedelta(hours=24)).isoformat(),
                        now.isoformat(),
                        creator.actor_id,
                    ),
                )
                connection.execute(
                    "INSERT INTO account_profiles(account_id,updated_at) VALUES(?,?)",
                    (actor_id, now.isoformat()),
                )
                self._audit(
                    connection,
                    creator.actor_id,
                    "account_created",
                    actor_id,
                    now,
                    "legacy_initial_password",
                )
                self._activity(connection, actor_id, "account_created", actor_id, now, None)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("duplicate_account") from exc
        profile = self.get_profile(actor_id)
        assert profile is not None
        return profile

    def set_session_metadata(
        self, digest: str, method: str, device: str, expires_at: datetime, now: datetime
    ) -> None:
        with self.storage.transaction() as connection:
            safe_device = "".join(c for c in device if c.isprintable() and c not in "\r\n")[:80]
            safe_method = (
                "".join(c for c in method if c.isascii() and (c.isalnum() or c in "_-"))[:32]
                or "password"
            )
            connection.execute(
                "INSERT INTO session_metadata "
                "(token_digest,device,method,expires_at,revoked_at) VALUES(?,?,?,?,NULL) "
                "ON CONFLICT(token_digest) DO UPDATE SET device=excluded.device, "
                "method=excluded.method,expires_at=excluded.expires_at,revoked_at=NULL",
                (digest, safe_device, safe_method, expires_at.isoformat()),
            )

    def unlink_google(self, actor_id: str, now: datetime) -> bool:
        with self.storage.transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM account_identities WHERE account_id=? AND provider='google'",
                (actor_id,),
            )
            if cursor.rowcount:
                self._audit(connection, actor_id, "google_unlinked", actor_id, now, None)
                self._activity(connection, actor_id, "google_unlinked", actor_id, now, None)
            return bool(cursor.rowcount)

    def _audit(
        self,
        connection: sqlite3.Connection,
        actor_id: str,
        action: str,
        object_id: str,
        now: datetime,
        reason: str | None,
    ) -> None:
        event = AuditEvent(
            event_id=uuid.uuid4().hex,
            actor_id=actor_id,
            action=action,
            object_id=object_id,
            recorded_at=now,
            reason=reason,
        )
        self.storage.record_audit(connection, event)

    @staticmethod
    def _require_admin(connection: sqlite3.Connection, actor: Actor) -> None:
        row = connection.execute(
            "SELECT role,disabled FROM accounts WHERE actor_id=?", (actor.actor_id,)
        ).fetchone()
        if row is None or row[0] != ActorRole.ADMIN.value or row[1]:
            raise AuthorizationError("access denied")

    @staticmethod
    def _require_live_admin_session(
        connection: sqlite3.Connection, actor: Actor, token_digest: str, now: datetime
    ) -> None:
        stamp = now.isoformat()
        row = connection.execute(
            "SELECT 1 FROM sessions s JOIN accounts a ON a.actor_id=s.actor_id "
            "LEFT JOIN session_metadata m ON m.token_digest=s.token_digest "
            "WHERE s.token_digest=? AND s.actor_id=? AND s.role=? AND a.role=? AND a.disabled=0 "
            "AND s.idle_expires_at>? AND s.absolute_expires_at>? "
            "AND (m.expires_at IS NULL OR m.expires_at>?) AND m.revoked_at IS NULL",
            (
                token_digest,
                actor.actor_id,
                actor.role.value,
                ActorRole.ADMIN.value,
                stamp,
                stamp,
                stamp,
            ),
        ).fetchone()
        if row is None:
            raise AuthorizationError("session unavailable")

    @staticmethod
    def _require_active_student(connection: sqlite3.Connection, actor: Actor) -> None:
        row = connection.execute(
            "SELECT role,disabled FROM accounts WHERE actor_id=?", (actor.actor_id,)
        ).fetchone()
        if row is None or row[0] != ActorRole.STUDENT.value or row[1]:
            raise AuthorizationError("access denied")

    @staticmethod
    def _activity(
        connection: sqlite3.Connection,
        actor_id: str,
        kind: str,
        object_id: str | None,
        now: datetime,
        detail: str | None,
    ) -> None:
        connection.execute(
            "INSERT INTO activity_events VALUES(?,?,?,?,?,?)",
            (uuid.uuid4().hex, actor_id, kind, object_id, now.isoformat(), detail),
        )


def _valid_actor_id(actor_id: str) -> bool:
    return (
        isinstance(actor_id, str)
        and actor_id.isascii()
        and 1 <= len(actor_id) <= 80
        and all(c.isalnum() or c in "-_" for c in actor_id)
    )
