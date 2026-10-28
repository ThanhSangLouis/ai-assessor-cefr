from __future__ import annotations

from datetime import date, timedelta

import pytest
from assessment_fixture import asgi, build_assessment_service, headers
from conftest import feature_set
from fastapi.testclient import TestClient

from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    CriterionCoverage,
    QcResult,
    QcStatus,
    Response,
    Status,
    TaskPurpose,
    Transcript,
    Word,
)
from aicefr.report.bands import ASPECTS, Provenance
from aicefr.report.comments import CommentBuilder
from aicefr.report.evidence import EvidenceBuilder
from aicefr.services.core.assessment import context
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.repository import Repository


@pytest.fixture
def assessment_service(tmp_path, monkeypatch, request):
    return build_assessment_service(tmp_path, monkeypatch, request)


def test_assessment_api_registers_the_migrated_response_review_admin_and_class_routes(
    assessment_service,
):
    parts, _settings = assessment_service
    paths = {route.path for router in parts.routers for route in getattr(router, "routes", ())}

    assert "/api/v1/responses" in paths
    assert "/api/v1/review/queue" in paths
    assert "/api/v1/admin/models" in paths
    assert "/api/v1/classes/{class_id}/assignments" in paths
    assert "/api/v1/me/assignments" in paths


def test_class_assignment_query_omits_practice_and_handles_no_members(tmp_path):
    repo = Repository(tmp_path / "assessment.db")
    repo.save(
        Response(response_id="assessment-1", status=Status.COMPLETED, config_version="v1"),
        "SV-001",
        "P3",
        account_id="student-1",
    )
    repo.save(
        Response(response_id="practice-1", status=Status.COMPLETED, config_version="v1"),
        "SV-001",
        "P3",
        account_id="student-1",
        purpose=TaskPurpose.PRACTICE,
    )

    rows = repo.assessments_since(["student-1", "student-2"], "P3", "2000-01-01")

    assert [row["response_id"] for row in rows] == ["assessment-1"]
    assert rows[0]["account_id"] == "student-1"
    assert repo.assessments_since([], "P3", "2000-01-01") == []


def test_band_descriptors_distinguish_unmeasured_and_out_of_scope_aspects():
    aspects = {aspect.key: aspect for aspect in ASPECTS}

    assert aspects["accuracy"].provenance is Provenance.NOT_MEASURED
    assert aspects["interaction"].provenance is Provenance.NOT_ASSESSED


def test_student_can_join_a_class_and_see_its_open_assignment(assessment_service):
    parts, settings = assessment_service
    app = asgi(parts, settings)
    teacher = Account("teacher-1", "GV-01", Role.TEACHER)
    student = Account("student-1", "SV-001", Role.STUDENT)

    with TestClient(app) as client:
        made = client.post(
            "/api/v1/classes",
            json={"name": "Lớp kiểm thử"},
            headers=headers(teacher),
        )
        assert made.status_code == 200, made.text
        class_info = made.json()

        joined = client.post(
            "/api/v1/me/classes/join",
            json={"code": class_info["code"].lower()},
            headers=headers(student),
        )
        assert joined.status_code == 200, joined.text

        due_on = (date.today() + timedelta(days=1)).isoformat()
        assigned = client.post(
            f"/api/v1/classes/{class_info['class_id']}/assignments",
            json={"task_id": "P3", "due_on": due_on},
            headers=headers(teacher),
        )
        assert assigned.status_code == 200, assigned.text

        mine = client.get("/api/v1/me/assignments", headers=headers(student))
        assert mine.status_code == 200, mine.text
        assert mine.json()["todo"][0]["state"] == "open"
        assert mine.json()["todo"][0]["task_id"] == "P3"


def test_teacher_review_queue_and_admin_stats_are_wired(assessment_service):
    parts, settings = assessment_service
    app = asgi(parts, settings)
    teacher = Account("teacher-1", "GV-01", Role.TEACHER)
    admin = Account("admin-1", "QT-01", Role.ADMIN)

    with TestClient(app) as client:
        queue = client.get("/api/v1/review/queue", headers=headers(teacher))
        assert queue.status_code == 200, queue.text
        assert queue.json() == []

        stats = client.get("/api/v1/stats", headers=headers(admin))
        assert stats.status_code == 200, stats.text
        assert stats.json()["total"] == 0


def test_submission_requires_consent_before_writing_audio_or_response(assessment_service):
    parts, settings = assessment_service
    context.svc().peers.identity.consent = lambda *, account_id: None
    student = Account("student-1", "SV-001", Role.STUDENT)
    with TestClient(asgi(parts, settings)) as client:
        denied = client.post(
            "/api/v1/responses",
            files={"audio": ("recording.wav", b"RIFF" + b"0" * 40, "audio/wav")},
            headers=headers(student),
        )
        assert denied.status_code == 403
        assert context.svc().repo.stats()["total"] == 0


