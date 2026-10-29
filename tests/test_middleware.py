"""Focused checks for the shared HTTP middleware used by the W7 runtime."""

from __future__ import annotations

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aicefr.api.middleware import (
    LoginRateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from aicefr.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoginRateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    @app.get("/login")
    def login_page() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/private")
    def private_api() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/error")
    def error() -> None:
        raise RuntimeError("private implementation detail")

    return app


def test_request_id_is_generated_and_inbound_value_is_preserved() -> None:
    client = TestClient(make_app())

    generated = client.get("/login").headers["x-request-id"]
    supplied = client.get("/login", headers={"x-request-id": "trace-123"})

    assert re.fullmatch(r"[0-9a-f]{16}", generated)
    assert supplied.headers["x-request-id"] == "trace-123"


def test_security_headers_and_private_api_cache_policy() -> None:
    client = TestClient(make_app())

    page = client.get("/login")
    api = client.get("/api/private")

    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.headers["x-frame-options"] == "DENY"
    assert "microphone=(self)" in page.headers["permissions-policy"]
    assert api.headers["cache-control"] == "private, no-store"


def test_hsts_is_added_only_when_https_only_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AICEFR_HTTPS_ONLY", "true")
    get_settings.cache_clear()

    response = TestClient(make_app()).get("/login")

    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_login_rate_limit_returns_429_with_retry_after(monkeypatch) -> None:
    monkeypatch.setenv("AICEFR_LOGIN_RATE", "2")
    get_settings.cache_clear()
    client = TestClient(make_app())

    responses = [client.post("/api/v1/auth/login") for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 429]
    assert responses[-1].headers["retry-after"] == "60"
    assert responses[-1].headers["x-request-id"]


def test_unhandled_error_returns_generic_body_with_security_headers() -> None:
    response = TestClient(make_app()).get("/error")

    assert response.status_code == 500
    assert response.json() == {"detail": "lỗi nội bộ, vui lòng thử lại"}
    assert response.headers["x-request-id"]
    assert response.headers["x-frame-options"] == "DENY"
    assert "private implementation detail" not in response.text
