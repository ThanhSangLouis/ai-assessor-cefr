from __future__ import annotations

import sqlite3

import pytest

from aicefr.auth.service import AccountRecord
from aicefr.contracts import Actor, ActorRole
from aicefr.storage import migrations
from aicefr.storage.learning import (
    LearningAttemptState,
    LearningRepository,
    LegacyPublishedLessonVersion,
)
from aicefr.storage.migrations import restore_backup
from aicefr.storage.sqlite import SQLiteStore


def _schema_v10(data_dir):
    data_dir.mkdir(parents=True)
    store = SQLiteStore.__new__(SQLiteStore)
    store.data_dir = data_dir
    store.connection = sqlite3.connect(data_dir / "metadata.sqlite3", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._create_v1_schema()
    store._upgrade_v1_to_v2()
    store._upgrade_v2_to_v3()
    store._upgrade_v3_to_v4()
    store.connection.execute(
        "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "checksum TEXT NOT NULL)"
    )
    for version, group in enumerate(migrations.GROUPS[:6], start=5):
        path = migrations.MIGRATION_DIR / f"{version:03d}_{group}.sql"
        migrations._run_sql(store.connection, path.read_text())
        migrations._verify_group(store.connection, group)
        store.connection.execute(
            "INSERT INTO schema_migrations(version,name,checksum) VALUES(?,?,?)",
            (version, group, migrations._sha256(path)),
        )
    store.connection.execute("PRAGMA user_version=10")
    return store


