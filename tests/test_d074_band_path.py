"""Learning by band (D074), through the API.

* the learner chooses where they start -- suggested by their latest
  assessment -- and where they aim, and gets a path of the published lessons
  of exactly those bands;
* a class shows each learner's bands; a teacher assigns a published path to
  the learners of their class, which replaces each learner's own path and says
  who assigned it; a learner outside the teacher's classes is refused.
"""

from __future__ import annotations

import pytest
from test_lessons_integration import (  # noqa: F401  (the fixture `m` is used by name)
    account_id,
    login_as,
    m,
    scored,
)

from aicefr.contracts import Band, Criterion

pytestmark = pytest.mark.integration

BANDS = "/api/v1/learn/bands"


def _lessons(plan: dict) -> list[dict]:
    return [item for u in plan["units"] for item in u["lessons"]]


def test_without_an_assessment_the_suggestion_starts_at_a1(m):
    student = login_as(m, "SV-001")
    d = student.get(BANDS).json()
    assert (d["assessed_band"], d["suggested_from"], d["suggested_to"], d["plan"]) == (
        None,
        "A1",
        "A2",
        None,
    )


def test_the_latest_assessment_suggests_where_to_start(m):
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    m.repo.save(scored("as-1", Band.B1, [Criterion.FLUENCY]), "SV-001", "P3", account_id=acc)
    d = student.get(BANDS).json()
    assert (d["assessed_band"], d["suggested_from"], d["suggested_to"]) == ("B1", "B1", "B2")


def test_the_learner_gets_the_lessons_of_the_bands_they_chose(m):
    student = login_as(m, "SV-001")
    r = student.post(BANDS, json={"band_from": "A2", "band_to": "B1"})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert (plan["goal"]["band_from"], plan["goal"]["band_to"]) == ("A2", "B1")
    lessons = _lessons(plan)
    per_band = {b: sum(i["band"] == b for i in lessons) for b in ("A2", "B1")}
    # Each band its own share: one band with many lessons never crowds out the other.
    assert {i["band"] for i in lessons} == {"A2", "B1"} and all(
        1 <= n <= 6 for n in per_band.values()
    )
    assert student.get(BANDS).json()["plan"]["plan_id"] == plan["plan_id"]


def test_the_target_may_not_be_below_the_start(m):
    student = login_as(m, "SV-001")
    assert student.post(BANDS, json={"band_from": "B2", "band_to": "A2"}).status_code == 422
    assert student.post(BANDS, json={"band_from": "B1", "band_to": "B1"}).status_code == 200


def test_a_class_shows_each_learners_bands_and_a_teacher_assigns_a_path(m):
    teacher = login_as(m, "GV-01", "teacher")
    an = login_as(m, "SV-001")
    binh = login_as(m, "SV-002")
    an.post(BANDS, json={"band_from": "A2", "band_to": "B1"})
    made = teacher.post("/api/v1/classes", json={"name": "Lớp B1"}).json()
    teacher.post(
        f"/api/v1/classes/{made['class_id']}/members", json={"people": ["SV-001", "SV-002"]}
    )
    members = {
        r["pseudonym"]: r["bands"]
        for r in teacher.get(f"/api/v1/classes/{made['class_id']}").json()["members"]
    }
    assert members["SV-001"]["band_from"] == "A2" and members["SV-001"]["band_to"] == "B1"
    assert members["SV-002"] is None

    path = next(p for p in teacher.get("/api/v1/teach/paths").json() if p["status"] == "published")
    ids = [account_id(m, "SV-001"), account_id(m, "SV-002")]
    r = teacher.post(f"/api/v1/teach/paths/{path['path_id']}/assign", json={"account_ids": ids})
    assert r.status_code == 200, r.text
    assert r.json()["assigned"] == 2
    for learner in (an, binh):
        plan = learner.get(BANDS).json()["plan"]
        assert plan["goal"]["path_title"] == path["title"]
        assert plan["goal"]["assigned_by"] and _lessons(plan)
    roster = teacher.get(f"/api/v1/classes/{made['class_id']}").json()["members"]
    assert all(r["bands"]["assigned_by"] for r in roster)


def test_a_teacher_assigns_only_to_their_own_learners(m):
    teacher = login_as(m, "GV-01", "teacher", school=False)
    login_as(m, "SV-009", school=False)
    path = next(p for p in teacher.get("/api/v1/teach/paths").json() if p["status"] == "published")
    r = teacher.post(
        f"/api/v1/teach/paths/{path['path_id']}/assign",
        json={"account_ids": [account_id(m, "SV-009")]},
    )
    assert r.status_code == 403
    student = login_as(m, "SV-010")
    assert (
        student.post(
            f"/api/v1/teach/paths/{path['path_id']}/assign", json={"account_ids": ["x"]}
        ).status_code
        == 403
    )


def test_what_comes_next_follows_the_bands_the_learner_chose(m):
    student = login_as(m, "SV-001")
    before = student.get("/api/v1/learn").json()["next"]
    plan = student.post(BANDS, json={"band_from": "B1", "band_to": "B2"}).json()
    first = _lessons(plan)[0]
    after = student.get("/api/v1/learn").json()["next"]
    assert after["lesson_id"] == first["lesson_id"] != before["lesson_id"]
    assert after["basis"] == "band_plan" and "B1 → B2" in after["reason"]
    student.delete("/api/v1/learn/plan")
    assert student.get("/api/v1/learn").json()["next"]["lesson_id"] == before["lesson_id"]


def test_a_unit_has_a_band_inside_its_paths_bands(m):
    teacher = login_as(m, "GV-01", "teacher")
    body = {"title": "Lộ trình B1–B2", "band_from": "B1", "band_to": "B2"}
    pid = teacher.post("/api/v1/teach/paths", json=body).json()["path_id"]
    units = f"/api/v1/teach/paths/{pid}/units"
    assert teacher.post(units, json={"title": "Không band"}).status_code == 422
    assert teacher.post(units, json={"title": "Quá thấp", "band": "A2"}).status_code == 422
    uid = teacher.post(units, json={"title": "Vừa", "band": "B2"}).json()["unit_id"]
    moved = teacher.patch(f"/api/v1/teach/units/{uid}", json={"title": "Vừa", "band": "C1"})
    assert moved.status_code == 422 and "B1–B2" in moved.json()["detail"]