def test_submission_persists_a_queued_response_in_mongodb(assessment_service):
    parts, settings = assessment_service
    student = Account("student-1", "SV-001", Role.STUDENT)
    with TestClient(asgi(parts, settings)) as client:
        accepted = client.post(
            "/api/v1/responses",
            files={"audio": ("recording.wav", b"RIFF" + b"0" * 40, "audio/wav")},
            headers=headers(student),
        )
        assert accepted.status_code == 202, accepted.text
        rid = accepted.json()["response_id"]
        saved = context.svc().repo.get(rid)
        assert saved is not None
        assert saved.status is Status.QUEUED
        assert context.svc().repo.owner_of(rid) == student.account_id


def test_report_endpoint_returns_traceable_comments_and_evidence(assessment_service):
    parts, settings = assessment_service
    features = feature_set(
        {
            "n_words": 40.0,
            "words_per_sec": 1.4,
            "total_dur": 30.0,
            "ttr": 0.45,
            "vad_pause_per_min": 12.0,
            "asr_conf_mean": 0.88,
        }
    )
    transcript = Transcript(
        text="hello there um friend",
        words=[
            Word(text="hello", start_s=0.0, end_s=0.4, prob=0.95),
            Word(text="there", start_s=0.5, end_s=0.9, prob=0.92),
            Word(text="um", start_s=1.0, end_s=1.2, prob=0.9),
            Word(text="friend", start_s=2.5, end_s=2.9, prob=0.25),
        ],
        engine="fake",
        model_version="v1",
        has_word_timestamps=True,
        is_verbatim=True,
    )
    evidence = EvidenceBuilder().build(transcript, features, [(0.0, 1.2), (2.5, 3.0)])
    comments = CommentBuilder().comments(features, evidence, 0.88, [])
    priorities = CommentBuilder().priorities({"ttr": -0.4}, 0.88)
    assessment = Assessment(
        overall_0_6=3.4,
        overall_band=Band.B1,
        criteria=[CriterionCoverage(criterion=c, coverage=1.0) for c in Criterion],
        evidence=evidence,
        comments=comments,
        priorities=priorities,
        model_version="v1",
    )
    report = Response(
        response_id="report-1",
        status=Status.COMPLETED,
        qc=QcResult(
            duration_ms=30_000,
            sample_rate_hz=16_000,
            channels=1,
            silence_ratio=0.1,
            clipping_ratio=0.0,
            qc_status=QcStatus.PASS,
        ),
        asr=transcript,
        features=features,
        assessment=assessment,
        config_version="v1",
    )
    context.svc().repo.save(report, "SV-001", "P3", account_id="student-1")

    student = Account("student-1", "SV-001", Role.STUDENT)
    with TestClient(asgi(parts, settings)) as client:
        result = client.get("/api/v1/responses/report-1", headers=headers(student))
    assert result.status_code == 200, result.text
    assessment_json = result.json()["assessment"]
    ids = {row["evidence_id"] for row in assessment_json["evidence"]}
    assert assessment_json["comments"]
    assert all(set(row["evidence_refs"]) <= ids for row in assessment_json["comments"])
    assert assessment_json["priorities"][0]["feature_name"] == "ttr"


def test_review_queue_includes_pending_response_and_teacher_can_lock_it(assessment_service):
    parts, settings = assessment_service
    report = Response(
        response_id="needs-review",
        status=Status.REVIEW_REQUIRED,
        assessment=Assessment(
            overall_0_6=3.4,
            overall_band=Band.B1,
            criteria=[CriterionCoverage(criterion=c, coverage=1.0) for c in Criterion],
            model_version="v1",
        ),
        config_version="v1",
    )
    context.svc().repo.save(report, "SV-001", "P3", account_id="student-1")
    teacher = Account("teacher-1", "GV-01", Role.TEACHER)

    with TestClient(asgi(parts, settings)) as client:
        queue = client.get("/api/v1/review/queue", headers=headers(teacher))
        assert queue.status_code == 200, queue.text
        assert [item["response_id"] for item in queue.json()] == ["needs-review"]
        locked = client.post("/api/v1/review/needs-review/lock", headers=headers(teacher))
        assert locked.status_code == 200, locked.text


def test_admin_can_read_runtime_config(assessment_service):
    parts, settings = assessment_service
    admin = Account("admin-1", "QT-01", Role.ADMIN)
    with TestClient(asgi(parts, settings)) as client:
        config = client.get("/api/v1/admin/config", headers=headers(admin))
    assert config.status_code == 200, config.text
    assert config.json()["qc_config_version"] == "qc-v1"
