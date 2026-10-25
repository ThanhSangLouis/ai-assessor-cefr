"""Native, escaped portal pages without a frontend build or external requests."""

# ruff: noqa: E501 -- embedded HTML literals intentionally contain long lines.

from __future__ import annotations

import json
from html import escape
from urllib.parse import quote, urlencode

from aicefr.api.templates import _document, render_logout_form, render_report_content
from aicefr.auth.contracts import PROFILE_COLORS, PROFILE_ICONS


def e(value) -> str:
    return escape(str(value if value is not None else "—"), quote=True)


def _selected(value, expected) -> str:
    return " selected" if value == expected else ""


RESPONSE_STATUS_LABELS = {
    "QUEUED": "Đang chờ xử lý",
    "RUNNING": "Đang xử lý",
    "COMPLETED": "Đã xử lý",
    "REVIEW_REQUIRED": "Cần xem xét thêm",
    "REJECTED": "Không thể tiếp nhận",
    "FAILED": "Xử lý thất bại",
}


def nav(role: str, current: str = "") -> str:
    links = [
        ("Nộp bài", "/student/upload"),
        ("Đề bài", "/student/tasks"),
        ("Bài đã nộp", "/student/responses"),
        ("Tiến độ", "/student/progress"),
        ("Đồng ý dữ liệu", "/student/consent"),
        ("Tài khoản", "/student/account"),
    ]
    if role != "student":
        links = [
            ("Hàng đợi", "/teacher/reviews"),
            ("Tất cả bài nộp", "/teacher/responses"),
            ("Thống kê", "/teacher/stats"),
        ]
    if role == "admin":
        links += [
            ("Quản trị", "/admin"),
            ("Tài khoản", "/admin/accounts"),
            ("Đề bài", "/admin/tasks"),
            ("Model", "/admin/models"),
            ("Cấu hình QC", "/admin/config"),
            ("Audit", "/admin/audit"),
            ("Dữ liệu", "/admin/erase"),
            ("Bảo trì", "/admin/maintenance"),
            ("Vận hành", "/admin/health"),
        ]
    items = ""
    for label, path in links:
        is_active = current == path or (
            path != "/" and current.startswith(path + "/")
        )
        active = ' aria-current="page"' if is_active else ""
        items += f'<a href="{path}"{active}>{e(label)}</a>'
    return (
        '<header class="site-nav"><a class="nav-brand" href="/">'
        '<span class="brand-mark" aria-hidden="true">A</span>AI Assessor CEFR</a>'
        f'<nav class="nav-links" aria-label="Điều hướng">{items}</nav></header>'
    )


def page(title: str, body: str, role: str, current: str = "") -> str:
    return _document(title, nav(role, current) + body + render_logout_form())


