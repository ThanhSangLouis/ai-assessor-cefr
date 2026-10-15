from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.auth.service import AuthService
from aicefr.billing.errors import BillingError
from aicefr.billing.licenses import LicenseError, LicenseService, _canonical
from aicefr.billing.plans import PLANS
from aicefr.billing.secrets import KeyRing
from aicefr.contracts import ActorRole
from aicefr.storage.billing import BillingRepository
from aicefr.storage.sqlite import SQLiteStore

NOW = datetime(2026, 10, 15, 4, 0, tzinfo=UTC)


@pytest.fixture
def license_env(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    repo = BillingRepository(store)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "safe test password")
    token = auth.login("fixture-admin", "safe test password")
    keyring = KeyRing(tmp_path / "data")
    service = LicenseService(auth, store, keyring, clock=lambda: NOW)
    try:
        yield store, repo, auth, token, keyring, service
    finally:
        store.close()


def test_issue_and_install_are_admin_only_and_same_license_is_idempotent(license_env):
    store, _, auth, token, _, service = license_env
    issued = service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
    assert set(issued) == {"license", "signed_license"}
    assert issued["license"]["plan_code"] == "STANDARD"
    assert "signature" not in issued["license"]
    assert issued["signed_license"]["payload"]["organization"] == "local-demo"
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1

    installed = service.install(token, issued["signed_license"])
    assert installed["license_id"] == issued["license"]["license_id"]
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1
    service.clock = lambda: NOW + timedelta(days=31)
    with pytest.raises(LicenseError, match="license_expired"):
        service.install(token, issued["signed_license"])

    student = auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student pass")
    student_token = auth.login(student.actor_id, "student pass")
    before = store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
    with pytest.raises(LicenseError, match="admin_required"):
        service.issue(student_token, "STANDARD")
    with pytest.raises(LicenseError, match="admin_required"):
        service.install(student_token, issued["signed_license"])
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == before


def test_license_issue_idempotency_replays_artifact_and_rejects_changed_input(license_env):
    store, _, _, token, _, service = license_env
    expiry = NOW + timedelta(days=30)
    first = service.issue(token, "STANDARD", expires_at=expiry, idempotency_key="license-issue-001")
    replay = service.issue(
        token, "STANDARD", expires_at=expiry, idempotency_key="license-issue-001"
    )
    assert replay == first
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    assert (
        store.connection.execute(
            "SELECT COUNT(*) FROM audit WHERE action='billing_license_issued'"
        ).fetchone()[0]
        == 1
    )

    with pytest.raises(LicenseError, match="idempotency_key_reused"):
        service.issue(token, "ADVANCED", expires_at=expiry, idempotency_key="license-issue-001")
    with pytest.raises(LicenseError, match="invalid_idempotency_key"):
        service.issue(token, "STANDARD", expires_at=expiry, idempotency_key="bad key")
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1

    soon_expiry = NOW + timedelta(minutes=10)
    shortly_valid = service.issue(
        token, "TRIAL", expires_at=soon_expiry, idempotency_key="license-issue-002"
    )
    service.clock = lambda: NOW + timedelta(minutes=11)
    expired_retry = service.issue(
        token, "TRIAL", expires_at=soon_expiry, idempotency_key="license-issue-002"
    )
    assert expired_retry == shortly_valid
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 2


