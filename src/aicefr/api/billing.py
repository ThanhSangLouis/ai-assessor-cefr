"""Admin-only HTTP adapter for sandbox billing and license operations."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from http import HTTPStatus

from aicefr.api.wsgi import HttpInputError
from aicefr.auth.errors import AuthorizationError, LockoutError, ResourceNotFound
from aicefr.billing.errors import BillingError
from aicefr.contracts import ActorRole


class BillingApi:
    def __init__(self, auth, service, gateways, licenses) -> None:
        self.auth, self.service = auth, service
        self.gateways, self.licenses = gateways, licenses

    def dispatch(self, app, environ):
        path = str(environ.get("PATH_INFO", ""))
        if not (
            path.startswith("/api/v1/admin/billing") or path.startswith("/api/v1/billing/webhooks/")
        ):
            return None
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            if path.startswith("/api/v1/billing/webhooks/"):
                gateway = path.removeprefix("/api/v1/billing/webhooks/")
                if not gateway or "/" in gateway or method != "POST":
                    raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
                body = app._read_body(environ)
                result = self.service.handle_event(
                    gateway,
                    body,
                    headers=self._signature_headers(environ),
                    channel="webhook",
                )
                return app._json(HTTPStatus.OK, self._dto(result))

            suffix = path.removeprefix("/api/v1/admin/billing").strip("/")
            token = app._session_token(environ, unsafe=method not in {"GET", "HEAD"})
            self.auth.resolve(token, allowed_roles=frozenset({ActorRole.ADMIN}))
            if not suffix and method == "GET":
                return app._json(
                    HTTPStatus.OK,
                    {
                        "overview": self._dto(self.service.overview(token)),
                        "gateways": self._dto(self.gateways.status()),
                        "license": self._dto(self.licenses.status(token)),
                    },
                )
            if suffix == "gateways" and method == "GET":
                return app._json(HTTPStatus.OK, self._dto(self.gateways.status()))
            if suffix == "quotes" and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, {"plan_code", "months", "idempotency_key"})
                result = self.service.quote(
                    token, values["plan_code"], values["months"], values["idempotency_key"]
                )
                return app._json(HTTPStatus.CREATED, self._dto(result))
            if suffix == "orders" and method == "POST":
                values = self._request_values(app, environ)
                self._keys(values, {"quote_id", "gateway", "idempotency_key"})
                result = self.service.create_order(
                    token, values["quote_id"], values["gateway"], values["idempotency_key"]
                )
                return app._json(HTTPStatus.CREATED, self._dto(result))
            if suffix == "orders" and method == "GET":
                return app._json(
                    HTTPStatus.OK,
                    {"items": [self._dto(item) for item in self.service.list_orders(token)]},
                )
            if suffix.startswith("orders/"):
                parts = suffix.split("/")
                if len(parts) == 3 and parts[2] == "receipt" and method == "GET":
                    return app._json(
                        HTTPStatus.OK, self._dto(self.service.receipt(token, parts[1]))
                    )
                if len(parts) == 3 and parts[2] in {"settle", "cancel"} and method == "POST":
                    values = self._request_values(app, environ)
                    if parts[2] == "settle":
                        self._keys(values, {"outcome", "idempotency_key"})
                        result = self.service.settle_sandbox(
                            token, parts[1], values["outcome"], values["idempotency_key"]
                        )
                    else:
                        self._keys(values, {"idempotency_key"})
                        result = self.service.cancel_order(
                            token, parts[1], values["idempotency_key"]
                        )
                    return app._json(HTTPStatus.OK, self._dto(result))
            if suffix == "licenses" and method == "GET":
                return app._json(HTTPStatus.OK, self._dto(self.licenses.status(token)))
            if suffix == "licenses" and method == "POST":
                values = self._request_values(app, environ)
                if set(values) == {"signed_license"}:
                    result = self.licenses.install(token, values["signed_license"])
                else:
                    required = {"plan_code", "features", "student_limit", "expires_at"}
                    if not required <= set(values) or set(values) - required - {"idempotency_key"}:
                        raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
                    result = self.licenses.issue(
                        token,
                        values["plan_code"],
                        features=values["features"],
                        student_limit=values["student_limit"],
                        expires_at=values["expires_at"],
                        idempotency_key=values.get("idempotency_key"),
                    )
                return app._json(HTTPStatus.CREATED, self._dto(result))
            raise HttpInputError(HTTPStatus.NOT_FOUND, "RESOURCE_UNAVAILABLE")
        except HttpInputError:
            raise
        except BillingError as error:
            status = (
                HTTPStatus(error.status_code)
                if error.status_code in HTTPStatus._value2member_map_
                else HTTPStatus.UNPROCESSABLE_ENTITY
            )
            return app._json(status, {"error": error.code})
        except ResourceNotFound:
            return app._json(HTTPStatus.NOT_FOUND, {"error": "RESOURCE_UNAVAILABLE"})
        except LockoutError as error:
            return app._json(
                HTTPStatus.TOO_MANY_REQUESTS,
                {"error": "LOGIN_LOCKED", "retry_after": error.retry_after},
            )
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
        except (ValueError, TypeError, KeyError):
            return app._json(HTTPStatus.BAD_REQUEST, {"error": "INVALID_REQUEST"})

    @staticmethod
    def _signature_headers(environ):
        allowed = {
            "HTTP_X_SIGNATURE",
            "HTTP_X_TIMESTAMP",
            "HTTP_STRIPE_SIGNATURE",
            "HTTP_X_MOMO_SIGNATURE",
            "HTTP_X_VNPAY_SIGNATURE",
            "HTTP_X_SANDBOX_SIGNATURE",
        }
        return {
            name[5:].lower().replace("_", "-"): str(value)
            for name, value in environ.items()
            if name in allowed
        }

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

    @classmethod
    def _dto(cls, value):
        if is_dataclass(value):
            allowed = {
                "Quote": {
                    "quote_id",
                    "plan_code",
                    "months",
                    "subtotal_minor",
                    "discount_minor",
                    "credit_minor",
                    "total_minor",
                    "currency",
                    "created_at",
                    "expires_at",
                    "effective_at",
                    "ends_at",
                    "change_kind",
                },
                "Order": {
                    "order_id",
                    "quote_id",
                    "state",
                    "gateway",
                    "mode",
                    "checkout_ref",
                    "amount_minor",
                    "currency",
                    "created_at",
                    "updated_at",
                },
                "Receipt": {
                    "receipt_id",
                    "order_id",
                    "plan_code",
                    "amount_minor",
                    "currency",
                    "issued_at",
                },
            }.get(type(value).__name__, set())
            return {
                field.name: cls._dto(getattr(value, field.name))
                for field in fields(value)
                if field.name in allowed
            }
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat()
        if isinstance(value, dict):
            return {str(key): cls._dto(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [cls._dto(item) for item in value]
        if value is None or type(value) in {str, int, bool, float}:
            return value
        return str(value.value) if hasattr(value, "value") else None

    @staticmethod
    def _keys(values, allowed):
        if set(values) != allowed:
            raise HttpInputError(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST")
