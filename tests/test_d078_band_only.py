"""Bands, not research tools and not exam parts (D078).

* where a score sits inside its band, in thirds, with the band above;
* a learner's report and progress carry that position, so the pages show the
  band and not the 0-6 number;
* the class statistics go by the band of the prompt answered;
* a submission names its prompt; the blind rating, the feedback study, the
  research export and the old practice home are gone.
"""

from __future__ import annotations

import json

import pytest
from dbutil import store
from test_lessons_integration import (  # noqa: F401  (the fixture `m` is used by name)
    login_as,
    m,
    submit_assessment,
)

from aicefr.scoring.band_map import DEFAULT_THRESHOLDS, position


def _score(response_id: str, score: float, band: str) -> None:
    responses = store()["response"]
    report = json.loads(responses.find_one({"response_id": response_id})["report_json"])
    a = report.get("assessment") or {"model_version": "test"}
    a.update(overall_0_6=score, overall_band=band)
    report["assessment"] = a
    responses.update_one(
        {"response_id": response_id},
        {
            "$set": {
                "status": "COMPLETED",
                "overall_0_6": score,
                "overall_band": band,
                "report_json": json.dumps(report),
            }
        },
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("score", "band", "part", "above"),
    [
        (2.8, "B1", "low", "B2"),
        (3.2, "B1", "mid", "B2"),
        (3.7, "B1", "high", "B2"),
        (0.3, "A1", "low", "A2"),
        (6.0, "C2", "low", None),
    ],
)
def test_a_score_is_placed_in_thirds_of_its_band(score, band, part, above):
    p = position(score, None, DEFAULT_THRESHOLDS)
    assert (p["band"], p["part"], p["next"]) == (band, part, above)
    assert 0 <= p["share"] <= 1


@pytest.mark.unit
def test_a_band_a_teacher_moved_has_no_position():
    assert position(3.2, "B2", DEFAULT_THRESHOLDS) is None
    assert position(3.2, "B1", DEFAULT_THRESHOLDS)["band"] == "B1"


@pytest.mark.integration
def test_the_learner_reads_the_band_and_where_they_stand_in_it(m):
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    _score(rid, 3.7, "B1")
    a = student.get(f"/api/v1/responses/{rid}").json()["assessment"]
    assert a["band_position"] == {"band": "B1", "share": 0.95, "part": "high", "next": "B2"}
    progress = student.get("/api/v1/me/progress").json()
    assert progress["results"][0]["band_position"]["part"] == "high"
    assert set(progress["band_thresholds"]) == set(DEFAULT_THRESHOLDS)


@pytest.mark.integration
def test_class_statistics_go_by_the_band_of_the_prompt(m):
    student = login_as(m, "SV-001")
    _score(submit_assessment(student), 3.2, "B1")  # P3 is a B1 prompt: at the band
    _score(submit_assessment(student), 2.0, "A2")  # below it
    stats = login_as(m, "GV-01", "teacher").get("/api/v1/review/stats").json()
    assert "by_task" not in stats
    (b1,) = stats["by_prompt_band"]
    assert (b1["band"], b1["n"], b1["learners"], b1["at"], b1["below"], b1["above"]) == (
        "B1",
        2,
        1,
        1,
        1,
        0,
    )


@pytest.mark.integration
def test_a_submission_names_its_prompt(m):
    student = login_as(m, "SV-001")
    r = student.post("/api/v1/responses", files={"audio": ("a.wav", b"RIFF", "audio/wav")})
    assert r.status_code == 422


@pytest.mark.integration
def test_the_research_tools_and_the_old_practice_home_are_gone(m):
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    for url in (
        "/api/v1/rate/assignments",
        "/api/v1/admin/ratings/batches",
        "/api/v1/admin/studies",
        "/api/v1/admin/export/research.json",
    ):
        assert admin.get(url).status_code == 404, url
    for url in ("/api/v1/me/study", "/api/v1/practice", "/api/v1/practice/tasks/PR-FLU-A2"):
        assert student.get(url).status_code == 404, url
    for page in ("/rate", "/rate/x", "/admin/study"):
        gone = admin.get(page, follow_redirects=False)
        assert (gone.status_code, gone.headers["location"]) == (301, "/"), page
    assert "Chấm mù" not in admin.get("/admin").text


@pytest.mark.integration
def test_a_lesson_is_at_its_units_band(m):
    teacher = login_as(m, "GV-01", "teacher")
    pid = teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình B1"}).json()["path_id"]
    uid = teacher.post(
        f"/api/v1/teach/paths/{pid}/units", json={"title": "Du lịch", "band": "B1"}
    ).json()["unit_id"]
    url = f"/api/v1/teach/units/{uid}/lessons"
    made = teacher.post(url, json={"title": "Đặt phòng", "free_prompt": "Kể một chuyến đi."})
    assert made.status_code == 200, made.text
    lesson = teacher.get(f"/api/v1/teach/lessons/{made.json()['lesson_id']}").json()["lesson"]
    assert lesson["band"] == "B1"  # the unit's, not a built-in default
    other = teacher.post(url, json={"title": "Sai band", "band": "C1"})
    assert other.status_code == 422 and "B1" in other.json()["detail"]
    lesson["band"] = "A2"
    saved = teacher.put(f"/api/v1/teach/lessons/{lesson['lesson_id']}", json=lesson)
    assert saved.status_code == 422


@pytest.mark.unit
def test_migration_11_removes_the_data_of_what_was_removed():
    from aicefr.storage.db import database
    from aicefr.storage.migrations import _d078_research_data

    db = database("mongomock://d078_migration")
    db["rating_batch"].insert_one({"batch_id": "b1", "ratings": []})
    db["study"].insert_one({"study_id": "s1", "participants": []})
    db["response"].insert_one({"response_id": "r1", "machine_seen": [{"account_id": "t"}]})
    db["task"].insert_one({"task_id": "P3", "part": "P3", "band": "B1"})
    db["system"].insert_many(
        [{"key": "assessment.measurement_error"}, {"key": "assessment.coach_tier"}]
    )
    db["path"].insert_one(
        {
            "path_id": "path-sample",
            "title": "Lộ trình mẫu: Nói tiếng Anh A1 → C2",
            "description": "Sáu bậc. Nội dung mẫu, chờ giảng viên Khoa Ngoại ngữ duyệt.",
        }
    )

    _d078_research_data(db, "mongomock://d078_migration")

    assert {"rating_batch", "study"}.isdisjoint(db.list_collection_names())
    assert "machine_seen" not in db["response"].find_one()
    task = db["task"].find_one()
    assert "part" not in task and task["band"] == "B1"
    assert [r["key"] for r in db["system"].find()] == ["assessment.coach_tier"]
    path = db["path"].find_one()
    assert (path["title"], path["description"]) == ("Nói tiếng Anh A1 → C2", "Sáu bậc.")
