from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest

from aicefr.auth.service import AuthService
from aicefr.billing.contracts import Entitlement, Quote
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import PLANS
from aicefr.contracts import ActorRole
from aicefr.storage.billing import BillingRepository
from aicefr.storage.sqlite import SQLiteStore

NOW = datetime(2026, 10, 15, 8, tzinfo=UTC)


def _setup(tmp_path):
    store = SQLiteStore(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "valid-admin-password")
    token = auth.login("fixture-admin", "valid-admin-password")
    repo = BillingRepository(store)
    quote = Quote(
        "quote-1",
        "fixture-admin",
        "STANDARD",
        1,
        99_000,
        0,
        0,
        99_000,
        "VND",
        NOW,
        NOW + timedelta(minutes=15),
        '{"effective_at":"2026-10-15T08:00:00+00:00"}',
    )
    repo.save_quote(quote)
    order = repo.create_order(
        order_id="order-1",
        quote=quote,
        gateway="internal",
        mode="sandbox",
        idempotency_hash="order-idem-hash",
        now=NOW,
        token=token,
    )
    order = repo.set_checkout(
        order.order_id, "checkout-1", NOW, token=token, actor_id="fixture-admin"
    )
    event = {
        "event_id": "event-1",
        "order_id": "order-1",
        "checkout_id": "checkout-1",
        "amount": 99_000,
        "currency": "VND",
        "status": "paid",
        "mode": "sandbox",
        "gateway": "internal",
        "payload_hash": "a" * 64,
        "signature_valid": True,
        "occurred_at": NOW,
    }
    return store, repo, token, order, event


def _apply(db, **values):
    plan = PLANS[values["plan_code"]]
    db.execute(
        "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,student_limit,"
        "warning_quota,effective_at,expires_at,grace_until,source_order,created_at) "
        "VALUES('ent-1',?,?,?,?,?,?,?,?,?,?)",
        (
            values["account_id"],
            plan.code,
            '["learning"]',
            plan.student_limit,
            plan.warning_quota,
            values["effective_at"].isoformat(),
            values["expires_at"].isoformat(),
            values["grace_until"].isoformat(),
            values["source_order"],
            NOW.isoformat(),
        ),
    )


def test_settlement_is_atomic_and_duplicate_event_never_duplicates_receipt(tmp_path):
    store, repo, token, _, event = _setup(tmp_path)

    def fail_after_entitlement(db, **kwargs):
        _apply(db, **kwargs)
        raise RuntimeError("injected failure")

    with pytest.raises(RuntimeError, match="injected failure"):
        repo.settle(
            event,
            now=NOW,
            apply_entitlement=fail_after_entitlement,
            organization_id="local-demo",
            admin_token=token,
            admin_actor_id="fixture-admin",
        )
    assert repo.get_order("order-1").state == "PENDING"
    assert repo.receipt("order-1") is None
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0

    paid = repo.settle(
        event,
        now=NOW,
        apply_entitlement=_apply,
        organization_id="local-demo",
        admin_token=token,
        admin_actor_id="fixture-admin",
    )
    replay = repo.settle(
        event,
        now=NOW + timedelta(seconds=1),
        apply_entitlement=_apply,
        organization_id="local-demo",
        admin_token=token,
        admin_actor_id="fixture-admin",
    )
    assert paid.state == replay.state == "PAID"
    assert repo.receipt("order-1").amount_minor == 99_000
    assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
    store.close()


def test_tampered_amount_and_revoked_admin_session_are_rejected(tmp_path):
    store, repo, token, _, event = _setup(tmp_path)
    forged = {**event, "amount": 1}
    with pytest.raises(BillingError, match="payment_binding_mismatch"):
        repo.settle(forged, now=NOW, apply_entitlement=_apply, organization_id="local-demo")
    store.connection.execute("DELETE FROM sessions")
    with pytest.raises(BillingError, match="access_denied"):
        repo.settle(
            event,
            now=NOW,
            apply_entitlement=_apply,
            organization_id="local-demo",
            admin_token=token,
            admin_actor_id="fixture-admin",
        )
    assert repo.get_order("order-1").state == "PENDING"
    store.close()


