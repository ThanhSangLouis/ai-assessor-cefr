"""Portal routes reuse the established WSGI authentication and request boundary."""

from __future__ import annotations

import io
from http import HTTPStatus
from urllib.parse import parse_qs

import soundfile as sf

from aicefr.api.wsgi import HttpInputError, WebResponse
from aicefr.contracts import ActorRole
from aicefr.portal import templates as html
from aicefr.portal.contracts import (
    AccountChange,
    AccountCreate,
    DeleteRequest,
    PageQuery,
    QCChange,
    ReviewReopen,
    TaskRecord,
)
from aicefr.scoring.artifact import ModelArtifactError
from aicefr.storage.blob import BlobIntegrityError
from aicefr.storage.sqlite import ConcurrentResponseUpdate


class PortalRouter:
    def __init__(self, service, control, data, metrics) -> None:
        self.service, self.control, self.data, self.metrics = service, control, data, metrics

    @staticmethod
    def query(environ) -> PageQuery:
        parsed = parse_qs(
            str(environ.get("QUERY_STRING", "")), keep_blank_values=True, max_num_fields=20
        )
        if any(len(value) != 1 for value in parsed.values()):
            raise ValueError("duplicate query parameter")
        return PageQuery(**{key: value[0] for key, value in parsed.items() if value[0]})

    def dispatch(self, app, environ):
        try:
            return self._dispatch(app, environ)
        except HttpInputError:
            raise
        except (ValueError, KeyError, TypeError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
        except ConcurrentResponseUpdate as error:
            raise HttpInputError(HTTPStatus.CONFLICT, "STALE_REVISION") from error
        except ModelArtifactError as error:
            raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, error.reason.value) from error
        except BlobIntegrityError as error:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from error

    def _dispatch(self, app, environ):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        raw_path = environ.get("PATH_INFO", "/")
        api = raw_path.startswith("/api/")
        path = raw_path[4:] if api else raw_path
        if path in {"/health", "/healthz", "/live"} and method == "GET":
            return app._json(HTTPStatus.OK, {"alive": True})
        if path in {"/ready", "/readyz"} and method == "GET":
            result = self.control.readiness()
            return app._json(
                HTTPStatus.OK if result["ready"] else HTTPStatus.SERVICE_UNAVAILABLE, result
            )
        known = (
            raw_path.endswith("/reopen")
            and path.startswith("/teacher/reviews/")
            or (
                path.startswith(("/admin", "/teacher/responses", "/student/"))
                or path == "/teacher/stats"
                or path in {"/me", "/metrics"}
            )
        )
        if not known:
            return None
        # Existing upload, consent and status endpoints retain their original handler.
        if path in {
            "/student/upload",
            "/student/consent",
            "/student/consent/accept",
            "/student/consent/withdraw",
        }:
            return None
        if path == "/student/responses" and method == "POST":
            return None
        parts = path.strip("/").split("/")
        if len(parts) >= 4 and parts[:2] == ["student", "responses"] and parts[3] in {"status"}:
            return None
        if len(parts) == 3 and parts[:2] == ["student", "responses"]:
            return None
        token = app._session_token(environ, unsafe=method not in {"GET", "HEAD"})
        actor = self.service.actor(token)
        role = actor.role.value

        def result(payload, renderer=None, status=HTTPStatus.OK):
            if api or path.endswith(".json") or renderer is None:
                return app._json(status, payload)
            return app._html(status, renderer(payload))

        def changed(payload, location):
            if api:
                return app._json(HTTPStatus.OK, payload)
            return WebResponse(
                HTTPStatus.SEE_OTHER, "text/plain; charset=utf-8", b"", (("Location", location),)
            )

        if path.startswith("/teacher/reviews/") and path.endswith("/reopen") and method == "POST":
            pieces = path.strip("/").split("/")
            if len(pieces) != 4:
                raise ValueError("invalid review path")
            candidate = self.service.reopen_review(
                token, pieces[2], ReviewReopen(**app._request_values(environ)), app._reviews
            )
            return changed(candidate.model_dump(mode="json"), f"/teacher/reviews/{pieces[2]}")

        if path == "/me" and method == "GET":
            consent = self.service.store.get_consent(actor.actor_id)
            return result(
                {
                    "actor": actor.model_dump(mode="json"),
                    "consent": consent.model_dump(mode="json") if consent else None,
                }
            )
        if path == "/metrics" and method == "GET":
            self.service.actor(token, frozenset({ActorRole.ADMIN}))
            return WebResponse(
                HTTPStatus.OK,
                "text/plain; version=0.0.4; charset=utf-8",
                self.metrics.render().encode(),
            )
        if path == "/student/tasks" and method == "GET":
            data = self.service.task_list(token)
            return result(data, lambda rows: html.tasks(rows, role))
        if path in {"/student/responses", "/teacher/responses"} and method == "GET":
            query = self.query(environ)
            data = self.service.responses(token, query, mine=path.startswith("/student"))
            return result(data, lambda value: html.responses(value, role, query))
        if path in {"/student/progress", "/teacher/stats", "/admin/stats"} and method == "GET":
            if path == "/admin/stats":
                self.service.actor(token, frozenset({ActorRole.ADMIN}))
            query = self.query(environ)
            data = self.service.statistics(token, query, mine=path.startswith("/student"))
            return result(data, lambda value: html.statistics(value, role, query))
        if path == "/student/profile.json" and method == "GET":
            return result(self.service.profile(token))
        if path == "/student/export.json" and method == "GET":
            response = result(self.service.export_own(token))
            return WebResponse(
                response.status,
                response.content_type,
                response.body,
                (("Content-Disposition", 'attachment; filename="my-data.json"'),),
            )
        if len(parts) == 4 and parts[0] in {"student", "teacher"} and parts[1] == "responses":
            staff = parts[0] == "teacher"
            rid, action = parts[2:]
            _, response = self.service.response(token, rid, staff=staff)
            if action == "audio" and method == "GET":
                if not response.audio_available:
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                data = self.data.blobs.read(response.blob)
                from aicefr.audio.recordings import recording_format

                recording = recording_format(data)
                if recording is not None:
                    return app._audio_response(environ, data, f"audio/{recording}")
                with sf.SoundFile(io.BytesIO(data)) as audio:
                    mime = {
                        "WAV": "audio/wav",
                        "FLAC": "audio/flac",
                        "OGG": "audio/ogg",
                        "MPEG_LAYER_III": "audio/mpeg",
                    }.get(audio.format)
                if mime is None:
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                return app._audio_response(environ, data, mime)
            if action == "report" and method == "GET":
                if not staff:
                    view = app._student_api.get_report(token, rid)
                    if view.report is None:
                        return None
                    report = view.report
                else:
                    report = app._reports.get(rid)
                    if report is None:
                        raise HttpInputError(HTTPStatus.CONFLICT, "REPORT_NOT_READY")
                return result(
                    report.model_dump(mode="json"),
                    lambda _: html.report_page(
                        report, response, role, candidate=app._reviews.get(rid) if staff else None
                    ),
                )
            if action == "history" and staff and method == "GET":
                history = self.service.history(token, rid)
                return result(
                    history, lambda value: html.json_page("Lịch sử xử lý bài", value, role)
                )
            if action == "review" and staff and method == "POST":
                values = app._request_values(environ)
                candidate = self.service.request_review(
                    token, rid, int(values["expected_revision"]), app._reviews
                )
                return changed(candidate.model_dump(mode="json"), f"/teacher/reviews/{rid}")
            if action == "delete" and not staff:
                if method == "GET":
                    return app._html(HTTPStatus.OK, html.delete_page(response))
                if method == "POST":
                    deleted = self.data.delete_response(
                        token, rid, DeleteRequest(**app._request_values(environ))
                    )
                    return changed(deleted, "/student/responses")
        if not path.startswith("/admin"):
            return None
        self.service.actor(token, frozenset({ActorRole.ADMIN}))
        if path == "/admin/health" and method == "GET":
            from aicefr.audio.recordings import recording_available

            health = self.control.readiness()
            counts = self.service.store.connection.execute(
                "SELECT status,COUNT(*) FROM responses GROUP BY status"
            ).fetchall()
            artifact = getattr(self.control.pipeline._scorer, "artifact", None)
            health.update(
                response_statuses=dict(counts),
                recording_available=recording_available(),
                aggregation_enabled=bool(self.control.config.get("long_response_windows", False)),
                request_counters=self.metrics.render(),
                model_version=artifact.model_version if artifact else None,
            )
            return result(health, lambda value: html.json_page("Trạng thái vận hành", value, role))
        if path == "/admin" and method == "GET":
            data = self.service.statistics(token, PageQuery())
            body = html.statistics(data, role, PageQuery())
            return result(data, lambda _: body)
        if path == "/admin/accounts":
            if method == "GET":
                return result(self.service.accounts(token), html.accounts)
            if method == "POST":
                return changed(
                    self.service.create_account(
                        token, AccountCreate(**app._request_values(environ))
                    ),
                    path,
                )
        if len(parts) == 3 and parts[:2] == ["admin", "accounts"] and method == "POST":
            return changed(
                self.service.change_account(
                    token, parts[2], AccountChange(**app._request_values(environ))
                ),
                "/admin/accounts",
            )
        if path == "/admin/tasks":
            if method == "GET":
                return result(
                    self.service.task_list(token, admin=True),
                    lambda rows: html.tasks(rows, "admin"),
                )
            if method == "POST":
                values = app._request_values(environ)
                expected = int(values.pop("expected_revision"))
                return changed(self.service.save_task(token, TaskRecord(**values), expected), path)
        if path == "/admin/audit" and method == "GET":
            return result(
                self.service.audit_entries(token, self.query(environ)),
                lambda value: html.json_page("Audit", value, role),
            )
        if path == "/admin/config":
            if method == "GET":
                return result(self.control.qc(token), html.config_page)
            if method == "POST":
                values = app._request_values(environ)
                if "changes" not in values:
                    values = {
                        "expected_revision": values.pop("expected_revision"),
                        "changes": values,
                    }
                return changed(self.control.change_qc(token, QCChange(**values)), path)
        if path == "/admin/models" and method == "GET":
            return result(self.control.models(token), html.model_page)
        if path == "/admin/models/activate" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"name", "expected_revision"}:
                raise ValueError("invalid activation request")
            return changed(
                self.control.activate_model(
                    token, str(values["name"]), int(values["expected_revision"])
                ),
                "/admin/models",
            )
        if path == "/admin/research.json" and method == "GET":
            return result(self.service.research_export(token, app._consent_version))
        if path == "/admin/erase" and method == "GET":
            return app._html(HTTPStatus.OK, html.erasure())
        if path == "/admin/erase/preview" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"actor_id"}:
                raise ValueError("invalid preview request")
            return result(self.data.erasure_preview(token, str(values["actor_id"])), html.erasure)
        if path == "/admin/erase" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"actor_id", "confirm_id", "fingerprint"}:
                raise ValueError("invalid erasure request")
            return changed(self.data.erase(token, **values), "/admin/accounts")
        if path == "/admin/maintenance" and method == "GET":
            retention, orphans = self.data.retention(token), self.data.orphans(token)
            return result(
                {"retention": retention, "orphans": orphans},
                lambda _: html.maintenance(retention, orphans),
            )
        if len(parts) == 3 and parts[:2] == ["admin", "maintenance"] and method == "POST":
            action = parts[2]
            values = app._request_values(environ)
            if values != {"confirm_action": action} or action not in {"retention", "orphans"}:
                raise ValueError("explicit maintenance confirmation required")
            return changed(getattr(self.data, action)(token, apply=True), "/admin/maintenance")
        return None
