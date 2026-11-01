"""The prices of the runs, set by an administrator on the dashboard (D078).

* until the first change, the settings' prices, free runs and packs stand;
* a change is a new version: quotes, free runs and the packs on sale follow it
  at once, and a charge made before keeps the version it was held under;
* impossible prices are refused, and only an administrator sets them.
"""

from __future__ import annotations

import pytest
from test_billing import boot
from test_lessons_integration import account_id, login_as

pytestmark = pytest.mark.integration

PRICES = "/api/v1/admin/prices"
NEW = {
    "first_minute_runs": 1.5,
    "extra_minute_runs": 1.0,
    "practice_factor": 0.5,
    "upgrade_runs": 0.4,
    "idpoint_per_run": 1000,
    "free_runs": 5,
    "packs": [{"runs": 20, "price_vnd": 30000}, {"runs": 5, "price_vnd": 9000}],
}


@pytest.fixture
def m(tmp_path, monkeypatch):
    return boot(
        tmp_path,
        monkeypatch,
        AICEFR_BILLING="on",
        AICEFR_METERING="on",
        AICEFR_CREDIT_PACKS="10:19000",
    )


def test_the_settings_stand_until_an_administrator_changes_them(m):
    admin = login_as(m, "QT-01", "admin")
    d = admin.get(PRICES).json()
    assert d["from_settings"] is True and d["metering"] is True
    assert (d["first_minute_runs"], d["free_runs"]) == (1.0, 3.0)
    assert d["packs"] == [{"runs": 10, "price_vnd": 19000}]


def test_a_change_is_a_new_version_that_everything_follows(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    before = student.get("/api/v1/me/credits/quote?seconds=60").json()
    assert before["runs"] == 1.0 and before["free_runs_left"] == 3.0

    saved = admin.put(PRICES, json=NEW)

    assert saved.status_code == 200, saved.text
    d = saved.json()
    assert (d["version"], d["from_settings"], d["free_runs"]) == ("price-admin-1", False, 5.0)
    assert [p["runs"] for p in d["packs"]] == [5, 20]  # sorted by runs
    after = student.get("/api/v1/me/credits/quote?seconds=60").json()
    assert (after["runs"], after["idpoint"], after["free_runs_left"]) == (1.5, 1500, 5.0)
    packs = student.get("/api/v1/me/credit-packs").json()["packs"]
    assert [(p["runs"], p["price_vnd"]) for p in packs] == [(5, 9000), (20, 30000)]
    again = admin.put(PRICES, json={**NEW, "upgrade_runs": 0.5}).json()
    assert again["version"] == "price-admin-2"
    assert [h["version"] for h in again["history"]] == ["price-admin-1"]


def test_a_charge_keeps_the_price_it_was_held_under(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    r = student.post(
        "/api/v1/responses",
        files={"audio": ("a.wav", _wav(), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    admin.put(PRICES, json=NEW)
    ledger = m.core_parts.state["metering"].history(account_id(m, "SV-001"))
    assert ledger[0]["price_version"] != "price-admin-1"


def test_impossible_prices_are_refused_and_only_admins_set_them(m):
    admin = login_as(m, "QT-01", "admin")
    teacher = login_as(m, "GV-01", "teacher")
    assert admin.put(PRICES, json={**NEW, "practice_factor": 0}).status_code == 422
    assert admin.put(PRICES, json={**NEW, "packs": []}).status_code == 422
    assert admin.put(PRICES, json={**NEW, "free_runs": -1}).status_code == 422
    assert teacher.get(PRICES).status_code == 403
    assert teacher.put(PRICES, json=NEW).status_code == 403


def _wav() -> bytes:
    from test_lessons_integration import wav

    return wav(35.0)
