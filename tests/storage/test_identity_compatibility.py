from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from tests.storage.test_w5_storage_foundation import _make_v4

from aicefr.auth.accounts import AccountService
from aicefr.auth.contracts import ProfileUpdate
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole
from aicefr.storage.google_identity import GoogleIdentityRepository, google_subject_hash
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore


def test_v4_identity_rows_survive_v9_upgrade_and_reopen(tmp_path):
    data_dir = tmp_path / "legacy-v4"
    legacy = _make_v4(data_dir)
    raw_session = "legacy-session-token-preserved-through-upgrade"
    session_digest = hashlib.sha256(raw_session.encode("ascii")).hexdigest()
    created_at = "2026-10-15T11:00:00+00:00"
    last_seen_at = "2026-10-15T11:30:00+00:00"
    idle_expires_at = "2026-10-15T13:00:00+00:00"
    absolute_expires_at = "2026-10-16T11:00:00+00:00"
    legacy.connection.execute("DELETE FROM sessions")
    legacy.connection.execute(
        "INSERT INTO sessions VALUES(?,?,?,?,?,?,?)",
        (
            session_digest,
            "student",
            "student",
            created_at,
            last_seen_at,
            idle_expires_at,
            absolute_expires_at,
        ),
    )
    legacy.close()

    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    migrated = SQLiteStore(data_dir)
    assert migrated.connection.execute("PRAGMA user_version").fetchone() == (9,)
    legacy_account = migrated.connection.execute(
        "SELECT actor_id,role,password_hash FROM accounts WHERE actor_id='student'"
    ).fetchone()
    assert legacy_account == ("student", "student", "hash")
    assert migrated.connection.execute(
        "SELECT token_digest,actor_id,role,created_at,last_seen_at,idle_expires_at,"
        "absolute_expires_at "
        "FROM sessions WHERE actor_id='student'"
    ).fetchone() == (
        session_digest,
        "student",
        "student",
        created_at,
        last_seen_at,
        idle_expires_at,
        absolute_expires_at,
    )
    assert migrated.connection.execute(
        "SELECT participant_id,consent_version,state,recorded_at,research_allowed "
        "FROM consents WHERE participant_id='student'"
    ).fetchone() == (
        "student",
        "v1",
        "active",
        "2026-10-01T00:00:00+00:00",
        1,
    )

    repository = IdentityRepository(migrated)
    auth = AuthService(migrated, migrated, clock=lambda: now, identity_repository=repository)
    accounts = AccountService(auth, repository)
    actor = auth.resolve(raw_session)
    assert actor.actor_id == "student"
    assert actor.role is ActorRole.STUDENT
    profile = accounts.get_profile(raw_session)
    assert profile.actor_id == "student"
    assert profile.role is ActorRole.STUDENT
    assert profile.temporary_password_required is False

    sessions = accounts.list_sessions(raw_session)
    assert len(sessions) == 1
    assert sessions[0].current is True
    assert sessions[0].actor_id == "student"
    assert sessions[0].session_id != session_digest
    assert raw_session not in repr(sessions[0])

    updated = accounts.update_profile(
        raw_session,
        ProfileUpdate(goal=3, icon="book", color="blue"),
    )
    assert (updated.goal, updated.icon, updated.color) == (3, "book", "blue")
    assert accounts.consent(raw_session).consent_version == "v1"
    changed_consent = accounts.set_consent(
        raw_session,
        version="consent-v2",
        research_allowed=False,
        active=True,
    )
    assert changed_consent.consent_version == "consent-v2"
    assert changed_consent.research_allowed is False

    subject = "synthetic-legacy-link-subject"
    google_repository = GoogleIdentityRepository(migrated)
    google_repository.link_subject("student", google_subject_hash(subject), now)
    assert google_repository.account_for_subject(google_subject_hash(subject)) == "student"
    assert migrated.connection.execute(
        "SELECT subject_hash FROM account_identities WHERE account_id='student' "
        "AND provider='google'"
    ).fetchone() == (google_subject_hash(subject),)

    profile_columns = {
        row[1] for row in migrated.connection.execute("PRAGMA table_info(account_profiles)")
    }
    assert profile_columns == {"account_id", "goal", "icon", "color", "revision", "updated_at"}
    profile_row = migrated.connection.execute(
        "SELECT goal,icon,color FROM account_profiles WHERE account_id='student'"
    ).fetchone()
    assert profile_row == (3, "book", "blue")
    assert migrated.connection.execute(
        "SELECT consent_version,state,research_allowed,source FROM consent_events "
        "WHERE account_id='student'"
    ).fetchall() == [("consent-v2", "active", 0, "self_service")]
    assert migrated.connection.execute(
        "SELECT event_id,actor_id,action,object_id FROM audit WHERE action='google_linked'"
    ).fetchone()[1:] == ("student", "google_linked", "student")
    assert migrated.connection.execute(
        "SELECT token_digest FROM sessions WHERE actor_id='student'"
    ).fetchone() == (session_digest,)
    assert migrated.connection.execute("PRAGMA user_version").fetchone() == (9,)
    assert raw_session not in repr(migrated.connection.execute("SELECT * FROM accounts").fetchall())
    assert subject not in repr(
        migrated.connection.execute("SELECT * FROM account_identities").fetchall()
    )
    assert session_digest not in repr(sessions)

    migrated.close()
    reopened = SQLiteStore(data_dir)
    try:
        assert reopened.connection.execute("PRAGMA user_version").fetchone() == (9,)
        reopened_repository = IdentityRepository(reopened)
        reopened_auth = AuthService(
            reopened,
            reopened,
            clock=lambda: now + timedelta(minutes=1),
            identity_repository=reopened_repository,
        )
        reopened_accounts = AccountService(reopened_auth, reopened_repository)
        assert reopened_auth.resolve(raw_session).actor_id == "student"
        assert reopened_accounts.get_profile(raw_session).goal == 3
        assert reopened_accounts.consent(raw_session).consent_version == "consent-v2"
        assert reopened.connection.execute(
            "SELECT COUNT(*) FROM consent_events WHERE account_id='student'"
        ).fetchone() == (1,)
        assert reopened.connection.execute(
            "SELECT subject_hash FROM account_identities WHERE account_id='student' "
            "AND provider='google'"
        ).fetchone() == (google_subject_hash(subject),)
        assert reopened.connection.execute(
            "SELECT COUNT(*) FROM sessions WHERE actor_id='student' AND token_digest=?",
            (session_digest,),
        ).fetchone() == (1,)
    finally:
        reopened.close()
