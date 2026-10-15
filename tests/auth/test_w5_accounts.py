from datetime import UTC, datetime, timedelta

import pytest

from aicefr.auth.accounts import AccountService
from aicefr.auth.contracts import AccountCreate, ProfileUpdate
from aicefr.auth.errors import (
    AuthorizationError,
    ConflictError,
    LockoutError,
    NotFoundError,
    ValidationError,
)
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 1, tzinfo=UTC)

    def __call__(self):
        return self.now


@pytest.fixture
def account_fixture(tmp_path):
    store = SQLiteStore(tmp_path / "identity")
    clock = Clock()
    repository = IdentityRepository(store)
    auth = AuthService(store, store, clock=clock, identity_repository=repository)
    auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "admin-pass")
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass")
    accounts = AccountService(auth, repository)
    yield store, clock, auth, repository, accounts
    store.close()


def test_profile_allowlist_and_temporary_password_gate(account_fixture):
    store, clock, auth, _, service = account_fixture
    student = auth.login("fixture-student", "student-pass")
    profile = service.update_profile(student, ProfileUpdate(goal=3, icon="book", color="blue"))
    assert (profile.goal, profile.icon, profile.color) == (3, "book", "blue")
    profile = service.update_profile(student, ProfileUpdate(goal=5))
    assert (profile.goal, profile.icon, profile.color) == (5, "book", "blue")
    profile = service.update_profile(student, ProfileUpdate(icon=None))
    assert profile.icon is None and profile.color == "blue"
    latest_audit = store.connection.execute(
        "SELECT reason FROM audit WHERE action='profile_updated' ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    assert latest_audit == (None,)
    with pytest.raises(ValidationError):
        service.update_profile(student, alias="private name")
    with pytest.raises(ValidationError):
        service.update_profile(student, ProfileUpdate(goal=True))
    with pytest.raises(ValidationError):
        service.update_profile(student, ProfileUpdate(icon="realname"))
    with pytest.raises(ValidationError):
        service.update_profile(student, ProfileUpdate(color="https"))

    admin = auth.login("fixture-admin", "admin-pass")
    legacy = service.create_legacy_account(admin, "legacy-a", ActorRole.STUDENT, "legacy-pass")
    with pytest.raises(ConflictError):
        service.create_legacy_account(admin, "legacy-a", ActorRole.STUDENT, "legacy-pass")
    legacy_token = auth.login("legacy-a", "legacy-pass")
    assert legacy.temporary_password_required
    with pytest.raises(AuthorizationError):
        auth.resolve(legacy_token)
    clock.now += timedelta(hours=25)
    with pytest.raises(AuthorizationError) as expired:
        auth.login("legacy-a", "legacy-pass")
    assert expired.value.code == "temporary_password_expired"
    admin = auth.login("fixture-admin", "admin-pass")
    reset = service.admin_action(admin, "legacy-a", "reset")
    assert service.get_profile(
        auth.login("legacy-a", reset.temporary_password)
    ).temporary_password_required
    created = service.create_accounts(
        admin, [AccountCreate("cohort-a1", ActorRole.STUDENT, goal=5)]
    )
    assert len(created) == 1 and created[0].temporary_password not in repr(created[0])
    temporary_token = auth.login("cohort-a1", created[0].temporary_password)
    assert service.get_profile(temporary_token).temporary_password_required
    with pytest.raises(AuthorizationError):
        auth.resolve(temporary_token)
    with pytest.raises(AuthorizationError):
        service.update_profile(temporary_token, ProfileUpdate(goal=2))
    with pytest.raises(AuthorizationError):
        service.list_sessions(temporary_token)
    with pytest.raises(AuthorizationError):
        service.activity(temporary_token)

    rotated = service.change_password(
        temporary_token, created[0].temporary_password, "changed-pass"
    )
    assert auth.resolve(rotated).actor_id == "cohort-a1"
    assert not service.get_profile(rotated).temporary_password_required
    with pytest.raises(AuthorizationError):
        auth.resolve(temporary_token, allow_temporary=True)


def test_password_policy_session_ownership_and_lockout(account_fixture):
    store, clock, auth, _, service = account_fixture
    first = auth.login("fixture-student", "student-pass")
    second = auth.login("fixture-student", "student-pass")
    sessions = service.list_sessions(first)
    assert len(sessions) == 2 and sum(item.current for item in sessions) == 1
    assert all(item.session_id != item.actor_id for item in sessions)
    with pytest.raises(ValidationError):
        service.change_password(first, "student-pass", "é" * 37)
    with pytest.raises(NotFoundError):
        service.revoke_session(
            first, service.list_sessions(auth.login("fixture-admin", "admin-pass"))[0].session_id
        )
    assert service.revoke_other_sessions(first) == 1
    with pytest.raises(AuthorizationError):
        auth.resolve(second)
    for _ in range(5):
        try:
            auth.login("fixture-student", "incorrect")
        except (AuthorizationError, LockoutError):
            pass
    with pytest.raises(LockoutError) as locked:
        auth.login("fixture-student", "student-pass")
    assert locked.value.retry_after == 900
    assert (
        store.connection.execute(
            "SELECT failed_attempts FROM accounts WHERE actor_id='fixture-student'"
        ).fetchone()[0]
        == 5
    )
    clock.now = clock.now.replace(minute=16)
    assert auth.login("fixture-student", "student-pass")


def test_admin_batch_is_atomic_and_self_guards(account_fixture):
    store, _, auth, repository, service = account_fixture
    admin = auth.login("fixture-admin", "admin-pass")
    with pytest.raises(ConflictError):
        service.create_accounts(
            admin,
            [
                AccountCreate("cohort-x", ActorRole.STUDENT),
                AccountCreate("cohort-x", ActorRole.TEACHER),
            ],
        )
    with pytest.raises(ValidationError):
        service.create_accounts(
            admin,
            [
                AccountCreate("cohort-y", ActorRole.STUDENT),
                AccountCreate("cohort-z", ActorRole.STUDENT, goal=4),
            ],
        )
    assert (
        store.connection.execute(
            "SELECT 1 FROM accounts WHERE actor_id IN ('cohort-x','cohort-y','cohort-z')"
        ).fetchone()
        is None
    )
    with pytest.raises(ConflictError):
        service.admin_action(admin, "fixture-admin", "disable")
    with pytest.raises(ConflictError):
        service.admin_action(admin, "fixture-admin", "reset")
    student = auth.login("fixture-student", "student-pass")
    with pytest.raises(AuthorizationError):
        service.create_accounts(student, [AccountCreate("unauthorized", ActorRole.STUDENT)])
    with pytest.raises(ValidationError):
        service.admin_action(admin, "fixture-student", "role")
    service.admin_action(admin, "fixture-student", "role", ActorRole.TEACHER)
    with pytest.raises(AuthorizationError):
        auth.resolve(student)
    service.admin_action(admin, "fixture-student", "unlock")
    service.admin_action(admin, "fixture-student", "disable")
    with pytest.raises(AuthorizationError):
        auth.login("fixture-student", "student-pass")
    assert repository.activity("fixture-student")[0].kind == "login_failed"
    admin_actor = auth.resolve(admin)
    disabled = next(
        item for item in repository.list_accounts(admin_actor) if item.actor_id == "fixture-student"
    )
    assert disabled.disabled


def test_password_rotation_rechecks_session_after_hashing(account_fixture, monkeypatch):
    _, clock, auth, repository, service = account_fixture
    token = auth.login("fixture-student", "student-pass")
    original_hash = type(auth._hasher).hash

    def revoke_during_hash(hasher, password):
        if hasher is auth._hasher:
            repository.revoke_all_sessions("fixture-student", clock(), "race-test")
        return original_hash(hasher, password)

    monkeypatch.setattr(type(auth._hasher), "hash", revoke_during_hash)
    with pytest.raises(AuthorizationError):
        service.change_password(token, "student-pass", "updated-pass")
    with pytest.raises(AuthorizationError):
        auth.resolve(token)
    assert auth.login("fixture-student", "student-pass")
