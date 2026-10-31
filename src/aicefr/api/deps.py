"""Shared API-layer dependencies: resolve the current user and check roles.

Implements FR-32. Before this iteration, /review and POST /api/v1/review/{id}
were wide open: anyone who knew the path could change scores and set
teacher_verified. That broke the project's central argument -- "the machine
grades provisionally, the teacher decides" -- because teacher_verified became
meaningless and the audit log only recorded a self-declared identity.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from fastapi import Response as HttpResponse

from aicefr.auth.sessions import COOKIE_NAME, LIFETIME_HOURS
from aicefr.billing.plans import PlanFeature
from aicefr.config import get_settings
from aicefr.storage.auth_repository import Account, AuthRepository, Role

# Start page for each role after login, mirrored by the brand link in base.html.
ROLE_HOME = {Role.STUDENT: "/practice", Role.TEACHER: "/review", Role.ADMIN: "/admin"}

# What an account holding a temporary password may still call (D028): who am I,
# change the password, sign out. Everything else waits until the person has a
# password nobody else has seen.
PASSWORD_CHANGE_PATHS = frozenset(
    {"/api/v1/me", "/api/v1/me/account", "/api/v1/me/password", "/api/v1/auth/logout"}
)


def get_auth_repo(request: Request) -> AuthRepository:
    """Return the auth repository from the application state.

    It is not rebuilt on every call: each construction re-runs the table
    creation statements.
    """
    return request.app.state.auth_repo


def optional_account(request: Request) -> Account | None:
    """The current account, or None when nobody is logged in.

    Read through `app.state.callers` (D043): the session cookie where the
    sessions are (the identity service, or everything in one process), the
    gateway's account header in the other services.
    """
    return request.app.state.callers.for_request(request)


def require_login(
    request: Request,
    account: Account | None = Depends(optional_account),
) -> Account:
    if account is None:
        raise HTTPException(401, "chưa đăng nhập hoặc phiên đã hết hạn")
    if account.must_change_password and request.url.path not in PASSWORD_CHANGE_PATHS:
        raise HTTPException(
            403, "cần đặt mật khẩu mới thay cho mật khẩu tạm trước, ở trang /account"
        )
    return account


def require_role(*role: Role) -> Callable[..., Account]:
    """Build a dependency that only lets the listed roles through."""

    def check(account: Account = Depends(require_login)) -> Account:
        if account.role not in role:
            raise HTTPException(403, "tài khoản không có quyền thực hiện việc này")
        return account

    return check


# One dependency per kind of caller, shared by every router.
STUDENT_ONLY = Depends(require_role(Role.STUDENT))
STAFF_ONLY = Depends(require_role(Role.TEACHER, Role.ADMIN))
ADMIN_ONLY = Depends(require_role(Role.ADMIN))


def require_plan(plans, feature: PlanFeature) -> None:
    """403 with the reason and the plans that include it, when the plan in force
    does not (D034). `plans` is the billing service's facade; None means no
    plans, and nothing is locked."""
    if plans is None:
        return
    reason = plans.plan_refusal(feature=feature.value)
    if reason:
        raise HTTPException(403, reason)


def set_session_cookie(response: HttpResponse, token: str) -> None:
    """Hand the browser its session cookie: the same flags for every way of signing in."""
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        # Without Secure the browser sends the session cookie over plain HTTP
        # too, so anyone on the same network can read it. Off on localhost so
        # development still works; on behind TLS via AICEFR_HTTPS_ONLY.
        secure=get_settings().https_only,
        samesite="lax",
        max_age=LIFETIME_HOURS * 3600,
        path="/",
    )
