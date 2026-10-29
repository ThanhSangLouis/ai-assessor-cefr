"""Layer 2 for the learning-evidence features D039-D042, through the API.

* D039: lesson word marks name the Vietnamese-learner pattern, and the learner
  and the teacher each read a profile of them -- the teacher's without names.
* D040: the feedback study holds feedback back from the score-only arm on the
  server, never from teachers, never after the learner leaves, never after the
  study is closed; erasure takes the learner out of it.
* D041: opening and deciding a review leaves a session, and the KPI reports
  minutes only from enough of them.
* D042: progress is called progress only past the measurement error, and that
  error is either measured from test-retest pairs or typed in with its source.
"""

from __future__ import annotations

import json
import uuid

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


# ================================================================= D040


def _start_study(m, n: int = 4):
    students = {f"SV-{i:03d}": login_as(m, f"SV-{i:03d}") for i in range(1, n + 1)}
    admin = login_as(m, "AD-01", "admin")
    r = admin.post("/api/v1/admin/studies", json={"name": "Thực nghiệm thử", "min_days": 7})
    assert r.status_code == 200, r.text
    study_id = r.json()["study_id"]
    arms = {p["account_id"]: p["arm"] for p in m.studies.participants(study_id)}
    by_arm = {
        arm: next(c for name, c in students.items() if arms[account_id(m, name)] == arm)
        for arm in ("feedback", "score_only")
    }
    return admin, study_id, students, by_arm


def test_study_enrols_students_with_terms_half_in_each_arm(m):
    login_as(m, "SV-NO", terms=False)
    login_as(m, "GV-01", "teacher")
    admin, study_id, students, _ = _start_study(m, n=5)
    people = m.studies.participants(study_id)
    assert {p["account_id"] for p in people} == {account_id(m, s) for s in students}
    assert sorted(sum(p["arm"] == a for p in people) for a in ("feedback", "score_only")) == [2, 3]
    assert admin.post("/api/v1/admin/studies", json={"name": "Lần hai"}).status_code == 409
    audit = [e for e in admin.get("/api/v1/audit").json() if e["action"] == "study.create"]
    assert audit and "seed=" in audit[0]["detail"]


def test_study_needs_enough_students_with_terms(m):
    login_as(m, "SV-001")
    admin = login_as(m, "AD-01", "admin")
    r = admin.post("/api/v1/admin/studies", json={"name": "Quá ít"})
    assert r.status_code == 422 and "ít nhất" in r.json()["detail"]


def test_score_only_arm_gets_the_score_and_nothing_more(m):
    admin, study_id, _, arm = _start_study(m)
    reports = {}
    for name, client in arm.items():
        rid = submit_assessment(client)
        _with_feedback(rid)
        reports[name] = (client, rid)

    client, rid = reports["score_only"]
    body = client.get(f"/api/v1/responses/{rid}").json()
    assert body["feedback_withheld"] is True
    a = body["assessment"]
    assert a["overall_0_6"] == 3.4 and a["overall_band"] == "B1"
    assert a["comments"] == a["priorities"] == a["evidence"] == a["weakest_criteria"] == []

    client, other = reports["feedback"]
    full = client.get(f"/api/v1/responses/{other}").json()
    assert "feedback_withheld" not in full and full["assessment"]["comments"]

    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.get(f"/api/v1/responses/{rid}").json()["assessment"]["comments"]


def test_leaving_the_study_or_closing_it_brings_feedback_back(m):
    admin, study_id, _, arm = _start_study(m)
    client = arm["score_only"]
    rid = submit_assessment(client)
    _with_feedback(rid)
    assert client.get(f"/api/v1/responses/{rid}").json().get("feedback_withheld")

    assert client.post("/api/v1/me/study/withdraw").json() == {"withdrawn": True}
    assert "feedback_withheld" not in client.get(f"/api/v1/responses/{rid}").json()
    assert client.get("/api/v1/me/study").json()["withdrawn"] is True

    other = arm["feedback"]
    closed = admin.post(f"/api/v1/admin/studies/{study_id}/status", json={"status": "closed"})
    assert closed.status_code == 200
    assert other.get("/api/v1/me/study").json() == {"enrolled": False}


def test_feedback_stays_held_back_through_the_survey_and_in_the_export(m):
    """The survey phase still gates: the score-only arm answers without having seen advice."""
    admin, study_id, _, arm = _start_study(m)
    client = arm["score_only"]
    rid = submit_assessment(client)
    _with_feedback(rid)
    status = f"/api/v1/admin/studies/{study_id}/status"
    assert admin.post(status, json={"status": "survey"}).status_code == 200

    assert client.get(f"/api/v1/responses/{rid}").json()["feedback_withheld"] is True
    exported = client.get("/api/v1/me/export.json").json()["responses"]
    item = next(r for r in exported if r["response_id"] == rid)
    assert item["assessment"]["overall_0_6"] == 3.4
    assert item["assessment"]["comments"] == item["assessment"]["priorities"] == []

    assert admin.post(status, json={"status": "closed"}).status_code == 200
    assert "feedback_withheld" not in client.get(f"/api/v1/responses/{rid}").json()


