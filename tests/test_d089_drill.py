"""D089 integration layer: saying again the unclear words of a recording, in the application.

* only the learner who recorded a scored response practises from it, on the
  page and through the API; anyone else gets 404;
* the words offered come from the stored transcript, each with its place in
  the recording, its phrase and a tip when the spelling gives one;
* a take is measured by the speech service; two clear takes in a row close the
  word, a take that is not sends it to spaced review, where it comes back as a
  word to use in a sentence of one's own;
* the progress page carries the share of unclear words per assessment, and
  the words still open; the personal export carries the drills, and erasing a
  participant forgets them.
"""

from __future__ import annotations

import pytest
from dbutil import store
from test_d069_coach import scored
from test_lessons_integration import account_id, login_as, m, submit_assessment, wav  # noqa: F401

from aicefr.contracts import Transcript, Word
from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
from aicefr.pronunciation.vietnamese import classify
from aicefr.services.core.learning import drill_api

SPOKEN = [  # (word, probability)
    ("I", 0.95), ("worked", 0.21), ("very", 0.9), ("hard", 0.88), ("in", 0.97),
    ("three", 0.33), ("cities", 0.92), ("um", 0.1), ("last", 0.9), ("year.", 0.94),
]  # fmt: skip


def with_words(m, rid: str) -> None:
    """A scored response whose transcript has two unclear words: worked, three."""
    scored(m, rid)
    report = m.repo.get(rid)
    t, words = 0.0, []
    for text, prob in SPOKEN:
        words.append(Word(text=text, start_s=round(t, 2), end_s=round(t + 0.4, 2), prob=prob))
        t += 0.5
    report.asr = Transcript(
        text=" ".join(w for w, _ in SPOKEN), words=words, engine="fake", model_version="small"
    )
    store()["response"].update_one(
        {"response_id": rid}, {"$set": {"report_json": report.model_dump_json()}}
    )


@pytest.fixture
def heard(monkeypatch):
    """The speech service, answering what the test says it heard of the target word."""
    answers: list[tuple[WordStatus, str | None]] = []

    def measure(step, data, kind, round_index, answers_, keep=None):
        assert step.kind is StepKind.READ_ALOUD and keep is None  # the take is not kept
        status, said = answers.pop(0)
        shown = step.text.split()
        target = next(i for i, w in enumerate(shown) if w.lower() == step.hint_words[0])
        # As the read-aloud check marks it: the pattern the gap names, if one does.
        pattern = classify(step.hint_words[0], said) if said else None
        marks = [
            WordMark(index=i, text=w, status=status if i == target else WordStatus.HEARD,
                     said=said if i == target else None,
                     pattern=pattern.value if pattern and i == target else None)
            for i, w in enumerate(shown)
        ]  # fmt: skip
        return StepResult(
            step_id=step.step_id, kind=step.kind, passed=True, words=marks, transcript=step.text
        )

    monkeypatch.setattr(drill_api, "_measure", measure)
    return answers


def take(client, rid: str, word: str):
    return client.post(
        f"/api/v1/learn/drill/{rid}/takes",
        files={"audio": ("t.wav", wav(3.0), "audio/wav")},
        data={"word": word},
    )


def test_only_the_owner_of_a_scored_response_practises_its_words(m):
    owner = login_as(m, "SV-D01")
    rid = submit_assessment(owner)
    other = login_as(m, "SV-D02")
    assert owner.get(f"/api/v1/learn/drill/{rid}").status_code == 404  # not scored yet
    with_words(m, rid)
    assert other.get(f"/api/v1/learn/drill/{rid}").status_code == 404
    assert take(other, rid, "worked").status_code == 404
    teacher = login_as(m, "GV-D01", "teacher")
    assert teacher.get(f"/api/v1/learn/drill/{rid}").status_code == 403
    assert 'data-response-id="' + rid + '"' in owner.get(f"/drill/{rid}").text


