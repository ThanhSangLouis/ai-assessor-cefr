"""Where every repository keeps its documents: one MongoDB database (D048).

A repository names its store with one string:

* a URL (`mongodb://user:pass@db:27017/aicefr`, `mongodb+srv://...`) is a
  database on a MongoDB server: what the services use. The database is the
  path of the URL, `aicefr` when the URL names none;
* `mongomock://name` is an in-memory database of that name, for tests;
* anything else -- a path such as `aicefr.db`, as the tests and older settings
  give -- is an in-memory database too, one per path, so two repositories
  opened on the same path in one process see the same documents. It lives as
  long as the process: it is for tests and throwaway runs, never for data
  anybody wants to keep, and saying so is logged once.

Each table of the former SQL schema is a collection of the same name, each row
a document with the same field names, so the repositories still read
`row["pseudonym"]`. A document's `_id` is MongoDB's own and never leaves this
package; it orders documents by insertion where SQLite's `rowid` once did.
What a primary key or a UNIQUE constraint guaranteed, a unique index guarantees
(`ensure_indexes`); an `INTEGER PRIMARY KEY AUTOINCREMENT` is a counter
(`next_id`).

There are no multi-document transactions: a standalone server and the test
double do not have them. Every write that must not race is one conditional
update of one document -- "set RUNNING where it is still QUEUED" -- or an
insert a unique index may refuse, and a change spanning documents makes its
guarding write first, so a lost race leaves nothing half done.

`pymongo` (Apache-2.0) talks to a server; `mongomock` (ISC), needed only for
in-memory stores, is a development dependency.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

MONGO_SCHEMES = ("mongodb://", "mongodb+srv://")
MOCK_SCHEME = "mongomock://"
DEFAULT_DATABASE = "aicefr"

logger = logging.getLogger(__name__)

# A unique index refused the write: the document is there already.
IntegrityError = DuplicateKeyError


def now_iso() -> str:
    """The time documents are stamped with: UTC, to the second."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def is_server(target: str | Path) -> bool:
    """Whether `target` names a MongoDB server rather than an in-memory store."""
    return str(target).startswith(MONGO_SCHEMES)


# ================================================================= clients

_clients: dict[str, Any] = {}
_clients_lock = threading.Lock()
_warned: set[str] = set()


def _server_client(url: str):
    from pymongo import MongoClient

    with _clients_lock:
        client = _clients.get(url)
        if client is None:
            # One client per server per process: it pools its own connections
            # and is safe to share between threads.
            client = MongoClient(url, serverSelectionTimeoutMS=10_000, tz_aware=False)
            _clients[url] = client
    return client


def _split(url: str) -> tuple[str, str]:
    """(the server's URL without a database, the database's name).

    One client per server, not per URL: every test, and every service on one
    machine, names a database of its own on the same server, and a client per
    database would open a pool of connections and monitor threads for each.
    """
    parts = urlsplit(url)
    name = unquote(parts.path.lstrip("/")) or DEFAULT_DATABASE
    query = dict(parse_qsl(parts.query))
    # authSource defaults to the database in the path; keep that meaning once
    # the path is gone, so a user defined in its own database still signs in.
    if parts.username and "authSource" not in query and parts.path.strip("/"):
        query["authSource"] = name
    return urlunsplit(parts._replace(path="/", query=urlencode(query))), name


def _mock_client():
    try:
        import mongomock
    except ImportError as e:  # pragma: no cover - depends on the install
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
    # A path: one database per resolved path. Database names are short and
    # may not hold "/" or ".", so the path is hashed.
    resolved = str(Path(target).expanduser().resolve())
    if resolved not in _warned:
        _warned.add(resolved)
        logger.warning("store %s is in memory: its documents go when the process ends", target)
    return "m_" + hashlib.sha256(resolved.encode()).hexdigest()[:24]


def database(target: str | Path) -> Database:
    """The database `target` names (see the module's docstring).

    Production never runs on an in-memory store: a deployment that lost its
    AICEFR_DB would otherwise start, take submissions, and lose them all at
    the next restart.
    """
    t = str(target)
    if is_server(t):
        server, name = _split(t)
        return _server_client(server)[name]
    if os.getenv("AICEFR_ENV", "development") == "production":
        raise RuntimeError(f"production needs a mongodb:// store, not {t!r}")
    return _mock_client()[_mock_name(t)]


# ================================================================= shared by every repository


def doc(found: Mapping | None) -> dict | None:
    """A document as the repositories hand it out: a plain dict, without `_id`."""
    if found is None:
        return None
    out = dict(found)
    out.pop("_id", None)
    return out


def docs(found: Iterable[Mapping]) -> list[dict]:
    return [doc(d) for d in found]  # type: ignore[misc]


def fields(found: Mapping | None, names: Sequence[str]) -> dict | None:
    """Only `names`, each present: a missing field reads None, as a NULL column did."""
    if found is None:
        return None
    return {n: found.get(n) for n in names}


def next_id(db: Database, name: str) -> int:
    """The next number of the series `name`, 1 first: what AUTOINCREMENT gave.

    One atomic update of one counter document, so two writers never draw the
    same number.
    """
    counter = db["_counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return int(counter["seq"])


IndexSpec = tuple[tuple[str, ...], bool]  # (fields, unique)

_indexed: set[tuple[str, str]] = set()
_indexed_lock = threading.Lock()


def ensure_indexes(db: Database, specs: Mapping[str, Sequence[IndexSpec]], owner: str) -> None:
    """Create the indexes `specs` names, once per database per process.

    Creating an index that exists is a no-op on the server, so two processes
    starting at once agree; doing it once per process only saves round trips.
    """
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
    """Make the next `ensure_indexes` look again: for tests that drop a database."""
    with _indexed_lock:
        _indexed.clear()


class MongoStore:
    """A repository on one database. pymongo's client is thread-safe, so each
    method uses the shared handle; no method keeps state between calls."""

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
    """Whether collection `name` is already in the store at `target`, creating nothing.

    For tools that must not run against the wrong store: opening a repository
    creates its collections, so an empty store looks like a valid one with no
    documents.
    """
    return name in database(target).list_collection_names()
