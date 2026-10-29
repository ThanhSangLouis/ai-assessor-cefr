"""Layer 2 -- INTEGRATION: the lesson path through the real runner, database and API (D025).

Each test wires real components together: SQLite in a temporary file, the real
step runner (practice QC, energy VAD, step checker), FastAPI through
TestClient. Only the speech recogniser is a fake -- loading Whisper in tests
breaks AGENTS.md -- and the audio is a synthetic sine wave with silent gaps,
never a real human voice.

The fake recogniser spreads a fixed sentence evenly over the recording; `say`
swaps that sentence for one test. Dates that depend on "today" are pinned by
`freeze`, so a run at midnight in Vietnam gives the same result as at noon.

Tests named after an acceptance criterion carry the exact name given in SRS
section 3.9b (FR-45..FR-50). Defects found while writing this suite were fixed
and their tests kept as regression tests; `docs/test/TEST_PLAN_D025.md`
section 8 lists them.
"""

from __future__ import annotations

import importlib
import io
import json
import warnings
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    QcStatus,
    ReasonCode,
    Response,
    ResponseStatus,
)
from aicefr.lessons.model import (
    STEP_RULES_VERSION,
    Step,
    StepKind,
    StepResult,
    WordMark,
    WordStatus,
)
from aicefr.lessons.runner import (
    PRACTICE_QC,
    PRACTICE_QC_VERSION,
    LessonRunner,
    practice_quality_checker,
)
from aicefr.lessons.seed import SAMPLE_PATH_ID, SAMPLE_UNITS, sample_lessons
from aicefr.qc.audio_qc import AudioQualityChecker
from aicefr.storage.auth_repository import Role
from aicefr.storage.lesson_repository import LessonRepository

pytestmark = pytest.mark.integration

PASSWORD = "matkhau-kiem-thu"
SR = 16_000

# The A2 sample lesson and its seven steps, in ladder order.
SAMPLE = "lesson-a2-neighborhood"
READ, REPEAT, GAP, LOOK_UP, KEYWORDS, OUTLINE, FREE = (f"{SAMPLE}-s{i}" for i in range(1, 8))
REPEAT_TEXT = "I like my neighborhood because the people are friendly."
# Holds the three key words of the KEYWORDS step: morning, walk, bus stop.
KEYWORD_TEXT = "every morning I walk to the bus stop near my home"
# Holds only one of them; "walk" and "bus stop" go to the review queue.
MISSING_TWO = "every morning I go to school"


# ---------------------------------------------------------------- synthetic audio


def pcm(*parts: tuple[str, float]) -> np.ndarray:
    """A sine tone ("tone") with silent stretches ("pause"), in that order."""
    chunks = []
    for kind, seconds in parts:
        n = int(round(SR * seconds))
        if kind == "tone":
            chunks.append(0.2 * np.sin(2 * np.pi * 220 * np.arange(n) / SR))
        else:
            chunks.append(np.zeros(n))
    return np.concatenate(chunks).astype(np.float32)


