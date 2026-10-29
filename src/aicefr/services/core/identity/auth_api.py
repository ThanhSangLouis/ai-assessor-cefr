"""Sign-in, consent, the merged audit log, and the session check the gateway makes (D043).

FR-32 (sign-in), FR-01 and FR-35 (consent), FR-36 (audit). Consent is checked
where a recording is made -- the assessment and learning services ask this one
-- not at login: a student may still read an old report after withdrawing; what
withdrawal stops is making new recordings and using existing ones for research.
A change of consent is announced on the bus (`consent.changed`), so a learner
who no longer allows research use leaves the feedback study at once (D040).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request
from fastapi import Response as HttpResponse

from aicefr.api.deps import ADMIN_ONLY, ROLE_HOME, require_login, set_session_cookie
from aicefr.api.schemas import LoginRequest
from aicefr.auth.sessions import COOKIE_NAME, device_label
from aicefr.contracts import AuditEntry
from aicefr.observability import count
from aicefr.platform.bus import MessageBus
from aicefr.platform.callers import ACCOUNT_HEADER, GATEWAY_HEADER, encode_account
from aicefr.platform.rpc import RemoteError, same_key
from aicefr.services import Peers
from aicefr.storage.audit_repository import AuditLog, merge
from aicefr.storage.auth_repository import Account, AccountLocked, AuthRepository, Role
from aicefr.storage.consent_repository import CURRENT_CONSENT_VERSION, ConsentRepository

router = APIRouter()

CONSENT_CHANGED = "consent.changed"


@dataclass
class Services:
    auth: AuthRepository
    consents: ConsentRepository
    audit_log: AuditLog
    bus: MessageBus
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


# ================================================================= consent


def consent_state(consent, account: Account) -> dict:
    return {
        "signed": consent is not None,
        "consent_version": consent.consent_version if consent else CURRENT_CONSENT_VERSION,
        "current_version": CURRENT_CONSENT_VERSION,
        "audio_storage_allowed": bool(consent and consent.audio_storage_allowed),
        "research_use_allowed": bool(consent and consent.research_use_allowed),
        "signed_at": consent.signed_at if consent else None,
        "may_submit": bool(consent and consent.may_submit),
        "role": account.role.value,
    }


@router.get("/api/v1/me/consent", tags=["student"])
def my_consent(account: Account = Depends(require_login)) -> dict:
    """What the current user has agreed to, if anything."""
    return consent_state(svc().consents.current(account.account_id), account)


@router.post("/api/v1/me/consent", tags=["student"])
def sign_consent(
    audio_storage_allowed: bool = Form(False),
    research_use_allowed: bool = Form(False),
    account: Account = Depends(require_login),
) -> dict:
    """Record a signature. The two permissions are separate on purpose.

    A single "I agree" button would make it impossible to tell afterwards
    whether somebody meant "you may keep my recording" or "you may publish
    numbers derived from it". They are different questions and they are asked
    separately.
    """
    s = svc()
    c = s.consents.sign(
        account.account_id,
        audio_storage_allowed=audio_storage_allowed,
        research_use_allowed=research_use_allowed,
    )
    s.audit_log.write(
        account.pseudonym,
        "consent.sign",
        c.consent_id,
        f"version={c.consent_version} audio={int(c.audio_storage_allowed)}"
        f" research={int(c.research_use_allowed)}",
    )
    s.bus.publish(
        CONSENT_CHANGED,
        {"account_id": account.account_id, "research_use_allowed": c.research_use_allowed},
    )
    count("consent_signed_total")
    return consent_state(c, account)


@router.post("/api/v1/me/consent/withdraw", tags=["student"])
def withdraw_consent(account: Account = Depends(require_login)) -> dict:
    """Withdraw consent. The student does this themselves, FR-35.

    Needing to email an administrator is not a right, it is a queue. Results
    already produced stay readable by their owner until the retention job
    removes them; what stops immediately is new recording and research use.
    """
    s = svc()
    withdrawn = s.consents.withdraw(account.account_id)
    s.bus.publish(
        CONSENT_CHANGED, {"account_id": account.account_id, "research_use_allowed": False}
    )
    if withdrawn:
        s.audit_log.write(account.pseudonym, "consent.withdraw", account.account_id, None)
        count("consent_withdrawn_total")
    return {"withdrawn": withdrawn, **consent_state(None, account)}


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
