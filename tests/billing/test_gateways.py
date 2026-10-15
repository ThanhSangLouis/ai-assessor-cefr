from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aicefr.billing.gateways import (
    GatewayError,
    GatewayRegistry,
    _canonical,
    _headers,
    _momo_signature,
    _strict_json,
    _timestamp,
    _vnpay_signature,
)
from aicefr.billing.secrets import KeyRing, KeyStoreError

NOW = datetime(2026, 10, 15, 4, 0, tzinfo=UTC)


def test_keyring_is_private_persistent_and_domain_separated(tmp_path):
    first = KeyRing(tmp_path)
    second = KeyRing(tmp_path)
    path = tmp_path / "billing-hmac.key"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert first.sign_license(b"payload") == second.sign_license(b"payload")
    assert first.verify_license(b"payload", second.sign_license(b"payload"))
    assert not first.verify_gateway_event(b"payload", second.sign_license(b"payload"))


def test_keyring_rejects_symlink_hardlink_and_open_permissions(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"do not follow")
    linkdir = tmp_path / "linkdir"
    linkdir.mkdir()
    (linkdir / "billing-hmac.key").symlink_to(target)
    with pytest.raises(KeyStoreError):
        KeyRing(linkdir)

    linkfile_dir = tmp_path / "hardlinkdir"
    linkfile_dir.mkdir()
    key_path = linkfile_dir / "billing-hmac.key"
    KeyRing(linkfile_dir)
    os.link(key_path, linkfile_dir / "second-link")
    with pytest.raises(KeyStoreError):
        KeyRing(linkfile_dir)

    loose = tmp_path / "loose"
    loose.mkdir()
    KeyRing(loose)
    (loose / "billing-hmac.key").chmod(0o640)
    with pytest.raises(KeyStoreError):
        KeyRing(loose)


def test_keyring_rejects_bad_injected_or_persisted_material_and_bounds_signatures(tmp_path):
    with pytest.raises(KeyStoreError, match="invalid key material"):
        KeyRing(tmp_path / "injected", key=b"short")
    bad_version = tmp_path / "bad-version"
    bad_version.mkdir()
    (bad_version / "billing-hmac.key").write_bytes(b"wrong-format")
    (bad_version / "billing-hmac.key").chmod(0o600)
    with pytest.raises(KeyStoreError, match="invalid billing key version"):
        KeyRing(bad_version)

    bad_encoded = tmp_path / "bad-encoded"
    bad_encoded.mkdir()
    (bad_encoded / "billing-hmac.key").write_bytes(KeyRing._prefix + b"%%%\n")
    (bad_encoded / "billing-hmac.key").chmod(0o600)
    with pytest.raises(KeyStoreError, match="billing key storage unavailable"):
        KeyRing(bad_encoded)

    oversized = tmp_path / "oversized"
    oversized.mkdir()
    (oversized / "billing-hmac.key").write_bytes(KeyRing._prefix + b"A" * 600)
    (oversized / "billing-hmac.key").chmod(0o600)
    with pytest.raises(KeyStoreError, match="invalid billing key file"):
        KeyRing(oversized)

    ring = KeyRing(tmp_path / "good")
    assert not ring.verify_license(b"data", "short")
    assert not ring.verify_license(b"data", "0" * 64)
    assert not ring.verify("license:é", b"data", "0" * 64)
    with pytest.raises(ValueError, match="invalid signature domain"):
        ring.sign("", b"data")
    with pytest.raises(ValueError, match="invalid signature payload"):
        ring.sign("license:v1", b"x" * 65_537)