def test_tamper_wrong_org_version_limits_and_nonce_replay_are_rejected(license_env):
    store, _, _, token, keyring, service = license_env
    issued = service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
    signed = issued["signed_license"]

    tampered = {
        "payload": dict(signed["payload"], student_limit=999),
        "signature": signed["signature"],
    }
    with pytest.raises(LicenseError):
        service.install(token, tampered)

    wrong_org_payload = dict(signed["payload"], organization="another-org")
    wrong_org = {
        "payload": wrong_org_payload,
        "signature": keyring.sign_license(
            json.dumps(
                wrong_org_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_wrong_organization"):
        service.install(token, wrong_org)

    wrong_version_payload = dict(signed["payload"], key_version="2")
    wrong_version = {
        "payload": wrong_version_payload,
        "signature": keyring.sign_license(
            json.dumps(
                wrong_version_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_wrong_version"):
        service.install(token, wrong_version)

    reused_nonce_payload = dict(
        signed["payload"],
        plan_code="ADVANCED",
        features=sorted(PLANS["ADVANCED"].features),
        student_limit=PLANS["ADVANCED"].student_limit,
    )
    replay = {
        "payload": reused_nonce_payload,
        "signature": keyring.sign_license(
            json.dumps(
                reused_nonce_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_nonce_replayed"):
        service.install(token, replay)
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1


def test_entitlement_write_uses_caller_transaction_and_audits_without_secret(license_env):
    store, _, _, _, _, service = license_env
    with pytest.raises(RuntimeError):
        with store.transaction() as db:
            service.apply_entitlement(
                db,
                account_id="fixture-admin",
                organization_id="local-demo",
                plan_code="TRIAL",
                features=PLANS["TRIAL"].features,
                student_limit=PLANS["TRIAL"].student_limit,
                warning_quota=PLANS["TRIAL"].warning_quota,
                effective_at=NOW,
                expires_at=NOW + timedelta(days=30),
                grace_until=None,
                source_order=None,
            )
            raise RuntimeError("exercise rollback")
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0

    with store.transaction() as db:
        entitlement_id = service.apply_entitlement(
            db,
            account_id="fixture-admin",
            organization_id="local-demo",
            plan_code="TRIAL",
            features=PLANS["TRIAL"].features,
            student_limit=PLANS["TRIAL"].student_limit,
            warning_quota=PLANS["TRIAL"].warning_quota,
            effective_at=NOW,
            expires_at=NOW + timedelta(days=30),
            grace_until=None,
            source_order=None,
        )
    audit = store.connection.execute(
        "SELECT action,object_id,reason FROM audit WHERE object_id=?", (entitlement_id,)
    ).fetchone()
    assert audit == ("billing_entitlement_applied", entitlement_id, None)


def test_license_issue_requires_known_plan_features_bounded_seats_and_expiry(license_env):
    store, _, _, token, _, service = license_env
    assert service.status(token) == {"organization": "local-demo", "license_count": 0}
    with pytest.raises(LicenseError, match="license_invalid_time"):
        service.issue(token, "STANDARD")
    with pytest.raises(LicenseError, match="license_invalid_plan"):
        service.issue(token, "SUPER")
    with pytest.raises(LicenseError, match="license_invalid_features"):
        service.issue(
            token,
            "STANDARD",
            features="learning",
            expires_at=NOW + timedelta(days=7),
        )
    with pytest.raises(LicenseError, match="license_invalid_features"):
        service.issue(
            token,
            "STANDARD",
            features=["learning", "learning"],
            expires_at=NOW + timedelta(days=7),
        )
    with pytest.raises(LicenseError, match="license_invalid_features"):
        service.issue(
            token,
            "STANDARD",
            features=["learning", "research_export"],
            expires_at=NOW + timedelta(days=7),
        )
    with pytest.raises(LicenseError, match="license_invalid_limits"):
        service.issue(
            token,
            "STANDARD",
            student_limit=10_000,
            expires_at=NOW + timedelta(days=7),
        )
    with pytest.raises(LicenseError, match="license_invalid_time"):
        service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=3651))
    with pytest.raises(LicenseError, match="license_expired"):
        service.issue(token, "STANDARD", expires_at=NOW)
    service.issue(token, "TRIAL", expires_at=NOW + timedelta(days=7))
    status = service.status(token)
    assert status["plan_code"] == "TRIAL"
    assert status["student_limit"] == PLANS["TRIAL"].student_limit
    assert "signature" not in status and "payload" not in status
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1


def test_license_configuration_and_canonical_payload_bounds(tmp_path, license_env):
    with pytest.raises(BillingError, match="organization_binding_mismatch"):
        LicenseService(None, license_env[0], license_env[4], organization="org_abc12345")
    with pytest.raises(LicenseError, match="license_invalid_payload"):
        _canonical({"nonserializable": object()})
    with pytest.raises(LicenseError, match="license_payload_too_large"):
        _canonical({"bounded": "x" * 16_385})


def test_license_payload_uses_pseudonymous_org_and_install_binding_is_immutable(tmp_path):
    store = SQLiteStore(tmp_path / "org-data")
    BillingRepository(store)
    auth = AuthService(store, store, clock=lambda: NOW)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "safe test password")
    token = auth.login("fixture-admin", "safe test password")
    keyring = KeyRing(store.data_dir)
    service = LicenseService(auth, store, keyring, organization="org_abc12345", clock=lambda: NOW)
    try:
        issued = service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
        assert issued["signed_license"]["payload"]["organization"] == "org_abc12345"
        with pytest.raises(BillingError, match="organization_binding_mismatch"):
            LicenseService(auth, store, keyring, organization="org_other1234", clock=lambda: NOW)
    finally:
        store.close()


def test_transaction_rechecks_admin_after_payload_work_and_rolls_back(license_env, monkeypatch):
    store, _, _, token, _, service = license_env
    original = service._build_payload

    def expire_session_after_build(*args, **kwargs):
        payload = original(*args, **kwargs)
        store.connection.execute(
            "UPDATE sessions SET idle_expires_at=? WHERE token_digest=?",
            (NOW.isoformat(), hashlib.sha256(token.encode("ascii")).hexdigest()),
        )
        return payload

    monkeypatch.setattr(service, "_build_payload", expire_session_after_build)
    with pytest.raises(LicenseError, match="admin_required"):
        service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 0
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0


def test_apply_entitlement_validates_org_limits_features_time_and_identity(license_env):
    store, _, _, _, _, service = license_env
    params = {
        "account_id": "fixture-admin",
        "organization_id": "local-demo",
        "plan_code": "TRIAL",
        "effective_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "grace_until": None,
        "source_order": None,
    }
    failures = [
        {"organization_id": "other"},
        {"features": ["research_export"]},
        {"student_limit": True},
        {"warning_quota": 101},
        {"expires_at": NOW},
        {"grace_until": NOW - timedelta(seconds=1)},
        {"account_id": ""},
        {"source_order": "x" * 201},
    ]
    for override in failures:
        arguments = (
            {
                "features": PLANS["TRIAL"].features,
                "student_limit": PLANS["TRIAL"].student_limit,
                "warning_quota": PLANS["TRIAL"].warning_quota,
            }
            | params
            | override
        )
        with pytest.raises(LicenseError):
            with store.transaction() as db:
                service.apply_entitlement(db, **arguments)
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 0


def test_signed_license_rejects_bad_signature_and_unknown_payload_field(license_env):
    _, _, _, token, _, service = license_env
    issued = service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
    invalid_signature = dict(issued["signed_license"], signature="0" * 64)
    with pytest.raises(LicenseError, match="license_invalid_signature"):
        service.install(token, invalid_signature)
    unknown_payload = dict(issued["signed_license"]["payload"], research_export=True)
    with pytest.raises(LicenseError, match="license_invalid_payload"):
        service.install(
            token, {"payload": unknown_payload, "signature": issued["signed_license"]["signature"]}
        )


def test_signed_license_refuses_future_issuance_and_expiry_before_issuance(license_env):
    _, _, _, token, keyring, service = license_env
    issued = service.issue(token, "STANDARD", expires_at=NOW + timedelta(days=30))
    original = issued["signed_license"]["payload"]

    future_issued = dict(original, issued_at=(NOW + timedelta(minutes=6)).isoformat())
    future = {
        "payload": future_issued,
        "signature": keyring.sign_license(
            json.dumps(
                future_issued, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_invalid_time"):
        service.install(token, future)

    reversed_dates = dict(
        original,
        issued_at=(NOW + timedelta(minutes=5)).isoformat(),
        expires_at=(NOW + timedelta(minutes=4)).isoformat(),
    )
    reversed_artifact = {
        "payload": reversed_dates,
        "signature": keyring.sign_license(
            json.dumps(
                reversed_dates, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_invalid_time"):
        service.install(token, reversed_artifact)

    short_nonce = dict(original, nonce="tiny")
    invalid_nonce = {
        "payload": short_nonce,
        "signature": keyring.sign_license(
            json.dumps(
                short_nonce, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_invalid_nonce"):
        service.install(token, invalid_nonce)

    naive_time = dict(original, issued_at=NOW.replace(tzinfo=None).isoformat())
    naive_artifact = {
        "payload": naive_time,
        "signature": keyring.sign_license(
            json.dumps(
                naive_time, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ),
    }
    with pytest.raises(LicenseError, match="license_invalid_time"):
        service.install(token, naive_artifact)


def test_install_new_signed_license_writes_entitlement_and_fixed_audit_atomically(license_env):
    store, _, _, token, keyring, service = license_env
    payload = service._build_payload("STANDARD", None, None, NOW + timedelta(days=30))
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    artifact = {"payload": payload, "signature": keyring.sign_license(canonical)}

    installed = service.install(token, artifact)
    assert installed["plan_code"] == "STANDARD"
    assert store.connection.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1
    assert store.connection.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0] == 1
    entitlement = store.connection.execute(
        "SELECT object_id FROM audit WHERE action='billing_entitlement_applied'"
    ).fetchone()
    assert entitlement is not None
    assert store.connection.execute(
        "SELECT action FROM audit WHERE object_id=?", (entitlement[0],)
    ).fetchone() == ("billing_entitlement_applied",)
