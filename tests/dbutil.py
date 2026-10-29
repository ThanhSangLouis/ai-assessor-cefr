"""Open a service's store directly, to arrange rows by hand, on SQLite or PostgreSQL alike."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from aicefr.config import get_settings
from aicefr.storage.db import SqlStore


class _Store(SqlStore):
    def __init__(self, target: str) -> None:
        self.db_path = str(target)


@contextmanager
def connect() -> Iterator:
    """A connection to this test's core store, committed on leaving."""
    with _Store(get_settings().store("core"))._conn() as c:
        yield c
