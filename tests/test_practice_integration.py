"""Layer 2 -- INTEGRATION: the practice mode through the real pipeline, database and API (D023).

Each test runs real components wired together: SQLite in a temporary file, the
real pipeline (QC, energy VAD, feature extraction, mission checker), FastAPI
through TestClient. Only the speech recogniser is a fake -- loading Whisper in
tests breaks AGENTS.md -- and the audio is a synthetic sine wave, never a real
human voice.

Test case ids (TC-PR-Ixx) and acceptance criteria are listed in
`docs/test/TEST_PLAN_D023.md`.
"""

from __future__ import annotations

import importlib
import io
import json

import numpy as np
import pytest
import soundfile as sf
from dbutil import one_school
from fastapi.testclient import TestClient

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    MissionKind,
    ProcessingRequest,
    ReasonCode,
    Response,
    ResponseStatus,
    TaskPurpose,
)
from aicefr.pipeline import ResponseProcessor
from aicefr.practice.bank import PRACTICE_TASKS
from aicefr.storage.repository import Repository
from aicefr.storage.task_repository import TaskRepository

pytestmark = pytest.mark.integration

PASSWORD = "matkhau-kiem-thu"
SR = 16_000
# Fake transcript used for every API submission: it holds the 4 linking words of PR-COH-A2.
COH_TEXT = "I like pho because it is tasty and cheap but I do not like durian so I never eat it"
PHO_A2 = next(t for t in PRACTICE_TASKS if t.task_id == "PR-PHO-A2")


def tone(seconds: float) -> np.ndarray:
    t = np.arange(int(SR * seconds)) / SR
    return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def wav(seconds: float = 35.0) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, tone(seconds), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


# ================================================================= database (FR-40, FR-44)


def test_task_repository_seeds_30_practice_tasks_and_lists_assessment_by_default(tmp_path):
    tasks = TaskRepository(tmp_path / "t.db")
    practice = tasks.list_active(TaskPurpose.PRACTICE)
    assert len(practice) == 30 and all(t.is_practice for t in practice)
    assessment = tasks.list_active()
    assert len(assessment) == 36 and not any(t.is_practice for t in assessment)
    loaded = tasks.get("PR-COH-B2")
    assert loaded.criterion is Criterion.COHERENCE and loaded.band is Band.B2
    assert [m.kind for m in loaded.missions] == [
        MissionKind.USE_WORDS,
        MissionKind.USE_WORDS,
        MissionKind.SPEAK_SECONDS,
    ]
    assert tasks.get("PR-PHO-A2").reference_text


def test_bank_version_bump_updates_the_row_and_same_version_leaves_it(tmp_path):
    db = tmp_path / "t.db"
    stored = TaskRepository(db).col("task")
    stored.update_one({"task_id": "PR-FLU-A2"}, {"$set": {"prompt_version": "v0", "title": "cu"}})
    stored.update_one({"task_id": "PR-FLU-B1"}, {"$set": {"title": "giu"}})
    tasks = TaskRepository(db)
    assert tasks.get("PR-FLU-A2").title != "cu"
    assert tasks.get("PR-FLU-A2").prompt_version == "v1"
    assert tasks.get("PR-FLU-B1").title == "giu"


def _queued(rid: str) -> Response:
    return Response(response_id=rid, status=ResponseStatus.QUEUED, config_version="v1")


def test_later_save_without_purpose_keeps_the_stored_purpose(tmp_path):
    """The worker saving a result does not know the purpose; losing it turns practice into exams."""
    repo = Repository(tmp_path / "r.db")
    repo.save(_queued("p1"), "SV-1", "PR-COH-A2", account_id="a1", purpose=TaskPurpose.PRACTICE)
    done = Response(response_id="p1", status=ResponseStatus.COMPLETED, config_version="v1")
    assert repo.save(done, "SV-1", "PR-COH-A2", account_id="a1", must_exist=True)
    assert repo.status_of("p1")["purpose"] == "practice"
    repo.save(_queued("a1"), "SV-1", "P3", account_id="a1")
    assert repo.status_of("a1")["purpose"] == "assessment"


