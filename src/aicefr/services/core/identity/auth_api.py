"""Sign-in, the terms of use, the merged audit log, and the gateway's session check (D043).

FR-32 (sign-in), FR-01 (terms of use, D058), FR-36 (audit). The terms are
checked where a recording is made, not at login: the account the gateway
forwards carries `terms_accepted_at`, so the assessment and learning services
decide without asking this one.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi import Response as HttpResponse

from aicefr.api.deps import ADMIN_ONLY, ROLE_HOME, require_login, set_session_cookie
from aicefr.api.schemas import LoginRequest
from aicefr.auth.sessions import COOKIE_NAME, device_label
from aicefr.contracts import AuditEntry
from aicefr.observability import count
from aicefr.platform.callers import ACCOUNT_HEADER, GATEWAY_HEADER, encode_account
from aicefr.platform.rpc import RemoteError, same_key
from aicefr.services import Peers
from aicefr.storage.audit_repository import AuditLog, merge
from aicefr.storage.auth_repository import Account, AccountLocked, AuthRepository, Role

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
    known = s.auth.get_by_pseudonym(info.pseudonym)
    try:
        token = s.auth.login(
            info.pseudonym, info.password, device_label(request.headers.get("user-agent"))
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
        raise HTTPException(401, "bút danh hoặc mật khẩu không đúng")
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


# ================================================================= terms of use


def terms_state(account: Account, accepted_at: str | None = None) -> dict:
    accepted_at = accepted_at or account.terms_accepted_at
    return {
        "accepted": accepted_at is not None,
        "accepted_at": accepted_at,
        "may_submit": accepted_at is not None,
        "role": account.role.value,
    }


@router.get("/api/v1/me/terms", tags=["student"])
def my_terms(account: Account = Depends(require_login)) -> dict:
    """Whether the current user accepted the terms of use, and when."""
    return terms_state(account)


@router.post("/api/v1/me/terms", tags=["student"])
def accept_terms(account: Account = Depends(require_login)) -> dict:
    """Accept the terms of use (D058). Accepting again keeps the first date."""
    s = svc()
    first = account.terms_accepted_at is None
    accepted_at = s.auth.accept_terms(account.account_id)
    if first:
        s.audit_log.write(account.pseudonym, "terms.accept", account.account_id, None)
        count("terms_accepted_total")
    return terms_state(account, accepted_at)


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