def test_annual_paid_value_uses_actual_remaining_period(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2027, 1, 1, tzinfo=UTC)
    store.connection.execute(
        "UPDATE billing_orders SET state='PAID',amount_minor=1009800 WHERE order_id='order-1'"
    )
    entitlement = Entitlement(
        "STANDARD",
        frozenset({"learning"}),
        100,
        1000,
        start,
        end,
        end + timedelta(days=14),
        "ent-annual",
        "order-1",
    )
    now = datetime(2026, 7, 2, tzinfo=UTC)
    expected = 1_009_800 * int((end - now).total_seconds()) // int((end - start).total_seconds())
    assert repo.paid_value_remaining(entitlement, now) == expected
    assert repo.paid_value_remaining(entitlement, end) == 0
    assert (
        repo.paid_value_remaining(
            Entitlement("STANDARD", frozenset(), 100, 1_000, start, end, None), now
        )
        == 0
    )
    missing_order = Entitlement(
        "STANDARD", frozenset(), 100, 1_000, start, end, None, "missing-ent", "missing-order"
    )
    assert repo.paid_value_remaining(missing_order, now) == 0
    zero_period = Entitlement(
        "STANDARD", frozenset(), 100, 1_000, start, start, None, "zero-ent", "order-1"
    )
    assert repo.paid_value_remaining(zero_period, start) == 0
    store.close()


def test_entitlement_ties_follow_insert_order_and_scheduled_plan_starts_at_boundary(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)

    def insert_entitlement(entitlement_id, plan_code, effective_at, expires_at):
        plan = PLANS[plan_code]
        store.connection.execute(
            "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
            "student_limit,warning_quota,effective_at,expires_at,grace_until,"
            "source_order,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                entitlement_id,
                "fixture-admin",
                plan_code,
                '["learning","practice"]',
                plan.student_limit,
                plan.warning_quota,
                effective_at.isoformat(),
                expires_at.isoformat(),
                None,
                None,
                NOW.isoformat(),
            ),
        )

    standard_expires = NOW + timedelta(days=30)
    insert_entitlement("ent-standard", "STANDARD", NOW, standard_expires)
    insert_entitlement("ent-advanced", "ADVANCED", NOW, NOW + timedelta(days=30))
    assert repo.current_entitlement(NOW).plan_code == "ADVANCED"

    store.connection.execute("DELETE FROM entitlements")
    scheduled_at = NOW + timedelta(days=1)
    insert_entitlement(
        "ent-scheduled-standard", "STANDARD", scheduled_at, scheduled_at + timedelta(days=30)
    )
    insert_entitlement("ent-scheduled", "ADVANCED", scheduled_at, scheduled_at + timedelta(days=30))
    assert repo.current_entitlement(NOW).plan_code == "FREE"
    assert repo.scheduled_entitlement(NOW)["plan_code"] == "ADVANCED"
    assert repo.current_entitlement(scheduled_at).plan_code == "ADVANCED"
    assert repo.scheduled_entitlement(scheduled_at) is None
    store.close()


def test_current_entitlement_remains_available_through_grace_then_falls_back_to_free(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)
    plan = PLANS["STANDARD"]
    expires_at = NOW
    grace_until = NOW + timedelta(days=14)
    store.connection.execute(
        "INSERT INTO entitlements(entitlement_id,account_id,plan_code,features_json,"
        "student_limit,warning_quota,effective_at,expires_at,grace_until,source_order,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ent-grace",
            "fixture-admin",
            "STANDARD",
            '["learning","practice"]',
            plan.student_limit,
            plan.warning_quota,
            (NOW - timedelta(days=30)).isoformat(),
            expires_at.isoformat(),
            grace_until.isoformat(),
            "order-1",
            NOW.isoformat(),
        ),
    )
    assert repo.current_entitlement(NOW).plan_code == "STANDARD"
    assert repo.current_entitlement(grace_until).plan_code == "STANDARD"
    assert repo.current_entitlement(grace_until + timedelta(microseconds=1)).plan_code == "FREE"
    store.close()


