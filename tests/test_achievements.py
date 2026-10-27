"""Layer 2 -- INTEGRATION: achievements and the week, through the real API and database (D032).

The fixtures of the lesson path are reused (`tests/test_lessons_integration.py`):
SQLite in a temporary file, the real step runner, FastAPI through TestClient,
a fake recogniser and synthetic tones, never a human voice. Attempts on chosen
days are stored straight through the repository, the way the lesson tests
arrange a history; the clock of the lesson API is pinned by `freeze`.

Test case ids (TC-TT-Ixx) are listed in `docs/test/TEST_PLAN_D032.md`; tests
named after an acceptance criterion carry the name given in SRS section 3.9f.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from test_lessons_integration import (  # noqa: F401  (the fixture `m` is used by name)
    FREE,
    KEYWORDS,
    MISSING_TWO,
    READ,
    SAMPLE,
    account_id,
    freeze,
    login_as,
    m,
    record,
    say,
    scored,
    wav,
)

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import StepKind, StepResult
from aicefr.lessons.seed import SAMPLE_PATH_ID

pytestmark = pytest.mark.integration

NOON = datetime(2026, 10, 7, 5, 0, tzinfo=UTC)  # 12:00 on 7 October in Vietnam


def spoke(m, acc: str, days_ago: int, seconds: float = 60.0, **result) -> None:
    """Store one measured attempt at 10:00 Vietnam time, `days_ago` days before NOON."""
    at = (NOON - timedelta(days=days_ago)).replace(hour=3).isoformat(timespec="seconds")
    fields = {"step_id": READ, "kind": StepKind.READ_ALOUD, "passed": True} | result
    m.lessons.add_attempt(acc, SAMPLE, 1, StepResult(speaking_s=seconds, **fields), created_at=at)


def items(client) -> dict[str, dict]:
    r = client.get("/api/v1/me/achievements")
    assert r.status_code == 200, r.text
    return {i["code"]: i for i in r.json()["items"]}


def unlocked(client) -> set[str]:
    return {code for code, i in items(client).items() if i["unlocked"]}


# ================================================================= FR-65 achievements


def test_a_first_recording_is_congratulated_once(m):
    student = login_as(m, "SV-001")

    first = record(student, SAMPLE, KEYWORDS)
    second = record(student, SAMPLE, KEYWORDS)

    assert [a["code"] for a in first["achievements"]] == ["take_1"]
    assert first["achievements"][0]["title"] == "Lượt nói đầu tiên"
    assert second["achievements"] == []
    stored = m.lessons.achievements(account_id(m, "SV-001"))
    assert list(stored) == ["take_1"] and stored["take_1"]["seen_at"] is None


def test_the_list_shows_how_far_each_one_is_without_a_score(m, monkeypatch):
    freeze(monkeypatch, NOON)
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    for ago in (2, 1):
        spoke(m, acc, ago, 50.0)

    r = student.get("/api/v1/me/achievements")

    assert r.status_code == 200
    body = r.json()
    assert (body["total"], body["unlocked"], body["best_streak"]) == (17, 1, 2)
    assert [g["key"] for g in body["groups"]] == [
        "habit",
        "voice",
        "path",
        "persistence",
        "assessment",
    ]
    got = {i["code"]: i for i in body["items"]}
    assert got["take_1"]["unlocked"] and got["take_1"]["value"] == 1
    assert (got["streak_3"]["value"], got["streak_3"]["target"]) == (2, 3)
    assert got["streak_3"]["unlocked"] is False and got["streak_3"]["unlocked_at"] is None
    assert (got["minutes_10"]["value"], got["minutes_10"]["unit"]) == (1, "phút")
    text = r.text.lower()
    for word in ("overall", "band", "score", "điểm", "rank", "xếp hạng"):
        assert word not in text
    # Private, and only to the person signed in.
    assert m.app.state  # the app is up; a client without a session is refused
    from fastapi.testclient import TestClient

    assert TestClient(m.app).get("/api/v1/me/achievements").status_code == 401


def test_new_achievements_are_marked_seen_by_their_owner_only(m):
    student = login_as(m, "SV-001")
    other = login_as(m, "SV-002")
    record(student, SAMPLE, KEYWORDS)
    record(other, SAMPLE, KEYWORDS)
    assert items(student)["take_1"]["new"] is True

    r = student.post("/api/v1/me/achievements/seen", json={"codes": ["take_1", "streak_30"]})

    assert r.json() == {"seen": 1}  # only what is stored and not seen yet
    assert items(student)["take_1"]["new"] is False
    assert items(other)["take_1"]["new"] is True
    assert student.post("/api/v1/me/achievements/seen").json() == {"seen": 0}
    assert other.post("/api/v1/me/achievements/seen").json() == {"seen": 1}
    too_many = {"codes": [f"c{i}" for i in range(40)]}
    assert student.post("/api/v1/me/achievements/seen", json=too_many).status_code == 422


def test_an_achievement_is_never_taken_back(m):
    say(m, "every morning I go to school")
    student = login_as(m, "SV-001")
    miss = record(student, SAMPLE, KEYWORDS)
    assert miss["result"]["passed"] is False
    say(m, "every morning I walk to the bus stop near my home")
    win = record(student, SAMPLE, KEYWORDS)
    assert win["result"]["passed"] is True
    assert {a["code"] for a in win["achievements"]} == {"retry_1"}

    # A teacher finds the pass was not one after all, and the learner deletes
    # the first attempt: the facts no longer hold, the achievements stay.
    teacher = login_as(m, "GV-01", "teacher")
    r = teacher.post(
        f"/api/v1/teach/attempts/{win['attempt_id']}/override",
        json={"passed": False, "note": "Chưa nghe rõ cụm bus stop."},
    )
    assert r.status_code == 200
    assert student.delete(f"/api/v1/learn/attempts/{miss['attempt_id']}").status_code == 200

    got = items(student)
    assert got["retry_1"]["unlocked"] and got["retry_1"]["value"] == 1
    assert got["take_1"]["unlocked"]


def test_habit_achievements_count_vietnam_days_and_the_learners_goal(m, monkeypatch):
    freeze(monkeypatch, NOON)
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    for ago in (8, 4, 3, 2, 0):  # 29 September, then 3, 4, 5 and 7 October
        spoke(m, acc, ago, 60.0)
    # 00:30 on 6 October in Vietnam is still 5 October in UTC. Counted in UTC,
    # the 6th would be a rest day and the streak four days long.
    m.lessons.add_attempt(
        acc,
        SAMPLE,
        1,
        StepResult(step_id=READ, kind=StepKind.READ_ALOUD, passed=True, speaking_s=200.0),
        created_at=datetime(2026, 10, 5, 17, 30, tzinfo=UTC).isoformat(timespec="seconds"),
    )
    assert items(student)["goal_10"]["value"] == 1  # only the 6th reaches 180 seconds

    assert student.patch("/api/v1/me/profile", json={"daily_goal_s": 60}).status_code == 200
    got = items(student)

    assert got["streak_3"]["unlocked"] and got["streak_7"]["value"] == 5
    assert got["goal_1"]["unlocked"] and got["goal_10"]["value"] == 6
    assert got["comeback"]["unlocked"]  # 29 September, then nothing until 3 October


def test_completing_a_lesson_and_a_unit_reach_the_path_achievements(m):
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    first_unit = m.lessons.outline(SAMPLE_PATH_ID)[0]
    lessons = [item["lesson"] for item in first_unit["lessons"]]
    assert len(lessons) > 1

    def complete(lesson) -> list[str]:
        for step in lesson.steps:
            result = StepResult(step_id=step.step_id, kind=step.kind, passed=True, speaking_s=8.0)
            m.lessons.add_attempt(acc, lesson.lesson_id, 1, result)
        return sorted(code for code, i in items(student).items() if i["unlocked"])

    after_one = complete(lessons[0])
    assert "lesson_1" in after_one and "unit_1" not in after_one
    for lesson in lessons[1:]:
        reached = complete(lesson)
    assert "unit_1" in reached and "free_1" in reached
    assert items(student)["lesson_10"]["value"] == len(lessons)


def test_review_attempts_count_towards_the_review_achievement(m, monkeypatch):
    freeze(monkeypatch, datetime(2026, 10, 5, 18, 30, tzinfo=UTC))  # 6 October in Vietnam
    say(m, MISSING_TWO)
    student = login_as(m, "SV-001")
    record(student, SAMPLE, KEYWORDS)
    freeze(monkeypatch, datetime(2026, 10, 7, 3, 0, tzinfo=UTC))
    [entry] = student.get("/api/v1/learn/review").json()["steps"]

    r = student.post(
        "/api/v1/learn/review/attempts",
        files={"audio": ("review.wav", wav(), "audio/wav")},
        data={"review_id": entry["review_id"]},
    )

    assert r.status_code == 200, r.text
    assert "achievements" in r.json()
    assert items(student)["review_10"]["value"] == 1


def test_assessments_with_a_result_count_towards_the_assessment_achievements(m):
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    assert items(student)["assessment_1"]["unlocked"] is False
    for k in range(5):
        m.repo.save(scored(f"as-{k}", Band.B1, [Criterion.RANGE]), "SV-001", "P3", account_id=acc)
        if k == 0:
            assert items(student)["assessment_1"]["unlocked"]

    got = items(student)

    assert got["assessment_5"]["unlocked"]
    progress = student.get("/api/v1/me/progress").json()
    assert progress["trend"]["direction"] != "chua_du_du_lieu"  # the page now speaks of a trend


# ================================================================= FR-66 the week


def test_the_practice_page_shows_the_record_rest_days_and_last_week(m, monkeypatch):
    freeze(monkeypatch, NOON)
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    for ago in (13, 12, 11, 10, 9):  # a five-day streak, long gone
        spoke(m, acc, ago, 30.0)
    for ago in (3, 1, 0):  # the current one, across a rest day two days ago
        spoke(m, acc, ago, 40.0)

    body = student.get("/api/v1/learn").json()
    today = body["today"]

    assert (today["streak"], today["best_streak"]) == (3, 5)
    assert today["rest_days"] == ["2026-10-05"]
    assert today["week_seconds"] == 120.0
    assert today["last_week_seconds"] == 150.0
    # The card: the first take, three days in a row, and the comeback after
    # the gap; the nearest is the week-long streak, 5 of 7.
    card = body["achievements"]
    assert (card["unlocked"], card["total"], card["new"]) == (3, 17, 3)
    assert {x["code"] for x in card["recent"]} == {"take_1", "streak_3", "comeback"}
    assert card["next"]["code"] == "streak_7" and card["next"]["value"] == 5


def test_the_personal_export_and_erasure_cover_achievements(m):
    student = login_as(m, "SV-001")
    bystander = login_as(m, "SV-002")
    record(student, SAMPLE, KEYWORDS)
    record(bystander, SAMPLE, KEYWORDS)

    exported = student.get("/api/v1/me/export.json").json()

    [item] = exported["achievements"]
    assert (item["code"], item["title"], item["seen_at"]) == ("take_1", "Lượt nói đầu tiên", None)
    assert "achievements" in exported["fields"]
    admin = login_as(m, "AD-01", "admin")
    erased = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert erased.status_code == 200
    assert m.lessons.achievements(account_id(m, "SV-001")) == {}
    assert list(m.lessons.achievements(account_id(m, "SV-002"))) == ["take_1"]
