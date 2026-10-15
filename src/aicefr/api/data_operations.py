"""Bounded authenticated API for personal export and admin data controls."""

from __future__ import annotations

import hashlib
import re
import uuid
from http import HTTPStatus
from urllib.parse import parse_qs

from aicefr.api.wsgi import HttpInputError
from aicefr.auth.errors import AuthorizationError, LockoutError, ResourceNotFound
from aicefr.contracts import ActorRole
from aicefr.storage.sqlite import ConcurrentResponseUpdate


class DataOperationsApi:
    def __init__(self, auth, portal, data) -> None:
        self.auth, self.portal, self.data = auth, portal, data
        base = portal.store.data_dir.parent / "admin-backups"
        if base.is_symlink():
            raise ValueError("backup root cannot be a symlink")
        base.mkdir(mode=0o700, exist_ok=True)
        install_id = hashlib.sha256(str(portal.store.data_dir).encode()).hexdigest()[:24]
        self.backups = base / install_id
        self.backups.mkdir(mode=0o700, exist_ok=True)
        if self.backups.is_symlink():
            raise ValueError("backup root cannot be a symlink")
        self.restores = portal.store.data_dir.parent / "restore-staging" / install_id
        if self.restores.is_symlink():
            raise ValueError("restore root cannot be a symlink")

    def dispatch(self, app, environ):
        path = str(environ.get("PATH_INFO", ""))
        owned = path in {
            "/api/v1/me/export",
            "/api/v1/admin/data/erasure/preview",
            "/api/v1/admin/data/erasure/confirm",
            "/api/v1/admin/data/retention",
            "/api/v1/admin/data/backups",
            "/api/v1/admin/data/restore",
        }
        if not owned:
            return None
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            token = app._session_token(environ, unsafe=method not in {"GET", "HEAD"})
            if path == "/api/v1/me/export" and method == "GET":
                return app._json(HTTPStatus.OK, self.portal.export_own(token))
            self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
            if path.endswith("/erasure/preview") and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, {"actor_id"})
                if not self._opaque_id(values["actor_id"]):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                return app._json(
                    HTTPStatus.OK, self.data.erasure_preview(token, values["actor_id"])
                )
            if path.endswith("/erasure/confirm") and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, {"actor_id", "confirm_id", "fingerprint"})
                if (
                    not self._opaque_id(values["actor_id"])
                    or not self._opaque_id(values["confirm_id"])
                    or not isinstance(values["fingerprint"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", values["fingerprint"])
                ):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                return app._json(
                    HTTPStatus.OK,
                    self.data.erase(
                        token, values["actor_id"], values["confirm_id"], values["fingerprint"]
                    ),
                )
            if path.endswith("/retention") and method in {"GET", "POST"}:
                values = self._request_values(app, environ) if method == "POST" else {}
                self._keys(values, {"days"} if method == "POST" else set())
                if method == "GET":
                    query = parse_qs(
                        str(environ.get("QUERY_STRING", "")),
                        keep_blank_values=True,
                        max_num_fields=2,
                    )
                    if set(query) - {"days"} or any(len(item) != 1 for item in query.values()):
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    raw_days = query.get("days", ["180"])[0]
                    if not raw_days.isascii() or not raw_days.isdigit():
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    days = int(raw_days)
                else:
                    days = values.get("days", 180)
                if type(days) is not int:
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                return app._json(
                    HTTPStatus.OK, self.data.retention(token, days=days, apply=method == "POST")
                )
            if path.endswith("/backups") and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, set())
                backup_id = uuid.uuid4().hex
                manifest = self.data.backup(token, self.backups / backup_id)
                return app._json(HTTPStatus.CREATED, {"backup_id": backup_id, "manifest": manifest})
            if path.endswith("/restore") and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, {"backup_id"})
                backup_id = values["backup_id"]
                if not isinstance(backup_id, str) or not re.fullmatch(r"[0-9a-f]{32}", backup_id):
                    raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                source = self.backups / backup_id
                if source.is_symlink() or not source.is_dir():
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                restore_id = uuid.uuid4().hex
                destination = self.restores / restore_id
                self.data.restore_backup(source, destination, token)
                return app._json(HTTPStatus.CREATED, {"restore_id": restore_id, "verified": True})
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        except HttpInputError:
            raise
        except ResourceNotFound:
            return app._json(HTTPStatus.NOT_FOUND, {"error": "RESOURCE_UNAVAILABLE"})
        except LockoutError as error:
            return app._json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "LOGIN_LOCKED", "retry_after": error.retry_after},
            )
        except ConcurrentResponseUpdate:
            return app._json(HTTPStatus.CONFLICT, {"error": "STALE_PREVIEW"})
        except AuthorizationError as error:
            denied = error.code in {
                "forbidden",
                "access_denied",
                "role_required",
                "password_change_required",
            }
            return app._json(
                HTTPStatus.FORBIDDEN if denied else HTTPStatus.UNAUTHORIZED,
                {"error": "ACCESS_DENIED" if denied else "SESSION_REQUIRED"},
            )
        except ValueError:
            return app._json(HTTPStatus.CONFLICT, {"error": "DATA_OPERATION_REJECTED"})

    @staticmethod
    def _keys(values, allowed):
        if set(values) != allowed:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")

    @staticmethod
    def _opaque_id(value):
        return (
            isinstance(value, str)
            and value.isascii()
            and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value) is not None
        )

    @staticmethod
    def _request_values(app, environ):
        import json

        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        if not str(environ.get("CONTENT_TYPE", "")).lower().startswith("application/json"):
            raise HttpInputError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_REQUEST_FORMAT")
        try:
            value = json.loads(
                app._read_body(environ),
                object_pairs_hook=object_pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid number")),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST") from error
        if not isinstance(value, dict):
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
        return value
