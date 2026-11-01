"""Sign-in, the merged audit log, and the gateway's session check (D043).

FR-32 (sign-in), FR-36 (audit). There is no terms-of-use step any more (D064):
a signed-in learner records straight away. D065: a student may open an account
with a password (/signup) and replace a forgotten one with a recovery code
(/forgot) -- the system keeps no email address to send a reset link to.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi import Response as HttpResponse

from aicefr.api.deps import ADMIN_ONLY, ROLE_HOME, require_login, set_session_cookie
from aicefr.api.schemas import LoginRequest, RecoverRequest, SignupRequest
from aicefr.auth.sessions import COOKIE_NAME, device_label
from aicefr.config import get_settings
from aicefr.contracts import AuditEntry
from aicefr.platform.callers import ACCOUNT_HEADER, GATEWAY_HEADER, encode_account
from aicefr.platform.rpc import RemoteError, same_key
from aicefr.services import Peers
from aicefr.storage.audit_repository import AuditLog, merge
from aicefr.storage.auth_repository import (
    Account,
    AccountLocked,
    AuthRepository,
    EmailTaken,
    Role,
)

router = APIRouter()


@dataclass
class Services:
    auth: AuthRepository
    audit_log: AuditLog
    gateway_token: str
    # The other services, whose audit logs the administrator reads here
    # together with this one's.
    peers: Peers


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured when the service is built
        raise RuntimeError("identity API used before configure()")
    return _services


# ================================================================= sign-in


@router.post("/api/v1/auth/login", tags=["auth"])
def login(info: LoginRequest, request: Request, response: HttpResponse) -> dict:
    """Log in and set the session cookie.

    The error message deliberately does NOT distinguish a wrong account from a
    wrong password. Any hint that separates the two cases leaks which accounts
    actually exist.
    """
    s = svc()
    # D029: an account's own history shows its sign-ins and failed attempts.
    # Only for pseudonyms that exist: a typed string that matches no account
    # is attacker input, and the audit log is not a place to keep it.
    known = s.auth.by_sign_in_name(info.identifier)
    try:
        token = s.auth.login(
            info.identifier, info.password, device_label(request.headers.get("user-agent"))
        )
    except AccountLocked as e:
        if known is not None:
            s.audit_log.write(
                known["pseudonym"], "auth.login_failed", known["account_id"], "locked"
            )
        # NFR-07: the sixth attempt returns 429, not 401.
        raise HTTPException(429, f"tài khoản tạm khóa đến {e.args[0]}, thử lại sau") from e
    if token is None:
        if known is not None:
            s.audit_log.write(
                known["pseudonym"], "auth.login_failed", known["account_id"], "wrong_password"
            )
        raise HTTPException(401, "email hoặc mật khẩu không đúng")
    s.audit_log.write(known["pseudonym"], "auth.login", known["account_id"], "method=password")

    set_session_cookie(response, token)
    # Where this role starts its work. A temporary password goes to the
    # account page first (D028).
    must_change = bool(known["must_change_password"])
    home = ROLE_HOME.get(Role(known["role"]), "/")
    return {
        "status": "ok",
        "home": "/account?first=1" if must_change else home,
        "must_change_password": must_change,
    }


# A response carrying a recovery code must not be kept by a browser or a proxy.
NO_STORE = {"Cache-Control": "no-store"}


@router.post("/api/v1/auth/signup", tags=["auth"])
def signup(info: SignupRequest, request: Request, response: HttpResponse) -> dict:
    """Open a student account with an email, a full name and a password; sign it in.

    D065, D071. The email is how the person signs in from now on; the
    pseudonym is the system's choice and stays inside. The recovery code that
    comes back is shown once: it is the one way back in without an administrator.
    Only students sign themselves up; a teacher or an administrator is given
    their role by somebody with authority (FR-32).
    """
    if not get_settings().self_signup:
        raise HTTPException(404, "máy chủ này không cho tự đăng ký")
    s = svc()
    try:
        aid, pseudonym, code, token = s.auth.signup(
            info.email,
            info.full_name,
            info.password,
            device_label(request.headers.get("user-agent")),
        )
    except EmailTaken as e:
        raise HTTPException(
            409, "email này đã có tài khoản: hãy đăng nhập, hoặc dùng Quên mật khẩu"
        ) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    s.audit_log.write(pseudonym, "account.signup", aid, "method=password")
    set_session_cookie(response, token)
    response.headers.update(NO_STORE)
    return {
        "pseudonym": pseudonym,
        "email": s.auth.get(aid)["email"],
        "recovery_code": code,
        "home": ROLE_HOME[Role.STUDENT],
    }


@router.post("/api/v1/auth/recover", tags=["auth"])
def recover(info: RecoverRequest, request: Request, response: HttpResponse) -> dict:
    """Replace a forgotten password with the recovery code; sign in (D065).

    Answers a wrong email and a wrong code with the same sentence, as the
    login does. A wrong code counts towards the lockout (NFR-07). On success
    every other session of the account ends and a new code replaces the one
    just used, shown once.
    """
    s = svc()
    known = s.auth.by_sign_in_name(info.identifier)
    try:
        done = s.auth.recover(
            info.identifier,
            info.recovery_code,
            info.new_password,
            device_label(request.headers.get("user-agent")),
        )
    except AccountLocked as e:
        if known is not None:
            s.audit_log.write(
                known["pseudonym"], "auth.recover_failed", known["account_id"], "locked"
            )
        raise HTTPException(429, f"tài khoản tạm khóa đến {e.args[0]}, thử lại sau") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if done is None:
        if known is not None:
            s.audit_log.write(
                known["pseudonym"], "auth.recover_failed", known["account_id"], "wrong_code"
            )
        raise HTTPException(401, "email hoặc mã khôi phục không đúng")
    token, row, code = done
    s.audit_log.write(row["pseudonym"], "account.recover", row["account_id"], None)
    set_session_cookie(response, token)
    response.headers.update(NO_STORE)
    return {
        "pseudonym": row["pseudonym"],
        "email": row["email"],
        "recovery_code": code,
        "home": ROLE_HOME.get(Role(row["role"]), "/"),
    }


@router.post("/api/v1/auth/logout", tags=["auth"])
def logout(request: Request, response: HttpResponse) -> dict:
    """Destroy the session. AC-32.4: the old cookie must return 401 on the very next call."""
    svc().auth.logout(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/api/v1/me", tags=["auth"])
def me(account: Account = Depends(require_login)) -> dict:
    return {
        "account_id": account.account_id,
        "pseudonym": account.pseudonym,
        "role": account.role.value,
        "email": account.email,
        "full_name": account.full_name,
    }


@router.get("/internal/identity/session", include_in_schema=False)
def session_for_gateway(
    request: Request,
    response: HttpResponse,
    gateway: str | None = Header(None, alias=GATEWAY_HEADER),
) -> dict:
    """Who the session cookie belongs to, for the gateway's `auth_request`.

    Always 200: an anonymous visitor is a valid answer (an empty account
    header), and the service behind the gateway decides what an anonymous
    visitor may see.
    """
    s = svc()
    if not same_key(s.gateway_token, gateway):
        raise HTTPException(403, "gateway only")
    account = s.auth.account_for_token(request.cookies.get(COOKIE_NAME))
    response.headers[ACCOUNT_HEADER] = encode_account(account)
    return {"signed_in": account is not None}


# ================================================================= audit


@router.get("/api/v1/audit", tags=["admin"])
def audit_entries(
    limit: int = Query(100, ge=1, le=500), account: Account = ADMIN_ONLY
) -> list[AuditEntry]:
    """Every service's audit log, merged by time (D043)."""
    s = svc()
    logs = [s.audit_log.recent(limit)]
    for facade in (s.peers.assessment, s.peers.learning, s.peers.billing):
        if facade is None:
            continue
        try:
            logs.append(facade.audit_recent(limit=limit))
        except RemoteError as e:
            raise HTTPException(503, f"chưa đọc được nhật ký của một dịch vụ: {e}") from e
    return merge(logs, limit)
