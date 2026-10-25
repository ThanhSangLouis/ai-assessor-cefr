from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import numpy as np
import soundfile as sf

from aicefr.api.review import ReviewApi
from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import (
    ActorRole,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Interaction,
    ReasonCode,
    ReviewCandidate,
)
from aicefr.local.app import SQLiteSessionRepository
from aicefr.report.contracts import DiagnosticReport, ReportStatus
from aicefr.review.service import ReviewService
from aicefr.review.sqlite import SQLiteReviewRepository
from aicefr.storage.blob import BlobStore
from aicefr.storage.service import ResponseService
from aicefr.storage.sqlite import SQLiteStore


class _UnusedStudentBoundary:
    def submit(self, token, request):  # pragma: no cover
        raise AssertionError("student upload is not part of this request")


def _wsgi(app, path: str, cookie: str) -> tuple[str, dict[str, str], bytes]:
    result: dict[str, object] = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "CONTENT_LENGTH": "0",
        "CONTENT_TYPE": "",
        "HTTP_COOKIE": cookie,
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(),
    }

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = dict(headers)

    body = b"".join(app(environ, start_response))
    return str(result["status"]), result["headers"], body


def test_teacher_audio_requires_teacher_session_and_review_candidate(tmp_path):
    store = SQLiteStore(tmp_path / "data")
    session_repo = SQLiteSessionRepository(store)
    auth = AuthService(store, session_repo)
    auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "student-password")
    auth.bootstrap_fixture_account("fixture-teacher", ActorRole.TEACHER, "teacher-password")
    consent = ConsentService(store)
    student = auth.resolve(auth.login("fixture-student", "student-password"))
    consent.activate(student, "v1", audio_storage_allowed=True)
    buffer = BytesIO()
    sf.write(buffer, np.ones(16_000, dtype=np.float32) * 0.1, 16_000, format="WAV")
    response_service = ResponseService(store, BlobStore(store.data_dir, max_bytes=100_000), consent)
    response = response_service.submit(
        student,
        task_id="demo-task",
        task_version="1",
        consent_version="v1",
        audio_bytes=buffer.getvalue(),
    )
    reviews = SQLiteReviewRepository(store)
    reviews.add(
        ReviewCandidate(
            response_id=response.response_id,
            response_revision=response.revision,
            assessment_status=AssessmentStatus.NOT_EVALUATED,
            reasons=(ReasonCode.ASR_FAILED,),
            source_versions={"model": "unavailable"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    report = DiagnosticReport(
        response_id=response.response_id,
        status=ReportStatus.PROVISIONAL,
        assessment_status=AssessmentStatus.ESTIMATED,
        overall_score=3.1,
        overall_band=Band.B1,
        criteria=tuple(CriterionCoverage(criterion=item) for item in Criterion),
        interaction=Interaction(),
    )
    app = StudentTeacherApp(
        StudentApi(_UnusedStudentBoundary()),
        review_api=ReviewApi(auth, ReviewService(reviews)),
        auth=auth,
        responses=response_service,
        reviews=reviews,
        reports=type("Reports", (), {"get": lambda self, response_id: report})(),
    )
    student_token = auth.login("fixture-student", "student-password")
    teacher_token = auth.login("fixture-teacher", "teacher-password")

    denied, _, denied_body = _wsgi(
        app,
        f"/teacher/reviews/{response.response_id}/audio",
        f"aicefr_session={student_token}",
    )
    assert denied.startswith("403")
    assert b"blobs" not in denied_body
    detail_denied, _, _ = _wsgi(
        app,
        f"/teacher/reviews/{response.response_id}",
        f"aicefr_session={student_token}",
    )
    assert detail_denied.startswith("403")

    missing, _, missing_body = _wsgi(
        app,
        "/teacher/reviews/00000000000000000000000000000000/audio",
        f"aicefr_session={teacher_token}",
    )
    assert missing.startswith("404")
    assert b"blobs" not in missing_body

    allowed, headers, audio = _wsgi(
        app,
        f"/teacher/reviews/{response.response_id}/audio",
        f"aicefr_session={teacher_token}",
    )
    assert allowed.startswith("200")
    assert headers["Content-Type"] == "audio/wav"
    assert audio == buffer.getvalue()
    detail, _, detail_body = _wsgi(
        app,
        f"/teacher/reviews/{response.response_id}",
        f"aicefr_session={teacher_token}",
    )
    assert detail.startswith("200")
    detail_text = detail_body.decode()
    assert "Duyệt bài" in detail_text
    assert "Overall: 3.10 (B1)" in detail_text
    assert "Kết quả tạm thời" in detail_text
