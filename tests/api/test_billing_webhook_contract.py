from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import quote_plus, urlencode

from aicefr.api.billing import BillingApi
from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.auth.service import AuthService
from aicefr.billing.gateways import GatewayRegistry
from aicefr.billing.licenses import LicenseService
from aicefr.billing.secrets import KeyRing
from aicefr.billing.service import BillingService
from aicefr.contracts import ActorRole
from aicefr.local.app import SQLiteSessionRepository
from aicefr.portal.router import PortalRouter
from aicefr.storage.billing import BillingRepository
from aicefr.storage.sqlite import SQLiteStore

NOW = datetime(2026, 10, 15, 4, 0, tzinfo=UTC)
STRIPE_TEST_KEY = "sk_test_" + "x" * 20
STRIPE_HOOK = "whsec_" + "y" * 20
VNPAY_SECRET = "fixture-vnpay-secret"


class _NoStudentApi:
    def submit(self, token, request):  # pragma: no cover - unrelated route
        raise AssertionError("student route is outside this test")


def _app(tmp_path, *, stripe=True, vnpay=True):
    store = SQLiteStore(tmp_path / "data")
    auth = AuthService(store, SQLiteSessionRepository(store), clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    token = auth.login("fixture-admin", "valid-admin-password")
    response_calls = []

    def mock_transport(**request):
        response_calls.append(request)
        order_id = request["payload"].get("client_reference_id") or request["payload"].get(
            "vnp_TxnRef"
        )
        if request["endpoint"].endswith("checkout/sessions"):
            return {
                "id": "cs_test_" + str(len(response_calls)),
                "url": "https://checkout.stripe.com/c/pay/test",
            }
        return {
            "vnp_TxnRef": order_id,
            "redirect_url": "https://sandbox.vnpayment.vn/payment2?fixture=1",
        }

    gateway_config = {
        "stripe": {
            "enabled": stripe,
            "mode": "test",
            "test_secret_key": STRIPE_TEST_KEY,
            "webhook_secret": STRIPE_HOOK,
        },
        "vnpay": {
            "enabled": vnpay,
            "mode": "test",
            "terminal_code": "TESTTMN1",
            "hash_secret": VNPAY_SECRET,
        },
    }
    keyring = KeyRing(store.data_dir)
    gateways = GatewayRegistry(
        gateway_config, store.data_dir, mock_transport, keyring=keyring, clock=lambda: NOW
    )
    repository = BillingRepository(store)
    licenses = LicenseService(auth, store, keyring, clock=lambda: NOW)
    billing = BillingService(auth, repository, gateways, licenses, clock=lambda: NOW)
    billing_api = BillingApi(auth, billing, gateways, licenses)
    router = PortalRouter(None, None, None, None, billing_api=billing_api)
    app = StudentTeacherApp(StudentApi(_NoStudentApi()), auth=auth, portal=router)
    return store, auth, token, gateways, billing, app, response_calls


def _call(
    app, path, *, method="POST", body=b"", token=None, headers=None, content_type="application/json"
):
    result = {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_HOST": "localhost:8000",
        "HTTP_ORIGIN": "http://localhost:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
    }
    if token:
        environ["HTTP_AUTHORIZATION"] = "Bearer " + token
    if headers:
        environ.update(headers)

    def start_response(status, response_headers):
        result["status"] = status
        result["headers"] = response_headers

    response = b"".join(app(environ, start_response))
    return result["status"], response


def _create_order(billing, token, gateway):
    quote = billing.quote(token, "STANDARD", 1, f"quote-{gateway}-key")
    return billing.create_order(token, quote.quote_id, gateway, f"order-{gateway}-key")


def _stripe_event(order, *, amount=None, top_live=False, session_live=False):
    body = json.dumps(
        {
            "id": "evt_contract_1",
            "type": "checkout.session.completed",
            "livemode": top_live,
            "data": {
                "object": {
                    "id": order.checkout_ref,
                    "client_reference_id": order.order_id,
                    "amount_total": order.amount_minor if amount is None else amount,
                    "currency": order.currency.lower(),
                    "payment_status": "paid",
                    "livemode": session_live,
                }
            },
        },
        separators=(", ", ": "),
    ).encode()
    timestamp = str(int(NOW.timestamp()))
    digest = hmac.new(
        STRIPE_HOOK.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return body, {"HTTP_STRIPE_SIGNATURE": f"t={timestamp},v1={digest}"}


def _vnpay_form(order, *, amount=None):
    fields = {
        "vnp_TmnCode": "TESTTMN1",
        "vnp_TxnRef": order.order_id,
        "vnp_TransactionNo": "txn-contract-1",
        "vnp_Amount": str((order.amount_minor if amount is None else amount) * 100),
        "vnp_CurrCode": "VND",
        "vnp_TransactionStatus": "00",
        "vnp_ResponseCode": "00",
        "vnp_PayDate": "20261015110000",
    }
    signed = "&".join(
        f"{key}={quote_plus(value, safe='')}" for key, value in sorted(fields.items())
    )
    fields["vnp_SecureHash"] = hmac.new(
        VNPAY_SECRET.encode(), signed.encode("ascii"), hashlib.sha512
    ).hexdigest()
    return urlencode(fields).encode()


def test_stripe_webhook_preserves_exact_raw_body_and_duplicate_delivery_settles_once(tmp_path):
    store, _, token, _, billing, app, _ = _app(tmp_path)
    try:
        order = _create_order(billing, token, "stripe")
        body, signature = _stripe_event(order)
        status, response = _call(
            app, "/api/v1/billing/webhooks/stripe", body=body, headers=signature
        )
        assert status.startswith("200")
        assert json.loads(response)["state"] == "PAID"

        status, response = _call(
            app, "/api/v1/billing/webhooks/stripe", body=body, headers=signature
        )
        assert status.startswith("200")
        assert json.loads(response)["state"] == "PAID"
        assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
        assert billing._repository.current_entitlement(NOW).plan_code == "STANDARD"
    finally:
        store.close()


def test_stripe_signature_mode_and_amount_failures_do_not_apply_entitlement(tmp_path):
    store, _, token, _, billing, app, _ = _app(tmp_path)
    try:
        order = _create_order(billing, token, "stripe")
        bad_body, signature = _stripe_event(order)
        status, response = _call(
            app,
            "/api/v1/billing/webhooks/stripe",
            body=bad_body + b" ",
            headers=signature,
        )
        assert status.startswith("422")
        assert json.loads(response) == {"error": "gateway_invalid_signature"}

        wrong_mode, signature = _stripe_event(order, session_live=True)
        status, response = _call(
            app, "/api/v1/billing/webhooks/stripe", body=wrong_mode, headers=signature
        )
        assert status.startswith("409")
        assert json.loads(response) == {"error": "gateway_mode_mismatch"}

        wrong_event_mode, signature = _stripe_event(order, top_live=True)
        status, response = _call(
            app,
            "/api/v1/billing/webhooks/stripe",
            body=wrong_event_mode,
            headers=signature,
        )
        assert status.startswith("409")
        assert json.loads(response) == {"error": "gateway_mode_mismatch"}

        wrong_amount, signature = _stripe_event(order, amount=order.amount_minor - 100)
        status, response = _call(
            app,
            "/api/v1/billing/webhooks/stripe",
            body=wrong_amount,
            headers=signature,
        )
        assert status.startswith("409")
        assert json.loads(response) == {"error": "payment_binding_mismatch"}
        assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
        assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 0
        assert billing._repository.current_entitlement(NOW).plan_code == "FREE"
    finally:
        store.close()


def test_vnpay_form_encoded_signed_callback_settles_matching_order(tmp_path):
    store, _, token, _, billing, app, _ = _app(tmp_path)
    try:
        order = _create_order(billing, token, "vnpay")
        status, response = _call(
            app,
            "/api/v1/billing/webhooks/vnpay",
            body=_vnpay_form(order),
            content_type="application/x-www-form-urlencoded",
        )
        assert status.startswith("200")
        assert json.loads(response)["state"] == "PAID"
        assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
    finally:
        store.close()


def test_internal_sandbox_http_webhook_uses_signed_header_and_deduplicates(tmp_path):
    store, _, token, gateways, billing, app, _ = _app(tmp_path)
    try:
        order = _create_order(billing, token, "sandbox")
        raw, signed_headers = gateways.sign_sandbox_event(
            {
                "event_id": "evt_sandbox_contract_1",
                "order_id": order.order_id,
                "checkout_id": order.checkout_ref,
                "amount": order.amount_minor,
                "currency": order.currency,
                "status": "paid",
            }
        )
        headers = {"HTTP_X_SANDBOX_SIGNATURE": signed_headers["X-Sandbox-Signature"]}
        status, response = _call(app, "/api/v1/billing/webhooks/sandbox", body=raw, headers=headers)
        assert status.startswith("200")
        assert json.loads(response)["state"] == "PAID"

        status, response = _call(app, "/api/v1/billing/webhooks/sandbox", body=raw, headers=headers)
        assert status.startswith("200")
        assert json.loads(response)["state"] == "PAID"
        assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
    finally:
        store.close()


def test_license_issue_api_replays_exact_artifact_and_conflicts_on_changed_payload(tmp_path):
    store, _, token, _, _, app, _ = _app(tmp_path)
    try:
        request = {
            "plan_code": "STANDARD",
            "features": ["learning", "practice", "class_insights"],
            "student_limit": 100,
            "expires_at": "2026-11-14T04:00:00+00:00",
            "idempotency_key": "api-license-issue-01",
        }
        body = json.dumps(request, separators=(",", ":")).encode()
        status, first = _call(
            app,
            "/api/v1/admin/billing/licenses",
            body=body,
            token=token,
        )
        assert status.startswith("201")
        status, replay = _call(
            app,
            "/api/v1/admin/billing/licenses",
            body=body,
            token=token,
        )
        assert status.startswith("201")
        assert json.loads(replay) == json.loads(first)
        issued = json.loads(first)
        assert issued["signed_license"]["payload"]["organization"] == "local-demo"
        assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1

        changed = dict(request, plan_code="ADVANCED")
        status, response = _call(
            app,
            "/api/v1/admin/billing/licenses",
            body=json.dumps(changed, separators=(",", ":")).encode(),
            token=token,
        )
        assert status.startswith("409")
        assert json.loads(response) == {"error": "idempotency_key_reused"}
        assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    finally:
        store.close()


def test_disabled_provider_webhook_is_not_ready_and_does_not_mutate_state(tmp_path):
    store, _, _, _, _, app, _ = _app(tmp_path, stripe=False, vnpay=False)
    try:
        status, body = _call(
            app,
            "/api/v1/billing/webhooks/stripe",
            body=b"{}",
            headers={"HTTP_STRIPE_SIGNATURE": "t=1,v1=" + "0" * 64},
        )
        assert status.startswith("503")
        assert json.loads(body) == {"error": "gateway_not_ready"}
        assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    finally:
        store.close()
