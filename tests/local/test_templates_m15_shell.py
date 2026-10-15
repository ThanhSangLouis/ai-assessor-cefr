from __future__ import annotations

import re
from datetime import UTC, datetime
from html.parser import HTMLParser

from aicefr.api.student import StudentStatus
from aicefr.api.templates import (
    LOCAL_CSS,
    _document,
    render_consent,
    render_login,
    render_notice,
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


class _LandmarkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_links: list[dict[str, str | None]] = []
        self.mains: list[dict[str, str | None]] = []
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "a" and "skip-link" in (attr_dict.get("class") or "").split():
            self.skip_links.append(attr_dict)
        elif tag == "main":
            self.mains.append(attr_dict)
        elif tag == "h1":
            self.h1_count += 1


def test_css_tokens_contain_surface_text_action_and_states() -> None:
    required_tokens = (
        "--surface-bg",
        "--surface-card",
        "--surface-subtle",
        "--text-primary",
        "--text-secondary",
        "--text-muted",
        "--text-inverse",
        "--border-color",
        "--border-subtle",
        "--border-strong",
        "--primary",
        "--primary-hover",
        "--primary-active",
        "--primary-subtle",
        "--focus-ring",
        "--focus-offset",
        "--error-text",
        "--error-bg",
        "--error-border",
        "--disabled-bg",
        "--disabled-text",
        "--disabled-border",
        "--radius-sm",
        "--radius-md",
        "--shadow-sm",
        "--shadow-md",
        "--shell-max-width",
    )
    for token in required_tokens:
        assert token in LOCAL_CSS, f"Missing required CSS token: {token}"


def test_css_includes_dark_mode_contrast_tokens() -> None:
    assert "@media (prefers-color-scheme: dark)" in LOCAL_CSS
    dark_section_match = re.search(
        r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{([^}]+)\}",
        LOCAL_CSS,
        re.DOTALL,
    )
    assert dark_section_match is not None
    dark_css = dark_section_match.group(1)
    assert "--surface-bg" in dark_css
    assert "--surface-card" in dark_css
    assert "--text-primary" in dark_css
    assert "--primary" in dark_css
    assert "--error-text" in dark_css


def test_css_includes_reduced_motion_and_print() -> None:
    assert "@media (prefers-reduced-motion: reduce)" in LOCAL_CSS
    assert "animation-duration: 0.01ms !important" in LOCAL_CSS

    assert "@media print" in LOCAL_CSS
    assert ".skip-link" in LOCAL_CSS
    assert "display: none !important" in LOCAL_CSS


def test_css_responsive_and_touch_target_rules() -> None:
    assert "min-height: 2.75rem" in LOCAL_CSS
    assert "overflow-wrap: anywhere" in LOCAL_CSS
    assert "word-break: break-word" in LOCAL_CSS
    assert "@media (max-width: 480px)" in LOCAL_CSS
    assert ":focus-visible" in LOCAL_CSS


def test_document_skip_link_and_main_landmark_integrity() -> None:
    html = _document("Tiêu đề kiểm thử <an toàn>", "<p>Nội dung</p>")
    parser = _LandmarkParser()
    parser.feed(html)
    parser.close()

    assert len(parser.skip_links) == 1
    assert parser.skip_links[0].get("href") == "#main"
    assert len(parser.mains) == 1
    assert parser.mains[0].get("id") == "#main" or parser.mains[0].get("id") == "main"
    assert parser.h1_count == 1
    assert "Tiêu đề kiểm thử &lt;an toàn&gt;" in html
    assert '<html lang="vi">' in html


