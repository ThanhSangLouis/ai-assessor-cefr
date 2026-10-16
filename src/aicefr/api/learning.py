"""Authenticated API for personal practice progress and pronunciation evidence."""

from __future__ import annotations

from http import HTTPStatus

from aicefr.api.wsgi import HttpInputError
from aicefr.auth.errors import AuthorizationError, LockoutError, ResourceNotFound
from aicefr.contracts import ActorRole


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
