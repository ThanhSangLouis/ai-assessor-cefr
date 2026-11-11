"""Persistence for accounts and login sessions. Implements FR-32 and NFR-07.

Kept separate from Repository so that scoring logic and authentication are not
mixed together, but pointed at the SAME database so there is only one
connection target to manage.

An account is its email (how the person signs in, D071), its full name (what a
teacher reads) and its role. Nothing else of the person is kept: no student ID,
no phone, no photo.
"""

from __future__ import annotations

import os
import re
import secrets
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from aicefr.auth import contact, passwords
from aicefr.auth import sessions as session_tokens
from aicefr.contracts import AuthSession
from aicefr.storage.db import (
    IntegrityError,
    MongoStore,
    ensure_indexes,
    ensure_system,
    setting_once,
)
from aicefr.storage.db import now_iso as _now

# NFR-07: lock the account for 15 minutes after 5 consecutive failed logins;
# the 6th attempt returns HTTP 429.
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15

# account.identities (D029): outside identities (Google) linked to the account
# by its owner, part of the account's document (D060). Only a one-way hash of
# the provider's subject identifier is kept: no email, no name, no photo. One
# identity per account per provider (kept so by `link_identity`), one account
# per identity (a unique index over the accounts that have one). The secrets
# this deployment signs with (D036) are made once and kept in `system`, so
# every worker and every restart agree. Not a person's data; never shown.
INDEXES = {
    "account": [
        (("account_id",), True),
        # One account per email: the email is how the account is found.
        (("email",), True),
        (
            ("identities.provider", "identities.subject_hash"),
            True,
            {"identities.subject_hash": {"$exists": True}},
        ),
    ],
    "session": [(("token_hash",), True), (("account_id",), False)],
}
SETTING = "identity."  # this part's keys in `system`
SESSION_KEY = "session_jwt"  # the key session JWTs are signed with (D091)

# Every field of an account document, so a reader gets None for one never set,
# as it got NULL from a column.
ACCOUNT_FIELDS = (
    "account_id",
    "password_hash",
    "role",
    "failed_attempts",
    "locked_until",
    "disabled",
    "created_at",
    "must_change_password",
    "last_login_at",
    "password_changed_at",
    "avatar_icon",
    "avatar_color",
    "daily_goal_s",
    "identities",
    "email",
    "email_verified",
    "full_name",
    "email_reminders",
)


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
# D079: a code sent by email -- six digits, ten minutes, five tries, one a minute.
EMAIL_CODE_MINUTES = 10
EMAIL_CODE_TRIES = 5
EMAIL_CODE_GAP_S = 60
EMAIL_CODE_PURPOSES = ("reset", "verify")

DAILY_GOALS = (60, 120, 180, 300, 600)
DEFAULT_DAILY_GOAL = 180


@dataclass(frozen=True)
class Account:
    account_id: str
    email: str
    role: Role
    # Set on an account created or reset by an administrator (D028): the
    # password on the printed slip works for one thing only, choosing a new one.
    must_change_password: bool = False
    # D029 profile, read with the session so every page can draw the avatar.
    avatar_icon: str | None = None
    avatar_color: str | None = None
    daily_goal_s: int = DEFAULT_DAILY_GOAL
    # D060: the providers of the outside identities linked to the account.
    identities: tuple[str, ...] = ()
    # D071: what a teacher reads. None until the owner gives one.
    full_name: str | None = None

    @property
    def is_staff(self) -> bool:
        return self.role in (Role.TEACHER, Role.ADMIN)

    @property
    def display_name(self) -> str:
        return self.full_name or self.email


class AccountLocked(Exception):
    """The account is temporarily locked after too many failed logins."""


class WrongPassword(Exception):
    """The current password given to a password change does not match."""


class IdentityTaken(Exception):
    """The outside identity is already linked to a different account."""


class EmailTaken(Exception):
    """Another account already signs in with this email (D071)."""


def _account(found) -> dict | None:
    """An account document with every field, `_id` left out."""
    if found is None:
        return None
    return {name: found.get(name) for name in ACCOUNT_FIELDS}


