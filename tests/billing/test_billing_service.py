import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.auth.service import AuthService
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS
from aicefr.billing.service import BillingService
from aicefr.contracts import ActorRole
from aicefr.storage.billing import BillingRepository
from aicefr.storage.sqlite import SQLiteStore

NOW = datetime(2026, 10, 15, 8, tzinfo=UTC)


class FakeGateway:
    def status(self, gateway=None):
        return {"enabled": True, "ready": True, "mode": "test", "label": "sandbox"}

    def get(self, gateway):
        return self

    def create_session(self, gateway, order):
        return {
            "gateway": gateway,
            "mode": order["mode"],
            "checkout_id": f"checkout-{order['order_id']}",
            "redirect_url": None,
        }

    def sandbox_event(self, *, order, outcome, idempotency_key):
        return {
            "event_id": hashlib.sha256(idempotency_key.encode()).hexdigest(),
            "order_id": order.order_id,
            "checkout_id": order.checkout_ref,
            "amount": order.amount_minor,
            "currency": order.currency,
            "status": outcome,
            "mode": order.mode,
            "gateway": order.gateway,
            "payload_hash": hashlib.sha256((order.order_id + outcome).encode()).hexdigest(),
            "signature_valid": True,
            "occurred_at": NOW,
        }


class FakeLicenseService:
    def apply_entitlement(self, db, **values):
        plan = PLANS[values["plan_code"]]
        effective_at = values["effective_at"]
        expires_at = values["expires_at"]
        grace_until = values["grace_until"]
        db.execute(
            "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
            "student_limit,warning_quota,effective_at,expires_at,grace_until,source_order,"
            "created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                uuid.uuid4().hex,
                values["account_id"],
                plan.code,
                json.dumps(sorted(plan.features), separators=(",", ":")),
                plan.student_limit,
                plan.warning_quota,
                effective_at.astimezone(UTC).isoformat(),
                expires_at.astimezone(UTC).isoformat() if expires_at else None,
                grace_until.astimezone(UTC).isoformat() if grace_until else None,
                values["source_order"],
                effective_at.astimezone(UTC).isoformat(),
            ),
        )


def _new_env(tmp_path, *, gateway=None, current_time=None, config=None):
    current_time = current_time or [NOW]
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: current_time[0])
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    repository = BillingRepository(store)
    service = BillingService(
        auth,
        repository,
        gateway or FakeGateway(),
        FakeLicenseService(),
        config=config,
        clock=lambda: current_time[0],
    )
    return store, auth, admin, repository, service, current_time


