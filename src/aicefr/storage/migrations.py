"""Additive W5 schema migrations, snapshot and restore helpers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from time import monotonic, sleep

SCHEMA_VERSION = 12
MIGRATION_DIR = Path(__file__).with_name("migrations")
GROUPS = (
    "identity",
    "learning",
    "research",
    "billing",
    "jobs",
    "privacy",
    "learning_runtime",
    "consent_audio_storage",
)


@contextmanager
def migration_lock(data_dir: Path) -> Iterator[None]:
    """Hold an OS lock across preflight, snapshot, apply and verification."""
    path = data_dir / ".migration.lock"
    handle = path.open("a+b")
    descriptor = handle.fileno()
    os.chmod(path, 0o600)
    deadline = monotonic() + 5.0
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            while monotonic() < deadline:
                try:
                    handle.seek(0)
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError:
                    sleep(0.05)
        else:
            import fcntl

            while monotonic() < deadline:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    sleep(0.05)
        if not locked:
            raise TimeoutError("SQLite migration lock is busy")
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
        handle.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_protected_key(path: Path) -> bytes:
    import stat

    info = path.lstat()
    expected_uid = os.getuid() if hasattr(os, "getuid") else None
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or (expected_uid is not None and info.st_uid != expected_uid)
        or info.st_mode & 0o077
    ):
        raise ValueError("protected key file is unsafe")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (expected_uid is not None and opened.st_uid != expected_uid)
            or opened.st_ino != info.st_ino
            or opened.st_dev != info.st_dev
            or opened.st_mode & 0o077
            or opened.st_size > 4096
        ):
            raise ValueError("protected key file is unsafe")
        data = os.read(descriptor, 4097)
        if len(data) != opened.st_size or len(data) > 4096:
            raise ValueError("protected key file is unsafe")
        return data
    finally:
        os.close(descriptor)


def create_pre_migration_backup(
    connection: sqlite3.Connection, data_dir: Path, *, schema_version: int = 4
) -> Path:
    """Snapshot the v4 database and blob tree without overwriting an earlier backup."""
    backups = data_dir / "backups"
    if backups.is_symlink():
        raise ValueError("backup directory cannot be a symlink")
    backups.mkdir(mode=0o700, exist_ok=True)
    os.chmod(backups, 0o700)
    target = backups / f"schema-v{schema_version}-{time.time_ns()}"
    target.mkdir(mode=0o700)
    try:
        database = target / "metadata.sqlite3"
        # This must occur before beginning the migration write transaction.
        with sqlite3.connect(database) as backup:
            connection.backup(backup)
        os.chmod(database, 0o600)
        source_blobs = data_dir / "blobs"
        if source_blobs.is_symlink():
            raise ValueError("blob backup source cannot be a symlink")
        if source_blobs.is_dir():
            if any(item.is_symlink() for item in source_blobs.rglob("*")):
                raise ValueError("blob backup cannot include symlinks")
            shutil.copytree(source_blobs, target / "blobs", copy_function=shutil.copy2)
            for item in (target / "blobs").rglob("*"):
                os.chmod(item, 0o700 if item.is_dir() else 0o600)
        sensitive_files = []
        for filename in ("billing-hmac.key", "google-flow-hmac.key"):
            source_key = data_dir / filename
            if source_key.exists() or source_key.is_symlink():
                data = _read_protected_key(source_key)
                key_target = target / filename
                key_target.write_bytes(data)
                os.chmod(key_target, 0o600)
                sensitive_files.append(filename)
        files = sorted(p for p in target.rglob("*") if p.is_file())
        manifest = {
            "schema_version": schema_version,
            "sensitive_files": sensitive_files,
            "files": {p.relative_to(target).as_posix(): _sha256(p) for p in files},
        }
        manifest_path = target / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        os.chmod(manifest_path, 0o600)
        return target
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise


def restore_backup(source: Path | str, destination: Path | str) -> Path:
    """Verify a backup manifest and restore its database/blob files to a new path."""
    source_input = Path(source).expanduser().absolute()
    destination_input = Path(destination).expanduser().absolute()
    for candidate in (
        source_input,
        *source_input.parents,
        destination_input,
        *destination_input.parents,
    ):
        if candidate.is_symlink():
            raise ValueError("restore paths cannot contain symlinks")
    source_path = source_input.resolve(strict=True)
    destination_path = destination_input.resolve(strict=False)
    if (
        destination_path == source_path
        or destination_path.is_relative_to(source_path)
        or source_path.is_relative_to(destination_path)
    ):
        raise ValueError("restore destination must be outside the backup source")
    if destination_path.exists() and any(destination_path.iterdir()):
        raise FileExistsError("restore destination must be empty")
    manifest_path = source_path / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("backup manifest is missing or unsafe")
    manifest = json.loads(manifest_path.read_text())
    files = manifest.get("files")
    backup_schema = manifest.get("schema_version")
    if (
        isinstance(backup_schema, bool)
        or not isinstance(backup_schema, int)
        or not 4 <= backup_schema <= SCHEMA_VERSION
        or not isinstance(files, dict)
    ):
        raise ValueError("backup manifest is invalid")
    if "metadata.sqlite3" not in files:
        raise ValueError("backup manifest does not include database")
    listed: set[Path] = set()
    for relative, expected in manifest["files"].items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("backup manifest path is unsafe")
        path = source_path / relative_path
        if path.is_symlink() or not path.resolve().is_relative_to(source_path):
            raise ValueError("backup manifest path is unsafe")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or not path.is_file()
            or _sha256(path) != expected
        ):
            raise ValueError("backup checksum verification failed")
        listed.add(relative_path)
    actual = {item.relative_to(source_path) for item in source_path.rglob("*") if item.is_file()}
    if any(item.is_symlink() for item in source_path.rglob("*")):
        raise ValueError("backup contains symlinks")
    actual.discard(Path("manifest.json"))
    if actual != listed:
        raise ValueError("backup manifest file list is incomplete")
    database = sqlite3.connect(
        f"file:{(source_path / 'metadata.sqlite3').as_posix()}?mode=ro", uri=True
    )
    try:
        if database.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("backup database integrity check failed")
        if database.execute("PRAGMA user_version").fetchone()[0] != backup_schema:
            raise ValueError("backup schema version mismatch")
        if database.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("backup foreign-key check failed")
    finally:
        database.close()
    destination_path.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copy2(source_path / "metadata.sqlite3", destination_path / "metadata.sqlite3")
    if (source_path / "blobs").is_dir():
        shutil.copytree(source_path / "blobs", destination_path / "blobs")
        for item in (destination_path / "blobs").rglob("*"):
            os.chmod(item, 0o700 if item.is_dir() else 0o600)
        os.chmod(destination_path / "blobs", 0o700)
    os.chmod(destination_path / "metadata.sqlite3", 0o600)
    for filename in manifest.get("sensitive_files", []):
        if filename not in {"billing-hmac.key", "google-flow-hmac.key"}:
            raise ValueError("backup sensitive file manifest is invalid")
        data = _read_protected_key(source_path / filename)
        target_key = destination_path / filename
        target_key.write_bytes(data)
        os.chmod(target_key, 0o600)
    os.chmod(destination_path, 0o700)
    return destination_path


def _run_sql(connection: sqlite3.Connection, sql: str) -> None:
    statement = ""
    for line in sql.splitlines():
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            if statement.strip():
                connection.execute(statement)
            statement = ""
    if statement.strip():
        raise RuntimeError("incomplete migration SQL")


def _verify_group(connection: sqlite3.Connection, group: str) -> None:
    expected = {
        "identity": {
            "account_profiles",
            "temporary_passwords",
            "session_metadata",
            "account_identities",
            "consent_events",
            "activity_events",
        },
        "learning": {
            "learning_paths",
            "learning_units",
            "learning_lessons",
            "lesson_versions",
            "lesson_steps",
            "practice_attempts",
            "step_attempts",
            "review_items",
            "achievements",
            "streak_days",
            "learning_media",
        },
        "research": {
            "rating_batches",
            "rating_assignments",
            "research_ratings",
            "adjudications",
            "machine_seen",
            "feedback_studies",
            "study_enrollments",
            "study_surveys",
            "review_sessions",
            "sem_configs",
        },
        "billing": {
            "billing_plans",
            "billing_quotes",
            "billing_orders",
            "payment_events",
            "billing_receipts",
            "licenses",
            "entitlements",
        },
        "jobs": {"durable_jobs", "cleanup_intents"},
        "privacy": {"privacy_erasure_links"},
        "learning_runtime": {
            "learning_seed_manifest",
            "learning_audio_artifacts",
            "teacher_override_events",
            "step_review_items",
        },
        "consent_audio_storage": {"consents", "consent_events"},
    }[group]
    actual = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if not expected <= actual:
        raise RuntimeError(f"migration verification failed for {group}")
    if group == "jobs":
        columns = {row[1] for row in connection.execute("PRAGMA table_info(durable_jobs)")}
        required = {
            "job_id",
            "response_id",
            "kind",
            "state",
            "attempt",
            "max_attempts",
            "lease_owner",
            "lease_until",
            "idempotency_key",
            "schema_version",
            "created_at",
            "updated_at",
            "available_at",
            "last_reason",
            "revision",
        }
        if columns != required:
            raise RuntimeError("durable_jobs schema verification failed")
    if group == "consent_audio_storage":
        for table in ("consents", "consent_events"):
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if "audio_storage_allowed" not in columns:
                raise RuntimeError(f"{table} audio consent schema verification failed")


def verify_current_schema(connection: sqlite3.Connection) -> None:
    """Reject incomplete/tampered W5 schema even when user_version is current."""
    ledger = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    if len(ledger) != len(GROUPS):
        raise RuntimeError("incomplete migration ledger")
    for version, group in enumerate(GROUPS, start=5):
        path = MIGRATION_DIR / f"{version:03d}_{group}.sql"
        checksum = _sha256(path)
        row = ledger[version - 5]
        if row != (version, group, checksum):
            raise RuntimeError("migration ledger checksum mismatch")
        _verify_group(connection, group)
    expected = _expected_objects()
    for name, (object_type, sql) in expected.items():
        row = connection.execute(
            "SELECT type,sql FROM sqlite_master WHERE name=?", (name,)
        ).fetchone()
        if row is None or row[0] != object_type or _normalize_sql(row[1]) != _normalize_sql(sql):
            raise RuntimeError(f"migration schema verification failed for {name}")


def _normalize_sql(sql: str) -> str:
    normalized: list[str] = []
    quote: str | None = None
    pending_space = False
    index = 0
    while index < len(sql):
        character = sql[index]
        if quote is not None:
            normalized.append(character)
            if character == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    normalized.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif character in ("'", '"', "`"):
            if pending_space and normalized:
                normalized.append(" ")
            pending_space = False
            quote = character
            normalized.append(character)
        elif character.isspace():
            pending_space = True
        else:
            if pending_space and normalized:
                normalized.append(" ")
            pending_space = False
            normalized.append(character)
        index += 1
    return "".join(normalized)


def _expected_objects() -> dict[str, tuple[str, str]]:
    """Derive the exact W5 table/index/trigger shape from the packaged migrations."""
    expected_connection = sqlite3.connect(":memory:")
    try:
        expected_connection.executescript(
            "CREATE TABLE accounts(actor_id TEXT PRIMARY KEY);"
            "CREATE TABLE sessions(token_digest TEXT PRIMARY KEY);"
            "CREATE TABLE consents(participant_id TEXT PRIMARY KEY, "
            "consent_version TEXT NOT NULL, state TEXT NOT NULL, "
            "recorded_at TEXT NOT NULL, research_allowed INTEGER NOT NULL DEFAULT 0);"
            "CREATE TABLE responses(response_id TEXT PRIMARY KEY);"
            "CREATE TABLE audit (\n"
            "                event_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, "
            "action TEXT NOT NULL,\n"
            "                object_id TEXT NOT NULL, recorded_at TEXT NOT NULL, reason TEXT\n"
            "            );"
            "CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit "
            "BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;"
            "CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit "
            "BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;"
            "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL UNIQUE, checksum TEXT NOT NULL);"
        )
        for version, group in enumerate(GROUPS, start=5):
            _run_sql(
                expected_connection, (MIGRATION_DIR / f"{version:03d}_{group}.sql").read_text()
            )
        rows = expected_connection.execute(
            "SELECT name,type,sql FROM sqlite_master "
            "WHERE type IN ('table','index','trigger') AND sql IS NOT NULL"
        ).fetchall()
        return {
            name: (object_type, sql)
            for name, object_type, sql in rows
            if name not in {"accounts", "sessions", "consents", "responses"}
        }
    finally:
        expected_connection.close()


def migrate(connection: sqlite3.Connection, data_dir: Path, *, lock_held: bool = False) -> None:
    """Apply all pending W5 groups in a single transaction after a v4 backup."""
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA foreign_keys=ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("SQLite foreign keys are required")
    lock_context = nullcontext() if lock_held else migration_lock(data_dir)
    with lock_context:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION or version < 0:
            raise RuntimeError("unsupported SQLite schema version")
        if version < 4:
            raise RuntimeError("legacy migration did not reach schema v4")
        if version == SCHEMA_VERSION:
            verify_current_schema(connection)
            return
        if version == 4:
            _verify_v4_preflight(connection)
        else:
            _verify_migration_prefix(connection, version)
        create_pre_migration_backup(connection, data_dir, schema_version=version)
        connection.execute("BEGIN IMMEDIATE")
        try:
            if version == 4:
                connection.execute(
                    "CREATE TABLE schema_migrations("
                    "version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
                    "checksum TEXT NOT NULL)"
                )
                pending = list(enumerate(GROUPS, start=5))
            else:
                pending = [
                    (migration_version, group)
                    for migration_version, group in enumerate(GROUPS, start=5)
                    if migration_version > version
                ]
            for migration_version, group in pending:
                path = MIGRATION_DIR / f"{migration_version:03d}_{group}.sql"
                sql = path.read_text()
                _run_sql(connection, sql)
                _verify_group(connection, group)
                connection.execute(
                    "INSERT INTO schema_migrations(version,name,checksum) VALUES(?,?,?)",
                    (migration_version, group, _sha256(path)),
                )
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            verify_current_schema(connection)
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("SQLite foreign key verification failed")
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _verify_migration_prefix(connection: sqlite3.Connection, version: int) -> None:
    """Require an exact, checksum-valid ledger before extending a partial schema."""
    if not 5 <= version < SCHEMA_VERSION:
        raise RuntimeError("unsupported partial SQLite schema")
    actual_tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "schema_migrations" not in actual_tables:
        raise RuntimeError("partial schema is missing its migration ledger")
    ledger = connection.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    if len(ledger) != version - 4:
        raise RuntimeError("incomplete migration ledger")
    for expected_version, group in enumerate(GROUPS, start=5):
        if expected_version > version:
            break
        path = MIGRATION_DIR / f"{expected_version:03d}_{group}.sql"
        expected = (expected_version, group, _sha256(path))
        if ledger[expected_version - 5] != expected:
            raise RuntimeError("migration ledger checksum mismatch")
        _verify_group(connection, group)


def _verify_v4_preflight(connection: sqlite3.Connection) -> None:
    required = {
        "accounts": {
            "actor_id",
            "role",
            "password_hash",
            "disabled",
            "failed_attempts",
            "locked_until",
        },
        "sessions": {"token_digest", "actor_id"},
        "consents": {"participant_id", "consent_version", "state", "research_allowed"},
        "responses": {"response_id", "owner_id", "revision", "status", "audio_deleted_at"},
        "diagnostic_reports": {"response_id", "report_json"},
        "runtime_settings": {"key", "payload", "revision"},
    }
    for table, expected_columns in required.items():
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        if not expected_columns <= {row[1] for row in rows}:
            raise RuntimeError(f"schema v4 preflight failed for {table}")