def encode(samples: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def wav(seconds: float = 4.0) -> bytes:
    return encode(pcm(("tone", seconds)))


# ---------------------------------------------------------------- app and accounts


@pytest.fixture
def m(tmp_path, monkeypatch):
    """A freshly imported app on the per-test database of conftest."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", KEYWORD_TEXT)
    # Energy VAD on every machine: Silero (present with torch) does not take a
    # sine wave for speech, so timings would differ between machines.
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    from aicefr.api import main

    importlib.reload(main)
    return main


def say(m, text: str, **fake) -> None:
    """What the fake recogniser hears in every step recorded from now on."""
    m.speech.runner = LessonRunner(FakeAsrEngine(transcript=text, **fake), EnergyVad())


def freeze(monkeypatch, moment: datetime) -> None:
    """Pin the clock the lesson API uses for "today" (Vietnam time)."""
    monkeypatch.setattr("aicefr.services.core.learning.lessons_api._now", lambda: moment)


def login_as(m, pseudonym: str, role: str = "student", raise_errors: bool = True) -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    client = TestClient(m.app, raise_server_exceptions=raise_errors)
    r = client.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client


def account_id(m, pseudonym: str) -> str:
    return m.app.state.auth_repo.get_by_pseudonym(pseudonym)["account_id"]


def record(
    c: TestClient,
    lesson_id: str,
    step_id: str,
    audio: bytes | None = None,
    round_: int | None = None,
    expect: int = 200,
) -> dict:
    r = c.post(
        f"/api/v1/learn/lessons/{lesson_id}/steps/{step_id}/attempts",
        files={"audio": ("step.wav", audio or wav(), "audio/wav")},
        data={"round": str(round_)} if round_ else {},
    )
    assert r.status_code == expect, r.text
    return r.json()


def submit_assessment(c: TestClient) -> str:
    r = c.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(35.0), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    return r.json()["response_id"]


def scored(response_id: str, band: Band, weakest: list[Criterion]) -> Response:
    return Response(
        response_id=response_id,
        status=ResponseStatus.COMPLETED,
        config_version="v1",
        assessment=Assessment(
            overall_0_6=3.2, overall_band=band, model_version="test", weakest_criteria=weakest
        ),
    )


def teacher_draft(teacher: TestClient, lesson_id: str = SAMPLE) -> dict:
    return teacher.get(f"/api/v1/teach/lessons/{lesson_id}").json()["lesson"]


def audit_entries(m, target_id: str) -> list[dict]:
    admin = login_as(m, "AD-01", "admin")
    return [e for e in admin.get("/api/v1/audit").json() if e["target_id"] == target_id]


# ================================================================= paths and versions (FR-45)


def test_fresh_install_seeds_the_sample_path(m, tmp_path):
    repo = LessonRepository(tmp_path / "fresh.db")
    LessonRepository(tmp_path / "fresh.db")  # a restart must not seed it twice

    [path] = repo.paths(published_only=True)
    assert path["path_id"] == SAMPLE_PATH_ID and path["sample"] == 1
    assert "chờ giảng viên" in path["description"]  # labelled as content awaiting review
    units = repo.outline(SAMPLE_PATH_ID)
    # Six levels in order (D059), each through units on different topics.
    assert [u["band"] for u in units] == (
        ["A1"] * 2 + ["A2"] * 6 + ["B1"] * 6 + ["B2"] * 6 + ["C1"] * 2 + ["C2"] * 2
    )
    for band in ("A1", "A2", "B1", "B2", "C1", "C2"):
        topics = [u["topic"] for u in units if u["band"] == band]
        assert len(set(topics)) == len(topics) >= 2
    items = [item for u in units for item in u["lessons"]]
    assert len(items) == 46
    assert all(item["published_version"] == 1 for item in items)
    assert all(item["lesson"].sample for item in items)
    assert all(item["lesson"].steps[-1].kind is StepKind.FREE for item in items)

    home = login_as(m, "SV-001").get("/api/v1/learn").json()
    assert home["path"]["path_id"] == SAMPLE_PATH_ID and home["path"]["sample"] is True
    assert home["path"]["lessons_total"] == 46 and home["path"]["lessons_completed"] == 0
    assert home["next"]["lesson_id"] == "lesson-pr-flu-a1" and home["next"]["basis"] == "path_order"


def test_students_see_the_published_version_until_republished(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    draft = teacher_draft(teacher)
    original = draft["steps"][3]["text"]
    draft["steps"][3]["text"] = "The only problem is the noise at night."

    assert teacher.put(f"/api/v1/teach/lessons/{SAMPLE}", json=draft).status_code == 200
    assert teacher.get(f"/api/v1/teach/lessons/{SAMPLE}").json()["meta"]["draft_changed"] is True

    seen = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert seen["version"] == 1 and seen["lesson"]["steps"][3]["text"] == original

    assert teacher.post(f"/api/v1/teach/lessons/{SAMPLE}/publish").json() == {"version": 2}
    seen = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert seen["version"] == 2
    assert seen["lesson"]["steps"][3]["text"] == "The only problem is the noise at night."


def test_attempt_records_lesson_version_and_rules_version(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    draft = teacher_draft(teacher)
    draft["steps"][4]["keywords"] = ["morning", "walk", "home"]
    teacher.put(f"/api/v1/teach/lessons/{SAMPLE}", json=draft)
    assert teacher.post(f"/api/v1/teach/lessons/{SAMPLE}/publish").json() == {"version": 2}

    body = record(student, SAMPLE, KEYWORDS)

    row = m.lessons.attempt(body["attempt_id"])
    assert row["lesson_version"] == 2
    assert row["rules_version"] == STEP_RULES_VERSION
    assert row["result"].rules_version == body["result"]["rules_version"] == STEP_RULES_VERSION

    # A later version does not change what the attempt was measured against.
    draft["steps"][4]["keywords"] = ["evening", "bus", "home"]
    teacher.put(f"/api/v1/teach/lessons/{SAMPLE}", json=draft)
    assert teacher.post(f"/api/v1/teach/lessons/{SAMPLE}/publish").json() == {"version": 3}
    seen = teacher.get(f"/api/v1/teach/attempts/{body['attempt_id']}").json()
    assert seen["step"]["keywords"] == ["morning", "walk", "home"]
    assert [h["text"] for h in seen["result"]["found"]] == ["morning", "walk", "home"]


def test_archived_lesson_is_hidden_from_learners_but_its_attempts_stay_readable(m):
    student = login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")
    attempt_id = record(student, SAMPLE, KEYWORDS)["attempt_id"]

    assert teacher.delete(f"/api/v1/teach/lessons/{SAMPLE}").json() == {"status": "ok"}

    assert student.get(f"/api/v1/learn/lessons/{SAMPLE}").status_code == 404
    record(student, SAMPLE, KEYWORDS, expect=404)
    assert student.get("/api/v1/learn").json()["path"]["lessons_total"] == 45
    seen = teacher.get(f"/api/v1/teach/attempts/{attempt_id}").json()
    assert seen["lesson"]["title"] == "Khu phố của tôi" and seen["step"]["kind"] == "keywords"
    exported = student.get("/api/v1/me/export.json").json()["lesson_attempts"]
    assert [a["attempt_id"] for a in exported] == [attempt_id]


def test_attempts_on_a_lesson_of_a_draft_path_are_refused(m):
    teacher = login_as(m, "GV-01", "teacher")
    path_id = teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình nháp"}).json()["path_id"]
    unit_id = teacher.post(
        f"/api/v1/teach/paths/{path_id}/units", json={"title": "Chặng 1", "band": "A2"}
    ).json()["unit_id"]
    lesson_id = teacher.post(
        f"/api/v1/teach/units/{unit_id}/lessons",
        json={"title": "Buổi sáng", "keywords": ["walk", "bus stop"], "free_prompt": "Kể lại."},
    ).json()["lesson_id"]
    assert teacher.post(f"/api/v1/teach/lessons/{lesson_id}/publish").json() == {"version": 1}
    step_id = teacher_draft(teacher, lesson_id)["steps"][0]["step_id"]
    student = login_as(m, "SV-001")

    # The lesson is published, its path is not: no page and no attempts.
    assert student.get(f"/api/v1/learn/lessons/{lesson_id}").status_code == 404
    record(student, lesson_id, step_id, expect=404)
    assert m.lessons.attempts() == []

    teacher.patch(f"/api/v1/teach/paths/{path_id}", json={"status": "published"})
    assert student.get(f"/api/v1/learn/lessons/{lesson_id}").status_code == 200
    record(student, lesson_id, step_id)

    teacher.patch(f"/api/v1/teach/paths/{path_id}", json={"status": "archived"})
    record(student, lesson_id, step_id, expect=404)
    assert len(m.lessons.attempts()) == 1

    # A lesson never published, in a live path, takes no attempts either.
    draft_id = teacher.post(
        "/api/v1/teach/units/unit-sample-a2/lessons",
        json={"title": "Chưa xuất bản", "keywords": ["walk"], "free_prompt": "Kể lại."},
    ).json()["lesson_id"]
    record(student, draft_id, teacher_draft(teacher, draft_id)["steps"][0]["step_id"], expect=404)
    assert len(m.lessons.attempts()) == 1


# ================================================================= measuring a step (FR-46)


def test_practice_clip_qc_accepts_short_recordings_assessment_does_not():
    clip = pcm(("tone", 3.0))

    practice = practice_quality_checker().check(clip, SR)
    assessment = AudioQualityChecker().check(clip, SR)

    assert practice.qc_status is QcStatus.PASS and practice.reasons == []
    assert practice.qc_config_version == PRACTICE_QC_VERSION
    assert PRACTICE_QC.min_duration_s == 1.0
    assert assessment.qc_status is QcStatus.REJECT
    assert ReasonCode.AUDIO_TOO_SHORT in assessment.reasons

    step = Step(kind=StepKind.KEYWORDS, keywords=["walk", "bus stop"], min_words=4)
    runner = LessonRunner(FakeAsrEngine(transcript="I walk to the bus stop"), EnergyVad())
    result = runner.run(step, clip, SR)
    assert result.measured and result.passed
    assert result.speaking_s == pytest.approx(3.0, abs=0.05)


class SpyEngine(FakeAsrEngine):
    """The fake recogniser, remembering how it was called."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.calls: list[tuple[int, list[str]]] = []

    def transcribe(self, *args, **kwargs):
        self.calls.append((len(args), sorted(kwargs)))
        return super().transcribe(*args, **kwargs)


def test_step_runner_says_why_a_recording_was_not_measured():
    step = Step(kind=StepKind.READ_ALOUD, text="the people are friendly")

    def run(samples: np.ndarray, **fake):
        engine = SpyEngine(transcript="the people are friendly", **fake)
        return LessonRunner(engine, EnergyVad()).run(step, samples, SR), engine

    short, engine = run(pcm(("tone", 0.5)))
    assert short.reasons == [ReasonCode.AUDIO_TOO_SHORT] and not short.measured
    assert short.tip and engine.calls == []  # QC stops it before recognition

    silent, engine = run(pcm(("pause", 5.0)))
    assert ReasonCode.HIGH_SILENCE_RATIO in silent.reasons and not silent.measured
    assert engine.calls == []

    foreign, _ = run(pcm(("tone", 4.0)), language="vi", language_probability=0.95)
    assert foreign.reasons == [ReasonCode.LANGUAGE_NOT_ENGLISH] and not foreign.measured

    heard, engine = run(pcm(("tone", 4.0)))
    assert heard.measured and heard.passed
    # The recogniser gets the audio and its rate, never the expected text as a prompt.
    assert engine.calls == [(2, [])]


def test_recorded_step_counts_its_speaking_time_and_an_unmeasured_one_does_not(m, monkeypatch):
    say(m, MISSING_TWO)
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")

    def seconds_today_of(attempt: dict) -> float:
        # "Today" is the day the attempt was stored, even across midnight.
        stored = m.lessons.attempt(attempt["attempt_id"])["created_at"]
        freeze(monkeypatch, datetime.fromisoformat(stored))
        return student.get("/api/v1/learn").json()["today"]["seconds"]

    rejected = record(student, SAMPLE, KEYWORDS, audio=encode(pcm(("tone", 0.5))))
    assert rejected["result"]["measured"] is False
    assert rejected["result"]["reasons"] == ["AUDIO_TOO_SHORT"] and rejected["result"]["tip"]
    assert seconds_today_of(rejected) == 0
    assert m.lessons.open_reviews(acc) == []  # nothing measured, nothing to review

    kept = record(student, SAMPLE, KEYWORDS, audio=wav(4.5))
    assert kept["result"]["measured"] is True
    assert kept["result"]["speaking_s"] == pytest.approx(4.5, abs=0.05)
    assert seconds_today_of(kept) == pytest.approx(4.5, abs=0.1)
    assert sorted(i["word"] for i in m.lessons.open_reviews(acc)) == ["bus stop", "walk"]


def test_learner_lesson_view_never_carries_gap_answers_but_attempts_use_them(m):
    student = login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")

    lesson = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()["lesson"]
    assert all("answers" not in step for step in lesson["steps"])
    assert lesson["steps"][2]["kind"] == "gap" and lesson["steps"][2]["blank_count"] == 2
    preview = teacher.get(f"/api/v1/teach/lessons/{SAMPLE}/preview").json()["lesson"]
    assert all("answers" not in step for step in preview["steps"])
    assert teacher_draft(teacher)["steps"][2]["answers"] == ["quiet", "nearby"]

    say(m, "my street is quiet but there are many shops and a park far")
    result = record(student, SAMPLE, GAP)["result"]
    assert [(g["said"], g["status"]) for g in result["gaps"]] == [
        ("quiet", "correct"),
        ("far", "distractor"),
    ]


def test_free_round_three_result_carries_the_comparison_with_round_one(m):
    say(m, "last weekend I went to the market with my friends and we bought fresh fruit")
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")

    first = record(
        student, SAMPLE, FREE, encode(pcm(("tone", 6), ("pause", 3), ("tone", 6))), round_=1
    )
    assert first["result"]["round"] == 1 and first["result"]["changes"] == []
    assert m.lessons.open_reviews(acc) == []  # the talk comes back only after the last round

    third = record(
        student, SAMPLE, FREE, encode(pcm(("tone", 6), ("pause", 1.2), ("tone", 6))), round_=3
    )
    assert third["result"]["round"] == 3
    assert (
        "Quãng ngừng dài nhất giảm từ 3,0 giây còn 1,2 giây, tốt hơn lượt đầu"
        in third["result"]["changes"]
    )
    assert [(i["kind"], i["step_id"]) for i in m.lessons.open_reviews(acc)] == [("talk", FREE)]


# ================================================================= authoring (FR-47)


def test_students_cannot_edit_paths(m):
    student = login_as(m, "SV-001")
    exported = login_as(m, "GV-01", "teacher").get(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}/export")
    lesson_json = m.lessons.draft(SAMPLE)[0].model_dump(mode="json")

    answers = [
        student.post("/api/v1/teach/paths", json={"title": "Lộ trình riêng"}),
        student.patch(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}", json={"title": "Đổi tên"}),
        student.post(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}/units", json={"title": "Chặng mới"}),
        student.post(
            "/api/v1/teach/units/unit-sample-a2/lessons",
            json={"title": "Bài mới", "model_text": "I like green tea."},
        ),
        student.put(f"/api/v1/teach/lessons/{SAMPLE}", json={**lesson_json, "title": "Bài sửa"}),
        student.post(f"/api/v1/teach/lessons/{SAMPLE}/publish"),
        student.delete(f"/api/v1/teach/lessons/{SAMPLE}"),
        student.post("/api/v1/teach/paths/import", content=exported.content),
        student.get(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}/export"),
    ]

    assert [r.status_code for r in answers] == [403] * len(answers)
    assert [p["path_id"] for p in m.lessons.paths()] == [SAMPLE_PATH_ID]
    lesson, meta = m.lessons.draft(SAMPLE)
    assert lesson.title == "Khu phố của tôi"
    assert meta["published_version"] == 1 and meta["draft_changed"] is False


def test_lesson_endpoints_check_login_and_role(m):
    anonymous = TestClient(m.app)
    for url in (
        "/api/v1/learn",
        f"/api/v1/learn/lessons/{SAMPLE}",
        "/api/v1/learn/review",
        "/api/v1/teach/paths",
        f"/api/v1/teach/lessons/{SAMPLE}",
        "/api/v1/teach/insights",
    ):
        assert anonymous.get(url).status_code == 401, url

    # Teachers try a step through the preview; a learner attempt is a learner's.
    record(login_as(m, "GV-01", "teacher"), SAMPLE, KEYWORDS, expect=403)
    assert m.lessons.attempts() == []


def test_keywords_without_a_text_build_a_word_lesson(m):
    teacher = login_as(m, "GV-01", "teacher")
    url = "/api/v1/teach/units/unit-sample-a2/lessons"

    def create(**body) -> str:
        r = teacher.post(url, json={"band": "A2", **body})
        assert r.status_code == 200, r.text
        return r.json()["lesson_id"]

    words = create(
        title="Từ lớp hay bỏ",
        keywords=["traffic", "nearby", "quiet", "friendly"],
        free_prompt="Tả khu phố của bạn.",
    )
    with_text = create(title="Có đoạn văn", model_text="I live near a quiet park.")
    bare = create(title="Chỉ nói tự do")

    draft = teacher.get(f"/api/v1/teach/lessons/{words}").json()
    steps = draft["lesson"]["steps"]
    assert [s["kind"] for s in steps] == ["keywords", "keywords", "free"]
    assert [s["keywords"] for s in steps[:2]] == [["traffic", "nearby", "quiet"], ["friendly"]]
    assert steps[-1]["text"] == "Tả khu phố của bạn." and steps[-1]["rounds"] == [45, 35]
    assert steps[-1]["missions"][0]["kind"] == "use_words"
    assert steps[-1]["missions"][0]["target"] == 3
    assert [i for i in draft["lint"] if i["level"] == "warn"] == []
    # The other two branches are unchanged: a text gives the ladder, nothing gives free speech.
    assert teacher_draft(teacher, with_text)["steps"][0]["kind"] == "read_aloud"
    assert [s["kind"] for s in teacher_draft(teacher, bare)["steps"]] == ["free"]

    assert teacher.post(f"/api/v1/teach/lessons/{words}/publish").json() == {"version": 1}
    student = login_as(m, "SV-001")
    units = student.get("/api/v1/learn").json()["path"]["units"]
    [a2] = [u for u in units if u["unit_id"] == "unit-sample-a2"]
    assert a2["lessons"][-1]["lesson_id"] == words  # the two drafts stay hidden
    assert a2["lessons"][-1]["kinds"] == ["keywords", "keywords", "free"]
    say(m, "the traffic near my home is bad but the park nearby is quiet")
    result = record(student, words, steps[0]["step_id"])["result"]
    assert [h["text"] for h in result["found"]] == ["traffic", "nearby", "quiet"]


def test_lesson_page_is_a_preview_for_teachers_and_the_lesson_for_students(m):
    url = f"/practice/lessons/{SAMPLE}"

    student = login_as(m, "SV-001").get(f"{url}?preview=1")
    teacher = login_as(m, "GV-01", "teacher").get(url)
    admin = login_as(m, "AD-01", "admin").get(url)

    assert student.status_code == teacher.status_code == admin.status_code == 200
    assert 'data-mode="lesson"' in student.text  # asking for a preview changes nothing
    assert 'data-mode="preview"' in teacher.text and 'data-mode="preview"' in admin.text


def test_model_audio_that_does_not_match_its_text_is_flagged(m):
    teacher = login_as(m, "GV-01", "teacher")
    url = f"/api/v1/teach/lessons/{SAMPLE}/steps/{REPEAT}/model-audio"

    say(m, "I like my neighborhood")
    off = teacher.post(url, files={"audio": ("model.wav", wav(3.0), "audio/wav")}).json()

    assert off["check"]["heard"] == 4 and off["check"]["total"] == 9
    assert off["check"]["ratio"] == round(4 / 9, 3)
    assert "4/9" in off["check"]["warning"]

    say(m, REPEAT_TEXT)
    good = teacher.post(url, files={"audio": ("model.wav", wav(3.0), "audio/wav")}).json()
    assert good["check"]["ratio"] == 1.0 and good["check"]["warning"] == ""

    lesson, _ = m.lessons.draft(SAMPLE)
    assert lesson.step(REPEAT).model_audio == good["media_key"]
    served = teacher.get(good["url"])
    assert served.status_code == 200 and served.headers["content-type"] == "audio/wav"


def test_teacher_cannot_inject_media_keys_through_the_lesson_form(m):
    teacher = login_as(m, "GV-01", "teacher")
    say(m, REPEAT_TEXT)
    key = teacher.post(
        f"/api/v1/teach/lessons/{SAMPLE}/steps/{REPEAT}/model-audio",
        files={"audio": ("model.wav", wav(3.0), "audio/wav")},
    ).json()["media_key"]
    draft = teacher_draft(teacher)
    draft["steps"][0]["model_audio"] = "m-injected"  # the reading step has no recording
    draft["steps"][0]["image"] = "m-injected"
    draft["steps"][1]["model_audio"] = "m-someone-elses"  # the repeat step has its own

    assert teacher.put(f"/api/v1/teach/lessons/{SAMPLE}", json=draft).status_code == 200

    saved, _ = m.lessons.draft(SAMPLE)
    assert saved.steps[0].model_audio is None and saved.steps[0].image is None
    assert saved.steps[1].model_audio == key
    # Removing a recording through the form still works.
    draft["steps"][1]["model_audio"] = None
    teacher.put(f"/api/v1/teach/lessons/{SAMPLE}", json=draft)
    assert m.lessons.draft(SAMPLE)[0].steps[1].model_audio is None


def test_teacher_preview_attempt_stores_nothing(m):
    teacher = login_as(m, "GV-01", "teacher")
    uploads = Path(m.settings.upload_dir)
    before = sorted(p.name for p in uploads.iterdir())
    say(m, MISSING_TWO)
    form = {"lesson_id": SAMPLE, "step_id": KEYWORDS}

    r = teacher.post(
        "/api/v1/teach/preview", files={"audio": ("step.wav", wav(), "audio/wav")}, data=form
    )

    body = r.json()
    assert r.status_code == 200 and body["preview"] is True
    assert body["attempt_id"] is None and body["audio_url"] is None
    assert body["result"]["measured"] and body["result"]["missing"] == ["walk", "bus stop"]
    assert m.lessons.attempts() == []
    assert m.lessons.open_reviews(account_id(m, "GV-01")) == []
    assert sorted(p.name for p in uploads.iterdir()) == before
    student = login_as(m, "SV-001")
    denied = student.post(
        "/api/v1/teach/preview", files={"audio": ("step.wav", wav(), "audio/wav")}, data=form
    )
    assert denied.status_code == 403


def _shape(m, path_id: str) -> list:
    """Units, lessons and steps of a path, without ids or media."""
    return [
        (
            u["title"],
            u["function"],
            u["band"],
            u["criterion"],
            u["topic"],
            [
                (
                    item["lesson"].title,
                    item["lesson"].band,
                    item["lesson"].criterion,
                    item["lesson"].model_text,
                    item["lesson"].keywords,
                    [
                        (s.kind, s.text, s.hint_words, s.answers, s.keywords, s.markers, s.rounds)
                        for s in item["lesson"].steps
                    ],
                )
                for item in u["lessons"]
            ],
        )
        for u in m.lessons.outline(path_id, published_only=False)
    ]


def test_path_export_import_roundtrip(m):
    teacher = login_as(m, "GV-01", "teacher")
    say(m, REPEAT_TEXT)
    teacher.post(
        f"/api/v1/teach/lessons/{SAMPLE}/steps/{REPEAT}/model-audio",
        files={"audio": ("model.wav", wav(3.0), "audio/wav")},
    )

    exported = teacher.get(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}/export")
    assert exported.status_code == 200
    assert "attachment" in exported.headers["content-disposition"]
    data = exported.json()
    steps = [s for u in data["units"] for ls in u["lessons"] for s in ls["steps"]]
    assert all(s["model_audio"] is None and "step_id" not in s for s in steps)  # no media, no ids

    new_id = teacher.post("/api/v1/teach/paths/import", content=exported.content).json()["path_id"]

    assert new_id != SAMPLE_PATH_ID and m.lessons.path(new_id)["status"] == "draft"
    assert _shape(m, new_id) == _shape(m, SAMPLE_PATH_ID)
    imported = [i for u in m.lessons.outline(new_id, published_only=False) for i in u["lessons"]]
    original = [i for u in m.lessons.outline(SAMPLE_PATH_ID) for i in u["lessons"]]
    assert len(imported) == 46
    assert all(i["published_version"] == 0 for i in imported)  # drafts, nothing published
    assert not {i["lesson"].lesson_id for i in imported} & {i["lesson"].lesson_id for i in original}
    learner_paths = login_as(m, "SV-001").get("/api/v1/learn").json()["paths"]
    assert [p["path_id"] for p in learner_paths] == [SAMPLE_PATH_ID]


def test_import_rejects_a_file_that_is_not_a_path_object(m):
    teacher = login_as(m, "GV-01", "teacher", raise_errors=False)
    for body in ([1, 2, 3], {"format": "aicefr-lesson-path", "title": "X", "units": ["oops"]}):
        r = teacher.post("/api/v1/teach/paths/import", content=json.dumps(body).encode())
        assert r.status_code == 422, (body, r.status_code)


def test_rejected_import_leaves_no_half_built_path(m):
    teacher = login_as(m, "GV-01", "teacher")
    data = {
        "format": "aicefr-lesson-path",
        "title": "Lộ trình nhập lỗi",
        "units": [
            {"title": "Chặng 1", "band": "B1", "lessons": []},
            {"title": "Chặng 2", "band": "D1", "lessons": []},
        ],
    }

    r = teacher.post("/api/v1/teach/paths/import", content=json.dumps(data).encode())

    assert r.status_code == 422
    assert [p["path_id"] for p in m.lessons.paths()] == [SAMPLE_PATH_ID]


def test_import_gives_new_ids_and_drops_media_keys(m):
    teacher = login_as(m, "GV-01", "teacher")
    exported = teacher.get(f"/api/v1/teach/paths/{SAMPLE_PATH_ID}/export").json()
    first = exported["units"][0]["lessons"][0]
    first["lesson_id"] = SAMPLE  # an id this installation already has
    first["steps"][0]["model_audio"] = "m-someone-elses-recording"
    first["steps"][0]["image"] = "m-someone-elses-picture"

    r = teacher.post("/api/v1/teach/paths/import", content=json.dumps(exported).encode())

    assert r.status_code == 200, r.text
    outline = m.lessons.outline(r.json()["path_id"], published_only=False)
    imported = outline[0]["lessons"][0]["lesson"]
    assert imported.lesson_id != SAMPLE
    assert imported.steps[0].model_audio is None and imported.steps[0].image is None
    assert m.lessons.draft(SAMPLE)[0].title == "Khu phố của tôi"  # the original is untouched


def test_units_carry_their_topic_through_the_api_export_and_import(m):
    teacher = login_as(m, "GV-01", "teacher")
    pid = teacher.post("/api/v1/teach/paths", json={"title": "Lộ trình chủ đề"}).json()["path_id"]
    uid = teacher.post(
        f"/api/v1/teach/paths/{pid}/units", json={"title": "Đi xa", "band": "B1", "topic": "travel"}
    ).json()["unit_id"]
    listed = next(p for p in teacher.get("/api/v1/teach/paths").json() if p["path_id"] == pid)
    assert listed["units"][0]["topic"] == "travel"

    patched = {"title": "Đi xa", "band": "B1", "topic": "environment"}
    assert teacher.patch(f"/api/v1/teach/units/{uid}", json=patched).status_code == 200
    assert m.lessons.unit(uid)["topic"] == "environment"
    unknown = {"title": "Sao chiếu mệnh", "topic": "astrology"}
    assert teacher.post(f"/api/v1/teach/paths/{pid}/units", json=unknown).status_code == 422

    exported = teacher.get(f"/api/v1/teach/paths/{pid}/export").json()
    assert exported["units"][0]["topic"] == "environment"
    copy = teacher.post("/api/v1/teach/paths/import", content=json.dumps(exported).encode())
    copied = m.lessons.outline(copy.json()["path_id"], published_only=False)
    assert [u["topic"] for u in copied] == ["environment"]

    # Every unit of the sample path tells the learner what it is about.
    home = login_as(m, "SV-001").get("/api/v1/learn").json()
    assert all(u["topic"] for u in home["path"]["units"])


OLD_SAMPLE_UNITS = {"unit-sample-a2": "A2", "unit-sample-b1": "B1", "unit-sample-b2": "B2"}
OLD_SAMPLE_LESSONS = {
    "unit-sample-a2": ["lesson-a2-neighborhood"],
    "unit-sample-b1": ["lesson-b1-trip"],
    "unit-sample-b2": ["lesson-b2-online"],
}


def _old_sample_path(db: Path) -> LessonRepository:
    """A store as the first layout (D025) left it: no topic, one unit per band."""
    from aicefr.contracts import Band

    every = {ls.lesson_id: ls for unit in sample_lessons().values() for ls in unit}
    repo = LessonRepository(db, seed=False)
    # The documents of the time (in the D060 layout): no topic, no record of the layout.
    units = [
        {"unit_id": uid, "title": f"Chặng cũ {band}", "function": "", "band": band,
         "criterion": None, "position": pos, "created_at": "2026-10-01"}
        for pos, (uid, band) in enumerate(OLD_SAMPLE_UNITS.items(), 1)
    ]  # fmt: skip
    repo.col("path").insert_one(
        {"path_id": SAMPLE_PATH_ID, "title": "Lộ trình mẫu cũ", "description": "Mô tả cũ",
         "band_from": "A2", "band_to": "B2", "status": "published", "sample": 1,
         "created_by": "system", "created_at": "2026-10-01T00:00:00+00:00",
         "updated_at": "2026-10-01T00:00:00+00:00", "units": units}
    )  # fmt: skip
    by_band = {"A2": "unit-sample-a2", "B1": "unit-sample-b1", "B2": "unit-sample-b2"}
    for uid, ids in OLD_SAMPLE_LESSONS.items():
        for lid in ids:
            repo.add_lesson(uid, every[lid], by="system")
            repo.publish(lid, by="system")
    for lid, lesson in every.items():
        if lid.startswith("lesson-pr-") and Band(lesson.band).value in by_band:
            repo.add_lesson(by_band[Band(lesson.band).value], lesson, by="system")
            repo.publish(lid, by="system")
    return repo


def test_an_older_sample_path_is_laid_out_by_topic_once(tmp_path):
    db = tmp_path / "old.db"
    old = _old_sample_path(db)
    result = StepResult(step_id="lesson-pr-coh-a2-s1", kind=StepKind.KEYWORDS, passed=True)
    old.add_attempt("acc-1", "lesson-pr-coh-a2", 1, result)
    own = old.add_unit(SAMPLE_PATH_ID, "Chặng của cô Lan", band=None)

    repo = LessonRepository(db)  # the upgrade

    units = repo.outline(SAMPLE_PATH_ID, published_only=False)
    ids = [u["unit_id"] for u in units]
    assert ids == [*(u["unit_id"] for u in SAMPLE_UNITS), own]  # a teacher's unit stays, last
    assert all(u["topic"] for u in units[:-1]) and units[-1]["topic"] is None
    assert units[2]["title"] == "Đời sống hằng ngày" and repo.path(SAMPLE_PATH_ID)["title"] != (
        "Lộ trình mẫu cũ"
    )
    where = {i["lesson"].lesson_id: u["unit_id"] for u in units for i in u["lessons"]}
    assert where["lesson-pr-coh-a2"] == "unit-a2-food"
    assert len([lid for lid in where if lid.startswith("lesson-")]) == 46  # D059 adds 15
    assert repo.path(SAMPLE_PATH_ID)["band_from"] == "A1"
    assert repo.published("lesson-b2-plastic")[1] == 1  # new lessons arrive published
    assert len(repo.attempts(lesson_id="lesson-pr-coh-a2")) == 1  # attempts untouched

    # Once only: a teacher's later move survives the next start.
    repo.col("lesson").update_one(
        {"lesson_id": "lesson-pr-coh-a2"}, {"$set": {"unit_id": "unit-sample-a2"}}
    )
    LessonRepository(db)
    assert repo.draft("lesson-pr-coh-a2")[1]["unit_id"] == "unit-sample-a2"


# ================================================================= spaced review (FR-48)


def test_missed_words_are_scheduled_for_tomorrow(m, monkeypatch):
    # 18:30 UTC on 5 October is 01:30 on 6 October in Vietnam: tomorrow is the 7th.
    freeze(monkeypatch, datetime(2026, 10, 5, 18, 30, tzinfo=UTC))
    say(m, MISSING_TWO)
    student = login_as(m, "SV-001")

    body = record(student, SAMPLE, KEYWORDS)

    assert body["result"]["missing"] == ["walk", "bus stop"]
    items = m.lessons.open_reviews(account_id(m, "SV-001"))
    assert sorted((i["word"], i["kind"], i["box"], i["due_date"]) for i in items) == [
        ("bus stop", "word", 1, "2026-10-07"),
        ("walk", "word", 1, "2026-10-07"),
    ]
    assert {(i["lesson_id"], i["step_id"]) for i in items} == {(SAMPLE, KEYWORDS)}


def test_review_session_moves_words_through_the_leitner_boxes(m, monkeypatch):
    freeze(monkeypatch, datetime(2026, 10, 5, 18, 30, tzinfo=UTC))  # 6 October in Vietnam
    say(m, MISSING_TWO)
    student = login_as(m, "SV-001")
    record(student, SAMPLE, KEYWORDS)
    assert student.get("/api/v1/learn/review").json()["steps"] == []  # not due the same day

    freeze(monkeypatch, datetime(2026, 10, 7, 3, 0, tzinfo=UTC))  # 7 October, 10:00
    assert student.get("/api/v1/learn").json()["reviews_due"] == 2
    [entry] = student.get("/api/v1/learn/review").json()["steps"]
    assert entry["source"] == "words"
    assert sorted(entry["step"]["keywords"]) == ["bus stop", "walk"]

    say(m, "I walk to school with my friends every day")
    r = student.post(
        "/api/v1/learn/review/attempts",
        files={"audio": ("review.wav", wav(), "audio/wav")},
        data={"review_id": entry["review_id"]},
    )

    assert r.status_code == 200, r.text
    outcome = {i["word"]: (i["passed"], i["due"]) for i in r.json()["items"]}
    assert outcome == {"walk": (True, "2026-10-10"), "bus stop": (False, "2026-10-08")}
    boxes = {
        i["word"]: (i["box"], i["due_date"])
        for i in m.lessons.open_reviews(account_id(m, "SV-001"))
    }
    assert boxes == {"walk": (2, "2026-10-10"), "bus stop": (1, "2026-10-08")}
    assert student.get("/api/v1/learn/review").json()["due"] == 0


def test_review_items_of_an_archived_lesson_are_closed(m, monkeypatch):
    freeze(monkeypatch, datetime(2026, 10, 6, 3, 0, tzinfo=UTC))  # 10:00 in Vietnam
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    m.lessons.schedule(acc, "talk", SAMPLE, FREE, "", date(2026, 10, 6))
    assert student.get("/api/v1/learn").json()["reviews_due"] == 1

    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.delete(f"/api/v1/teach/lessons/{SAMPLE}").status_code == 200

    # Nothing is left to review, so the item is closed rather than counted forever.
    assert student.get("/api/v1/learn").json()["reviews_due"] == 0
    assert m.lessons.open_reviews(acc) == []


# ================================================================= teachers follow (FR-49)


def test_teacher_override_updates_the_result_and_is_audited(m):
    say(m, "I like my neighborhood because the people friendly")
    student = login_as(m, "SV-001")
    attempt = record(student, SAMPLE, REPEAT)
    are = next(w for w in attempt["result"]["words"] if w["text"] == "are")
    assert are["status"] == "missed" and are["teacher"] is None
    teacher = login_as(m, "GV-01", "teacher")

    r = teacher.post(
        f"/api/v1/teach/attempts/{attempt['attempt_id']}/override",
        json={"words": {str(are["index"]): "heard"}, "note": "Em đọc rõ từ này."},
    )

    assert r.status_code == 200
    seen = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()["latest"][REPEAT]["result"]
    mark = next(w for w in seen["words"] if w["index"] == are["index"])
    assert mark["teacher"] == "heard" and mark["status"] == "missed"  # both views are kept
    assert seen["teacher_reviewed"] is True and seen["teacher_note"] == "Em đọc rõ từ này."
    view = teacher.get(f"/api/v1/teach/attempts/{attempt['attempt_id']}").json()
    assert view["overridden_by"] == "GV-01"
    assert view["override"]["words"] == {str(are["index"]): "heard"}
    entries = audit_entries(m, attempt["attempt_id"])
    assert [(e["actor_id"], e["action"]) for e in entries] == [("GV-01", "lesson.override")]


def test_passed_steps_and_the_teacher_view_respect_overrides(m):
    student = login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")
    first = record(student, SAMPLE, KEYWORDS)  # all three key words: passed
    say(m, MISSING_TWO)
    record(student, SAMPLE, KEYWORDS)  # a later attempt that does not pass
    say(m, "I like my neighborhood")  # 4 of 9 words, under the pass mark
    repeat = record(student, SAMPLE, REPEAT)
    assert first["result"]["passed"] is True and repeat["result"]["passed"] is False

    view = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert view["latest"][KEYWORDS]["passed"] is False  # the latest attempt...
    assert view["passed_steps"] == [KEYWORDS]  # ...does not undo an earlier pass

    override = f"/api/v1/teach/attempts/{repeat['attempt_id']}/override"
    assert teacher.post(override, json={"passed": True, "note": "Đọc đủ ý."}).json()["passed"]
    corrected = teacher.get(f"/api/v1/teach/attempts/{repeat['attempt_id']}").json()
    assert corrected["passed"] is True and corrected["machine_passed"] is False
    assert corrected["override"] == {"words": {}, "note": "Đọc đủ ý.", "passed": True}
    untouched = teacher.get(f"/api/v1/teach/attempts/{first['attempt_id']}").json()
    assert untouched["override"] is None and untouched["machine_passed"] is True

    view = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert view["passed_steps"] == sorted([KEYWORDS, REPEAT])
    assert view["progress"]["passed"] == 2
    # A correction the other way takes a pass away.
    teacher.post(f"/api/v1/teach/attempts/{first['attempt_id']}/override", json={"passed": False})
    view = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert view["passed_steps"] == [REPEAT] and view["progress"]["passed"] == 1
    preview = teacher.get(f"/api/v1/teach/lessons/{SAMPLE}/preview").json()
    assert preview["passed_steps"] == []


def test_teacher_word_correction_keeps_its_status_type(tmp_path):
    repo = LessonRepository(tmp_path / "lessons.db", seed=False)
    machine = StepResult(
        step_id="s1",
        kind=StepKind.READ_ALOUD,
        passed=False,
        words=[WordMark(index=0, text="are", status=WordStatus.MISSED)],
    )
    attempt_id = repo.add_attempt("acc-1", "lesson-x", 1, machine)
    # Stored exactly as POST .../override stores it.
    repo.set_override(attempt_id, {"words": {0: WordStatus.HEARD.value}, "note": ""}, by="GV-01")

    result = repo.attempt(attempt_id)["result"]

    assert result.words[0].final is WordStatus.HEARD
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result.model_dump(mode="json")


def test_lesson_attempts_stay_out_of_queue_and_research_export(m):
    student = login_as(m, "SV-001")
    lesson_attempts = {
        record(student, SAMPLE, KEYWORDS)["attempt_id"],
        record(student, SAMPLE, FREE, round_=1)["attempt_id"],
    }
    assessment_id = submit_assessment(student)

    queue = login_as(m, "GV-01", "teacher").get("/api/v1/review/queue").json()
    export = login_as(m, "AD-01", "admin").get("/api/v1/admin/export/research.json").json()

    assert not lesson_attempts & {r["response_id"] for r in queue}
    assert {r["task_id"] for r in queue} <= {"P3"}
    assert [r["response_id"] for r in export["rows"]] == [assessment_id]
    assert [r["response_id"] for r in student.get("/api/v1/me/responses").json()] == [assessment_id]


# ================================================================= own data (FR-34, FR-35)


def test_attempt_recordings_belong_to_their_learner(m):
    student = login_as(m, "SV-001")
    other = login_as(m, "SV-002")
    teacher = login_as(m, "GV-01", "teacher")
    clip = wav(4.0)
    attempt = record(student, SAMPLE, KEYWORDS, audio=clip)
    url = attempt["audio_url"]
    key = m.lessons.attempt(attempt["attempt_id"])["audio_key"]

    own = student.get(url)
    assert own.status_code == 200 and own.content == clip
    assert own.headers["content-type"] == "audio/wav"
    assert "no-store" in own.headers["cache-control"]
    assert teacher.get(url).status_code == 200  # a teacher may listen back (FR-49)
    assert other.get(url).status_code == 404  # 404, not 403: the id is not confirmed

    delete = f"/api/v1/learn/attempts/{attempt['attempt_id']}"
    assert other.delete(delete).status_code == 404
    assert teacher.delete(delete).status_code == 404
    assert m.blobs.exists(key)
    assert student.delete(delete).json() == {"status": "ok"}

    assert m.lessons.count_attempts(account_id(m, "SV-001")) == 0
    assert not m.blobs.exists(key)  # the recording, not only the row
    assert student.get(url).status_code == 404
    lesson = student.get(f"/api/v1/learn/lessons/{SAMPLE}").json()
    assert lesson["latest"] == {} and lesson["progress"]["passed"] == 0


def test_listening_to_a_lesson_recording_is_audited(m):
    student = login_as(m, "SV-001")
    attempt = record(student, SAMPLE, KEYWORDS)
    teacher = login_as(m, "GV-01", "teacher")

    assert teacher.get(attempt["audio_url"]).status_code == 200

    heard = [e for e in audit_entries(m, attempt["attempt_id"]) if e["action"] == "AUDIO_ACCESS"]
    assert [e["actor_id"] for e in heard] == [account_id(m, "GV-01")]


def test_deleting_an_attempt_is_audited_without_its_content(m):
    student = login_as(m, "SV-001")
    attempt_id = record(student, SAMPLE, KEYWORDS)["attempt_id"]

    assert student.delete(f"/api/v1/learn/attempts/{attempt_id}").status_code == 200

    entries = audit_entries(m, attempt_id)
    assert len(entries) == 1
    assert entries[0]["actor_id"] in {"SV-001", account_id(m, "SV-001")}
    assert "morning" not in (entries[0]["detail"] or "")  # no transcript in the log


def test_orphan_cleanup_keeps_lesson_recordings_and_teacher_media(tmp_path):
    from aicefr.retention import orphaned_recordings
    from aicefr.storage.repository import Repository

    db = tmp_path / "shared.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    lessons = LessonRepository(db, seed=False)
    result = StepResult(step_id="s1", kind=StepKind.KEYWORDS, passed=True)
    lessons.add_attempt("acc-1", "lesson-x", 1, result, audio_key="lesson-audio-a1.wav")
    # Media belong to the lesson they were uploaded for (D060).
    unit = lessons.add_unit(lessons.create_path("P"), "U")
    lesson = next(iter(sample_lessons().values()))[0].model_copy(update={"lesson_id": "l1"})
    lessons.add_lesson(unit, lesson)
    lessons.add_media("l1", "image", "image/png", "lesson-media-l1-s1-x.png", "GV-01")
    for name in ("lesson-audio-a1.wav", "lesson-media-l1-s1-x.png", "nobody.wav"):
        (uploads / name).write_bytes(b"RIFF")

    found = orphaned_recordings(Repository(db), uploads)

    assert [f.name for f in found] == ["nobody.wav"]


def test_retention_sweep_covers_lesson_attempts(tmp_path):
    from aicefr.retention import apply_retention
    from aicefr.storage.repository import Repository

    db = tmp_path / "shared.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    lessons = LessonRepository(db, seed=False)
    machine = StepResult(
        step_id="s1",
        kind=StepKind.READ_ALOUD,
        passed=False,
        transcript="the people friendly",
        words=[
            WordMark(index=0, text="the", status=WordStatus.HEARD),
            WordMark(index=1, text="are", status=WordStatus.MISSED, said="our"),
        ],
    )
    attempt_id = lessons.add_attempt(
        "acc-1", "lesson-x", 1, machine, audio_key="lesson-audio-old.wav"
    )
    (uploads / "lesson-audio-old.wav").write_bytes(b"RIFF" + b"x" * 100)

    preview = apply_retention(Repository(db), days=-1, dry_run=True, upload_dir=uploads)
    assert preview.lesson_attempts == 1 and preview.audio_deleted == 1
    assert (uploads / "lesson-audio-old.wav").is_file()

    apply_retention(Repository(db), days=-1, dry_run=False, upload_dir=uploads)

    row = lessons.attempt(attempt_id)
    assert not (uploads / "lesson-audio-old.wav").exists()
    assert row["audio_key"] is None
    assert row["result"].transcript == ""
    assert [w.said for w in row["result"].words] == [None, None]
    # The record of the practice stays: which words were heard, the verdict.
    assert [w.status for w in row["result"].words] == [WordStatus.HEARD, WordStatus.MISSED]
    assert row["passed"] is False


def test_a_learner_records_a_step_straight_after_signing_in(m):
    """D064: no terms step stands between signing in and recording."""
    student = login_as(m, "SV-001")
    record(student, SAMPLE, KEYWORDS)
    assert m.lessons.count_attempts(account_id(m, "SV-001")) == 1


def test_personal_export_and_erasure_cover_lesson_attempts(m):
    say(m, MISSING_TWO)
    student = login_as(m, "SV-001")
    bystander = login_as(m, "SV-002")
    acc, other = account_id(m, "SV-001"), account_id(m, "SV-002")
    attempt = record(student, SAMPLE, KEYWORDS)
    record(bystander, SAMPLE, KEYWORDS)
    key = m.lessons.attempt(attempt["attempt_id"])["audio_key"]

    exported = student.get("/api/v1/me/export.json").json()
    assert exported["lesson_attempt_count"] == 1
    [item] = exported["lesson_attempts"]
    assert (item["attempt_id"], item["lesson_id"], item["lesson_version"], item["step_id"]) == (
        attempt["attempt_id"],
        SAMPLE,
        1,
        KEYWORDS,
    )
    assert item["result"]["transcript"] == MISSING_TWO

    admin = login_as(m, "AD-01", "admin")
    assert admin.get("/api/v1/admin/erase/SV-001").json()["lesson_attempts"] == 1
    erased = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    ).json()

    assert erased["lesson_attempts"] == 1
    assert m.lessons.count_attempts(acc) == 0 and m.lessons.open_reviews(acc) == []
    assert not m.blobs.exists(key)
    assert m.lessons.count_attempts(other) == 1 and len(m.lessons.open_reviews(other)) == 2


