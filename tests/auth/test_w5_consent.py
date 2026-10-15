from datetime import UTC, datetime

import pytest

from aicefr.auth.accounts import AccountService
from aicefr.auth.errors import AuthorizationError, ValidationError
from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import ActorRole, ConsentState
from aicefr.portal.service import PortalService
from aicefr.portal.tasks import TaskRepository
from aicefr.storage.identity import IdentityRepository
from aicefr.storage.sqlite import SQLiteStore


def test_consent_events_and_withdrawal_propagation_are_atomic(tmp_path):
    store = SQLiteStore(tmp_path / "consent")
    try:
        now = datetime(2026, 10, 1, tzinfo=UTC)
        repository = IdentityRepository(store)
        auth = AuthService(store, store, clock=lambda: now, identity_repository=repository)
        auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass")
        auth.bootstrap_fixture_account("fixture-teacher", ActorRole.TEACHER, "teacher-pass")
        service = AccountService(auth, repository)
        token = auth.login("fixture-student", "student-pass")
        staff = auth.login("fixture-teacher", "teacher-pass")
        with pytest.raises(AuthorizationError):
            service.set_consent(staff, "v1", True)

        service.set_consent(token, "consent-2026-01", True)
        assert service.consent(token).research_allowed is True
        store.connection.execute(
            "INSERT INTO feedback_studies VALUES "
            "('study-1','fixture study','RUNNING',1,'{}','fixture-teacher',?,NULL)",
            (now.isoformat(),),
        )
        store.connection.execute(
            "INSERT INTO study_enrollments VALUES "
            "('enrollment-1','study-1','fixture-student','pseudonym-1','control',?,NULL)",
            (now.isoformat(),),
        )
        consent_service = ConsentService(store, clock=lambda: now)
        actor = auth.resolve(token)
        withdrawn = consent_service.withdraw(actor)

        assert withdrawn.state is ConsentState.WITHDRAWN
        assert withdrawn.research_allowed is False
        assert service.consent(token).state is ConsentState.WITHDRAWN
        enrollment = store.connection.execute(
            "SELECT withdrawn_at FROM study_enrollments WHERE enrollment_id='enrollment-1'"
        ).fetchone()
        assert enrollment[0] == now.isoformat()
        rows = store.connection.execute(
            "SELECT state,research_allowed FROM consent_events ORDER BY recorded_at,rowid"
        ).fetchall()
        assert rows == [("active", 1), ("withdrawn", 0)]
        with pytest.raises(AuthorizationError):
            consent_service.require_active(actor, "consent-2026-01")
    finally:
        store.close()