def test_admin_flow_is_sandbox_only_and_zero_cost_trial_activates_once(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth,
        BillingRepository(store),
        FakeGateway(),
        FakeLicenseService(),
        config={"live": True},
        clock=lambda: NOW,
    )
    overview = service.overview(admin)
    assert overview["sandbox"] is True
    assert overview["entitlement"]["plan_code"] == "FREE"
    with pytest.raises(BillingError, match="live_payment_disabled"):
        quote = service.quote(admin, "STANDARD", 1, "quote-key-001")
        service.create_order(admin, quote.quote_id, "fixture", "order-key-001")

    service = BillingService(
        auth, service._repository, FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    quote = service.quote(admin, "TRIAL", 1, "trial-quote-001")
    order = service.create_order(admin, quote.quote_id, "internal", "trial-order-001")
    replay = service.create_order(admin, quote.quote_id, "internal", "trial-order-001")
    assert replay.order_id == order.order_id
    assert order.state == "PAID"
    assert service._repository.current_entitlement(NOW).plan_code == "TRIAL"
    assert service.quote(admin, "TRIAL", 1, "trial-quote-001").quote_id == quote.quote_id
    with pytest.raises(BillingError, match="trial_already_used"):
        service.quote(admin, "TRIAL", 1, "trial-quote-002")
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        service.quote(admin, "STANDARD", 1, "trial-quote-001")
    assert quote.effective_at == NOW
    assert quote.ends_at == NOW + timedelta(days=30)
    assert quote.change_kind == "trial"


def test_quote_freezes_safe_calendar_schedule_and_change_kind(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    repository = BillingRepository(store)
    service = BillingService(
        auth, repository, FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )

    initial = service.quote(admin, "STANDARD", 1, "schedule-initial")
    assert initial.effective_at == NOW
    assert initial.ends_at == datetime(2026, 11, 15, 8, tzinfo=UTC)
    assert initial.change_kind == "initial"
    order = service.create_order(admin, initial.quote_id, "fixture", "schedule-order")
    service.settle_sandbox(admin, order.order_id, "paid", "schedule-settlement")
    assert service.overview(admin)["entitlement"]["status"] == "ACTIVE"

    renewal = service.quote(admin, "STANDARD", 1, "schedule-renewal")
    assert renewal.effective_at == initial.ends_at
    assert renewal.ends_at == datetime(2026, 12, 15, 8, tzinfo=UTC)
    assert renewal.change_kind == "renewal"
    replay = service.quote(admin, "STANDARD", 1, "schedule-renewal")
    assert replay.effective_at == renewal.effective_at
    assert replay.ends_at == renewal.ends_at
    assert replay.change_kind == renewal.change_kind
    assert "entitlement_snapshot" in renewal.context_json
    assert "effective_at" in renewal.context_json
    store.close()


def test_billing_requires_license_installation_port(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    with pytest.raises(BillingError, match="license_installation_unavailable"):
        BillingService(auth, BillingRepository(store), FakeGateway(), object(), clock=lambda: NOW)
    store.close()


def test_trial_term_invalid_key_and_missing_quote_are_refused(tmp_path):
    store, _, admin, _, service, _ = _new_env(tmp_path)
    with pytest.raises(BillingError, match="invalid_billing_term"):
        service.quote(admin, "TRIAL", 12, "trial-term-key")
    with pytest.raises(BillingError, match="invalid_idempotency_key"):
        service.quote(admin, "STANDARD", 1, "bad key")
    with pytest.raises(BillingError, match="quote_unavailable"):
        service.create_order(admin, "missing-quote", "fixture", "missing-quote-order")
    store.close()


def test_order_idempotency_key_is_bound_to_quote_and_gateway(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth, BillingRepository(store), FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    quote = service.quote(admin, "STANDARD", 1, "quote-key-001")
    first = service.create_order(admin, quote.quote_id, "fixture", "order-key-001")
    same = service.create_order(admin, quote.quote_id, "fixture", "order-key-001")
    assert same.order_id == first.order_id
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        service.create_order(admin, quote.quote_id, "other", "order-key-001")
    store.close()


def test_nested_live_configuration_is_hard_disabled(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    repository = BillingRepository(store)
    quote = BillingService(
        auth, repository, FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    ).quote(admin, "STANDARD", 1, "quote-live-001")
    service = BillingService(
        auth,
        repository,
        FakeGateway(),
        FakeLicenseService(),
        config={"gateways": {"stripe": {"mode": "live"}}},
        clock=lambda: NOW,
    )
    with pytest.raises(BillingError, match="live_payment_disabled"):
        service.create_order(admin, quote.quote_id, "fixture", "order-live-001")
    store.close()


def test_quote_cannot_be_used_after_entitlement_changes(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth, BillingRepository(store), FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    stale_quote = service.quote(admin, "STANDARD", 1, "quote-key-stale")
    trial_quote = service.quote(admin, "TRIAL", 1, "trial-key-stale")
    service.create_order(admin, trial_quote.quote_id, "internal", "trial-order-stale")
    with pytest.raises(BillingError, match="quote_stale"):
        service.create_order(admin, stale_quote.quote_id, "fixture", "standard-order-stale")
    store.close()


def test_create_order_rechecks_entitlement_inside_insert_transaction(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    repository = BillingRepository(store)
    quote = BillingService(
        auth, repository, FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    ).quote(admin, "STANDARD", 1, "quote-race-001")

    class RacingGateway(FakeGateway):
        changed = False

        def status(self, gateway=None):
            if not self.changed:
                self.changed = True
                store.connection.execute(
                    "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
                    "student_limit,warning_quota,effective_at,expires_at,grace_until,"
                    "source_order,created_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        "ent-race",
                        "fixture-admin",
                        "TRIAL",
                        '["learning","practice"]',
                        30,
                        100,
                        NOW.isoformat(),
                        (NOW + timedelta(days=30)).isoformat(),
                        None,
                        None,
                        NOW.isoformat(),
                    ),
                )
            return super().status(gateway)

    service = BillingService(
        auth, repository, RacingGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    with pytest.raises(BillingError, match="quote_stale"):
        service.create_order(admin, quote.quote_id, "fixture", "order-race-001")
    assert repository.list_orders() == ()
    store.close()


def test_pending_checkout_retry_rechecks_quote_expiry_and_entitlement(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")

    class FailingCheckoutGateway(FakeGateway):
        def create_session(self, gateway, order):
            raise BillingError("gateway_unavailable", 503)

    repository = BillingRepository(store)
    service = BillingService(
        auth, repository, FailingCheckoutGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    quote = service.quote(admin, "STANDARD", 1, "quote-retry-stale")
    with pytest.raises(BillingError, match="gateway_unavailable"):
        service.create_order(admin, quote.quote_id, "fixture", "order-retry-stale")
    assert len(repository.list_orders()) == 1

    store.connection.execute(
        "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
        "student_limit,warning_quota,effective_at,expires_at,grace_until,source_order,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ent-retry-stale",
            "fixture-admin",
            "TRIAL",
            '["learning","practice"]',
            30,
            100,
            NOW.isoformat(),
            (NOW + timedelta(days=30)).isoformat(),
            None,
            None,
            NOW.isoformat(),
        ),
    )
    with pytest.raises(BillingError, match="quote_stale"):
        service.create_order(admin, quote.quote_id, "fixture", "order-retry-stale")
    store.close()


def test_pending_checkout_cannot_be_reopened_after_quote_expiry(tmp_path):
    clock = [NOW]

    class FailingCheckoutGateway(FakeGateway):
        def create_session(self, gateway, order):
            raise BillingError("gateway_unavailable", 503)

    store, _, admin, repository, service, _ = _new_env(
        tmp_path, gateway=FailingCheckoutGateway(), current_time=clock
    )
    quote = service.quote(admin, "STANDARD", 1, "pending-expiry-quote")
    with pytest.raises(BillingError, match="gateway_unavailable"):
        service.create_order(admin, quote.quote_id, "fixture", "pending-expiry-order")
    clock[0] += timedelta(minutes=15)
    with pytest.raises(BillingError, match="quote_expired"):
        service.create_order(admin, quote.quote_id, "fixture", "pending-expiry-order")
    assert len(repository.list_orders()) == 1
    store.close()


def test_pending_checkout_retry_after_transient_failure_reuses_the_order(tmp_path):
    class RetryableGateway(FakeGateway):
        attempts = 0

        def create_session(self, gateway, order):
            self.attempts += 1
            if self.attempts == 1:
                raise BillingError("gateway_unavailable", 503)
            return super().create_session(gateway, order)

    gateway = RetryableGateway()
    store, _, admin, repository, service, _ = _new_env(tmp_path, gateway=gateway)
    quote = service.quote(admin, "STANDARD", 1, "retry-success-quote")
    with pytest.raises(BillingError, match="gateway_unavailable"):
        service.create_order(admin, quote.quote_id, "fixture", "retry-success-order")
    opened = service.create_order(admin, quote.quote_id, "fixture", "retry-success-order")
    assert opened.checkout_ref == f"checkout-{opened.order_id}"
    assert len(repository.list_orders()) == 1
    assert gateway.attempts == 2
    store.close()


@pytest.mark.parametrize(
    "ready,mode,result,code,expected_orders",
    [
        (False, "test", None, "gateway_unavailable", 0),
        (True, "live", None, "live_payment_disabled", 0),
        (True, "test", None, "gateway_unavailable", 1),
        (
            True,
            "test",
            {"gateway": "wrong", "mode": "test", "checkout_id": "x"},
            "gateway_binding_mismatch",
            1,
        ),
        (
            True,
            "test",
            {"gateway": "fixture", "mode": "sandbox", "checkout_id": "x"},
            "gateway_binding_mismatch",
            1,
        ),
        (True, "test", {"gateway": "fixture", "mode": "test"}, "gateway_unavailable", 1),
    ],
)
def test_checkout_refuses_unready_live_or_malformed_gateway_results(
    tmp_path, ready, mode, result, code, expected_orders
):
    class ConfiguredGateway(FakeGateway):
        def status(self, gateway=None):
            return {"enabled": True, "ready": ready, "mode": mode}

        def create_session(self, gateway, order):
            return result

    store, _, admin, repository, service, _ = _new_env(tmp_path, gateway=ConfiguredGateway())
    quote = service.quote(admin, "STANDARD", 1, "gateway-quote-001")
    with pytest.raises(BillingError, match=code):
        service.create_order(admin, quote.quote_id, "fixture", "gateway-order-001")
    assert len(repository.list_orders()) == expected_orders
    if expected_orders:
        assert repository.list_orders()[0].checkout_ref is None
    store.close()


def test_expired_quote_is_rejected_and_corrupt_quote_key_fails_closed(tmp_path):
    store, _, admin, repository, service, clock = _new_env(tmp_path)
    expired = service.quote(admin, "STANDARD", 1, "expired-quote-001")
    clock[0] += timedelta(minutes=15)
    with pytest.raises(BillingError, match="quote_expired"):
        service.create_order(admin, expired.quote_id, "fixture", "expired-order-001")
    assert repository.list_orders() == ()

    key_hash = service._idempotency_digest("corrupt-quote-key")
    store.connection.execute(
        "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
        "VALUES(?,?,1,'v1','test',?)",
        (f"billing.quote.{key_hash}", "{bad-json", NOW.isoformat()),
    )
    with pytest.raises(BillingError, match="idempotency_record_invalid"):
        service.quote(admin, "STANDARD", 1, "corrupt-quote-key")

    valid_clock = [NOW]
    store2, _, admin2, repository2, service2, _ = _new_env(
        tmp_path / "corrupt-quote-context", current_time=valid_clock
    )
    quote = service2.quote(admin2, "STANDARD", 1, "corrupt-context-key")
    store2.connection.execute(
        "UPDATE billing_quotes SET inputs_json=? WHERE quote_id=?",
        ('{"months":1,"effective_at":"2026-10-15T08:00:00+00:00"}', quote.quote_id),
    )
    with pytest.raises(BillingError, match="quote_invalid"):
        service2.create_order(admin2, quote.quote_id, "fixture", "corrupt-context-order")
    assert repository2.list_orders() == ()
    store2.close()
    store.close()


def test_billing_rejects_non_admin_invalid_token_and_naive_clock(tmp_path):
    store, auth, admin, _, service, _ = _new_env(tmp_path)
    student = auth.bootstrap_fixture_account(
        "fixture-student", ActorRole.STUDENT, "student-password"
    )
    student_token = auth.login(student.actor_id, "student-password")
    with pytest.raises(BillingError, match="access_denied"):
        service.overview(student_token)
    with pytest.raises(BillingError, match="access_denied"):
        service.quote("not-a-valid-token", "STANDARD", 1, "invalid-auth-key")
    with pytest.raises(BillingError, match="timezone_required"):
        BillingService(
            auth,
            BillingRepository(store),
            FakeGateway(),
            FakeLicenseService(),
            clock=lambda: datetime(2026, 10, 15, 8),
        )
    store.close()


def test_missing_orders_and_unpaid_receipts_are_not_found(tmp_path):
    store, _, admin, _, service, _ = _new_env(tmp_path)
    with pytest.raises(BillingError, match="order_unavailable"):
        service.receipt(admin, "missing-order")
    quote = service.quote(admin, "STANDARD", 1, "unpaid-receipt-quote")
    order = service.create_order(admin, quote.quote_id, "fixture", "unpaid-receipt-order")
    with pytest.raises(BillingError, match="receipt_unavailable"):
        service.receipt(admin, order.order_id)
    with pytest.raises(BillingError, match="order_unavailable"):
        service.settle_sandbox(admin, "missing-order", "paid", "missing-settle-key")
    with pytest.raises(BillingError, match="order_unavailable"):
        service.cancel_order(admin, "missing-order", "missing-cancel-key")
    store.close()


def test_paid_receipt_is_readable_and_cancel_replay_is_idempotent(tmp_path):
    store, _, admin, _, service, _ = _new_env(tmp_path)
    paid_quote = service.quote(admin, "STANDARD", 1, "receipt-quote-key")
    paid_order = service.create_order(admin, paid_quote.quote_id, "fixture", "receipt-order-key")
    service.settle_sandbox(admin, paid_order.order_id, "paid", "receipt-settle-key")
    receipt = service.receipt(admin, paid_order.order_id)
    assert receipt.amount_minor == paid_quote.total_minor
    assert receipt.currency == "VND"

    cancel_quote = service.quote(admin, "ADVANCED", 1, "cancel-quote-key")
    cancel_order = service.create_order(admin, cancel_quote.quote_id, "fixture", "cancel-order-key")
    cancelled = service.cancel_order(admin, cancel_order.order_id, "cancel-idem-key")
    replay = service.cancel_order(admin, cancel_order.order_id, "cancel-idem-key")
    assert cancelled.state == replay.state == "CANCELLED"
    store.close()


def test_sandbox_settlement_and_webhook_reject_invalid_paths(tmp_path):
    store, _, admin, repository, service, _ = _new_env(tmp_path)
    quote = service.quote(admin, "STANDARD", 1, "invalid-settlement-quote")
    order = service.create_order(admin, quote.quote_id, "fixture", "invalid-settlement-order")
    with pytest.raises(BillingError, match="invalid_payment_outcome"):
        service.settle_sandbox(admin, order.order_id, "unknown", "invalid-outcome-key")

    service._gateways.get = lambda gateway: None
    with pytest.raises(BillingError, match="sandbox_settlement_unavailable"):
        service.settle_sandbox(admin, order.order_id, "paid", "unavailable-settle-key")

    store.connection.execute(
        "UPDATE billing_orders SET mode='live' WHERE order_id=?", (order.order_id,)
    )
    with pytest.raises(BillingError, match="live_payment_disabled"):
        service.settle_sandbox(admin, order.order_id, "paid", "live-settle-key")
    assert repository.receipt(order.order_id) is None
    with pytest.raises(BillingError, match="invalid_payment_channel"):
        service.handle_event("fixture", {}, channel="other")

    class BrokenVerifier:
        def verify_event(self, *args):
            raise RuntimeError("provider internal details")

    service._gateways = BrokenVerifier()
    with pytest.raises(BillingError, match="invalid_payment_event"):
        service.handle_event("fixture", {}, channel="webhook")
    service._gateways = type("EmptyVerifier", (), {"verify_event": lambda *args: None})()
    with pytest.raises(BillingError, match="invalid_payment_event"):
        service.handle_event("fixture", {}, channel="webhook")
    store.close()


def test_admin_session_revoked_during_gateway_preflight_cannot_create_order(tmp_path):
    class RevokingGateway(FakeGateway):
        store = None

        def status(self, gateway=None):
            self.store.connection.execute("DELETE FROM sessions")
            return super().status(gateway)

    gateway = RevokingGateway()
    store, _, admin, repository, service, _ = _new_env(tmp_path, gateway=gateway)
    gateway.store = store
    quote = service.quote(admin, "STANDARD", 1, "session-race-quote")
    with pytest.raises(BillingError, match="access_denied"):
        service.create_order(admin, quote.quote_id, "fixture", "session-race-order")
    assert repository.list_orders() == ()
    store.close()


def test_overview_reports_grace_then_free_after_grace(tmp_path):
    store, auth, _, _, service, clock = _new_env(tmp_path)
    admin = auth.login("fixture-admin", "valid-admin-password")
    paid_quote = service.quote(admin, "STANDARD", 1, "grace-quote-001")
    order = service.create_order(admin, paid_quote.quote_id, "fixture", "grace-order-001")
    service.settle_sandbox(admin, order.order_id, "paid", "grace-settle-001")
    expiry = paid_quote.ends_at

    clock[0] = expiry + timedelta(days=1)
    admin = auth.login("fixture-admin", "valid-admin-password")
    assert service.overview(admin)["entitlement"]["status"] == "GRACE"

    clock[0] = expiry + timedelta(days=15)
    admin = auth.login("fixture-admin", "valid-admin-password")
    assert service.overview(admin)["entitlement"]["status"] == "FREE"
    store.close()


def test_overview_uses_internal_status_when_gateway_registry_is_unavailable(tmp_path):
    class MissingStatusGateway(FakeGateway):
        def status(self, gateway=None):
            return None

    store, _, admin, _, service, _ = _new_env(tmp_path, gateway=MissingStatusGateway())
    overview = service.overview(admin)
    assert overview["gateways"] == {"internal": {"enabled": True, "mode": "sandbox"}}
    assert overview["entitlement"]["status"] == "FREE"
    store.close()


def test_upgrade_quote_credits_remaining_value_of_annual_purchase(tmp_path):
    clock = [NOW]
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: clock[0])
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth, BillingRepository(store), FakeGateway(), FakeLicenseService(), clock=lambda: clock[0]
    )
    annual = service.quote(admin, "STANDARD", 12, "annual-quote-001")
    order = service.create_order(admin, annual.quote_id, "fixture", "annual-order-001")
    service.settle_sandbox(admin, order.order_id, "paid", "annual-settle-001")

    clock[0] = NOW.replace(year=2027, month=4, day=15)
    admin = auth.login("fixture-admin", "valid-admin-password")
    upgrade = service.quote(admin, "ADVANCED", 12, "upgrade-quote-001")
    expires_at = NOW.replace(year=2027, month=10, day=15)
    expected_credit = (
        annual.total_minor
        * int((expires_at - clock[0]).total_seconds())
        // int((expires_at - NOW).total_seconds())
    )
    assert upgrade.credit_minor == expected_credit
    assert upgrade.total_minor == upgrade.subtotal_minor - upgrade.discount_minor - expected_credit
    store.close()


def test_sandbox_settlement_key_cannot_be_reused_for_changed_outcome(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth, BillingRepository(store), FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    quote = service.quote(admin, "STANDARD", 1, "quote-key-idem")
    order = service.create_order(admin, quote.quote_id, "fixture", "order-key-idem")
    assert (
        service.settle_sandbox(admin, order.order_id, "pending", "settle-key-001").state
        == "PENDING"
    )
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        service.settle_sandbox(admin, order.order_id, "paid", "settle-key-001")
    assert service._repository.receipt(order.order_id) is None
    assert service.settle_sandbox(admin, order.order_id, "paid", "settle-key-002").state == "PAID"
    store.close()


def test_overview_reports_monthly_quota_warning_without_blocking_learning(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "valid-student-password")
    admin = auth.login("fixture-admin", "valid-admin-password")
    service = BillingService(
        auth, BillingRepository(store), FakeGateway(), FakeLicenseService(), clock=lambda: NOW
    )
    for index in range(64):
        store.connection.execute(
            "INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,"
            "size_bytes,status,revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                f"resp-{index}",
                "fixture-student",
                "task-1",
                "v1",
                f"blob-{index}",
                "a" * 64,
                100,
                "DONE",
                1,
                NOW.isoformat(),
            ),
        )
    store.connection.execute(
        "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,student_limit,"
        "warning_quota,effective_at,expires_at,grace_until,source_order,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            "scheduled-1",
            "fixture-admin",
            "STANDARD",
            '["learning","practice"]',
            100,
            1000,
            "2027-01-01T00:00:00+00:00",
            "2027-02-01T00:00:00+00:00",
            "2027-02-15T00:00:00+00:00",
            None,
            NOW.isoformat(),
        ),
    )
    overview = service.overview(admin)
    assert overview["entitlement"]["status"] == "FREE"
    assert overview["usage"]["assessments_current_month"] == 64
    assert overview["usage"]["warnings"] == [
        {"code": "assessment_usage_80_percent", "used": 64, "quota": 80}
    ]
    assert overview["scheduled_entitlement"]["plan_code"] == "STANDARD"
    assert overview["usage"]["research_exclusion_enabled"] is False
    for index in range(64, 80):
        store.connection.execute(
            "INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,"
            "size_bytes,status,revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                f"resp-{index}",
                "fixture-student",
                "task-1",
                "v1",
                f"blob-{index}",
                "a" * 64,
                100,
                "DONE",
                1,
                NOW.isoformat(),
            ),
        )
    at_quota = service.overview(admin)
    assert at_quota["usage"]["warnings"] == [
        {"code": "assessment_usage_80_percent", "used": 80, "quota": 80},
        {"code": "assessment_usage_100_percent", "used": 80, "quota": 80},
    ]
    assert service.can_add_students(1) is True
    store.close()