def test_keyring_requires_external_storage_or_injected_key(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    assert not (repo_root / "billing-hmac.key").exists()
    with pytest.raises(KeyStoreError, match="billing key storage unavailable"):
        KeyRing(repo_root)
    assert not (repo_root / "billing-hmac.key").exists()

    injected = KeyRing(tmp_path, key=b"k" * 32)
    assert injected.verify_license(b"payload", injected.sign_license(b"payload"))
    assert not (tmp_path / "billing-hmac.key").exists()


def test_internal_sandbox_event_signature_timestamp_and_duplicate_json(tmp_path):
    registry = GatewayRegistry(data_dir=tmp_path, clock=lambda: NOW)
    event = {
        "event_id": "evt_1",
        "order_id": "ord_1",
        "checkout_id": "sbx_1",
        "amount": 123,
        "currency": "VND",
        "status": "paid",
    }
    raw, headers = registry.sign_sandbox_event(event)
    result = registry.verify_event("sandbox", raw, headers)
    assert result["status"] == "paid"
    assert result["signature_valid"] is True
    assert result["occurred_at"] == NOW

    bad_headers = {"X-Sandbox-Signature": "0" * 64}
    with pytest.raises(GatewayError, match="gateway_invalid_signature"):
        registry.verify_event("sandbox", raw, bad_headers)

    duplicate = b'{"event_id":"a","event_id":"b"}'
    duplicate_signature = KeyRing(tmp_path).sign_gateway_event(duplicate)
    with pytest.raises(GatewayError, match="gateway_duplicate_field"):
        registry.verify_event("sandbox", duplicate, {"X-Sandbox-Signature": duplicate_signature})

    stale = dict(event, occurred_at=(NOW - timedelta(minutes=6)).isoformat())
    stale_raw, stale_headers = registry.sign_sandbox_event(stale)
    with pytest.raises(GatewayError, match="gateway_expired_event"):
        registry.verify_event("sandbox", stale_raw, stale_headers)


def test_stripe_test_webhook_requires_raw_body_signature_and_mock_transport(tmp_path):
    calls = []

    def mock_transport(**request):
        calls.append(request)
        return {"id": "cs_test_1", "url": "https://checkout.stripe.com/c/pay/cs_test_1"}

    config = {
        "stripe": {
            "enabled": True,
            "mode": "test",
            "test_secret_key": "sk_test_" + "x" * 20,
            "webhook_secret": "whsec_" + "y" * 20,
        }
    }
    registry = GatewayRegistry(config, tmp_path, mock_transport, clock=lambda: NOW)
    checkout = registry.create_session(
        "stripe", {"order_id": "ord_1", "amount": 99000, "currency": "VND"}
    )
    assert checkout["checkout_id"] == "cs_test_1"
    assert len(calls) == 1
    assert calls[0]["endpoint"] == "https://api.stripe.com/v1/checkout/sessions"

    body = json.dumps(
        {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "client_reference_id": "ord_1",
                    "amount_total": 99000,
                    "currency": "vnd",
                    "payment_status": "paid",
                    "livemode": False,
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    stamp = str(int(NOW.timestamp()))
    sig = hmac.new(
        config["stripe"]["webhook_secret"].encode(), stamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    result = registry.verify_event("stripe", body, {"Stripe-Signature": f"t={stamp},v1={sig}"})
    assert (result["order_id"], result["amount"], result["gateway"], result["mode"]) == (
        "ord_1",
        99000,
        "stripe",
        "test",
    )
    fallback_body = json.dumps(
        {
            "id": "evt_fallback_1",
            "type": "checkout.session.expired",
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_test_fallback",
                    "metadata": {"order_id": "ord_metadata_fallback"},
                    "amount_total": 99000,
                    "currency": "vnd",
                    "payment_status": "unpaid",
                    "livemode": False,
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    fallback_sig = hmac.new(
        config["stripe"]["webhook_secret"].encode(),
        stamp.encode() + b"." + fallback_body,
        hashlib.sha256,
    ).hexdigest()
    fallback = registry.verify_event(
        "stripe", fallback_body, {"Stripe-Signature": f"t={stamp},v1={fallback_sig}"}
    )
    assert fallback["order_id"] == "ord_metadata_fallback"
    assert fallback["status"] == "pending"

    malformed_body = json.dumps(
        {"id": "evt_malformed", "type": "checkout.session.completed", "data": {}},
        separators=(",", ":"),
    ).encode()
    malformed_sig = hmac.new(
        config["stripe"]["webhook_secret"].encode(),
        stamp.encode() + b"." + malformed_body,
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.verify_event(
            "stripe", malformed_body, {"Stripe-Signature": f"t={stamp},v1={malformed_sig}"}
        )
    with pytest.raises(GatewayError, match="gateway_invalid_signature"):
        registry.verify_event("stripe", body + b" ", {"Stripe-Signature": f"t={stamp},v1={sig}"})
    live_body = body.replace(b'"livemode":false', b'"livemode":true', 1)
    live_sig = hmac.new(
        config["stripe"]["webhook_secret"].encode(),
        stamp.encode() + b"." + live_body,
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(GatewayError, match="gateway_mode_mismatch"):
        registry.verify_event("stripe", live_body, {"Stripe-Signature": f"t={stamp},v1={live_sig}"})
    with pytest.raises(GatewayError, match="gateway_invalid_signature"):
        registry.verify_event("stripe", body, {})


def test_live_configuration_and_unconfigured_provider_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="live gateways are disabled"):
        GatewayRegistry({"stripe": {"enabled": True, "mode": "live"}}, tmp_path)
    registry = GatewayRegistry(data_dir=tmp_path)
    assert registry.status("stripe") == {
        "gateway": "stripe",
        "enabled": False,
        "mode": "test",
        "ready": False,
        "reason": "disabled",
    }
    with pytest.raises(GatewayError, match="gateway_not_ready"):
        registry.create_session("stripe", {"order_id": "ord", "amount": 100, "currency": "VND"})
    with pytest.raises(ValueError, match="data_dir is required"):
        GatewayRegistry()
    incomplete = GatewayRegistry(
        {"stripe": {"enabled": True, "mode": "test"}},
        tmp_path / "incomplete",
        lambda **_: {},
    )
    assert incomplete.status("stripe")["reason"] == "test_configuration_incomplete"
    full_config_no_transport = GatewayRegistry(
        {
            "stripe": {
                "enabled": True,
                "mode": "test",
                "test_secret_key": "sk_test_" + "x" * 20,
                "webhook_secret": "whsec_" + "y" * 20,
            }
        },
        tmp_path / "no-transport",
    )
    assert full_config_no_transport.status("stripe")["reason"] == "mock_transport_required"


def test_momo_capturewallet_mock_and_signed_ipn_normalize_to_test_event(tmp_path):
    calls = []

    def mock_transport(**request):
        calls.append(request)
        return {
            "requestId": request["payload"]["requestId"],
            "payUrl": "https://test-payment.momo.vn/pay",
        }

    config = {
        "momo": {
            "enabled": True,
            "mode": "test",
            "partner_code": "partner-test",
            "access_key": "access-test",
            "secret_key": "secret-test-only",
        }
    }
    registry = GatewayRegistry(config, tmp_path, mock_transport, clock=lambda: NOW)
    checkout = registry.create_session(
        "momo", {"order_id": "ord_momo", "amount": 99000, "currency": "VND"}
    )
    assert checkout["mode"] == "test"
    assert calls[0]["endpoint"] == "https://test-payment.momo.vn/v2/gateway/api/create"
    assert calls[0]["payload"]["requestType"] == "captureWallet"
    assert checkout["checkout_id"] == calls[0]["payload"]["requestId"]

    callback = {
        "partnerCode": "partner-test",
        "orderId": "ord_momo",
        "requestId": checkout["checkout_id"],
        "amount": 99000,
        "orderInfo": "AI Assessor sandbox plan",
        "orderType": "momo_wallet",
        "transId": 123456,
        "message": "Successful",
        "payType": "webApp",
        "responseTime": int(NOW.timestamp() * 1000),
        "resultCode": 0,
        "extraData": "",
    }
    callback["signature"] = _momo_signature(
        callback, "secret-test-only", response=True, access_key="access-test"
    )
    result = registry.verify_event("momo", callback)
    assert (result["order_id"], result["checkout_id"], result["status"], result["mode"]) == (
        "ord_momo",
        checkout["checkout_id"],
        "paid",
        "test",
    )
    callback["amount"] = 99001
    with pytest.raises(GatewayError, match="gateway_invalid_signature"):
        registry.verify_event("momo", callback)
    callback["amount"] = 99000
    callback["resultCode"] = 9000
    callback["signature"] = _momo_signature(
        callback, "secret-test-only", response=True, access_key="access-test"
    )
    assert registry.verify_event("momo", callback)["status"] == "pending"


def test_vnpay_210_mock_and_signed_callback_verify_tmn_amount_and_time(tmp_path):
    calls = []

    def mock_transport(**request):
        calls.append(request)
        return {
            "vnp_TxnRef": request["payload"]["vnp_TxnRef"],
            "redirect_url": "https://sandbox.vnpayment.vn/payment2?fixture=1",
        }

    config = {
        "vnpay": {
            "enabled": True,
            "mode": "test",
            "terminal_code": "TESTTMN1",
            "hash_secret": "fixture-hash-secret",
        }
    }
    registry = GatewayRegistry(config, tmp_path, mock_transport, clock=lambda: NOW)
    checkout = registry.create_session(
        "vnpay", {"order_id": "ord_vnpay", "amount": 99000, "currency": "VND"}
    )
    assert checkout["checkout_id"] == "ord_vnpay"
    assert calls[0]["endpoint"] == "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    assert calls[0]["payload"]["vnp_Version"] == "2.1.0"
    assert calls[0]["payload"]["vnp_CreateDate"] == "20261015110000"
    callback = {
        "vnp_TmnCode": "TESTTMN1",
        "vnp_TxnRef": "ord_vnpay",
        "vnp_TransactionNo": "1234",
        "vnp_Amount": "9900000",
        "vnp_CurrCode": "VND",
        "vnp_TransactionStatus": "00",
        "vnp_PayDate": "20261015110000",
    }
    callback["vnp_SecureHash"] = _vnpay_signature(callback, "fixture-hash-secret")
    result = registry.verify_event("vnpay", callback)
    assert (result["amount"], result["currency"], result["status"], result["mode"]) == (
        99000,
        "VND",
        "paid",
        "test",
    )
    callback["vnp_Amount"] = "1"
    callback["vnp_SecureHash"] = _vnpay_signature(callback, "fixture-hash-secret")
    malformed_amount = dict(callback, vnp_Amount="9900001")
    malformed_amount["vnp_SecureHash"] = _vnpay_signature(malformed_amount, "fixture-hash-secret")
    with pytest.raises(GatewayError, match="gateway_invalid_amount"):
        registry.verify_event("vnpay", malformed_amount)

    contradictory = dict(callback, vnp_Amount="9900000", vnp_ResponseCode="24")
    contradictory["vnp_SecureHash"] = _vnpay_signature(contradictory, "fixture-hash-secret")
    assert registry.verify_event("vnpay", contradictory)["status"] == "failed"
    wrong_currency = dict(callback, vnp_Amount="9900000", vnp_CurrCode="USD")
    wrong_currency["vnp_SecureHash"] = _vnpay_signature(wrong_currency, "fixture-hash-secret")
    with pytest.raises(GatewayError, match="gateway_currency_mismatch"):
        registry.verify_event("vnpay", wrong_currency)


def test_status_never_returns_configured_provider_credentials(tmp_path):
    secret = "sk_test_" + "secret-value-123456"
    registry = GatewayRegistry(
        {
            "stripe": {
                "enabled": True,
                "mode": "test",
                "test_secret_key": secret,
                "webhook_secret": "whsec_" + "x" * 20,
            }
        },
        tmp_path,
        lambda **_: {"id": "cs_test_1", "url": "https://checkout.stripe.com/pay"},
    )
    status = registry.status()
    assert secret not in json.dumps(status)
    assert "endpoint" not in json.dumps(status)
    assert registry.get("stripe") is registry


@pytest.mark.parametrize(
    "config",
    [
        {"unknown": {"enabled": True}},
        {"stripe": {"enabled": True, "mode": "test", "endpoint": "https://example.invalid"}},
        {"stripe": {"enabled": "yes", "mode": "test"}},
        "not-a-mapping",
    ],
)
def test_registry_rejects_unknown_or_unbounded_configuration(tmp_path, config):
    with pytest.raises(ValueError):
        GatewayRegistry(config, tmp_path)


def test_registry_rejects_unknown_names_duplicate_headers_and_invalid_payloads(tmp_path):
    registry = GatewayRegistry(data_dir=tmp_path, clock=lambda: NOW)
    with pytest.raises(GatewayError, match="gateway_unknown"):
        registry.status("paypal")
    with pytest.raises(GatewayError, match="gateway_unknown"):
        registry.get("paypal")
    with pytest.raises(GatewayError, match="gateway_invalid_headers"):
        registry.verify_event("sandbox", b"{}", {"x" * 101: "v"})
    with pytest.raises(GatewayError, match="gateway_invalid_headers"):
        registry.verify_event("sandbox", b"{}", {"X-Test": 1})
    with pytest.raises(GatewayError, match="gateway_duplicate_header"):
        registry.verify_event("sandbox", b"{}", {"X-Test": "a", "x-test": "b"})
    with pytest.raises(GatewayError, match="gateway_payload_too_large"):
        registry.verify_event("sandbox", b"x" * 70_000)
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.verify_event("sandbox", b"[]")
    with pytest.raises(GatewayError, match="gateway_invalid_channel"):
        registry.verify_event("sandbox", b"{}", channel="poll")
    bad_status_raw, bad_status_headers = registry.sign_sandbox_event(
        {
            "event_id": "evt_bad_status",
            "order_id": "ord_1",
            "checkout_id": "cs_1",
            "amount": 1,
            "currency": "VND",
            "status": "settled",
        }
    )
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.verify_event("sandbox", bad_status_raw, bad_status_headers)
    wrong_mode = {
        "event_id": "evt_wrong_mode",
        "order_id": "ord_1",
        "checkout_id": "cs_1",
        "amount": 1,
        "currency": "VND",
        "status": "paid",
        "mode": "live",
    }
    wrong_mode_raw, wrong_mode_headers = registry.sign_sandbox_event(wrong_mode)
    with pytest.raises(GatewayError, match="gateway_mode_mismatch"):
        registry.verify_event("sandbox", wrong_mode_raw, wrong_mode_headers)
    with pytest.raises(GatewayError, match="gateway_invalid_amount"):
        registry.create_session("sandbox", {"order_id": "x", "amount": True, "currency": "VND"})
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.create_session("sandbox", {"order_id": "", "amount": 1, "currency": "VND"})
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.create_session("sandbox", {"order_id": "ord\n1", "amount": 1, "currency": "VND"})


def test_bounded_canonicalization_json_headers_and_timestamps_reject_bad_inputs():
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _canonical({"bad": object()})
    with pytest.raises(GatewayError, match="gateway_payload_too_large"):
        _canonical({"large": "x" * 70_000})
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _strict_json(b"{bad json")
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _strict_json(b'{"amount": NaN}')
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _strict_json(b"\xff")
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _strict_json("\ud800")
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        _strict_json(42)
    with pytest.raises(GatewayError, match="gateway_invalid_headers"):
        _headers({"x": "a\nb"})
    with pytest.raises(GatewayError, match="gateway_invalid_headers"):
        _headers({"x": "a" * 1025})
    assert _headers(None) == {}
    for stamp in (True, -1, 1.2, "2026-10-15T04:00:00"):
        with pytest.raises(GatewayError, match="gateway_expired_event"):
            _timestamp(stamp, millis=isinstance(stamp, int), clock=lambda: NOW)
    for stamp, millis in ((10**100, False), (10**100, True)):
        with pytest.raises(GatewayError, match="gateway_expired_event"):
            _timestamp(stamp, millis=millis, clock=lambda: NOW)


def test_vnpay_parser_refuses_unicode_duplicate_expired_and_missing_status(tmp_path):
    config = {
        "vnpay": {
            "enabled": True,
            "mode": "test",
            "terminal_code": "TESTTMN1",
            "hash_secret": "fixture-hash-secret",
        }
    }
    registry = GatewayRegistry(config, tmp_path, lambda **_: {}, clock=lambda: NOW)
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.verify_event("vnpay", "vnp_TmnCode=é")
    with pytest.raises(GatewayError, match="gateway_duplicate_field"):
        registry.verify_event("vnpay", b"vnp_TmnCode=TESTTMN1&vnp_TmnCode=OTHER")

    missing_status = {
        "vnp_TmnCode": "TESTTMN1",
        "vnp_TxnRef": "ord_missing_status",
        "vnp_Amount": "9900000",
        "vnp_CurrCode": "VND",
        "vnp_PayDate": "20261015110000",
    }
    missing_status["vnp_SecureHash"] = _vnpay_signature(missing_status, "fixture-hash-secret")
    with pytest.raises(GatewayError, match="gateway_invalid_payload"):
        registry.verify_event("vnpay", missing_status)

    invalid_time = dict(missing_status, vnp_TransactionStatus="00", vnp_PayDate="not-a-date")
    invalid_time["vnp_SecureHash"] = _vnpay_signature(invalid_time, "fixture-hash-secret")
    with pytest.raises(GatewayError, match="gateway_expired_event"):
        registry.verify_event("vnpay", invalid_time)


def test_mock_transport_object_path_and_unusable_provider_response_fails_safely(tmp_path):
    class MockResponse:
        def json(self):
            return {"id": "cs_test", "url": "https://checkout.stripe.com/pay"}

    class MockTransport:
        def __init__(self, response):
            self.calls = []
            self.response = response

        def post(self, endpoint, **kwargs):
            self.calls.append((endpoint, kwargs))
            return self.response

    cfg = {
        "stripe": {
            "enabled": True,
            "mode": "test",
            "test_secret_key": "sk_test_" + "k" * 24,
            "webhook_secret": "whsec_" + "h" * 24,
        }
    }
    transport = MockTransport(MockResponse())
    registry = GatewayRegistry(cfg, tmp_path, transport, clock=lambda: NOW)
    result = registry.create_session(
        "stripe", {"order_id": "ord_object", "amount": 1200, "currency": "VND"}
    )
    assert result["checkout_id"] == "cs_test"
    assert transport.calls[0][1]["timeout"] == 5
    assert transport.calls[0][1]["allow_redirects"] is False

    broken = GatewayRegistry(cfg, tmp_path / "second", lambda **_: [], clock=lambda: NOW)
    with pytest.raises(GatewayError, match="gateway_unavailable"):
        broken.create_session(
            "stripe", {"order_id": "ord_broken", "amount": 1200, "currency": "VND"}
        )
    secret_bearing = GatewayRegistry(
        cfg,
        tmp_path / "third",
        lambda **_: (_ for _ in ()).throw(RuntimeError("sk_test_secret-do-not-leak")),
        clock=lambda: NOW,
    )
    with pytest.raises(GatewayError, match="gateway_unavailable") as caught:
        secret_bearing.create_session(
            "stripe", {"order_id": "ord_error", "amount": 1200, "currency": "VND"}
        )
    assert caught.value.__cause__ is None
    assert "secret-do-not-leak" not in str(caught.value)

    redirect_attack = GatewayRegistry(
        cfg,
        tmp_path / "fourth",
        lambda **_: {"id": "cs_test", "url": "https://evil.example/collect"},
        clock=lambda: NOW,
    )
    with pytest.raises(GatewayError, match="gateway_unavailable"):
        redirect_attack.create_session(
            "stripe", {"order_id": "ord_redirect", "amount": 1200, "currency": "VND"}
        )


def test_momo_and_vnpay_invalid_times_and_unknown_signature_fields_reject(tmp_path):
    momo_config = {
        "momo": {
            "enabled": True,
            "mode": "test",
            "partner_code": "partner-test",
            "access_key": "access-test",
            "secret_key": "secret-test-only",
        }
    }
    momo = GatewayRegistry(
        momo_config,
        tmp_path / "momo",
        lambda **request: {
            "requestId": request["payload"]["requestId"],
            "payUrl": "https://test-payment.momo.vn/pay",
        },
        clock=lambda: NOW,
    )
    callback = {
        "partnerCode": "partner-test",
        "orderId": "ord_momo_time",
        "requestId": "req_momo_time",
        "amount": 1,
        "orderInfo": "test",
        "orderType": "momo_wallet",
        "transId": 1,
        "message": "ok",
        "payType": "webApp",
        "responseTime": int((NOW - timedelta(minutes=6)).timestamp() * 1000),
        "resultCode": 1,
        "extraData": "",
    }
    callback["signature"] = _momo_signature(
        callback, "secret-test-only", response=True, access_key="access-test"
    )
    with pytest.raises(GatewayError, match="gateway_expired_event"):
        momo.verify_event("momo", callback)

    vnp_config = {
        "vnpay": {
            "enabled": True,
            "mode": "test",
            "terminal_code": "TESTTMN1",
            "hash_secret": "fixture-hash-secret",
        }
    }
    vnp = GatewayRegistry(vnp_config, tmp_path / "vnp", lambda **_: {}, clock=lambda: NOW)
    params = {
        "vnp_TmnCode": "WRONGTMN",
        "vnp_TxnRef": "ord_vnp_time",
        "vnp_TransactionNo": "1234",
        "vnp_Amount": "100",
        "vnp_CurrCode": "VND",
        "vnp_TransactionStatus": "00",
        "vnp_PayDate": "20261015110000",
    }
    params["vnp_SecureHash"] = _vnpay_signature(params, "fixture-hash-secret")
    with pytest.raises(GatewayError, match="gateway_mode_mismatch"):
        vnp.verify_event("vnpay", params)
