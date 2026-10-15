from __future__ import annotations

from contextlib import AbstractContextManager

import pytest

from aicefr.auth.google_transport import (
    JWKS_URL,
    TOKEN_URL,
    GoogleHttpsTransport,
    GoogleTransportError,
    _NoRedirect,
)


class FakeResponse(AbstractContextManager):
    def __init__(self, body: bytes, *, url: str = JWKS_URL, headers: dict[str, str] | None = None):
        self.body = body
        self.url = url
        self.headers = headers or {}
        self.read_size: int | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        self.read_size = size
        return self.body[:size]


class FakeOpener:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.timeout: float | None = None

    def open(self, _request, *, timeout: float):
        self.timeout = timeout
        if self.error:
            raise self.error
        return self.response


def test_transport_rejects_non_fixed_endpoints_and_methods():
    transport = GoogleHttpsTransport()
    with pytest.raises(GoogleTransportError):
        transport.request_json("GET", "https://attacker.example/jwks")
    with pytest.raises(GoogleTransportError):
        transport.request_json("POST", JWKS_URL, data={"code": "secret"})


def test_transport_rejects_redirects_and_caps_response_body():
    transport = GoogleHttpsTransport()
    redirected = FakeResponse(b"{}", url="https://attacker.example/collect")
    transport._opener = FakeOpener(redirected)
    with pytest.raises(GoogleTransportError, match="redirect"):
        transport.request_json("GET", JWKS_URL)

    oversized = FakeResponse(b'{"keys":[]}', headers={"Content-Length": "100"})
    transport._opener = FakeOpener(oversized)
    with pytest.raises(GoogleTransportError, match="too large"):
        transport.request_json("GET", JWKS_URL, max_bytes=10)

    unbounded = FakeResponse(b"x" * 11)
    transport._opener = FakeOpener(unbounded)
    with pytest.raises(GoogleTransportError, match="too large"):
        transport.request_json("GET", JWKS_URL, max_bytes=10)
    assert unbounded.read_size == 11


def test_transport_uses_timeout_and_rejects_invalid_or_duplicate_json():
    transport = GoogleHttpsTransport()
    response = FakeResponse(b'{"keys":[]}')
    opener = FakeOpener(response)
    transport._opener = opener
    assert transport.request_json("GET", JWKS_URL, timeout=1.25) == {"keys": []}
    assert opener.timeout == 1.25

    transport._opener = FakeOpener(FakeResponse(b'{"keys":[],"keys":[]}'))
    with pytest.raises(GoogleTransportError, match="invalid"):
        transport.request_json("GET", JWKS_URL)

    transport._opener = FakeOpener(error=TimeoutError("sensitive timeout details"))
    with pytest.raises(GoogleTransportError, match="failed") as error:
        transport.request_json("POST", TOKEN_URL, data={"code": "not-for-logs"})
    assert "sensitive timeout details" not in str(error.value)


def test_redirect_handler_never_constructs_a_redirect_request():
    handler = _NoRedirect()
    assert (
        handler.redirect_request(None, None, 302, "found", {}, "https://attacker.example") is None
    )