def account_page(
    profile,
    tab: str,
    *,
    sessions=(),
    activity=(),
    consent=None,
    google: dict | None = None,
    notice: str = "",
) -> str:
    tabs = (("profile", "Hồ sơ"), ("security", "Bảo mật"), ("activity", "Hoạt động"), ("data", "Dữ liệu"))
    tab_links = ""
    for key, label in tabs:
        active = ' aria-current="page"' if key == tab else ""
        tab_links += f'<a href="/student/account?tab={key}"{active}>{e(label)}</a>'
    alert = f'<p role="status">{e(notice)}</p>' if notice else ""
    goals = "".join(
        f'<option value="{goal}"{_selected(profile.goal, goal)}>{goal} buổi</option>'
        for goal in (1, 2, 3, 5, 10)
    )
    icons = "".join(
        f'<option value="{e(icon)}"{_selected(profile.icon, icon)}>{e(icon.title())}</option>'
        for icon in sorted(PROFILE_ICONS)
    )
    colors = "".join(
        f'<option value="{e(color)}"{_selected(profile.color, color)}>{e(color.title())}</option>'
        for color in sorted(PROFILE_COLORS)
    )
    profile_panel = f'''<section class="account-card" aria-labelledby="profile-title">
<p class="eyebrow">Hồ sơ học tập</p><h2 id="profile-title">Thông tin của bạn</h2>
<dl class="data-list"><dt>Mã tài khoản</dt><dd><code>{e(profile.actor_id)}</code></dd>
<dt>Vai trò</dt><dd>{e(profile.role.value)}</dd></dl>
<form method="post" action="/student/account/profile">
<label for="goal">Mục tiêu luyện tập mỗi tuần</label><select id="goal" name="goal">
<option value="">Chưa đặt</option>{goals}</select>
<label for="icon">Biểu tượng</label><select id="icon" name="icon"><option value="">Mặc định</option>
{icons}</select>
<label for="color">Màu hồ sơ</label><select id="color" name="color"><option value="">Mặc định</option>
{colors}</select>
<button type="submit">Lưu hồ sơ</button></form></section>'''

    security_panel = ""
    if tab == "security":
        session_rows = "".join(
            f'''<li><p><strong>{e(session.device or "Thiết bị")}</strong>
<span class="pill">{e(session.method)}</span>{" · Phiên hiện tại" if session.current else ""}</p>
<p class="meta">Đăng nhập: {e(session.created_at)} · Hoạt động gần nhất: {e(session.last_seen_at)}</p>
<form class="inline-form" method="post" action="/student/account/sessions/{quote(session.session_id, safe="")}/revoke">
<button class="secondary" type="submit">Thu hồi phiên</button></form></li>'''
            for session in sessions
        )
        google = google or {"enabled": False, "linked": False}
        if google.get("enabled"):
            google_panel = (
                '<p>Google đang được cấu hình. Tài khoản được liên kết: '
                + ("Có." if google.get("linked") else "Chưa.")
                + "</p>"
                + (
                    '<form method="post" action="/student/account/google/unlink">'
                    '<button class="secondary" type="submit">Ngắt liên kết Google</button></form>'
                    if google.get("linked")
                    else '<form method="post" action="/auth/google/start?intent=link">'
                    '<button type="submit">Liên kết Google</button></form>'
                )
            )
        else:
            google_panel = '<p role="status">Google hiện chưa được cấu hình. Bạn vẫn có thể dùng tài khoản và mật khẩu.</p>'
        security_panel = f'''<section class="account-card"><p class="eyebrow">Bảo mật</p>
<h2>Đổi mật khẩu</h2><p class="help">Mật khẩu được gửi trực tiếp tới server; không lưu trong trình duyệt.</p>
<form method="post" action="/student/account/password">
<label for="current-password">Mật khẩu hiện tại</label><input id="current-password" name="current_password" type="password" autocomplete="current-password" required>
<label for="new-password">Mật khẩu mới</label><input id="new-password" name="new_password" type="password" autocomplete="new-password" minlength="8" required>
<label for="confirm-password">Nhập lại mật khẩu mới</label><input id="confirm-password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" required>
<button type="submit">Đổi mật khẩu</button></form>
<div class="section-space"><h2>Phiên đăng nhập</h2>
<form method="post" action="/student/account/sessions/revoke-others"><button class="secondary" type="submit">Đăng xuất khỏi thiết bị khác</button></form>
<ul class="item-list">{session_rows or '<li>Không có phiên nào khác để hiển thị.</li>'}</ul></div>
<div class="section-space"><h2>Kết nối Google</h2>{google_panel}</div></section>'''

    activity_panel = ""
    if tab == "activity":
        rows = "".join(
            f'<li><strong>{e(item.kind)}</strong><p class="meta">{e(item.recorded_at)}'
            f'{" · " + e(item.detail_code) if item.detail_code else ""}</p></li>'
            for item in activity
        )
        activity_panel = f'''<section class="account-card"><p class="eyebrow">Lịch sử tài khoản</p>
<h2>Hoạt động gần đây</h2><p class="help">Chỉ hoạt động của tài khoản này được hiển thị.</p>
<ul class="item-list">{rows or '<li>Chưa có hoạt động để hiển thị.</li>'}</ul></section>'''

    data_panel = ""
    if tab == "data":
        state = getattr(getattr(consent, "state", None), "value", "Chưa có bản ghi đồng ý")
        version = getattr(consent, "consent_version", "—") if consent else "—"
        research = bool(consent and getattr(consent, "research_allowed", False))
        research_state = "Đang cho phép" if research else "Không cho phép"
        audio_storage = bool(consent and getattr(consent, "audio_storage_allowed", False))
        audio_state = "Đang cho phép" if audio_storage else "Không cho phép"
        data_panel = f'''<section class="account-card"><p class="eyebrow">Quyền dữ liệu</p>
<h2>Đồng ý xử lý dữ liệu</h2><dl class="data-list"><dt>Trạng thái</dt><dd>{e(state)}</dd>
<dt>Phiên bản</dt><dd>{e(version)}</dd><dt>Lưu audio</dt><dd>{audio_state}</dd>
<dt>Dùng cho nghiên cứu</dt><dd>{research_state}</dd></dl>
<p>Đọc lại nội dung đồng ý trước khi thay đổi lựa chọn. Việc rút đồng ý được ghi nhận bởi server.</p>
<a class="button button-secondary" href="/student/consent">Xem hoặc thay đổi đồng ý</a>
<h2>Bản sao dữ liệu của bạn</h2><p>Tải xuống bản xuất hoặc xem danh sách bài nộp của tài khoản này.</p>
<a class="button button-secondary" href="/student/export.json">Tải dữ liệu JSON</a>
<a class="button button-secondary" href="/student/responses">Xem bài đã nộp</a></section>'''

    content = {
        "profile": profile_panel,
        "security": security_panel,
        "activity": activity_panel,
        "data": data_panel,
    }[tab]
    body = f'''<p class="eyebrow">Tài khoản sinh viên</p>
<div class="account-layout"><aside class="account-aside"><nav class="tab-list" aria-label="Các phần tài khoản">{tab_links}</nav>
<p class="help">Mọi thay đổi được xử lý bởi server.</p></aside>
<div>{alert}{content}</div></div>'''
    return _document(
        "Tài khoản", nav("student", "/student/account") + body + render_logout_form()
    )


