from __future__ import annotations

from datetime import UTC, datetime
from html.parser import HTMLParser

from aicefr.api.student import StudentStatus
from aicefr.api.templates import (
    render_report,
    render_review_detail,
    render_review_queue,
    render_student_status,
    render_upload_form,
)
from aicefr.contracts import (
    AssessmentStatus,
    Criterion,
    CriterionCoverage,
    Interaction,
    ReasonCode,
    ResponseStatus,
    ReviewCandidate,
)
from aicefr.report.contracts import DiagnosticReport, ReportStatus


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts = {name: 0 for name in ("html", "head", "body")}
        self.viewport = False

    def handle_starttag(self, tag, attrs):
        if tag in self.counts:
            self.counts[tag] += 1
        if tag == "meta" and dict(attrs).get("name") == "viewport":
            self.viewport = True


def _assert_one_mobile_document(document: str) -> None:
    parser = _DocumentParser()
    parser.feed(document)
    parser.close()
    assert parser.counts == {"html": 1, "head": 1, "body": 1}
    assert parser.viewport
    assert 'href="/local.css"' in document
    assert '<a href="#main" class="skip-link">Chuyển đến nội dung chính</a>' in document
    assert '<main id="main">' in document


def _report() -> DiagnosticReport:
    return DiagnosticReport(
        response_id="a" * 32,
        status=ReportStatus.PROVISIONAL,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        criteria=tuple(CriterionCoverage(criterion=item) for item in Criterion),
        interaction=Interaction(),
        reasons=(ReasonCode.ASR_FAILED,),
    )


def _candidate() -> ReviewCandidate:
    now = datetime.now(UTC)
    return ReviewCandidate(
        response_id="a" * 32,
        response_revision=2,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        reasons=(ReasonCode.ASR_FAILED,),
        source_versions={"model": "unavailable"},
        created_at=now,
        updated_at=now,
    )


def test_student_and_teacher_pages_have_one_valid_document_and_mobile_stylesheet():
    report = _report()
    candidate = _candidate()
    status = StudentStatus(
        response_id=report.response_id,
        status=ResponseStatus.REVIEW_REQUIRED,
        revision=2,
        report_available=True,
    )
    pages = (
        render_upload_form(demo=True),
        render_student_status(status, demo=True),
        render_report(report, demo=True),
        render_review_queue((candidate,), demo=True),
        render_review_detail(candidate, report, demo=True),
    )
    for page in pages:
        _assert_one_mobile_document(page)
        assert "dữ liệu kiểm thử do nhóm tạo" in page
    detail = pages[-1]
    assert '<section aria-labelledby="report-heading">' in detail
    assert detail.count("Đăng xuất") == 1
