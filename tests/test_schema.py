"""The frozen, versioned structure of the core store (D045, D048).

A fresh store must equal the committed snapshot `docs/db/schema_core.json`;
a store built by an older release must reach the same structure through the
migrations; every collection must be described in the data dictionary.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from aicefr import db_cli
from aicefr.storage.db import database
from aicefr.storage.migrations import LATEST, MIGRATIONS, applied, migrate, pending, snapshot

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "db" / "schema_core.json"
DICTIONARY = ROOT / "docs" / "db" / "TU_DIEN_DU_LIEU.md"


def test_versions_are_numbered_one_by_one():
    assert [m.version for m in MIGRATIONS] == list(range(1, LATEST + 1))


def test_a_fresh_store_matches_the_committed_snapshot():
    """An index change without a migration and a new snapshot fails here.

    To change the structure: add a Migration, then
    `python -m aicefr.db_cli snapshot > docs/db/schema_core.json`.
    """
    assert db_cli.fresh_snapshot() == SNAPSHOT.read_text(encoding="utf-8")


def test_every_identifier_a_table_had_as_key_is_unique():
    """What the SQL primary keys guaranteed, unique indexes still guarantee."""
    shape = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    # D060: one collection per aggregate root; a part embedded in its root
    # (a review, a rating sheet, a lesson version) needs no key of its own.
    keys = {
        "response": ["response_id"],
        "account": ["account_id"],
        "session": ["token_hash"],
        "task": ["task_id"],
        "order": ["order_id"],
        "license": ["license_id"],
        "rating_batch": ["batch_id"],
        "study": ["study_id"],
        "classroom": ["class_id"],
        "path": ["path_id"],
        "lesson": ["lesson_id"],
        "attempt": ["attempt_id"],
        "learning_plan": ["plan_id"],
        "wallet": ["user_ref"],
        "ledger": ["key", "action"],
        "system": ["key"],
    }
    for name, key in keys.items():
        assert any(i["keys"] == key and i["unique"] for i in shape[name]), name


def test_migrate_is_idempotent_and_records_every_version(tmp_path):
    target = tmp_path / "core.db"
    assert migrate(target) == list(range(1, LATEST + 1))
    assert migrate(target) == []
    assert sorted(applied(target)) == list(range(1, LATEST + 1))
    assert pending(target) == []


def test_a_store_built_by_d044_reaches_the_same_structure(tmp_path):
    """An installation from before D045: collections made by the repositories, no ledger."""
    old = tmp_path / "d044.db"
    MIGRATIONS[0].apply(database(old), str(old))
    assert "learning_plan" not in database(old).list_collection_names()

    assert migrate(old) == list(range(1, LATEST + 1))
    fresh = tmp_path / "fresh.db"
    migrate(fresh)
    assert snapshot(old) == snapshot(fresh)


def test_processes_starting_together_record_each_version_once(tmp_path):
    target = tmp_path / "core.db"
    errors: list[BaseException] = []

    def run():
        try:
            migrate(target)
        except BaseException as e:  # noqa: BLE001 - collected and asserted below
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert sorted(applied(target)) == list(range(1, LATEST + 1))
    assert database(target)["schema_migrations"].count_documents({}) == LATEST


def test_status_says_what_is_pending(tmp_path, capsys):
    target = str(tmp_path / "core.db")
    MIGRATIONS[0].apply(database(target), target)
    assert db_cli.main(["--db", target, "status"]) == 1
    assert "CHƯA áp dụng" in capsys.readouterr().out
    assert db_cli.main(["--db", target, "migrate"]) == 0
    assert db_cli.main(["--db", target, "status"]) == 0


def test_every_collection_is_in_the_data_dictionary():
    text = DICTIONARY.read_text(encoding="utf-8")
    collections = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    missing = [c for c in collections if f"`{c}`" not in text]
    assert missing == []