def test_survey_opens_only_in_the_survey_phase_and_checks_answers(m):
    admin, study_id, _, arm = _start_study(m)
    client = arm["feedback"]
    answers = {i["key"]: 4 for i in client.get("/api/v1/me/study").json()["survey_items"]}
    url = "/api/v1/me/study/survey"
    assert client.post(url, json={"answers": answers}).status_code == 409

    status = f"/api/v1/admin/studies/{study_id}/status"
    assert admin.post(status, json={"status": "survey"}).status_code == 200
    assert admin.post(status, json={"status": "survey"}).status_code == 409  # forward only
    assert client.post(url, json={"answers": {**answers, "trusted": 6}}).status_code == 422
    assert client.post(url, json={"answers": {"trusted": 4}}).status_code == 422
    assert client.post(url, json={"answers": answers}).json() == {"saved": True}
    assert client.get("/api/v1/me/study").json()["survey_done"] is True

    report = admin.get(f"/api/v1/admin/studies/{study_id}/report").json()
    assert report["arms"]["feedback"]["survey_responses"] == 1
    assert report["arms"]["feedback"]["survey"]["trusted"] == 4


def test_study_export_carries_codes_not_people(m):
    admin, study_id, students, _ = _start_study(m)
    csv_text = admin.get(f"/api/v1/admin/studies/{study_id}/export.csv").text
    assert csv_text.splitlines()[0].startswith("participant,arm,withdrawn")
    assert "P001" in csv_text
    for name in students:
        assert name not in csv_text and account_id(m, name) not in csv_text
    assert students["SV-001"].get("/api/v1/admin/studies").status_code == 403


def test_erasure_takes_the_learner_out_of_every_study(m):
    admin, study_id, _, _ = _start_study(m)
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert r.status_code == 200, r.text
    left = {p["account_id"] for p in m.studies.participants(study_id)}
    assert account_id(m, "SV-001") not in left and len(left) == 3


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


def test_teacher_kpi_reports_minutes_only_from_enough_sessions(m):
    teacher = login_as(m, "GV-01", "teacher")
    body = teacher.get("/api/v1/review/kpi").json()
    assert body["review_with_machine"] == {"n": 0, "median_minutes": None, "idle_left_out": 0}
    assert body["time_saved"] is None and body["settled_alone"]["ci95"] is None

    for minutes in (2, 3, 4, 5, 6, 45):
        store()["response"].insert_one(
            {
                "response_id": uuid.uuid4().hex,
                "review_visits": [
                    {
                        "reviewer_id": "t",
                        "opened_at": "2026-10-01T10:00:00+00:00",
                        "decided_at": f"2026-10-01T10:{minutes:02d}:00+00:00",
                        "action": "decision",
                    }
                ],
            }
        )
    body = teacher.get("/api/v1/review/kpi").json()
    assert body["review_with_machine"] == {"n": 5, "median_minutes": 4.0, "idle_left_out": 1}
    assert login_as(m, "SV-001").get("/api/v1/review/kpi").status_code == 403


# ================================================================= D042


def test_progress_says_no_error_measured_until_an_admin_sets_one(m):
    student = login_as(m, "SV-001")
    for score in (3.0, 3.0, 3.0, 4.2, 4.2, 4.2):
        _with_feedback(submit_assessment(student), score)
    change = student.get("/api/v1/me/progress").json()["reliable_change"]
    assert change["verdict"] == "chua_co_sai_so" and change["sem_source"] is None

    admin = login_as(m, "AD-01", "admin")
    url = "/api/v1/admin/measurement-error"
    assert admin.post(url, json={"use": "manual", "sem": 0.25}).status_code == 422
    r = admin.post(url, json={"use": "manual", "sem": 0.25, "note": "Pilot thử lại tháng 9"})
    assert r.status_code == 200 and r.json()["source"] == "manual"

    change = student.get("/api/v1/me/progress").json()["reliable_change"]
    assert change["verdict"] == "tien_bo" and change["sem_source"] == "manual"
    assert change["difference"] == 1.2 and change["threshold"] < 1.2
    assert admin.get(url).json()["current"]["note"] == "Pilot thử lại tháng 9"
    assert student.post(url, json={"use": "manual", "sem": 0.1, "note": "x"}).status_code == 403


def test_measured_error_needs_enough_retest_pairs(m, monkeypatch):
    admin = login_as(m, "AD-01", "admin")
    url = "/api/v1/admin/measurement-error"
    r = admin.post(url, json={"use": "retest"})
    assert r.status_code == 422 and "cặp" in r.json()["detail"]

    rows = []
    for i in range(10):
        for hour, score in ((8, 3.0), (9, 3.0 + (0.2 if i % 2 else -0.2))):
            rows.append({"account_id": f"u{i}", "task_id": "P3", "overall_0_6": score,
                         "created_at": f"2026-10-01T{hour:02d}:00:00+00:00"})  # fmt: skip
    monkeypatch.setattr(m.repo, "scored_assessments", lambda *a, **k: rows)
    assert admin.get(url).json()["candidate"]["pairs"] == 10
    body = admin.post(url, json={"use": "retest"}).json()
    assert body["source"] == "retest" and body["pairs"] == 10 and 0.1 < body["sem"] < 0.2
