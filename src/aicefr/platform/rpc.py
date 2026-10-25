"""Internal calls between services: a facade's methods, over JSON and HTTP (D043).

When one service needs another's data while answering a request -- the
assessment service asking identity which students allow research use, the
learning service asking assessment for a learner's latest result -- it calls a
method of the other service's **facade**. The facade is a plain class in the
owning service, with plain JSON-able arguments and results. The same object
answers in two ways:

* in one process (`aicefr.api.main`, the tests) the caller holds the facade
  itself and the call is a method call;
* between services the caller holds a `RemoteFacade`, which POSTs the keyword
  arguments to `/internal/<service>/<method>` on the owner, where
  `internal_router` calls the facade and returns the result.

Only methods marked `@exposed` can be reached, and only with the deployment's
internal key in `X-Aicefr-Internal`: the gateway never forwards `/internal/`,
and a request without the key is refused even from inside the network.

No exception crosses the wire as an exception. A facade method that can refuse
returns the refusal (a reason string, None for "allowed"); a failure of the
call itself raises `RemoteError` on the caller's side.
"""

from __future__ import annotations

import hmac
import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Body, Header, HTTPException
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

INTERNAL_HEADER = "X-Aicefr-Internal"
TIMEOUT_S = 15.0

# (method, path, JSON body) -> (status, JSON body). The default goes over
# HTTP with urllib; the tests pass one that goes through a TestClient.
Transport = Callable[[str, str, dict | None], tuple[int, Any]]


def exposed(func: Callable) -> Callable:
    """Mark a facade method as callable from another service."""
    func.__exposed__ = True
    return func


def same_key(expected: str, given: str | None) -> bool:
    """A constant-time comparison that refuses, not crashes, on a header of odd characters."""
    if not expected or not given:
        return False
    return hmac.compare_digest(expected.encode(), given.encode("utf-8", "replace"))


def check_internal(token: str, given: str | None) -> None:
    """Refuse a call that does not carry the deployment's internal key."""
    if not same_key(token, given):
        raise HTTPException(403, "internal endpoint")


class RemoteError(Exception):
    """An internal call failed: the other service refused it or did not answer."""

    def __init__(self, service: str, method: str, status: int, detail: str) -> None:
        super().__init__(f"{service}.{method}: {status} {detail}")
        self.status = status


def internal_router(service: str, facade: object, token: str) -> APIRouter:
    """`/internal/<service>/<method>` for each `@exposed` method of `facade`."""
    router = APIRouter(prefix=f"/internal/{service}", include_in_schema=False)

    @router.post("/{method}")
    def call(
        method: str,
        kwargs: Annotated[dict | None, Body()] = None,
        internal: Annotated[str | None, Header(alias=INTERNAL_HEADER)] = None,
    ) -> dict:
        check_internal(token, internal)
        func = getattr(facade, method, None)
        if func is None or not getattr(func, "__exposed__", False):
            raise HTTPException(404, f"{service} has no internal method {method}")
        try:
            return {"result": jsonable_encoder(func(**(kwargs or {})))}
        except TypeError as e:
            raise HTTPException(422, str(e)) from e

    return router


def http_transport(base_url: str, token: str, timeout: float = TIMEOUT_S) -> Transport:
    def send(method: str, path: str, body: dict | None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            base_url.rstrip("/") + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", INTERNAL_HEADER: token},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - internal URL from settings
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"null")
            except ValueError:
                return e.code, None

    return send


class RemoteFacade:
    """Another service's facade, reached over HTTP. `client.method(**kwargs)` as if local."""

    def __init__(self, service: str, transport: Transport) -> None:
        self._service = service
        self._transport = transport

    def __getattr__(self, method: str) -> Callable[..., Any]:
        if method.startswith("_"):
            raise AttributeError(method)

        def call(**kwargs: Any) -> Any:
            try:
                status, body = self._transport(
                    "POST", f"/internal/{self._service}/{method}", jsonable_encoder(kwargs)
                )
            except OSError as e:
                raise RemoteError(self._service, method, 503, str(e)) from e
            if status != 200:
                detail = body.get("detail") if isinstance(body, dict) else body
                raise RemoteError(self._service, method, status, str(detail))
            return body["result"]

        return call


def remote(service: str, base_url: str, token: str) -> RemoteFacade:
    return RemoteFacade(service, http_transport(base_url, token))