def test_student_capacity_checks_total_existing_seats_at_limit(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "valid-student-password")
    repo.bind_organization("local-demo", now=NOW)
    assert repo.active_student_count() == 1
    assert repo.can_add_students(29, now=NOW) is True
    assert repo.can_add_students(30, now=NOW) is False
    assert repo.can_add_students(0, now=NOW) is False
    assert repo.can_add_students(True, now=NOW) is False
    store.close()


def test_organization_binding_is_pseudonymous_installation_wide_and_immutable(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)
    organization_id = "org_abcdefgh"
    assert repo.bind_organization(organization_id, now=NOW) == organization_id
    assert repo.bind_organization(organization_id, now=NOW) == organization_id
    assert repo.can_add_students(1, organization_id, now=NOW) is True
    assert repo.can_add_students(1, "local-demo", now=NOW) is False
    with pytest.raises(BillingError, match="organization_binding_mismatch"):
        repo.bind_organization("org_ijklmnop", now=NOW)
    with pytest.raises(BillingError, match="organization_unavailable"):
        repo.bind_organization("admin@example.org", now=NOW)
    store.close()


def test_organization_binding_corruption_and_naive_timestamps_fail_closed(tmp_path):
    store, repo, _, _, _ = _setup(tmp_path)
    with pytest.raises(BillingError, match="timezone_required"):
        repo.bind_organization("local-demo", now=datetime(2026, 10, 15, 8))
    store.connection.execute(
        "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
        "VALUES('billing.installation.organization','[]',1,'v1','test',?)",
        (NOW.isoformat(),),
    )
    with pytest.raises(BillingError, match="organization_binding_invalid"):
        repo.bind_organization("local-demo", now=NOW)
    store.close()


def test_quote_and_order_idempotency_conflicts_are_transactional(tmp_path):
    store, repo, token, _, _ = _setup(tmp_path)
    quote = Quote(
        "quote-2",
        "fixture-admin",
        "ADVANCED",
        1,
        199_000,
        0,
        0,
        199_000,
        "VND",
        NOW,
        NOW + timedelta(minutes=15),
        '{"effective_at":"2026-10-15T08:00:00+00:00"}',
    )
    repo.save_quote_with_idempotency(
        quote, key_hash="quote-key-hash", input_hash="first", token=token
    )
    repo.save_quote_with_idempotency(
        quote, key_hash="quote-key-hash", input_hash="first", token=token
    )
    assert repo.get_quote(quote.quote_id).plan_code == "ADVANCED"
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        repo.save_quote_with_idempotency(
            quote, key_hash="quote-key-hash", input_hash="changed", token=token
        )
    assert store.connection.execute("SELECT COUNT(*) FROM billing_quotes").fetchone()[0] == 2
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        repo.create_order(
            order_id="order-conflict",
            quote=repo.get_quote("quote-1"),
            gateway="different-gateway",
            mode="sandbox",
            idempotency_hash="order-idem-hash",
            now=NOW,
            token=token,
        )
    assert repo.get_order("order-conflict") is None
    store.close()


def test_order_creation_returns_existing_order_for_exact_idempotent_retry(tmp_path):
    store, repo, token, order, _ = _setup(tmp_path)

    replay = repo.create_order(
        order_id="order-retry-must-not-be-used",
        quote=repo.get_quote("quote-1"),
        gateway="internal",
        mode="sandbox",
        idempotency_hash="order-idem-hash",
        now=NOW + timedelta(seconds=1),
        token=token,
    )

    assert replay == order
    assert len(repo.list_orders()) == 1
    store.close()


def test_cancel_idempotency_record_with_missing_order_fails_closed(tmp_path):
    store, repo, token, _, _ = _setup(tmp_path)
    with store.transaction() as db:
        repo.set_setting(
            db,
            "billing.cancel.missing-order-key",
            {"order_id": "deleted-order"},
            NOW,
        )

    with pytest.raises(BillingError, match="order_unavailable"):
        repo.cancel_order_idempotent(
            "deleted-order",
            "missing-order-key",
            "fixture-admin",
            NOW,
            token,
        )
    store.close()


