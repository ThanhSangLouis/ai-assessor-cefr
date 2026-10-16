"""Presentation-only adapter for the transferred browser pages."""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote, unquote

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
    teachers = frozenset({ActorRole.TEACHER, ActorRole.ADMIN})

    if path == "/admin":
        return "admin.html", "admin", frozenset({ActorRole.ADMIN}), {}
    if path == "/admin/ratings":
        return "admin_ratings.html", "admin", frozenset({ActorRole.ADMIN}), {}
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
    if path in {"/review", "/teacher/reviews"}:
        return "queue.html", "queue", teachers, {}
    if re.fullmatch(r"/(?:review|teacher/reviews)/[^/]+", path):
        return "review_one.html", "queue", teachers, {}
    if path == "/rate":
        return "rate_list.html", "rate", teachers, {}
    match = re.fullmatch(r"/rate/([^/]+)", path)
    if match:
        return "rate_one.html", "rate", teachers, {"assignment_id": match[1]}
    if path == "/teach":
        return "teach_paths.html", "teach", teachers, {}
    match = re.fullmatch(r"/teach/lessons/([^/]+)", path)
    if match:
        return "teach_lesson.html", "teach", teachers, {"lesson_id": match[1]}
    if path == "/teach/insights":
        return "teach_insights.html", "teach", teachers, {}
    return None


def dispatch_page(app, environ):
    """Serve transferred student and teacher pages plus packaged assets.

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
        if content_type.startswith("text/") or content_type == "image/svg+xml":
            content_type = f"{content_type}; charset=utf-8"
        return WebResponse(
            HTTPStatus.OK,
            content_type,
            target.read_bytes(),
            (("Cache-Control", "public, max-age=86400"),),
        )

    if method != "GET":
        return None
    route = _page_for(path)
    if route is None or app._auth is None:
        # Preserve existing WSGI/API routes for apps constructed without the
        # page-level AuthService (for example, ReviewApi-owned test fixtures).
        return None
    template, nav_here, roles, extra = route
    actor = app._auth.resolve(app._session_token(environ), allowed_roles=roles)
    if template == "rate_one.html":
        extra = {
            **extra,
            "criteria": ("range", "accuracy", "fluency", "coherence", "phonology"),
            "bands": ("A2", "B1", "B2"),
            "unscorable_reasons": {
                "broken": "Bản ghi bị lỗi",
                "inaudible": "Không nghe rõ",
                "off_task": "Không đúng nội dung đề bài",
            },
        }
    review_match = re.fullmatch(r"/(?:review|teacher/reviews)/([^/]+)", path)
    if review_match:
        from datetime import UTC, datetime

        from markupsafe import Markup

        from aicefr.api.templates import render_report_content
        from aicefr.contracts import ReviewState
        from aicefr.review.service import claim_expired

        response_id = review_match[1]
        if app._reviews is None or app._reports is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        research = app._research_api
        if research is not None:
            if not research.service.may_view_machine(actor.actor_id, response_id):
                raise HttpInputError(HTTPStatus.FORBIDDEN, "BLIND_RATING_ACTIVE")
            research.service.mark_machine_seen(actor.actor_id, response_id, "review_detail")
        candidate = app._reviews.get(response_id)
        if candidate is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        report = app._reports.get(response_id)
        record = app._responses.metadata.get_response(response_id) if app._responses else None
        expired_claim = claim_expired(candidate, datetime.now(UTC))
        can_review = candidate.state in {ReviewState.PENDING, ReviewState.IN_REVIEW} and (
            candidate.claimed_by in {None, actor.actor_id} or expired_claim
        )
        claim_action = None
        if can_review:
            if candidate.state is ReviewState.PENDING or expired_claim:
                claim_action = "claim"
            elif candidate.claimed_by == actor.actor_id:
                claim_action = "release"
        extra = {
            **extra,
            "response_id": response_id,
            "response_path": quote(response_id, safe=""),
            "candidate": candidate,
            "report_html": Markup(render_report_content(report)) if report else None,
            "audio_available": record.audio_available if record else app._responses is None,
            "claim_action": claim_action,
            "can_review": can_review,
        }
        template = "review_one.html"
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
