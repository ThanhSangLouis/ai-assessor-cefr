"""Presentation-only adapter for the transferred browser pages."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from aicefr.contracts import ActorRole

_PACKAGE = Path(__file__).parent
_TEMPLATES = _PACKAGE / "templates"
_STATIC = _PACKAGE / "static"
_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(("html", "xml")),
    enable_async=False,
)


def _asset(path: str) -> str:
    try:
        version = int((_STATIC / path).stat().st_mtime)
    except OSError:
        return f"/static/{path}"
    return f"/static/{path}?v={version}"


_ENV.globals["asset"] = _asset


def _render(template: str, **context: object) -> str:
    return _ENV.get_template(template).render(api_docs=False, **context)


def _page_for(path: str) -> tuple[str, str, frozenset[ActorRole], dict[str, object]] | None:
    student = frozenset({ActorRole.STUDENT})

    if path == "/practice":
        return "practice_path.html", "practice", student, {}
    if path == "/practice/review":
        return "lesson.html", "practice", student, {"mode": "review", "lesson_id": ""}
    match = re.fullmatch(r"/practice/lessons/([^/]+)", path)
    if match:
        return "lesson.html", "practice", student, {"mode": "lesson", "lesson_id": match[1]}
    match = re.fullmatch(r"/practice/results/([^/]+)", path)
    if match:
        return "practice_result.html", "practice", student, {"response_id": match[1]}
    match = re.fullmatch(r"/practice/([^/]+)", path)
    if match:
        return "practice_task.html", "practice", student, {"task_id": match[1]}
    if path == "/my-progress":
        return "my_progress.html", "progress", student, {}
    return None


def dispatch_page(app, environ):
    """Serve SCRUM-74 student learning pages and their packaged assets.

    API calls continue through the existing WSGI API dispatchers. This adapter
    only authenticates page access and renders the transferred presentation.
    """
    from http import HTTPStatus

    from aicefr.api.wsgi import HttpInputError, WebResponse

    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = str(environ.get("PATH_INFO", "/"))

    if method == "GET" and path.startswith("/static/"):
        relative = unquote(path.removeprefix("/static/"))
        if not relative or "\\" in relative:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        target = (_STATIC / relative).resolve()
        try:
            target.relative_to(_STATIC.resolve())
        except ValueError:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from None
        if not target.is_file():
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "text/javascript"
        elif target.suffix == ".css":
            content_type = "text/css"
        elif target.suffix == ".svg":
            content_type = "image/svg+xml"
        elif target.suffix == ".woff2":
            content_type = "font/woff2"
        return WebResponse(
            HTTPStatus.OK,
            f"{content_type}; charset=utf-8" if content_type.startswith("text/") or content_type == "image/svg+xml" else content_type,
            target.read_bytes(),
            (("Cache-Control", "public, max-age=86400"),),
        )

    if method != "GET":
        return None
    route = _page_for(path)
    if route is None:
        return None
    if app._auth is None:
        raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")
    template, nav_here, roles, extra = route
    actor = app._auth.resolve(app._session_token(environ), allowed_roles=roles)
    account = SimpleNamespace(
        role=actor.role,
        pseudonym=actor.actor_id,
        avatar_color=None,
        avatar_icon=None,
        must_change_password=False,
    )
    context: dict[str, object] = {
        "account": account,
        "nav_here": nav_here,
        "max_size_mib": max(1, app._max_request_bytes // (1024 * 1024)),
        **extra,
    }
    return app._html(HTTPStatus.OK, _render(template, **context))
