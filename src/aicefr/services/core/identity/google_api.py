"""Sign in with Google: the two browser routes of the round trip (D029, D036).

`/auth/google/start` sends the browser to Google with a fresh state, nonce and
PKCE challenge kept in a ten-minute signed cookie; `/auth/google/callback`
checks them, redeems the code and then either links the Google account to the
person already signed in, or signs in the account that Google account is
linked to. Every refusal goes back to the page it came from with a fixed code,
never with text from the URL. The rules themselves live in `aicefr.auth.google`.

`/api/v1/admin/google` tells the administrator whether sign-in with Google is
on and which redirect address to register with Google, so plugging in the
keys is a matter of copying what the page says.
"""

from __future__ import annotations

import ipaddress
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from aicefr.api.deps import (
    ADMIN_ONLY,
    ROLE_HOME,
    optional_account,
    set_session_cookie,
)
from aicefr.auth import google
from aicefr.auth.sessions import device_label
from aicefr.config import get_settings
from aicefr.services.core.identity import accounts_api
from aicefr.storage.auth_repository import Account, AuthRepository, IdentityTaken, Role

router = APIRouter()

FLOW_PATH = "/auth/google"


def _config() -> google.GoogleConfig | None:
    settings = get_settings()
    if not settings.google_enabled:
        return None
    return google.GoogleConfig(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        allowed_domain=settings.google_allowed_domain,
    )


def _redirect_uri(request: Request) -> str:
    """Where Google sends the browser back. Must match the URI registered with Google."""
    public = get_settings().public_url
    if public:
        return public.rstrip("/") + f"{FLOW_PATH}/callback"
    return str(request.url_for("google_callback"))


def _key(request: Request) -> bytes:
    """The key the flow cookie is signed with, kept by this deployment (D036)."""
    return request.app.state.auth_repo.secret("google_flow")


def _cookie() -> tuple[str, str, bool]:
    """The flow cookie's name, path and Secure flag.

    Behind TLS it is a `__Host-` cookie, which must be Secure with Path=/ and
    no Domain; that is what stops a subdomain from setting it. On plain HTTP
    (localhost) the prefix is not allowed, so it keeps a plain name and a path
    that sends it to the two routes of the round trip only.
    """
    secure = get_settings().https_only
    return google.cookie_name(secure), "/" if secure else FLOW_PATH, secure


def _forget(response) -> None:
    name, path, secure = _cookie()
    response.delete_cookie(name, path=path, secure=secure, httponly=True, samesite="lax")


def _back(target: str, code: str) -> RedirectResponse:
    response = RedirectResponse(f"{target}?google={code}", status_code=303)
    _forget(response)
    return response


@router.get(f"{FLOW_PATH}/start", include_in_schema=False)
def google_start(
    request: Request,
    mode: str = "login",
    next: str = "",
    account: Account | None = Depends(optional_account),
):
    """Begin a round trip: `mode=login` from the login page, `mode=link` from the account page."""
    mode = "link" if mode == "link" else "login"
    back = "/account" if mode == "link" else "/login"
    config = _config()
    if config is None:
        return _back(back, "not_configured")
    if mode == "link" and account is None:
        return _back("/login", "signin")
    if _redirect_uri(request).startswith("https://") and not get_settings().https_only:
        # Behind TLS the flow cookie must be a __Host- cookie; without the
        # setting it would not be, and a planted flow could sign someone in
        # to another person's account (auth/google.py).
        return _back(back, "insecure")
    flow = google.new_flow(mode, next, account.account_id if mode == "link" else None)
    response = RedirectResponse(
        google.authorization_url(config, flow, _redirect_uri(request)), status_code=303
    )
    name, path, secure = _cookie()
    response.set_cookie(
        name,
        google.encode_flow(flow, _key(request)),
        max_age=google.FLOW_SECONDS,
        httponly=True,
        secure=secure,
        # Lax, not Strict: the callback is a top-level navigation coming back
        # from Google, and a Strict cookie would not be sent with it.
        samesite="lax",
        path=path,
    )
    return response


