"""Native, escaped portal pages without a frontend build or external requests."""

from __future__ import annotations

import json
from html import escape
from urllib.parse import quote, urlencode

from aicefr.api.templates import _document, render_logout_form, render_report_content


def e(value) -> str:
    return escape(str(value if value is not None else "—"), quote=True)


def nav(role: str) -> str:
    links = [
        ("Nộp bài", "/student/upload"),
        ("Đề bài", "/student/tasks"),
        ("Bài đã nộp", "/student/responses"),
        ("Tiến độ", "/student/progress"),
        ("Đồng ý dữ liệu", "/student/consent"),
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
    return (
        '<nav aria-label="Điều hướng">'
        + " · ".join(f'<a href="{path}">{e(label)}</a>' for label, path in links)
        + "</nav>"
    )


def page(title: str, body: str, role: str) -> str:
    return _document(title, nav(role) + body + render_logout_form())


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
            else ""
        )
        audio = (
            f'<a href="/{prefix}/responses/{rid}/audio">Audio</a>'
            if row["audio_available"]
            else "Audio đã xóa"
        )
        owner = "" if prefix == "student" else f"<p>Tài khoản: {e(row['owner_id'])}</p>"
        controls = (
            f'<a href="/student/responses/{rid}/delete">Xóa bài</a>'
            if prefix == "student"
            else f'<a href="/teacher/responses/{rid}/history">Lịch sử xử lý</a>'
        )
        items.append(
            f"<li><h2>{e(row['task_id'])} / {e(row['task_version'])}</h2>{owner}"
            f"<p>{e(row['response_id'])} · {e(row['created_at'])}</p><p>{e(row['status'])}</p>"
            f"<p>Overall AI: {e(row['overall_score'])} / {e(row['overall_band'])}; "
            f"Band giảng viên: {e(row['teacher_final_band'])}</p>"
            f"<p>{report} · {audio} · {controls}</p>"
            f"</li>"
        )
    body = (
        filters(query)
        + f"<p>Tổng: {data['total']} bài</p><ul>"
        + ("".join(items) or "<li>Chưa có bài.</li>")
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
    return page("Bài đã nộp" if prefix == "student" else "Tất cả bài nộp", body, role)


def statistics(data: dict, role: str, query) -> str:
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
        body += (
            f"<h2>{label}</h2><ul>"
            + "".join(
                f'<li>{e(name)}: {count} <meter min="0" max="{max(1, data["total"])}" '
                f'value="{count}">'
                f"{count}</meter></li>"
                for name, count in data[key].items()
            )
            + "</ul>"
        )
    body += (
        "<h2>Overall trung bình theo model</h2><ul>"
        + "".join(
            f"<li>{e(name)}: {value:.2f}</li>"
            for name, value in data["mean_overall_by_model"].items()
        )
        + "</ul>"
    )
    if role == "student":
        body += (
            "<h2>Tiến độ theo lần nộp</h2><ol>"
            + "".join(
                f"<li>{e(row['created_at'])} · {e(row['task_id'])} "
                f"· {e(row['status'])} · AI {e(row['overall_band'])} "
                f"· giảng viên {e(row['teacher_final_band'])} "
                f'<a href="/student/responses/{quote(row["response_id"], safe="")}/report">'
                f"Xem bài</a></li>"
                for row in data["items"]
            )
            + "</ol>"
        )
    return page(
        "Tiến độ học tập" if role == "student" else "Thống kê bài nói",
        body + f"<p>{e(data['note'])}</p>",
        role,
    )


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
    return page("Đề bài nói", body or "<p>Chưa có đề mở.</p>", role)


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