def test_attempts_keep_submission_order_within_one_second_and_filter_by_task(tmp_path):
    repo = Repository(tmp_path / "r.db")
    for rid, task in (("x1", "PR-COH-A2"), ("x2", "PR-FLU-A2"), ("x3", "PR-COH-A2")):
        repo.save(_queued(rid), "SV-1", task, account_id="a1", purpose=TaskPurpose.PRACTICE)
    repo.col("response").update_many({}, {"$set": {"created_at": "2026-10-06T01:00:00+00:00"}})
    assert [a["response_id"] for a in repo.practice_attempts("a1")] == ["x1", "x2", "x3"]
    assert [a["response_id"] for a in repo.practice_attempts("a1", "PR-COH-A2")] == ["x1", "x3"]
    assert repo.practice_attempts("a2") == []


def _scored(rid: str, band: Band, weakest: list[Criterion], verified: bool = False) -> Response:
    return Response(
        response_id=rid,
        status=ResponseStatus.COMPLETED,
        config_version="v1",
        assessment=Assessment(
            overall_0_6=3.2,
            overall_band=band,
            model_version="kiem-thu",
            weakest_criteria=weakest,
            teacher_verified=verified,
        ),
    )


def test_latest_assessment_ignores_practice_and_unscored_rows(tmp_path):
    repo = Repository(tmp_path / "r.db")
    repo.save(_scored("old", Band.A2, [Criterion.FLUENCY]), "SV-1", "P3", account_id="a1")
    repo.save(_scored("new", Band.B1, [Criterion.RANGE]), "SV-1", "P4", account_id="a1")
    repo.save(_queued("unscored"), "SV-1", "P3", account_id="a1")
    repo.save(_queued("prac"), "SV-1", "PR-RAN-B1", account_id="a1", purpose=TaskPurpose.PRACTICE)
    for i, rid in enumerate(("old", "new", "unscored", "prac")):
        repo.col("response").update_one(
            {"response_id": rid}, {"$set": {"created_at": f"2026-10-0{i + 1}T01:00:00+00:00"}}
        )
    basis = repo.latest_assessment("a1")
    assert basis["response_id"] == "new" and basis["band"] == "B1"
    assert basis["weakest_criteria"] == ["range"]
    assert repo.latest_assessment("khac") is None


