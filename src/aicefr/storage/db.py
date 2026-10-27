"""Where every repository keeps its documents and rows: MongoDB database (D048)
with SQLite and PostgreSQL compatibility layer for relational repositories.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import threading
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

MONGO_SCHEMES = ("mongodb://", "mongodb+srv://")
POSTGRES_SCHEMES = ("postgresql://", "postgres://")
MOCK_SCHEME = "mongomock://"
DEFAULT_DATABASE = "aicefr"

logger = logging.getLogger(__name__)

# A unique index or constraint refused the write.
IntegrityError = (DuplicateKeyError, sqlite3.IntegrityError)


def now_iso() -> str:
    """The time documents or rows are stamped with: UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def is_server(target: str | Path) -> bool:
    """Whether `target` names a MongoDB server rather than an in-memory store."""
    return str(target).startswith(MONGO_SCHEMES)


def is_postgres(target: str | Path) -> bool:
    return str(target).startswith(POSTGRES_SCHEMES)


# ================================================================= MongoDB

_clients: dict[str, Any] = {}
_clients_lock = threading.Lock()
_warned: set[str] = set()


def _server_client(url: str):
    from pymongo import MongoClient

    with _clients_lock:
        client = _clients.get(url)
        if client is None:
            client = MongoClient(url, serverSelectionTimeoutMS=10_000, tz_aware=False)
            _clients[url] = client
    return client


