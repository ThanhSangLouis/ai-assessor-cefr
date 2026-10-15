from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace

from aicefr.audio.config import QCConfig
from aicefr.billing.plans import PLANS
from aicefr.contracts import ActorRole
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.scoring.scorer import RidgeScorer


def _call(app, path, *, token=None, method="GET", raw=None, payload=None):
    body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/json" if payload is not None or raw is not None else "",
        "HTTP_AUTHORIZATION": "Bearer " + token if token else "",
        "HTTP_HOST": "localhost:8000",
        "HTTP_ORIGIN": "http://localhost:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
    }
    result = {}
    response = b"".join(app(environ, lambda status, headers: result.update(status=status)))
    result["body"] = response
    result["json"] = json.loads(response) if response else None
    return result


def test_admin_billing_quote_order_settlement_and_receipt_are_safe(tmp_path):
    config = _demo_config()
    pipeline = SimpleNamespace(_qc_config=QCConfig(**config["qc"]), _scorer=RidgeScorer.load())
    runtime = create_runtime(tmp_path / "data", config=config, pipeline=pipeline)
    try:
        admin = runtime.auth.bootstrap_fixture_account(
            "fixture-admin", ActorRole.ADMIN, "admin-password"
        )
        student = runtime.auth.bootstrap_fixture_account(
            "fixture-student", ActorRole.STUDENT, "student-password"
        )
        admin_token = runtime.auth.login(admin.actor_id, "admin-password")
        student_token = runtime.auth.login(student.actor_id, "student-password")
        denied = _call(runtime.app, "/api/v1/admin/billing", token=student_token)
        assert denied["status"].startswith("403")
        overview = _call(runtime.app, "/api/v1/admin/billing", token=admin_token)
        assert overview["status"].startswith("200")
        assert overview["json"]["overview"]["sandbox"] is True
        assert "secret" not in overview["body"].decode().lower()

        duplicate = _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            raw=b'{"plan_code":"STANDARD","plan_code":"ADVANCED",'
            b'"months":1,"idempotency_key":"quote-duplicate"}',
        )
        assert duplicate["status"].startswith("400")

        quote = _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            payload={"plan_code": "STANDARD", "months": 1, "idempotency_key": "quote-api-1"},
        )
        assert quote["status"].startswith("201")
        order = _call(
            runtime.app,
            "/api/v1/admin/billing/orders",
            token=admin_token,
            method="POST",
            payload={
                "quote_id": quote["json"]["quote_id"],
                "gateway": "sandbox",
                "idempotency_key": "order-api-1",
            },
        )
        assert order["status"].startswith("201")
        order_id = order["json"]["order_id"]
        settled = _call(
            runtime.app,
            f"/api/v1/admin/billing/orders/{order_id}/settle",
            token=admin_token,
            method="POST",
            payload={"outcome": "paid", "idempotency_key": "settle-api-1"},
        )
        assert settled["status"].startswith("200")
        receipt = _call(
            runtime.app, f"/api/v1/admin/billing/orders/{order_id}/receipt", token=admin_token
        )
        assert receipt["status"].startswith("200")
        assert receipt["json"]["order_id"] == order_id
        assert "signature" not in receipt["body"].decode().lower()
    finally:
        runtime.close()


def test_billing_api_lists_cancels_and_issues_safe_license_artifact(tmp_path):
    config = _demo_config()
    pipeline = SimpleNamespace(_qc_config=QCConfig(**config["qc"]), _scorer=RidgeScorer.load())
    runtime = create_runtime(tmp_path / "data", config=config, pipeline=pipeline)
    try:
        admin = runtime.auth.bootstrap_fixture_account(
            "fixture-admin", ActorRole.ADMIN, "admin-password"
        )
        student = runtime.auth.bootstrap_fixture_account(
            "fixture-student", ActorRole.STUDENT, "student-password"
        )
        admin_token = runtime.auth.login(admin.actor_id, "admin-password")
        student_token = runtime.auth.login(student.actor_id, "student-password")
        assert _call(runtime.app, "/api/v1/admin/billing/no-such-route", token=admin_token)[
            "status"
        ].startswith("404")
        assert _call(runtime.app, "/api/v1/admin/billing/gateways", token=admin_token)[
            "status"
        ].startswith("200")
        assert _call(runtime.app, "/api/v1/admin/billing/licenses", token=admin_token)[
            "status"
        ].startswith("200")
        assert _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            raw=b'{"plan_code":"STANDARD","months":1,"idempotency_key":"same","months":2}',
        )["status"].startswith("400")
        assert _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            raw=b'{"plan_code":NaN}',
        )["status"].startswith("400")
        assert _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            raw=b"{}",
        )["status"].startswith("400")

        quote = _call(
            runtime.app,
            "/api/v1/admin/billing/quotes",
            token=admin_token,
            method="POST",
            payload={"plan_code": "STANDARD", "months": 1, "idempotency_key": "cancel-q"},
        )
        order = _call(
            runtime.app,
            "/api/v1/admin/billing/orders",
            token=admin_token,
            method="POST",
            payload={
                "quote_id": quote["json"]["quote_id"],
                "gateway": "sandbox",
                "idempotency_key": "cancel-o",
            },
        )
        order_id = order["json"]["order_id"]
        listing = _call(runtime.app, "/api/v1/admin/billing/orders", token=admin_token)
        assert listing["status"].startswith("200")
        assert any(row["order_id"] == order_id for row in listing["json"]["items"])
        cancelled = _call(
            runtime.app,
            f"/api/v1/admin/billing/orders/{order_id}/cancel",
            token=admin_token,
            method="POST",
            payload={"idempotency_key": "cancel-c"},
        )
        assert cancelled["status"].startswith("200")
        assert cancelled["json"]["state"] == "CANCELLED"
        assert _call(
            runtime.app,
            "/api/v1/admin/billing/orders/missing/receipt",
            token=admin_token,
        )["status"].startswith("404")

        issue = _call(
            runtime.app,
            "/api/v1/admin/billing/licenses",
            token=admin_token,
            method="POST",
            payload={
                "plan_code": "STANDARD",
                "features": sorted(PLANS["STANDARD"].features),
                "student_limit": 50,
                "expires_at": "2027-10-15T00:00:00+00:00",
                "idempotency_key": "license-api-issue",
            },
        )
        assert issue["status"].startswith("201")
        artifact = issue["json"]["signed_license"]
        assert "signature" in json.dumps(artifact)
        installed = _call(
            runtime.app,
            "/api/v1/admin/billing/licenses",
            token=admin_token,
            method="POST",
            payload={"signed_license": artifact},
        )
        assert installed["status"].startswith("201")
        assert "signature" not in installed["body"].decode().lower()
        assert _call(runtime.app, "/api/v1/admin/billing", token=student_token)[
            "status"
        ].startswith("403")
    finally:
        runtime.close()