def hidden(name: str, value) -> str:
    return f'<input type="hidden" name="{name}" value="{e(value)}">'


def field(name: str, label: str, value="", kind="text", required=True) -> str:
    return (
        f'<label>{e(label)}<input name="{name}" type="{kind}" value="{e(value)}" '
        + ("required" if required else "")
        + "></label>"
    )


def filters(query) -> str:
    return (
        '<form method="get">'
        + field("task_id", "Lọc theo mã bài", query.task_id or "", required=False)
        + field("status", "Trạng thái", query.status or "", required=False)
        + field(
            "since",
            "Từ ngày (ISO, có múi giờ)",
            query.since.isoformat() if query.since else "",
            required=False,
        )
        + field(
            "until",
            "Đến ngày (ISO, có múi giờ)",
            query.until.isoformat() if query.until else "",
            required=False,
        )
        + "<button>Lọc</button></form>"
    )


def responses(data: dict, role: str, query) -> str:
    prefix = "student" if role == "student" else "teacher"
    items = []
    for row in data["items"]:
        rid = quote(row["response_id"], safe="")
        report = (
            f'<a href="/{prefix}/responses/{rid}/report">Báo cáo</a>'
            if row["report_available"]
            else f'<a href="/{prefix}/responses/{rid}">Trạng thái</a>'
        )
        audio = (
            f'<a href="/{prefix}/responses/{rid}/audio" aria-label="Nghe bài {e(row["task_id"])}">Nghe bài nói</a>'
            if row["audio_available"]
            else "Âm thanh không còn khả dụng"
        )
        owner = "" if prefix == "student" else f"<p>Tài khoản: {e(row['owner_id'])}</p>"
        controls = (
            f'<a href="/student/responses/{rid}/delete">Quản lý/xóa bài</a>'
            if prefix == "student"
            else f'<a href="/teacher/responses/{rid}/history">Lịch sử xử lý</a>'
        )
        estimate = (
            f'{e(row["overall_score"])} · {e(row["overall_band"])}'
            if row["overall_score"] is not None and row["overall_band"] is not None
            else "Chưa có ước lượng tổng thể"
        )
        if row["teacher_verified"]:
            teacher_result = (
                f"Giảng viên xác nhận · band cuối: {e(row['teacher_final_band'])}"
                if row["teacher_final_band"] is not None
                else "Giảng viên đã xác nhận"
            )
        else:
            teacher_result = "Chưa được giảng viên xác nhận"
        status = RESPONSE_STATUS_LABELS.get(row["status"], row["status"])
        items.append(
            f'<li class="response-card"><h2>{e(row["task_id"])} / {e(row["task_version"])}</h2>{owner}'
            f'<p class="meta">{e(row["created_at"])} · <span class="pill">{e(status)}</span></p>'
            f'<p>Mã bài nộp: <code>{e(row["response_id"])}</code></p>'
            f'<p>Ước lượng AI: {estimate}</p><p>{teacher_result}</p>'
            f'<p class="hero-actions">{report} · {audio} · {controls}</p></li>'
        )
    empty = (
        '<li class="empty-state"><h2>Chưa có bài nộp</h2>'
        '<p>Khi sẵn sàng, chọn một đề bài để bắt đầu.</p>'
        '<a class="button" href="/student/tasks">Xem đề bài</a></li>'
        if prefix == "student"
        else "<li>Chưa có bài.</li>"
    )
    body = (
        filters(query)
        + f'<p role="status">Tổng: {data["total"]} bài</p><ul class="item-list">'
        + ("".join(items) or empty)
        + "</ul>"
    )
    params = query.model_dump(mode="json", exclude_none=True)
    if query.offset > 0:
        params["offset"] = max(0, query.offset - query.limit)
        body += f'<a href="?{e(urlencode(params))}">Trang trước</a> '
    if query.offset + query.limit < data["total"]:
        params["offset"] = query.offset + query.limit
        body += f'<a href="?{e(urlencode(params))}">Trang tiếp</a>'
    if prefix == "student":
        body += (
            '<p><a href="/student/export.json">Tải dữ liệu của tôi (JSON)</a> · '
            '<a href="/student/profile.json">Hồ sơ học tập (JSON)</a></p>'
        )
    return page(
        "Bài đã nộp" if prefix == "student" else "Tất cả bài nộp",
        body,
        role,
        "/student/responses" if prefix == "student" else "/teacher/responses",
    )


