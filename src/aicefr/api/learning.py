from __future__ import annotations

import re
from dataclasses import fields, is_dataclass
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from enum import Enum
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from aicefr.api.wsgi import HttpInputError, WebResponse
from aicefr.auth.errors import AuthorizationError, LockoutError, ResourceNotFound
from aicefr.contracts import ActorRole
from aicefr.lessons.model import LearningPath, LearningUnit, Lesson
from aicefr.practice.contracts import PracticePurpose

class LearningApi:
    def __init__(self, auth, learning_service) -> None:
        self.auth = auth
        self.learning = learning_service

    def dispatch(self, app, environ):
        path = str(environ.get("PATH_INFO", ""))
        if not path.startswith("/api/v1/me/learning/") and not path.startswith(
            "/api/v1/teacher/learning/"
        ):
            return None
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            token = app._session_token(environ, unsafe=method not in {"GET", "HEAD"})
            if path.startswith("/api/v1/me/learning/"):
                actor = self.auth.resolve(token, allowed_roles=frozenset({ActorRole.STUDENT}))
                owner = actor.actor_id
                if path == "/api/v1/me/learning/achievements" and method == "GET":
                    return app._json(HTTPStatus.OK, self.learning.achievements(owner))
                if path == "/api/v1/me/learning/achievements/seen" and method == "POST":
                    values = app._request_values(environ)
                    if set(values) != {"codes"} or not isinstance(values["codes"], list):
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    return app._json(HTTPStatus.OK, self.learning.mark_seen(owner, values["codes"]))
                if path == "/api/v1/me/learning/progress" and method == "GET":
                    return app._json(HTTPStatus.OK, self.learning.progress(owner))
                if path == "/api/v1/me/learning/pronunciation" and method == "GET":
                    return app._json(HTTPStatus.OK, self.learning.pronunciation(owner))
                prefix = "/api/v1/me/learning/pronunciation/examples/"
                if path.startswith(prefix) and method == "GET":
                    attempt_id = path.removeprefix(prefix)
                    if not attempt_id or "/" in attempt_id:
                        raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                    example = self.learning.pronunciation_example(owner, attempt_id)
                    if example is None:
                        raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                    return app._json(HTTPStatus.OK, example)
            if path == "/api/v1/teacher/learning/pronunciation-cohort" and method == "GET":
                self.auth.resolve(
                    token, allowed_roles=frozenset({ActorRole.TEACHER, ActorRole.ADMIN})
                )
                return app._json(HTTPStatus.OK, self.learning.cohort_pronunciation())
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        except HttpInputError:
            raise
        except ResourceNotFound:
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from None
        except LockoutError as error:
            raise HttpInputError(HTTPStatus.TOO_MANY_REQUESTS, "LOGIN_LOCKED") from error
        except AuthorizationError as error:
            denied = error.code in {"forbidden", "access_denied", "role_required"}
            raise HttpInputError(
                HTTPStatus.FORBIDDEN if denied else HTTPStatus.UNAUTHORIZED,
                "ACCESS_DENIED" if denied else "SESSION_REQUIRED",
            ) from error
        except (ValueError, TypeError, KeyError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error


_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_INTEGER = re.compile(r"^[0-9]{1,10}$")
_MAX_REVISION = 2_147_483_647


class LearningExperienceApi:
    def __init__(self, service: Any, lessons: Any, *, consents: Any, consent_version: str) -> None:
        self._service = service
        self._lessons = lessons
        self._consents = consents
        self._consent_version = consent_version

    def dispatch(self, app: Any, environ: dict[str, Any]) -> WebResponse | None:
        path = str(environ.get("PATH_INFO", ""))
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        if not any(
            path.startswith(prefix)
            for prefix in (
                "/api/v1/practice",
                "/api/v1/learn",
                "/api/v1/teacher/learn",
            )
        ):
            return None
        if app._auth is None:
            raise HttpInputError(HTTPStatus.UNAUTHORIZED, "SESSION_REQUIRED")
        unsafe = method not in {"GET", "HEAD"}
        token = app._session_token(environ, unsafe=unsafe)
        actor = app._auth.resolve(token)
        if path.startswith("/api/v1/teacher/learn/"):
            if actor.role not in {ActorRole.TEACHER, ActorRole.ADMIN}:
                raise HttpInputError(HTTPStatus.FORBIDDEN, "ACCESS_DENIED")
            insight_route = re.fullmatch(r"/api/v1/teacher/learn/insights/([^/]+)", path)
            if insight_route and method == "GET":
                owner_id = insight_route.group(1)
                self._validate_id(owner_id)
                insight = self._lessons.learning_insights(owner_id)
                return app._json(HTTPStatus.OK, self._json_value(insight))
            return self._teacher_dispatch(app, environ, actor, path, method)
        if actor.role is not ActorRole.STUDENT:
            raise HttpInputError(HTTPStatus.FORBIDDEN, "ACCESS_DENIED")
        self._consents.require_active(actor, self._consent_version)

        if path in {"/api/v1/practice", "/api/v1/practice/missions"} and method == "GET":
            return app._json(
                HTTPStatus.OK,
                {"missions": [m.model_dump(mode="json") for m in self._service.catalogue()]},
            )
        if path.startswith("/api/v1/practice/missions/") and method == "GET":
            mission_id = path.removeprefix("/api/v1/practice/missions/")
            self._validate_id(mission_id)
            try:
                mission = self._service.mission(mission_id)
            except KeyError:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from None
            return app._json(HTTPStatus.OK, mission.model_dump(mode="json"))
        if path == "/api/v1/practice/attempts" and method == "POST":
            values = self._multipart(
                app,
                environ,
                text_fields={"mission_id", "prompt_version", "purpose", "idempotency_key"},
            )
            allowed = {"mission_id", "prompt_version", "purpose", "audio", "idempotency_key"}
            if set(values) != allowed or not all(
                isinstance(values[key], str) for key in ("mission_id", "purpose", "idempotency_key")
            ):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            mission_id, prompt_version, purpose, audio, idempotency_key = (
                values[k]
                for k in ("mission_id", "prompt_version", "purpose", "audio", "idempotency_key")
            )
            if not isinstance(audio, tuple):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
            try:
                typed_purpose = PracticePurpose(purpose)
            except ValueError:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            if typed_purpose is not PracticePurpose.PRACTICE:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            filename, mime, content = audio
            extension = self._extension(filename, mime)
            record = self._service.submit(
                actor.actor_id,
                mission_id,
                content,
                extension,
                idempotency_key,
                prompt_version=prompt_version,
                purpose=typed_purpose,
                content_type=mime.lower(),
            )
            return app._json(HTTPStatus.CREATED, self._public_record(record))
        if path == "/api/v1/practice/attempts" and method == "GET":
            query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=2)
            try:
                limit = int(query.get("limit", ["20"])[0])
            except (IndexError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            if set(query) - {"limit"} or not 1 <= limit <= 100:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            return app._json(
                HTTPStatus.OK,
                {
                    "attempts": [
                        self._public_record(row)
                        for row in self._service.attempts(actor.actor_id, limit=limit)
                    ]
                },
            )
        if path.startswith("/api/v1/practice/attempts/"):
            attempt_id = path.removeprefix("/api/v1/practice/attempts/")
            self._validate_id(attempt_id)
            if method == "GET":
                record = self._service.attempt(actor.actor_id, attempt_id)
                if record is None:
                    raise ResourceNotFound("resource unavailable")
                return app._json(HTTPStatus.OK, self._public_record(record))
            if method == "DELETE":
                revision = self._revision_query(environ)
                record = self._service.delete_attempt(
                    actor.actor_id, attempt_id, expected_revision=revision
                )
                return app._json(HTTPStatus.OK, self._public_record(record))
        if path == "/api/v1/practice/recommendation" and method == "GET":
            value = self._service.recommendation(actor.actor_id)
            return app._json(HTTPStatus.OK, value.model_dump(mode="json"))
        if path == "/api/v1/learn/path" and method == "GET":
            rows = self._lessons.paths()
            return app._json(
                HTTPStatus.OK, {"paths": [row.model_dump(mode="json") for row in rows]}
            )
        if path.startswith("/api/v1/learn/lessons/") and method == "GET":
            progress_match = re.fullmatch(r"/api/v1/learn/lessons/([^/]+)/progress", path)
            if progress_match:
                lesson_id = progress_match.group(1)
                self._validate_id(lesson_id)
                query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=2)
                try:
                    selected_version = (
                        self._bounded_integer(query["version"][0], minimum=1)
                        if "version" in query
                        else None
                    )
                except (IndexError, ValueError):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
                if set(query) - {"version"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                progress = self._lessons.progress(actor.actor_id, lesson_id, selected_version)
                if progress is None:
                    raise ResourceNotFound("resource unavailable")
                return app._json(HTTPStatus.OK, progress.model_dump(mode="json"))
            version_match = re.fullmatch(r"/api/v1/learn/lessons/([^/]+)/versions/(\d+)", path)
            if version_match:
                lesson_id, version_raw = version_match.groups()
                self._validate_id(lesson_id)
                lesson = self._lessons.lesson(
                    lesson_id, self._bounded_integer(version_raw, minimum=1)
                )
                if lesson is None:
                    raise ResourceNotFound("resource unavailable")
                return app._json(HTTPStatus.OK, self._public_lesson(lesson))
            media_match = re.fullmatch(
                r"/api/v1/learn/lessons/([^/]+)/versions/(\d+)/steps/([^/]+)/media/([^/]+)", path
            )
            if media_match:
                lesson_id, version_raw, step_id, media_id = media_match.groups()
                self._validate_id(lesson_id)
                self._validate_id(step_id)
                self._validate_id(media_id)
                artifacts = self._lessons.media(
                    lesson_id, self._bounded_integer(version_raw, minimum=1), step_id
                )
                artifact = next((item for item in artifacts if item.media_id == media_id), None)
                if artifact is None:
                    raise ResourceNotFound("resource unavailable")
                data = self._lessons.read_media(artifact)
                return app._audio_response(environ, data, artifact.content_type)
            lesson_id = path.removeprefix("/api/v1/learn/lessons/")
            self._validate_id(lesson_id)
            lesson = self._lessons.lesson(lesson_id)
            if lesson is None:
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.OK, self._public_lesson(lesson))
        if path == "/api/v1/learn/reviews/due" and method == "GET":
            return app._json(
                HTTPStatus.OK,
                {
                    "reviews": [
                        self._json_value(item) for item in self._lessons.due_reviews(actor.actor_id)
                    ]
                },
            )
        review_attempt_route = re.fullmatch(r"/api/v1/learn/reviews/([^/]+)/attempts", path)
        if review_attempt_route and method == "POST":
            review_id = review_attempt_route.group(1)
            self._validate_id(review_id)
            values = self._multipart(app, environ, text_fields={"idempotency_key"})
            if set(values) != {"idempotency_key", "audio"} or not isinstance(
                values.get("idempotency_key"), str
            ):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            filename, mime, content = values["audio"]
            extension = self._extension(filename, mime)
            key = values["idempotency_key"]
            practice_replay = self._service.review_replay(actor.actor_id, key)
            step_replay = self._lessons.review_replay(actor.actor_id, key)
            if practice_replay is not None:
                record = self._service.submit_review(
                    actor.actor_id, review_id, content, extension, key, content_type=mime.lower()
                )
            elif step_replay is not None:
                record = self._lessons.submit_review(
                    actor.actor_id, review_id, content, extension, key, content_type=mime.lower()
                )
            else:
                record = self._service.submit_review(
                    actor.actor_id, review_id, content, extension, key, content_type=mime.lower()
                )
                if record is None:
                    record = self._lessons.submit_review(
                        actor.actor_id,
                        review_id,
                        content,
                        extension,
                        key,
                        content_type=mime.lower(),
                    )
            if record is None:
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.CREATED, self._public_record(record))
        step_attempt = re.fullmatch(r"/api/v1/learn/step-attempts/([^/]+)", path)
        if step_attempt and method in {"GET", "DELETE"}:
            attempt_id = step_attempt.group(1)
            self._validate_id(attempt_id)
            if method == "GET":
                record = self._lessons.attempt(actor.actor_id, attempt_id)
                if record is None:
                    raise ResourceNotFound("resource unavailable")
                return app._json(HTTPStatus.OK, self._public_record(record))
            revision = self._revision_query(environ)
            record = self._lessons.delete_attempt(
                actor.actor_id, attempt_id, expected_revision=revision
            )
            if not record:
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.OK, {"deleted": True})
        if path == "/api/v1/learn/step-attempts" and method == "POST":
            values = self._multipart(
                app,
                environ,
                text_fields={
                    "lesson_id",
                    "lesson_version",
                    "step_id",
                    "round_index",
                    "idempotency_key",
                },
            )
            if set(values) - {
                "lesson_id",
                "lesson_version",
                "step_id",
                "round_index",
                "idempotency_key",
                "audio",
            } or not {
                "lesson_id",
                "lesson_version",
                "step_id",
                "idempotency_key",
                "audio",
            }.issubset(values):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            filename, mime, content = values["audio"]
            extension = self._extension(filename, mime)
            try:
                round_index = (
                    self._bounded_integer(values["round_index"], maximum=100)
                    if "round_index" in values
                    else None
                )
                lesson_version = self._bounded_integer(values["lesson_version"], minimum=1)
            except ValueError:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            result = self._lessons.submit_step(
                actor.actor_id,
                values["lesson_id"],
                lesson_version,
                values["step_id"],
                content,
                extension,
                values["idempotency_key"],
                round_index=round_index,
                content_type=mime.lower(),
            )
            if result is None:
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.CREATED, self._public_record(result))
        if path == "/api/v1/learn/step-attempts" and method == "GET":
            query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=3)
            try:
                limit = int(query.get("limit", ["50"])[0])
            except (IndexError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            if set(query) - {"limit", "lesson_id"} or not 1 <= limit <= 100:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            lesson_id = query.get("lesson_id", [None])[0]
            if lesson_id is not None:
                self._validate_id(lesson_id)
            return app._json(
                HTTPStatus.OK,
                {
                    "attempts": [
                        self._public_record(row)
                        for row in self._lessons.attempts(
                            actor.actor_id, lesson_id=lesson_id, limit=limit
                        )
                    ]
                },
            )
        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    def _teacher_dispatch(
        self, app: Any, environ: dict[str, Any], actor: Any, path: str, method: str
    ) -> WebResponse:
        authored = self._authoring_dispatch(app, environ, actor, path, method)
        if authored is not None:
            return authored
        if path == "/api/v1/teacher/learn/lessons" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"unit_id", "expected_revision", "lesson"}:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            if not isinstance(values["unit_id"], str) or not isinstance(values["lesson"], dict):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (ValueError, TypeError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            saved = self._lessons.save_draft(
                actor.actor_id,
                values["unit_id"],
                Lesson.model_validate(values["lesson"]),
                expected_revision=revision,
            )
            return app._json(HTTPStatus.CREATED, saved.model_dump(mode="json"))
        media_match = re.fullmatch(
            r"/api/v1/teacher/learn/lessons/([^/]+)/versions/(\d+)/steps/([^/]+)/media",
            path,
        )
        if media_match and method == "POST":
            lesson_id, version_raw, step_id = media_match.groups()
            self._validate_id(lesson_id)
            self._validate_id(step_id)
            values = self._multipart(app, environ, text_fields={"media_kind"})
            if set(values) - {"media_kind", "audio"} or "audio" not in values:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                version = self._bounded_integer(version_raw, minimum=1)
            except ValueError:
                raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE") from None
            filename, mime, data = values["audio"]
            extension = self._extension(filename, mime)
            artifact = self._lessons.upload_media(
                actor.actor_id,
                lesson_id,
                version,
                step_id,
                data,
                extension,
                mime.lower(),
                media_kind=values.get("media_kind", "sample_audio"),
            )
            if artifact is None:
                raise ResourceNotFound("resource unavailable")
            return app._json(
                HTTPStatus.CREATED,
                self._media_payload(artifact, draft=True),
            )
        draft_media_match = re.fullmatch(
            r"/api/v1/teacher/learn/lessons/([^/]+)/versions/(\d+)/steps/([^/]+)/media/([^/]+)",
            path,
        )
        if draft_media_match and method == "GET":
            lesson_id, version_raw, step_id, media_id = draft_media_match.groups()
            self._validate_id(lesson_id)
            self._validate_id(step_id)
            self._validate_id(media_id)
            artifacts = self._lessons.media(
                lesson_id,
                self._bounded_integer(version_raw, minimum=1),
                step_id,
                include_draft=True,
                actor_id=actor.actor_id,
            )
            artifact = next((item for item in artifacts if item.media_id == media_id), None)
            if artifact is None:
                raise ResourceNotFound("resource unavailable")
            return app._audio_response(
                environ, self._lessons.read_media(artifact), artifact.content_type
            )
        if path.startswith("/api/v1/teacher/learn/lessons/"):
            rest = path.removeprefix("/api/v1/teacher/learn/lessons/")
            if rest.endswith("/publish") and method == "POST":
                lesson_id = rest.removesuffix("/publish")
                self._validate_id(lesson_id)
                values = app._request_values(environ)
                if set(values) != {"expected_revision"}:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                try:
                    revision = self._bounded_integer(values["expected_revision"])
                except (ValueError, TypeError):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
                version = self._lessons.publish(
                    actor.actor_id, lesson_id, expected_revision=revision
                )
                return app._json(HTTPStatus.CREATED, version.model_dump(mode="json"))
            if rest.endswith("/lint") and method == "POST":
                lesson_id = rest.removesuffix("/lint")
                self._validate_id(lesson_id)
                values = app._request_values(environ)
                if set(values) - {"lesson", "for_publish"} or not isinstance(
                    values.get("lesson"), dict
                ):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                if "for_publish" in values and not isinstance(values["for_publish"], bool):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                lesson = Lesson.model_validate(values["lesson"])
                validation = self._lessons.lint(
                    lesson, for_publish=bool(values.get("for_publish", False))
                )
                return app._json(HTTPStatus.OK, validation.model_dump(mode="json"))
            if method == "GET":
                self._validate_id(rest)
                draft = self._lessons.draft_record(rest)
                if draft is None:
                    raise ResourceNotFound("resource unavailable")
                payload = self._public_lesson(
                    draft.lesson,
                    include_draft=True,
                    actor_id=actor.actor_id,
                    lesson_version=draft.version,
                )
                payload["version"] = draft.version
                return app._json(HTTPStatus.OK, payload)
        if (
            path.startswith("/api/v1/teacher/learn/paths/")
            and path.endswith("/reorder")
            and method == "POST"
        ):
            path_id = path.removeprefix("/api/v1/teacher/learn/paths/").removesuffix("/reorder")
            self._validate_id(path_id)
            values = app._request_values(environ)
            if set(values) != {"expected_revision", "unit_ids"} or not isinstance(
                values["unit_ids"], list
            ):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (ValueError, TypeError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            result = self._lessons.reorder(
                actor.actor_id, path_id, values["unit_ids"], expected_revision=revision
            )
            return app._json(HTTPStatus.OK, {"revision": result})
        raise HttpInputError(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND")

    def _authoring_dispatch(
        self, app: Any, environ: dict[str, Any], actor: Any, path: str, method: str
    ) -> WebResponse | None:
        if path == "/api/v1/teacher/learn/paths/import" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"path_json"} or not isinstance(values["path_json"], str):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            imported = self._lessons.import_path(
                actor.actor_id, values["path_json"].encode("utf-8")
            )
            return app._json(HTTPStatus.CREATED, imported.model_dump(mode="json"))

        path_export = re.fullmatch(r"/api/v1/teacher/learn/paths/([^/]+)/export", path)
        if path_export and method == "GET":
            path_id = path_export.group(1)
            self._validate_id(path_id)
            query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=2)
            try:
                published_only = query.get("published", ["false"])[0] == "true"
                if set(query) - {"published"} or query.get("published", ["false"])[0] not in {
                    "true",
                    "false",
                }:
                    raise ValueError
                payload = self._lessons.export_path(path_id, published_only=published_only)
                import json

                return app._json(HTTPStatus.OK, json.loads(payload))
            except KeyError:
                raise ResourceNotFound("resource unavailable") from None
            except (ValueError, UnicodeDecodeError):
                raise HttpInputError(HTTPStatus.UNPROCESSABLE_ENTITY, "INVALID_EXPORT") from None

        if path == "/api/v1/teacher/learn/paths" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"expected_revision", "path"} or not isinstance(values["path"], dict):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            saved = self._lessons.save_path(
                actor.actor_id,
                LearningPath.model_validate(values["path"]),
                expected_revision=revision,
            )
            return app._json(HTTPStatus.CREATED, self._authoring_path_payload(saved))

        path_publish = re.fullmatch(r"/api/v1/teacher/learn/paths/([^/]+)/publish", path)
        if path_publish and method == "POST":
            path_id = path_publish.group(1)
            self._validate_id(path_id)
            values = app._request_values(environ)
            if set(values) != {"expected_revision"}:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            path_value = self._lessons.publish_path(
                actor.actor_id, path_id, expected_revision=revision
            )
            return app._json(HTTPStatus.CREATED, path_value.model_dump(mode="json"))

        path_resource = re.fullmatch(r"/api/v1/teacher/learn/paths/([^/]+)", path)
        if path_resource and method in {"GET", "DELETE"}:
            path_id = path_resource.group(1)
            self._validate_id(path_id)
            if method == "GET":
                item = self._lessons.path_by_id(path_id, published_only=False)
                if item is None:
                    raise ResourceNotFound("resource unavailable")
                return app._json(HTTPStatus.OK, self._authoring_path_payload(item))
            revision = self._revision_query(environ)
            if not self._lessons.delete_path(actor.actor_id, path_id, expected_revision=revision):
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.OK, {"deleted": True})

        unit_collection = re.fullmatch(r"/api/v1/teacher/learn/paths/([^/]+)/units", path)
        if unit_collection and method == "POST":
            path_id = unit_collection.group(1)
            self._validate_id(path_id)
            values = app._request_values(environ)
            if set(values) != {"expected_revision", "unit"} or not isinstance(values["unit"], dict):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            saved = self._lessons.save_unit(
                actor.actor_id,
                path_id,
                LearningUnit.model_validate(values["unit"]),
                expected_revision=revision,
            )
            return app._json(HTTPStatus.CREATED, saved.model_dump(mode="json"))

        unit_resource = re.fullmatch(r"/api/v1/teacher/learn/paths/([^/]+)/units/([^/]+)", path)
        if unit_resource and method == "DELETE":
            path_id, unit_id = unit_resource.groups()
            self._validate_id(path_id)
            self._validate_id(unit_id)
            revision = self._revision_query(environ)
            if not self._lessons.delete_unit(
                actor.actor_id, path_id, unit_id, expected_revision=revision
            ):
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.OK, {"deleted": True})

        if path == "/api/v1/teacher/learn/lessons/import" and method == "POST":
            values = app._request_values(environ)
            if set(values) != {"unit_id", "expected_revision", "lesson_json"} or not isinstance(
                values["lesson_json"], str
            ):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            saved = self._lessons.import_lesson(
                actor.actor_id,
                values["unit_id"],
                values["lesson_json"].encode("utf-8"),
                expected_revision=revision,
            )
            return app._json(HTTPStatus.CREATED, saved.model_dump(mode="json"))

        export_route = re.fullmatch(r"/api/v1/teacher/learn/lessons/([^/]+)/export", path)
        if export_route and method == "GET":
            lesson_id = export_route.group(1)
            self._validate_id(lesson_id)
            query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=2)
            if set(query) - {"version"}:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                version = (
                    self._bounded_integer(query["version"][0], minimum=1)
                    if "version" in query
                    else None
                )
            except (IndexError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            lesson = None
            if version is None:
                draft = self._lessons.draft_record(lesson_id)
                lesson = draft.lesson if draft is not None else None
            if lesson is None:
                lesson = self._lessons.lesson(lesson_id, version)
            if lesson is None:
                raise ResourceNotFound("resource unavailable")
            import json

            payload = json.loads(self._lessons.export_lesson(lesson))
            return app._json(HTTPStatus.OK, payload)

        lesson_delete = re.fullmatch(r"/api/v1/teacher/learn/lessons/([^/]+)", path)
        if lesson_delete and method == "DELETE":
            lesson_id = lesson_delete.group(1)
            self._validate_id(lesson_id)
            revision = self._revision_query(environ)
            if not self._lessons.delete_lesson(
                actor.actor_id, lesson_id, expected_revision=revision
            ):
                raise ResourceNotFound("resource unavailable")
            return app._json(HTTPStatus.OK, {"deleted": True})

        step_delete = re.fullmatch(r"/api/v1/teacher/learn/lessons/([^/]+)/steps/([^/]+)", path)
        if step_delete and method == "DELETE":
            lesson_id, step_id = step_delete.groups()
            self._validate_id(lesson_id)
            self._validate_id(step_id)
            revision = self._revision_query(environ)
            updated = self._lessons.delete_step(
                actor.actor_id, lesson_id, step_id, expected_revision=revision
            )
            return app._json(HTTPStatus.OK, updated.model_dump(mode="json"))

        step_reorder = re.fullmatch(r"/api/v1/teacher/learn/lessons/([^/]+)/steps/reorder", path)
        if step_reorder and method == "POST":
            lesson_id = step_reorder.group(1)
            self._validate_id(lesson_id)
            values = app._request_values(environ)
            if set(values) != {"expected_revision", "step_ids"} or not isinstance(
                values["step_ids"], list
            ):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            updated = self._lessons.reorder_steps(
                actor.actor_id, lesson_id, values["step_ids"], expected_revision=revision
            )
            return app._json(HTTPStatus.OK, updated.model_dump(mode="json"))

        override_route = re.fullmatch(r"/api/v1/teacher/learn/step-attempts/([^/]+)/override", path)
        if override_route and method == "POST":
            attempt_id = override_route.group(1)
            self._validate_id(attempt_id)
            values = app._request_values(environ)
            if set(values) != {"owner_id", "new_value", "reason", "expected_revision"}:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
            try:
                revision = self._bounded_integer(values["expected_revision"])
            except (TypeError, ValueError):
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
            record = self._lessons.override_attempt(
                actor.actor_id,
                values["owner_id"],
                attempt_id,
                new_value=values["new_value"],
                reason=values["reason"],
                expected_revision=revision,
            )
            return app._json(HTTPStatus.OK, self._public_record(record))
        return None

    @staticmethod
    def _revision_query(environ: dict[str, Any]) -> int:
        query = parse_qs(str(environ.get("QUERY_STRING", "")), max_num_fields=2)
        try:
            if len(query.get("expected_revision", ())) != 1:
                raise ValueError("expected one revision")
            revision = LearningExperienceApi._bounded_integer(query["expected_revision"][0])
        except (KeyError, IndexError, ValueError):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from None
        if set(query) != {"expected_revision"}:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        return revision

    @staticmethod
    def _bounded_integer(value: Any, *, minimum: int = 0, maximum: int = _MAX_REVISION) -> int:
        """Parse API integer fields without accepting bools or truncating floats."""
        if isinstance(value, bool):
            raise ValueError("invalid integer")
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str) and _INTEGER.fullmatch(value):
            parsed = int(value)
        else:
            raise ValueError("invalid integer")
        if not minimum <= parsed <= maximum:
            raise ValueError("integer out of bounds")
        return parsed

    @staticmethod
    def _validate_id(value: str) -> None:
        if not _ID.fullmatch(value):
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")

    @staticmethod
    def _public_record(record: Any) -> dict[str, Any]:
        if hasattr(record, "model_dump"):
            payload = record.model_dump(mode="json")
        elif is_dataclass(record):
            payload = {
                field.name: LearningExperienceApi._json_value(getattr(record, field.name))
                for field in fields(record)
            }
        else:
            raise TypeError("unsupported learning record")
        for key in (
            "audio",
            "review_source_kind",
            "review_source_attempt_id",
            "review_content_key",
            "expected_review_revision",
            "review_box",
        ):
            payload.pop(key, None)
        payload["audio_available"] = record.audio is not None
        return payload

    @staticmethod
    def _json_value(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        if is_dataclass(value):
            return {
                field.name: LearningExperienceApi._json_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, (tuple, list)):
            return [LearningExperienceApi._json_value(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): LearningExperienceApi._json_value(item)
                for key, item in value.items()
            }
        return value

    def _authoring_path_payload(self, path: LearningPath) -> dict[str, Any]:
        return path.model_dump(mode="json")

    def _public_lesson(
        self,
        lesson: Any,
        *,
        include_draft: bool = False,
        actor_id: str | None = None,
        lesson_version: int | None = None,
    ) -> dict[str, Any]:
        payload = lesson.model_dump(mode="json")
        version = lesson_version if lesson_version is not None else getattr(lesson, "version", None)
        if version is not None:
            payload["version"] = version
            payload["sample_media"] = self._lessons.public_media(
                lesson,
                include_draft=include_draft,
                actor_id=actor_id,
                lesson_version=version,
            )
        else:
            payload["sample_media"] = []
        return payload

    @staticmethod
    def _media_payload(artifact: Any, *, draft: bool) -> dict[str, Any]:
        prefix = "/api/v1/teacher/learn" if draft else "/api/v1/learn"
        url = (
            f"{prefix}/lessons/{artifact.lesson_id}/versions/{artifact.lesson_version}/"
            f"steps/{artifact.step_id}/media/{artifact.media_id}"
        )
        return {
            "media_id": artifact.media_id,
            "lesson_id": artifact.lesson_id,
            "lesson_version": artifact.lesson_version,
            "step_id": artifact.step_id,
            "media_kind": artifact.media_kind,
            "content_type": artifact.content_type,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "url": url,
        }

    @staticmethod
    def _extension(filename: str, mime: str) -> str:
        suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed = {
            "wav": "audio/wav",
            "flac": "audio/flac",
            "ogg": "audio/ogg",
            "mp3": "audio/mpeg",
            "webm": "audio/webm",
            "mp4": "audio/mp4",
        }
        if suffix not in allowed or mime.lower() != allowed[suffix]:
            raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")
        return suffix

    @staticmethod
    def _multipart(app: Any, environ: dict[str, Any], *, text_fields: set[str]) -> dict[str, Any]:
        content_type = str(environ.get("CONTENT_TYPE", ""))
        if not content_type.lower().startswith("multipart/form-data"):
            raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")
        body = app._read_body(environ)
        try:
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
            )
        except (UnicodeEncodeError, ValueError):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART") from None
        if not message.is_multipart():
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
        values: dict[str, Any] = {}
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
            name = part.get_param("name", header="content-disposition")
            payload = part.get_payload(decode=True) or b""
            if name == "audio" and part.get_filename():
                if "audio" in values:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
                values[name] = (part.get_filename(), part.get_content_type(), payload)
            elif name in text_fields:
                if name in values:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
                try:
                    values[name] = payload.decode("utf-8")
                except UnicodeDecodeError:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART") from None
            else:
                raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_MULTIPART")
        return values
