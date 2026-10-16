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
  color-scheme: light dark;
  font-family: "Roboto", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
  --canvas: #f2f6f3;
  --surface: #ffffff;
  --surface-soft: #e8f0ec;
  --ink: #162722;
  --muted: #526760;
  --line: #d3e0da;
  --brand: #12665b;
  --brand-strong: #0c5148;
  --brand-soft: #d8eee7;
  --accent: #c2643e;
  --danger: #a33232;
  --focus: #cf722f;
  --shadow: 0 20px 55px rgba(25, 62, 51, .10);
}
@font-face {
  font-family: "Roboto";
  src: url("/static/fonts/Roboto-Variable.ttf") format("truetype");
  font-style: normal;
  font-weight: 100 900;
  font-display: swap;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; min-height: 100vh; padding: clamp(.75rem, 2vw, 2rem);
  color: var(--ink); background:
    radial-gradient(ellipse at 8% 0%, rgba(198, 224, 207, .45), transparent 36rem),
    var(--canvas);
}
body::before {
  position: fixed; z-index: -1; top: 58vh; right: -8rem; width: 20rem; height: 20rem;
  border: 1px solid rgba(18, 102, 91, .10); border-radius: 50%; content: "";
  box-shadow: 0 0 0 2.5rem rgba(18, 102, 91, .025), 0 0 0 5rem rgba(18, 102, 91, .018);
}
.app-shell { width: min(100%, 76rem); margin: 0 auto; }
.app-shell > h1.page-title { margin: 1.5rem 0; font-size: clamp(1.8rem, 4vw, 3rem); letter-spacing: -.045em; line-height: 1.08; }
h1, h2, h3, h4 { line-height: 1.16; letter-spacing: -.025em; }
h2 { font-size: clamp(1.25rem, 2.4vw, 1.75rem); }
p, dd, li { overflow-wrap: anywhere; }
p { color: var(--muted); }
a { color: var(--brand-strong); text-underline-offset: .18em; }
a:hover { text-decoration-thickness: 2px; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; border-radius: .3rem; }
.skip-link { position: fixed; z-index: 10; top: .5rem; left: .5rem; transform: translateY(-150%); padding: .7rem 1rem; background: var(--surface); border-radius: .6rem; }
.skip-link:focus { transform: translateY(0); }
.site-nav, .public-nav {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  margin: 0 0 1.25rem; padding: .8rem 1rem; border: 1px solid var(--line);
  border-radius: 1.1rem; background: color-mix(in srgb, var(--surface) 92%, transparent);
  box-shadow: 0 8px 28px rgba(25, 62, 51, .06); backdrop-filter: blur(12px);
}
.nav-brand, .brand { display: inline-flex; align-items: center; gap: .65rem; color: var(--ink); font-weight: 800; text-decoration: none; white-space: nowrap; }
.brand-mark { display: inline-grid; width: 2.1rem; height: 2.1rem; place-items: center; border-radius: .72rem; color: white; background: var(--brand); font-size: .85rem; }
.nav-links, .public-links { display: flex; align-items: center; flex-wrap: wrap; justify-content: flex-end; gap: .25rem; }
.nav-links a, .public-links a { padding: .5rem .7rem; border-radius: .7rem; color: var(--muted); font-size: .93rem; font-weight: 650; text-decoration: none; }
.nav-links a:hover, .public-links a:hover { color: var(--brand-strong); background: var(--surface-soft); }
.nav-links a[aria-current="page"] { color: var(--brand-strong); background: var(--brand-soft); }
main { width: 100%; }
main > h1:first-child { max-width: 19ch; }
.card, .panel, .account-card, .report-card, .task-card, .response-card {
  padding: clamp(1rem, 2.4vw, 1.65rem); border: 1px solid var(--line); border-radius: 1.1rem;
  background: var(--surface); box-shadow: 0 12px 34px rgba(25, 62, 51, .055);
}
.card-grid, .feature-grid, .account-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.eyebrow { color: var(--brand); font-size: .76rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.muted, .help, .meta { color: var(--muted); font-size: .93rem; }
.button, button, input[type=submit] {
  display: inline-flex; align-items: center; justify-content: center; gap: .45rem;
  min-height: 2.85rem; margin: .35rem .35rem .35rem 0; padding: .68rem 1rem;
  border: 1px solid var(--brand); border-radius: .75rem; color: #fff; background: var(--brand);
  font: inherit; font-weight: 750; text-decoration: none; cursor: pointer;
  transition: background-color .16s ease, transform .16s ease, box-shadow .16s ease;
}
button:hover, input[type=submit]:hover, .button:hover { background: var(--brand-strong); box-shadow: 0 8px 18px rgba(18, 102, 91, .18); transform: translateY(-1px); }
button:disabled, input[type=submit]:disabled { cursor: not-allowed; opacity: .58; transform: none; box-shadow: none; }
.button-secondary, button.secondary { color: var(--brand-strong); background: var(--surface); }
.button-secondary:hover, button.secondary:hover { color: white; }
.button-quiet { border-color: transparent; color: var(--brand-strong); background: transparent; }
.button-danger, button.danger { border-color: var(--danger); background: var(--danger); }
form { margin: 1rem 0; }
label { display: block; margin: .9rem 0 .35rem; color: var(--ink); font-size: .93rem; font-weight: 700; }
input:not([type=file]), select, textarea {
  display: block; width: 100%; min-height: 2.85rem; padding: .68rem .8rem;
  border: 1px solid var(--line); border-radius: .7rem; color: var(--ink); background: var(--surface); font: inherit;
}
input:not([type=file]):focus, select:focus, textarea:focus { border-color: var(--brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 18%, transparent); outline: none; }
input[type=file] { display: block; max-width: 100%; padding: .6rem 0; color: var(--muted); font: inherit; }
textarea { min-height: 7rem; }
input[type=checkbox], input[type=radio] { width: 1.1rem; height: 1.1rem; accent-color: var(--brand); vertical-align: middle; }
input[type=checkbox] + span { margin-left: .35rem; }
fieldset { min-width: 0; margin: 1rem 0; padding: 1rem; border: 1px solid var(--line); border-radius: .85rem; }
legend { padding: 0 .4rem; font-weight: 750; }
nav { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: 1rem; }
form[role="group"], .inline-form { display: inline-flex; align-items: center; flex-wrap: wrap; gap: .35rem; }
.status-banner, [role="status"], [role="alert"] { padding: .85rem 1rem; border: 1px solid var(--line); border-radius: .8rem; background: var(--surface-soft); }
[role="alert"] { border-color: color-mix(in srgb, var(--danger) 35%, var(--line)); color: var(--danger); background: color-mix(in srgb, var(--danger) 7%, var(--surface)); }
.pill { display: inline-flex; align-items: center; padding: .18rem .58rem; border: 1px solid var(--line); border-radius: 999px; color: var(--brand-strong); background: var(--brand-soft); font-size: .82rem; font-weight: 750; }
.metric-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: .8rem; }
.metric { padding: 1rem; border-radius: .85rem; background: var(--surface-soft); }
.metric strong { display: block; font-size: 1.55rem; letter-spacing: -.04em; }
.hero { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(17rem, .9fr); align-items: center; gap: clamp(2rem, 6vw, 5rem); padding: clamp(1.4rem, 5vw, 4rem) 0 3rem; }
.hero h1 { max-width: 12ch; margin: .6rem 0 1rem; font-size: clamp(2.7rem, 6vw, 5.25rem); letter-spacing: -.065em; line-height: .99; }
.hero-copy { max-width: 38rem; font-size: clamp(1.05rem, 1.7vw, 1.2rem); }
.hero-actions { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: 1.5rem; }
.hero-art { position: relative; min-height: 20rem; display: grid; place-items: center; overflow: hidden; border: 1px solid var(--line); border-radius: 1.5rem; background: linear-gradient(145deg, var(--brand-soft), var(--surface)); }
.hero-art::before, .hero-art::after { position: absolute; width: 12rem; height: 12rem; border: 1px solid color-mix(in srgb, var(--brand) 22%, transparent); border-radius: 50%; content: ""; }
.hero-art::after { width: 17rem; height: 17rem; }
.evidence-stack { position: relative; z-index: 1; width: min(82%, 19rem); padding: 1.25rem; border: 1px solid var(--line); border-radius: 1.1rem; background: var(--surface); box-shadow: var(--shadow); transform: rotate(-3deg); }
.evidence-line { height: .55rem; margin: .65rem 0; border-radius: 99px; background: var(--surface-soft); }
.evidence-line.short { width: 58%; }
.evidence-line.mid { width: 78%; }
.section-space { margin: 2.5rem 0; }
.section-heading { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.band-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .85rem; }
.band-card { padding: 1.1rem; border-top: 3px solid var(--brand); border-radius: .9rem; background: var(--surface); }
.band-card:nth-child(3n + 2) { border-color: var(--accent); }
.band-card:nth-child(3n) { border-color: #718c57; }
.tab-list { display: flex; flex-wrap: wrap; gap: .45rem; margin: 1rem 0 1.5rem; border-bottom: 1px solid var(--line); }
.tab-list a { margin-bottom: -.06rem; padding: .7rem .9rem; border-bottom: 3px solid transparent; color: var(--muted); font-weight: 700; text-decoration: none; }
.tab-list a[aria-current="page"] { border-color: var(--brand); color: var(--brand-strong); }
.account-layout { display: grid; grid-template-columns: minmax(13rem, .32fr) minmax(0, 1fr); gap: 1rem; align-items: start; }
.account-aside { position: sticky; top: 1rem; }
.account-aside a { display: block; padding: .65rem .8rem; border-radius: .65rem; color: var(--muted); font-weight: 700; text-decoration: none; }
.account-aside a[aria-current="page"] { color: var(--brand-strong); background: var(--brand-soft); }
.data-list { display: grid; grid-template-columns: minmax(8rem, .35fr) minmax(0, 1fr); gap: .6rem 1rem; }
.data-list dt { color: var(--muted); }
.data-list dd { margin: 0; font-weight: 650; }
.item-list { display: grid; gap: .8rem; padding: 0; list-style: none; }
.item-list > li { margin: 0; padding: 1rem; border: 1px solid var(--line); border-radius: .85rem; background: var(--surface); }
.report-overall { padding: 1.3rem; border-radius: 1rem; background: var(--brand-soft); }
.report-overall strong { display: block; font-size: clamp(1.7rem, 4vw, 2.5rem); }
progress, meter { width: min(100%, 20rem); height: .85rem; accent-color: var(--brand); }
audio { display: block; width: 100%; margin: .75rem 0; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
section, li { margin-bottom: 1rem; }
.site-footer { margin-top: 3rem; padding: 1rem 0; border-top: 1px solid var(--line); color: var(--muted); font-size: .9rem; }
@media (prefers-color-scheme: dark) {
  :root {
    --canvas: #101917; --surface: #182421; --surface-soft: #22332e; --ink: #edf5f1;
    --muted: #afc2ba; --line: #354b43; --brand: #79c7b8; --brand-strong: #a4e1d4;
    --brand-soft: #243f37; --accent: #f0a27d; --danger: #ff9b91; --focus: #ffc078;
    --shadow: 0 20px 55px rgba(0, 0, 0, .28);
  }
  body { background: radial-gradient(ellipse at 8% 0%, rgba(38, 83, 66, .32), transparent 36rem), var(--canvas); }
  .button, button, input[type=submit] { color: #10231e; }
  .button-secondary, button.secondary { color: var(--brand-strong); }
  .hero-art { background: linear-gradient(145deg, var(--brand-soft), var(--surface)); }
}
@media (max-width: 760px) {
  body { padding: .7rem; }
  .site-nav, .public-nav { align-items: flex-start; flex-direction: column; padding: .75rem; }
  .nav-links, .public-links { justify-content: flex-start; width: 100%; }
  .nav-links a, .public-links a { padding: .45rem .55rem; }
  .hero { grid-template-columns: 1fr; padding-top: 1.5rem; }
  .hero-art { min-height: 15rem; }
  .card-grid, .feature-grid, .account-grid, .band-grid { grid-template-columns: 1fr; }
  .account-layout { grid-template-columns: 1fr; }
  .account-aside { position: static; }
  .account-aside nav { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .section-heading { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
@media print {
  body { padding: 0; color: #111; background: white; }
  .site-nav, .public-nav, .hero-actions, button, input[type=submit], .site-footer, .skip-link { display: none !important; }
  .app-shell { max-width: none; }
  .card, .panel, .account-card, .report-card { box-shadow: none; break-inside: avoid; }
}
"""


def _document(
    title: str, body: str, *, refresh: bool = False, show_heading: bool = True, page_class: str = ""
) -> str:
    refresh_tag = '<meta http-equiv="refresh" content="5">' if refresh else ""
    heading = f'<h1 class="page-title">{escape(title)}</h1>' if show_heading else ""
    class_name = f' class="app-shell {escape(page_class, quote=True)}"'
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark">{refresh_tag}
<title>{escape(title)}</title><link rel="stylesheet" href="/local.css"></head>
<body><a class="skip-link" href="#main-content">Bỏ qua đến nội dung</a>
<main id="main-content"{class_name}>{heading}{body}</main></body></html>"""


def _demo_note(demo: bool) -> str:
    if not demo:
        return ""
    return (
        '<p class="demo-note"><strong>Trình diễn local:</strong> chỉ dùng tài khoản '
        "fixture và dữ liệu kiểm thử do nhóm tạo.</p>"
    )


def _public_nav(active: str = "") -> str:
    links = (("Cách hoạt động", "/#how-it-works"), ("Thang CEFR", "/bands"))
    items = ""
    for label, path in links:
        current = ' aria-current="page"' if active == path else ""
        items += f'<a href="{path}"{current}>{escape(label)}</a>'
    return f'''<header class="public-nav">
<a class="brand" href="/" aria-label="AI Assessor CEFR — trang chủ">
<span class="brand-mark" aria-hidden="true">A</span><span>AI Assessor CEFR</span></a>
<nav class="public-links" aria-label="Điều hướng công khai">{items}
<a class="button" href="/login">Đăng nhập</a></nav></header>'''


def render_public_home() -> str:
    body = f'''{_public_nav()}
<section class="hero" aria-labelledby="hero-title">
  <div>
    <p class="eyebrow">Luyện nói · Có bằng chứng · Rõ giới hạn</p>
    <h1 id="hero-title">Nói tiếng Anh. Hiểu rõ bước tiếp theo.</h1>
    <p class="hero-copy">Bài đánh giá hỗ trợ học tập giúp bạn xem lại phần thể hiện và bằng chứng liên quan. Kết quả là ước lượng; khi dữ liệu chưa đủ, điều đó sẽ được nói rõ.</p>
    <div class="hero-actions"><a class="button" href="/login">Bắt đầu với tài khoản</a>
      <a class="button button-secondary" href="/bands">Tìm hiểu thang CEFR</a></div>
    <p class="help">Không phải chứng chỉ và không dùng để quyết định đậu hay rớt.</p>
  </div>
  <div class="hero-art" aria-hidden="true"><div class="evidence-stack">
    <span class="pill">Bằng chứng của bài nói</span><div class="evidence-line"></div>
    <div class="evidence-line mid"></div><div class="evidence-line short"></div>
    <div class="evidence-line"></div><p class="meta">Nghe lại · xem nhận xét · chọn bước luyện tập</p>
  </div></div>
</section>
<section class="section-space" id="how-it-works" aria-labelledby="how-title">
  <div class="section-heading"><div><p class="eyebrow">Hành trình của bạn</p>
    <h2 id="how-title">Từ một câu trả lời đến một kế hoạch luyện tập</h2></div>
    <p class="help">Bạn kiểm soát bài nộp và có thể xem lại lịch sử của mình.</p></div>
  <div class="feature-grid">
    <article class="card"><span class="pill">01 · Chọn</span><h3>Chọn đề bài</h3>
      <p>Đọc đề, chuẩn bị trong 30 giây hoặc bỏ qua, rồi ghi âm hay chọn tệp được hỗ trợ.</p></article>
    <article class="card"><span class="pill">02 · Gửi</span><h3>Nghe lại trước khi nộp</h3>
      <p>Xem trước bản ghi, ghi lại nếu cần và kiểm tra trạng thái xử lý sau khi gửi.</p></article>
    <article class="card"><span class="pill">03 · Xem</span><h3>Đọc bằng chứng</h3>
      <p>Xem ước lượng tổng thể, phần bằng chứng có sẵn và giới hạn khi dữ liệu chưa đủ.</p></article>
    <article class="card"><span class="pill">04 · Tiếp tục</span><h3>Quay lại tiến độ</h3>
      <p>Lịch sử và thông tin học tập chỉ hiển thị theo quyền của tài khoản bạn.</p></article>
  </div>
</section>
<section class="section-space panel" aria-labelledby="principles-title">
  <p class="eyebrow">Cách đọc kết quả</p><h2 id="principles-title">Điểm số cần đi cùng bằng chứng</h2>
  <div class="card-grid"><p>Khi một tiêu chí chưa có đủ dữ liệu, trang giữ nguyên trạng thái thiếu bằng chứng thay vì thay bằng điểm 0.</p>
  <p>Nhận xét có thể liên kết tới đoạn âm thanh liên quan. Kết quả của giảng viên được tách khỏi ước lượng tự động khi có.</p></div>
  <a href="/bands">Xem giải thích về thang CEFR</a>
</section>
<footer class="site-footer">AI Assessor CEFR · Công cụ hỗ trợ học tập, không cấp chứng chỉ.</footer>'''
    return _document("AI Assessor CEFR — luyện nói có bằng chứng", body, show_heading=False, page_class="marketing-page")


def render_bands_page() -> str:
    levels = (
        ("A1", "Làm quen", "Hiểu và dùng những cách diễn đạt rất cơ bản trong tình huống quen thuộc."),
        ("A2", "Cơ bản", "Trao đổi về nhu cầu gần gũi và chủ đề quen thuộc."),
        ("B1", "Độc lập", "Xử lý các chủ đề quen thuộc và diễn đạt ý chính của trải nghiệm."),
        ("B2", "Độc lập nâng cao", "Tham gia trao đổi đa dạng và trình bày quan điểm có giải thích."),
        ("C1", "Thành thạo", "Diễn đạt linh hoạt, rõ ràng trong nhiều ngữ cảnh."),
        ("C2", "Thành thạo cao", "Hiểu và diễn đạt sắc thái tinh tế trong ngữ cảnh phức tạp."),
    )
    cards = "".join(
        f'<article class="band-card"><span class="pill">{escape(code)}</span>'
        f'<h2>{escape(name)}</h2><p>{escape(description)}</p></article>'
        for code, name, description in levels
    )
    body = f'''{_public_nav("/bands")}
<section class="section-space"><p class="eyebrow">Thang tham chiếu</p>
<h1>CEFR mô tả khả năng sử dụng ngôn ngữ theo từng mức</h1>
<p class="hero-copy">Các mô tả dưới đây giúp bạn định hướng khi đọc kết quả. Chúng không phải ranh giới điểm số của hệ thống; trang chỉ hiển thị band khi báo cáo có dữ liệu tương ứng.</p>
<div class="band-grid">{cards}</div></section>
<section class="section-space card"><h2>Đọc kết quả có ngữ cảnh</h2>
<ul><li>Band được hiển thị cùng một ước lượng tổng thể và bằng chứng có sẵn.</li>
<li>Một bài nói riêng lẻ không đại diện cho toàn bộ năng lực ngôn ngữ.</li>
<li>Thiếu bằng chứng được ghi rõ; không tự chuyển thành điểm 0.</li>
<li>Đây là công cụ hỗ trợ học tập, không cấp chứng chỉ hay quyết định đậu/rớt.</li></ul>
<a class="button" href="/login">Đăng nhập để xem bài của bạn</a></section>
<footer class="site-footer"><a href="/">Trang chủ</a> · AI Assessor CEFR</footer>'''
    return _document("Thang CEFR và cách đọc kết quả", body, show_heading=False, page_class="bands-page")


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
    task_items = tasks or []
    selected_task = next(
        (
            item
            for item in task_items
            if item["task_id"] == selected.get("task_id")
            and item["task_version"] == selected.get("task_version")
        ),
        task_items[0] if task_items else None,
    )
    task_options = "".join(
        f'<option value="{escape(item["task_id"] + "::" + item["task_version"], quote=True)}" '
        f'data-task-id="{escape(item["task_id"], quote=True)}" '
        f'data-task-version="{escape(item["task_version"], quote=True)}" '
        f'data-prompt="{escape(item["prompt_text"], quote=True)}"'
        f'{" selected" if item is selected_task else ""}>'
        f'{escape(item["title"])} · {escape(item["task_id"])} / {escape(item["task_version"])}</option>'
        for item in task_items
    )
    task_prompt = escape(selected_task["prompt_text"]) if selected_task else ""
    task_id = escape(selected_task["task_id"], quote=True) if selected_task else ""
    task_version = escape(selected_task["task_version"], quote=True) if selected_task else ""
    no_tasks = not task_items
    select_disabled = " disabled" if no_tasks else ""
    ready_disabled = " disabled" if no_tasks else ""
    body = f'''{nav("student", "/student/upload")}{_demo_note(demo)}{message}
<section class="card task-card"><p class="eyebrow">Bài đánh giá</p>
<h2>Chọn đề bài</h2><p>Đọc đề và chuẩn bị câu trả lời trước khi ghi âm hoặc chọn tệp.</p>
<label for="task-selector">Đề bài đang mở</label>
<select id="task-selector"{select_disabled} aria-describedby="task-prompt">
{task_options or '<option value="">Hiện chưa có đề bài mở</option>'}</select>
<p id="task-prompt" class="task-prompt">{task_prompt or "Khi có đề bài, nội dung sẽ hiện ở đây."}</p>
<p class="help">Kết quả là ước lượng hỗ trợ học tập. Báo cáo có thể ghi rõ khi chưa đủ bằng chứng.</p>
<p><a href="/student/consent">Xem hoặc thay đổi đồng ý xử lý dữ liệu</a></p></section>
<form method="post" action="/student/responses" enctype="multipart/form-data" data-recorder
data-recording-enabled="{str(recording_enabled).lower()}"
data-max-seconds="{max_seconds}" data-max-bytes="{max_bytes}">
<input type="hidden" id="task-id" name="task_id" value="{task_id}" required>
<input type="hidden" id="task-version" name="task_version" value="{task_version}" required>
<input type="hidden" id="consent-version" name="consent_version" value="{escape(consent_version, quote=True)}" required>
<section class="card preparation" aria-labelledby="preparation-title" data-preparation>
<p class="eyebrow">Chuẩn bị</p><h2 id="preparation-title">Sẵn sàng nói theo cách của bạn</h2>
<p>Thời gian chuẩn bị là 30 giây. Bạn có thể bỏ qua bất cứ lúc nào.</p>
<p id="prep-clock" role="status" aria-live="polite">Chưa bắt đầu · 30 giây</p>
<button type="button" id="prep-begin"{ready_disabled}>Bắt đầu chuẩn bị</button>
<button type="button" id="prep-skip" class="secondary"{ready_disabled}>Bỏ qua chuẩn bị</button></section>
<section class="card" aria-labelledby="audio-title"><p class="eyebrow">Bản ghi của bạn</p>
<h2 id="audio-title">Ghi âm hoặc chọn tệp</h2>
<section id="recording-controls" hidden aria-label="Ghi âm trực tiếp">
<button type="button" id="record-start">Bắt đầu ghi âm</button>
<button type="button" id="record-stop" disabled>Dừng ghi âm</button></section>
<label for="audio">Chọn tệp âm thanh</label>
<input id="audio" name="audio" type="file" accept="audio/*"{ready_disabled}>
<audio id="record-preview" controls hidden aria-label="Nghe bản ghi xem trước"></audio>
<p id="record-notice" role="status" aria-live="polite">Bắt đầu hoặc bỏ qua phần chuẩn bị để tiếp tục.</p>
<div id="retry-confirm" class="status-banner" hidden>
<p>Kết nối bị gián đoạn; chưa xác nhận được server đã nhận bài. Hãy kiểm tra <a href="/student/responses">lịch sử bài nộp</a> trước khi gửi lại.</p>
<label><input id="retry-checked" type="checkbox"><span>Tôi đã kiểm tra lịch sử và xác nhận gửi lại</span></label></div>
<progress id="upload-progress" max="100" value="0" hidden aria-label="Tiến trình gửi tệp"></progress>
<button type="submit"{ready_disabled}>Nộp bài</button></section></form>
{render_logout_form()}<script src="/recorder.js" defer></script>'''
    return _document("Nộp bài nói", body)


def render_login(error: str | None = None, *, demo: bool = False) -> str:
    message = f'<p role="alert">{escape(error)}</p>' if error else ""
    body = f"""{_public_nav("/login")}<section class="account-card auth-card">
<p class="eyebrow">Chào mừng bạn quay lại</p><h2>Đăng nhập vào tài khoản</h2>
{_demo_note(demo)}{message}<form method="post" action="/login">
<label for="actor-id">Tài khoản</label>
<input id="actor-id" name="actor_id" required autocomplete="username">
<label for="password">Mật khẩu</label>
<input id="password" name="password" type="password" required autocomplete="current-password">
<button type="submit">Đăng nhập</button></form>
<p class="help">Phiên đăng nhập được bảo vệ bởi server. Không nhập thông tin đăng nhập trên thiết bị không tin cậy.</p>
<a href="/bands">Tìm hiểu cách đọc band CEFR</a></section>"""
    return _document("Đăng nhập", body, show_heading=False, page_class="login-page")


def render_consent(
    version: str, active: bool, demo: bool, *, research_allowed: bool = False
) -> str:
    from aicefr.portal.templates import nav

    state = "Bạn đã đồng ý phiên bản hiện tại." if active else "Bạn chưa đồng ý phiên bản hiện tại."
    body = f"""{nav("student", "/student/consent")}{_demo_note(demo)}<section class="account-card">
<p class="eyebrow">Quyền dữ liệu</p><h2>{state}</h2>
<p>Phiên bản nội dung: {escape(version)}. Bạn có thể rút lại đồng ý bất cứ lúc nào.</p>
<form method="post" action="/student/consent/accept">
<label><input type="checkbox" name="research_allowed" value="true"
{"checked" if research_allowed else ""}>
Cho phép dùng số liệu tổng hợp đã bỏ ID tài khoản cho nghiên cứu (tùy chọn).</label>
<button type="submit">Đồng ý</button></form>
<form method="post" action="/student/consent/withdraw">
<button type="submit">Rút lại đồng ý</button></form>
<p><a href="/student/upload">Quay lại nộp bài</a> · <a href="/student/account?tab=data">Quản lý tài khoản và dữ liệu</a></p>
</section>{render_logout_form()}"""
    return _document("Đồng ý xử lý dữ liệu", body)


def render_student_status(status: StudentStatus, *, demo: bool = False) -> str:
    from aicefr.portal.templates import nav

    reason_value = getattr(status.reason, "value", status.reason)
    status_labels = {
        "QUEUED": "Đang chờ xử lý",
        "RUNNING": "Đang xử lý",
        "COMPLETED": "Đã xử lý",
        "REVIEW_REQUIRED": "Cần xem xét thêm",
        "REJECTED": "Không thể tiếp nhận",
        "FAILED": "Xử lý thất bại",
    }
    reason = (
        f'<p class="help">Thông tin xử lý: {escape(str(reason_value))}</p>'
        if reason_value
        else ""
    )
    report_link = (
        f'<a href="/student/responses/{escape(status.response_id)}/report">Xem báo cáo</a>'
        if status.report_available
        else '<p role="status">Báo cáo chưa sẵn sàng. Trạng thái sẽ được cập nhật khi xử lý hoàn tất.</p>'
    )
    response_path = quote(status.response_id, safe="")
    body = f'''{nav("student", f"/student/responses/{response_path}")}{_demo_note(demo)}
<section class="account-card"><p class="eyebrow">Bài đã nộp</p><h2>Trạng thái xử lý</h2>
<dl class="data-list"><dt>Mã bài nộp</dt><dd><code>{escape(status.response_id)}</code></dd>
<dt>Trạng thái</dt><dd><span class="pill">{escape(status_labels.get(status.status.value, status.status.value))}</span></dd></dl>
{reason}<div class="hero-actions">{report_link}<a class="button button-secondary" href="/student/responses/{response_path}">Làm mới trạng thái</a>
<a href="/student/responses">Xem lịch sử bài nộp</a></div></section>{render_logout_form()}'''
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
    interaction_value = (
        escape(str(report.interaction.level))
        if report.interaction.level is not None
        else "Chưa đủ bằng chứng"
    )
    interaction_status = escape(report.interaction.score_status)
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
        teacher_result = f'<p class="pill">Kết quả giảng viên: {escape(final_value)}</p>{reason}'
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
    return f"""<section class="report-card" aria-labelledby="report-heading">
<p class="eyebrow">Bài đánh giá</p><h2 id="report-heading">Báo cáo chẩn đoán</h2>
<p role="status">{verification}</p><div class="report-overall"><span>{overall_label}</span>
<strong>{escape(overall)}</strong></div>{teacher_result}
<h3>Độ bao phủ theo tiêu chí</h3>
<p class="help">Bằng chứng và độ bao phủ được trình bày riêng với ước lượng tổng thể.</p>
<ul class="item-list">{coverage or '<li>Chưa có dữ liệu tiêu chí để hiển thị.</li>'}</ul>
<h3>Tương tác</h3><p>{interaction_value} · {interaction_status}</p>{trust_html}
<h3>Nhận xét có bằng chứng</h3><details><summary>{len(report.comments)} nhận xét</summary>
<ul class="item-list">{comments or '<li>Chưa có nhận xét liên kết với bằng chứng.</li>'}</ul></details>
<p><strong>Lý do/trạng thái dữ liệu:</strong> {reasons}</p>
<h3>Giới hạn kết quả</h3>
<ul>{limitations or '<li>Không có giới hạn bổ sung được ghi trong báo cáo.</li>'}</ul>
<details><summary>Phiên bản và bằng chứng</summary><dl>{provenance}</dl>
<ul>{issues or '<li>Không có lỗi bằng chứng được ghi.</li>'}</ul></details></section>"""


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


def render_report(
    report: DiagnosticReport, *, demo: bool = False, response_id: str | None = None
) -> str:
    from aicefr.portal.templates import nav

    response_path = quote(response_id, safe="") if response_id else ""
    audio = (
        f'<section class="card"><h2>Âm thanh bài nộp</h2><audio id="report-audio" controls preload="none" '
        f'src="/student/responses/{response_path}/audio">Trình duyệt không hỗ trợ phát âm thanh.</audio>'
        '<p id="audio-status" class="help" role="status" aria-live="polite">'
        'Nếu âm thanh không phát được, kiểm tra quyền truy cập hoặc thử lại sau.</p></section>'
        if response_path
        else ""
    )
    history = (
        f'<p><a href="/student/responses/{response_path}">Trạng thái bài nộp</a> · '
        '<a href="/student/responses">Lịch sử bài nộp</a></p>'
        if response_path
        else ""
    )
    body = (
        nav("student", f"/student/responses/{response_path}/report" if response_path else "")
        + _demo_note(demo)
        + render_report_content(report)
        + audio
        + history
        + render_logout_form()
    )
    return _document("Báo cáo chẩn đoán", body + '<script src="/report.js" defer></script>')


def _coverage_row(criterion: str, coverage: float | None) -> str:
    value = f"{coverage:.2f}" if coverage is not None else "Chưa đủ bằng chứng"
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