def test_exact_payment_idempotency_retry_and_new_paid_event_are_safe(tmp_path):
    store, repo, token, order, event = _setup(tmp_path)
    paid = repo.settle(
        event,
        now=NOW,
        apply_entitlement=_apply,
        organization_id="local-demo",
        admin_token=token,
        admin_actor_id="fixture-admin",
        idempotency_key_hash="sandbox-key-hash",
    )
    exact_retry = repo.settle(
        event,
        now=NOW + timedelta(seconds=1),
        apply_entitlement=_apply,
        organization_id="local-demo",
        admin_token=token,
        admin_actor_id="fixture-admin",
        idempotency_key_hash="sandbox-key-hash",
    )
    assert exact_retry == paid

    second_paid_event = {**event, "event_id": "event-2", "payload_hash": "b" * 64}
    replay = repo.settle(
        second_paid_event,
        now=NOW + timedelta(seconds=2),
        apply_entitlement=_apply,
        organization_id="local-demo",
        admin_token=token,
        admin_actor_id="fixture-admin",
    )
    assert replay == paid
    assert repo.get_order(order.order_id).state == "PAID"
    assert store.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
    store.close()


def test_non_ascii_admin_token_is_rejected_before_database_lookup(tmp_path):
    store, repo, token, _, _ = _setup(tmp_path)
    with pytest.raises(BillingError, match="access_denied"):
        repo.assert_admin_session(store.connection, token + "é", "fixture-admin", NOW)
    store.close()


def test_checkout_and_order_state_transitions_cover_missing_idempotent_and_invalid_rows(tmp_path):
    store, repo, token, order, _ = _setup(tmp_path)
    with pytest.raises(BillingError, match="invalid_checkout_reference"):
        repo.set_checkout(order.order_id, "", NOW, token=token, actor_id="fixture-admin")
    assert (
        repo.set_checkout(
            order.order_id, "checkout-1", NOW, token=token, actor_id="fixture-admin"
        ).checkout_ref
        == "checkout-1"
    )
    with pytest.raises(BillingError, match="checkout_reference_conflict"):
        repo.set_checkout(
            order.order_id, "checkout-other", NOW, token=token, actor_id="fixture-admin"
        )
    with pytest.raises(BillingError, match="order_unavailable"):
        repo.set_checkout(
            "missing-order", "checkout-missing", NOW, token=token, actor_id="fixture-admin"
        )
    assert repo.set_order_state(order.order_id, "PENDING", NOW).state == "PENDING"
    with pytest.raises(BillingError, match="invalid_order_transition"):
        repo.set_order_state(order.order_id, "PAID", NOW)
    assert repo.set_order_state(order.order_id, "EXPIRED", NOW).state == "EXPIRED"
    assert repo.set_order_state(order.order_id, "EXPIRED", NOW).state == "EXPIRED"
    with pytest.raises(BillingError, match="order_unavailable"):
        repo.set_order_state("missing-order", "EXPIRED", NOW)
    store.close()


def test_cancel_idempotency_conflicts_missing_and_terminal_order(tmp_path):
    store, repo, token, order, _ = _setup(tmp_path)
    cancelled = repo.cancel_order_idempotent(
        order.order_id, "cancel-key", "fixture-admin", NOW, token
    )
    assert cancelled.state == "CANCELLED"
    assert (
        repo.cancel_order_idempotent(
            order.order_id, "cancel-key", "fixture-admin", NOW, token
        ).state
        == "CANCELLED"
    )
    with pytest.raises(BillingError, match="order_unavailable"):
        repo.cancel_order_idempotent("missing-order", "missing-key", "fixture-admin", NOW, token)
    with pytest.raises(BillingError, match="invalid_order_transition"):
        repo.cancel_order_idempotent(order.order_id, "new-cancel-key", "fixture-admin", NOW, token)
    with pytest.raises(BillingError, match="idempotency_key_reused"):
        repo.cancel_order_idempotent("another-order", "cancel-key", "fixture-admin", NOW, token)
    store.close()


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"amount": 1}, "payment_binding_mismatch"),
        ({"currency": "USD"}, "payment_binding_mismatch"),
        ({"gateway": "other"}, "payment_binding_mismatch"),
        ({"mode": "live"}, "payment_binding_mismatch"),
        ({"checkout_id": "other"}, "payment_binding_mismatch"),
        ({"signature_valid": False}, "invalid_payment_event"),
    ],
)
def test_settlement_rejects_unbound_event_fields(tmp_path, changes, code):
    store, repo, _, _, event = _setup(tmp_path)
    with pytest.raises(BillingError, match=code):
        repo.settle(
            {**event, **changes},
            now=NOW,
            apply_entitlement=_apply,
            organization_id="local-demo",
        )
    assert repo.get_order("order-1").state == "PENDING"
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    store.close()


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"order_id": "missing-order"}, "order_unavailable"),
        ({"status": "unknown"}, "invalid_payment_status"),
        ({"occurred_at": datetime(2026, 10, 15, 8)}, "invalid_payment_timestamp"),
        ({"occurred_at": NOW - timedelta(minutes=6)}, "invalid_payment_timestamp"),
    ],
)
def test_settlement_rejects_missing_order_invalid_status_and_timestamps(tmp_path, changes, code):
    store, repo, _, _, event = _setup(tmp_path)
    if "status" in changes or "occurred_at" in changes:
        changes = {**changes, "payload_hash": "d" * 64}
    with pytest.raises(BillingError, match=code):
        repo.settle(
            {**event, **changes}, now=NOW, apply_entitlement=_apply, organization_id="local-demo"
        )
    assert repo.get_order("order-1").state == "PENDING"
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    store.close()


