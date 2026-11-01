"""D083: the practice tasks of D023 are gone, with every attempt at them.

* migration 14 deletes the practice tasks, the responses made on them, their
  review sessions and their recordings, drops `response.purpose` and the
  practice fields of a task, and indexes the tasks on `active`;
* no practice task is seeded and every task listed is an assessment prompt;
* the practice result page and its API answer 404;
* the price list has no practice factor; the ledger keeps its old entries.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from test_billing import boot

from aicefr.metering.pricing import PriceList
from aicefr.storage.db import database
from aicefr.storage.metering_repository import MeteredAction
from aicefr.storage.migrations import MIGRATIONS, migrate
from aicefr.storage.task_repository import TaskRepository

pytestmark = pytest.mark.integration


def test_migration_14_removes_the_practice_tasks_and_their_attempts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "old.db"
    db = database(target)
    for step in MIGRATIONS[:13]:
        step.apply(db, str(target))
    recording = tmp_path / "practice.wav"
    recording.write_bytes(b"RIFF")
    db["task"].insert_many(
        [
            {"task_id": "PR-FLU-A2", "purpose": "practice", "criterion": "fluency"},
            {"task_id": "B1-ABC", "purpose": "assessment", "criterion": None,
             "missions_json": "[]", "tips_json": "[]", "reference_text": None},
        ]
    )  # fmt: skip
    db["task"].create_index([("purpose", 1), ("active", 1)], name="i_purpose_active")
    db["response"].insert_many(
        [
            {"response_id": "p1", "purpose": "practice", "audio_path": str(recording)},
            {"response_id": "a1", "purpose": "assessment"},
        ]
    )
    db["review_session"].insert_one({"response_id": "p1", "lock": None, "visits": []})

    migrate(target)

    assert [r["response_id"] for r in db["response"].find()] == ["a1"]
    assert "purpose" not in db["response"].find_one({"response_id": "a1"})
    assert db["review_session"].count_documents({"response_id": "p1"}) == 0
    assert not recording.exists()
    assert [
        t["task_id"] for t in db["task"].find({"task_id": {"$in": ["PR-FLU-A2", "B1-ABC"]}})
    ] == ["B1-ABC"]
    kept = db["task"].find_one({"task_id": "B1-ABC"})
    assert not {"purpose", "criterion", "missions_json", "tips_json", "reference_text"} & set(kept)
    names = {ix["name"] for ix in db["task"].list_indexes()}
    assert "i_active" in names and "i_purpose_active" not in names


def test_no_practice_task_is_seeded(tmp_path):
    tasks = TaskRepository(tmp_path / "t.db")
    listed = tasks.list_active()
    assert listed and all(not t.task_id.startswith("PR-") for t in listed)
    assert all(t.band is not None for t in listed)


def test_the_practice_routes_are_gone(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    c = TestClient(m.app)
    password = "-".join(["mot", "cau", "dai", "123"])
    body = {"email": "a@example.edu.vn", "full_name": "An", "password": password}
    assert c.post("/api/v1/auth/signup", json=body).status_code == 200
    assert c.get("/api/v1/practice/attempts/x").status_code == 404
    assert c.get("/practice/results/x").status_code == 404


def test_prices_have_no_practice_factor_and_old_entries_still_read():
    assert "practice_factor" not in PriceList().as_dict()
    assert MeteredAction("practice") is MeteredAction.PRACTICE  # entries made before D083