def test_teacher_queue_never_holds_practice_even_if_marked_for_review(tmp_path):
    """Defence in depth: the pipeline never puts a practice attempt up for review."""
    repo = Repository(tmp_path / "r.db")
    stray = Response(response_id="p1", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1")
    repo.save(stray, "SV-1", "PR-COH-A2", account_id="a1", purpose=TaskPurpose.PRACTICE)
    real = Response(response_id="a1", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1")
    repo.save(real, "SV-1", "P3", account_id="a1")
    assert [r["response_id"] for r in repo.queue_with_locks(ResponseStatus.REVIEW_REQUIRED)] == [
        "a1"
    ]


def test_research_rows_exclude_practice(tmp_path):
    repo = Repository(tmp_path / "r.db")
    repo.save(_queued("a1"), "SV-1", "P3", account_id="acc")
    repo.save(_queued("p1"), "SV-1", "PR-COH-A2", account_id="acc", purpose=TaskPurpose.PRACTICE)
    assert [r["response_id"] for r in repo.research_rows({"acc"})] == ["a1"]


def test_practice_summary_counts_processed_attempts_per_criterion(tmp_path):
    db = tmp_path / "r.db"
    repo = Repository(db)
    tasks = TaskRepository(db)
    proc = ResponseProcessor(
        FakeAsrEngine(transcript=COH_TEXT), vad=EnergyVad(), task_lookup=tasks.get
    )
    for rid, acc in (("p1", "a1"), ("p2", "a2")):
        done = proc.process(_req("PR-COH-A2", rid), tone(35), SR)
        repo.save(done, "SV", "PR-COH-A2", account_id=acc, purpose=TaskPurpose.PRACTICE)
    repo.save(_queued("p3"), "SV", "PR-FLU-A2", account_id="a1", purpose=TaskPurpose.PRACTICE)
    summary = repo.practice_summary()
    assert summary["attempts"] == 2 and summary["learners"] == 2 and summary["completed"] == 2
    assert summary["by_criterion"] == {"coherence": {"attempts": 2, "completed": 2}}


def test_speaking_profile_carries_the_practice_task_for_the_weakest_criterion(tmp_path):
    repo = Repository(tmp_path / "h.db")
    repo.save(_scored("r1", Band.B1, [Criterion.FLUENCY], verified=True), "SV-1", "P3", "acc-1")
    repo.save(_scored("r2", Band.B2, [], verified=True), "SV-1", "P3", "acc-1")
    rows = {r["response_id"]: r for r in repo.speaking_profile("acc-1")}
    assert rows["r1"]["next_task_id"] == "PR-FLU-B1"
    assert rows["r1"]["next_task_hint"]  # the old field keeps its meaning
    assert rows["r2"]["next_task_id"] is None and rows["r2"]["next_task_hint"] is None


# ================================================================= pipeline (FR-41)


def _req(task_id: str = "PR-COH-A2", rid: str = "p1") -> ProcessingRequest:
    return ProcessingRequest(
        response_id=rid,
        speaker_id="SV-001",
        task_id=task_id,
        audio_path="unused.wav",
        prompt_version="v1",
        config_version="v1",
    )


def processor(tmp_path, text: str, engine=None, **fake) -> ResponseProcessor:
    tasks = TaskRepository(tmp_path / "task.db")
    asr = engine or FakeAsrEngine(transcript=text, **fake)
    return ResponseProcessor(asr, vad=EnergyVad(), task_lookup=tasks.get)


def test_practice_attempt_is_measured_not_scored_and_not_routed(tmp_path):
    r = processor(tmp_path, COH_TEXT).process(_req(), tone(40), SR)
    assert r.status is ResponseStatus.COMPLETED
    assert r.assessment is None  # no band, no score
    assert r.practice is not None and r.practice.task_id == "PR-COH-A2"
    assert r.practice.completed is True
    used, spoken = r.practice.checks
    assert used.kind is MissionKind.USE_WORDS and used.measured == 4
    assert spoken.kind is MissionKind.SPEAK_SECONDS and spoken.measured == pytest.approx(40, 0.05)


def test_non_english_practice_is_rejected_not_sent_to_a_teacher(tmp_path):
    p = processor(tmp_path, "xin chao cac ban", language="vi", language_probability=0.95)
    r = p.process(_req(), tone(40), SR)
    assert r.status is ResponseStatus.REJECTED and r.reasons == [ReasonCode.LANGUAGE_NOT_ENGLISH]
    assert r.practice is None


def test_non_english_assessment_still_goes_to_a_teacher(tmp_path):
    p = processor(tmp_path, "xin chao cac ban", language="vi", language_probability=0.95)
    r = p.process(_req("P3"), tone(40), SR)
    assert r.status is ResponseStatus.REVIEW_REQUIRED and r.practice is None


def test_practice_with_empty_transcript_is_rejected_with_its_reason(tmp_path):
    r = processor(tmp_path, "   ").process(_req(), tone(40), SR)
    assert r.status is ResponseStatus.REJECTED and r.reasons == [ReasonCode.ASR_EMPTY_TRANSCRIPT]


def test_too_short_practice_is_rejected_by_qc_without_calling_asr(tmp_path):
    class MustNotRun:
        name = "x"

        def transcribe(self, pcm, sr):  # pragma: no cover
            raise AssertionError("ASR must not run when QC rejects")

    r = processor(tmp_path, "", engine=MustNotRun()).process(_req(), tone(10), SR)
    assert r.status is ResponseStatus.REJECTED and ReasonCode.AUDIO_TOO_SHORT in r.reasons
    assert r.practice is None


def test_practice_flagged_by_qc_is_still_measured_and_keeps_the_qc_reason(tmp_path):
    r = processor(tmp_path, COH_TEXT).process(_req(), tone(25), SR)
    assert r.status is ResponseStatus.COMPLETED
    assert ReasonCode.AUDIO_TOO_SHORT in r.reasons
    spoken = r.practice.checks[1]
    assert spoken.met is False  # 25 seconds < the 30-second target


def test_looping_transcript_is_measured_on_the_trimmed_part(tmp_path):
    looped = "I like pho because it is good and cheap " + "so " * 12
    r = processor(tmp_path, looped).process(_req(), tone(40), SR)
    assert r.status is ResponseStatus.COMPLETED
    assert ReasonCode.ASR_HALLUCINATION in r.reasons
    assert r.practice.checks[0].measured <= 3  # the "so so so" loop was cut off


def test_read_aloud_matching_the_reference_is_completed(tmp_path):
    p = processor(tmp_path, PHO_A2.reference_text)
    r = p.process(_req("PR-PHO-A2"), tone(40), SR)
    assert r.status is ResponseStatus.COMPLETED and r.practice.completed is True
    assert r.practice.checks[0].measured == 1.0


def test_assessment_response_has_no_practice_result(tmp_path):
    r = processor(tmp_path, "i think that learning online is useful " * 6).process(
        _req("P3"), tone(40), SR
    )
    assert r.practice is None


# ================================================================= API (FR-40..FR-44)


@pytest.fixture
def m(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", COH_TEXT)
    # Energy VAD on EVERY machine. Silero (present when torch is installed) does not
    # treat a sine wave as speech, so silence missions would differ between a
    # machine with torch and CI.
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    from aicefr.api import main

    importlib.reload(main)
    return main


def login_as(m, pseudonym: str, role: str = "student") -> TestClient:
    from aicefr.storage.auth_repository import Role

    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    one_school(pseudonym, role)
    c = TestClient(m.app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200
    return c


def submit(c: TestClient, task: str, seconds: float = 35.0, expect: int = 202) -> str | None:
    r = c.post(
        "/api/v1/responses",
        files={"audio": ("attempt.wav", wav(seconds), "audio/wav")},
        data={"task_id": task},
    )
    assert r.status_code == expect, r.text
    return r.json().get("response_id") if expect == 202 else None


def test_every_practice_endpoint_requires_login(m):
    anon = TestClient(m.app)
    for url in (
        "/api/v1/practice",
        "/api/v1/practice/tasks/PR-FLU-A2",
        "/api/v1/practice/attempts/x",
    ):
        assert anon.get(url).status_code == 401, url


def test_new_learner_gets_an_a2_suggestion_and_the_full_path(m):
    body = login_as(m, "SV-001").get("/api/v1/practice").json()
    assert body["recommendation"]["task_id"] == "PR-FLU-A2"
    assert body["recommendation"]["basis"] == "no_assessment"
    assert body["assessment"] is None and body["review"] == []
    assert [row["criterion"] for row in body["path"]] == [
        "fluency",
        "coherence",
        "range",
        "accuracy",
        "phonology",
    ]
    assert all(
        [t["band"] for t in row["tasks"]] == ["A1", "A2", "B1", "B2", "C1", "C2"]
        for row in body["path"]
    )
    assert body["daily"]["today"] == 0 and body["daily"]["streak"] == 0
    assert len(body["daily"]["week"]) == 7
    assert body["totals"] == {"tasks": 30, "completed": 0, "attempts": 0}


def test_practice_tasks_never_appear_in_the_assessment_task_list(m):
    ids = [t["task_id"] for t in login_as(m, "SV-001").get("/api/v1/tasks").json()]
    assert ids and not any(i.startswith("PR-") for i in ids)


def test_task_detail_returns_missions_tips_and_passage(m):
    c = login_as(m, "SV-001")
    t = c.get("/api/v1/practice/tasks/PR-PHO-A2").json()
    assert t["criterion"] == "phonology" and t["band"] == "A2" and t["status"] == "new"
    assert t["reference_text"] and t["tips"] and t["history"] == []
    assert t["missions"][0]["kind"] == "read_aloud"
    words = c.get("/api/v1/practice/tasks/PR-COH-A2").json()["missions"][0]["words"]
    assert words == ["and", "but", "because", "so", "also"]


@pytest.mark.parametrize("task_id", ["P3", "NO-SUCH-TASK"])
def test_task_detail_rejects_assessment_and_unknown_tasks(m, task_id):
    assert login_as(m, "SV-001").get(f"/api/v1/practice/tasks/{task_id}").status_code == 404


def test_practice_submission_gets_a_result_without_band_and_skips_the_queue(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2")

    status = student.get(f"/api/v1/responses/{rid}/status").json()
    assert status["status"] == "COMPLETED" and status["purpose"] == "practice"
    assert status["task_id"] == "PR-COH-A2" and status["overall_band"] is None

    body = student.get(f"/api/v1/practice/attempts/{rid}").json()
    assert body["is_pending"] is False and body["reasons"] == []
    assert body["result"]["completed"] is True
    assert body["result"]["met_count"] == body["result"]["total"] == 2
    words = body["result"]["checks"][0]
    assert {h["text"] for h in words["hits"]} == {"and", "but", "because", "so"}
    assert all(h["start_s"] is not None for h in words["hits"])
    assert words["measured_text"] and body["result"]["takeaway"]
    assert body["daily"]["today"] == 1 and body["daily"]["streak"] == 1
    assert body["next"]["task_id"] != "PR-COH-A2"

    mine = student.get("/api/v1/me/responses").json()
    assert [(r["response_id"], r["purpose"]) for r in mine] == [(rid, "practice")]

    teacher = login_as(m, "GV-01", "teacher")
    assert rid not in {r["response_id"] for r in teacher.get("/api/v1/review/queue").json()}

    hub = student.get("/api/v1/practice").json()
    coherence = next(r for r in hub["path"] if r["criterion"] == "coherence")
    assert coherence["tasks"][1]["status"] == "completed"  # [0] is A1
    assert hub["totals"] == {"tasks": 30, "completed": 1, "attempts": 1}


def test_completing_the_suggested_task_moves_the_suggestion_on(m):
    student = login_as(m, "SV-001")
    first = student.get("/api/v1/practice").json()["recommendation"]["task_id"]
    submit(student, first)  # 35-second sine: continuous speech, no silence
    after = student.get("/api/v1/practice").json()["recommendation"]
    assert first == "PR-FLU-A2" and after["task_id"] == "PR-FLU-B1"


def test_practice_is_accepted_straight_after_signing_in(m):
    """D064: no terms step; a new learner's first practice is taken."""
    student = login_as(m, "SV-001")
    assert submit(student, "PR-COH-A2") is not None


def test_submission_to_an_unknown_task_is_refused(m):
    submit(login_as(m, "SV-001"), "PR-NO-SUCH-TASK", expect=422)


def test_qc_rejected_practice_counts_toward_neither_goal_nor_path(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2", seconds=10)
    body = student.get(f"/api/v1/practice/attempts/{rid}").json()
    assert body["status"] == "REJECTED" and body["result"] is None
    assert "AUDIO_TOO_SHORT" in body["reasons"]
    assert body["daily"]["today"] == 0
    hub = student.get("/api/v1/practice").json()
    coherence = next(r for r in hub["path"] if r["criterion"] == "coherence")
    assert coherence["tasks"][0]["status"] == "new" and hub["totals"]["attempts"] == 0
    detail = student.get("/api/v1/practice/tasks/PR-COH-A2").json()
    assert [h["status"] for h in detail["history"]] == ["REJECTED"]


def test_second_attempt_compares_with_the_previous_one_on_the_same_task(m):
    student = login_as(m, "SV-001")
    first = submit(student, "PR-COH-A2")
    second = submit(student, "PR-COH-A2")
    body = student.get(f"/api/v1/practice/attempts/{second}").json()
    assert body["result"]["previous_response_id"] == first
    assert body["result"]["checks"][0]["previous"] == 4
    earlier = student.get(f"/api/v1/practice/attempts/{first}").json()
    assert earlier["result"]["previous_response_id"] is None
    assert earlier["result"]["checks"][0]["previous"] is None


def test_only_the_owner_can_open_a_practice_result(m):
    rid = submit(login_as(m, "SV-001"), "PR-COH-A2")
    assert login_as(m, "SV-002").get(f"/api/v1/practice/attempts/{rid}").status_code == 404
    teacher = login_as(m, "GV-01", "teacher")
    assert teacher.get(f"/api/v1/practice/attempts/{rid}").status_code == 404


def test_assessment_response_cannot_be_opened_as_practice(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "P3")
    assert student.get(f"/api/v1/practice/attempts/{rid}").status_code == 404
    assert student.get("/api/v1/practice/attempts/no-such-id").status_code == 404


def test_deleting_your_practice_attempt_removes_it_from_the_path(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2")
    assert student.delete(f"/api/v1/responses/{rid}").status_code == 200
    assert student.get(f"/api/v1/practice/attempts/{rid}").status_code == 404
    assert student.get("/api/v1/practice").json()["totals"]["attempts"] == 0


def test_class_stats_keep_practice_apart_from_scoring_numbers(m):
    student = login_as(m, "SV-001")
    submit(student, "P3")
    submit(student, "PR-COH-A2")
    stats = login_as(m, "GV-01", "teacher").get("/api/v1/review/stats").json()
    assert stats["responses"] == 1
    assert [t["task_id"] for t in stats["by_task"]] == ["P3"]
    assert stats["practice"]["attempts"] == 1 and stats["practice"]["learners"] == 1
    assert stats["practice"]["by_criterion"]["coherence"] == {"attempts": 1, "completed": 1}


def test_admin_research_export_excludes_practice(m):
    student = login_as(m, "SV-001")
    assessment_id = submit(student, "P3")
    submit(student, "PR-COH-A2")
    body = login_as(m, "AD-01", "admin").get("/api/v1/admin/export/research.json").json()
    assert [r["response_id"] for r in body["rows"]] == [assessment_id]


def test_personal_export_includes_practice_and_explains_the_field(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2")
    body = student.get("/api/v1/me/export.json").json()
    assert "practice" in body["fields"]
    item = next(r for r in body["responses"] if r["response_id"] == rid)
    assert item["practice"]["completed"] is True and item["assessment"] is None


def test_progress_and_profile_ignore_practice(m):
    student = login_as(m, "SV-001")
    submit(student, "PR-COH-A2")
    assert student.get("/api/v1/me/progress").json()["results"] == []
    assert student.get("/api/v1/me/profile.json").json()["results"] == []


def test_suggestion_follows_the_weakest_criterion_of_the_latest_assessment(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "P3")
    assert m.repo.save(_scored(rid, Band.B1, [Criterion.RANGE]), "", "")
    body = student.get("/api/v1/practice").json()
    assert body["recommendation"]["task_id"] == "PR-RAN-B1"
    assert body["recommendation"]["basis"] == "weakest_criterion"
    assert body["assessment"]["band"] == "B1"
    assert body["assessment"]["weakest_criteria"] == ["range"]


def test_practice_pages_mark_navigation_and_load_their_scripts(m):
    student = login_as(m, "SV-001")
    hub = student.get("/practice").text
    assert 'href="/practice" aria-current="page"' in hub and "practice_path.js?v=" in hub
    # D068: practice tasks are folded into the lesson path; an old link goes there.
    gone = student.get("/practice/PR-COH-A2", follow_redirects=False)
    assert gone.status_code == 301 and gone.headers["location"] == "/practice"
    result = student.get("/practice/results/abc123").text
    assert 'data-response-id="abc123"' in result and "practice_result.js?v=" in result
    assert (
        "Luyện tập" not in TestClient(m.app).get("/").text.split("site-nav")[1].split("</nav>")[0]
    )


def test_progress_page_sends_practice_to_the_practice_result(m):
    """progress.js reads `purpose` from the status endpoint, so the endpoint must return it."""
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2")
    assert student.get(f"/api/v1/responses/{rid}/status").json()["purpose"] == "practice"
    from aicefr.api.web import STATIC_DIR

    source = (STATIC_DIR / "progress.js").read_text(encoding="utf-8")
    assert "/practice/results/" in source and 'd.purpose === "practice"' in source


def test_practice_report_json_round_trips_into_a_response(m):
    student = login_as(m, "SV-001")
    rid = submit(student, "PR-COH-A2")
    raw = student.get(f"/api/v1/responses/{rid}").json()
    again = Response.model_validate_json(json.dumps(raw))
    assert again.practice is not None and again.practice.completed is True
