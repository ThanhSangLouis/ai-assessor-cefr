"""D064: the terms-of-use step is gone; the store forgets it and old links still land."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from aicefr.storage import migrations
from aicefr.storage.db import database


def test_migration_8_drops_the_acceptance_date_and_is_safe_to_repeat():
    db = database(f"mongomock://d064-{uuid.uuid4().hex[:8]}")
    db["account"].insert_many(
        [
            {"account_id": "a", "terms_accepted_at": "2026-10-28T00:00:00+00:00"},
            {"account_id": "b", "terms_accepted_at": None},
            {"account_id": "c"},
        ]
    )
    for _ in range(2):
        migrations._drop_terms(db, "core")
    assert not db["account"].count_documents({"terms_accepted_at": {"$exists": True}})
    assert db["account"].count_documents({}) == 3


def test_a_store_without_accounts_is_left_alone():
    db = database(f"mongomock://d064-{uuid.uuid4().hex[:8]}")
    migrations._drop_terms(db, "learning")
    assert "account" not in db.list_collection_names()


def test_the_old_terms_and_consent_addresses_go_home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr import config

    config.get_settings.cache_clear()
    from aicefr.api import main

    client = TestClient(main.app)
    for path in ("/terms", "/consent"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"] == "/"
    assert client.get("/api/v1/me/terms").status_code in (401, 404, 405)
