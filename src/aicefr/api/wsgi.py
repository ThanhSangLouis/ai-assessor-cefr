"""Dependency-injected WSGI surface for student upload and teacher review.

The local application exposes fixture-account login through M08. API clients
may also supply an existing M08 session as a Bearer token.
"""

from __future__ import annotations

import ipaddress
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from pydantic import ValidationError

from aicefr.api.review import ReviewApi
from aicefr.api.student import (
    StudentApi,
    SubmissionError,
    SubmitRequest,
    student_trust_summary,
)
from aicefr.api.templates import (
    LOCAL_CSS,
    render_consent,
    render_login,
    render_notice,
    render_report,
    render_review_detail,
    render_review_queue,
    render_student_status,
    render_upload_form,
)
from aicefr.auth.errors import LockoutError
from aicefr.auth.service import AuthorizationError, AuthService, ConsentService, ResourceNotFound
from aicefr.contracts import ActorRole, ConsentState
from aicefr.limits import RateLimiter
from aicefr.report.contracts import DiagnosticReport
from aicefr.report.service import ReportNotFound, UnverifiedReviewDecision
from aicefr.review.service import (
    InvalidReviewTransition,
    ReviewActionRequest,
    ReviewNotFound,
    StaleReview,
)
from aicefr.storage.service import ResponseService

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def _coarse_device_category(user_agent: str) -> str:
    """Reduce browser metadata to a small category; never retain the raw header."""
    value = user_agent.lower()
    if "ipad" in value or "tablet" in value or ("android" in value and "mobile" not in value):
        return "tablet"
    if "iphone" in value or "ipod" in value or ("android" in value and "mobile" in value):
        return "mobile"
    if any(marker in value for marker in ("windows", "macintosh", "mac os x", "x11", "linux")):
        return "desktop"
    return "unknown"


