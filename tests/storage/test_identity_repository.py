import sqlite3
from datetime import UTC, datetime

import pytest

from aicefr.auth.contracts import AccountCreate
from aicefr.auth.errors import ValidationError
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole
from aicefr.storage.identity import IdentityRepository, public_session_id
from aicefr.storage.sqlite import SQLiteStore


def test_batch_limit_and_opaque_session_identifier(tmp_path):
    store = SQLiteStore(tmp_path / "identity")
    try:
        now = datetime(2026, 10, 1, tzinfo=UTC)
        repository = IdentityRepository(store)
        auth = AuthService(store, store, clock=lambda: now)
        creator = auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "admin-pass")
        entries = [
            (AccountCreate(f"bulk-{i:03d}", ActorRole.STUDENT), "account-hash", "temporary-hash")
            for i in range(200)
        ]
        created = repository.create_accounts(creator, entries, now)
        assert len(created) == 200
        assert (
            store.connection.execute("SELECT count(*) FROM temporary_passwords").fetchone()[0]
            == 200
        )
        with pytest.raises(ValidationError):
            repository.create_accounts(
                creator, entries + [(AccountCreate("bulk-over", ActorRole.STUDENT), "h", "h")], now
            )
        assert store.connection.execute("SELECT count(*) FROM accounts").fetchone()[0] == 201

        student = auth.bootstrap_fixture_account(
            "fixture-session", ActorRole.STUDENT, "student-pass"
        )
        token = auth.login(student.actor_id, "student-pass")
        digest = store.connection.execute(
            "SELECT token_digest FROM sessions WHERE actor_id=?", (student.actor_id,)
        ).fetchone()[0]
        session_id = public_session_id(digest)
        assert session_id != digest
        assert token not in session_id
        assert len(repository.list_sessions(student.actor_id)[0][0].session_id) == 64
    finally:
        store.close()


def test_batch_database_failure_rolls_back_every_insert_and_side_effect(tmp_path):
    store = SQLiteStore(tmp_path / "identity-batch-rollback")
    try:
        now = datetime(2026, 10, 1, tzinfo=UTC)
        repository = IdentityRepository(store)
        auth = AuthService(store, store, clock=lambda: now, identity_repository=repository)
        creator = auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "admin-pass")
        store.connection.execute(
            "CREATE TRIGGER reject_second_profile BEFORE INSERT ON account_profiles "
            "WHEN NEW.account_id='cohort-second' "
            "BEGIN SELECT RAISE(ABORT,'injected profile failure'); END"
        )
        before = {
            "accounts": store.connection.execute(
                "SELECT count(*) FROM accounts WHERE actor_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
            "profiles": store.connection.execute(
                "SELECT count(*) FROM account_profiles WHERE account_id IN "
                "('cohort-first','cohort-second')"
            ).fetchone()[0],
            "temporary_passwords": store.connection.execute(
                "SELECT count(*) FROM temporary_passwords WHERE account_id IN "
                "('cohort-first','cohort-second')"
            ).fetchone()[0],
            "audit": store.connection.execute(
                "SELECT count(*) FROM audit WHERE action='account_created' "
                "AND object_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
            "activity": store.connection.execute(
                "SELECT count(*) FROM activity_events WHERE kind='account_created' "
                "AND object_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
        }
        entries = [
            (AccountCreate("cohort-first", ActorRole.STUDENT), "account-hash", "temporary-hash"),
            (AccountCreate("cohort-second", ActorRole.STUDENT), "account-hash", "temporary-hash"),
        ]
        with pytest.raises(sqlite3.IntegrityError, match="injected profile failure"):
            repository.create_accounts(creator, entries, now)
        after = {
            "accounts": store.connection.execute(
                "SELECT count(*) FROM accounts WHERE actor_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
            "profiles": store.connection.execute(
                "SELECT count(*) FROM account_profiles WHERE account_id IN "
                "('cohort-first','cohort-second')"
            ).fetchone()[0],
            "temporary_passwords": store.connection.execute(
                "SELECT count(*) FROM temporary_passwords WHERE account_id IN "
                "('cohort-first','cohort-second')"
            ).fetchone()[0],
            "audit": store.connection.execute(
                "SELECT count(*) FROM audit WHERE action='account_created' "
                "AND object_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
            "activity": store.connection.execute(
                "SELECT count(*) FROM activity_events WHERE kind='account_created' "
                "AND object_id IN ('cohort-first','cohort-second')"
            ).fetchone()[0],
        }
        assert after == before
    finally:
        store.close()
