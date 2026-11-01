"""Layer 2 for the learning-evidence features D039 and D041, through the API.

* D039: lesson word marks name the Vietnamese-learner pattern, and the learner
  and the teacher each read a profile of them -- the teacher's without names.
* D041: opening and deciding a review leaves a session (D078 removed the KPI
  built on it, and D042's measurement error).
"""

from __future__ import annotations

import json

import pytest
from dbutil import store
from test_lessons_integration import (  # noqa: F401  (the fixture `m` is used by name)
    REPEAT,
    SAMPLE,
    account_id,
    login_as,
    m,
    record,
    say,
    submit_assessment,
)

pytestmark = pytest.mark.integration

MISHEARD = "I like my neighborhood becau the people are friendly"


def _with_feedback(response_id: str, score: float = 3.4) -> None:
    """Give a submitted response a score and every kind of feedback the report carries."""
    responses = store()["response"]
    report = json.loads(responses.find_one({"response_id": response_id})["report_json"])
    a = report.get("assessment") or {"model_version": "test"}
    a.update(
        overall_0_6=score,
        overall_band="B1",
        comments=[{"criterion": "fluency", "text": "Nói còn ngắt quãng."}],
        priorities=[{"feature_name": "pause_rate", "text": "Bớt ngắt nghỉ.", "impact": 0.4}],
        weakest_criteria=["fluency"],
        evidence=[{"criterion": "fluency", "kind": "pause", "note": "ngắt 2 giây"}],
    )
    report["assessment"] = a
    responses.update_one(
        {"response_id": response_id},
        {"$set": {"overall_0_6": score, "overall_band": "B1", "report_json": json.dumps(report)}},
    )


# ================================================================= D039


def test_lesson_word_marks_name_the_vietnamese_pattern(m):
    say(m, MISHEARD)
    student = login_as(m, "SV-001")
    words = record(student, SAMPLE, REPEAT)["result"]["words"]
    because = next(w for w in words if w["text"] == "because")
    assert (because["said"], because["pattern"]) == ("becau", "final_consonant")
    assert next(w for w in words if w["text"] == "like")["pattern"] is None


def test_learner_profile_counts_errors_against_opportunities(m):
    say(m, MISHEARD)
    student = login_as(m, "SV-001")
    assert student.get("/api/v1/me/pronunciation").json()["steps"] == 0
    for _ in range(2):
        record(student, SAMPLE, REPEAT)

    body = student.get("/api/v1/me/pronunciation").json()
    final = next(p for p in body["patterns"] if p["pattern"] == "final_consonant")
    assert final["errors"] == 2
    assert final["opportunities"] >= body["min_opportunities"]
    assert final["enough"] and 0 < final["rate"] < 1
    assert final["examples"][0]["lesson_id"] == SAMPLE
    assert body["patterns"][0]["pattern"] == "final_consonant"


def test_class_profile_is_for_staff_and_names_nobody(m):
    say(m, MISHEARD)
    for name in ("SV-001", "SV-002"):
        record(login_as(m, name), SAMPLE, REPEAT)
    teacher = login_as(m, "GV-09", "teacher")

    body = teacher.get("/api/v1/teach/pronunciation").json()
    assert body["learners"] == 2
    final = next(p for p in body["patterns"] if p["pattern"] == "final_consonant")
    assert final["errors"] == 2
    assert all(set(e) == {"word", "said"} for e in final["examples"])
    assert "SV-001" not in json.dumps(body) and account_id(m, "SV-001") not in json.dumps(body)
    assert login_as(m, "SV-003").get("/api/v1/teach/pronunciation").status_code == 403


# ================================================================= D041


def test_review_lock_and_decision_leave_a_timed_session(m):
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    _with_feedback(rid)
    store()["response"].update_one({"response_id": rid}, {"$set": {"status": "REVIEW_REQUIRED"}})
    teacher = login_as(m, "GV-01", "teacher")

    assert teacher.post(f"/api/v1/review/{rid}/lock").status_code == 200
    r = teacher.post(f"/api/v1/review/{rid}", json={"new_band": "B1", "reason": "đúng mức"})
    assert r.status_code == 200, r.text
    sessions = m.repo.review_sessions()
    assert len(sessions) == 1
    assert sessions[0]["action"] == "decision" and sessions[0]["decided_at"]
    visits = store()["response"].find_one({"response_id": rid})["review_visits"]
    assert [v["reviewer_id"] for v in visits] == [account_id(m, "GV-01")]
    # The decision carries when the teacher opened the response (D041, D060).
    assert m.repo.review_history(rid)[0].opened_at == visits[0]["opened_at"]
