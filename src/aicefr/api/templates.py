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
:root {
  color-scheme: light;
  --surface-bg: #f8fafc;
  --surface-card: #ffffff;
  --surface-subtle: #f1f5f9;
  --surface-overlay: rgba(15, 23, 42, 0.6);
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-muted: #64748b;
  --text-inverse: #ffffff;
  --border-color: #cbd5e1;
  --border-subtle: #e2e8f0;
  --border-strong: #94a3b8;
  --primary: #0369a1;
  --primary-hover: #075985;
  --primary-active: #0c4a6e;
  --primary-subtle: #e0f2fe;
  --focus-ring: #0284c7;
  --focus-offset: 2px;
  --error-text: #991b1b;
  --error-bg: #fef2f2;
  --error-border: #f87171;
  --disabled-bg: #e2e8f0;
  --disabled-text: #94a3b8;
  --disabled-border: #cbd5e1;
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shell-max-width: 54rem;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
}

@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --surface-bg: #0b1120;
    --surface-card: #1e293b;
    --surface-subtle: #334155;
    --surface-overlay: rgba(0, 0, 0, 0.75);
    --text-primary: #f8fafc;
    --text-secondary: #e2e8f0;
    --text-muted: #94a3b8;
    --text-inverse: #0f172a;
    --border-color: #475569;
    --border-subtle: #334155;
    --border-strong: #64748b;
    --primary: #38bdf8;
    --primary-hover: #7dd3fc;
    --primary-active: #bae6fd;
    --primary-subtle: #0c4a6e;
    --focus-ring: #38bdf8;
    --error-text: #fecaca;
    --error-bg: #450a0a;
    --error-border: #ef4444;
    --disabled-bg: #334155;
    --disabled-text: #64748b;
    --disabled-border: #475569;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.4);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
  }
}

* {
  box-sizing: border-box;
}

html, body {
  overflow-x: hidden;
  max-width: 100%;
}

body {
  margin: 0;
  padding: 1rem;
  color: var(--text-primary);
  background: var(--surface-bg);
  min-height: 100vh;
}

.skip-link {
  position: absolute;
  top: -9999px;
  left: -9999px;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  z-index: 1000;
  padding: 0.6rem 1.1rem;
  background: var(--surface-card);
  color: var(--primary);
  border: 2px solid var(--primary);
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-decoration: none;
  box-shadow: var(--shadow-md);
}

.skip-link:focus, .skip-link:focus-visible {
  position: static;
  display: inline-block;
  width: auto;
  height: auto;
  overflow: visible;
  clip: auto;
  white-space: normal;
  margin-bottom: 0.75rem;
  outline: 3px solid var(--focus-ring);
  outline-offset: var(--focus-offset);
}

main {
  width: 100%;
  max-width: var(--shell-max-width);
  margin: 0 auto;
  padding: 1.5rem;
  background: var(--surface-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  overflow-wrap: anywhere;
  word-break: break-word;
}

main:focus, main:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: var(--focus-offset);
}

h1, h2, h3 {
  line-height: 1.25;
  color: var(--text-primary);
  margin-top: 0;
}

h1 {
  font-size: 1.75rem;
  margin-bottom: 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-subtle);
}

h2 {
  font-size: 1.35rem;
  margin-bottom: 1rem;
}

h3 {
  font-size: 1.1rem;
  margin-bottom: 0.75rem;
}

p, dd, li {
  overflow-wrap: anywhere;
  color: var(--text-secondary);
}

label {
  display: block;
  margin: 0.85rem 0 0.3rem;
  font-weight: 600;
  color: var(--text-primary);
}

input:not([type=file]):not([type=checkbox]), select, textarea {
  display: block;
  width: 100%;
  max-width: 32rem;
  min-height: 2.75rem;
  padding: 0.55rem 0.75rem;
  font: inherit;
  color: var(--text-primary);
  background: var(--surface-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  transition: border-color 0.15s ease-in-out;
}

input:not([type=file]):not([type=checkbox]):focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 1px;
  border-color: var(--primary);
}

input[type=file] {
  display: block;
  max-width: 100%;
  min-height: 2.75rem;
  padding: 0.4rem 0;
  color: var(--text-secondary);
}

input[type=checkbox] {
  display: inline-block;
  width: 1.2rem;
  height: 1.2rem;
  min-height: auto;
  vertical-align: middle;
  margin-right: 0.5rem;
  accent-color: var(--primary);
}

textarea {
  min-height: 5.5rem;
  resize: vertical;
}

button, input[type=submit] {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  margin: 0.45rem 0.35rem 0.45rem 0;
  padding: 0.55rem 1.1rem;
  font: inherit;
  font-weight: 600;
  color: var(--text-inverse);
  background: var(--primary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: background-color 0.15s ease-in-out;
}

button:hover:not(:disabled), input[type=submit]:hover:not(:disabled) {
  background: var(--primary-hover);
}

button:active:not(:disabled), input[type=submit]:active:not(:disabled) {
  background: var(--primary-active);
}

button:disabled, input[type=submit]:disabled {
  cursor: not-allowed;
  opacity: 0.65;
  background: var(--disabled-bg);
  color: var(--disabled-text);
  border-color: var(--disabled-border);
  box-shadow: none;
}

a {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

a:hover {
  color: var(--primary-hover);
}

:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: var(--focus-offset);
}

form {
  margin: 1.25rem 0;
}

nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1.25rem;
}

pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: var(--surface-subtle);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  font-size: 0.9em;
}

audio {
  width: 100%;
  max-width: 32rem;
  margin: 0.5rem 0;
  border-radius: var(--radius-sm);
}

section, li {
  margin-bottom: 1rem;
}

[role="alert"] {
  padding: 0.75rem 1rem;
  margin: 0.75rem 0;
  color: var(--error-text);
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.demo-note {
  padding: 0.6rem 0.9rem;
  margin: 0.75rem 0;
  background: var(--surface-subtle);
  border-left: 4px solid var(--primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 0.925rem;
  color: var(--text-secondary);
}

@media (max-width: 480px) {
  body {
    padding: 0.5rem;
  }
  main {
    padding: 1rem;
    border-radius: var(--radius-sm);
    border: none;
  }
  input:not([type=file]):not([type=checkbox]), select, textarea {
    max-width: 100%;
  }
  button, input[type=submit] {
    width: 100%;
    margin-right: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

@media print {
  *, *::before, *::after {
    background: transparent !important;
    color: #000 !important;
    box-shadow: none !important;
    text-shadow: none !important;
  }
  body {
    margin: 0;
    padding: 0;
    background: #fff !important;
    color: #000 !important;
  }
  main {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    box-shadow: none !important;
  }
  .skip-link, nav, form, button, [role="alert"], audio, script,
  input, select, textarea, .demo-note {
    display: none !important;
  }
  a {
    text-decoration: underline;
    color: #000 !important;
  }
  a[href^="http"]::after, a[href^="/"]::after {
    content: " (" attr(href) ")";
    font-size: 0.85em;
  }
}
"""


def _document(title: str, body: str, *, refresh: bool = False) -> str:
    refresh_tag = '<meta http-equiv="refresh" content="5">' if refresh else ""
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{refresh_tag}
<title>{escape(title)}</title><link rel="stylesheet" href="/local.css"></head>
<body><a href="#main" class="skip-link">Chuyển đến nội dung chính</a>
<main id="main" tabindex="-1"><h1>{escape(title)}</h1>{body}</main></body></html>"""


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