def test_v10_attempts_and_published_lesson_survive_v11_as_explicit_legacy(tmp_path):
    data_dir = tmp_path / "v10"
    store = _schema_v10(data_dir)
    now = "2026-10-15T00:00:00+00:00"
    store.add_account(
        AccountRecord(Actor(actor_id="legacy-student", role=ActorRole.STUDENT), "hash")
    )
    db = store.connection
    db.execute(
        "INSERT INTO learning_paths(path_id,title,state,created_at,updated_at) VALUES(?,?,?,?,?)",
        ("legacy-path", "Legacy path", "published", now, now),
    )
    db.execute(
        "INSERT INTO learning_units(unit_id,path_id,title,ordinal) VALUES(?,?,?,?)",
        ("legacy-unit", "legacy-path", "Legacy unit", 1),
    )
    db.execute(
        "INSERT INTO learning_lessons(lesson_id,unit_id,title,active_version,created_at) "
        "VALUES(?,?,?,?,?)",
        ("legacy-lesson", "legacy-unit", "Legacy lesson title", None, now),
    )
    db.execute(
        "INSERT INTO lesson_versions(lesson_id,version,state,rules_version,"
        "published_at,created_at) "
        "VALUES(?,?,?,?,?,?)",
        ("legacy-lesson", 1, "draft", "rules-old", None, now),
    )
    raw_step = '{"text":"preserve exactly"}'
    db.execute(
        "INSERT INTO lesson_steps(lesson_id,version,step_id,kind,ordinal,payload) "
        "VALUES(?,?,?,?,?,?)",
        ("legacy-lesson", 1, "legacy-step", "repeat", 1, raw_step),
    )
    db.execute(
        "UPDATE lesson_versions SET state='published',published_at=? "
        "WHERE lesson_id=? AND version=1",
        (now, "legacy-lesson"),
    )
    db.execute("UPDATE learning_lessons SET active_version=1 WHERE lesson_id='legacy-lesson'")
    db.execute(
        """INSERT INTO practice_attempts(
            attempt_id,owner_id,mission_id,prompt_version,status,measurements,evidence,
            created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            "legacy-practice",
            "legacy-student",
            "PR-FLU-A2",
            "prompt-old",
            "UNMEASURED",
            '{"x":1}',
            '{"y":2}',
            now,
            now,
        ),
    )
    db.execute(
        """INSERT INTO practice_attempts(
            attempt_id,owner_id,mission_id,prompt_version,status,measurements,evidence,
            created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            "legacy-queued",
            "legacy-student",
            "PR-FLU-A2",
            "prompt-old",
            "QUEUED",
            "{}",
            "{}",
            now,
            now,
        ),
    )
    db.execute(
        """INSERT INTO practice_attempts(
            attempt_id,owner_id,mission_id,prompt_version,status,measurements,evidence,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            "legacy-error",
            "legacy-student",
            "PR-FLU-A2",
            "prompt-old",
            "ERROR",
            '{"technical":"decoder"}',
            '{"keep":true}',
            now,
            now,
        ),
    )
    db.execute(
        """INSERT INTO step_attempts(
            attempt_id,owner_id,lesson_id,lesson_version,step_id,rules_version,status,
            measurements,evidence,teacher_override,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "legacy-step-attempt",
            "legacy-student",
            "legacy-lesson",
            1,
            "legacy-step",
            "rules-old",
            "UNMEASURED",
            '{"a":1}',
            '{"b":2}',
            None,
            now,
        ),
    )
    migrations.migrate(db, data_dir)

    assert db.execute("PRAGMA user_version").fetchone() == (11,)
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert db.execute(
        "SELECT status,measurements,evidence,attempt_state,result_json,reasons_json "
        "FROM practice_attempts WHERE attempt_id='legacy-practice'"
    ).fetchone() == (
        "UNMEASURED",
        '{"x":1}',
        '{"y":2}',
        "LEGACY",
        None,
        '["LEGACY_RESULT_NOT_TYPED"]',
    )
    assert db.execute(
        "SELECT status,measurements,evidence,attempt_state,result_json,reasons_json "
        "FROM step_attempts WHERE attempt_id='legacy-step-attempt'"
    ).fetchone() == (
        "UNMEASURED",
        '{"a":1}',
        '{"b":2}',
        "LEGACY",
        None,
        '["LEGACY_RESULT_NOT_TYPED"]',
    )
    assert db.execute(
        "SELECT payload FROM lesson_steps WHERE lesson_id='legacy-lesson' AND version=1"
    ).fetchone() == (raw_step,)
    lesson = LearningRepository(store).get_lesson("legacy-lesson", version=1)
    assert isinstance(lesson, LegacyPublishedLessonVersion)
    assert lesson.title == "Legacy lesson title"
    assert lesson.band is None and lesson.content_hash is None
    assert lesson.steps == (
        {
            "lesson_id": "legacy-lesson",
            "version": 1,
            "step_id": "legacy-step",
            "kind": "repeat",
            "ordinal": 1,
            "payload": {"text": "preserve exactly"},
        },
    )
    attempt = LearningRepository(store).get_practice_attempt("legacy-student", "legacy-practice")
    assert attempt is not None and attempt.state is LearningAttemptState.LEGACY
    assert attempt.mission is None and attempt.result is None
    # Legacy path metadata has no historical band/content version. It remains
    # in SQLite but is omitted from the typed catalogue rather than fabricated.
    assert LearningRepository(store).list_paths() == ()
    assert db.execute(
        "SELECT status,attempt_state,measurements,evidence FROM practice_attempts "
        "WHERE attempt_id='legacy-error'"
    ).fetchone() == (
        "ERROR",
        "LEGACY",
        '{"technical":"decoder"}',
        '{"keep":true}',
    )
    assert db.execute(
        "SELECT status,attempt_state,result_json FROM practice_attempts "
        "WHERE attempt_id='legacy-queued'"
    ).fetchone() == ("QUEUED", "LEGACY", None)
    backup = next((data_dir / "backups").glob("schema-v10-*"))
    restored = restore_backup(backup, tmp_path / "restored")
    restored_db = sqlite3.connect(restored / "metadata.sqlite3")
    try:
        assert restored_db.execute("PRAGMA user_version").fetchone() == (10,)
        assert restored_db.execute(
            "SELECT status FROM practice_attempts WHERE attempt_id='legacy-error'"
        ).fetchone() == ("ERROR",)
    finally:
        restored_db.close()
    store.close()


def test_v10_upgrade_failure_rolls_back_schema_and_preserves_retryable_backup(
    tmp_path, monkeypatch
):
    data_dir = tmp_path / "failed-v10"
    store = _schema_v10(data_dir)
    db = store.connection
    original_run_sql = migrations._run_sql

    def fail_learning_runtime(connection, sql):
        if "learning_audio_artifacts" in sql:
            raise RuntimeError("injected learning runtime migration failure")
        original_run_sql(connection, sql)

    monkeypatch.setattr(migrations, "_run_sql", fail_learning_runtime)
    try:
        with pytest.raises(RuntimeError, match="injected learning runtime"):
            migrations.migrate(db, data_dir)
        assert db.execute("PRAGMA user_version").fetchone() == (10,)
        assert (
            db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_audio_artifacts'"
            ).fetchone()
            is None
        )
        assert db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone() == (6,)
        assert next((data_dir / "backups").glob("schema-v10-*"))
    finally:
        store.close()
