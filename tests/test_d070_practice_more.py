"""After the upgraded answer: shadow it, keep its phrases, watch the habits move (D070).

* the phrase book makes one card per phrase of the learner's upgrades, a few
  due a day, moved through Leitner boxes by the learner's own judgement, its
  state kept inside the upgrade it came from;
* the progress view carries the habits the next-band targets name, one series
  each over the scored assessments, with a direction only from three on;
* shadowing is the browser's own voice: the pages load it, the server adds
  nothing.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from dbutil import store
from test_d069_coach import coach_on, scored  # noqa: F401
from test_lessons_integration import login_as, m, submit_assessment  # noqa: F401

from aicefr.coach import phrasebook
from aicefr.report import habits

NOW = datetime(2026, 10, 31, 9, 0, tzinfo=UTC)


def upgrade(rid: str, phrases: list[dict], at: str = "2026-10-30T08:00:00+00:00") -> dict:
    return {
        "response_id": rid,
        "created_at": at,
        "upgraded": "On balance, I prefer the class. It keeps me focused.",
        "phrases": phrases,
    }


# ================================================================= the phrase book, in itself


def test_one_card_per_phrase_with_the_sentence_that_used_it():
    cards = phrasebook.cards(
        [
            upgrade("r1", [{"phrase": "On balance", "meaning_vi": "cân nhắc mọi mặt"}]),
            upgrade(
                "r2", [{"phrase": "on  balance", "meaning_vi": "khác"}, {"phrase": "keeps me"}]
            ),
        ],
        NOW,
    )
    assert [c["key"] for c in cards] == ["on balance", "keeps me"]
    first = cards[0]
    assert first["response_id"] == "r1" and first["meaning_vi"] == "cân nhắc mọi mặt"
    assert first["example"] == "On balance, I prefer the class."
    assert first["box"] == 0 and phrasebook.due_today(cards, NOW)[0]["key"] == "on balance"


def test_remembered_moves_up_a_box_and_forgotten_comes_back_tomorrow():
    card = {"box": 0, "reviews": 0}
    once = phrasebook.reviewed(card, True, NOW)
    assert once["box"] == 1 and once["due"] == "2026-11-01T09:00:00+00:00"
    twice = phrasebook.reviewed({**card, **once}, True, NOW)
    assert twice["box"] == 2 and twice["due"] == "2026-11-03T09:00:00+00:00"
    lost = phrasebook.reviewed({**card, **twice}, False, NOW)
    assert lost["box"] == 1 and lost["reviews"] == 3
    top = phrasebook.reviewed({"box": phrasebook.LAST_BOX, "reviews": 9}, True, NOW)
    assert top["box"] == phrasebook.LAST_BOX


def test_a_day_asks_for_a_few_cards_the_longest_waiting_first():
    phrases = [{"phrase": f"p{i}", "meaning_vi": "x"} for i in range(8)]
    cards = phrasebook.cards([upgrade("r1", phrases)], NOW)
    later = (NOW + timedelta(days=2)).isoformat(timespec="seconds")
    cards[0]["due"] = later
    due = phrasebook.due_today(cards, NOW)
    assert len(due) == phrasebook.PER_DAY and "p0" not in [c["key"] for c in due]
    assert phrasebook.summary(cards, NOW)["due_count"] == 7


# ================================================================= the phrase book, served


def test_the_upgrade_fills_the_phrase_book_and_a_review_moves_the_card(m, coach_on):
    student = login_as(m, "SV-P01")
    rid = submit_assessment(student)
    scored(m, rid)
    assert student.get("/api/v1/me/phrases").json()["total"] == 0
    student.post(f"/api/v1/responses/{rid}/upgrade")

    book = student.get("/api/v1/me/phrases").json()
    assert book["total"] == 1 and book["due"][0]["key"] == "on balance"
    assert "on balance" in book["due"][0]["example"].lower()

    r = student.post("/api/v1/me/phrases/review", json={"key": "On balance", "remembered": True})
    assert r.status_code == 200 and r.json()["box"] == 1
    book = student.get("/api/v1/me/phrases").json()
    assert book["due"] == [] and book["cards"][0]["box"] == 1
    # Kept with the upgrade it came from: erased with the response.
    kept = store()["response"].find_one({"response_id": rid})["coach_upgrade"]["phrases"][0]
    assert kept["box"] == 1 and kept["reviews"] == 1

    missing = student.post("/api/v1/me/phrases/review", json={"key": "nope", "remembered": True})
    assert missing.status_code == 404


def test_nobody_else_reads_or_moves_my_cards(m, coach_on):
    owner = login_as(m, "SV-P02")
    rid = submit_assessment(owner)
    scored(m, rid)
    owner.post(f"/api/v1/responses/{rid}/upgrade")
    other = login_as(m, "SV-P03")
    assert other.get("/api/v1/me/phrases").json()["total"] == 0
    r = other.post("/api/v1/me/phrases/review", json={"key": "on balance", "remembered": True})
    assert r.status_code == 404


def test_the_phrase_book_page_needs_a_sign_in(m):
    from fastapi.testclient import TestClient

    anonymous = TestClient(m.app, follow_redirects=False)
    assert anonymous.get("/phrases").headers["location"] == "/login?next=/phrases"
    student = login_as(m, "SV-P04")
    page = student.get("/phrases").text
    assert 'id="phrase-today"' in page and "shadow.js" in page and "phrases.js" in page


# ================================================================= habits over time


def test_the_progress_view_carries_each_habit_over_the_assessments(m):
    student = login_as(m, "SV-P05")
    rids = [submit_assessment(student) for _ in range(3)]
    for rid in rids:
        scored(m, rid)
    got = student.get("/api/v1/me/progress").json()["habits"]
    assert [h["feature"] for h in got] == list(habits.NAMES)
    pace = got[0]
    assert pace["label"] == "Tốc độ nói" and pace["better"] == "up"
    assert [p["response_id"] for p in pace["points"]] == rids
    assert pace["movement"] is not None and pace["movement"]["delta"] == 0


def test_a_direction_only_from_three_assessments_and_named_against_better():
    rows = [
        {"created_at": f"2026-10-2{i}T00:00:00+00:00", "response_id": f"r{i}",
         "values": {"vad_pause_per_min": v}}
        for i, v in enumerate((9.0, 8.0, 6.0))
    ]  # fmt: skip
    pauses = next(h for h in habits.habit_series(rows) if h["feature"] == "vad_pause_per_min")
    assert pauses["movement"] == {
        "first": 9.0, "last": 6.0, "delta": -3.0, "toward_better": True, "n": 1
    }  # fmt: skip
    assert habits.habit_series(rows[:2])[1]["movement"] is None


def test_the_report_and_the_retell_page_load_the_voice(m):
    student = login_as(m, "SV-P06")
    rid = submit_assessment(student)
    assert "shadow.js" in student.get(f"/report/{rid}").text
    assert "shadow.js" in student.get(f"/retell/{rid}").text


def test_the_report_carries_the_upgrade_and_its_cards_as_the_contract_says(m, coach_on):
    """Response ◆ CoachUpgrade ◆ PhraseCard: the class diagram's parts are real fields."""
    from aicefr.contracts import PhraseCard

    student = login_as(m, "SV-P07")
    rid = submit_assessment(student)
    scored(m, rid)
    assert student.get(f"/api/v1/responses/{rid}").json()["upgrade"] is None
    student.post(f"/api/v1/responses/{rid}/upgrade")
    student.post("/api/v1/me/phrases/review", json={"key": "on balance", "remembered": True})
    up = student.get(f"/api/v1/responses/{rid}").json()["upgrade"]
    assert (up["from_band"], up["to_band"], up["model"]) == ("B1", "B2", "llama-3.3-70b-versatile")
    card = PhraseCard(**up["phrases"][0])
    assert card.box == 1 and not card.is_due("2026-01-01T00:00:00+00:00")
    # Kept beside the stored report, never inside it.
    row = store()["response"].find_one({"response_id": rid})
    assert json.loads(row["report_json"]).get("upgrade") is None and row["coach_upgrade"]
