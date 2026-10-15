from __future__ import annotations

from datetime import UTC, datetime

import pytest

from aicefr.auth.service import AuthService
from aicefr.billing.errors import BillingError
from aicefr.billing.gateways import GatewayRegistry
from aicefr.billing.licenses import LicenseService
from aicefr.billing.secrets import KeyRing
from aicefr.billing.service import BillingService
from aicefr.contracts import ActorRole
from aicefr.storage.billing import BillingRepository
from aicefr.storage.sqlite import SQLiteStore

NOW = datetime(2026, 10, 15, 4, 0, tzinfo=UTC)


@pytest.fixture
def billing_env(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    repository = BillingRepository(store)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "safe test password")
    token = auth.login("fixture-admin", "safe test password")
    keyring = KeyRing(tmp_path / "data")
    gateways = GatewayRegistry(data_dir=tmp_path / "data", keyring=keyring, clock=lambda: NOW)
    licenses = LicenseService(auth, store, keyring, clock=lambda: NOW)
    service = BillingService(auth, repository, gateways, licenses, clock=lambda: NOW)
    try:
        yield store, token, gateways, service
    finally:
        store.close()


def test_signed_amount_tampering_is_rejected_then_valid_event_settles_once(billing_env):
    store, token, gateways, service = billing_env
    quote = service.quote(token, "STANDARD", 1, "quote-key-1")
    order = service.create_order(token, quote.quote_id, "sandbox", "order-key-1")
    assert order.checkout_ref

    forged_amount = {
        "event_id": "evt_tampered",
        "order_id": order.order_id,
        "checkout_id": order.checkout_ref,
        "amount": order.amount_minor + 1,
        "currency": order.currency,
        "status": "paid",
        "mode": "sandbox",
        "gateway": "sandbox",
    }
    forged_raw, forged_headers = gateways.sign_sandbox_event(forged_amount)
    with pytest.raises(BillingError, match="payment_binding_mismatch"):
        service.handle_event("sandbox", forged_raw, forged_headers)
    assert service.list_orders(token)[0].state == "PENDING"
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0

    valid = dict(forged_amount, event_id="evt_valid", amount=order.amount_minor)
    valid_raw, valid_headers = gateways.sign_sandbox_event(valid)
    paid = service.handle_event("sandbox", valid_raw, valid_headers)
    assert paid.state == "PAID"
    assert service.handle_event("sandbox", valid_raw, valid_headers).state == "PAID"
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 1


def test_invalid_gateway_signature_never_mutates_billing_state(billing_env):
    store, token, gateways, service = billing_env
    quote = service.quote(token, "STANDARD", 1, "quote-key-2")
    order = service.create_order(token, quote.quote_id, "sandbox", "order-key-2")
    payload, headers = gateways.sign_sandbox_event(
        {
            "event_id": "evt_invalid_sig",
            "order_id": order.order_id,
            "checkout_id": order.checkout_ref,
            "amount": order.amount_minor,
            "currency": order.currency,
            "status": "paid",
            "mode": "sandbox",
            "gateway": "sandbox",
        }
    )
    with pytest.raises(BillingError, match="gateway_invalid_signature"):
        service.handle_event("sandbox", payload, {"X-Sandbox-Signature": "0" * 64})
    assert service.list_orders(token)[0].state == "PENDING"
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0
