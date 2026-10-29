"""Open a service's store directly, to arrange documents by hand (D048)."""

from __future__ import annotations

from pymongo.database import Database

from aicefr.config import get_settings
from aicefr.storage.db import database


def store() -> Database:
    """This test's core store."""
    return database(get_settings().store("core"))