class HttpInputError(ValueError):
    def __init__(self, status: HTTPStatus, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


def _trust_recovery(reasons: tuple[Any, ...]) -> str | None:
    """Student-facing recovery text uses stable reasons only."""
    values = {getattr(reason, "value", str(reason)) for reason in reasons}
    if values & {"CALIBRATION_MISSING", "CALIBRATION_INVALID", "CALIBRATION_HASH_MISMATCH"}:
        return "Kết quả đang chờ kiểm tra; hãy xem lại sau hoặc hỏi giảng viên."
    if "LANGUAGE_NOT_ENGLISH" in values:
        return "Hãy ghi lại câu trả lời bằng tiếng Anh."
    if "LANGUAGE_UNCERTAIN" in values:
        return "Hãy ghi lại câu trả lời rõ tiếng Anh hơn."
    if values & {"OFF_TOPIC_SUSPECTED", "PROMPT_READING_SUSPECTED", "SCORE_NEAR_BOUNDARY"}:
        return "Giảng viên cần xem lại kết quả trước khi sử dụng."
    return None


def _bounded_versions(values: dict[str, str], *, max_value: int = 160) -> dict[str, str]:
    """Drop oversized values and path-like strings from external report payloads."""
    return {
        key: value
        for key, value in values.items()
        if isinstance(key, str)
        and isinstance(value, str)
        and len(key) <= 64
        and len(value) <= max_value
        and "/" not in value
        and "\\" not in value
    }


@dataclass(frozen=True)
class WebResponse:
    status: HTTPStatus
    content_type: str
    body: bytes
    headers: tuple[tuple[str, str], ...] = ()


class StudentTeacherApp:
    """HTTP/UI adapter with explicit, bounded request parsing.

    This is intentionally framework-free so the assessed service contracts can
    be checked without a web-server dependency.  Production hosting still
    chooses TLS, session issuance and deployment through the M08 owner.
    """

    _SECURITY_HEADERS = (
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        (
            "Content-Security-Policy",
            "default-src 'self'; media-src 'self' blob:; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        ),
    )

    def __init__(
        self,
        student_api: StudentApi,
        *,
        review_api: ReviewApi | None = None,
        auth: AuthService | None = None,
        consents: ConsentService | None = None,
        responses: ResponseService | None = None,
        reviews: Any | None = None,
        reports: Any | None = None,
        consent_version: str = "local-v1",
        demo: bool = False,
        max_request_bytes: int = 10 * 1024 * 1024,
        portal: Any | None = None,
        metrics: Any | None = None,
    ) -> None:
        if max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be positive")
        self._student_api = student_api
        self._review_api = review_api
        self._auth = auth
        self._consents = consents
        self._responses = responses
        self._reviews = reviews
        self._reports = reports
        self._consent_version = consent_version
        self._demo = demo
        self._max_request_bytes = max_request_bytes
        self._portal = portal
        self._metrics = metrics
        self._limiter = RateLimiter()

    def __call__(self, environ: dict[str, Any], start_response: StartResponse) -> list[bytes]:
        try:
            response = self._dispatch(environ)
        except HttpInputError as error:
            response = self._controlled_error(environ, error.status, error.code)
        except SubmissionError as error:
            response = self._controlled_error(
                environ, HTTPStatus.UNPROCESSABLE_ENTITY, error.code.value
            )
        except ResourceNotFound:
            response = self._controlled_error(environ, HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        except LockoutError:
            response = self._controlled_error(environ, HTTPStatus.TOO_MANY_REQUESTS, "LOGIN_LOCKED")
        except AuthorizationError as error:
            if error.code == "password_change_required":
                response = self._controlled_error(
                    environ, HTTPStatus.FORBIDDEN, "PASSWORD_CHANGE_REQUIRED"
                )
            elif error.code in {"access denied", "access_denied"}:
                response = self._controlled_error(environ, HTTPStatus.FORBIDDEN, "ACCESS_DENIED")
            else:
                response = self._controlled_error(
                    environ, HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED"
                )
        except ReviewNotFound:
            response = self._controlled_error(environ, HTTPStatus.NOT_FOUND, "REVIEW_UNAVAILABLE")
        except (StaleReview, InvalidReviewTransition):
            response = self._controlled_error(environ, HTTPStatus.CONFLICT, "STALE_OR_FINAL_REVIEW")
        except (ReportNotFound, UnverifiedReviewDecision):
            response = self._controlled_error(environ, HTTPStatus.CONFLICT, "REPORT_NOT_READY")
        except ValidationError:
            response = self._controlled_error(environ, HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        except Exception:
            # Do not leak internal paths, database details, or submitted content.
            response = self._controlled_error(
                environ, HTTPStatus.INTERNAL_SERVER_ERROR, "REQUEST_FAILED"
            )
        if self._metrics is not None:
            self._metrics.record(str(environ.get("PATH_INFO", "")), response.status.value)
        headers = [
            ("Content-Type", response.content_type),
            ("Content-Length", str(len(response.body))),
            ("X-Request-ID", uuid.uuid4().hex),
            *self._SECURITY_HEADERS,
            *response.headers,
        ]
        start_response(f"{response.status.value} {response.status.phrase}", headers)
        return [response.body]

    @classmethod
    def _controlled_error(
        cls, environ: dict[str, Any], status: HTTPStatus, code: str
    ) -> WebResponse:
        path = str(environ.get("PATH_INFO", ""))
        if path.startswith("/api/"):
            return cls._json(status, {"error": code})
        messages = {
            "SESSION_REQUIRED": "Vui lòng đăng nhập để tiếp tục.",
            "PASSWORD_CHANGE_REQUIRED": "Hãy đổi mật khẩu tạm thời trước khi tiếp tục.",
            "ACCESS_DENIED": "Tài khoản không được phép thực hiện thao tác này.",
            "CSRF_ORIGIN_REQUIRED": "Yêu cầu không hợp lệ. Hãy tải lại trang và thử lại.",
            "RESOURCE_UNAVAILABLE": "Không tìm thấy nội dung hoặc bạn không có quyền truy cập.",
            "REQUEST_TOO_LARGE": "Tệp gửi lên vượt giới hạn.",
            "UNSUPPORTED_REQUEST_FORMAT": "Định dạng yêu cầu không được hỗ trợ.",
            "REQUEST_FAILED": "Không thể xử lý yêu cầu. Vui lòng thử lại.",
            "CONSENT_VERSION_STALE": (
                "Nội dung đồng ý đã thay đổi. Hãy đọc và xác nhận phiên bản hiện tại."
            ),
            "RATE_LIMITED": "Bạn thao tác quá nhiều lần. Hãy đợi một phút rồi thử lại.",
            "STALE_REVISION": "Dữ liệu đã thay đổi. Hãy tải lại trang trước khi lưu.",
            "REPORT_NOT_READY": "Báo cáo chưa sẵn sàng. Hãy đợi xử lý bài và tải lại trang.",
            "STALE_OR_FINAL_REVIEW": (
                "Bài đã thay đổi hoặc có người khác nhận duyệt. Hãy tải lại hàng đợi."
            ),
        }
        return cls._html(
            status,
            render_notice(
                "Không thể xử lý yêu cầu", messages.get(code, "Thông tin gửi lên không hợp lệ.")
            ),
        )

    def _dispatch(self, environ: dict[str, Any]) -> WebResponse:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", "/"))
        if self._portal is not None:
            portal_response = self._portal.dispatch(self, environ)
            if portal_response is not None:
                return portal_response
        if path == "/" and method == "GET":
            return WebResponse(
                HTTPStatus.SEE_OTHER, "text/plain; charset=utf-8", b"", (("Location", "/login"),)
            )
        if path == "/login":
            if method == "GET":
                return self._html(HTTPStatus.OK, render_login(demo=self._demo))
            if method == "POST":
                return self._login(environ)
        if path == "/local.css" and method == "GET":
            return WebResponse(
                HTTPStatus.OK,
                "text/css; charset=utf-8",
                LOCAL_CSS.encode("utf-8"),
                (("Cache-Control", "public, max-age=300"),),
            )
        if path in {"/recorder.js", "/report.js"} and method == "GET":
            return WebResponse(
                HTTPStatus.OK,
                "text/javascript; charset=utf-8",
                (Path(__file__).parent / "static" / path.removeprefix("/")).read_bytes(),
            )
        if path == "/logout" and method == "POST":
            self._require_origin(environ)
            token = self._session_token(environ, unsafe=True)
            if self._auth is None:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
            self._auth.logout(token)
            return WebResponse(
                HTTPStatus.SEE_OTHER,
                "text/plain; charset=utf-8",
                b"",
                (
                    ("Location", "/login"),
                    (
                        "Set-Cookie",
                        self._clear_session_cookie(secure=self._request_secure(environ)),
                    ),
                ),
            )
        if path == "/student/consent" and method == "GET":
            actor = self._resolve_cookie_actor(environ, ActorRole.STUDENT)
            record = self._consents.current(actor) if self._consents else None
            active = bool(
                record
                and record.state is ConsentState.ACTIVE
                and record.consent_version == self._consent_version
            )
            return self._html(
                HTTPStatus.OK,
                render_consent(
                    self._consent_version,
                    active,
                    self._demo,
                    research_allowed=bool(record and record.research_allowed),
                ),
            )
        if path in {"/student/consent/accept", "/student/consent/withdraw"} and method == "POST":
            token = self._session_token(environ, unsafe=True)
            actor = (
                self._auth.resolve(token, allowed_roles=frozenset({ActorRole.STUDENT}))
                if self._auth
                else None
            )
            if actor is None or self._consents is None:
                raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")
            if path.endswith("accept"):
                values = (
                    self._request_values(environ)
                    if environ.get("CONTENT_LENGTH") not in {None, "", "0"}
                    else {}
                )
                if set(values) - {"research_allowed"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                research = values.get("research_allowed", False)
                if not isinstance(research, (bool, str)) or research not in (
                    False,
                    True,
                    "true",
                    "false",
                    "on",
                    "off",
                ):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                self._consents.activate(
                    actor,
                    self._consent_version,
                    research_allowed=research in (True, "true", "on"),
                )
            else:
                self._consents.withdraw(actor)
            return WebResponse(
                HTTPStatus.SEE_OTHER,
                "text/plain; charset=utf-8",
                b"",
                (("Location", "/student/consent"),),
            )
        if method == "GET" and path == "/student/upload":
            if self._auth is not None:
                self._resolve_cookie_actor(environ, ActorRole.STUDENT)
            tasks = (
                self._portal.service.task_list(self._session_token(environ)) if self._portal else []
            )
            try:
                selected = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=10)
            except ValueError as error:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
            from aicefr.audio.recordings import recording_available

            qc = self._portal.control.pipeline._qc_config if self._portal else None
            enabled = bool(
                qc and {"webm", "mp4"}.issubset(qc.accepted_formats) and recording_available()
            )
            return self._html(
                HTTPStatus.OK,
                render_upload_form(
                    demo=self._demo,
                    tasks=tasks,
                    selected={key: values[0] for key, values in selected.items()},
                    consent_version=self._consent_version,
                    recording_enabled=enabled,
                    max_seconds=qc.max_duration_s if qc else 180,
                    max_bytes=qc.max_input_bytes if qc else self._max_request_bytes,
                ),
            )
        if method == "POST" and path == "/api/student/responses":
            return self._submit(environ, browser=False)
        if method == "GET" and path.startswith("/api/v1/reports/"):
            return self._safe_report_api(environ, path)
        if method == "POST" and path == "/student/responses":
            return self._submit(environ, browser=True)
        if path.startswith("/api/student/responses/"):
            return self._student_api_route(method, path, environ)
        if path.startswith("/student/responses/"):
            return self._student_page(method, path, environ)
        if self._review_api is not None:
            if method == "GET" and path == "/teacher/reviews":
                return self._teacher_queue_page(environ)
            if (
                method == "GET"
                and path.startswith("/teacher/reviews/")
                and not path.endswith("/audio")
            ):
                return self._teacher_detail(environ, path)
            if method == "GET" and path.startswith("/teacher/reviews/") and path.endswith("/audio"):
                return self._teacher_audio(environ, path)
            if method == "GET" and path == "/api/teacher/reviews":
                return self._teacher_queue_api(environ)
            if path.startswith("/api/teacher/reviews/"):
                return self._teacher_api_route(method, path, environ)
            if path.startswith("/teacher/reviews/"):
                return self._teacher_form_route(method, path, environ)
        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    def _teacher_detail(self, environ: dict[str, Any], path: str) -> WebResponse:
        response_id = path.removeprefix("/teacher/reviews/")
        if (
            not response_id
            or "/" in response_id
            or self._auth is None
            or self._reviews is None
            or self._reports is None
        ):
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        self._auth.resolve(
            self._session_token(environ),
            allowed_roles=frozenset({ActorRole.TEACHER, ActorRole.ADMIN}),
        )
        candidate = self._reviews.get(response_id)
        if candidate is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        report = self._reports.get(response_id)
        record = self._responses.metadata.get_response(response_id) if self._responses else None
        return self._html(
            HTTPStatus.OK,
            render_review_detail(
                candidate,
                report,
                demo=self._demo,
                audio_available=record.audio_available if record else self._responses is None,
            ),
        )

    def _login(self, environ: dict[str, Any]) -> WebResponse:
        self._require_origin(environ)
        if self._auth is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        values = self._request_values(environ)
        if not self._limiter.allow("login", str(environ.get("REMOTE_ADDR", "loopback")), limit=30):
            raise HttpInputError(HTTPStatus.TOO_MANY_REQUESTS, "RATE_LIMITED")
        if set(values) != {"actor_id", "password"} or not all(
            isinstance(values[k], str) for k in values
        ):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        try:
            device = _coarse_device_category(str(environ.get("HTTP_USER_AGENT", "")))
            token = self._auth.login(
                str(values["actor_id"]), str(values["password"]), device=device
            )
            actor = self._auth.resolve(token, allow_temporary=True)
            temporary = bool(
                self._auth.identity_repository is not None
                and self._auth.identity_repository.has_temporary_password(actor.actor_id)
            )
        except LockoutError:
            return self._html(
                HTTPStatus.TOO_MANY_REQUESTS,
                render_login("Tạm khóa đăng nhập. Hãy đợi rồi thử lại.", demo=self._demo),
            )
        except AuthorizationError:
            return self._html(
                HTTPStatus.UNAUTHORIZED,
                render_login("Tài khoản hoặc mật khẩu không hợp lệ.", demo=self._demo),
            )
        landing = (
            "/password-change"
            if temporary
            else "/teacher/reviews"
            if actor.role is ActorRole.TEACHER
            else "/student/consent"
            if actor.role is ActorRole.STUDENT
            else "/admin"
        )
        return WebResponse(
            HTTPStatus.SEE_OTHER,
            "text/plain; charset=utf-8",
            b"",
            (
                ("Location", landing),
                (
                    "Set-Cookie",
                    self._session_cookie(token, secure=self._request_secure(environ)),
                ),
            ),
        )

    def _resolve_cookie_actor(self, environ: dict[str, Any], role: ActorRole):
        token = self._session_token(environ)
        if self._auth is None:
            raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")
        return self._auth.resolve(token, allowed_roles=frozenset({role}))

    @staticmethod
    def _require_origin(environ: dict[str, Any]) -> None:
        scheme = str(environ.get("wsgi.url_scheme", "http"))
        host = str(environ.get("HTTP_HOST", ""))
        origin = str(environ.get("HTTP_ORIGIN", ""))
        try:
            host_parts = urlsplit(f"//{host}")
            origin_parts = urlsplit(origin)
            hostname = host_parts.hostname
            is_loopback = hostname == "localhost" or bool(
                hostname and ipaddress.ip_address(hostname).is_loopback
            )
            matches = (
                is_loopback
                and not host_parts.username
                and origin_parts.scheme == scheme
                and origin_parts.netloc == host
                and not origin_parts.username
                and origin_parts.path == ""
                and not origin_parts.query
                and not origin_parts.fragment
            )
        except ValueError:
            matches = False
        if not matches:
            raise HttpInputError(HTTPStatus.FORBIDDEN, "CSRF_ORIGIN_REQUIRED")

    def _teacher_audio(self, environ: dict[str, Any], path: str) -> WebResponse:
        response_id = path.removeprefix("/teacher/reviews/").removesuffix("/audio")
        if (
            not response_id
            or "/" in response_id
            or self._reviews is None
            or self._responses is None
            or self._auth is None
        ):
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        self._auth.resolve(
            self._session_token(environ),
            allowed_roles=frozenset({ActorRole.TEACHER, ActorRole.ADMIN}),
        )
        candidate = self._reviews.get(response_id)
        record = self._responses.metadata.get_response(response_id)
        if candidate is None or record is None or not record.audio_available:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        data = self._responses.blobs.read(record.blob)
        from aicefr.audio.recordings import recording_format

        recording = recording_format(data)
        if recording is not None:
            return self._audio_response(environ, data, f"audio/{recording}")
        import io

        import soundfile as sf

        from aicefr.audio.decoder import _detected_format

        try:
            with sf.SoundFile(io.BytesIO(data)) as audio:
                fmt = _detected_format(audio.format, audio.subtype)
        except Exception:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from None
        mime = {
            "wav": "audio/wav",
            "flac": "audio/flac",
            "ogg": "audio/ogg",
            "mp3": "audio/mpeg",
        }.get(str(fmt))
        if mime is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        return self._audio_response(environ, data, mime)

    @staticmethod
    def _audio_response(environ: dict[str, Any], data: bytes, mime: str) -> WebResponse:
        headers = (("Accept-Ranges", "bytes"), ("Content-Disposition", "inline"))
        requested = str(environ.get("HTTP_RANGE", ""))
        if not requested:
            return WebResponse(HTTPStatus.OK, mime, data, headers)
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested) if len(requested) <= 100 else None
        size = len(data)
        if match is not None and any(match.groups()):
            first, last = match.groups()
            if first:
                start, end = int(first), min(int(last), size - 1) if last else size - 1
            else:
                start, end = max(0, size - int(last)), size - 1
                if int(last) == 0:
                    start = size
            if 0 <= start <= end < size:
                return WebResponse(
                    HTTPStatus.PARTIAL_CONTENT,
                    mime,
                    data[start : end + 1],
                    headers + (("Content-Range", f"bytes {start}-{end}/{size}"),),
                )
        return WebResponse(
            HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
            mime,
            b"",
            headers + (("Content-Range", f"bytes */{size}"),),
        )

    def _submit(self, environ: dict[str, Any], *, browser: bool) -> WebResponse:
        token = self._session_token(environ, unsafe=True)
        if self._auth is not None:
            actor = self._auth.resolve(token, allowed_roles=frozenset({ActorRole.STUDENT}))
            if not self._limiter.allow("upload", actor.actor_id, limit=10):
                raise HttpInputError(HTTPStatus.TOO_MANY_REQUESTS, "RATE_LIMITED")
        body = self._read_body(environ)
        request = self._multipart_submit_request(str(environ.get("CONTENT_TYPE", "")), body)
        if self._auth is not None and self._consents is not None:
            actor = self._auth.resolve(token, allowed_roles=frozenset({ActorRole.STUDENT}))
            consent = self._consents.current(actor)
            if (
                request.consent_version != self._consent_version
                or consent is None
                or consent.state is not ConsentState.ACTIVE
                or consent.consent_version != self._consent_version
            ):
                raise HttpInputError(HTTPStatus.FORBIDDEN, "CONSENT_VERSION_STALE")
        status = self._student_api.submit(token, request)
        if browser:
            return WebResponse(
                HTTPStatus.SEE_OTHER,
                "text/plain; charset=utf-8",
                b"",
                (("Location", f"/student/responses/{status.response_id}"),),
            )
        return self._json(HTTPStatus.CREATED, status.model_dump(mode="json"))

    def _student_api_route(self, method: str, path: str, environ: dict[str, Any]) -> WebResponse:
        response_id, suffix = self._student_path(path, "/api/student/responses/")
        token = self._session_token(environ)
        if method == "GET" and suffix == "/status":
            status = self._student_api.get_status(token, response_id)
            return self._json(HTTPStatus.OK, status.model_dump(mode="json"))
        if method == "GET" and suffix == "/report":
            view = self._student_api.get_report(token, response_id)
            if view.report is None:
                return self._json(
                    HTTPStatus.ACCEPTED,
                    {"status": view.status.model_dump(mode="json"), "report": None},
                )
            return self._json(HTTPStatus.OK, self._report_payload(view.report, teacher=False))
        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    def _student_page(self, method: str, path: str, environ: dict[str, Any]) -> WebResponse:
        if method != "GET":
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        response_id, suffix = self._student_path(path, "/student/responses/")
        token = self._session_token(environ)
        if suffix == "":
            status = self._student_api.get_status(token, response_id)
            return self._html(HTTPStatus.OK, render_student_status(status, demo=self._demo))
        if suffix == "/report":
            view = self._student_api.get_report(token, response_id)
            if isinstance(view.report, DiagnosticReport):
                return self._html(HTTPStatus.OK, render_report(view.report, demo=self._demo))
            return self._html(
                HTTPStatus.ACCEPTED,
                render_student_status(view.status, demo=self._demo),
            )
        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    def _teacher_queue_page(self, environ: dict[str, Any]) -> WebResponse:
        assert self._review_api is not None
        queue = self._review_api.get_queue(self._session_token(environ))
        return self._html(HTTPStatus.OK, render_review_queue(queue, demo=self._demo))

    def _teacher_queue_api(self, environ: dict[str, Any]) -> WebResponse:
        assert self._review_api is not None
        queue = self._review_api.get_queue(self._session_token(environ))
        return self._json(
            HTTPStatus.OK,
            {"items": [item.model_dump(mode="json") for item in queue]},
        )

    def _teacher_api_route(self, method: str, path: str, environ: dict[str, Any]) -> WebResponse:
        response_id, action = self._teacher_path(path, "/api/teacher/reviews/")
        if method != "POST" or action not in {"claim", "release", "decision"}:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        outcome = self._teacher_action(environ, response_id, action)
        payload = (
            outcome.model_dump(mode="json")
            if hasattr(outcome, "model_dump")
            else {
                "candidate": outcome.candidate.model_dump(mode="json"),
                "decision": outcome.decision.model_dump(mode="json"),
                "audit": outcome.audit.model_dump(mode="json"),
            }
        )
        return self._json(HTTPStatus.OK, payload)

    def _teacher_form_route(self, method: str, path: str, environ: dict[str, Any]) -> WebResponse:
        response_id, action = self._teacher_path(path, "/teacher/reviews/")
        if method != "POST" or action not in {"claim", "release", "decision"}:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        self._teacher_action(environ, response_id, action)
        return WebResponse(
            status=HTTPStatus.SEE_OTHER,
            content_type="text/plain; charset=utf-8",
            body=b"",
            headers=(("Location", "/teacher/reviews"),),
        )

    def _teacher_action(self, environ: dict[str, Any], response_id: str, action: str):
        assert self._review_api is not None
        token = self._session_token(environ, unsafe=True)
        values = self._request_values(environ)
        if action in {"claim", "release"}:
            try:
                expected_revision = int(values["expected_revision"])
            except (KeyError, TypeError, ValueError) as error:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
            return getattr(self._review_api, action)(token, response_id, expected_revision)
        request = ReviewActionRequest(**self._decision_values(values))
        return self._review_api.decide(token, response_id, request)

    def _request_values(self, environ: dict[str, Any]) -> dict[str, object]:
        body = self._read_body(environ)
        content_type = str(environ.get("CONTENT_TYPE", "")).lower()
        if content_type.startswith("application/json"):
            try:
                values = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
            if not isinstance(values, dict):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return values
        if content_type.startswith("application/x-www-form-urlencoded"):
            try:
                parsed = parse_qs(body.decode("utf-8"), strict_parsing=True)
            except (UnicodeDecodeError, ValueError) as error:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
            if any(len(value) != 1 for value in parsed.values()):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return {key: value[0] for key, value in parsed.items()}
        raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")

    @staticmethod
    def _decision_values(values: dict[str, object]) -> dict[str, object]:
        allowed = {"action", "expected_revision", "final_band", "reason"}
        if set(values) - allowed:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        normalised = dict(values)
        for field in ("final_band", "reason"):
            if normalised.get(field) == "":
                normalised[field] = None
        return normalised

    def _read_body(self, environ: dict[str, Any]) -> bytes:
        content_length = environ.get("CONTENT_LENGTH", "")
        try:
            length = int(content_length) if content_length else None
        except ValueError as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_CONTENT_LENGTH") from error
        if length is not None and (length < 0 or length > self._max_request_bytes):
            raise HttpInputError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")
        raw = environ.get("wsgi.input")
        if raw is None:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        body = raw.read(self._max_request_bytes + 1 if length is None else length)
        if len(body) > self._max_request_bytes or (length is not None and len(body) != length):
            raise HttpInputError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE")
        return body

    @staticmethod
    def _multipart_submit_request(content_type: str, body: bytes) -> SubmitRequest:
        if not content_type.lower().startswith("multipart/form-data"):
            raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")
        try:
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
            )
        except (UnicodeEncodeError, ValueError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART") from error
        if not message.is_multipart():
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
        fields: dict[str, str] = {}
        audio: tuple[str, str, bytes] | None = None
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
            name = part.get_param("name", header="content-disposition")
            payload = part.get_payload(decode=True) or b""
            if name == "audio":
                if audio is not None or part.get_filename() is None:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
                audio = (part.get_filename(), part.get_content_type(), payload)
            elif name in {"task_id", "task_version", "consent_version"}:
                if name in fields:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
                try:
                    fields[name] = payload.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART") from error
            else:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
        if audio is None or set(fields) != {"task_id", "task_version", "consent_version"}:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
        return SubmitRequest(
            **fields,
            filename=audio[0],
            content_type=audio[1],
            audio_bytes=audio[2],
        )

    def _session_token(self, environ: dict[str, Any], *, unsafe: bool = False) -> str:
        authorization = str(environ.get("HTTP_AUTHORIZATION", ""))
        if authorization.startswith("Bearer ") and authorization[7:]:
            return authorization[7:]
        secure = self._request_secure(environ)
        cookie_name = "__Host-aicefr_session" if secure else "aicefr_session"
        cookies = str(environ.get("HTTP_COOKIE", ""))
        for value in cookies.split(";"):
            name, separator, token = value.strip().partition("=")
            if name == cookie_name and separator and token:
                if unsafe:
                    if self._auth is not None and self._consents is not None:
                        self._require_origin(environ)
                    else:
                        scheme = str(environ.get("wsgi.url_scheme", "http"))
                        host = str(environ.get("HTTP_HOST", ""))
                        origin = str(environ.get("HTTP_ORIGIN", ""))
                        if not host or origin != f"{scheme}://{host}":
                            raise HttpInputError(HTTPStatus.FORBIDDEN, "CSRF_ORIGIN_REQUIRED")
                return token
        raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")

    @staticmethod
    def _request_secure(environ: dict[str, Any]) -> bool:
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
    def _student_path(path: str, prefix: str) -> tuple[str, str]:
        remainder = path.removeprefix(prefix)
        response_id, separator, suffix = remainder.partition("/")
        if not response_id:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        return response_id, f"/{suffix}" if separator else ""

    @staticmethod
    def _teacher_path(path: str, prefix: str) -> tuple[str, str]:
        response_id, separator, action = path.removeprefix(prefix).partition("/")
        if not response_id or not separator or "/" in action:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")
        return response_id, action

    @staticmethod
    def _report_payload(report: object, *, teacher: bool = False) -> dict[str, object]:
        if not isinstance(report, DiagnosticReport):
            raise HttpInputError(HTTPStatus.NOT_FOUND, "REPORT_UNAVAILABLE")
        payload = report.model_dump(mode="json")
        payload["source_versions"] = _bounded_versions(report.source_versions, max_value=100_000)
        if report.trust is not None and not teacher:
            payload["trust"] = student_trust_summary(report.trust).model_dump(mode="json")
            payload.pop("prediction_set", None)
            payload.pop("provenance", None)
            payload["criterion_indicators"] = [
                {"name": item.name.value, "label": item.label, "coverage": item.coverage}
                for item in report.criterion_indicators
            ]
        elif teacher:
            payload["provenance"] = _bounded_versions(report.provenance)
        return payload

    def _safe_report_api(self, environ: dict[str, Any], path: str) -> WebResponse:
        response_id = path.removeprefix("/api/v1/reports/")
        if not response_id or "/" in response_id or self._auth is None or self._reports is None:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        token = self._session_token(environ)
        actor = self._auth.resolve(
            token,
            allowed_roles=frozenset({ActorRole.STUDENT, ActorRole.TEACHER, ActorRole.ADMIN}),
        )
        teacher = actor.role in {ActorRole.TEACHER, ActorRole.ADMIN}
        response = None
        if teacher:
            if self._responses is None:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
            response = self._responses.metadata.get_response(response_id)
            if response is None:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        else:
            if self._responses is None:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
            response = self._responses.get_response(actor, response_id)
        report = self._reports.get(response_id)
        if report is None:
            return self._json(
                HTTPStatus.ACCEPTED,
                {
                    "response_id": response_id,
                    "status": response.status.value if response is not None else "REVIEW_REQUIRED",
                    "report": None,
                },
            )
        return self._json(
            HTTPStatus.OK,
            {"response_id": response_id, "report": self._report_payload(report, teacher=teacher)},
        )

    @classmethod
    def _html(cls, status: HTTPStatus, page: str) -> WebResponse:
        return WebResponse(status, "text/html; charset=utf-8", page.encode("utf-8"))

    @classmethod
    def _json(cls, status: HTTPStatus, payload: object) -> WebResponse:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return WebResponse(status, "application/json; charset=utf-8", body)