# ================================================================= progress (FR-50)


def test_daily_goal_counts_seconds_spoken(m, monkeypatch):
    freeze(monkeypatch, datetime(2026, 10, 6, 5, 0, tzinfo=UTC))  # noon in Vietnam
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")

    def spoke(step_id: str, kind: StepKind, seconds: float, at: str, measured: bool = True):
        result = StepResult(
            step_id=step_id, kind=kind, passed=True, measured=measured, speaking_s=seconds
        )
        m.lessons.add_attempt(acc, SAMPLE, 1, result, created_at=at)

    spoke(FREE, StepKind.FREE, 40.0, "2026-10-06T01:00:00+00:00")
    spoke(READ, StepKind.READ_ALOUD, 55.0, "2026-10-06T04:30:00+00:00")
    spoke(READ, StepKind.READ_ALOUD, 30.0, "2026-10-05T16:30:00+00:00")  # 23:30 yesterday
    spoke(GAP, StepKind.GAP, 12.0, "2026-10-06T02:00:00+00:00", measured=False)

    today = student.get("/api/v1/learn").json()["today"]

    assert today["seconds"] == 95.0 and today["goal_seconds"] == 180
    assert today["goal_met"] is False
    assert today["week"][-2:] == [
        {"date": "2026-10-05", "seconds": 30.0},
        {"date": "2026-10-06", "seconds": 95.0},
    ]


