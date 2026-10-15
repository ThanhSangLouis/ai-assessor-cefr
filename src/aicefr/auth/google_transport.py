"""Small bounded HTTPS transport for the fixed Google OIDC endpoints."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Protocol

TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
MAX_RESPONSE_BYTES = 256 * 1024


class GoogleTransportError(RuntimeError):
    """Provider request failed or exceeded the safe response policy."""


class JsonTransport(Protocol):
    def request_json(
        self,
        method: str,
        url: str,
        *,
        data: Mapping[str, str] | None = None,
        timeout: float = 5.0,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> dict[str, object]: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class GoogleHttpsTransport:
    """HTTPS-only JSON client with certificate checks and bounded bodies."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            _NoRedirect(),
        )

    def request_json(
        self,
        method: str,
        url: str,
        *,
        data: Mapping[str, str] | None = None,
        timeout: float = 5.0,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> dict[str, object]:
        if url not in (TOKEN_URL, JWKS_URL) or method not in ("GET", "POST"):
            raise GoogleTransportError("provider endpoint unavailable")
        if (method, url) not in (("GET", JWKS_URL), ("POST", TOKEN_URL)):
            raise GoogleTransportError("provider request unavailable")
        payload = None
        headers = {"Accept": "application/json"}
        if data is not None:
            payload = urllib.parse.urlencode(data).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                if response.geturl() != url:
                    raise GoogleTransportError("provider redirect rejected")
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > max_bytes:
                    raise GoogleTransportError("provider response too large")
                body = response.read(max_bytes + 1)
        except GoogleTransportError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise GoogleTransportError("provider request failed") from exc
        if len(body) > max_bytes:
            raise GoogleTransportError("provider response too large")
        try:
            result = json.loads(body, object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise GoogleTransportError("provider response invalid") from exc
        if not isinstance(result, dict):
            raise GoogleTransportError("provider response invalid")
        return result


def _unique_object(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result
