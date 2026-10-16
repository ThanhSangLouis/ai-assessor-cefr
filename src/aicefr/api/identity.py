"""Stable HTTP boundary for M11 identity, account, and Google routes."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from html import escape
from http import HTTPStatus
from urllib.parse import parse_qs

from aicefr.api.wsgi import HttpInputError, WebResponse
from aicefr.auth.contracts import PROFILE_COLORS, PROFILE_ICONS, AccountCreate
from aicefr.auth.errors import (
    AccountError,
    ConflictError,
    LockoutError,
    NotFoundError,
)
from aicefr.auth.errors import (
    AuthorizationError as AccountAuthorizationError,
)
from aicefr.auth.errors import (
    ResourceNotFound as AccountNotFound,
)
from aicefr.auth.errors import (
    ValidationError as AccountValidationError,
)
from aicefr.auth.service import AuthorizationError
from aicefr.contracts import ActorRole

_API_PATHS = {
    "/password-change",
    "/api/v1/me",
    "/api/v1/me/profile",
    "/api/v1/me/password",
    "/api/v1/me/sessions",
    "/api/v1/me/sessions/revoke-others",
    "/api/v1/me/activity",
    "/api/v1/me/consent",
    "/api/v1/me/google",
    "/api/v1/admin/accounts",
    "/api/v1/admin/google",
}
_GOOGLE_PATHS = {"/auth/google/start", "/auth/google/callback"}


def _plain(value):
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (datetime,)):
        return value.astimezone(UTC).isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "value"):
        return value.value
    return value


class IdentityApi:
    """Narrow adapter; business rules remain in AuthService/AccountService."""

    def __init__(self, auth, accounts, google=None) -> None:
        self.auth = auth
        self.accounts = accounts
        self.google = google

    @staticmethod
    def owns(path: str) -> bool:
        return (
            path in _API_PATHS
            or path.startswith("/api/v1/me/sessions/")
            or (path.startswith("/api/v1/admin/accounts/"))
            or path in _GOOGLE_PATHS
        )

    def dispatch(self, app, environ) -> WebResponse | None:
        path = str(environ.get("PATH_INFO", "/"))
        if not self.owns(path):
            return None
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            return self._dispatch(app, environ, method, path)
        except HttpInputError:
            raise
        except LockoutError as error:
            return self._with_headers(
                app._json(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    {"error": "LOGIN_LOCKED", "retry_after": error.retry_after},
                ),
                (("Retry-After", str(error.retry_after)),),
            )
        except AccountValidationError as error:
            return app._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": _safe_code(error.code)})
        except ConflictError as error:
            return app._json(HTTPStatus.CONFLICT, {"error": _safe_code(error.code)})
        except (AccountNotFound, NotFoundError):
            return app._json(HTTPStatus.NOT_FOUND, {"error": "RESOURCE_UNAVAILABLE"})
        except AccountAuthorizationError as error:
            forbidden = error.code in {
                "forbidden",
                "access_denied",
                "role_required",
                "password_change_required",
            }
            public_code = (
                "PASSWORD_CHANGE_REQUIRED"
                if error.code == "password_change_required"
                else "ACCESS_DENIED"
            )
            return app._json(
                HTTPStatus.FORBIDDEN if forbidden else HTTPStatus.UNAUTHORIZED,
                {"error": public_code if forbidden else "SESSION_REQUIRED"},
            )
        except AccountError as error:
            return app._json(HTTPStatus.BAD_REQUEST, {"error": _safe_code(error.code)})
        except AuthorizationError:
            return app._json(HTTPStatus.UNAUTHORIZED, {"error": "SESSION_REQUIRED"})
        except Exception as error:
            from aicefr.auth.google import GoogleIdentityError

            if isinstance(error, GoogleIdentityError):
                status = HTTPStatus(error.status_code)
                return app._json(status, {"error": _safe_code(error.code)})
            raise

    def _dispatch(self, app, environ, method: str, path: str) -> WebResponse:
        if path == "/auth/google/start":
            if self.google is None:
                return self._google_disabled(app)
            # Login start is a safe navigation; link intent is POST-only and CSRF protected.
            values = self._query(environ)
            intent = values.get("intent", ["login"])[0]
            token = None
            if intent == "link":
                if method != "POST":
                    return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
                app._require_origin(environ)
                token = app._session_token(environ, unsafe=True)
            elif intent != "login" or method != "GET":
                return app._json(HTTPStatus.BAD_REQUEST, {"error": "INVALID_REQUEST"})
            started = self.google.start(intent=intent, token=token)
            secure = bool(getattr(self.google.config, "cookie_secure", False))
            cookie = self._flow_cookie(started.flow_cookie, secure=secure)
            return WebResponse(
                HTTPStatus.SEE_OTHER,
                "text/plain; charset=utf-8",
                b"",
                (("Location", started.authorization_url), ("Set-Cookie", cookie)),
            )

        if path == "/auth/google/callback":
            if self.google is None:
                return self._google_disabled(app)
            secure = bool(getattr(self.google.config, "cookie_secure", False))
            clear = self._clear_flow_cookie(secure)
            try:
                if method != "GET":
                    return self._with_headers(
                        app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"}),
                        (("Set-Cookie", clear),),
                    )
                values = self._query(environ, allowed={"state", "code", "error"})
                if "error" in values or set(values) != {"state", "code"}:
                    return self._with_headers(
                        app._json(HTTPStatus.UNAUTHORIZED, {"error": "GOOGLE_LOGIN_FAILED"}),
                        (("Set-Cookie", clear),),
                    )
                flow_cookie_name = "__Host-aicefr_google_flow" if secure else "aicefr_google_flow"
                flow_cookie = self._cookie(environ, flow_cookie_name)
                result = self.google.callback(
                    flow_cookie,
                    values["state"][0],
                    values["code"][0],
                    token=self._optional_session_token(environ),
                )
                headers = [("Set-Cookie", clear)]
                if result.session_token:
                    headers.append(
                        ("Set-Cookie", self._session_cookie(result.session_token, secure=secure))
                    )
                return self._with_headers(
                    app._json(
                        HTTPStatus.OK, {"outcome": result.outcome, "actor_id": result.actor_id}
                    ),
                    tuple(headers),
                )
            except HttpInputError:
                return self._with_headers(
                    app._json(HTTPStatus.BAD_REQUEST, {"error": "INVALID_REQUEST"}),
                    (("Set-Cookie", clear),),
                )
            except Exception as error:
                from aicefr.auth.google import GoogleIdentityError

                if isinstance(error, GoogleIdentityError):
                    return self._with_headers(
                        app._json(HTTPStatus(error.status_code), {"error": _safe_code(error.code)}),
                        (("Set-Cookie", clear),),
                    )
                return self._with_headers(
                    app._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "REQUEST_FAILED"}),
                    (("Set-Cookie", clear),),
                )

        if path.startswith("/api/v1/admin/google"):
            token = self._token(app, environ)
            self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
            if path != "/api/v1/admin/google" or method != "GET":
                return app._json(HTTPStatus.NOT_FOUND, {"error": "ROUTE_NOT_FOUND"})
            if self.google is None:
                return app._json(HTTPStatus.OK, {"enabled": False, "ready": False})
            return app._json(HTTPStatus.OK, self.google.status())

        if path == "/password-change":
            if method == "POST":
                self._write_origin(app, environ)
                token = app._session_token(environ, unsafe=True)
                self.auth.resolve(token, allow_temporary=True)
                try:
                    body = app._request_values(environ)
                except (ValueError, TypeError):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
                if set(body) != {
                    "current_password",
                    "new_password",
                    "confirm_password",
                } or not all(
                    isinstance(body.get(field), str)
                    for field in ("current_password", "new_password", "confirm_password")
                ):
                    raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
                if body["new_password"] != body["confirm_password"]:
                    return app._html(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        self._password_page("Mật khẩu mới chưa khớp."),
                    )
                rotated = self.accounts.change_password(
                    token, body["current_password"], body["new_password"]
                )
                actor = self.auth.resolve(rotated, allow_temporary=True)
                destination = {
                    ActorRole.STUDENT: "/student/consent",
                    ActorRole.TEACHER: "/teacher/reviews",
                    ActorRole.ADMIN: "/admin",
                }[actor.role]
                return WebResponse(
                    HTTPStatus.SEE_OTHER,
                    "text/plain; charset=utf-8",
                    b"",
                    (
                        ("Location", destination),
                        (
                            "Set-Cookie",
                            self._session_cookie(rotated, secure=self._request_secure(environ)),
                        ),
                    ),
                )
            if method != "GET":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            token = app._session_token(environ)
            self.auth.resolve(token, allow_temporary=True)
            return WebResponse(
                HTTPStatus.OK,
                "text/html; charset=utf-8",
                self._password_page().encode("utf-8"),
            )

        if path == "/api/v1/me/google":
            token = self._token(app, environ, unsafe=method != "GET")
            self.auth.resolve(token)
            if method == "GET":
                if self.google is None:
                    return app._json(HTTPStatus.OK, {"linked": False, "enabled": False})
                return app._json(
                    HTTPStatus.OK,
                    {
                        "linked": self.google.is_linked(token),
                        "enabled": self.google.status()["ready"],
                    },
                )
            if method == "POST":
                self._write_origin(app, environ)
                if self.google is None:
                    return self._google_disabled(app)
                self.google.unlink(token)
                return app._json(HTTPStatus.OK, {"linked": False})
            return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})

        if path == "/api/v1/me":
            if method != "GET":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            token = self._token(app, environ, allow_temporary=True)
            profile = self.accounts.get_profile(token)
            return app._json(
                HTTPStatus.OK,
                {
                    "profile": _plain(profile),
                    "catalog": {
                        "goals": [1, 2, 3, 5, 10],
                        "icons": sorted(PROFILE_ICONS),
                        "colors": sorted(PROFILE_COLORS),
                    },
                },
            )

        if path == "/api/v1/me/profile":
            token = self._token(
                app,
                environ,
                unsafe=method != "GET",
                allow_temporary=method == "GET",
            )
            if method == "GET":
                return app._json(HTTPStatus.OK, _plain(self.accounts.get_profile(token)))
            if method != "PATCH":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            body = self._body(app, environ, {"goal", "icon", "color"})
            updated = self.accounts.update_profile(token, **body)
            return app._json(HTTPStatus.OK, _plain(updated))

        if path == "/api/v1/me/password":
            if method != "POST":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            token = app._session_token(environ, unsafe=True)
            self.auth.resolve(token, allow_temporary=True)
            body = self._body(app, environ, {"current_password", "new_password"})
            if not all(
                isinstance(body.get(field), str) for field in ("current_password", "new_password")
            ):
                raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
            rotated = self.accounts.change_password(
                token, body.get("current_password"), body.get("new_password")
            )
            secure = self._request_secure(environ)
            return self._with_headers(
                app._json(HTTPStatus.OK, {"changed": True}),
                (("Set-Cookie", self._session_cookie(rotated, secure=secure)),),
            )

        if path == "/api/v1/me/sessions" and method == "GET":
            token = self._token(app, environ)
            return app._json(
                HTTPStatus.OK, {"sessions": _plain(self.accounts.list_sessions(token))}
            )

        if path.startswith("/api/v1/me/sessions/") and path != "/api/v1/me/sessions/revoke-others":
            token = self._token(app, environ, unsafe=True)
            if method != "DELETE":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            session_id = path.removeprefix("/api/v1/me/sessions/")
            if not session_id or "/" in session_id:
                return app._json(HTTPStatus.NOT_FOUND, {"error": "RESOURCE_UNAVAILABLE"})
            current = self.accounts.revoke_session(token, session_id)
            headers = (
                (
                    (
                        "Set-Cookie",
                        self._clear_session_cookie(secure=self._request_secure(environ)),
                    ),
                )
                if current
                else ()
            )
            return self._with_headers(
                app._json(HTTPStatus.OK, {"revoked": True, "current": current}), headers
            )

        if path == "/api/v1/me/sessions/revoke-others":
            if method != "POST":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            token = app._session_token(environ, unsafe=True)
            revoked = self.accounts.revoke_other_sessions(token)
            return app._json(HTTPStatus.OK, {"revoked": revoked})

        if path == "/api/v1/me/activity" and method == "GET":
            token = self._token(app, environ)
            query = self._query(environ, allowed={"limit", "offset"})
            try:
                limit = int(query.get("limit", ["50"])[0])
                offset = int(query.get("offset", ["0"])[0])
            except ValueError as error:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
            if not 1 <= limit <= 100 or not 0 <= offset <= 100_000:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return app._json(
                HTTPStatus.OK, {"items": _plain(self.accounts.activity(token, limit, offset))}
            )

        if path == "/api/v1/me/consent":
            token = self._token(app, environ, unsafe=method != "GET")
            if method == "GET":
                return app._json(HTTPStatus.OK, _plain(self.accounts.consent(token)))
            if method != "POST":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            body = self._body(app, environ, {"version", "research_allowed", "active"})
            consent = self.accounts.set_consent(
                token,
                body.get("version"),
                body.get("research_allowed"),
                body.get("active", True),
            )
            return app._json(HTTPStatus.OK, _plain(consent))

        if path == "/api/v1/admin/accounts":
            token = self._token(app, environ, unsafe=method != "GET")
            if method == "GET":
                actor = self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
                rows = self.accounts.repository.list_accounts(actor)
                return app._json(HTTPStatus.OK, {"accounts": _plain(rows)})
            if method != "POST":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            body = self._body(app, environ, {"accounts"})
            rows = body.get("accounts")
            if not isinstance(rows, list):
                raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
            if not 1 <= len(rows) <= 200 or any(not isinstance(row, dict) for row in rows):
                raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
            creates = []
            for row in rows:
                if set(row) - {"actor_id", "role", "goal"} or not {"actor_id", "role"}.issubset(
                    row
                ):
                    raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
                try:
                    creates.append(
                        AccountCreate(row["actor_id"], ActorRole(row["role"]), row.get("goal"))
                    )
                except (TypeError, ValueError) as error:
                    raise HttpInputError(
                        HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST"
                    ) from error
            created = self.accounts.create_accounts(token, creates)
            return app._json(HTTPStatus.CREATED, {"accounts": _plain(created)})

        if path.startswith("/api/v1/admin/accounts/"):
            if method != "POST":
                return app._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "METHOD_NOT_ALLOWED"})
            self._write_origin(app, environ)
            token = app._session_token(environ, unsafe=True)
            suffix = path.removeprefix("/api/v1/admin/accounts/").split("/")
            if len(suffix) != 2 or not all(suffix):
                return app._json(HTTPStatus.NOT_FOUND, {"error": "RESOURCE_UNAVAILABLE"})
            target_id, action = suffix
            body = self._body(app, environ, {"role"}) if self._body_present(environ) else {}
            role = body.get("role")
            if role is not None:
                try:
                    role = ActorRole(role)
                except (TypeError, ValueError) as error:
                    raise HttpInputError(
                        HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST"
                    ) from error
            value = self.accounts.admin_action(token, target_id, action, role=role)
            return app._json(HTTPStatus.OK, _plain(value))

        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    @staticmethod
    def _safe_code(code: str) -> str:
        return _safe_code(code)

    @staticmethod
    def _body(app, environ, allowed: set[str]) -> dict:
        content_type = str(environ.get("CONTENT_TYPE", "")).lower().split(";", 1)[0].strip()
        if content_type != "application/json":
            raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")
        raw = app._read_body(environ)

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result

        try:
            body = json.loads(raw, object_pairs_hook=unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
        if not isinstance(body, dict):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        if set(body) - allowed:
            raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_REQUEST")
        return body

    @staticmethod
    def _body_present(environ) -> bool:
        return str(environ.get("CONTENT_LENGTH", "")) not in {"", "0"}

    @staticmethod
    def _query(environ, allowed: set[str] | None = None) -> dict[str, list[str]]:
        try:
            query = parse_qs(
                str(environ.get("QUERY_STRING", "")), keep_blank_values=True, max_num_fields=8
            )
        except ValueError as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
        if any(len(items) != 1 for items in query.values()) or (
            allowed is not None and set(query) - allowed
        ):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        return query

    @staticmethod
    def _cookie(environ, name: str) -> str:
        for item in str(environ.get("HTTP_COOKIE", "")).split(";"):
            key, equals, value = item.strip().partition("=")
            if key == name and equals and value:
                return value
        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

    @staticmethod
    def _optional_session_token(environ) -> str | None:
        secure = str(environ.get("wsgi.url_scheme", "http")).lower() == "https"
        cookie_name = "__Host-aicefr_session" if secure else "aicefr_session"
        for item in str(environ.get("HTTP_COOKIE", "")).split(";"):
            key, equals, value = item.strip().partition("=")
            if key == cookie_name and equals and value:
                return value
        authorization = str(environ.get("HTTP_AUTHORIZATION", ""))
        return authorization[7:] if authorization.startswith("Bearer ") else None

    @staticmethod
    def _token(app, environ, *, unsafe: bool = False, allow_temporary: bool = False) -> str:
        token = app._session_token(environ, unsafe=unsafe)
        # Bearer remains supported for API clients; unsafe cookie writes require Origin.
        if unsafe and not str(environ.get("HTTP_AUTHORIZATION", "")).startswith("Bearer "):
            app._require_origin(environ)
        if app._auth is None:
            raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")
        app._auth.resolve(token, allow_temporary=allow_temporary)
        return token

    @staticmethod
    def _require_origin(app, environ) -> None:
        app._require_origin(environ)

    @staticmethod
    def _write_origin(app, environ) -> None:
        if not str(environ.get("HTTP_AUTHORIZATION", "")).startswith("Bearer "):
            app._require_origin(environ)

    @staticmethod
    def _request_secure(environ) -> bool:
        return str(environ.get("wsgi.url_scheme", "http")).lower() == "https"

    @staticmethod
    def _session_cookie(token: str, *, secure: bool) -> str:
        name = "__Host-aicefr_session" if secure else "aicefr_session"
        suffix = "; Secure" if secure else ""
        return f"{name}={token}; HttpOnly; SameSite=Lax; Path=/{suffix}"

    @staticmethod
    def _clear_session_cookie(*, secure: bool) -> str:
        name = "__Host-aicefr_session" if secure else "aicefr_session"
        suffix = "; Secure" if secure else ""
        return f"{name}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0{suffix}"

    @staticmethod
    def _flow_cookie(value: str, *, secure: bool) -> str:
        name = "__Host-aicefr_google_flow" if secure else "aicefr_google_flow"
        path = "/" if secure else "/auth/google/"
        suffix = "; Secure" if secure else ""
        return f"{name}={value}; HttpOnly; SameSite=Lax; Path={path}; Max-Age=600{suffix}"

    @staticmethod
    def _clear_flow_cookie(secure: bool) -> str:
        name = "__Host-aicefr_google_flow" if secure else "aicefr_google_flow"
        path = "/" if secure else "/auth/google/"
        suffix = "; Secure" if secure else ""
        return f"{name}=; HttpOnly; SameSite=Lax; Path={path}; Max-Age=0{suffix}"

    @staticmethod
    def _with_headers(response: WebResponse, headers) -> WebResponse:
        return WebResponse(
            response.status, response.content_type, response.body, response.headers + tuple(headers)
        )

    @staticmethod
    def _google_disabled(app) -> WebResponse:
        return app._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "GOOGLE_UNAVAILABLE"})

    @staticmethod
    def _password_page(message: str | None = None) -> str:
        from aicefr.api.templates import _document

        notice = f'<p role="status">{escape(message)}</p>' if message else ""
        body = (
            "<h2>Đổi mật khẩu tạm thời</h2>"
            "<p>Hãy đặt mật khẩu mới để tiếp tục sử dụng tài khoản.</p>"
            f'{notice}<form method="post" action="/password-change">'
            '<label>Mật khẩu hiện tại<input name="current_password" '
            'type="password" autocomplete="current-password" required></label>'
            '<label>Mật khẩu mới<input name="new_password" type="password" '
            'autocomplete="new-password" minlength="8" required></label>'
            '<label>Nhập lại mật khẩu mới<input name="confirm_password" '
            'type="password" autocomplete="new-password" minlength="8" required></label>'
            '<button type="submit">Đổi mật khẩu</button></form>'
        )
        return _document("Đổi mật khẩu", body)


def _safe_code(code: str) -> str:
    # Service codes are fixed constants. Normalize defensively in case an error
    # carries internal detail rather than a public code.
    normalized = "".join(char for char in str(code).upper() if char.isalnum() or char == "_")
    return normalized[:48] or "REQUEST_FAILED"
