"""Small semantic HTML renderers for the student and teacher browser flow."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING
from urllib.parse import quote

from aicefr.api.student import StudentStatus

if TYPE_CHECKING:
    from aicefr.contracts import ReviewCandidate
    from aicefr.report.contracts import DiagnosticReport


LOCAL_CSS = """\
:root { color-scheme: light; font-family: system-ui, sans-serif; line-height: 1.5; }
* { box-sizing: border-box; }
body { margin: 0; padding: 1rem; color: #182230; background: #f6f8fb; }
main { width: 100%; max-width: 52rem; margin: 0 auto; padding: 1rem; background: #fff; }
h1, h2 { line-height: 1.2; }
p, dd, li { overflow-wrap: anywhere; }
label { display: block; margin: .8rem 0 .25rem; font-weight: 600; }
input:not([type=file]), select, textarea {
  display: block; width: 100%; max-width: 32rem;
  min-height: 2.75rem; padding: .55rem; font: inherit;
}
input[type=file] { display: block; max-width: 100%; padding: .4rem 0; }
textarea { min-height: 5rem; }
button {
  min-height: 2.75rem; margin: .45rem .35rem .45rem 0;
  padding: .55rem .9rem; font: inherit;
}
a { color: #0759a5; }
:focus-visible { outline: 3px solid #1264a3; outline-offset: 2px; }
form { margin: 1rem 0; }
nav { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1rem; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
audio { width: 100%; }
input[type=checkbox] { display: inline; width: auto; min-height: auto; }
section, li { margin-bottom: 1rem; }
"""


def _document(title: str, body: str, *, refresh: bool = False) -> str:
    refresh_tag = '<meta http-equiv="refresh" content="5">' if refresh else ""
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{refresh_tag}
<title>{escape(title)}</title><link rel="stylesheet" href="/local.css"></head>
<body><main><h1>{escape(title)}</h1>{body}</main></body></html>"""


def _demo_note(demo: bool) -> str:
    if not demo:
        return ""
    return (
        '<p class="demo-note"><strong>Trình diễn local:</strong> chỉ dùng tài khoản '
        "fixture và dữ liệu kiểm thử do nhóm tạo.</p>"
    )


def render_upload_form(
    error: str | None = None,
    *,
    demo: bool = False,
    tasks: list[dict] | None = None,
    selected: dict | None = None,
    consent_version: str = "",
    recording_enabled: bool = False,
    max_seconds: float = 180,
    max_bytes: int = 20_000_000,
) -> str:
    message = f'<p role="alert">{escape(error)}</p>' if error else ""
    from aicefr.portal.templates import nav

    selected = selected or {}
    task_id = escape(selected.get("task_id", ""), quote=True)
    task_version = escape(selected.get("task_version", ""), quote=True)
    prompts = "".join(
        f"<li>{escape(item['title'])} "
        f"({escape(item['task_id'])}/{escape(item['task_version'])}): "
        f"{escape(item['prompt_text'])}</li>"
        for item in (tasks or [])
    )
    body = f"""{nav("student")}{_demo_note(demo)}{message}<ul>{prompts}</ul>
<p>Kết quả là ước lượng phục vụ học tập và có thể cần giảng viên duyệt.</p>
<p>Chỉ tiếp tục khi bạn đã đồng ý xử lý dữ liệu cho bài này.</p>
<p>Có thể rút lại đồng ý tại <a href="/student/consent">trang đồng ý</a>.</p>
<form method="post" action="/student/responses" enctype="multipart/form-data" data-recorder
data-recording-enabled="{str(recording_enabled).lower()}"
data-max-seconds="{max_seconds}" data-max-bytes="{max_bytes}">
<label for="task-id">Mã bài</label><input id="task-id" name="task_id" value="{task_id}" required>
<label for="task-version">Phiên bản bài</label>
<input id="task-version" name="task_version" value="{task_version}" required>
<label for="consent-version">Phiên bản đồng ý</label>
<input id="consent-version" name="consent_version"
value="{escape(consent_version, quote=True)}" required>
<label for="audio">Tệp âm thanh</label>
<input id="audio" name="audio" type="file" accept="audio/*" required>
<section {"hidden" if not recording_enabled else ""} aria-label="Ghi âm trực tiếp">
<button type="button" id="record-start">Bắt đầu ghi âm</button>
<button type="button" id="record-stop" disabled>Dừng ghi âm</button>
<audio id="record-preview" controls hidden></audio></section>
<p id="record-notice" role="status" aria-live="polite">Ghi âm hoặc chọn tệp để nộp bài.</p>
<progress id="upload-progress" max="100" value="0" hidden
aria-label="Tiến trình gửi tệp"></progress>
<button type="submit">Nộp bài</button></form>{render_logout_form()}
<script src="/recorder.js" defer></script>"""
    return _document("Nộp bài nói", body)


def render_login(error: str | None = None, *, demo: bool = False) -> str:
    message = f'<p role="alert">{escape(error)}</p>' if error else ""
    body = f"""{_demo_note(demo)}{message}<form method="post" action="/login">
<label for="actor-id">Tài khoản</label>
<input id="actor-id" name="actor_id" required autocomplete="username">
<label for="password">Mật khẩu</label>
<input id="password" name="password" type="password" required autocomplete="current-password">
<button type="submit">Đăng nhập</button></form>"""
    return _document("Đăng nhập", body)


def render_consent(
    version: str, active: bool, demo: bool, *, research_allowed: bool = False
) -> str:
    from aicefr.portal.templates import nav

    state = "Bạn đã đồng ý phiên bản hiện tại." if active else "Bạn chưa đồng ý phiên bản hiện tại."
    body = f"""{nav("student")}{_demo_note(demo)}<p>{state}</p>
<p>Phiên bản nội dung: {escape(version)}. Bạn có thể rút lại đồng ý bất cứ lúc nào.</p>
<form method="post" action="/student/consent/accept">
<label><input type="checkbox" name="research_allowed" value="true"
{"checked" if research_allowed else ""}>
Cho phép dùng số liệu tổng hợp đã bỏ ID tài khoản cho nghiên cứu (tùy chọn).</label>
<button type="submit">Đồng ý</button></form>
<form method="post" action="/student/consent/withdraw">
<button type="submit">Rút lại đồng ý</button></form>
<p><a href="/student/upload">Nộp bài</a></p>{render_logout_form()}"""
    return _document("Đồng ý xử lý dữ liệu", body)


def render_student_status(status: StudentStatus, *, demo: bool = False) -> str:
    from aicefr.portal.templates import nav

    reason = f"<p>{escape(status.reason)}</p>" if status.reason else ""
    report_link = (
        f'<a href="/student/responses/{escape(status.response_id)}/report">Xem báo cáo</a>'
        if status.report_available
        else "<p>Báo cáo chưa sẵn sàng.</p>"
    )
    body = f"""{nav("student")}{_demo_note(demo)}<dl><dt>Mã bài nộp</dt>
<dd>{escape(status.response_id)}</dd><dt>Trạng thái</dt>
<dd>{escape(status.status.value)}</dd></dl>{reason}{report_link}{render_logout_form()}"""
    return _document(
        "Trạng thái bài nộp", body, refresh=status.status.value in {"QUEUED", "RUNNING"}
    )


def render_notice(title: str, message: str) -> str:
    body = f'<p role="alert">{escape(message)}</p><p><a href="/login">Đăng nhập</a></p>'
    return _document(title, body)


def render_logout_form() -> str:
    return '<form method="post" action="/logout"><button type="submit">Đăng xuất</button></form>'


def render_report_content(report: DiagnosticReport, *, teacher: bool = False) -> str:
    overall = "Chưa đủ điều kiện ước lượng"
    if report.overall_score is not None and report.overall_band is not None:
        overall = f"{report.overall_score:.2f} ({report.overall_band.value})"
    coverage = "".join(_coverage_row(row.criterion.value, row.coverage) for row in report.criteria)
    verification = "Đã có giảng viên duyệt" if report.teacher_verified else "Kết quả tạm thời"
    overall_label = "Overall AI tạm thời" if report.teacher_verified else "Overall"
    teacher_result = ""
    if report.teacher_final is not None:
        final_band = report.teacher_final.overall_band
        final_value = final_band.value if final_band is not None else "Không có band cuối"
        reason = (
            f"<p>Lý do giảng viên: {escape(report.teacher_final.reason)}</p>"
            if report.teacher_final.reason
            else ""
        )
        teacher_result = f"<p>Kết quả giảng viên: {escape(final_value)}</p>{reason}"
    refs = {ref.evidence_id: ref for ref in report.evidence_refs}
    comment_rows = []
    for comment in report.comments:
        reference = refs.get(comment.evidence_id)
        seek = ""
        if reference is not None and reference.start_s is not None:
            seek = (
                f'<button type="button" data-seek-second="{reference.start_s}">'
                f"Nghe tại {reference.start_s:.2f}s</button>"
            )
        comment_rows.append(
            f"<li>{escape(comment.criterion.value)}: {escape(comment.text)} "
            f"<small>Evidence: {escape(comment.evidence_id)} · "
            f"{escape(comment.source.value)}</small>{seek}</li>"
        )
    comments = "".join(comment_rows)
    limitations = "".join(f"<li>{escape(item)}</li>" for item in report.limitations)
    reasons = ", ".join(escape(reason.value) for reason in report.reasons) or "Không có"
    provenance = "".join(
        f"<dt>{escape(key)}</dt><dd>{escape(str(value))}</dd>"
        for key, value in sorted(
            _safe_report_versions(report.source_versions, max_value=100_000).items()
        )
    )
    issues = "".join(
        f"<li>{escape(issue.evidence_id)}: {escape(issue.reason)}</li>"
        for issue in report.evidence_issues
    )
    trust_html = ""
    if report.trust is not None:
        trust_reasons = ", ".join(escape(reason.value) for reason in report.trust.reasons)
        recovery = _student_trust_recovery(report.trust.reasons)
        indicator_rows = "".join(
            _coverage_row(f"{item.name.value} ({item.label})", item.coverage)
            for item in report.criterion_indicators
        )
        trust_html = (
            f"<h3>Độ tin cậy và bước tiếp theo</h3><p>{trust_reasons or 'Chưa có cảnh báo.'}</p>"
            f"<p>{escape(recovery or 'Có thể xem báo cáo như ước lượng tạm thời.')}</p>"
            f"<h3>Chỉ báo theo tiêu chí</h3><ul>{indicator_rows}</ul>"
        )
        if teacher:
            language = report.trust.language
            language_html = ""
            if language is not None:
                confidence = language.confidence if language.confidence is not None else "—"
                language_html = (
                    f"<li>Ngôn ngữ: {escape(language.language or 'unknown')} · "
                    f"{escape(language.method)} {escape(language.version)} · "
                    f"confidence {confidence}</li>"
                )
            guard_rows = "".join(
                "<li>"
                f"{escape(item.kind.value)}: {item.decision.value} · {item.value:.3f} · "
                f"{escape(item.threshold_version)} · spans "
                f"{escape(_trust_spans(item.spans) or '—')}"
                "</li>"
                for item in report.trust.relevance
            )
            prediction = report.trust.prediction_set
            prediction_html = ""
            if prediction is not None:
                bands = escape(", ".join(band.value for band in prediction.bands))
                prediction_html = (
                    f"<li>Prediction set: {bands}; "
                    f"interval [{prediction.low:.3f}, {prediction.high:.3f}], "
                    f"alpha {prediction.alpha:.3f}; calibration "
                    f"{escape(prediction.calibration_id)} ({escape(prediction.checksum)})</li>"
                )
            trust_provenance = "".join(
                f"<li>{escape(key)}: {escape(value)}</li>"
                for key, value in sorted(_safe_report_versions(report.provenance).items())
            )
            trust_html += (
                "<details><summary>Evidence Trust cho giảng viên</summary><ul>"
                f"{language_html}{guard_rows}{prediction_html}{trust_provenance}"
                "</ul></details>"
            )
    return f"""<section aria-labelledby="report-heading">
<h2 id="report-heading">Báo cáo chẩn đoán</h2>
<p>{verification}</p><p>{overall_label}: {escape(overall)}</p>{teacher_result}
<p>Interaction: insufficient_evidence</p><h3>Coverage</h3><ul>{coverage}</ul>
{trust_html}
<h3>Nhận xét có evidence</h3><details><summary>{len(report.comments)} nhận xét</summary>
<ul>{comments}</ul></details><p>Lý do: {reasons}</p>
<h3>Giới hạn kết quả</h3><ul>{limitations}</ul>
<details><summary>Phiên bản và evidence</summary>
<dl>{provenance}</dl><ul>{issues}</ul></details></section>"""


def _student_trust_recovery(reasons: tuple[object, ...]) -> str | None:
    values = {getattr(reason, "value", str(reason)) for reason in reasons}
    if values & {"CALIBRATION_MISSING", "CALIBRATION_INVALID", "CALIBRATION_HASH_MISMATCH"}:
        return "Kết quả đang chờ kiểm tra; hãy xem lại sau hoặc hỏi giảng viên."
    if "LANGUAGE_NOT_ENGLISH" in values:
        return "Hãy ghi lại câu trả lời bằng tiếng Anh."
    if "LANGUAGE_UNCERTAIN" in values:
        return "Hãy ghi lại câu trả lời rõ tiếng Anh hơn."
    if values & {"OFF_TOPIC_SUSPECTED", "PROMPT_READING_SUSPECTED", "SCORE_NEAR_BOUNDARY"}:
        return "Giảng viên cần xem lại kết quả trước khi sử dụng."
    return None


def _safe_report_versions(values: dict[str, str], *, max_value: int = 160) -> dict[str, str]:
    """Keep version labels visible while excluding filesystem paths and huge values."""
    return {
        key: value
        for key, value in values.items()
        if isinstance(key, str)
        and isinstance(value, str)
        and len(key) <= 64
        and len(value) <= max_value
        and "/" not in value
        and "\\" not in value
    }


def _trust_spans(spans: tuple[object, ...]) -> str:
    return ", ".join(f"{span.start_word}:{span.end_word}" for span in spans)


def render_report(report: DiagnosticReport, *, demo: bool = False) -> str:
    from aicefr.portal.templates import nav

    body = nav("student") + _demo_note(demo) + render_report_content(report) + render_logout_form()
    return _document("Báo cáo chẩn đoán", body + '<script src="/report.js" defer></script>')


def _coverage_row(criterion: str, coverage: float | None) -> str:
    value = f"{coverage:.2f}" if coverage is not None else "—"
    return f"<li>{escape(criterion)}: {value}</li>"


def render_review_queue(candidates: tuple[ReviewCandidate, ...], *, demo: bool = False) -> str:
    from aicefr.portal.templates import nav

    rows = "".join(_review_row(candidate) for candidate in candidates)
    if not rows:
        rows = "<li>Không có bài cần duyệt.</li>"
    body = f"{nav('teacher')}{_demo_note(demo)}<ul>{rows}</ul>{render_logout_form()}"
    return _document("Hàng đợi giảng viên", body)


def render_review_detail(
    candidate: ReviewCandidate,
    report: DiagnosticReport | None,
    *,
    demo: bool = False,
    audio_available: bool = True,
) -> str:
    from aicefr.portal.templates import nav

    report_html = (
        render_report_content(report, teacher=True)
        if report is not None
        else "<p>Báo cáo chưa sẵn sàng.</p>"
    )
    action_form = ""
    if candidate.state.value in {"PENDING", "IN_REVIEW"}:
        path_id = quote(candidate.response_id, safe="")
        action_form = f"""<form method="post" action="/teacher/reviews/{path_id}/decision">
<input type="hidden" name="expected_revision" value="{candidate.revision}">
<label for="decision">Quyết định</label><select id="decision" name="action">
<option value="APPROVE">Duyệt</option><option value="OVERRIDE">Sửa band</option>
<option value="REJECT">Từ chối</option></select>
<label for="final-band">Band cuối khi override</label><select id="final-band" name="final_band">
<option value="">Không áp dụng</option><option value="A2">A2</option>
<option value="B1">B1</option><option value="B2">B2</option></select>
<label for="reason">Lý do</label><textarea id="reason" name="reason"></textarea>
<button type="submit">Lưu quyết định</button></form>"""
    else:
        path_id = quote(candidate.response_id, safe="")
        action_form = (
            f'<form method="post" action="/teacher/reviews/{path_id}/reopen">'
            f'<input type="hidden" name="expected_revision" value="{candidate.revision}">'
            '<label>Lý do mở lại<textarea name="reason" required maxlength="1000">'
            "</textarea></label>"
            "<button>Mở lại để hiệu chỉnh</button></form>"
        )
    path_id = quote(candidate.response_id, safe="")
    audio_html = (
        f'<audio controls preload="none" src="/teacher/reviews/{path_id}/audio"></audio>'
        f'<p><a href="/teacher/reviews/{path_id}/audio">Nghe audio</a></p>'
        if audio_available
        else "<p>Audio đã được xóa theo retention.</p>"
    )
    claim = ""
    if candidate.state.value in {"PENDING", "IN_REVIEW"}:
        from datetime import UTC, datetime

        from aicefr.review.service import claim_expired

        action = (
            "claim"
            if candidate.state.value == "PENDING" or claim_expired(candidate, datetime.now(UTC))
            else "release"
        )
        label = "Nhận xử lý" if action == "claim" else "Trả lại hàng đợi"
        claim = (
            f'<form method="post" action="/teacher/reviews/{path_id}/{action}">'
            f'<input type="hidden" name="expected_revision" value="{candidate.revision}">'
            f"<button>{label}</button></form>"
        )
    body = f"""{nav("teacher")}{_demo_note(demo)}<p>Trạng thái: {escape(candidate.state.value)}</p>
<p>Người nhận: {escape(candidate.claimed_by or "Chưa có")}</p>{claim}
<p>Revision: {candidate.revision}</p>{report_html}
{audio_html}{action_form}
<p><a href="/teacher/reviews">Quay lại hàng đợi</a></p>{render_logout_form()}"""
    return _document("Duyệt bài", body + '<script src="/report.js" defer></script>')


def _review_row(candidate: ReviewCandidate) -> str:
    response_id = escape(candidate.response_id)
    path_id = quote(candidate.response_id, safe="")
    revision = str(candidate.revision)
    controls = ""
    if candidate.state.value == "PENDING":
        controls += f"""<form method="post" action="/teacher/reviews/{path_id}/claim">
<input type="hidden" name="expected_revision" value="{revision}">
<button type="submit">Nhận xử lý</button></form>"""
    if candidate.state.value in {"PENDING", "IN_REVIEW"}:
        controls += f"""<form method="post" action="/teacher/reviews/{path_id}/decision">
<input type="hidden" name="expected_revision" value="{revision}">
<label for="decision-{path_id}">Quyết định</label>
<select id="decision-{path_id}" name="action"><option value="APPROVE">Duyệt</option>
<option value="OVERRIDE">Sửa band</option><option value="REJECT">Từ chối</option></select>
<label for="band-{path_id}">Band cuối khi override</label>
<select id="band-{path_id}" name="final_band"><option value="">Không áp dụng</option>
<option value="A2">A2</option><option value="B1">B1</option><option value="B2">B2</option></select>
<label for="reason-{path_id}">Lý do</label>
<textarea id="reason-{path_id}" name="reason"></textarea>
<button type="submit">Lưu quyết định</button></form>"""
    detail = f'<a href="/teacher/reviews/{path_id}">Xem báo cáo và duyệt</a>'
    audio = f'<a href="/teacher/reviews/{path_id}/audio">Nghe audio</a>'
    return f"""<li><p>{response_id} — {escape(candidate.state.value)} (revision {revision})</p>
<p>{detail} · {audio}</p>{controls}</li>"""
