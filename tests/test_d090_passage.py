"""D090 integration layer: reading a passage written around the words still being said again.

* a passage needs three open words or more; it is for learners only;
* the language model writes it once for a set of words, and reading it again
  costs nothing; the words, the band and nothing else leave the system;
* on a metered deployment a passage costs its own price, charged only when
  the model wrote one with every word, released otherwise;
* a reading is one take of each word: two clear in a row close it, a word not
  clear goes to spaced review;
* without the model the learner's own phrases make a free passage;
* the caps keep the upgrades' share of the free quota, and a learner's own;
* the personal export carries the passages, and erasing a participant forgets them.
"""

from __future__ import annotations

import json

import pytest
from dbutil import store
from test_billing import boot
from test_lessons_integration import account_id, login_as, wav

from aicefr.coach import passage
from aicefr.coach.upgrade import UpgradeError
from aicefr.lessons.model import StepResult, WordMark, WordStatus
from aicefr.lessons.text import normalize_word, split_words
from aicefr.services.core.learning import drill_api

URL = "/api/v1/learn/passage"
USED = {"input_tokens": 340, "output_tokens": 190}
OPEN = [  # (response, word, phrase): the words the learner said again, not yet clear
    ("r-1", "worked", "I worked very hard"),
    ("r-1", "three", "in three cities"),
    ("r-2", "months", "for six months"),
    ("r-2", "worked", "we worked together"),  # the same spelling again: once in a passage
]


class Fake:
    name, model = "gemini", "gemini-3.5-flash-lite"

    def __init__(self) -> None:
        self.fail = False
        self.leave_out: str | None = None
        self.asked: list[dict] = []

    def complete_with_usage(self, user, calls, system=None, schema=None, max_tokens=None):
        calls.requests += 1
        asked = json.loads(user)
        self.asked.append({"user": asked, "system": system, "max_tokens": max_tokens})
        if self.fail:
            raise UpgradeError("nhà cung cấp mô hình trả lỗi 503")
        words = [w for w in asked["words"] if w != self.leave_out]
        text = "Last year " + ", and ".join(f"I said {w} again" for w in words) + "."
        return json.dumps({"text": text}), dict(USED)


@pytest.fixture
def model(monkeypatch):
    from aicefr.services.core.assessment import coach_api

    fake = Fake()
    monkeypatch.setattr(coach_api, "provider_from", lambda settings, paid=False: fake)
    return fake


def open_words(m, pseudonym: str, rows=OPEN) -> None:
    """The learner said these words again once each, and the machine was not sure."""
    drills = m.core_parts.state["drills"]
    me = account_id(m, pseudonym)
    for i, (rid, word, phrase) in enumerate(rows):
        drills.record(me, rid, word, i, phrase, False, None)


@pytest.fixture
def heard(monkeypatch):
    """The speech service, answering which words of the passage it did not hear clearly."""
    unclear: list[dict[str, str | None]] = []

    def measure(step, data, kind, round_index, answers, keep=None):
        assert step.step_id == "drill-passage" and keep is None
        missed = unclear.pop(0)
        marks = []
        for i, w in enumerate(split_words(step.text)):
            tokens = normalize_word(w)
            word = tokens[0] if len(tokens) == 1 else ""
            bad = word in missed
            marks.append(
                WordMark(
                    index=i,
                    text=w,
                    status=WordStatus.UNSURE if bad else WordStatus.HEARD,
                    said=missed.get(word) if bad else None,
                )
            )
        return StepResult(
            step_id=step.step_id, kind=step.kind, passed=True, words=marks, transcript=step.text
        )

    monkeypatch.setattr(drill_api, "_measure", measure)
    return unclear


def read(client, passage_id: str):
    return client.post(
        f"{URL}/{passage_id}/takes", files={"audio": ("t.wav", wav(20.0), "audio/wav")}
    )