@router.get(f"{FLOW_PATH}/callback", name="google_callback", include_in_schema=False)
def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    account: Account | None = Depends(optional_account),
):
    flow = google.decode_flow(request.cookies.get(_cookie()[0]), _key(request))
    back = "/account" if flow and flow.mode == "link" else "/login"
    config = _config()
    if config is None:
        return _back(back, "not_configured")
    if error:
        # access_denied when the person pressed Cancel on Google's page.
        return _back(back, "cancelled")
    if flow is None or not state or not secrets.compare_digest(state.encode(), flow.state.encode()):
        return _back(back, "state")
    try:
        id_token = google.exchange_code(config, code, flow, _redirect_uri(request))
        identity = google.verify_id_token(config, id_token, flow.nonce)
    except google.GoogleError as e:
        return _back(back, e.code)

    auth: AuthRepository = request.app.state.auth_repo
    audit = accounts_api.svc().audit
    if flow.mode == "link":
        # The person who finishes the link must be the one who started it.
        if account is None or account.account_id != flow.account_id:
            return _back("/account", "signin")
        try:
            auth.link_identity(account.account_id, google.PROVIDER, identity.subject_hash)
        except IdentityTaken:
            return _back("/account", "taken")
        audit(account.pseudonym, "account.google_link", account.account_id, None)
        return _back("/account", "linked")

    device = device_label(request.headers.get("user-agent"))
    opened = auth.login_with_identity(google.PROVIDER, identity.subject_hash, device)
    signed_up = False
    if opened is None:
        linked = auth.account_by_identity(google.PROVIDER, identity.subject_hash)
        if linked is not None:
            return _back("/login", "disabled")
        if not get_settings().google_signup:
            return _back("/login", "not_linked")
        # D063: first time this Google account is seen, it becomes a student.
        try:
            aid = auth.create_with_identity(google.PROVIDER, identity.subject_hash)
        except IdentityTaken:
            aid = None  # a second callback of the same person won the race
        opened = auth.login_with_identity(google.PROVIDER, identity.subject_hash, device)
        if opened is None:
            return _back("/login", "not_linked")
        signed_up = aid is not None
        if signed_up:
            audit(opened[1]["pseudonym"], "account.google_signup", aid, None)
    token, row = opened
    audit(row["pseudonym"], "auth.login", row["account_id"], "method=google")
    if row["must_change_password"]:
        # Google proves who is signing in; it does not make a password an
        # administrator has seen any less known. The D028 rule still applies.
        target = "/account?first=1"
    else:
        target = flow.next or ROLE_HOME.get(Role(row["role"]), "/")
    response = RedirectResponse(target, status_code=303)
    set_session_cookie(response, token)
    _forget(response)
    return response


# ================================================================= the administrator's view

LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
CLIENT_ID_END = ".apps.googleusercontent.com"


def _is_ip(host: str | None) -> bool:
    try:
        ipaddress.ip_address(host or "")
    except ValueError:
        return False
    return True


@router.get("/api/v1/admin/google", tags=["admin"])
def google_status(request: Request, account: Account = ADMIN_ONLY) -> dict:
    """Whether sign-in with Google is on, and what to register with Google to turn it on.

    The client id is public (it rides in every address sent to Google); the
    client secret is never returned, only whether it is set.
    """
    settings = get_settings()
    redirect = _redirect_uri(request)
    target = urlparse(redirect)
    problems = []
    if not settings.google_client_id:
        problems.append("Chưa đặt AICEFR_GOOGLE_CLIENT_ID.")
    elif not settings.google_client_id.endswith(CLIENT_ID_END):
        problems.append(
            f"AICEFR_GOOGLE_CLIENT_ID không có dạng mã OAuth client của Google (…{CLIENT_ID_END})."
        )
    if not settings.google_client_secret:
        problems.append("Chưa đặt AICEFR_GOOGLE_CLIENT_SECRET.")
    if _is_ip(target.hostname) and target.hostname not in LOOPBACK:
        problems.append(
            "Google không nhận địa chỉ IP làm tên máy trong địa chỉ chuyển hướng (trừ localhost). "
            "Đặt AICEFR_PUBLIC_URL theo tên miền."
        )
    elif target.scheme != "https" and target.hostname not in LOOPBACK:
        problems.append(
            "Địa chỉ chuyển hướng dùng http:// trên một máy không phải localhost; Google chỉ "
            "nhận như vậy cho localhost. Đặt AICEFR_PUBLIC_URL=https://… và AICEFR_HTTPS_ONLY=on."
        )
    elif target.scheme == "https" and not settings.https_only:
        problems.append(
            "Trang chạy qua https nhưng AICEFR_HTTPS_ONLY chưa bật: cookie đăng nhập "
            "thiếu cờ Secure."
        )
    auth: AuthRepository = request.app.state.auth_repo
    return {
        "enabled": settings.google_enabled,
        "client_id": settings.google_client_id or None,
        "secret_set": bool(settings.google_client_secret),
        "redirect_uri": redirect,
        "redirect_from_public_url": bool(settings.public_url),
        "allowed_domain": settings.google_allowed_domain,
        "scopes": google.SCOPE,
        "flow_cookie": _cookie()[0],
        "linked_accounts": auth.count_identities(google.PROVIDER),
        "problems": problems,
    }
