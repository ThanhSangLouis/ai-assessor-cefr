import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.auth.accounts import AccountService
from aicefr.auth.contracts import AccountCreate, ProfileUpdate
from aicefr.auth.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from aicefr.auth.service import AuthService, _digest
from aicefr.contracts import ActorRole
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 1, tzinfo=UTC)

    def __call__(self):
        return self.now


@pytest.fixture
def security_fixture(tmp_path):
    store = SQLiteStore(tmp_path / "account-security")
    clock = Clock()
    repository = IdentityRepository(store)
    auth = AuthService(store, store, clock=clock, identity_repository=repository)
    auth.bootstrap_fixture_account("fixture-security-admin", ActorRole.ADMIN, "admin-password")
    auth.bootstrap_fixture_account(
        "fixture-security-student", ActorRole.STUDENT, "student-password"
    )
    service = AccountService(auth, repository)
    yield store, clock, auth, repository, service
    store.close()


def test_account_service_rejects_bad_inputs_credentials_and_missing_profile(security_fixture):
    _, _, auth, repository, service = security_fixture
    admin = auth.login("fixture-security-admin", "admin-password")
    student = auth.login("fixture-security-student", "student-password")

    with pytest.raises(AuthorizationError):
        service.change_password(student, "wrong-password", "different-password")
    with pytest.raises(ValidationError, match="password_reuse"):
        service.change_password(student, "student-password", "fixture-security-student")
    with pytest.raises(ValidationError, match="password_reuse"):
        service.change_password(student, "student-password", "student-password")
    with pytest.raises(ValidationError, match="invalid_profile_fields"):
        service.update_profile(student, ProfileUpdate(goal=2), color="blue")
    with pytest.raises(ValidationError, match="invalid_profile_fields"):
        service.update_profile(student, object())

    for value in (None, (), "not-a-list", []):
        with pytest.raises(ValidationError, match="batch_size"):
            service.create_accounts(admin, value)
    with pytest.raises(ValidationError, match="invalid_account"):
        service.create_accounts(admin, [object()])
    with pytest.raises(ValidationError, match="batch_size"):
        service.create_accounts(
            admin,
            [AccountCreate(f"oversize-{i}", ActorRole.STUDENT) for i in range(201)],
        )
    with pytest.raises(ValidationError, match="password_policy"):
        service.create_legacy_account(admin, "short-pass-user", ActorRole.STUDENT, "short")
    with pytest.raises(ValidationError, match="password_reuse"):
        service.create_legacy_account(
            admin, "fixture-security-admin", ActorRole.STUDENT, "fixture-security-admin"
        )

    monkeypatch_get_profile = repository.get_profile
    repository.get_profile = lambda _: None
    with pytest.raises(NotFoundError, match="account_not_found"):
        service.get_profile(student)
    repository.get_profile = monkeypatch_get_profile


def test_session_revocation_reports_current_and_other_and_rejects_expired(security_fixture):
    _, clock, auth, _, service = security_fixture
    current = auth.login("fixture-security-student", "student-password")
    other = auth.login("fixture-security-student", "student-password")
    sessions = service.list_sessions(current)
    current_id = next(item.session_id for item in sessions if item.current)
    other_id = next(item.session_id for item in sessions if not item.current)

    assert service.revoke_session(current, other_id) is False
    with pytest.raises(AuthorizationError):
        auth.resolve(other)
    assert service.revoke_session(current, current_id) is True
    with pytest.raises(AuthorizationError):
        auth.resolve(current)

    fresh = auth.login("fixture-security-student", "student-password")
    clock.now += timedelta(hours=9)
    with pytest.raises(AuthorizationError):
        service.list_sessions(fresh)


def test_login_and_password_rotation_keep_only_coarse_device_metadata(security_fixture):
    _, _, auth, _, service = security_fixture
    mobile = auth.login("fixture-security-student", "student-password", device="mobile")
    session = next(item for item in service.list_sessions(mobile) if item.current)
    assert session.device == "mobile"

    rotated = service.change_password(mobile, "student-password", "rotated-device-pass")
    assert next(item for item in service.list_sessions(rotated) if item.current).device == "mobile"

    user_agent = "Mozilla/5.0 (real untrusted raw browser string)"
    unknown = auth.login("fixture-security-student", "rotated-device-pass", device=user_agent)
    unknown_session = next(item for item in service.list_sessions(unknown) if item.current)
    assert unknown_session.device == "unknown"
    assert user_agent not in repr(unknown_session)