def statistics(data: dict, role: str, query) -> str:
    if role == "student":
        body = (
            '<section class="metric-row" aria-label="Tóm tắt tiến độ">'
            f'<article class="metric"><span>Tổng bài nộp</span><strong>{data["total"]}</strong></article>'
            f'<article class="metric"><span>Có band AI</span><strong>{data["estimated_count"]}</strong></article>'
            f'<article class="metric"><span>Chưa có ước lượng</span><strong>{data["not_evaluated_count"]}</strong></article>'
            f'<article class="metric"><span>Được giảng viên xác nhận</span><strong>{data["teacher_verified_count"]}</strong></article>'
            '</section>'
        )
    else:
        body = (
            filters(query)
            + f"<p>Tổng bài: {data['total']} · Có ước lượng: {data['estimated_count']} · "
            f"Đã duyệt: {data['teacher_verified_count']}</p>"
        )
    for label, key in [
        ("Trạng thái", "statuses"),
        ("Band AI tạm thời", "ai_bands"),
        ("Band giảng viên", "teacher_final_bands"),
    ]:
        if role == "student" and key == "statuses":
            status_labels = {
                "QUEUED": "Đang chờ xử lý",
                "RUNNING": "Đang xử lý",
                "COMPLETED": "Đã xử lý",
                "REVIEW_REQUIRED": "Cần xem xét thêm",
                "REJECTED": "Không thể tiếp nhận",
                "FAILED": "Xử lý thất bại",
            }
            values = data[key]
        else:
            status_labels = {}
            values = data[key]
        body += (
            f"<h2>{label}</h2><ul class=\"item-list\">"
            + "".join(
                f'<li>{e(status_labels.get(name, name))}: {count} '
                f'<meter min="0" max="{max(1, data["total"])}" value="{count}">{count}</meter></li>'
                for name, count in values.items()
            )
            + ('<li>Chưa có dữ liệu.</li>' if not values else '')
            + "</ul>"
        )
    if role == "student":
        body += (
            '<section class="section-space" aria-labelledby="submission-history-title">'
            '<div class="section-heading"><div><p class="eyebrow">Lịch sử học tập</p>'
            '<h2 id="submission-history-title">Tiến độ theo lần nộp</h2></div>'
            '<a href="/student/responses">Xem toàn bộ lịch sử</a></div><ol class="item-list">'
            + _student_progress_rows(data["items"])
            + ('<li>Chưa có bài nộp. <a href="/student/tasks">Chọn đề bài để bắt đầu.</a></li>' if not data["items"] else '')
            + "</ol></section>"
            + '<section class="card evidence-empty" aria-labelledby="learning-evidence-title">'
            + '<p class="eyebrow">Bằng chứng học tập</p><h2 id="learning-evidence-title">Phát âm, thay đổi theo thời gian và nghiên cứu</h2>'
            + '<p>Dịch vụ hiện chưa trả dữ liệu M13 đủ điều kiện để hiển thị. Trang không suy diễn thành điểm 0, '
            + 'số mẫu, nguồn đánh giá hay kết luận về tiến bộ.</p>'
            + '<p class="help">Khi dịch vụ cung cấp dữ liệu, trang sẽ kèm nguồn, số mẫu và điều kiện đủ theo contract M13.</p>'
            + "</section>"
        )
    if role != "student":
        body += (
            "<h2>Overall trung bình theo model</h2><ul>"
            + "".join(
                f"<li>{e(name)}: {value:.2f}</li>"
                for name, value in data["mean_overall_by_model"].items()
            )
            + "</ul>"
        )
    return page(
        "Tiến độ học tập" if role == "student" else "Thống kê bài nói",
        body + f"<p>{e(data['note'])}</p>",
        role,
        "/student/progress" if role == "student" else "/teacher/stats",
    )


