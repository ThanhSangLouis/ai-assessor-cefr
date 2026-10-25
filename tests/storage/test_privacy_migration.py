from __future__ import annotations

import hashlib
import shutil
import sqlite3

import pytest

from aicefr.auth.service import AccountRecord
from aicefr.contracts import Actor, ActorRole
from aicefr.storage import migrations
from aicefr.storage.private_files import is_private_file
from aicefr.storage.sqlite import SQLiteStore


def _make_v9_store(data_dir):
    """Build a real v9 fixture; don't downgrade a newer schema in place."""
    data_dir.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore.__new__(SQLiteStore)
    store.data_dir = data_dir
    store.connection = sqlite3.connect(data_dir / "metadata.sqlite3", isolation_level=None)
    store.connection.execute("PRAGMA foreign_keys=ON")
    store._create_v1_schema()
    store._upgrade_v1_to_v2()
    store._upgrade_v2_to_v3()
    store._upgrade_v3_to_v4()
    store.connection.execute(
        "CREATE TABLE schema_migrations("
        "version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, checksum TEXT NOT NULL)"
    )
    for version, group in enumerate(migrations.GROUPS[:5], start=5):
        path = migrations.MIGRATION_DIR / f"{version:03d}_{group}.sql"
        migrations._run_sql(store.connection, path.read_text())
        migrations._verify_group(store.connection, group)
        store.connection.execute(
            "INSERT INTO schema_migrations(version,name,checksum) VALUES(?,?,?)",
            (version, group, migrations._sha256(path)),
        )
    store.connection.execute("PRAGMA user_version=9")
    return store


def _seed_v9_rows(store):
    now = "2026-10-15T00:00:00+00:00"
    connection = store.connection
    store.add_account(
        AccountRecord(Actor(actor_id="fixture-student", role=ActorRole.STUDENT), "hash")
    )
    blob = b"migration fixture audio"
    blob_id = hashlib.sha256(blob).hexdigest()[:32]
    (store.data_dir / "blobs").mkdir(exist_ok=True)
    (store.data_dir / "blobs" / blob_id).write_bytes(blob)
    connection.execute(
        "INSERT INTO responses(response_id,owner_id,task_id,task_version,blob_id,sha256,"
        "size_bytes,status,revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "a" * 32,
            "fixture-student",
            "task-1",
            "v1",
            blob_id,
            hashlib.sha256(blob).hexdigest(),
            len(blob),
            "COMPLETED",
            1,
            now,
        ),
    )
    connection.execute(
        "INSERT INTO diagnostic_reports(response_id,report_json) VALUES(?,?)",
        ("a" * 32, '{"report":"preserve"}'),
    )
    connection.execute("INSERT INTO billing_plans VALUES('FREE','Free','[]',30,80,1,0)")
    connection.execute(
        "INSERT INTO billing_quotes VALUES('quote-v9','fixture-student','FREE','{}',0,0,0,0,"
        "'VND',?,?)",
        (now, now),
    )
    connection.execute(
        "INSERT INTO billing_orders VALUES('order-v9','quote-v9','fixture-student','PAID',"
        "'sandbox','sandbox','idem-v9',NULL,0,'VND',?,?)",
        (now, now),
    )
    (store.data_dir / "billing-hmac.key").write_bytes(b"K" * 32)
    (store.data_dir / "billing-hmac.key").chmod(0o600)


def test_v9_backup_and_privacy_migration_preserve_rows_and_protected_key(tmp_path, monkeypatch):
    data_dir = tmp_path / "v9-store"
    store = _make_v9_store(data_dir)
    _seed_v9_rows(store)
    backup = migrations.create_pre_migration_backup(store.connection, data_dir, schema_version=9)
    manifest = migrations.json.loads((backup / "manifest.json").read_text())
    assert manifest["schema_version"] == 9
    assert manifest["sensitive_files"] == ["billing-hmac.key"]
    assert "billing-hmac.key" in manifest["files"]
    assert is_private_file(backup / "billing-hmac.key")

    restored = migrations.restore_backup(backup, tmp_path / "restored-v9")
    with sqlite3.connect(restored / "metadata.sqlite3") as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (9,)
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT order_id FROM billing_orders").fetchone() == ("order-v9",)
        assert connection.execute("SELECT report_json FROM diagnostic_reports").fetchone() == (
            '{"report":"preserve"}',
        )
    assert (restored / "billing-hmac.key").read_bytes() == b"K" * 32
    assert is_private_file(restored / "billing-hmac.key")

    broken_migrations = tmp_path / "broken-migrations"
    shutil.copytree(migrations.MIGRATION_DIR, broken_migrations)
    (broken_migrations / "010_privacy.sql").write_text("CREATE TABLE broken (\n")
    original_migrations = migrations.MIGRATION_DIR
    monkeypatch.setattr(migrations, "MIGRATION_DIR", broken_migrations)
    with pytest.raises(RuntimeError, match="incomplete migration SQL"):
        migrations.migrate(store.connection, data_dir)
    assert store.connection.execute("PRAGMA user_version").fetchone() == (9,)
    assert store.connection.execute(
        "SELECT COUNT(*) FROM billing_orders WHERE order_id='order-v9'"
    ).fetchone() == (1,)

    monkeypatch.setattr(migrations, "MIGRATION_DIR", original_migrations)
    migrations.migrate(store.connection, data_dir)
    assert store.connection.execute("PRAGMA user_version").fetchone() == (12,)
    migrations.migrate(store.connection, data_dir)
    store.close()

    reopened = SQLiteStore(data_dir)
    try:
        assert reopened.connection.execute("PRAGMA user_version").fetchone() == (12,)
        assert reopened.connection.execute("SELECT order_id FROM billing_orders").fetchone() == (
            "order-v9",
        )
        assert reopened.connection.execute(
            "SELECT report_json FROM diagnostic_reports WHERE response_id=?", ("a" * 32,)
        ).fetchone() == ('{"report":"preserve"}',)
    finally:
        reopened.close()


def test_v9_migration_refuses_protected_key_symlink_without_copying_target(
    tmp_path, make_symlink_or_skip
):
    data_dir = tmp_path / "v9-symlink-store"
    store = _make_v9_store(data_dir)
    _seed_v9_rows(store)
    key_path = data_dir / "google-flow-hmac.key"
    key_path.unlink(missing_ok=True)
    outside = tmp_path / "outside-key"
    outside.write_bytes(b"do-not-copy-this-key")
    make_symlink_or_skip(key_path, outside)

    with pytest.raises(ValueError, match="protected key file is unsafe"):
        migrations.migrate(store.connection, data_dir)

    assert store.connection.execute("PRAGMA user_version").fetchone() == (9,)
    assert outside.read_bytes() == b"do-not-copy-this-key"
    assert list((data_dir / "backups").glob("schema-v9-*")) == []
    store.close()


def test_v9_migration_with_protected_key_without_getuid_platform_api(tmp_path, monkeypatch):
    data_dir = tmp_path / "v9-no-getuid-store"
    store = _make_v9_store(data_dir)
    _seed_v9_rows(store)
    monkeypatch.delattr(migrations.os, "getuid", raising=False)

    migrations.migrate(store.connection, data_dir)

    assert store.connection.execute("PRAGMA user_version").fetchone() == (12,)
    assert (data_dir / "billing-hmac.key").read_bytes() == b"K" * 32
    store.close()