def test_next_lesson_follows_the_weakest_criterion(m):
    teacher = login_as(m, "GV-01", "teacher")
    path_id = teacher.post(
        "/api/v1/teach/paths", json={"title": "Lộ trình lớp B1", "band_from": "B1"}
    ).json()["path_id"]

    def unit(title: str, criterion: str) -> str:
        body = {"title": title, "band": "B1", "criterion": criterion}
        return teacher.post(f"/api/v1/teach/paths/{path_id}/units", json=body).json()["unit_id"]

    def lesson(unit_id: str, title: str) -> str:
        body = {
            "title": title,
            "band": "B1",
            "model_text": "Last summer I traveled to the coast. We visited a small fishing town.",
            "keywords": ["traveled", "visited", "town"],
            "free_prompt": "Kể về một chuyến đi.",
        }
        lid = teacher.post(f"/api/v1/teach/units/{unit_id}/lessons", json=body).json()["lesson_id"]
        assert teacher.post(f"/api/v1/teach/lessons/{lid}/publish").json() == {"version": 1}
        return lid

    fluency, rng = unit("Kể chuyện trôi chảy", "fluency"), unit("Mở rộng vốn từ", "range")
    first_fluency = lesson(fluency, "Kể lại một ngày")
    first_range, second_range = lesson(rng, "Từ về du lịch"), lesson(rng, "Từ về thành phố")
    teacher.patch(f"/api/v1/teach/paths/{path_id}", json={"status": "published"})
    student = login_as(m, "SV-001")
    acc = account_id(m, "SV-001")
    done, _ = m.lessons.published(first_range)
    for step in done.steps:  # the first Range lesson is already complete
        result = StepResult(step_id=step.step_id, kind=step.kind, passed=True, speaking_s=10.0)
        m.lessons.add_attempt(acc, first_range, 1, result)

    before = student.get(f"/api/v1/learn?path_id={path_id}").json()["next"]
    assert (before["lesson_id"], before["basis"]) == (first_fluency, "path_order")

    m.repo.save(scored("as-1", Band.B1, [Criterion.RANGE]), "SV-001", "P3", account_id=acc)
    after = student.get(f"/api/v1/learn?path_id={path_id}").json()["next"]

    assert after["lesson_id"] == second_range and after["basis"] == "weakest_criterion"
    assert after["title"] == "Từ về thành phố"
    assert "vốn từ" in after["reason"] and "B1" in after["reason"]