def test_event_id_cannot_be_reused_with_changed_normalized_payload(tmp_path):
    store, repo, _, _, event = _setup(tmp_path)
    pending = {**event, "status": "pending", "payload_hash": "b" * 64}
    repo.settle(pending, now=NOW, apply_entitlement=_apply, organization_id="local-demo")
    with pytest.raises(BillingError, match="payment_event_conflict"):
        repo.settle(
            {**pending, "status": "failed", "payload_hash": "c" * 64},
            now=NOW,
            apply_entitlement=_apply,
            organization_id="local-demo",
        )
    assert repo.get_order("order-1").state == "PENDING"
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 1
    store.close()


@pytest.mark.parametrize(
    "bad_context,code", [(False, "quote_unavailable"), (True, "quote_invalid")]
)
def test_settlement_rolls_back_missing_or_malformed_persisted_quote(tmp_path, bad_context, code):
    store, repo, _, _, event = _setup(tmp_path)
    if bad_context:
        store.connection.execute(
            "UPDATE billing_quotes SET inputs_json=? WHERE quote_id='quote-1'",
            ('{"months":1,"effective_at":null}',),
        )
    else:
        store.connection.execute("PRAGMA foreign_keys=OFF")
        store.connection.execute(
            "UPDATE billing_orders SET quote_id='missing-quote' WHERE order_id='order-1'"
        )
        store.connection.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(BillingError, match=code):
        repo.settle(event, now=NOW, apply_entitlement=_apply, organization_id="local-demo")
    assert repo.get_order("order-1").state == "PENDING"
    assert repo.receipt("order-1") is None
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    store.close()


def test_settlement_unknown_plan_rolls_back_paid_transition(tmp_path):
    store, repo, token, order, event = _setup(tmp_path)
    store.connection.execute("PRAGMA foreign_keys=OFF")
    store.connection.execute(
        "UPDATE billing_quotes SET plan_code='RETIRED' WHERE quote_id='quote-1'"
    )
    store.connection.execute("PRAGMA foreign_keys=ON")
    with pytest.raises(BillingError, match="unknown_plan"):
        repo.settle(
            event,
            now=NOW,
            apply_entitlement=_apply,
            organization_id="local-demo",
            admin_token=token,
            admin_actor_id="fixture-admin",
        )
    assert repo.get_order(order.order_id).state == "PENDING"
    assert repo.receipt(order.order_id) is None
    assert store.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 0
    store.close()