def _student_progress_rows(rows: list[dict]) -> str:
    rendered = []
    for row in rows:
        score = row["overall_score"]
        band = row["overall_band"]
        estimate = f"{score:.2f}" if score is not None else "Chưa có ước lượng"
        if band is not None:
            estimate += f" · {e(band)}"
        teacher_state = "Chưa được giảng viên xác nhận"
        if row["teacher_verified"]:
            teacher_state = "Đã được giảng viên xác nhận"
            if row["teacher_final_band"] is not None:
                teacher_state += f" · band {e(row['teacher_final_band'])}"
        response_id = quote(row["response_id"], safe="")
        rendered.append(
            f'<li><p class="meta">{e(row["created_at"])}</p>'
            f'<h3>{e(row["task_id"])} · {e(row["task_version"])}</h3>'
            f'<p><span class="pill">{e(RESPONSE_STATUS_LABELS.get(row["status"], row["status"]))}</span></p>'
            f'<p>Ước lượng AI: {estimate} · {teacher_state}</p>'
            f'<a href="/student/responses/{response_id}">Mở trạng thái và báo cáo</a></li>'
        )
    return "".join(rendered)


def tasks(items: list[dict], role: str) -> str:
    body = ""
    if role != "admin":
        for item in items:
            params = urlencode({"task_id": item["task_id"], "task_version": item["task_version"]})
            body += f"""<section>
<h2>{e(item["title"])}</h2>
<p>{e(item["prompt_text"])}</p>
<p>{e(item["task_id"])} / {e(item["task_version"])} ·
{item["min_seconds"]}–{item["max_seconds"]} giây</p>
<a href="/student/upload?{e(params)}">Làm bài</a>
</section>"""
    else:
        body += (
            "<p>Tạo phiên bản mới khi đổi nội dung đề đã có bài nộp. Đóng đề bằng active=false.</p>"
        )
        for item in [
            *items,
            {
                "task_id": "",
                "task_version": "1",
                "title": "",
                "prompt_text": "",
                "topic_keywords": (),
                "min_seconds": 40,
                "max_seconds": 60,
                "active": True,
                "revision": 0,
            },
        ]:
            body += '<form method="post" action="/admin/tasks">' + hidden(
                "expected_revision", item["revision"]
            )
            for name, label in [
                ("task_id", "Mã đề"),
                ("task_version", "Phiên bản"),
                ("title", "Tên đề"),
                ("min_seconds", "Thời lượng tối thiểu"),
                ("max_seconds", "Thời lượng tối đa"),
            ]:
                body += field(name, label, item[name])
            body += f"""<label>Nội dung đề
<textarea name="prompt_text">{e(item["prompt_text"])}</textarea>
</label>
<label>Từ khóa chủ đề, phân cách bằng dấu phẩy
<input name="topic_keywords" value="{e(", ".join(item.get("topic_keywords", ())))}">
</label>
<label>Mở đề<select name="active">
<option value="true" {"selected" if item["active"] else ""}>Có</option>
<option value="false" {"selected" if not item["active"] else ""}>Không</option>
</select>
</label>
<button>Lưu đề</button>
</form>"""
    return page(
        "Đề bài nói",
        body or '<p>Hiện chưa có đề bài mở.</p>',
        role,
        "/student/tasks" if role == "student" else "/admin/tasks",
    )


