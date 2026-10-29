"""Persistence for accounts and login sessions. Implements FR-32 and NFR-07.

Kept separate from Repository so that scoring logic and authentication are not
mixed together, but pointed at the SAME database so there is only one
connection target to manage.

The same privacy rule applies: the account table holds only pseudonyms. Never
store a real name, a student ID, or any contact detail.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path

from aicefr.auth import passwords
from aicefr.auth import sessions as session_tokens
from aicefr.auth.pseudonyms import validate_pseudonym
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
        (("pseudonym",), True),
        (("pseudonym_lower",), False),
        (
            ("identities.provider", "identities.subject_hash"),
            True,
            {"identities.subject_hash": {"$exists": True}},
        ),
    ],
    "session": [(("token_hash",), True), (("account_id",), False)],
}
SETTING = "identity."  # this part's keys in `system`

# Every field of an account document, so a reader gets None for one never set,
# as it got NULL from a column.
ACCOUNT_FIELDS = (
    "account_id",
    "pseudonym",
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
    "terms_accepted_at",
    "identities",
    "seen_markers",
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
    # D058: when the learner accepted the terms of use, None until then. It
    # replaces the research consent form: the voice-collection round is over,
    # and accepting the terms is what lets a recording be stored and used.
    terms_accepted_at: str | None = None
    # D060: the providers of the outside identities linked to the account, and
    # when its owner last looked at what can change behind their back (D028).
    identities: tuple[str, ...] = ()
    seen_markers: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_staff(self) -> bool:
        return self.role in (Role.TEACHER, Role.ADMIN)

    @property
    def may_submit(self) -> bool:
        """A recording is stored only for someone who accepted the terms."""
        return self.terms_accepted_at is not None


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
        aid: str, pseudonym: str, password_hash: str, role: Role, must_change: bool, now: str
    ) -> dict:
        return {
            "account_id": aid,
            "pseudonym": pseudonym,
            # Kept beside the pseudonym for the case-blind uniqueness check of
            # a class list, which SQL did with lower().
            "pseudonym_lower": pseudonym.lower(),
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
            "terms_accepted_at": None,
            "identities": [],
            "seen_markers": {},
        }

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
        # collection and only fail later, on somebody else's screen.
        pseudonym = validate_pseudonym(pseudonym)
        aid = uuid.uuid4().hex[:12]
        self.col("account").insert_one(
            self._new_account(
                aid,
                pseudonym,
                passwords.hash_password(raw_password),
                role,
                must_change_password,
                _now(),
            )
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
        accounts = self.col("account")
        taken = list(
            accounts.find(
                {"pseudonym_lower": {"$in": [n.lower() for n in names]}}, {"pseudonym": 1}
            )
        )
        if taken:
            raise ValueError(
                "bút danh đã tồn tại: " + ", ".join(sorted(r["pseudonym"] for r in taken))
            )
        temporaries = [passwords.temporary_password() for _ in names]
        workers = max(1, min(8, os.cpu_count() or 1, len(names)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            hashes = list(pool.map(passwords.hash_password, temporaries))
        created = [(uuid.uuid4().hex[:12], n, t) for n, t in zip(names, temporaries, strict=True)]
        now = _now()
        documents = [
            self._new_account(aid, name, h, role, True, now)
            for (aid, name, _), h in zip(created, hashes, strict=True)
        ]
        try:
            accounts.insert_many(documents, ordered=True)
        except IntegrityError as e:
            # Taken between the check and the insert: undo the ones that went in.
            accounts.delete_many({"account_id": {"$in": [d["account_id"] for d in documents]}})
            raise ValueError("bút danh vừa được tạo bởi người khác, hãy thử lại") from e
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
        rows = list(self.col("account").find().sort([("role", 1), ("pseudonym", 1)]))
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
                    "pseudonym": r["pseudonym"],
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
        names = self.col("account").distinct("pseudonym")
        used = [int(m.group(1)) for n in names if (m := pattern.match(n))]
        start = max(used, default=0) + 1
        width = max(3, len(str(start + count - 1)))
        return [f"{prefix}-{n:0{width}d}" for n in range(start, start + count)]

    def get_by_pseudonym(self, pseudonym: str) -> dict | None:
        return _account(self.col("account").find_one({"pseudonym": pseudonym, "disabled": 0}))

    def pseudonyms(self, account_ids: list[str]) -> dict[str, str]:
        """Pseudonym of each account id, for screens that list other people's work."""
        ids = list(dict.fromkeys(account_ids))
        if not ids:
            return {}
        rows = self.col("account").find(
            {"account_id": {"$in": ids}}, {"account_id": 1, "pseudonym": 1}
        )
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
        self.col("account").update_one(
            {"account_id": row["account_id"]}, {"$set": {"last_login_at": _now()}}
        )
        return self._open_session(row["account_id"], device)

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
        token = session_tokens.new_token()
        self.col("session").insert_one(
            {
                "token_hash": session_tokens.hash_token(token),
                "account_id": account_id,
                "expires_at": session_tokens.new_expiry(),
                "created_at": _now(),
                "device": device,
                "method": method,
            }
        )
        return token

    # ---------- sessions ----------

    def account_for_token(self, token: str | None) -> Account | None:
        """Return the account matching the session token, or None if it is invalid."""
        if not token:
            return None
        found = self.col("session").find_one({"token_hash": session_tokens.hash_token(token)})
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
            row["pseudonym"],
            Role(row["role"]),
            must_change_password=bool(row["must_change_password"]),
            avatar_icon=row["avatar_icon"],
            avatar_color=row["avatar_color"],
            daily_goal_s=row["daily_goal_s"] or DEFAULT_DAILY_GOAL,
            terms_accepted_at=row["terms_accepted_at"],
            identities=tuple(i["provider"] for i in row["identities"] or []),
            seen_markers=dict(row["seen_markers"] or {}),
        )

    def logout(self, token: str | None) -> None:
        """Delete the session. AC-32.4: after logout the old cookie must return 401
        immediately."""
        if not token:
            return
        self.col("session").delete_one({"token_hash": session_tokens.hash_token(token)})

    def purge_expired_sessions(self) -> int:
        return self.col("session").delete_many({"expires_at": {"$lte": _now()}}).deleted_count

    def revoke_sessions(self, account_id: str, keep_token: str | None = None) -> int:
        """End every session of an account except, optionally, the caller's own."""
        keep = session_tokens.hash_token(keep_token) if keep_token else ""
        return (
            self.col("session")
            .delete_many({"account_id": account_id, "token_hash": {"$ne": keep}})
            .deleted_count
        )

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

    def unlock_pseudonym(self, pseudonym: str) -> bool:
        """Lift the lockout of the account with this pseudonym; False when there is none."""
        done = self.col("account").update_one(
            {"pseudonym": pseudonym}, {"$set": {"failed_attempts": 0, "locked_until": None}}
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

    # ---------- terms of use (D058) ----------

    def accept_terms(self, account_id: str) -> str:
        """Record that the account accepted the terms; the first time stays.

        Returns the time of acceptance. Accepting again changes nothing, so a
        double click or a retried request does not move the date.
        """
        self.col("account").update_one(
            {"account_id": account_id, "terms_accepted_at": None},
            {"$set": {"terms_accepted_at": _now()}},
        )
        row = self.col("account").find_one({"account_id": account_id}, {"terms_accepted_at": 1})
        if row is None:
            raise KeyError(account_id)
        return row["terms_accepted_at"]

    def accounts_with_terms(self) -> set[str]:
        """Accounts whose data may be used in research: those that accepted the terms."""
        rows = self.col("account").find(
            {"terms_accepted_at": {"$ne": None}, "disabled": 0}, {"account_id": 1}
        )
        return {r["account_id"] for r in rows}

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
        account: one Google account opening two pseudonyms would let one person
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
