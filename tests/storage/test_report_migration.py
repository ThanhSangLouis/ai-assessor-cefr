import sqlite3
from datetime import UTC, datetime

from aicefr.storage.sqlite import SQLiteStore


def test_schema_v2_migrates_to_v3_without_losing_existing_response(tmp_path):
    store = object.__new__(SQLiteStore)
    store.connection = sqlite3.connect(":memory:", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._create_v1_schema()
    store._upgrade_v1_to_v2()
    store.connection.execute(
        "INSERT INTO accounts VALUES (?, ?, ?)", ("student", "student", "hash")
    )
    store.connection.execute(
        """INSERT INTO responses (
        response_id, owner_id, task_id, task_version, blob_id, sha256,
        size_bytes, status, status_reason, revision, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "a" * 32,
            "student",
            "task",
            "v1",
            "b" * 32,
            "c" * 64,
            4,
            "QUEUED",
            None,
            1,
            datetime(2026, 10, 2, tzinfo=UTC).isoformat(),
        ),
    )
    assert store.connection.execute("PRAGMA user_version").fetchone()[0] == 2
    store._migrate()
    assert (
        store.connection.execute("PRAGMA user_version").fetchone()[0] == SQLiteStore.SCHEMA_VERSION
    )
    tables = {
        row[0]
        for row in store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"responses", "review_candidates", "review_decisions", "diagnostic_reports"} <= tables
    assert store.get_response("a" * 32).owner_id == "student"
    store.close()


def test_future_schema_is_rejected(tmp_path):
    connection = sqlite3.connect(tmp_path / "metadata.sqlite3")
    connection.execute("PRAGMA user_version=99")
    connection.close()
    try:
        SQLiteStore(tmp_path)
    except RuntimeError as error:
        assert "unsupported SQLite schema" in str(error)
    else:
        raise AssertionError("future schema accepted")