def accounts(items: list[dict]) -> str:
    body = "<p>Chỉ tạo tài khoản fixture cho phiên local hiện tại.</p><ul>"
    for item in items:
        path_id = quote(item["actor_id"], safe="")
        body += (
            f"<li><p>{e(item['actor_id'])} · {e(item['role'])} "
            f"· {'Đã vô hiệu' if item['disabled'] else 'Đang bật'} "
            f"· sai {item['failed_attempts']} lần · khóa "
            f"đến {e(item['locked_until'])}</p>"
            f'<form method="post" action="/admin/accounts/{path_id}">'
            + hidden("disabled", not item["disabled"])
            + "<button>Đổi trạng thái tài khoản</button></form>"
        )
        body += (
            f'<form method="post" action="/admin/accounts/{path_id}">'
            + hidden("unlock", "true")
            + "<button>Mở khóa đăng nhập</button></form></li>"
        )
    body += (
        '</ul><h2>Tạo tài khoản</h2><form method="post" action="/admin/accounts">'
        + field("actor_id", "ID fixture-...")
        + field("password", "Mật khẩu (tối thiểu 8 ký tự)", kind="password")
        + '<label>Vai trò<select name="role"><option value="student">Sinh viên</option>'
        '<option value="teacher">Giảng viên</option><option value="admin">Quản trị</option>'
        "</select></label><button>Tạo tài khoản</button></form>"
    )
    return page("Quản lý tài khoản", body, "admin")


def model_page(data: dict) -> str:
    body = f"<p>{e(data.get('note', ''))}</p><ul>"
    for item in data["items"]:
        state = "Đang dùng" if item["active"] else ""
        detail = item.get("reason", item.get("model_version"))
        body += f"<li><p>{e(item['name'])} · {state} · {e(detail)}</p>"
        if item["compatible"] and not item["active"]:
            body += (
                '<form method="post" action="/admin/models/activate">'
                + hidden("name", item["name"])
                + hidden("expected_revision", data["revision"])
                + "<button>Kích hoạt</button></form>"
            )
        body += "</li>"
    return page("Model chấm điểm", body + "</ul>", "admin")


def json_page(title: str, data, role: str) -> str:
    return page(
        title,
        '<pre class="json-view">' + e(json.dumps(data, indent=2, ensure_ascii=False)) + "</pre>",
        role,
    )