def test_resolve_does_not_resurrect_session_revoked_between_read_and_touch(
    security_fixture, monkeypatch
):
    store, _, auth, _, _ = security_fixture
    token = auth.login("fixture-security-student", "student-password")
    second_connection = sqlite3.connect(
        store.data_dir / "metadata.sqlite3", isolation_level=None, timeout=5.0
    )
    original_touch = store.touch_session

    def revoke_then_touch(session, *, now):
        second_connection.execute(
            "DELETE FROM sessions WHERE token_digest=?", (session.token_digest,)
        )
        return original_touch(session, now=now)

    monkeypatch.setattr(store, "touch_session", revoke_then_touch)
    try:
        with pytest.raises(AuthorizationError):
            auth.resolve(token)
        assert store.get_session(_digest(token)) is None
        assert (
            second_connection.execute(
                "SELECT 1 FROM sessions WHERE token_digest=?", (_digest(token),)
            ).fetchone()
            is None
        )
    finally:
        second_connection.close()


def test_admin_reset_and_all_actions_revoke_sessions_and_return_safe_state(security_fixture):
    store, _, auth, repository, service = security_fixture
    admin = auth.login("fixture-security-admin", "admin-password")
    first = auth.login("fixture-security-student", "student-password")
    second = auth.login("fixture-security-student", "student-password")

    with pytest.raises(ConflictError, match="self_action_prohibited"):
        service.admin_action(admin, "fixture-security-admin", "reset")
    reset = service.admin_action(admin, "fixture-security-student", "reset")
    assert reset.actor.actor_id == "fixture-security-student"
    assert reset.temporary_password not in repr(reset)
    for token in (first, second):
        with pytest.raises(AuthorizationError):
            auth.resolve(token)
    with pytest.raises(AuthorizationError):
        auth.login("fixture-security-student", "student-password")

    temporary = auth.login("fixture-security-student", reset.temporary_password)
    rotated = service.change_password(temporary, reset.temporary_password, "rotated-password")
    assert auth.resolve(rotated).actor_id == "fixture-security-student"

    service.admin_action(admin, "fixture-security-student", "disable")
    with pytest.raises(AuthorizationError):
        auth.resolve(rotated)
    service.admin_action(admin, "fixture-security-student", "enable")
    enabled = auth.login("fixture-security-student", "rotated-password")
    service.admin_action(admin, "fixture-security-student", "revoke_all")
    with pytest.raises(AuthorizationError):
        auth.resolve(enabled)
    service.admin_action(admin, "fixture-security-student", "unlink")
    with pytest.raises(ValidationError, match="invalid_admin_action"):
        service.admin_action(admin, "fixture-security-student", "unknown")

    assert (
        repository.admin_account(auth.resolve(admin), "fixture-security-student").disabled is False
    )
    created = service.create_legacy_account(
        admin, "legacy-state-user", ActorRole.STUDENT, "legacy-password"
    )
    assert created.temporary_password_required
    changed = service.change_legacy_account(admin, "legacy-state-user", True, True)
    assert changed["disabled"] is True and changed["unlocked"] is True
    assert changed["locked_until"] is None
    changed = service.change_legacy_account(admin, "legacy-state-user", False, False)
    assert changed["disabled"] is False and changed["unlocked"] is False


def test_admin_reset_rechecks_live_authorization_after_hash_work(security_fixture, monkeypatch):
    _, clock, auth, repository, service = security_fixture
    admin = auth.login("fixture-security-admin", "admin-password")
    before = store_row(repository, "fixture-security-student")
    original_hash = type(auth._hasher).hash

    def revoke_admin_during_hash(hasher, password):
        if hasher is auth._hasher:
            repository.revoke_all_sessions("fixture-security-admin", clock(), "test-race")
        return original_hash(hasher, password)

    monkeypatch.setattr(type(auth._hasher), "hash", revoke_admin_during_hash)
    with pytest.raises(AuthorizationError):
        service.admin_action(admin, "fixture-security-student", "reset")
    assert store_row(repository, "fixture-security-student") == before


def store_row(repository, actor_id):
    return repository.connection.execute(
        "SELECT password_hash FROM accounts WHERE actor_id=?", (actor_id,)
    ).fetchone()[0]
