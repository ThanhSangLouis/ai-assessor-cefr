from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aicefr.auth.service import AccountRecord
from aicefr.contracts import Actor, ActorRole
from aicefr.storage import migrations
from aicefr.storage.migrations import restore_backup
from aicefr.storage.providers import (
    CleanupIntent,
    LearningPathRecord,
    PracticeAttemptRecord,
    ProfileRecord,
    QuoteRecord,
    ResearchRatingRecord,
    StudyRecord,
    build_providers,
)
from aicefr.storage.sqlite import SQLiteStore


def _make_v4(data_dir: Path) -> SQLiteStore:
    data_dir.mkdir()
    store = object.__new__(SQLiteStore)
    store.data_dir = data_dir
    store.connection = sqlite3.connect(data_dir / "metadata.sqlite3", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._create_v1_schema()
    store._upgrade_v1_to_v2()
    store._upgrade_v2_to_v3()
    store._upgrade_v3_to_v4()
    store.connection.execute(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES('student','student','hash')"
    )
    store.connection.execute(
        "INSERT INTO sessions VALUES(?,?,?,?,?,?,?)",
        (
            "f" * 64,
            "student",
            "student",
            "2026-10-01T00:00:00+00:00",
            "2026-10-01T00:00:00+00:00",
            "2026-10-02T00:00:00+00:00",
            "2026-10-08T00:00:00+00:00",
        ),
    )
    store.connection.execute(
        "INSERT INTO consents(participant_id,consent_version,state,recorded_at,research_allowed) "
        "VALUES('student','v1','active','2026-10-01T00:00:00+00:00',1)"
    )
    store.connection.execute(
        "INSERT INTO audit VALUES('audit-1','student','fixture_action','object-1',?,NULL)",
        ("2026-10-01T00:00:00+00:00",),
    )
    store.connection.execute(
        """INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,
        size_bytes,status,revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "a" * 32,
            "student",
            "task",
            "v1",
            "b" * 32,
            hashlib.sha256(b"fixture audio").hexdigest(),
            len(b"fixture audio"),
            "COMPLETED",
            2,
            "2026-10-01T00:00:00+00:00",
        ),
    )
    store.connection.execute(
        "INSERT INTO diagnostic_reports(response_id,report_json) VALUES(?,?)",
        ("a" * 32, '{"report":"preserve"}'),
    )
    store.connection.execute(
        "INSERT INTO runtime_settings VALUES(?,?,?,?,?,?)",
        ("fixture", '{"value":1}', 0, "v1", "admin", "2026-10-01T00:00:00+00:00"),
    )
    (data_dir / "blobs").mkdir()
    (data_dir / "blobs" / ("b" * 32)).write_bytes(b"fixture audio")
    return store


def test_w5_v4_migration_preserves_legacy_rows_and_restores_backup(tmp_path):
    data_dir = tmp_path / "existing-data"
    legacy = _make_v4(data_dir)
    legacy.close()

    store = SQLiteStore(data_dir)
    assert store.connection.execute("PRAGMA user_version").fetchone()[0] == 10
    assert store.connection.execute("SELECT actor_id,password_hash FROM accounts").fetchall() == [
        ("student", "hash")
    ]
    assert store.connection.execute("SELECT report_json FROM diagnostic_reports").fetchone() == (
        '{"report":"preserve"}',
    )
    assert store.connection.execute("SELECT state,research_allowed FROM consents").fetchone() == (
        "active",
        1,
    )
    assert store.connection.execute("SELECT token_digest,actor_id FROM sessions").fetchone() == (
        "f" * 64,
        "student",
    )
    assert store.connection.execute("SELECT event_id,action FROM audit").fetchone() == (
        "audit-1",
        "fixture_action",
    )
    backup_path = next((data_dir / "backups").iterdir())
    manifest = json.loads((backup_path / "manifest.json").read_text())
    assert manifest["files"]["blobs/" + "b" * 32] == hashlib.sha256(b"fixture audio").hexdigest()
    store.close()

    restored = restore_backup(backup_path, tmp_path / "restored")
    with sqlite3.connect(restored / "metadata.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("SELECT report_json FROM diagnostic_reports").fetchone() == (
            '{"report":"preserve"}',
        )
    assert (restored / "blobs" / ("b" * 32)).read_bytes() == b"fixture audio"
    migrated_again = SQLiteStore(data_dir)
    assert migrated_again.connection.execute("PRAGMA user_version").fetchone()[0] == 10
    assert migrated_again.connection.execute("SELECT COUNT(*) FROM accounts").fetchone() == (1,)
    assert migrated_again.connection.execute("SELECT COUNT(*) FROM sessions").fetchone() == (1,)
    assert migrated_again.connection.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone() == (6,)
    migrated_again.close()


@pytest.mark.parametrize("failed_group", migrations.GROUPS)
def test_w5_group_failure_rolls_back_entire_v4_upgrade(tmp_path, monkeypatch, failed_group):
    data_dir = tmp_path / "failing-data"
    legacy = _make_v4(data_dir)
    legacy.close()
    original_verify = migrations._verify_group

    def fail_on_group(connection: sqlite3.Connection, group: str) -> None:
        if group == failed_group:
            raise RuntimeError("injected migration failure")
        original_verify(connection, group)

    monkeypatch.setattr(migrations, "_verify_group", fail_on_group)
    with pytest.raises(RuntimeError, match="injected migration failure"):
        SQLiteStore(data_dir)
    with sqlite3.connect(data_dir / "metadata.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM consents").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM diagnostic_reports").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM runtime_settings").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='schema_migrations'"
            ).fetchone()
            is None
        )


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        ("DROP TABLE learning_paths", "migration verification failed"),
        ("DROP INDEX durable_jobs_queue_idx", "schema verification failed"),
        ("DROP TRIGGER consent_events_no_delete", "schema verification failed"),
        ("ALTER TABLE account_profiles DROP COLUMN goal", "schema verification failed"),
        ("UPDATE schema_migrations SET checksum='bad' WHERE version=5", "checksum mismatch"),
    ],
)
def test_w5_current_schema_tamper_is_rejected(tmp_path, statement, message):
    data_dir = tmp_path / "tampered"
    store = SQLiteStore(data_dir)
    store.connection.execute(statement)
    store.close()
    with pytest.raises(RuntimeError, match=message):
        SQLiteStore(data_dir)


def test_w5_current_schema_verifier_preserves_case_sensitive_check_literals(tmp_path):
    data_dir = tmp_path / "case-sensitive-check"
    store = SQLiteStore(data_dir)
    store.connection.execute("PRAGMA writable_schema=ON")
    store.connection.execute(
        "UPDATE sqlite_master SET sql=replace(sql, ?, ?) WHERE name='durable_jobs'",
        ("'queued'", "'QUEUED'"),
    )
    schema_version = store.connection.execute("PRAGMA schema_version").fetchone()[0]
    store.connection.execute(f"PRAGMA schema_version={schema_version + 1}")
    store.connection.execute("PRAGMA writable_schema=OFF")
    store.close()
    with pytest.raises(RuntimeError, match="schema verification failed for durable_jobs"):
        SQLiteStore(data_dir)


def test_w5_concurrent_fresh_initializers_serialize_migrations(tmp_path):
    data_dir = tmp_path / "concurrent"

    def initialize() -> int:
        store = SQLiteStore(data_dir)
        version = store.connection.execute("PRAGMA user_version").fetchone()[0]
        store.close()
        return version

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: initialize(), range(2))) == [10, 10]


def test_w5_restore_rejects_incomplete_or_escaping_manifests(tmp_path):
    data_dir = tmp_path / "backup-source"
    legacy = _make_v4(data_dir)
    legacy.close()
    store = SQLiteStore(data_dir)
    store.close()
    backup = next((data_dir / "backups").iterdir())

    no_database = tmp_path / "no-database-backup"
    shutil.copytree(backup, no_database)
    manifest_path = no_database / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    del manifest["files"]["metadata.sqlite3"]
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="does not include database"):
        restore_backup(no_database, tmp_path / "restore-no-database")

    escaping = tmp_path / "escaping-backup"
    shutil.copytree(backup, escaping)
    manifest_path = escaping / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../outside"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="path is unsafe"):
        restore_backup(escaping, tmp_path / "restore-escaping")

    with pytest.raises(ValueError, match="outside the backup source"):
        restore_backup(backup, backup / "nested-restore")


@pytest.mark.skipif(os.name == "nt", reason="symlink creation needs extra Windows privileges")
def test_w5_backup_and_restore_reject_blob_symlinks(tmp_path):
    data_dir = tmp_path / "symlink-data"
    legacy = _make_v4(data_dir)
    legacy.close()
    blob_path = data_dir / "blobs" / ("b" * 32)
    blob_path.unlink()
    outside = tmp_path / "sensitive-fixture"
    outside.write_bytes(b"private fixture")
    blob_path.symlink_to(outside)
    with pytest.raises(ValueError, match="cannot include symlinks"):
        SQLiteStore(data_dir)


def test_w5_providers_offer_typed_bounded_save_get_contracts(tmp_path):
    store = SQLiteStore(tmp_path / "providers")
    store.add_account(AccountRecord(Actor(actor_id="student", role=ActorRole.STUDENT), "hash"))
    store.add_account(AccountRecord(Actor(actor_id="admin", role=ActorRole.ADMIN), "hash"))
    providers = build_providers(store)
    timestamp = datetime(2026, 10, 1, tzinfo=UTC).isoformat()

    profile = providers.profiles.save(ProfileRecord("student", goal=3, icon="book", color="blue"))
    assert profile.goal == 3
    with pytest.raises(sqlite3.IntegrityError):
        providers.profiles.save(ProfileRecord("student", goal=4))
    with pytest.raises(sqlite3.IntegrityError):
        providers.profiles.save(ProfileRecord("student", icon="contains space"))
    with pytest.raises(sqlite3.IntegrityError):
        providers.profiles.save(ProfileRecord("missing-account", goal=3))
    store.connection.execute(
        "INSERT INTO account_identities VALUES('identity-1','student','google','subject-1',?)",
        (timestamp,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "INSERT INTO account_identities VALUES('identity-2','admin','google','subject-1',?)",
            (timestamp,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "INSERT INTO account_identities VALUES('identity-3','student','google','subject-2',?)",
            (timestamp,),
        )
    store.connection.execute(
        "INSERT INTO consent_events VALUES('consent-1','student','v1','accepted',1,?,'web')",
        (timestamp,),
    )
    with pytest.raises(sqlite3.IntegrityError, match="authorized privacy erasure"):
        store.connection.execute("DELETE FROM consent_events WHERE event_id='consent-1'")

    path = providers.learning.save_path(LearningPathRecord("path-1", "A2 to B1"))
    assert providers.learning.get_path("path-1") == path
    store.connection.execute("INSERT INTO learning_units VALUES('unit-1','path-1','Unit',1)")
    store.connection.execute(
        "INSERT INTO learning_lessons VALUES('lesson-1','unit-1','Lesson',1,?)",
        (timestamp,),
    )
    store.connection.execute(
        "INSERT INTO lesson_versions VALUES('lesson-1',1,'draft','rules-v1',NULL,?)",
        (timestamp,),
    )
    store.connection.execute(
        "INSERT INTO lesson_steps VALUES('lesson-1',1,'step-1','retell',1,'{}')"
    )
    store.connection.execute(
        "UPDATE lesson_versions SET state='published',published_at=? WHERE lesson_id='lesson-1'",
        (timestamp,),
    )
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        store.connection.execute(
            "UPDATE lesson_steps SET payload='{}' WHERE lesson_id='lesson-1' AND step_id='step-1'"
        )
    attempt = PracticeAttemptRecord(
        "attempt-1",
        "student",
        "mission-1",
        "v1",
        "complete",
        {"count": 1},
        {"source": "fixture"},
        timestamp,
        timestamp,
    )
    providers.learning.save_practice_attempt(attempt)
    assert providers.learning.get_practice_attempt("attempt-1") == attempt
    with pytest.raises(sqlite3.IntegrityError):
        providers.learning.save_practice_attempt(
            PracticeAttemptRecord(
                "attempt-orphan",
                "missing-account",
                "mission-1",
                "v1",
                "complete",
                {},
                {},
                timestamp,
                timestamp,
            )
        )

    store.connection.execute(
        "INSERT INTO rating_batches(batch_id,state,seed,criteria_version,created_by,created_at) "
        "VALUES('batch-1','OPEN',1,'v1','admin',?)",
        (timestamp,),
    )
    store.connection.execute(
        "INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,"
        "size_bytes,status,revision,created_at) "
        "VALUES('c','student','task','v1','d','e',1,'COMPLETE',1,?)",
        (timestamp,),
    )
    store.connection.execute(
        "INSERT INTO rating_assignments(assignment_id,batch_id,response_id,blind_token,"
        "ordinal,rater_id_hash,state,created_at) "
        "VALUES('assignment-1','batch-1','c','blind-1',1,'hash','OPEN',?)",
        (timestamp,),
    )
    rating = ResearchRatingRecord(
        "rating-1", "assignment-1", {"range": 4}, 4.5, None, "clear", timestamp
    )
    providers.rating.save_rating(rating)
    assert providers.rating.get_rating("assignment-1") == rating
    with pytest.raises(sqlite3.IntegrityError):
        providers.rating.save_rating(rating)

    study = StudyRecord("study-1", "Feedback", "DRAFT", 42, {"arm": 2}, "admin", timestamp)
    providers.research.save_study(study)
    assert providers.research.get_study("study-1") == study

    store.connection.execute(
        "INSERT INTO billing_plans(plan_code,title,features_json,student_limit,warning_quota) "
        "VALUES('FREE','Free','[]',10,0)"
    )
    quote = QuoteRecord("quote-1", "student", "FREE", {}, 0, 0, 0, 0, "VND", timestamp, timestamp)
    providers.billing.save_quote(quote)
    assert providers.billing.get_quote("quote-1") == quote

    intent = CleanupIntent("blob", "blob-1", 10.0, "student", created_at=5.0)
    assert providers.cleanup.enqueue(intent).resource_id == "blob-1"
    assert providers.cleanup.enqueue(intent).resource_id == "blob-1"
    assert providers.cleanup.pending(now=10.0) == (providers.cleanup.enqueue(intent),)
    store.close()
