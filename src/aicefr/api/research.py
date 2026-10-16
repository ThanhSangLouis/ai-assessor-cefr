"""Authenticated HTTP endpoints for blind rating and research analysis."""

from __future__ import annotations

import io
import json
import secrets
from http import HTTPStatus

import soundfile as sf

from aicefr.contracts import ActorRole
from aicefr.research.service import (
    ResearchConflict,
    ResearchInvalid,
    ResearchNotFound,
    ResearchService,
)


class ResearchApi:
    def __init__(self, auth, service: ResearchService, blobs) -> None:
        self.auth = auth
        self.service = service
        self.blobs = blobs

    def dispatch(self, app, environ):
        from aicefr.api.wsgi import HttpInputError, WebResponse

        path = str(environ.get("PATH_INFO", ""))
        roots = (
            "/api/v1/rating/",
            "/api/v1/admin/ratings/",
            "/api/v1/admin/studies",
            "/api/v1/me/study",
            "/api/v1/me/reliable-change",
            "/api/v1/teacher/research/",
            "/api/v1/admin/sem",
        )
        if not path.startswith(roots):
            return None

        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            token = app._session_token(environ, unsafe=method not in {"GET", "HEAD"})
            if path.startswith("/api/v1/admin/"):
                actor = self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
            elif path.startswith("/api/v1/teacher/") or path.startswith("/api/v1/rating/"):
                actor = self.auth.resolve(
                    token, allowed_roles=frozenset({ActorRole.TEACHER, ActorRole.ADMIN})
                )
            else:
                actor = self.auth.resolve(token, allowed_roles=frozenset({ActorRole.STUDENT}))

            if path == "/api/v1/rating/assignments" and method == "GET":
                return app._json(
                    HTTPStatus.OK, {"assignments": self.service.rater_assignments(actor.actor_id)}
                )
            prefix = "/api/v1/rating/assignments/"
            if path.startswith(prefix):
                tail = path.removeprefix(prefix)
                token_part, separator, action = tail.partition("/")
                if not token_part or "/" in action:
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                if method == "GET" and not separator:
                    return app._json(
                        HTTPStatus.OK, self.service.blind_sheet(actor.actor_id, token_part)
                    )
                if method == "GET" and action == "audio":
                    _, blob = self.service.audio_ref(actor.actor_id, token_part)
                    data = self.blobs.read(blob)
                    from aicefr.audio.recordings import recording_format

                    recording = recording_format(data)
                    if recording is not None:
                        return app._audio_response(environ, data, f"audio/{recording}")
                    try:
                        with sf.SoundFile(io.BytesIO(data)) as audio:
                            mime = {
                                "WAV": "audio/wav",
                                "FLAC": "audio/flac",
                                "OGG": "audio/ogg",
                                "MPEG_LAYER_III": "audio/mpeg",
                            }.get(audio.format)
                    except RuntimeError:
                        mime = None
                    if mime is None:
                        raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                    return app._audio_response(environ, data, mime)
                if method == "POST" and action in {"submit", "adjudicate"}:
                    values = app._request_values(environ)
                    allowed = {"criteria", "overall", "band", "rationale", "unrateable_reason"}
                    if set(values) - allowed:
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    args = {
                        "criteria": values.get("criteria", {}),
                        "overall": values.get("overall"),
                        "band": values.get("band"),
                    }
                    if not isinstance(args["criteria"], dict):
                        raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_RATING")
                    if action == "submit":
                        result = self.service.submit_rating(
                            actor.actor_id,
                            token_part,
                            **args,
                            rationale=str(values.get("rationale") or ""),
                            unrateable_reason=values.get("unrateable_reason"),
                        )
                    else:
                        result = self.service.submit_adjudication(
                            actor.actor_id,
                            token_part,
                            **args,
                            reason=str(values.get("rationale") or ""),
                        )
                    return app._json(HTTPStatus.OK, result)

            if path == "/api/v1/admin/ratings/setup" and method == "GET":
                return app._json(
                    HTTPStatus.OK,
                    {
                        "eligible_responses": len(self.service.eligible_responses()),
                        "raters": self.service.raters(),
                    },
                )
            if path == "/api/v1/admin/ratings/batches" and method == "GET":
                return app._json(HTTPStatus.OK, {"batches": self.service.list_batches()})
            if path == "/api/v1/admin/ratings/batches" and method == "POST":
                values = app._request_values(environ)
                if set(values) - {"name", "rater_ids", "limit", "only_new", "seed"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                result = self.service.create_batch(
                    actor.actor_id,
                    name=str(values.get("name") or ""),
                    rater_ids=values.get("rater_ids") or [],
                    limit=values.get("limit"),
                    only_new=values.get("only_new", True) is not False,
                    seed=values.get("seed")
                    if values.get("seed") is not None
                    else secrets.randbelow(2**31),
                )
                return app._json(HTTPStatus.CREATED, result)
            prefix = "/api/v1/admin/ratings/batches/"
            if path.startswith(prefix):
                tail = path.removeprefix(prefix)
                batch_id, separator, action = tail.partition("/")
                if not batch_id or not separator:
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                if action == "report" and method == "GET":
                    owed = self.service.blinded_response_ids(actor.actor_id)
                    batch_responses = self.service.batch_response_ids(batch_id)
                    if owed & batch_responses:
                        raise HttpInputError(HTTPStatus.CONFLICT, "BLIND_ASSIGNMENTS_PENDING")
                    payload = self.service.rating_report(batch_id)
                    self.service.audit_action(actor.actor_id, "rating.report", batch_id)
                    return app._json(HTTPStatus.OK, payload)
                if action == "export.csv" and method == "GET":
                    owed = self.service.blinded_response_ids(actor.actor_id)
                    if owed & self.service.batch_response_ids(batch_id):
                        raise HttpInputError(HTTPStatus.CONFLICT, "BLIND_ASSIGNMENTS_PENDING")
                    self.service.rating_report(batch_id)
                    body = self.service.rating_csv(batch_id).encode("utf-8")
                    self.service.audit_action(actor.actor_id, "rating.export", batch_id)
                    return WebResponse(
                        HTTPStatus.OK,
                        "text/csv; charset=utf-8",
                        body,
                        (
                            (
                                "Content-Disposition",
                                f'attachment; filename="ratings-{batch_id[:8]}.csv"',
                            ),
                        ),
                    )
                if action in {"close", "reopen"} and method == "POST":
                    return app._json(
                        HTTPStatus.OK,
                        self.service.close_batch(
                            actor.actor_id, batch_id, reopen=action == "reopen"
                        ),
                    )
                if action == "adjudicate" and method == "POST":
                    values = app._request_values(environ)
                    if set(values) != {"adjudicator_id"}:
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    return app._json(
                        HTTPStatus.OK,
                        self.service.create_adjudications(
                            actor.actor_id, batch_id, str(values["adjudicator_id"])
                        ),
                    )
                if action == "replace" and method == "POST":
                    values = app._request_values(environ)
                    if set(values) != {"rater_id"}:
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    return app._json(
                        HTTPStatus.OK,
                        self.service.replace_void(
                            actor.actor_id, batch_id, str(values["rater_id"])
                        ),
                    )

            if path == "/api/v1/admin/studies" and method == "POST":
                values = app._request_values(environ)
                if set(values) - {"title", "seed", "min_days"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                result = self.service.create_study(
                    actor.actor_id,
                    str(values.get("title") or ""),
                    int(values.get("seed", secrets.randbelow(2**31))),
                    int(values.get("min_days", 7)),
                )
                return app._json(HTTPStatus.CREATED, result)
            if path.startswith("/api/v1/admin/studies/"):
                tail = path.removeprefix("/api/v1/admin/studies/")
                study_id, separator, action = tail.partition("/")
                if separator and action in {"start", "survey", "close", "report", "export.csv"}:
                    if action == "start" and method == "POST":
                        result = self.service.start_study(actor.actor_id, study_id)
                        return app._json(HTTPStatus.OK, result)
                    if action in {"survey", "close"} and method == "POST":
                        state = "SURVEY" if action == "survey" else "CLOSED"
                        return app._json(
                            HTTPStatus.OK,
                            self.service.set_study_state(actor.actor_id, study_id, state),
                        )
                    if action == "report" and method == "GET":
                        payload = self.service.study_report(study_id)
                        self.service.audit_action(actor.actor_id, "study.report", study_id)
                        return app._json(HTTPStatus.OK, payload)
                    if action == "export.csv" and method == "GET":
                        self.service.study_report(study_id)
                        payload = self.service.study_csv(study_id)
                        self.service.audit_action(actor.actor_id, "study.export", study_id)
                        return WebResponse(
                            HTTPStatus.OK,
                            "text/csv; charset=utf-8",
                            payload.encode("utf-8"),
                            (
                                (
                                    "Content-Disposition",
                                    f'attachment; filename="study-{study_id[:8]}.csv"',
                                ),
                            ),
                        )

            if path == "/api/v1/me/study" and method == "GET":
                return app._json(
                    HTTPStatus.OK, {"study": self.service.study_for_participant(actor.actor_id)}
                )
            if path == "/api/v1/me/study/survey" and method == "POST":
                values = app._request_values(environ)
                if set(values) != {"phase", "answers"} or not isinstance(values["answers"], dict):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                return app._json(
                    HTTPStatus.CREATED,
                    self.service.submit_survey(actor.actor_id, values["phase"], values["answers"]),
                )
            if path == "/api/v1/me/reliable-change" and method == "GET":
                return app._json(HTTPStatus.OK, self.service.reliable_change_for(actor.actor_id))
            if path == "/api/v1/teacher/research/teacher-time" and method == "GET":
                return app._json(HTTPStatus.OK, self.service.teacher_time_report())
            if path == "/api/v1/admin/sem" and method == "POST":
                values = app._request_values(environ)
                if set(values) != {"value", "source", "sample_count"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                return app._json(
                    HTTPStatus.CREATED,
                    self.service.manual_sem(
                        actor.actor_id,
                        float(values["value"]),
                        str(values["source"]),
                        int(values["sample_count"]),
                    ),
                )
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        except HttpInputError:
            raise
        except ResearchNotFound as error:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from error
        except ResearchConflict as error:
            raise HttpInputError(HTTPStatus.CONFLICT, "RESEARCH_CONFLICT") from error
        except ResearchInvalid as error:
            raise HttpInputError(
                HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_RESEARCH_REQUEST"
            ) from error
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