def test_the_unclear_words_are_offered_with_their_place_phrase_and_tip(m):
    student = login_as(m, "SV-D03")
    rid = submit_assessment(student)
    with_words(m, rid)
    d = student.get(f"/api/v1/learn/drill/{rid}").json()
    assert [w["word"] for w in d["words"]] == ["worked", "three"]  # "um" is a filler
    worked, three = d["words"]
    assert worked["phrase"] == "I worked very hard" and worked["start_s"] == 0.3
    assert worked["pattern"] == "ed_ending" and three["pattern"] == "th_sound"
    assert (worked["takes"], worked["passed"], d["pass_streak"]) == (0, False, 2)
    assert d["unsure_share"] == pytest.approx(2 / 9)
    assert "chưa chắc là bạn phát âm sai" in d["note"]


def test_two_clear_takes_close_a_word_and_a_miss_sends_it_to_review(m, heard):
    student = login_as(m, "SV-D04")
    rid = submit_assessment(student)
    with_words(m, rid)
    heard += [(WordStatus.UNSURE, "work"), (WordStatus.HEARD, None), (WordStatus.HEARD, None)]

    miss = take(student, rid, "worked").json()
    assert (miss["passed"], miss["said"], miss["pattern_name"]) == (False, "work", "Đuôi -ed")
    assert miss["review_due"] and miss["drill"]["streak"] == 0
    review = student.get("/api/v1/learn/review").json()
    assert review["open"] == 1  # due tomorrow, not today

    assert take(student, rid, "worked").json()["drill"]["streak"] == 1
    done = take(student, rid, "Worked").json()
    assert done["passed"] and done["drill"]["passed"] and done["review_due"] is None
    words = student.get(f"/api/v1/learn/drill/{rid}").json()["words"]
    assert [(w["word"], w["passed"], w["takes"]) for w in words] == [
        ("worked", True, 3),
        ("three", False, 0),
    ]
    assert take(student, rid, "hello").status_code == 404  # not a word of this recording


def test_a_take_nothing_could_be_measured_from_does_not_count(m, monkeypatch):
    student = login_as(m, "SV-D05")
    rid = submit_assessment(student)
    with_words(m, rid)
    monkeypatch.setattr(
        drill_api,
        "_measure",
        lambda *a, **k: StepResult(
            step_id="drill", kind=StepKind.READ_ALOUD, passed=False, measured=False, tip="Nói lại."
        ),
    )
    d = take(student, rid, "three").json()
    assert (d["measured"], d["tip"]) == (False, "Nói lại.")
    assert student.get("/api/v1/learn/drill").json()["practised"] == 0


def test_a_real_take_goes_through_the_speech_service(m):
    student = login_as(m, "SV-D06")
    rid = submit_assessment(student)
    with_words(m, rid)
    r = take(student, rid, "three")
    assert r.status_code == 200, r.text
    assert set(r.json()) >= {"measured", "passed", "said", "transcript", "review_due"}


def test_progress_shows_the_unclear_share_and_the_open_words(m, heard):
    student = login_as(m, "SV-D07")
    rid = submit_assessment(student)
    with_words(m, rid)
    clarity = student.get("/api/v1/me/progress").json()["habits"][-1]
    assert clarity["feature"] == "unsure_share" and clarity["better"] == "down"
    assert [p["value"] for p in clarity["points"]] == [22.2]

    heard.append((WordStatus.MISSED, None))
    take(student, rid, "three")
    mine = student.get("/api/v1/learn/drill").json()
    assert (mine["practised"], mine["passed"]) == (1, 0)
    assert [(w["word"], w["response_id"]) for w in mine["open"]] == [("three", rid)]


def test_erasing_a_participant_forgets_their_drills(m, heard):
    student = login_as(m, "SV-D08")
    rid = submit_assessment(student)
    with_words(m, rid)
    heard.append((WordStatus.HEARD, None))
    take(student, rid, "worked")
    (kept,) = student.get("/api/v1/me/export.json").json()["word_drills"]
    assert (kept["word"], kept["response_id"], kept["takes"][0]["passed"]) == ("worked", rid, True)
    me = account_id(m, "SV-D08")
    admin = login_as(m, "QT-D01", "admin")
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-D08", "confirm_speaker_id": "SV-D08"}
    )
    assert r.status_code == 200
    assert store()["word_drill"].count_documents({"account_id": me}) == 0
