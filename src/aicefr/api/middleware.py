"""Cross-cutting request handling: correlation ids, access logs, security headers.

Middleware rather than per-endpoint code because every one of these has to
apply to every response, including the error paths. Anything you have to
remember to call on each endpoint is something you will eventually forget on
one of them -- and it will be the one that matters.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from aicefr.config import get_settings
from aicefr.infra.limits import InMemoryRateLimiter
from aicefr.observability import count, new_request_id, observe, request_id_var

logger = logging.getLogger("aicefr.access")

# Content-Security-Policy. The pages load their own stylesheet and scripts from
# /static and nothing else -- no CDN, by design -- so the policy can be strict.
# 'unsafe-inline' is allowed for style only because the admin screen carries a
# small inline <style>; scripts have no such exemption.
CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "media-src 'self' blob:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def _apply_security_headers(request: Request, response: Response) -> Response:
    response.headers.setdefault("Content-Security-Policy", CSP)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    # The microphone is needed by this origin only; everything else is off.
    response.headers.setdefault(
        "Permissions-Policy", "microphone=(self), camera=(), geolocation=()"
    )
    if get_settings().https_only:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    # Reports and audio are personal data; no shared cache may keep them.
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "private, no-store")
    return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Give every request an id, log how it went, and time it."""

    async def dispatch(self, request: Request, call_next):
        # Honour an inbound id so a reverse proxy or a client can stitch traces
        # together, but generate one when absent.
        rid = request.headers.get("x-request-id") or new_request_id()
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = (time.perf_counter() - started) * 1000
            logger.exception(
                "unhandled error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round(duration, 1),
                },
            )
            count("requests_failed_total")
            # Never leak a traceback to the client: it names internal paths and
            # module layout.
            response = JSONResponse({"detail": "lỗi nội bộ, vui lòng thử lại"}, status_code=500)
            response.headers["x-request-id"] = rid
            _apply_security_headers(request, response)
            request_id_var.reset(token)
            return response

        duration = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = rid
        # Static assets are noise in an access log; skip them.
        if not request.url.path.startswith("/static/"):
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration, 1),
                },
            )
        count("requests_total")
        if response.status_code >= 500:
            count("requests_failed_total")
        if not request.url.path.startswith("/static/"):
            # The route's template, never the path itself: a path holds ids.
            route = getattr(request.scope.get("route"), "path", None) or "unmatched"
            observe("http_request_seconds", duration / 1000, method=request.method, route=route,
                    status=f"{response.status_code // 100}xx")  # fmt: skip
        request_id_var.reset(token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers that turn off browser behaviour this application never wants."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        return _apply_security_headers(request, response)


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Cap login attempts per client address.

    The per-account lockout already stops an attacker grinding one account.
    This stops the other shape of the same attack: one guess, every account.
    Kept in memory on purpose -- a single process serves this deployment, and a
    shared store would be a dependency bought for very little.
    """

    PATH = "/api/v1/auth/login"

    def __init__(self, app) -> None:
        super().__init__(app)
        self._limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next):
        if request.url.path != self.PATH or request.method != "POST":
            return await call_next(request)

        limit = get_settings().login_attempts_per_minute
        who = request.client.host if request.client else "unknown"
        if not self._limiter.hit(who, limit):
            count("login_rate_limited_total")
            logger.warning("login rate limit hit", extra={"event": "rate_limit"})
            return JSONResponse(
                {"detail": "quá nhiều lần đăng nhập, thử lại sau một phút"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
