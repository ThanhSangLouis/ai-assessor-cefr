"""Persistence for accounts and login sessions. Implements FR-32 and NFR-07.

Kept separate from Repository so that scoring logic and authentication are not
mixed together, but pointed at the SAME database file so there is only one
connection target to manage.

The same privacy rule applies: the account table holds only pseudonyms. Never
store a real name, a student ID, or any contact detail.
"""

from __future__ import annotations

import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from aicefr.auth import passwords
from aicefr.auth import sessions as session_tokens
from aicefr.auth.pseudonyms import validate_pseudonym
from aicefr.contracts import AuthSession
from aicefr.storage.db import Connection, DbRow, SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

# NFR-07: lock the account for 15 minutes after 5 consecutive failed logins;
# the 6th attempt returns HTTP 429.
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15

SCHEMA_AUTH = """
CREATE TABLE IF NOT EXISTS account (
    account_id      TEXT PRIMARY KEY,
    pseudonym       TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    disabled        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash      TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES account(account_id),
    expires_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_account ON auth_sessions(account_id);

-- D029. An outside identity (Google) linked to an account by its owner. Only a
-- one-way hash of the provider's subject identifier is kept: no email, no
-- name, no photo. One identity per account per provider, one account per
-- identity.
CREATE TABLE IF NOT EXISTS account_identity (
    provider        TEXT NOT NULL,
    subject_hash    TEXT NOT NULL,
    account_id      TEXT NOT NULL REFERENCES account(account_id),
    linked_at       TEXT NOT NULL,
    PRIMARY KEY (provider, subject_hash),
    UNIQUE (account_id, provider)
);
-- D036. Random keys this deployment signs with, made once and kept, so every
-- worker and every restart agree. Not a person's data; never shown.
CREATE TABLE IF NOT EXISTS server_secret (
    name        TEXT PRIMARY KEY,
    value_hex   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


class Role(str, Enum):
    """The three roles defined by FR-32."""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# Profile choices (D029). Allowlists, not free text: an avatar is an icon of the
# sprite and a colour of the topic palette, never an uploaded photo, and there
# is no "display name" field that would invite a real name (FR-33).
AVATAR_ICONS = (
    "user",
    "star",
    "leaf",
    "heart",
    "flame",
    "sparkle",
    "trophy",
    "target",
    "cap",
    "plane",
    "briefcase",
    "bowl",
    "chip",
    "house",
    "news",
)
AVATAR_COLORS = (
    "daily",
    "education",
    "travel",
    "career",
    "food",
    "health",
    "technology",
    "environment",
    "people",
    "society",
)
# Seconds of speaking a learner aims for each day; 180 is the D025 default.
DAILY_GOALS = (60, 120, 180, 300, 600)
DEFAULT_DAILY_GOAL = 180


@dataclass(frozen=True)
class Account:
    account_id: str
    pseudonym: str
    role: Role
    # Set on an account created or reset by an administrator (D028): the
    # password on the printed slip works for one thing only, choosing a new one.
    must_change_password: bool = False
    # D029 profile, read with the session so every page can draw the avatar.
    avatar_icon: str | None = None
    avatar_color: str | None = None
    daily_goal_s: int = DEFAULT_DAILY_GOAL

    @property
    def is_teacher(self) -> bool:
        return self.role in (Role.TEACHER, Role.ADMIN)


class AccountLocked(Exception):
    """The account is temporarily locked after too many failed logins."""


class WrongPassword(Exception):
    """The current password given to a password change does not match."""


class IdentityTaken(Exception):
    """The outside identity is already linked to a different account."""


# Prefix of generated pseudonyms per role: SV-001 (sinh viên), GV-001 (giảng
# viên), QT-001 (quản trị). Short, sequential and meaningless outside the
# system, as FR-33 wants: the link to a real person lives on paper.
DEFAULT_PREFIX = {Role.STUDENT: "SV", Role.TEACHER: "GV", Role.ADMIN: "QT"}
PREFIX_PATTERN = re.compile(r"^[A-Za-z]{1,6}$")


class AuthRepository(SqlStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        self._secrets: dict[str, bytes] = {}
        with self._conn() as c:
            c.executescript(SCHEMA_AUTH)
            self._upgrade_schema(c)

    def secret(self, name: str) -> bytes:
        """A 32-byte key of this deployment for `name`, made the first time it is asked for.

        Two processes asking at once agree: the first insert wins and both read
        it back.
        """
        if name not in self._secrets:
            with self._conn() as c:
                c.execute(
                    "INSERT OR IGNORE INTO server_secret(name, value_hex, created_at)"
                    " VALUES (?,?,?)",
                    (name, os.urandom(32).hex(), _now()),
                )
                row = c.execute(
                    "SELECT value_hex FROM server_secret WHERE name=?", (name,)
                ).fetchone()
            self._secrets[name] = bytes.fromhex(row["value_hex"])
        return self._secrets[name]

    @staticmethod
    def _upgrade_schema(c: Connection) -> None:
        """Add the D028 and D029 columns to tables created by an older build."""
        for table, wanted in (
            (
                "account",
                (
                    ("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
                    ("last_login_at", "TEXT"),
                    ("password_changed_at", "TEXT"),
                    ("avatar_icon", "TEXT"),
                    ("avatar_color", "TEXT"),
                    ("daily_goal_s", f"INTEGER NOT NULL DEFAULT {DEFAULT_DAILY_GOAL}"),
                ),
            ),
            # D029: how a session was opened and on what kind of device, so a
            # person can tell "my phone" from "a computer I do not recognise".
            ("auth_sessions", (("device", "TEXT"), ("method", "TEXT"))),
        ):
            add_columns(c, table, wanted)

    # ---------- accounts ----------

    def create_account(
        self,
        pseudonym: str,
        raw_password: str,
        role: Role,
        must_change_password: bool = False,
    ) -> str:
        """Create a new account and return its account_id."""
        # Enforced here, at the one place a pseudonym enters the system. Doing
        # it at submission time instead let a bad pseudonym exist in the account
        # table and only fail later, on somebody else's screen.
        pseudonym = validate_pseudonym(pseudonym)
        aid = uuid.uuid4().hex[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO account(account_id,pseudonym,password_hash,role,created_at,"
                "must_change_password) VALUES(?,?,?,?,?,?)",
                (
                    aid,
                    pseudonym,
                    passwords.hash_password(raw_password),
                    role.value,
                    _now(),
                    int(must_change_password),
                ),
            )
        return aid

    def create_with_temporary_passwords(
        self, pseudonyms: list[str], role: Role
    ) -> list[tuple[str, str, str]]:
        """Create accounts that must choose a password at first login (D028).

        Returns (account_id, pseudonym, temporary password) per account; the
        passwords exist in clear only in this return value. All or nothing: one
        pseudonym already taken and no account is created, so a half-made class
        list never has to be untangled by hand.

        bcrypt at cost 12 takes about a quarter of a second per password and
        releases the GIL, so a class of ninety is hashed on a few threads
        instead of keeping the administrator waiting twenty seconds.
        """
        names = [validate_pseudonym(n) for n in pseudonyms]
        if len({n.lower() for n in names}) != len(names):
            raise ValueError("danh sách bút danh bị trùng")
        temporaries = [passwords.temporary_password() for _ in names]
        workers = max(1, min(8, os.cpu_count() or 1, len(names)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            hashes = list(pool.map(passwords.hash_password, temporaries))
        created = [(uuid.uuid4().hex[:12], n, t) for n, t in zip(names, temporaries, strict=True)]
        now = _now()
        with self._conn() as c:
            taken = c.execute(
                f"SELECT pseudonym FROM account WHERE lower(pseudonym) IN"
                f" ({','.join('?' * len(names))})",
                [n.lower() for n in names],
            ).fetchall()
            if taken:
                raise ValueError(
                    "bút danh đã tồn tại: " + ", ".join(sorted(r["pseudonym"] for r in taken))
                )
            c.executemany(
                "INSERT INTO account(account_id,pseudonym,password_hash,role,created_at,"
                "must_change_password) VALUES(?,?,?,?,?,1)",
                [
                    (aid, name, h, role.value, now)
                    for (aid, name, _), h in zip(created, hashes, strict=True)
                ],
            )
        return created

    def get(self, account_id: str) -> DbRow | None:
        """One account by id, disabled or not: the administrator's view."""
        with self._conn() as c:
            return c.execute("SELECT * FROM account WHERE account_id=?", (account_id,)).fetchone()

    def count_role(self, role: Role) -> int:
        """Enabled accounts of one role: the seats a plan counts (D033)."""
        with self._conn() as c:
            return c.execute(
                "SELECT COUNT(*) FROM account WHERE role=? AND disabled=0", (role.value,)
            ).fetchone()[0]

    def list_accounts(self) -> list[dict]:
        """Every account with what an administrator needs to look after it.

        No password hash leaves this method. `active_sessions` counts sessions
        that have not expired, so "signed in on two devices" is visible.
        """
        now = _now()
        with self._conn() as c:
            rows = c.execute(
                "SELECT a.account_id, a.pseudonym, a.role, a.created_at, a.last_login_at,"
                " a.password_changed_at, a.must_change_password, a.disabled,"
                " a.failed_attempts, a.locked_until, a.avatar_icon, a.avatar_color,"
                " EXISTS(SELECT 1 FROM account_identity i WHERE i.account_id = a.account_id)"
                "  AS identity_linked,"
                " (SELECT COUNT(*) FROM auth_sessions s WHERE s.account_id = a.account_id"
                "  AND s.expires_at > ?) AS active_sessions"
                " FROM account a ORDER BY a.role, a.pseudonym",
                (now,),
            ).fetchall()
        out = []
        for r in rows:
            locked = bool(r["locked_until"]) and not session_tokens.is_expired(r["locked_until"])
            out.append(
                {
                    "account_id": r["account_id"],
                    "pseudonym": r["pseudonym"],
                    "role": r["role"],
                    "created_at": r["created_at"],
                    "last_login_at": r["last_login_at"],
                    "password_changed_at": r["password_changed_at"],
                    "must_change_password": bool(r["must_change_password"]),
                    "disabled": bool(r["disabled"]),
                    "locked_until": r["locked_until"] if locked else None,
                    "failed_attempts": r["failed_attempts"],
                    "active_sessions": r["active_sessions"],
                    "avatar_icon": r["avatar_icon"],
                    "avatar_color": r["avatar_color"],
                    "google_linked": bool(r["identity_linked"]),
                }
            )
        return out

    def next_pseudonyms(self, prefix: str, count: int) -> list[str]:
        """The next `count` free pseudonyms of the form PREFIX-001, continuing the series.

        Numbering continues after the highest number in use, so SV-007 deleted
        by an erasure is never handed to somebody else: a pseudonym on an old
        paper record must keep pointing at one person.
        """
        if not PREFIX_PATTERN.match(prefix):
            raise ValueError("tiền tố chỉ gồm 1 đến 6 chữ cái không dấu")
        prefix = prefix.upper()
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$", re.IGNORECASE)
        with self._conn() as c:
            names = [r["pseudonym"] for r in c.execute("SELECT pseudonym FROM account")]
        used = [int(m.group(1)) for n in names if (m := pattern.match(n))]
        start = max(used, default=0) + 1
        width = max(3, len(str(start + count - 1)))
        return [f"{prefix}-{n:0{width}d}" for n in range(start, start + count)]

    def get_by_pseudonym(self, pseudonym: str) -> DbRow | None:
        with self._conn() as c:
            return c.execute(
                "SELECT * FROM account WHERE pseudonym=? AND disabled=0", (pseudonym,)
            ).fetchone()

    def pseudonyms(self, account_ids: list[str]) -> dict[str, str]:
        """Pseudonym of each account id, for screens that list other people's work."""
        ids = list(dict.fromkeys(account_ids))
        if not ids:
            return {}
        with self._conn() as c:
            rows = c.execute(
                f"SELECT account_id, pseudonym FROM account WHERE account_id IN"
                f" ({','.join('?' * len(ids))})",
                ids,
            ).fetchall()
        return {r["account_id"]: r["pseudonym"] for r in rows}

    # ---------- login ----------

    def login(self, pseudonym: str, raw_password: str, device: str | None = None) -> str | None:
        """Check the login credentials and return a session token, or None.

        Raises AccountLocked while the account is inside its lockout window. The
        caller must translate that exception into HTTP 429 per NFR-07.

        Returns None both when the account does not exist and when the password
        is wrong. Any hint that distinguishes the two cases would leak which
        accounts really exist.
        """
        row = self.get_by_pseudonym(pseudonym)

        # Clear the counter once the lock window has passed.
        #
        # Only a successful login reset it before, so after one lockout the
        # counter stayed at the maximum: a single wrong attempt, fifteen minutes
        # later, locked the account again. Anyone who knew a teacher's pseudonym
        # could hold it shut indefinitely with one request every fifteen minutes.
        if (
            row is not None
            and row["failed_attempts"] >= MAX_FAILED_ATTEMPTS
            and row["locked_until"]
            and session_tokens.is_expired(row["locked_until"])
        ):
            self._reset_failures(row["account_id"])
            row = self.get_by_pseudonym(pseudonym)
        if (
            row is not None
            and row["locked_until"]
            and not session_tokens.is_expired(row["locked_until"])
        ):
            raise AccountLocked(row["locked_until"])

        if row is None:
            # Same cost as a real check, so response time does not reveal
            # whether the pseudonym exists.
            passwords.waste_equivalent_time(raw_password)
            return None

        if not passwords.verify_password(raw_password, row["password_hash"]):
            self._record_failure(row["account_id"])
            return None

        self._reset_failures(row["account_id"])
        with self._conn() as c:
            c.execute(
                "UPDATE account SET last_login_at=? WHERE account_id=?", (_now(), row["account_id"])
            )
        return self._open_session(row["account_id"], device)

    def _record_failure(self, account_id: str) -> None:
        """Tang bo dem NGUYEN TU va khoa ngay trong cung cau lenh.

        Truoc day doc `failed_attempts` roi ghi `current + 1`. bcrypt mat khoang
        250 ms va endpoint chay tren threadpool, nen 20 lan thu sai song song deu
        doc cung mot gia tri: bo dem dung o 1 va tai khoan khong bao gio bi khoa.
        Trong SQLite, ve phai cua SET doc gia tri TRUOC khi cap nhat.
        """
        lock_at = (datetime.now(UTC) + timedelta(minutes=LOCK_MINUTES)).isoformat(
            timespec="seconds"
        )
        with self._conn() as c:
            c.execute(
                "UPDATE account SET failed_attempts = failed_attempts + 1,"
                " locked_until = CASE WHEN failed_attempts + 1 >= ? THEN ? ELSE locked_until END"
                " WHERE account_id = ?",
                (MAX_FAILED_ATTEMPTS, lock_at, account_id),
            )

    def _reset_failures(self, account_id: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE account SET failed_attempts=0, locked_until=NULL WHERE account_id=?",
                (account_id,),
            )

    def _open_session(
        self, account_id: str, device: str | None = None, method: str = "password"
    ) -> str:
        token = session_tokens.new_token()
        with self._conn() as c:
            c.execute(
                "INSERT INTO auth_sessions(token_hash,account_id,expires_at,created_at,"
                "device,method) VALUES(?,?,?,?,?,?)",
                (
                    session_tokens.hash_token(token),
                    account_id,
                    session_tokens.new_expiry(),
                    _now(),
                    device,
                    method,
                ),
            )
        return token

    # ---------- sessions ----------

    def account_for_token(self, token: str | None) -> Account | None:
        """Return the account matching the session token, or None if it is invalid."""
        if not token:
            return None
        with self._conn() as c:
            row = c.execute(
                "SELECT a.account_id, a.pseudonym, a.role, a.must_change_password, s.expires_at,"
                " a.avatar_icon, a.avatar_color, a.daily_goal_s"
                " FROM auth_sessions s JOIN account a ON a.account_id=s.account_id"
                " WHERE s.token_hash=? AND a.disabled=0",
                (session_tokens.hash_token(token),),
            ).fetchone()
        if row is None:
            return None
        # Doc ra AuthSession thay vi so sanh thang tren dict: luat "phien nay
        # con hieu luc hay khong" nam o mot cho duy nhat, va cho do la lop.
        session = AuthSession(account_id=row["account_id"], expires_at=row["expires_at"])
        if session_tokens.is_expired(session.expires_at):
            return None
        return Account(
            row["account_id"],
            row["pseudonym"],
            Role(row["role"]),
            must_change_password=bool(row["must_change_password"]),
            avatar_icon=row["avatar_icon"],
            avatar_color=row["avatar_color"],
            daily_goal_s=row["daily_goal_s"] or DEFAULT_DAILY_GOAL,
        )

    def logout(self, token: str | None) -> None:
        """Delete the session. AC-32.4: after logout the old cookie must return 401
        immediately."""
        if not token:
            return
        with self._conn() as c:
            c.execute(
                "DELETE FROM auth_sessions WHERE token_hash=?", (session_tokens.hash_token(token),)
            )

    def purge_expired_sessions(self) -> int:
        with self._conn() as c:
            cur = c.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_now(),))
            return cur.rowcount

    def revoke_sessions(self, account_id: str, keep_token: str | None = None) -> int:
        """End every session of an account except, optionally, the caller's own."""
        keep = session_tokens.hash_token(keep_token) if keep_token else ""
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM auth_sessions WHERE account_id=? AND token_hash<>?",
                (account_id, keep),
            )
            return cur.rowcount

    # ---------- passwords and account state (D028) ----------

    def change_password(
        self, account_id: str, current: str, new: str, keep_token: str | None = None
    ) -> int:
        """Replace the password after checking the current one. Returns sessions ended.

        A wrong current password counts as a failed login: otherwise a stolen
        session would be an unlimited, unthrottled way to guess the password it
        is about to replace. Every other session ends, because the reason to
        change a password is often that somebody else knows it.
        """
        row = self.get(account_id)
        if row is None or row["disabled"]:
            raise WrongPassword(account_id)
        if row["locked_until"] and not session_tokens.is_expired(row["locked_until"]):
            raise AccountLocked(row["locked_until"])
        if not passwords.verify_password(current, row["password_hash"]):
            self._record_failure(account_id)
            raise WrongPassword(account_id)
        passwords.check_new_password(new, row["pseudonym"], current)
        with self._conn() as c:
            c.execute(
                "UPDATE account SET password_hash=?, must_change_password=0,"
                " password_changed_at=?, failed_attempts=0, locked_until=NULL"
                " WHERE account_id=?",
                (passwords.hash_password(new), _now(), account_id),
            )
        return self.revoke_sessions(account_id, keep_token)

    def set_temporary_password(self, account_id: str) -> str:
        """Give an account a new one-time password and return it, in clear, once.

        The account must choose its own password at the next login, its lockout
        is lifted and every session ends: whoever held the old password is out.
        """
        temporary = passwords.temporary_password()
        with self._conn() as c:
            cur = c.execute(
                "UPDATE account SET password_hash=?, must_change_password=1,"
                " failed_attempts=0, locked_until=NULL WHERE account_id=?",
                (passwords.hash_password(temporary), account_id),
            )
        if cur.rowcount == 0:
            raise KeyError(account_id)
        self.revoke_sessions(account_id)
        return temporary

    def set_disabled(self, account_id: str, disabled: bool) -> None:
        """Turn an account off or on. Turning it off ends its sessions at once."""
        with self._conn() as c:
            cur = c.execute(
                "UPDATE account SET disabled=? WHERE account_id=?", (int(disabled), account_id)
            )
        if cur.rowcount == 0:
            raise KeyError(account_id)
        if disabled:
            self.revoke_sessions(account_id)

    def unlock(self, account_id: str) -> None:
        """Lift a lockout before its fifteen minutes are up."""
        if self.get(account_id) is None:
            raise KeyError(account_id)
        self._reset_failures(account_id)

    # ---------- sessions a person can see (D029) ----------

    def sessions(self, account_id: str) -> list[dict]:
        """Open sessions of one account, newest first, each with a short id.

        The id is the first sixteen hex characters of the token's hash: enough
        to tell sessions apart and to end one, useless for opening one.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT token_hash, created_at, expires_at, device, method FROM auth_sessions"
                " WHERE account_id=? AND expires_at > ? ORDER BY created_at DESC",
                (account_id, _now()),
            ).fetchall()
        return [
            {
                "session_id": r["token_hash"][:16],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "device": r["device"],
                "method": r["method"] or "password",
            }
            for r in rows
        ]

    def revoke_session(self, account_id: str, session_id: str) -> bool:
        """End one session of this account, by its short id. False if there is none."""
        if not re.fullmatch(r"[0-9a-f]{16}", session_id or ""):
            return False
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM auth_sessions WHERE account_id=? AND substr(token_hash,1,16)=?",
                (account_id, session_id),
            )
            return cur.rowcount > 0

    # ---------- profile and role (D029) ----------

    def update_profile(
        self,
        account_id: str,
        avatar_icon: str | None = None,
        avatar_color: str | None = None,
        daily_goal_s: int | None = None,
    ) -> None:
        """Change the parts of the profile that were given; refuse anything off the lists."""
        changes: dict[str, object] = {}
        if avatar_icon is not None:
            if avatar_icon not in AVATAR_ICONS:
                raise ValueError("biểu tượng ảnh đại diện không có trong danh sách")
            changes["avatar_icon"] = avatar_icon
        if avatar_color is not None:
            if avatar_color not in AVATAR_COLORS:
                raise ValueError("màu ảnh đại diện không có trong danh sách")
            changes["avatar_color"] = avatar_color
        if daily_goal_s is not None:
            if daily_goal_s not in DAILY_GOALS:
                raise ValueError("mục tiêu mỗi ngày phải là 1, 2, 3, 5 hoặc 10 phút")
            changes["daily_goal_s"] = daily_goal_s
        if not changes:
            return
        assignments = ", ".join(f"{k}=?" for k in changes)
        with self._conn() as c:
            c.execute(
                f"UPDATE account SET {assignments} WHERE account_id=?",
                (*changes.values(), account_id),
            )

    def set_role(self, account_id: str, role: Role) -> str:
        """Give an account another role; returns the role it had."""
        row = self.get(account_id)
        if row is None:
            raise KeyError(account_id)
        with self._conn() as c:
            c.execute("UPDATE account SET role=? WHERE account_id=?", (role.value, account_id))
        return row["role"]

    # ---------- outside identities (D029) ----------

    def account_by_identity(self, provider: str, subject_hash: str) -> DbRow | None:
        with self._conn() as c:
            return c.execute(
                "SELECT a.* FROM account_identity i JOIN account a ON a.account_id = i.account_id"
                " WHERE i.provider=? AND i.subject_hash=?",
                (provider, subject_hash),
            ).fetchone()

    def identity(self, account_id: str, provider: str) -> DbRow | None:
        with self._conn() as c:
            return c.execute(
                "SELECT provider, linked_at FROM account_identity"
                " WHERE account_id=? AND provider=?",
                (account_id, provider),
            ).fetchone()

    def link_identity(self, account_id: str, provider: str, subject_hash: str) -> None:
        """Link an outside identity to this account, replacing any earlier one.

        Raises IdentityTaken when the identity already belongs to another
        account: one Google account opening two pseudonyms would let one person
        speak as two participants.
        """
        owner = self.account_by_identity(provider, subject_hash)
        if owner is not None and owner["account_id"] != account_id:
            raise IdentityTaken(provider)
        with self._conn() as c:
            c.execute(
                "DELETE FROM account_identity WHERE account_id=? AND provider=?",
                (account_id, provider),
            )
            c.execute(
                "INSERT OR IGNORE INTO account_identity(provider,subject_hash,account_id,linked_at)"
                " VALUES(?,?,?,?)",
                (provider, subject_hash, account_id, _now()),
            )

    def count_identities(self, provider: str) -> int:
        with self._conn() as c:
            return c.execute(
                "SELECT COUNT(*) FROM account_identity WHERE provider=?", (provider,)
            ).fetchone()[0]

    def unlink_identity(self, account_id: str, provider: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM account_identity WHERE account_id=? AND provider=?",
                (account_id, provider),
            )
            return cur.rowcount > 0

    def login_with_identity(
        self, provider: str, subject_hash: str, device: str | None = None
    ) -> tuple[str, DbRow] | None:
        """Open a session for the account linked to this identity, or None.

        No password is involved, so the password lockout does not apply: it
        exists to stop guessing, and there is nothing to guess here. A disabled
        account stays shut.
        """
        row = self.account_by_identity(provider, subject_hash)
        if row is None or row["disabled"]:
            return None
        with self._conn() as c:
            c.execute(
                "UPDATE account SET last_login_at=? WHERE account_id=?", (_now(), row["account_id"])
            )
        return self._open_session(row["account_id"], device, method=provider), row
