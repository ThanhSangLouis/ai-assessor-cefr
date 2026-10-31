"""Accounts, profiles and what is new for a person (D028, D029).

A person looks after their own password, sessions, profile and linked Google
account; an administrator looks after everybody's account from the web, not
from a terminal on the server.
Only a student may register themself (D063 with Google, D065 with a password):
the role decides what a person may change, so a teacher or an administrator is
given that role by somebody with authority (FR-32).

Two rules shape the administrator's side:

* **A password an administrator has seen is temporary.** Accounts created or
  reset here get a one-time password, shown once and printable as a slip, and
  can do nothing but choose their own (`deps.PASSWORD_CHANGE_PATHS`).
* **Pseudonyms only.** The slip has a blank line for a name, filled in by hand
  and kept on paper outside the system, which is how FR-33 keeps the link
  between a pseudonym and a person.

Part of the identity service (D043). What waits for a person -- the sidebar's
counts -- comes from other services and is answered by the web service
(`aicefr.services.web.bff`); the account page itself is drawn there too.
Wired once at start-up through `configure`.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Response as HttpResponse
from pydantic import BaseModel, Field

from aicefr.api.deps import (
    ADMIN_ONLY,
    ROLE_HOME,
    get_auth_repo,
    require_login,
)
from aicefr.auth import google, passwords
from aicefr.auth.sessions import COOKIE_NAME, hash_token
from aicefr.config import get_settings
from aicefr.services import Peers
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import (
    AVATAR_COLORS,
    AVATAR_ICONS,
    DAILY_GOALS,
    DEFAULT_PREFIX,
    Account,
    AccountLocked,
    AuthRepository,
    EmailTaken,
    Role,
    WrongPassword,
)

router = APIRouter()

MAX_BATCH = 200
# A response carrying a temporary password must not be kept by a browser or a
# proxy: it is meant to be read once and printed.
NO_STORE = {"Cache-Control": "no-store"}


@dataclass
class Services:
    audit_log: AuditLog  # this service's audit log: written here, read for a person's history
    # The other services; `peers.billing` holds the seats of the plan in force
    # (D033). None there: no plans, as before D033.
    peers: Peers

    def audit(self, actor: str, action: str, target: str | None, detail: str | None) -> None:
        self.audit_log.write(actor, action, target, detail)


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("accounts API used before configure()")
    return _services


# ================================================================= own account


# Account events a person sees in their own history (D029).
ACTIVITY_ACTIONS = (
    "auth.login",
    "auth.login_failed",
    "account.create",
    "account.password_change",
    "account.reset_password",
    "account.sessions_revoked",
    "account.session_revoked",
    "account.disable",
    "account.enable",
    "account.unlock",
    "account.role_change",
    "account.google_link",
    "account.google_unlink",
    "account.profile",
    "account.signup",
    "account.google_signup",
    "account.recovery_code",
    "account.recover",
    "auth.recover_failed",
    "account.contact",
    "account.google_adopt",
)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


@router.get("/api/v1/me/account", tags=["auth"])
def my_account(
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    row = next(a for a in auth.list_accounts() if a["account_id"] == account.account_id)
    linked = auth.identity(account.account_id, google.PROVIDER)
    settings = get_settings()
    return {
        "pseudonym": row["pseudonym"],
        "role": row["role"],
        # D071: how the person signs in, and the name a teacher reads.
        "email": row["email"],
        "email_verified": row["email_verified"],
        "full_name": row["full_name"],
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
        "password_changed_at": row["password_changed_at"],
        "must_change_password": row["must_change_password"],
        "active_sessions": row["active_sessions"],
        "min_password_length": passwords.MIN_LENGTH,
        "home": ROLE_HOME.get(account.role, "/"),
        "profile": {
            "avatar_icon": account.avatar_icon,
            "avatar_color": account.avatar_color,
            "daily_goal_s": account.daily_goal_s,
        },
        "choices": {
            "avatar_icons": list(AVATAR_ICONS),
            "avatar_colors": list(AVATAR_COLORS),
            "daily_goals": list(DAILY_GOALS),
        },
        # D065: whether a recovery code is in force and since when; never the code.
        "recovery": {"issued_at": auth.get(account.account_id)["recovery_issued_at"]},
        "google": {
            "enabled": settings.google_enabled,
            "linked": linked is not None,
            "linked_at": linked["linked_at"] if linked else None,
            "domain": settings.google_allowed_domain,
        },
    }


class ProfileChange(BaseModel):
    """Any subset of the profile; each value must come from its list."""

    avatar_icon: str | None = Field(None, max_length=32)
    avatar_color: str | None = Field(None, max_length=32)
    daily_goal_s: int | None = None


@router.patch("/api/v1/me/profile", tags=["auth"])
def change_my_profile(
    body: ProfileChange,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Avatar and daily goal (D029). No free-text field: there is nowhere to type a name."""
    try:
        auth.update_profile(
            account.account_id,
            avatar_icon=body.avatar_icon,
            avatar_color=body.avatar_color,
            daily_goal_s=body.daily_goal_s,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    changed = sorted(k for k, v in body.model_dump().items() if v is not None)
    if changed:
        svc().audit(account.pseudonym, "account.profile", account.account_id, " ".join(changed))
    row = auth.get(account.account_id)
    return {
        "avatar_icon": row["avatar_icon"],
        "avatar_color": row["avatar_color"],
        "daily_goal_s": row["daily_goal_s"],
    }


class ContactChange(BaseModel):
    """D071: the sign-in email and the full name; either may be left out."""

    email: str | None = Field(None, max_length=254)
    full_name: str | None = Field(None, max_length=80)
    # Needed to change an email the account already signs in with.
    current_password: str | None = Field(None, max_length=200)


def _contact_view(row: dict) -> dict:
    return {
        "email": row["email"],
        "email_verified": bool(row["email_verified"]),
        "full_name": row["full_name"],
    }


@router.patch("/api/v1/me/contact", tags=["auth"])
def change_my_contact(
    body: ContactChange,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Set the sign-in email and the full name (D071).

    Adding a first email needs nothing more: the person is signed in. Changing
    one the account already signs in with needs the password, as changing the
    password does -- otherwise a borrowed session could move the account to
    another address and lock its owner out. A wrong password counts as a failed
    login (NFR-07).
    """
    row = auth.get(account.account_id)
    changing = (
        body.email is not None and row["email"] and body.email.strip().lower() != row["email"]
    )
    if changing:
        if not body.current_password or not passwords.verify_password(
            body.current_password, row["password_hash"]
        ):
            if body.current_password:
                auth.record_failure(account.account_id)
            raise HTTPException(403, "nhập đúng mật khẩu hiện tại để đổi email")
    try:
        row = auth.set_contact(account.account_id, email=body.email, full_name=body.full_name)
    except EmailTaken as e:
        raise HTTPException(409, "email này đã có tài khoản khác") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    changed = sorted(k for k in ("email", "full_name") if getattr(body, k) is not None)
    if changed:
        svc().audit(account.pseudonym, "account.contact", account.account_id, " ".join(changed))
    return _contact_view(row)


@router.get("/api/v1/me/sessions", tags=["auth"])
def my_sessions(
    request: Request,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> list[dict]:
    """Open sessions of this account; the one making the request is marked `current`."""
    token = request.cookies.get(COOKIE_NAME)
    here = hash_token(token)[:16] if token else ""
    return [{**s, "current": s["session_id"] == here} for s in auth.sessions(account.account_id)]


@router.delete("/api/v1/me/sessions/{session_id}", tags=["auth"])
def end_my_session(
    session_id: str,
    request: Request,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """End one session of this account, this one included (that is signing out)."""
    if not auth.revoke_session(account.account_id, session_id):
        raise HTTPException(404, "không có phiên này")
    token = request.cookies.get(COOKIE_NAME)
    current = bool(token) and hash_token(token)[:16] == session_id
    svc().audit(account.pseudonym, "account.session_revoked", account.account_id, None)
    return {"revoked": True, "current": current}


@router.get("/api/v1/me/activity", tags=["auth"])
def my_activity(account: Account = Depends(require_login)) -> list[dict]:
    """Sign-ins, failed attempts and account changes, newest first.

    Who acted is "you" or "an administrator": the administrator's pseudonym is
    not the person's business, and an attempt nobody made is worth noticing.
    """
    rows = svc().audit_log.about(account.account_id, ACTIVITY_ACTIONS)
    return [
        {
            "action": r["action"],
            "detail": r["detail"],
            "created_at": r["created_at"],
            "by_self": r["actor_id"] == account.pseudonym,
        }
        for r in rows
    ]


@router.post("/api/v1/me/google/unlink", tags=["auth"])
def unlink_my_google(
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    if not auth.unlink_identity(account.account_id, google.PROVIDER):
        raise HTTPException(404, "tài khoản chưa liên kết Google")
    svc().audit(account.pseudonym, "account.google_unlink", account.account_id, None)
    return {"linked": False}


@router.post("/api/v1/me/password", tags=["auth"])
def change_my_password(
    body: PasswordChange,
    request: Request,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Choose a new password. Every other session of the account ends."""
    try:
        ended = auth.change_password(
            account.account_id,
            body.current_password,
            body.new_password,
            keep_token=request.cookies.get(COOKIE_NAME),
        )
    except AccountLocked as e:
        raise HTTPException(429, f"tài khoản tạm khóa đến {e.args[0]}, thử lại sau") from e
    except WrongPassword as e:
        raise HTTPException(403, "mật khẩu hiện tại không đúng") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    svc().audit(
        account.pseudonym, "account.password_change", account.account_id, f"sessions_ended={ended}"
    )
    return {"status": "ok", "sessions_ended": ended, "home": ROLE_HOME.get(account.role, "/")}


@router.post("/api/v1/me/recovery-code", tags=["auth"])
def new_recovery_code(
    response: HttpResponse,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """A new recovery code, shown once; the previous one stops working (D065).

    Needs only the session, like linking Google: an account opened with
    Google has no password its owner knows, and this is how it gets one --
    make a code here, then use "Quên mật khẩu".
    """
    code = auth.issue_recovery_code(account.account_id)
    svc().audit(account.pseudonym, "account.recovery_code", account.account_id, None)
    response.headers.update(NO_STORE)
    return {"recovery_code": code}


@router.post("/api/v1/me/sessions/revoke-others", tags=["auth"])
def revoke_my_other_sessions(
    request: Request,
    account: Account = Depends(require_login),
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Sign out everywhere except here: a phone left in a lab, a shared computer."""
    ended = auth.revoke_sessions(account.account_id, keep_token=request.cookies.get(COOKIE_NAME))
    svc().audit(account.pseudonym, "account.sessions_revoked", account.account_id, f"count={ended}")
    return {"revoked": ended}


# ================================================================= administrator


class AccountCreate(BaseModel):
    """Either one named pseudonym or a numbered series (SV-001, SV-002, ...)."""

    role: Role
    count: int = Field(1, ge=1, le=MAX_BATCH)
    prefix: str | None = Field(None, max_length=6)
    pseudonym: str | None = Field(None, max_length=32)


def _seats(n: int) -> None:
    """Refuse `n` more enabled student accounts beyond the plan's seats (D033, BR-31).

    Only new ones: an account that exists is never turned off for a plan.
    """
    plans = svc().peers.billing
    if plans is None:
        return
    reason = plans.seat_refusal(n=n)
    if reason:
        raise HTTPException(409, reason)


def _target(auth: AuthRepository, account_id: str):
    row = auth.get(account_id)
    if row is None:
        raise HTTPException(404, "không tìm thấy tài khoản")
    return row


@router.get("/api/v1/admin/accounts", tags=["admin"])
def list_accounts(
    account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> list[dict]:
    return auth.list_accounts()


@router.post("/api/v1/admin/accounts", tags=["admin"])
def create_accounts(
    body: AccountCreate,
    response: HttpResponse,
    account: Account = ADMIN_ONLY,
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Create accounts with one-time passwords, shown in this response and nowhere else."""
    if body.role is Role.STUDENT:
        _seats(1 if body.pseudonym else body.count)
    try:
        if body.pseudonym:
            names = [body.pseudonym.strip()]
        else:
            names = auth.next_pseudonyms(body.prefix or DEFAULT_PREFIX[body.role], body.count)
        created = auth.create_with_temporary_passwords(names, body.role)
    except ValueError as e:
        status = 409 if "đã tồn tại" in str(e) else 422
        raise HTTPException(status, str(e)) from e
    for aid, name, _ in created:
        detail = f"pseudonym={name} role={body.role.value}"
        svc().audit(account.pseudonym, "account.create", aid, detail)
    response.headers.update(NO_STORE)
    return {
        "role": body.role.value,
        "created": [
            {"account_id": aid, "pseudonym": name, "temporary_password": temporary}
            for aid, name, temporary in created
        ],
    }


@router.post("/api/v1/admin/accounts/{account_id}/reset-password", tags=["admin"])
def reset_password(
    account_id: str,
    response: HttpResponse,
    account: Account = ADMIN_ONLY,
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """A forgotten password: a new one-time password, every session of the account ends."""
    if account_id == account.account_id:
        raise HTTPException(409, "mật khẩu của chính bạn thì đổi ở trang Tài khoản")
    row = _target(auth, account_id)
    temporary = auth.set_temporary_password(account_id)
    svc().audit(account.pseudonym, "account.reset_password", account_id, None)
    response.headers.update(NO_STORE)
    return {
        "account_id": account_id,
        "pseudonym": row["pseudonym"],
        "role": row["role"],
        "temporary_password": temporary,
    }


@router.post("/api/v1/admin/accounts/{account_id}/disable", tags=["admin"])
def disable_account(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    """Turn an account off; its data stays. Erasing data is a separate, explicit step.

    An administrator cannot turn off their own account, which also means the
    last enabled administrator can never be turned off: whoever is asking is
    one, and a different one would have to be enabled to ask.
    """
    if account_id == account.account_id:
        raise HTTPException(409, "không tự tắt tài khoản đang dùng")
    _target(auth, account_id)
    auth.set_disabled(account_id, True)
    svc().audit(account.pseudonym, "account.disable", account_id, None)
    return {"account_id": account_id, "disabled": True}


@router.post("/api/v1/admin/accounts/{account_id}/enable", tags=["admin"])
def enable_account(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    row = _target(auth, account_id)
    if row["role"] == Role.STUDENT.value and row["disabled"]:
        _seats(1)
    auth.set_disabled(account_id, False)
    svc().audit(account.pseudonym, "account.enable", account_id, None)
    return {"account_id": account_id, "disabled": False}


@router.post("/api/v1/admin/accounts/{account_id}/unlock", tags=["admin"])
def unlock_account(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    """Lift a lockout (NFR-07) without waiting the fifteen minutes."""
    _target(auth, account_id)
    auth.unlock(account_id)
    svc().audit(account.pseudonym, "account.unlock", account_id, None)
    return {"account_id": account_id, "locked_until": None}


class RoleChange(BaseModel):
    role: Role


@router.get("/api/v1/admin/accounts/{account_id}", tags=["admin"])
def account_detail(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    """One account for its detail panel (D029): state, sessions, Google link, history."""
    _target(auth, account_id)
    row = next(a for a in auth.list_accounts() if a["account_id"] == account_id)
    linked = auth.identity(account_id, google.PROVIDER)
    return {
        **row,
        "google_linked_at": linked["linked_at"] if linked else None,
        "sessions": auth.sessions(account_id),
        "activity": [
            {
                "action": r["action"],
                "detail": r["detail"],
                "created_at": r["created_at"],
                "actor_id": r["actor_id"],
            }
            for r in svc().audit_log.about(account_id, ACTIVITY_ACTIONS, limit=20)
        ],
    }


@router.patch("/api/v1/admin/accounts/{account_id}/contact", tags=["admin"])
def change_account_contact(
    account_id: str,
    body: ContactChange,
    account: Account = ADMIN_ONLY,
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """An administrator sets a person's email and full name (D071), e.g. for staff accounts."""
    _target(auth, account_id)
    try:
        row = auth.set_contact(account_id, email=body.email, full_name=body.full_name)
    except EmailTaken as e:
        raise HTTPException(409, "email này đã có tài khoản khác") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    svc().audit(account.pseudonym, "account.contact", account_id, "admin")
    return _contact_view(row)


@router.post("/api/v1/admin/accounts/{account_id}/role", tags=["admin"])
def change_role(
    account_id: str,
    body: RoleChange,
    account: Account = ADMIN_ONLY,
    auth: AuthRepository = Depends(get_auth_repo),
) -> dict:
    """Give an account another role. Not one's own: an administrator cannot demote themself
    by a slip of the mouse and leave nobody able to undo it."""
    if account_id == account.account_id:
        raise HTTPException(409, "không tự đổi vai trò của chính mình")
    row = _target(auth, account_id)
    if body.role is Role.STUDENT and row["role"] != Role.STUDENT.value and not row["disabled"]:
        _seats(1)
    before = auth.set_role(account_id, body.role)
    svc().audit(
        account.pseudonym,
        "account.role_change",
        account_id,
        f"from={before} to={body.role.value}",
    )
    return {"account_id": account_id, "role": body.role.value, "previous_role": before}


@router.post("/api/v1/admin/accounts/{account_id}/revoke-sessions", tags=["admin"])
def revoke_account_sessions(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    """Sign an account out everywhere, e.g. after a lost phone, without touching its password."""
    if account_id == account.account_id:
        raise HTTPException(409, "phiên của chính bạn thì đăng xuất ở trang Tài khoản")
    _target(auth, account_id)
    ended = auth.revoke_sessions(account_id)
    svc().audit(account.pseudonym, "account.sessions_revoked", account_id, f"count={ended}")
    return {"account_id": account_id, "revoked": ended}


@router.post("/api/v1/admin/accounts/{account_id}/unlink-google", tags=["admin"])
def unlink_account_google(
    account_id: str, account: Account = ADMIN_ONLY, auth: AuthRepository = Depends(get_auth_repo)
) -> dict:
    """Remove a Google link, e.g. when the person lost access to that Google account."""
    _target(auth, account_id)
    if not auth.unlink_identity(account_id, google.PROVIDER):
        raise HTTPException(404, "tài khoản chưa liên kết Google")
    svc().audit(account.pseudonym, "account.google_unlink", account_id, None)
    return {"account_id": account_id, "google_linked": False}