def _split(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    name = unquote(parts.path.lstrip("/")) or DEFAULT_DATABASE
    query = dict(parse_qsl(parts.query))
    if parts.username and "authSource" not in query and parts.path.strip("/"):
        query["authSource"] = name
    return urlunsplit(parts._replace(path="/", query=urlencode(query))), name


def _mock_client():
    try:
        import mongomock
    except ImportError as e:
        raise RuntimeError(
            "an in-memory store needs mongomock (pip install 'aicefr[dev]');"
            " a deployment sets AICEFR_DB to a mongodb:// URL"
        ) from e
    with _clients_lock:
        client = _clients.get(MOCK_SCHEME)
        if client is None:
            client = mongomock.MongoClient(tz_aware=False)
            _clients[MOCK_SCHEME] = client
    return client


def _mock_name(target: str) -> str:
    if target.startswith(MOCK_SCHEME):
        return target[len(MOCK_SCHEME) :] or DEFAULT_DATABASE
    resolved = str(Path(target).expanduser().resolve())
    if resolved not in _warned:
        _warned.add(resolved)
        logger.warning("store %s is in memory: its documents go when the process ends", target)
    return "m_" + hashlib.sha256(resolved.encode()).hexdigest()[:24]


def database(target: str | Path) -> Database:
    t = str(target)
    if is_server(t):
        server, name = _split(t)
        return _server_client(server)[name]
    if os.getenv("AICEFR_ENV", "development") == "production":
        raise RuntimeError(f"production needs a mongodb:// store, not {t!r}")
    return _mock_client()[_mock_name(t)]


def doc(found: Mapping | None) -> dict | None:
    if found is None:
        return None
    out = dict(found)
    out.pop("_id", None)
    return out


def docs(found: Iterable[Mapping]) -> list[dict]:
    return [doc(d) for d in found]  # type: ignore[misc]


def fields(found: Mapping | None, names: Sequence[str]) -> dict | None:
    if found is None:
        return None
    return {n: found.get(n) for n in names}


def next_id(db: Database, name: str) -> int:
    counter = db["_counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return int(counter["seq"])


IndexSpec = tuple[tuple[str, ...], bool]

_indexed: set[tuple[str, str]] = set()
_indexed_lock = threading.Lock()


def ensure_indexes(db: Database, specs: Mapping[str, Sequence[IndexSpec]], owner: str) -> None:
    key = (db.name + "@" + str(id(db.client)), owner)
    if key in _indexed:
        return
    with _indexed_lock:
        if key in _indexed:
            return
        for collection, indexes in specs.items():
            for keys, unique in indexes:
                db[collection].create_index(
                    [(k, ASCENDING) for k in keys],
                    unique=unique,
                    name=("u_" if unique else "i_") + "_".join(keys),
                )
        _indexed.add(key)


def forget_indexes() -> None:
    with _indexed_lock:
        _indexed.clear()


class MongoStore:
    db_path: str

    @property
    def db(self) -> Database:
        return database(self.db_path)

    @property
    def on_server(self) -> bool:
        return is_server(self.db_path)

    def col(self, name: str) -> Collection:
        return self.db[name]


def collection_exists(target: str | Path, name: str) -> bool:
    return name in database(target).list_collection_names()


# ================================================================= SQL (SQLite & Postgres)


def _scan(sql: str) -> Iterator[tuple[str, bool]]:
    piece, quoted = [], False
    for ch in sql:
        if ch == "'":
            if piece:
                yield "".join(piece), quoted
                piece = []
            yield ch, True
            quoted = not quoted
            continue
        piece.append(ch)
    if piece:
        yield "".join(piece), quoted


_INSERT_OR_IGNORE = re.compile(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b", re.I)
_BEGIN_IMMEDIATE = re.compile(r"^\s*BEGIN\s+IMMEDIATE\s*;?\s*$", re.I)
ADVISORY_LOCK = "SELECT pg_advisory_xact_lock(hashtext(current_schema()))"


def to_postgres(sql: str, has_params: bool) -> str:
    if _BEGIN_IMMEDIATE.match(sql):
        return ADVISORY_LOCK
    ignore = bool(_INSERT_OR_IGNORE.match(sql))
    if ignore:
        sql = _INSERT_OR_IGNORE.sub("INSERT INTO", sql, count=1)
    if has_params:
        out = []
        for piece, quoted in _scan(sql):
            piece = piece.replace("%", "%%")
            out.append(piece if quoted else piece.replace("?", "%s"))
        sql = "".join(out)
    if ignore:
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return sql


_TYPES = (
    (
        re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", re.I),
        "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY",
    ),
    (re.compile(r"\bINTEGER\b", re.I), "BIGINT"),
    (re.compile(r"\bREAL\b", re.I), "DOUBLE PRECISION"),
    (re.compile(r"\bBLOB\b", re.I), "BYTEA"),
)
_CREATE_TABLE = re.compile(r"^\s*CREATE\s+TABLE\b", re.I)


def ddl_to_postgres(stmt: str) -> str:
    for pattern, replacement in _TYPES:
        stmt = pattern.sub(replacement, stmt)
    if _CREATE_TABLE.match(stmt) and not re.search(r"\browid\b", stmt, re.I):
        close = stmt.rstrip().rfind(")")
        stmt = stmt[:close] + ",\n    rowid BIGINT GENERATED ALWAYS AS IDENTITY\n" + stmt[close:]
    return stmt


def split_script(script: str) -> list[str]:
    lines = [line.split("--", 1)[0] for line in script.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


class Row(tuple):
    def __new__(cls, names: Sequence[str], values: Sequence) -> Row:
        row = super().__new__(cls, values)
        row._names = names
        return row

    def keys(self) -> list[str]:
        return [n for n in self._names if n != "rowid"]

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return tuple.__getitem__(self, self._names.index(key))
            except ValueError:
                raise IndexError(f"No item with that key: {key}") from None
        return tuple.__getitem__(self, key)


def _row_factory(cursor):
    names = [d.name for d in cursor.description] if cursor.description else []
    return lambda values: Row(names, values)


_adapters_ready = threading.Lock()
_adapted = False


def _psycopg():
    global _adapted
    try:
        import psycopg
        from psycopg.adapt import Dumper, Loader
    except ImportError as e:
        raise RuntimeError("a PostgreSQL URL needs psycopg: pip install 'aicefr[services]'") from e
    with _adapters_ready:
        if not _adapted:

            class BoolAsInt(Dumper):
                oid = psycopg.adapters.types["int8"].oid

                def dump(self, obj: bool) -> bytes:
                    return b"1" if obj else b"0"

            class PlainNumber(Loader):
                def load(self, data) -> int | float:
                    d = Decimal(bytes(data).decode())
                    return int(d) if d == d.to_integral_value() else float(d)

            psycopg.adapters.register_dumper(bool, BoolAsInt)
            psycopg.adapters.register_loader("numeric", PlainNumber)
            _adapted = True
    return psycopg


def _connection_args(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    schema = query.pop("schema", "public")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
        raise ValueError(f"schema name {schema!r}: lower-case letters, digits and _ only")
    return urlunsplit(parts._replace(query=urlencode(query, quote_via=quote))), schema


class PgConnection:
    def __init__(self, raw) -> None:
        self.raw = raw

    def execute(self, sql: str, params: Sequence | None = ()):
        cur = self.raw.cursor()
        has = bool(params)
        cur.execute(to_postgres(sql, has), tuple(params) if has else None)
        return cur

    def executemany(self, sql: str, seq: Iterable[Sequence]):
        cur = self.raw.cursor()
        cur.executemany(to_postgres(sql, True), [tuple(p) for p in seq])
        return cur

    def executescript(self, script: str) -> None:
        for stmt in split_script(script):
            self.raw.execute(ddl_to_postgres(stmt))


_schemas_made: set[tuple[str, str]] = set()
POOL_SIZE = 8
_pool: dict[str, list] = {}
_pool_lock = threading.Lock()


def _take(dsn: str):
    with _pool_lock:
        idle = _pool.get(dsn)
        while idle:
            raw = idle.pop()
            if not raw.closed:
                return raw
    return _psycopg().connect(dsn, row_factory=_row_factory)


def _give_back(dsn: str, raw) -> None:
    if raw.closed or raw.info.transaction_status != 0:
        raw.close()
        return
    with _pool_lock:
        idle = _pool.setdefault(dsn, [])
        if len(idle) < POOL_SIZE:
            idle.append(raw)
            return
    raw.close()


def _ready(dsn: str, schema: str):
    psycopg = _psycopg()
    raw = _take(dsn)
    try:
        raw.execute(f"SET search_path TO {schema}")
    except psycopg.OperationalError:
        raw.close()
        raw = psycopg.connect(dsn, row_factory=_row_factory)
        raw.execute(f"SET search_path TO {schema}")
    return raw


@contextmanager
def _pg_connect(url: str) -> Iterator[PgConnection]:
    psycopg = _psycopg()
    dsn, schema = _connection_args(url)
    raw = _ready(dsn, schema)
    try:
        if (dsn, schema) not in _schemas_made:
            found = raw.execute(
                "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)
            ).fetchone()
            if not found:
                try:
                    raw.execute(f"CREATE SCHEMA {schema}")
                except psycopg.errors.DuplicateSchema:
                    raw.rollback()
            raw.commit()
            _schemas_made.add((dsn, schema))
            raw.execute(f"SET search_path TO {schema}")
        yield PgConnection(raw)
        raw.commit()
    except BaseException:
        if not raw.closed:
            try:
                raw.rollback()
            except psycopg.Error:
                raw.close()
        raise
    finally:
        _give_back(dsn, raw)


def _errors(name: str) -> tuple[type[Exception], ...]:
    kinds: list[type[Exception]] = [getattr(sqlite3, name)]
    try:
        import psycopg

        kinds.append(
            {
                "IntegrityError": psycopg.IntegrityError,
                "OperationalError": psycopg.errors.UndefinedTable,
            }[name]
        )
    except ImportError:
        pass
    return tuple(kinds)


MissingTable = _errors("OperationalError")


def add_columns(c, table: str, wanted: Iterable[tuple[str, str]]) -> None:
    if isinstance(c, PgConnection):
        rows = c.execute(
            "SELECT column_name AS name FROM information_schema.columns"
            " WHERE table_schema = current_schema() AND table_name = ?",
            (table,),
        )
        columns = {r["name"] for r in rows}
        for name, sql_type in wanted:
            if name not in columns:
                column = f"{name} {ddl_to_postgres(sql_type)}"
                c.raw.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column}")
        return
    columns = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
    for name, sql_type in wanted:
        if name not in columns:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


_shared_anchors: dict[str, sqlite3.Connection] = {}
_shared_lock = threading.Lock()


class SqlStore:
    db_path: str

    @property
    def on_postgres(self) -> bool:
        return is_postgres(self.db_path)

    def _prepare_location(self) -> None:
        if not self.on_postgres and not str(self.db_path).startswith(MOCK_SCHEME):
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self) -> Iterator:
        if self.on_postgres:
            with _pg_connect(self.db_path) as c:
                yield c
            return
        is_mock = str(self.db_path).startswith(MOCK_SCHEME)
        if is_mock:
            mem_name = _mock_name(str(self.db_path))
            uri = f"file:{mem_name}?mode=memory&cache=shared"
            with _shared_lock:
                if mem_name not in _shared_anchors:
                    _shared_anchors[mem_name] = sqlite3.connect(uri, uri=True)
            conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        else:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        if not is_mock:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


Connection = sqlite3.Connection | PgConnection
DbRow = sqlite3.Row | Row


def table_exists(target: str | Path, table: str) -> bool:
    if is_postgres(target):
        with _pg_connect(str(target)) as c:
            row = c.execute("SELECT to_regclass(?) IS NOT NULL", (table,)).fetchone()
            return bool(row[0])
    if not Path(target).is_file():
        return False
    conn = sqlite3.connect(str(target))
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()
