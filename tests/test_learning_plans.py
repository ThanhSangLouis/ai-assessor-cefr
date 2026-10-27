"""Layer 2 for the path model (D046), through the API.

A learner asks for a path and keeps it on their practice page; a teacher asks
for a proposal and saves what they keep as a draft path of copies. Only
published lessons ever enter a plan; plans leave with the learner's data.
"""

from __future__ import annotations

import pytest
from test_lessons_integration import (  # noqa: F401  (the fixture `m` is used by name)
    account_id,
    audit_entries,
    login_as,
    m,
    scored,
)

from aicefr.contracts import Band, Criterion

pytestmark = pytest.mark.integration

PLAN = "/api/v1/learn/plan"
COMPOSE = "/api/v1/teach/paths/compose"


def _lessons(plan: dict) -> list[dict]:
    return [item for u in plan["units"] for item in u["lessons"]]


def test_a_learner_gets_a_path_of_published_lessons_with_reasons(m):
    student = login_as(m, "SV-001")
    r = student.post(PLAN, json={"wish": "du lịch, tập trung trôi chảy", "length": 5})
    assert r.status_code == 200, r.text
    plan = r.json()
    lessons = _lessons(plan)
    assert len(lessons) == 5 and plan["lessons_total"] == 5 and plan["lessons_completed"] == 0
    assert plan["goal"]["topics"] == ["travel"] and plan["goal"]["criteria"] == ["fluency"]
    assert all(item["status"] == "new" and item["reasons"] for item in lessons)
    assert any("Du lịch" in reason for item in lessons for reason in item["reasons"])
    for item in lessons:  # every pick opens for the learner
        assert student.get(f"/api/v1/learn/lessons/{item['lesson_id']}").status_code == 200

    again = student.get(PLAN).json()["plan"]
    assert again["plan_id"] == plan["plan_id"]


def test_asking_again_replaces_the_plan_and_closing_it_sets_it_aside(m):
    student = login_as(m, "SV-001")
    first = student.post(PLAN, json={"length": 3}).json()["plan_id"]
    second = student.post(PLAN, json={"wish": "B2", "length": 4}).json()
    assert second["plan_id"] != first
    assert {i["band"] for i in _lessons(second)} == {"B2"}
    assert student.get(PLAN).json()["plan"]["plan_id"] == second["plan_id"]
    assert student.delete(PLAN).json() == {"closed": 1}
    assert student.get(PLAN).json() == {"plan": None}


def test_the_latest_assessment_steers_the_learners_path(m):
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    m.repo.save(scored("as-1", Band.B1, [Criterion.FLUENCY]), "SV-001", "P3", account_id=acc)
    plan = student.post(PLAN, json={"length": 4}).json()
    reasons = [r for item in _lessons(plan) for r in item["reasons"]]
    assert any("yếu nhất" in r for r in reasons)
    assert {i["band"] for i in _lessons(plan)} <= {"B1", "B2"}


def test_a_draft_path_never_reaches_a_learners_plan(m):
    teacher = login_as(m, "GV-01", "teacher")
    pid = teacher.post("/api/v1/teach/paths", json={"title": "Nháp"}).json()["path_id"]
    unit = {"title": "Sân bay", "band": "B1", "topic": "travel"}
    uid = teacher.post(f"/api/v1/teach/paths/{pid}/units", json=unit).json()["unit_id"]
    lid = teacher.post(
        f"/api/v1/teach/units/{uid}/lessons",
        json={"title": "At the airport", "band": "B1", "model_text": "I check in at the airport.",
              "keywords": ["airport", "passport"], "free_prompt": "Tell me about a trip."},
    ).json()["lesson_id"]  # fmt: skip
    assert teacher.post(f"/api/v1/teach/lessons/{lid}/publish").status_code == 200

    student = login_as(m, "SV-001")
    plan = student.post(PLAN, json={"wish": "airport passport", "length": 30}).json()
    assert lid not in [i["lesson_id"] for i in _lessons(plan)]
    proposal = teacher.post(COMPOSE, json={"wish": "airport passport", "length": 5}).json()
    assert lid in [i["lesson_id"] for i in _lessons(proposal)]


def test_a_teacher_saves_the_kept_lessons_as_a_draft_path_of_copies(m):
    teacher = login_as(m, "GV-01", "teacher")
    r = teacher.post(COMPOSE, json={"band_from": "A2", "band_to": "B1", "length": 6})
    assert r.status_code == 200, r.text
    proposal = r.json()
    picked = [i["lesson_id"] for i in _lessons(proposal)]
    assert len(picked) == 6 and proposal["order_model"]["pairs"] > 0
    keep = picked[:4]
    url = f"{COMPOSE}/{proposal['plan_id']}/save"
    saved = teacher.post(url, json={"title": "Lộ trình ghép", "lesson_ids": keep})
    assert saved.status_code == 200, saved.text
    path_id = saved.json()["path_id"]
    assert saved.json()["lessons"] == 4

    path = next(p for p in teacher.get("/api/v1/teach/paths").json() if p["path_id"] == path_id)
    assert path["status"] == "draft" and path["band_from"] == "A2"
    copies = [lesson for u in path["units"] for lesson in u["lessons"]]
    assert len(copies) == 4 and not set(c["lesson_id"] for c in copies) & set(picked)
    originals = {i["lesson_id"]: i["title"] for i in _lessons(proposal)}
    assert [c["title"] for c in copies] == [originals[k] for k in keep]

    assert teacher.post(url, json={"title": "Lần hai"}).status_code == 409
    assert audit_entries(m, path_id)[0]["action"] == "lesson.path.compose"


def test_only_staff_compose_and_only_the_author_saves(m):
    student = login_as(m, "SV-001")
    assert student.post(COMPOSE, json={"length": 3}).status_code == 403
    teacher = login_as(m, "GV-01", "teacher")
    plan_id = teacher.post(COMPOSE, json={"length": 3}).json()["plan_id"]
    other = login_as(m, "GV-02", "teacher")
    url = f"{COMPOSE}/{plan_id}/save"
    assert other.post(url, json={"title": "x"}).status_code == 403
    assert teacher.post(url, json={"title": "x", "lesson_ids": ["nope"]}).status_code == 422
    assert teacher.get(PLAN).status_code == 403  # a learner's plan is for learners


def test_plans_are_in_the_export_and_go_with_erasure(m):
    student = login_as(m, "SV-001")
    student.post(PLAN, json={"wish": "ẩm thực", "length": 3})
    exported = student.get("/api/v1/me/export.json").json()
    assert exported["learning_plans"][0]["goal"]["wish"] == "ẩm thực"
    assert "learning_plans" in exported["fields"]

    admin = login_as(m, "AD-01", "admin")
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert r.status_code == 200, r.text
    assert m.app.state.plans.of_account(account_id(m, "SV-001")) == []