class AuthRepository(MongoStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        self._secrets: dict[str, bytes] = {}
        ensure_indexes(self.db, INDEXES, "auth")
        ensure_system(self.db)

    def secret(self, name: str) -> bytes:
        """A 32-byte key of this deployment for `name`, made the first time it is asked for.

        Two processes asking at once agree: the first insert wins and both read
        it back.
        """
        if name not in self._secrets:
            kept, _mine = setting_once(self.db, SETTING + "secret." + name, os.urandom(32).hex())
            self._secrets[name] = bytes.fromhex(kept)
        return self._secrets[name]

    # ---------- accounts ----------

    @staticmethod
    def _new_account(
        aid: str, email: str, password_hash: str, role: Role, must_change: bool, now: str
    ) -> dict:
        return {
            "account_id": aid,
            "email": email,
            "password_hash": password_hash,
            "role": role.value,
            "failed_attempts": 0,
            "locked_until": None,
            "disabled": 0,
            "created_at": now,
            "must_change_password": int(must_change),
            "last_login_at": None,
            "password_changed_at": None,
            "avatar_icon": None,
            "avatar_color": None,
            "daily_goal_s": DEFAULT_DAILY_GOAL,
            "identities": [],
            # Verified once Google, or a code sent to it, has vouched for it.
            "email_verified": 0,
            "full_name": None,
        }

    def create_account(
        self,
        email: str,
        raw_password: str,
        role: Role,
        must_change_password: bool = False,
        full_name: str | None = None,
    ) -> str:
        """Create a new account and return its account_id. ValueError, EmailTaken.

        Made by an administrator (the command line, the seed), who vouches for
        the address: it counts as verified, so the account has its free runs (D103).
        """
        email = contact.normalize_email(email)
        doc = self._new_account(
            uuid.uuid4().hex[:12],
            email,
            passwords.hash_password(raw_password),
            role,
            must_change_password,
            _now(),
        )
        doc["email_verified"] = 1
        if full_name:
            doc["full_name"] = contact.normalize_name(full_name)
        try:
            self.col("account").insert_one(doc)
        except IntegrityError as e:
            raise EmailTaken(email) from e
        return doc["account_id"]

    def create_with_temporary_passwords(
        self, emails: list[str], role: Role
    ) -> list[tuple[str, str, str]]:
        """Create accounts that must choose a password at first login (D028).

        Returns (account_id, email, temporary password) per account; the
        passwords exist in clear only in this return value. All or nothing: one
        email already taken and no account is created, so a half-made class
        list never has to be untangled by hand. The administrator typed the
        addresses, so they count as verified, as in `create_account`.

        bcrypt at cost 12 takes about a quarter of a second per password and
        releases the GIL, so a class of ninety is hashed on a few threads
        instead of keeping the administrator waiting twenty seconds.
        """
        names = [contact.normalize_email(n) for n in emails]
        if len(set(names)) != len(names):
            raise ValueError("danh sách email bị trùng")
        accounts = self.col("account")
        taken = list(accounts.find({"email": {"$in": names}}, {"email": 1}))
        if taken:
            raise ValueError(
                "email đã có tài khoản: " + ", ".join(sorted(r["email"] for r in taken))
            )
        temporaries = [passwords.temporary_password() for _ in names]
        workers = max(1, min(8, os.cpu_count() or 1, len(names)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            hashes = list(pool.map(passwords.hash_password, temporaries))
        created = [(uuid.uuid4().hex[:12], n, t) for n, t in zip(names, temporaries, strict=True)]
        now = _now()
        documents = [
            {**self._new_account(aid, name, h, role, True, now), "email_verified": 1}
            for (aid, name, _), h in zip(created, hashes, strict=True)
        ]
        try:
            accounts.insert_many(documents, ordered=True)
        except IntegrityError as e:
            # Taken between the check and the insert: undo the ones that went in.
            accounts.delete_many({"account_id": {"$in": [d["account_id"] for d in documents]}})
            raise ValueError("email vừa được người khác dùng, hãy thử lại") from e
        return created

    def get(self, account_id: str) -> dict | None:
        """One account by id, disabled or not: the administrator's view."""
        return _account(self.col("account").find_one({"account_id": account_id}))

    def count_role(self, role: Role) -> int:
        """Enabled accounts of one role: the seats a plan counts (D033)."""
        return self.col("account").count_documents({"role": role.value, "disabled": 0})

    def list_accounts(self) -> list[dict]:
        """Every account with what an administrator needs to look after it.

        No password hash leaves this method. `active_sessions` counts sessions
        that have not expired, so "signed in on two devices" is visible.
        """
        now = _now()
        rows = list(self.col("account").find().sort([("role", 1), ("email", 1)]))
        linked = {r["account_id"] for r in rows if r.get("identities")}
        active: dict[str, int] = {}
        for s in self.col("session").find({"expires_at": {"$gt": now}}, {"account_id": 1}):
            active[s["account_id"]] = active.get(s["account_id"], 0) + 1
        out = []
        for found in rows:
            r = _account(found)
            locked = bool(r["locked_until"]) and not session_tokens.is_expired(r["locked_until"])
            out.append(
                {
                    "account_id": r["account_id"],
                    "role": r["role"],
                    "created_at": r["created_at"],
                    "last_login_at": r["last_login_at"],
                    "password_changed_at": r["password_changed_at"],
                    "must_change_password": bool(r["must_change_password"]),
                    "disabled": bool(r["disabled"]),
                    "locked_until": r["locked_until"] if locked else None,
                    "failed_attempts": r["failed_attempts"],
                    "active_sessions": active.get(r["account_id"], 0),
                    "avatar_icon": r["avatar_icon"],
                    "avatar_color": r["avatar_color"],
                    "google_linked": r["account_id"] in linked,
                    "email": r["email"],
                    "email_verified": bool(r["email_verified"]),
                    "full_name": r["full_name"],
                }
            )
        return out

    def get_by_email(self, email: str) -> dict | None:
        """The enabled account that signs in with this email (D071), or None."""
        try:
            email = contact.normalize_email(email)
        except ValueError:
            return None
        return _account(self.col("account").find_one({"email": email, "disabled": 0}))

    def display_names(self, account_ids: list[str]) -> dict[str, str]:
        """What a teacher reads for each account: the full name, else the email (D071)."""
        ids = list(dict.fromkeys(account_ids))
        if not ids:
            return {}
        rows = self.col("account").find(
            {"account_id": {"$in": ids}}, {"account_id": 1, "email": 1, "full_name": 1}
        )
        return {r["account_id"]: r.get("full_name") or r["email"] for r in rows}

    def set_contact(
        self, account_id: str, email: str | None = None, full_name: str | None = None
    ) -> dict:
        """Set the email and/or full name; returns the account. ValueError, EmailTaken.

        A changed email is no longer one Google vouched for, so it loses its
        verified mark until a Google sign-in with that address restores it.
        SEC-01: in the same update every code sent by email (verify and reset)
        is dropped: it went to the old mailbox and proves nothing about the new.
        """
        row = self.get(account_id)
        if row is None:
            raise KeyError(account_id)
        changes: dict[str, object] = {}
        update: dict[str, dict] = {}
        if full_name is not None:
            changes["full_name"] = contact.normalize_name(full_name)
        if email is not None:
            email = contact.normalize_email(email)
            if email != row["email"]:
                other = self.col("account").find_one({"email": email}, {"account_id": 1})
                if other is not None and other["account_id"] != account_id:
                    raise EmailTaken(email)
                changes.update(email=email, email_verified=0)
                update["$unset"] = {"email_codes": ""}
        if changes:
            update["$set"] = changes
            try:
                self.col("account").update_one({"account_id": account_id}, update)
            except IntegrityError as e:
                raise EmailTaken(email) from e
        return self.get(account_id)

    # ---------- login ----------

    def login(self, identifier: str, raw_password: str, device: str | None = None) -> str | None:
        """Check the login credentials and return a session token, or None.

        Raises AccountLocked while the account is inside its lockout window. The
        caller must translate that exception into HTTP 429 per NFR-07.

        Returns None both when the account does not exist and when the password
        is wrong. Any hint that distinguishes the two cases would leak which
        accounts really exist.
        """
        row = self._unlocked_row(identifier)

        if row is None:
            # Same cost as a real check, so response time does not reveal
            # whether the email has an account.
            passwords.waste_equivalent_time(raw_password)
            return None

        if not passwords.verify_password(raw_password, row["password_hash"]):
            self._record_failure(row["account_id"])
            return None

        self._reset_failures(row["account_id"])
        self.col("account").update_one(
            {"account_id": row["account_id"]}, {"$set": {"last_login_at": _now()}}
        )
        return self._open_session(row["account_id"], device)

    def _unlocked_row(self, identifier: str) -> dict | None:
        """The account to check a secret against, or None; AccountLocked inside a lockout.

        Shared by the password and the code sent by email (D079): both are
        guesses at a secret, so both count towards, and are stopped by, one lockout.
        """
        return self._check_lock(self.get_by_email(identifier))

    def _check_lock(self, row: dict | None) -> dict | None:
        """The row with an expired lockout cleared; AccountLocked inside a live one."""
        # Clear the counter once the lock window has passed.
        #
        # Only a successful login reset it before, so after one lockout the
        # counter stayed at the maximum: a single wrong attempt, fifteen minutes
        # later, locked the account again. Anyone who knew a teacher's email
        # could hold it shut indefinitely with one request every fifteen minutes.
        if (
            row is not None
            and row["failed_attempts"] >= MAX_FAILED_ATTEMPTS
            and row["locked_until"]
            and session_tokens.is_expired(row["locked_until"])
        ):
            self._reset_failures(row["account_id"])
            row = self.get(row["account_id"])
        if (
            row is not None
            and row["locked_until"]
            and not session_tokens.is_expired(row["locked_until"])
        ):
            raise AccountLocked(row["locked_until"])
        return row

    def reauthenticate(self, account_id: str, raw_password: str) -> None:
        """Check the password of a signed-in account before a sensitive change (SEC-03).

        Raises WrongPassword or AccountLocked; returns None when the password is
        right. Shares the login's counter and lockout (NFR-07): a session must
        not be an unthrottled way to guess the password, so a wrong one counts
        as a failed login and, while the account is locked, even the right one
        is refused. The counter goes up with an atomic $inc, so guesses sent at
        once all count; a right password resets it only if no lock was set
        meanwhile, so a guess racing the lock does not slip through.
        """
        row = self.get(account_id)
        if row is None or row["disabled"]:
            passwords.waste_equivalent_time(raw_password)
            raise WrongPassword(account_id)
        self._check_lock(row)
        if not passwords.verify_password(raw_password, row["password_hash"]):
            self._record_failure(account_id)
            raise WrongPassword(account_id)
        cleared = self.col("account").update_one(
            {
                "account_id": account_id,
                "$or": [{"locked_until": None}, {"locked_until": {"$lte": _now()}}],
            },
            {"$set": {"failed_attempts": 0, "locked_until": None}},
        )
        if cleared.matched_count == 0:
            raise AccountLocked((self.get(account_id) or {}).get("locked_until"))

    def _record_failure(self, account_id: str) -> None:
        """Tang bo dem NGUYEN TU va khoa ngay khi cham nguong.

        Truoc day doc `failed_attempts` roi ghi `current + 1`. bcrypt mat khoang
        250 ms va endpoint chay tren threadpool, nen 20 lan thu sai song song deu
        doc cung mot gia tri: bo dem dung o 1 va tai khoan khong bao gio bi khoa.
        Gio $inc la mot thao tac nguyen tu, va lan dem cham nguong dat khoa bang
        mot cap nhat co dieu kien tren chinh gia tri vua tang.
        """
        lock_at = (datetime.now(UTC) + timedelta(minutes=LOCK_MINUTES)).isoformat(
            timespec="seconds"
        )
        accounts = self.col("account")
        accounts.update_one({"account_id": account_id}, {"$inc": {"failed_attempts": 1}})
        accounts.update_one(
            {"account_id": account_id, "failed_attempts": {"$gte": MAX_FAILED_ATTEMPTS}},
            {"$set": {"locked_until": lock_at}},
        )

    def _reset_failures(self, account_id: str) -> None:
        self.col("account").update_one(
            {"account_id": account_id}, {"$set": {"failed_attempts": 0, "locked_until": None}}
        )

    def _open_session(
        self, account_id: str, device: str | None = None, method: str = "password"
    ) -> str:
        sid = session_tokens.new_token()
        expires_at = session_tokens.new_expiry()
        self.col("session").insert_one(
            {
                "token_hash": session_tokens.hash_token(sid),
                "account_id": account_id,
                "expires_at": expires_at,
                "created_at": _now(),
                "device": device,
                "method": method,
            }
        )
        return session_tokens.encode_jwt(self.secret(SESSION_KEY), account_id, sid, expires_at)

    # ---------- sessions ----------

    def _claims(self, token: str | None) -> dict | None:
        return session_tokens.decode_jwt(self.secret(SESSION_KEY), token)

    def session_hash(self, token: str | None) -> str:
        """The stored key of the session a token stands for, or "" for no valid token."""
        claims = self._claims(token)
        return session_tokens.hash_token(claims["sid"]) if claims else ""

    def account_for_token(self, token: str | None) -> Account | None:
        """Return the account matching the session token, or None if it is invalid."""
        claims = self._claims(token)
        if claims is None:
            return None
        found = self.col("session").find_one(
            {"token_hash": session_tokens.hash_token(claims["sid"]), "account_id": claims["sub"]}
        )
        if found is None:
            return None
        row = _account(
            self.col("account").find_one({"account_id": found["account_id"], "disabled": 0})
        )
        if row is None:
            return None
        # Doc ra AuthSession thay vi so sanh thang tren dict: luat "phien nay
        # con hieu luc hay khong" nam o mot cho duy nhat, va cho do la lop.
        session = AuthSession(account_id=row["account_id"], expires_at=found["expires_at"])
        if session_tokens.is_expired(session.expires_at):
            return None
        return Account(
            row["account_id"],
            row["email"],
            Role(row["role"]),
            must_change_password=bool(row["must_change_password"]),
            avatar_icon=row["avatar_icon"],
            avatar_color=row["avatar_color"],
            daily_goal_s=row["daily_goal_s"] or DEFAULT_DAILY_GOAL,
            identities=tuple(i["provider"] for i in row["identities"] or []),
            full_name=row["full_name"],
        )

    def logout(self, token: str | None) -> None:
        """Delete the session. AC-32.4: after logout the old cookie must return 401
        immediately."""
        key = self.session_hash(token)
        if key:
            self.col("session").delete_one({"token_hash": key})

    def purge_expired_sessions(self) -> int:
        return self.col("session").delete_many({"expires_at": {"$lte": _now()}}).deleted_count

    def revoke_sessions(self, account_id: str, keep_token: str | None = None) -> int:
        """End every session of an account except, optionally, the caller's own."""
        keep = self.session_hash(keep_token)
        return (
            self.col("session")
            .delete_many({"account_id": account_id, "token_hash": {"$ne": keep}})
            .deleted_count
        )

    def delete_account(self, account_id: str) -> bool:
        """Remove the account and every session of it, for good (D101).

        The email, the name, the password hash, the linked Google identity, the
        email codes and the recovery code all live on the account document, so
        nothing of the person is left here. The audit log keeps only the account id.
        """
        self.col("session").delete_many({"account_id": account_id})
        return bool(self.col("account").delete_one({"account_id": account_id}).deleted_count)

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
        self.reauthenticate(account_id, current)
        row = self.get(account_id)
        passwords.check_new_password(new, row["email"], current)
        self.col("account").update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "password_hash": passwords.hash_password(new),
                    "must_change_password": 0,
                    "password_changed_at": _now(),
                    "failed_attempts": 0,
                    "locked_until": None,
                }
            },
        )
        return self.revoke_sessions(account_id, keep_token)

    def set_temporary_password(self, account_id: str) -> str:
        """Give an account a new one-time password and return it, in clear, once.

        The account must choose its own password at the next login, its lockout
        is lifted and every session ends: whoever held the old password is out.
        """
        temporary = passwords.temporary_password()
        done = self.col("account").update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "password_hash": passwords.hash_password(temporary),
                    "must_change_password": 1,
                    "failed_attempts": 0,
                    "locked_until": None,
                }
            },
        )
        if done.matched_count == 0:
            raise KeyError(account_id)
        self.revoke_sessions(account_id)
        return temporary

    # ---------- self sign-up (D065) ----------

    def signup(
        self, email: str, full_name: str, raw_password: str, device: str | None = None
    ) -> tuple[str, str]:
        """Create a student account with an email, a name and a password; sign it in.

        Returns (account_id, session token). Raises ValueError, worded for the
        person, when the email, the name or the password will not do, and
        EmailTaken when the email already has an account.
        """
        email = contact.normalize_email(email)
        full_name = contact.normalize_name(full_name)
        if self.col("account").find_one({"email": email}, {"_id": 1}) is not None:
            raise EmailTaken(email)
        passwords.check_new_password(raw_password, email)
        now = _now()
        aid = uuid.uuid4().hex[:12]
        doc = self._new_account(
            aid, email, passwords.hash_password(raw_password), Role.STUDENT, False, now
        )
        doc.update(password_changed_at=now, last_login_at=now, full_name=full_name)
        try:
            self.col("account").insert_one(doc)
        except IntegrityError as e:
            raise EmailTaken(email) from e  # the email was taken in between
        return aid, self._open_session(aid, device)

    # ---------- email codes, verification, reminders (D079) ----------

    def issue_email_code(self, account_id: str, purpose: str, to: str | None = None) -> str | None:
        """A new six-digit code for `purpose`, kept hashed; None within a minute of the last.

        A new code replaces the one before, so only the latest email works. The
        code is bound to the address it goes to (SEC-01): it spends only while
        that is still the account's email. `to` is the address the caller is
        about to send it to; when it is no longer the account's -- the address
        changed after the caller read it -- no code is issued (None), so none
        goes to a mailbox the account has left.
        """
        if purpose not in EMAIL_CODE_PURPOSES:
            raise ValueError(purpose)
        row = self.col("account").find_one(
            {"account_id": account_id}, {"email_codes": 1, "email": 1}
        )
        if not (row or {}).get("email"):
            raise ValueError("tài khoản chưa có email")
        if to is not None and row["email"] != to:
            return None
        last = (row.get("email_codes") or {}).get(purpose)
        now = datetime.now(UTC)
        if last and (now - datetime.fromisoformat(last["sent_at"])).total_seconds() < (
            EMAIL_CODE_GAP_S
        ):
            return None
        code = f"{secrets.randbelow(10**6):06d}"
        # On the address just read: a change racing this one leaves no code bound
        # to an address it was not sent to.
        issued = self.col("account").update_one(
            {"account_id": account_id, "email": row["email"]},
            {
                "$set": {
                    f"email_codes.{purpose}": {
                        "hash": passwords.hash_password(code),
                        "email": row["email"],
                        "sent_at": now.isoformat(timespec="seconds"),
                        "expires_at": (now + timedelta(minutes=EMAIL_CODE_MINUTES)).isoformat(
                            timespec="seconds"
                        ),
                        "tries": 0,
                    }
                }
            },
        )
        return code if issued.matched_count == 1 else None

    def _spend_email_code(
        self,
        account_id: str,
        purpose: str,
        code: str,
        then: Callable[[], dict] | None = None,
    ) -> bool:
        """Whether `code` is the live one for `purpose`; a right one is spent, a wrong counts.

        SEC-01: a code is live only while the account's email is still the
        address it was sent to; a code issued before that rule, bound to no
        address, is dead. `then` gives the fields to set when the code is right;
        they are written in the same conditional update that spends it -- code,
        address and expiry checked by the database, not read then written -- so
        no change of address can slip between the check and the effect.
        """
        row = self.col("account").find_one(
            {"account_id": account_id}, {"email_codes": 1, "email": 1}
        )
        held = ((row or {}).get("email_codes") or {}).get(purpose)
        typed = "".join(ch for ch in str(code) if ch.isdigit())
        if (
            not held
            or held["tries"] >= EMAIL_CODE_TRIES
            or session_tokens.is_expired(held["expires_at"])
            or not held.get("email")
            or held["email"] != row.get("email")
        ):
            passwords.waste_equivalent_time(typed)
            return False
        if not passwords.verify_password(typed, held["hash"]):
            self.col("account").update_one(
                {"account_id": account_id, f"email_codes.{purpose}.hash": held["hash"]},
                {"$inc": {f"email_codes.{purpose}.tries": 1}},
            )
            return False
        update: dict[str, dict] = {"$unset": {f"email_codes.{purpose}": ""}}
        if then is not None:
            update["$set"] = then()
        # Conditional on the hash just checked: of two requests racing, one spends
        # it; and on the address and the clock, so a code moved away from or
        # gone stale meanwhile spends nothing.
        done = self.col("account").update_one(
            {
                "account_id": account_id,
                "email": held["email"],
                f"email_codes.{purpose}.hash": held["hash"],
                f"email_codes.{purpose}.email": held["email"],
                f"email_codes.{purpose}.tries": {"$lt": EMAIL_CODE_TRIES},
                f"email_codes.{purpose}.expires_at": {"$gt": _now()},
            },
            update,
        )
        return done.modified_count == 1

    def reset_with_email_code(
        self, email: str, code: str, new_password: str, device: str | None = None
    ) -> tuple[str, dict] | None:
        """Replace a forgotten password with a code sent to the account's email; sign in.

        None for an unknown email, a disabled account or a wrong, used or late
        code, all alike. Receiving the code shows the mailbox is theirs, so the
        email counts as verified from now on. Every other session ends.
        """
        row = self._unlocked_row(email)
        passwords.check_new_password(new_password, email)
        if row is None or row["disabled"]:
            passwords.waste_equivalent_time(code)
            return None
        now = _now()
        if not self._spend_email_code(
            row["account_id"],
            "reset",
            code,
            then=lambda: {
                "password_hash": passwords.hash_password(new_password),
                "must_change_password": 0,
                "password_changed_at": now,
                "last_login_at": now,
                "failed_attempts": 0,
                "locked_until": None,
                "email_verified": 1,
            },
        ):
            self._record_failure(row["account_id"])
            return None
        self.revoke_sessions(row["account_id"])
        token = self._open_session(row["account_id"], device, method="email_code")
        return token, self.get(row["account_id"])

    def verify_email(self, account_id: str, code: str) -> bool:
        """Mark the account's email verified with the code sent to that same address."""
        return self._spend_email_code(
            account_id, "verify", code, then=lambda: {"email_verified": 1}
        )

    def set_email_reminders(self, account_id: str, on: bool) -> None:
        self.col("account").update_one(
            {"account_id": account_id}, {"$set": {"email_reminders": int(on)}}
        )

    def reminder_candidates(self, day: str) -> list[dict]:
        """Learners a study reminder may go to today: verified email, reminders on, none sent."""
        rows = self.col("account").find(
            {
                "role": Role.STUDENT.value,
                "disabled": 0,
                "email_verified": 1,
                "email_reminders": {"$ne": 0},
                "reminder_sent_on": {"$ne": day},
            },
            {"account_id": 1, "email": 1, "full_name": 1, "daily_goal_s": 1},
        )
        return [dict(r) for r in rows]

    def claim_reminder(self, account_id: str, day: str) -> bool:
        """Take today's reminder for this learner; False when another process took it."""
        done = self.col("account").update_one(
            {"account_id": account_id, "reminder_sent_on": {"$ne": day}},
            {"$set": {"reminder_sent_on": day}},
        )
        return done.modified_count == 1

    def set_disabled(self, account_id: str, disabled: bool) -> None:
        """Turn an account off or on. Turning it off ends its sessions at once."""
        done = self.col("account").update_one(
            {"account_id": account_id}, {"$set": {"disabled": int(disabled)}}
        )
        if done.matched_count == 0:
            raise KeyError(account_id)
        if disabled:
            self.revoke_sessions(account_id)

    def unlock(self, account_id: str) -> None:
        """Lift a lockout before its fifteen minutes are up."""
        if self.get(account_id) is None:
            raise KeyError(account_id)
        self._reset_failures(account_id)

    def unlock_email(self, email: str) -> bool:
        """Lift the lockout of the account with this email; False when there is none."""
        try:
            email = contact.normalize_email(email)
        except ValueError:
            return False
        done = self.col("account").update_one(
            {"email": email}, {"$set": {"failed_attempts": 0, "locked_until": None}}
        )
        return done.matched_count > 0

    # ---------- sessions a person can see (D029) ----------

    def sessions(self, account_id: str) -> list[dict]:
        """Open sessions of one account, newest first, each with a short id.

        The id is the first sixteen hex characters of the token's hash: enough
        to tell sessions apart and to end one, useless for opening one.
        """
        rows = (
            self.col("session")
            .find({"account_id": account_id, "expires_at": {"$gt": _now()}})
            .sort([("created_at", -1), ("_id", -1)])
        )
        return [
            {
                "session_id": r["token_hash"][:16],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
                "device": r.get("device"),
                "method": r.get("method") or "password",
            }
            for r in rows
        ]

    def revoke_session(self, account_id: str, session_id: str) -> bool:
        """End one session of this account, by its short id. False if there is none."""
        if not re.fullmatch(r"[0-9a-f]{16}", session_id or ""):
            return False
        # The short id is hex only, so it is safe inside an anchored pattern.
        done = self.col("session").delete_many(
            {"account_id": account_id, "token_hash": {"$regex": f"^{session_id}"}}
        )
        return done.deleted_count > 0

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
        self.col("account").update_one({"account_id": account_id}, {"$set": changes})

    def set_role(self, account_id: str, role: Role) -> str:
        """Give an account another role; returns the role it had."""
        row = self.get(account_id)
        if row is None:
            raise KeyError(account_id)
        self.col("account").update_one({"account_id": account_id}, {"$set": {"role": role.value}})
        return row["role"]

    # ---------- outside identities (D029) ----------

    def account_by_identity(self, provider: str, subject_hash: str) -> dict | None:
        return _account(
            self.col("account").find_one(
                {"identities": {"$elemMatch": {"provider": provider, "subject_hash": subject_hash}}}
            )
        )

    def identity(self, account_id: str, provider: str) -> dict | None:
        row = self.col("account").find_one({"account_id": account_id}, {"identities": 1})
        for link in (row or {}).get("identities") or []:
            if link["provider"] == provider:
                return {"provider": link["provider"], "linked_at": link["linked_at"]}
        return None

    def link_identity(self, account_id: str, provider: str, subject_hash: str) -> None:
        """Link an outside identity to this account, replacing any earlier one.

        Raises IdentityTaken when the identity already belongs to another
        account: one Google account opening two accounts would let one person
        speak as two participants. On a MongoDB server a unique index also
        refuses the second of two accounts linking the same identity at once.
        """
        owner = self.account_by_identity(provider, subject_hash)
        if owner is not None and owner["account_id"] != account_id:
            raise IdentityTaken(provider)
        accounts = self.col("account")
        accounts.update_one(
            {"account_id": account_id}, {"$pull": {"identities": {"provider": provider}}}
        )
        link = {"provider": provider, "subject_hash": subject_hash, "linked_at": _now()}
        try:
            accounts.update_one({"account_id": account_id}, {"$push": {"identities": link}})
        except IntegrityError as e:
            # Linked to another account between the check and the update.
            raise IdentityTaken(provider) from e

    def create_with_identity(
        self,
        provider: str,
        subject_hash: str,
        email: str | None = None,
        full_name: str | None = None,
    ) -> str:
        """Sign up a student from an outside identity alone (D063); return the account_id.

        The address Google vouched for is the account's sign-in email (D071),
        already verified. The password is random and never shown, so the account
        opens through Google until its owner sets one. The identity is written
        with the account in one insert: there is no moment where the account
        exists unlinked. Raises IdentityTaken when the identity already has an
        account, which is how a second, simultaneous callback learns it lost the
        race; ValueError when Google gave no usable email.
        """
        if self.account_by_identity(provider, subject_hash) is not None:
            raise IdentityTaken(provider)
        email = contact.normalize_email(email or "")
        if self.col("account").find_one({"email": email}, {"_id": 1}) is not None:
            raise EmailTaken(email)
        name = None
        if full_name:
            try:
                name = contact.normalize_name(full_name)
            except ValueError:
                name = None  # Google's name will not do; the owner can set one
        now = _now()
        aid = uuid.uuid4().hex[:12]
        doc = self._new_account(
            aid,
            email,
            passwords.hash_password(secrets.token_urlsafe(32)),
            Role.STUDENT,
            False,
            now,
        )
        doc["identities"] = [{"provider": provider, "subject_hash": subject_hash, "linked_at": now}]
        doc.update(email_verified=1, full_name=name)
        try:
            self.col("account").insert_one(doc)
        except IntegrityError as e:
            if self.account_by_identity(provider, subject_hash) is not None:
                raise IdentityTaken(provider) from e
            raise EmailTaken(email) from e
        return aid

    def adopt_by_email(
        self, account_id: str, provider: str, subject_hash: str, email: str | None = None
    ) -> bool | None:
        """Join a Google sign-in to the account that already has its verified email (D071).

        Google has proved the address belongs to whoever is signing in. If the
        account's email was never proved -- typed at sign-up -- somebody else
        may have typed it: the password is replaced by an unknown one and every
        session ends, so only the address's owner, via
        Google, gets in. Returns whether that reset happened.

        SEC-01: "verified" is decided by the database at the moment of joining,
        on the address Google vouched for (`email`, when given): the account
        must still have that address and still be marked verified -- which,
        since codes are bound to their address, means proved for this one.
        Anything else is a takeover: password replaced, codes by email dropped,
        every session ended.

        The link and the takeover are each one update conditioned on that
        address and on the links read here, which it replaces whole (the old
        link of this provider dropped, the new one added): an account that
        moves to another address, or whose links change, meanwhile is not
        touched at all -- nothing linked, nothing unlinked, nothing reset.
        Returns None then.
        """
        accounts = self.col("account")
        raw = accounts.find_one({"account_id": account_id}, {"identities": 1})
        if raw is None:
            raise KeyError(account_id)
        owner = self.account_by_identity(provider, subject_hash)
        if owner is not None and owner["account_id"] != account_id:
            raise IdentityTaken(provider)
        held = raw.get("identities")
        at: dict[str, object] = {"account_id": account_id, "identities": held}
        if email:
            at["email"] = contact.normalize_email(email)
        link = {"provider": provider, "subject_hash": subject_hash, "linked_at": _now()}
        links = [i for i in held or [] if i.get("provider") != provider] + [link]
        try:
            kept = accounts.update_one({**at, "email_verified": 1}, {"$set": {"identities": links}})
            if kept.matched_count == 1:
                return False
            taken = accounts.update_one(
                {**at, "email_verified": {"$ne": 1}},
                {
                    "$set": {
                        "identities": links,
                        "email_verified": 1,
                        "password_hash": passwords.hash_password(secrets.token_urlsafe(32)),
                        "must_change_password": 0,
                    },
                    "$unset": {"email_codes": ""},
                },
            )
        except IntegrityError as e:
            # Linked to another account between the check and the update.
            raise IdentityTaken(provider) from e
        if taken.matched_count == 0:
            return None
        self.revoke_sessions(account_id)
        return True

    def fill_contact(self, account_id: str, email: str | None, full_name: str | None) -> None:
        """Fill what a Google account lacks from what Google says, never overwriting."""
        row = self.get(account_id)
        if row is None:
            return
        changes: dict[str, object] = {}
        if email and row["email"] == contact.normalize_email(email):
            changes["email_verified"] = 1
        if full_name and not row["full_name"]:
            try:
                changes["full_name"] = contact.normalize_name(full_name)
            except ValueError:
                pass
        if changes:
            try:
                self.col("account").update_one({"account_id": account_id}, {"$set": changes})
            except IntegrityError:
                pass  # the address was taken in between: keep the account as it was

    def count_identities(self, provider: str) -> int:
        return self.col("account").count_documents({"identities.provider": provider})

    def unlink_identity(self, account_id: str, provider: str) -> bool:
        done = self.col("account").update_one(
            {"account_id": account_id, "identities.provider": provider},
            {"$pull": {"identities": {"provider": provider}}},
        )
        return done.modified_count > 0

    def login_with_identity(
        self, provider: str, subject_hash: str, device: str | None = None
    ) -> tuple[str, dict] | None:
        """Open a session for the account linked to this identity, or None.

        No password is involved, so the password lockout does not apply: it
        exists to stop guessing, and there is nothing to guess here. A disabled
        account stays shut.
        """
        row = self.account_by_identity(provider, subject_hash)
        if row is None or row["disabled"]:
            return None
        self.col("account").update_one(
            {"account_id": row["account_id"]}, {"$set": {"last_login_at": _now()}}
        )
        return self._open_session(row["account_id"], device, method=provider), row