def test_all_rendered_pages_have_skip_link_and_main_target() -> None:
    report = DiagnosticReport(
        response_id="b" * 32,
        status=ReportStatus.PROVISIONAL,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        criteria=tuple(CriterionCoverage(criterion=c) for c in Criterion),
        interaction=Interaction(),
        reasons=(ReasonCode.ASR_FAILED,),
    )
    candidate = ReviewCandidate(
        response_id="b" * 32,
        response_revision=1,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        reasons=(ReasonCode.ASR_FAILED,),
        source_versions={"model": "fixture"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    status = StudentStatus(
        response_id=report.response_id,
        status=ResponseStatus.COMPLETED,
        revision=1,
        report_available=True,
    )
    pages = [
        render_upload_form(demo=True),
        render_login(demo=True),
        render_consent("v1", active=True, demo=True),
        render_student_status(status, demo=True),
        render_notice("Thông báo", "Nội dung thông báo"),
        render_report(report, demo=True),
        render_review_queue((candidate,), demo=True),
        render_review_detail(candidate, report, demo=True),
    ]
    for page_html in pages:
        parser = _LandmarkParser()
        parser.feed(page_html)
        parser.close()
        assert len(parser.skip_links) == 1, "Page missing skip link"
        assert parser.skip_links[0].get("href") == "#main"
        assert len(parser.mains) == 1, "Page missing main landmark"
        assert parser.mains[0].get("id") == "main"
        assert parser.h1_count == 1, "Page must have exactly one H1"


def test_template_branches_and_edge_cases() -> None:
    # 1. Report with overall score and teacher final
    from aicefr.contracts import Band, ReviewAction
    from aicefr.report.contracts import (
        DiagnosticComment,
        EvidenceIssue,
        EvidenceRef,
        EvidenceSource,
        TeacherFinalResult,
    )

    report = DiagnosticReport(
        response_id="c" * 32,
        status=ReportStatus.TEACHER_VERIFIED,
        assessment_status=AssessmentStatus.ESTIMATED,
        overall_score=4.5,
        overall_band=Band.B2,
        criteria=tuple(CriterionCoverage(criterion=c) for c in Criterion),
        interaction=Interaction(),
        teacher_verified=True,
        teacher_final=TeacherFinalResult(
            action=ReviewAction.OVERRIDE,
            overall_band=Band.B2,
            reason="Teacher override approved",
            audit_id="f" * 32,
            recorded_at="2026-10-15T12:00:00Z",
        ),
        comments=(
            DiagnosticComment(
                criterion=Criterion.FLUENCY,
                text="Tốt",
                evidence_id="ev-1",
                source=EvidenceSource.FEATURE_SET,
            ),
        ),
        evidence_refs=(
            EvidenceRef(
                evidence_id="ev-1",
                response_id="c" * 32,
                source=EvidenceSource.FEATURE_SET,
                source_version="v1",
                criterion=Criterion.FLUENCY,
                start_s=1.25,
                end_s=3.5,
            ),
        ),
        evidence_issues=(EvidenceIssue(evidence_id="ev-2", reason="Mất tiếng"),),
    )
    report_html = render_report(report, demo=False)
    assert "4.50 (B2)" in report_html
    assert "Đã có giảng viên duyệt" in report_html
    assert "Teacher override approved" in report_html
    assert "Nghe tại 1.25s" in report_html
    assert "Mất tiếng" in report_html

    # 2. Upload form with error and recording enabled
    upload_html = render_upload_form(
        error="Tệp quá lớn",
        demo=False,
        tasks=[{"task_id": "t1", "task_version": "1", "title": "Bài 1", "prompt_text": "Nói"}],
        selected={"task_id": "t1", "task_version": "1"},
        recording_enabled=True,
    )
    assert '<p role="alert">Tệp quá lớn</p>' in upload_html
    assert "Bài 1" in upload_html
    assert 'data-recording-enabled="true"' in upload_html

    # 3. Student status queued (meta refresh)
    st = StudentStatus(
        response_id="c" * 32,
        status=ResponseStatus.QUEUED,
        revision=1,
        report_available=False,
        reason=ReasonCode.ASR_FAILED,
    )
    status_html = render_student_status(st, demo=False)
    assert '<meta http-equiv="refresh" content="5">' in status_html
    assert "ASR_FAILED" in status_html
    assert "Báo cáo chưa sẵn sàng" in status_html

    # 4. Review queue empty
    queue_empty_html = render_review_queue((), demo=False)
    assert "Không có bài cần duyệt." in queue_empty_html

    # 5. Review detail completed state (reopen form)
    from aicefr.contracts import ReviewState

    candidate_done = ReviewCandidate(
        response_id="c" * 32,
        response_revision=3,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        reasons=(ReasonCode.ASR_FAILED,),
        source_versions={"model": "fixture"},
        state=ReviewState.APPROVED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    detail_done_html = render_review_detail(candidate_done, None, demo=False, audio_available=False)
    assert "Mở lại để hiệu chỉnh" in detail_done_html
    assert "Audio đã được xóa theo retention." in detail_done_html