def test_same_normalized_event_hash_cannot_be_replayed_for_another_order(tmp_path):
    store, repo, token, _, event = _setup(tmp_path)
    first = {**event, "status": "pending"}
    repo.settle(first, now=NOW, apply_entitlement=_apply, organization_id="local-demo")
    quote = repo.get_quote("quote-1")
    second = repo.create_order(
        order_id="order-2",
        quote=quote,
        gateway="internal",
        mode="sandbox",
        idempotency_hash="order-idem-hash-2",
        now=NOW,
        token=token,
    )
    repo.set_checkout(second.order_id, "checkout-2", NOW, token=token, actor_id="fixture-admin")
    replay = {**first, "event_id": "event-2", "order_id": "order-2", "checkout_id": "checkout-2"}
    with pytest.raises(BillingError, match="payment_event_replayed"):
        repo.settle(replay, now=NOW, apply_entitlement=_apply, organization_id="local-demo")
    assert repo.get_order("order-2").state == "PENDING"
    store.close()


@pytest.mark.parametrize("status", ["pending", "failed", "cancelled"])
def test_nonpaid_callback_after_checkout_expiry_is_recorded_as_expired(tmp_path, status):
    store, repo, _, _, event = _setup(tmp_path)
    late = NOW + timedelta(minutes=16)
    result = repo.settle(
        {**event, "status": status, "occurred_at": late},
        now=late,
        apply_entitlement=_apply,
        organization_id="local-demo",
    )
    assert result.state == "EXPIRED"
    assert repo.receipt("order-1") is None
    state = store.connection.execute(
        "SELECT processed_state FROM payment_events WHERE event_id='event-1'"
    ).fetchone()[0]
    assert state == "expired_checkout"
    store.close()


def test_signed_success_after_checkout_expiry_is_visible_review_without_receipt(tmp_path):
    store, repo, _, _, event = _setup(tmp_path)
    late = NOW + timedelta(minutes=16)
    paid = repo.settle(
        {**event, "occurred_at": late},
        now=late,
        apply_entitlement=_apply,
        organization_id="local-demo",
    )
    assert paid.state == "EXPIRED"
    assert repo.receipt("order-1") is None
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0
    state = store.connection.execute(
        "SELECT processed_state FROM payment_events WHERE event_id='event-1'"
    ).fetchone()[0]
    assert state == "late_success_review"
    store.close()


@pytest.mark.parametrize("terminal", ["FAILED", "CANCELLED"])
def test_late_paid_event_does_not_override_terminal_failure_or_cancel(tmp_path, terminal):
    store, repo, token, _, event = _setup(tmp_path)
    if terminal == "FAILED":
        failure = {**event, "event_id": "failure-1", "payload_hash": "b" * 64, "status": "failed"}
        assert (
            repo.settle(
                failure, now=NOW, apply_entitlement=_apply, organization_id="local-demo"
            ).state
            == "FAILED"
        )
    else:
        repo.cancel_order_idempotent("order-1", "cancel-key-hash", "fixture-admin", NOW, token)
    success = {
        **event,
        "event_id": "late-paid-1",
        "payload_hash": "c" * 64,
        "status": "paid",
        "occurred_at": NOW + timedelta(seconds=1),
    }
    result = repo.settle(
        success,
        now=NOW + timedelta(seconds=1),
        apply_entitlement=_apply,
        organization_id="local-demo",
    )
    assert result.state == terminal
    assert repo.receipt("order-1") is None
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0
    assert (
        store.connection.execute(
            "SELECT processed_state FROM payment_events WHERE event_id='late-paid-1'"
        ).fetchone()[0]
        == "late_success_review"
    )
    store.close()


def test_distinct_connections_settle_one_event_once(tmp_path):
    store, _, token, _, event = _setup(tmp_path)
    data_dir = store.data_dir
    store.close()
    start = Barrier(2)

    def settle_in_own_connection():
        local_store = SQLiteStore(data_dir)
        try:
            local_repo = BillingRepository(local_store)
            start.wait(timeout=5)
            return local_repo.settle(
                event,
                now=NOW,
                apply_entitlement=_apply,
                organization_id="local-demo",
                admin_token=token,
                admin_actor_id="fixture-admin",
            )
        finally:
            local_store.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: settle_in_own_connection(), range(2)))
    verify = SQLiteStore(data_dir)
    try:
        assert [item.state for item in results] == ["PAID", "PAID"]
        assert verify.connection.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 1
        assert verify.connection.execute("SELECT COUNT(*) FROM billing_receipts").fetchone()[0] == 1
        assert verify.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    finally:
        verify.close()