def test_a_passage_needs_three_open_words_and_is_for_learners(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-P01")
    open_words(m, "SV-P01", OPEN[:2])
    d = student.get(URL).json()
    assert (d["enough"], d["min_words"], len(d["words"])) == (False, 3, 2)
    r = student.post(URL, json={"source": "model"})
    assert r.status_code == 409 and "ít nhất 3 từ" in r.json()["detail"]
    assert model.asked == []
    teacher = login_as(m, "GV-P01", "teacher")
    assert teacher.get(URL).status_code == 403
    assert 'id="passage"' in student.get("/passage").text


def test_the_model_writes_a_passage_once_and_it_is_read_again_for_free(
    tmp_path, monkeypatch, model
):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-P02")
    open_words(m, "SV-P02")
    d = student.get(URL).json()
    assert [w["word"] for w in d["words"]] == ["worked", "months", "three"]  # latest first
    assert d["enough"] and d["passage"] is None and d["offer"]["available"]

    made = student.post(URL, json={"source": "model"}).json()

    assert (made["source"], made["band"]) == ("model", "B1")
    assert all(passage.places(made["text"], made["words"]).values())
    (asked,) = model.asked
    assert asked["user"] == {
        "band": "B1",
        "words": ["worked", "months", "three"],
        "length_words": "60-90",
    }
    assert asked["system"] == passage.SYSTEM and asked["max_tokens"] == passage.MAX_OUTPUT_TOKENS
    again = student.post(URL, json={"source": "model"}).json()
    assert again["passage_id"] == made["passage_id"] and len(model.asked) == 1
    assert student.get(URL).json()["passage"]["passage_id"] == made["passage_id"]
    admin = login_as(m, "QT-P01", "admin")
    today = admin.get("/api/v1/admin/coach").json()["today"]
    assert (today["passages"], today["upgrades"], today["requests"]) == (1, 0, 1)
    assert (today["input_tokens"], today["output_tokens"]) == (340, 190)


def test_metered_a_passage_costs_its_own_price_and_a_failure_nothing(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    student = login_as(m, "SV-P03")
    open_words(m, "SV-P03")
    assert student.get(URL).json()["offer"]["price"] == {"runs": 0.1, "idpoint": 200}

    made = student.post(URL, json={"source": "model"})
    assert made.status_code == 200, made.text
    model.leave_out = "three"  # the model forgot a word: no passage, no charge
    assert student.post(URL, json={"source": "model", "fresh": True}).status_code == 502
    model.leave_out, model.fail = None, True
    assert student.post(URL, json={"source": "model", "fresh": True}).status_code == 502

    ledger = m.core_parts.state["metering"].history(account_id(m, "SV-P03"))
    entries = [e for e in ledger if e["action"] == "drill_passage"]
    states = sorted((e["state"], e["charged"]) for e in entries)
    assert states == [("charged", 100), ("released", 0), ("released", 0)]
    charged = next(e for e in entries if e["state"] == "charged")
    assert (charged["input_tokens"], charged["output_tokens"]) == (340, 190)
    history = student.get("/api/v1/me/credits").json()["history"]
    assert any(h["action"] == "drill_passage" for h in history)


def test_a_reading_is_one_take_of_each_word(tmp_path, monkeypatch, model, heard):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-P04")
    open_words(m, "SV-P04")
    made = student.post(URL, json={"source": "model"}).json()
    heard += [{"three": "tree"}, {}]

    first = read(student, made["passage_id"]).json()

    verdicts = {w["word"]: w for w in first["words"]}
    assert verdicts["worked"]["passed"] and verdicts["months"]["passed"]
    three = verdicts["three"]
    assert (three["passed"], three["said"], three["drill"]["streak"]) == (False, "tree", 0)
    assert three["review_due"] and verdicts["worked"]["review_due"] is None
    assert verdicts["worked"]["drill"]["streak"] == 1

    second = {w["word"]: w for w in read(student, made["passage_id"]).json()["words"]}
    assert second["worked"]["drill"]["passed"] and second["months"]["drill"]["passed"]
    assert second["three"]["drill"]["streak"] == 1
    mine = student.get("/api/v1/learn/drill").json()
    assert sorted(w["word"] for w in mine["open"]) == ["three", "worked"]  # r-1's worked
    kept = store()["drill_passage"].find_one({"passage_id": made["passage_id"]})
    assert [t["unclear"] for t in kept["takes"]] == [["three"], []]
    assert read(student, "p-nope").status_code == 404


def test_without_the_model_the_learners_phrases_make_a_free_passage(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_PROVIDER="off", AICEFR_METERING="on")
    student = login_as(m, "SV-P05")
    open_words(m, "SV-P05")
    assert student.get(URL).json()["offer"] == {"available": False, "price": None}
    assert student.post(URL, json={"source": "model"}).status_code == 503

    made = student.post(URL, json={"source": "phrases"}).json()

    assert made["source"] == "phrases"
    assert made["text"] == "We worked together. For six months. In three cities."
    ledger = m.core_parts.state["metering"].history(account_id(m, "SV-P05"))
    assert not [e for e in ledger if e["action"] == "drill_passage"]


def test_the_caps_keep_the_upgrades_share_and_the_learners_own(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch, AICEFR_PASSAGE_GLOBAL_DAILY="1", AICEFR_PASSAGE_DAILY="2")
    first = login_as(m, "SV-P06")
    open_words(m, "SV-P06")
    assert first.post(URL, json={"source": "model"}).status_code == 200
    second = login_as(m, "SV-P07")
    open_words(m, "SV-P07")
    r = second.post(URL, json={"source": "model"})
    assert r.status_code == 429 and "số đoạn đọc trong ngày" in r.json()["detail"]

    m = boot(tmp_path, monkeypatch, AICEFR_PASSAGE_GLOBAL_DAILY="150", AICEFR_PASSAGE_DAILY="1")
    third = login_as(m, "SV-P08")
    open_words(m, "SV-P08")
    assert third.post(URL, json={"source": "model"}).status_code == 200
    assert third.get(URL).json()["daily_left"] == 0
    r = third.post(URL, json={"source": "model", "fresh": True})
    assert r.status_code == 429 and "tối đa 1 đoạn" in r.json()["detail"]

    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="0", AICEFR_PASSAGE_DAILY="3")
    fourth = login_as(m, "SV-P10")
    open_words(m, "SV-P10")
    r = fourth.post(URL, json={"source": "model"})
    assert r.status_code == 429 and "ghép đoạn từ cụm của bạn" in r.json()["detail"]
    assert fourth.post(URL, json={"source": "phrases"}).status_code == 200


def test_erasing_a_participant_forgets_their_passages(tmp_path, monkeypatch, model):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-P09")
    open_words(m, "SV-P09")
    made = student.post(URL, json={"source": "model"}).json()
    (kept,) = student.get("/api/v1/me/export.json").json()["drill_passages"]
    assert (kept["passage_id"], kept["source"], kept["words"]) == (
        made["passage_id"],
        "model",
        made["words"],
    )
    me = account_id(m, "SV-P09")
    admin = login_as(m, "QT-P02", "admin")
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-P09", "confirm_speaker_id": "SV-P09"}
    )
    assert r.status_code == 200
    assert store()["drill_passage"].count_documents({"account_id": me}) == 0