def test_research_optout_voids_assignments_and_export_without_rewriting_ratings(tmp_path):
    store = SQLiteStore(tmp_path / "research-consent")
    try:
        now = datetime(2026, 10, 1, tzinfo=UTC)
        repository = IdentityRepository(store)
        auth = AuthService(store, store, clock=lambda: now, identity_repository=repository)
        student = auth.bootstrap_fixture_account(
            "fixture-student", ActorRole.STUDENT, "student-pass"
        )
        admin = auth.bootstrap_fixture_account("fixture-admin", ActorRole.ADMIN, "admin-pass")
        service = AccountService(auth, repository)
        student_token = auth.login(student.actor_id, "student-pass")
        admin_token = auth.login(admin.actor_id, "admin-pass")
        service.set_consent(student_token, "v1", True)

        store.connection.execute(
            "INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,"
            "size_bytes,status,revision,created_at) VALUES('" + "c" * 32 + "',?,'task','v1',?,?,1,"
            "'COMPLETED',1,?)",
            (student.actor_id, "b" * 32, "a" * 64, now.isoformat()),
        )
        store.connection.execute(
            "INSERT INTO rating_batches(batch_id,state,seed,criteria_version,created_by,"
            "created_at) "
            "VALUES('batch-1','OPEN',1,'v1',?,?)",
            (admin.actor_id, now.isoformat()),
        )
        for assignment, token, ordinal, state in (
            ("assignment-open", "blind-open", 1, "OPEN"),
            ("assignment-submitted", "blind-submitted", 2, "SUBMITTED"),
        ):
            store.connection.execute(
                "INSERT INTO rating_assignments(assignment_id,batch_id,response_id,blind_token,"
                "ordinal,rater_id_hash,state,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    assignment,
                    "batch-1",
                    "c" * 32,
                    token,
                    ordinal,
                    "opaque-rater",
                    state,
                    now.isoformat(),
                ),
            )
        store.connection.execute(
            "INSERT INTO research_ratings VALUES('rating-1','assignment-submitted','{}',4.5,NULL,"
            "'rationale',?)",
            (now.isoformat(),),
        )
        store.connection.execute(
            "INSERT INTO feedback_studies VALUES('study-1','study','RUNNING',1,'{}',?,?,NULL)",
            (admin.actor_id, now.isoformat()),
        )
        store.connection.execute(
            "INSERT INTO study_enrollments VALUES('enrollment-1','study-1',?,'pseudonym-1',"
            "'control',?,NULL)",
            (student.actor_id, now.isoformat()),
        )

        # Keeping consent active while withdrawing research still removes access and participation.
        service.set_consent(student_token, "v1", False, active=True)
        assert store.connection.execute(
            "SELECT state FROM rating_assignments ORDER BY ordinal"
        ).fetchall() == [("VOID",), ("VOID",)]
        assert store.connection.execute(
            "SELECT withdrawn_at FROM study_enrollments WHERE enrollment_id='enrollment-1'"
        ).fetchone() == (now.isoformat(),)
        assert store.connection.execute(
            "SELECT criteria_json,band_half_step,rationale FROM research_ratings "
            "WHERE rating_id='rating-1'"
        ).fetchone() == ("{}", 4.5, "rationale")
        portal = PortalService(auth, store, TaskRepository(store))
        assert portal.research_export(admin_token, "v1")["row_count"] == 0

        service.set_consent(student_token, "v1", True, active=True)
        assert store.connection.execute(
            "SELECT withdrawn_at FROM study_enrollments WHERE enrollment_id='enrollment-1'"
        ).fetchone() == (now.isoformat(),)
        assert store.connection.execute(
            "SELECT state FROM rating_assignments ORDER BY ordinal"
        ).fetchall() == [("VOID",), ("VOID",)]
        # A fresh explicit opt-in permits export, but never recreates withdrawn participation.
        assert portal.research_export(admin_token, "v1")["row_count"] == 1
    finally:
        store.close()


def test_consent_validation_and_mid_transaction_failure_rollback(tmp_path):
    store = SQLiteStore(tmp_path / "consent-rollback")
    try:
        now = datetime(2026, 10, 1, tzinfo=UTC)
        repository = IdentityRepository(store)
        auth = AuthService(store, store, clock=lambda: now, identity_repository=repository)
        actor = auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-pass")
        service = AccountService(auth, repository)
        token = auth.login(actor.actor_id, "student-pass")
        for version, research_allowed, active in (
            ("", True, True),
            ("v1", 1, True),
            ("v1", True, 1),
        ):
            with pytest.raises(ValidationError):
                service.set_consent(token, version, research_allowed, active)

        store.connection.execute(
            "CREATE TRIGGER fail_consent_event BEFORE INSERT ON consent_events "
            "BEGIN SELECT RAISE(ABORT,'injected consent event failure'); END"
        )
        before = {
            table: store.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("consents", "consent_events", "audit", "activity_events")
        }
        with pytest.raises(Exception, match="injected consent event failure"):
            service.set_consent(token, "v1", True)
        after = {
            table: store.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in before
        }
        assert after == before
        assert store.get_consent(actor.actor_id) is None
    finally:
        store.close()
