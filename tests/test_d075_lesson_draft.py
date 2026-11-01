"""A teacher asks the language model for a lesson draft, paid like a learner's AI call (D075).

* the draft fills the "Bài học mới" form -- title, summary, model text, key
  words, free prompt -- and saves nothing; the teacher corrects and creates it;
* key words the model claims but that are not in its own text are dropped;
* on a metered deployment the teacher's own runs pay: the upgrade's price,
  held before the model is asked, charged when it answered, released when not;
* the same daily cap and day's counters as the learners' upgrades;
* learners cannot ask for one.
"""

from __future__ import annotations

import json

import pytest
from test_billing import boot
from test_lessons_integration import account_id, login_as

from aicefr.coach import lesson_draft
from aicefr.coach.upgrade import UpgradeError

DRAFT = {
    "title": "Món ăn quê nhà",
    "summary": "Bài này luyện kể về món ăn quê nhà.",
    "model_text": "My favourite dish is pho. My mother cooks it every Sunday morning.",
    "keywords": ["favourite dish", "cooks", "Sunday", "delicious"],
    "free_prompt": "Kể về một món ăn của quê bạn.",
}
USED = {"input_tokens": 300, "output_tokens": 220}
DRAFT_URL = "/api/v1/teach/lessons/draft"
BODY = {"band": "A2", "criterion": "range", "topic": "món ăn quê nhà"}


class Fake:
    name, model = "gemini", "gemini-3.5-flash-lite"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.asked: list[dict] = []

    def complete_with_usage(self, user, calls, system=None, schema=None):
        calls.requests += 1
        self.asked.append({"user": json.loads(user), "system": system})
        if self.fail:
            raise UpgradeError("nhà cung cấp mô hình trả lỗi 503")
        return json.dumps(DRAFT), dict(USED)


@pytest.fixture
def model(monkeypatch):
    from aicefr.services.core.assessment import coach_api

    fake = Fake()
    monkeypatch.setattr(coach_api, "provider_from", lambda settings, paid=False: fake)
    return fake


# ================================================================= the draft itself


@pytest.mark.unit
def test_keywords_not_in_the_text_are_dropped():
    draft = lesson_draft.parse(json.dumps(DRAFT))
    assert draft.keywords == ["favourite dish", "cooks", "Sunday"]
    assert draft.title == "Món ăn quê nhà" and draft.free_prompt.startswith("Kể về")


@pytest.mark.unit
def test_an_answer_without_a_title_or_text_is_refused():
    for bad in ("không phải json", json.dumps([1]), json.dumps(DRAFT | {"model_text": ""})):
        with pytest.raises(UpgradeError):
            lesson_draft.parse(bad)


@pytest.mark.unit
def test_the_request_names_the_band_and_its_length():
    asked = json.loads(lesson_draft.user_message("B1", "fluency", "du lịch"))
    assert asked == {
        "band": "B1",
        "criterion": "fluency",
        "topic": "du lịch",
        "model_text_words": "90-140",
    }


# ================================================================= through the API


def test_a_teacher_gets_a_draft_for_the_form(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch)
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.get(DRAFT_URL).json() == {"available": True, "price": None}

    r = teacher.post(DRAFT_URL, json=BODY)

    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["band"], d["criterion"], d["title"]) == ("A2", "range", "Món ăn quê nhà")
    assert d["keywords"] == ["favourite dish", "cooks", "Sunday"]
    assert model.asked[0]["system"] == lesson_draft.SYSTEM
    assert model.asked[0]["user"]["topic"] == "món ăn quê nhà"
    admin = login_as(m, "QT-01", "admin")
    today = admin.get("/api/v1/admin/coach").json()["today"]
    assert (today["drafts"], today["upgrades"], today["requests"]) == (1, 0, 1)


def test_learners_cannot_ask_for_a_draft(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-001")
    assert student.post(DRAFT_URL, json=BODY).status_code == 403
    assert student.get(DRAFT_URL).status_code == 403


def test_metered_the_teachers_runs_pay_for_the_draft(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.get(DRAFT_URL).json()["price"] == {"runs": 0.3, "idpoint": 600}

    assert teacher.post(DRAFT_URL, json=BODY).status_code == 200

    ledger = m.core_parts.state["metering"].history(account_id(m, "GV-01"))
    entry = next(e for e in ledger if e["action"] == "lesson_draft")
    assert (entry["state"], entry["charged"]) == ("charged", 300)
    assert (entry["input_tokens"], entry["output_tokens"]) == (300, 220)
    history = teacher.get("/api/v1/me/credits").json()["history"]
    assert any(h["action"] == "lesson_draft" for h in history)


def test_metered_a_failed_draft_costs_nothing(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    teacher = login_as(m, "GV-01", "teacher")
    model.fail = True

    assert teacher.post(DRAFT_URL, json=BODY).status_code == 502

    ledger = m.core_parts.state["metering"].history(account_id(m, "GV-01"))
    entry = next(e for e in ledger if e["action"] == "lesson_draft")
    assert (entry["state"], entry["charged"]) == ("released", 0)


def test_the_daily_cap_counts_drafts_too(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.post(DRAFT_URL, json=BODY).status_code == 200
    r = teacher.post(DRAFT_URL, json=BODY)
    assert r.status_code == 429 and "hệ thống đã dùng hết" in r.json()["detail"]


def test_without_a_language_model_no_draft_is_offered(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_PROVIDER="off")
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.get(DRAFT_URL).json() == {"available": False, "price": None}
    assert teacher.post(DRAFT_URL, json=BODY).status_code == 503