def report_page(report, response, role: str, *, candidate=None) -> str:
    prefix = "student" if role == "student" else "teacher"
    rid = quote(response.response_id, safe="")
    audio = (
        f'<audio controls preload="none" src="/{prefix}/responses/{rid}/audio"></audio>'
        if response.audio_available
        else "<p>Audio đã được xóa theo retention.</p>"
    )
    review = ""
    if role != "student":
        if candidate:
            review = f'<a href="/teacher/reviews/{rid}">Mở bài duyệt</a>'
        elif not report.teacher_verified:
            review = (
                f'<form method="post" action="/teacher/responses/{rid}/review">'
                + hidden("expected_revision", response.revision)
                + "<button>Đưa vào hàng đợi duyệt</button></form>"
            )
    return page(
        "Báo cáo chẩn đoán",
        render_report_content(report) + audio + review + '<script src="/report.js" defer></script>',
        role,
    )


def score_only_report_page(report, role: str) -> str:
    """Render only the model estimate for a score-only study participant."""
    body = (
        '<section aria-label="Kết quả đánh giá">'
        "<p>Trong nghiên cứu này, phản hồi chi tiết đang được ẩn theo nhóm tham gia.</p>"
        f"<p>Điểm ước lượng: <strong>{e(report.overall_score)}</strong></p>"
        f"<p>Band CEFR ước lượng: <strong>{e(report.overall_band)}</strong></p>"
        "</section>"
    )
    return page("Kết quả đánh giá", body, role)


def delete_page(response) -> str:
    body = (
        f"<p>Xóa audio và toàn bộ báo cáo của bài {e(response.response_id)}. "
        f"Audit giả danh được giữ.</p>"
        f'<form method="post">'
        + hidden("expected_revision", response.revision)
        + field("confirm_id", "Nhập mã bài để xác nhận")
        + "<button>Xóa bài nộp</button></form>"
    )
    return page("Xác nhận xóa bài", body, "student")


def erasure(preview=None) -> str:
    body = (
        '<form method="post" action="/admin/erase/preview">'
        + field("actor_id", "ID tài khoản sinh viên cần xóa")
        + "<button>Xem trước</button></form>"
    )
    if preview:
        body += (
            f"<p>{e(preview['note'])}</p><p>Số bài: {preview['row_count']}; "
            f"audio: {preview['audio_bytes']} bytes.</p>"
            f'<form method="post" action="/admin/erase">'
            + hidden("actor_id", preview["actor_id"])
            + hidden("fingerprint", preview["fingerprint"])
            + field("confirm_id", f"Nhập lại {preview['actor_id']} để xác nhận")
            + "<button>Xóa dữ liệu tài khoản</button></form>"
        )
    return page(
        "Quản trị dữ liệu fixture",
        body + '<p><a href="/admin/research.json">Export nghiên cứu chỉ các tài khoản '
        "opt-in (JSON)</a></p>",
        "admin",
    )


def config_page(data: dict) -> str:
    body = (
        "<p>Thay đổi tạo version QC mới cho bài nộp tiếp theo; kết quả cũ giữ version cũ.</p>"
        '<form method="post">' + hidden("expected_revision", data["revision"])
    )
    for name in data["editable_fields"]:
        body += field(name, name, data["qc"][name])
    return page("Cấu hình QC", body + "<button>Lưu cấu hình</button></form>", "admin")


def maintenance(retention: dict, orphans: dict) -> str:
    body = (
        f"<p>Xem trước retention 180 ngày: {retention['row_count']} bài; "
        f"orphan: {orphans['row_count']} blob.</p>"
    )
    for action, label in [("retention", "Áp dụng retention 180 ngày"), ("orphans", "Dọn orphan")]:
        body += (
            f'<form method="post" action="/admin/maintenance/{action}">'
            + field("confirm_action", f"Nhập {action} để xác nhận")
            + f"<button>{label}</button></form>"
        )
    body += "<p>Sao lưu nhất quán SQLite và blob qua CLI maintenance backup.</p>"
    return page("Bảo trì dữ liệu local", body, "admin")
