"""Layer 3 -- E2E for the interface redesign (D024).

Each test walks one of the paths the redesign changed, as a user would: log in
through the form, click, record with the fake microphone or pick a file, and
read what is on screen. Test case ids (TC-UI-Exx) are listed in
`docs/test/TEST_PLAN_UI.md`.

The server, browser and login helpers come from `test_practice_e2e.py` rather
than from a `conftest.py` (that module's docstring says why). Importing them
gives this module its own session server, so state changed here -- a QC
threshold, the queue -- never leaks into the practice tests.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    browser,
    context,
    live_server,
    login,
    wait_until,
)

pytestmark = pytest.mark.e2e


def login_home(page, server, pseudonym: str, home: str) -> None:
    """Log in WITHOUT `?next=`, and wait for the role's own start page."""
    page.goto("/login")
    page.get_by_label("Email", exact=True).fill(pseudonym)
    page.get_by_label("Mật khẩu", exact=True).fill(server.password)
    page.get_by_role("button", name="Đăng nhập", exact=True).click()
    page.wait_for_url(lambda url: urlparse(url).path == home)


def student_page(context, live_server, path: str = "/"):
    page = context.new_page()
    login(page, live_server, live_server.account(), path)
    page.goto(path)
    return page


def nav_texts(page) -> list[str]:
    return [t.strip() for t in page.locator(".site-nav a").all_inner_texts()]


def recorder_ready(page) -> bool:
    """Wait for /api/v1/health to switch the recorder on or off; True if on."""
    wait_until(
        page,
        "!document.getElementById('rec-live').hidden"
        " || !document.getElementById('recorder-off').hidden",
    )
    # Hidden by the page's own step (D093) is still switched on.
    return page.evaluate("!document.getElementById('rec-live').hidden")


def submit_assessment(page, live_server) -> str:
    """Upload a file on the submit page, listen-back step, submit; return the id."""
    page.goto("/")
    expect(page.locator(".task")).not_to_have_count(0)
    page.get_by_role("button", name="Nói về đề này").click()  # D093: one step at a time
    page.set_input_files("#audio", str(live_server.files / "full-35s.wav"))
    expect(page.locator("#rec-take")).to_contain_text("full-35s.wav")
    page.get_by_role("button", name="Nộp bài và chấm").click()
    page.wait_for_url(re.compile(r"/report/[0-9a-f]+$"), timeout=30_000)
    return urlparse(page.url).path.rsplit("/", 1)[1]


# ---------------------------------------------------------------- shell


def test_each_role_sees_only_its_own_navigation_and_lands_on_its_home(context, live_server):
    student = context.new_page()
    login_home(student, live_server, live_server.account(), "/practice")
    # D068: one "Kết quả" entry; D075: no "Bài được giao" any more; "Lượt của
    # tôi" shows only where runs are counted.
    assert nav_texts(student) == ["Lộ trình học", "Nộp bài", "Kết quả"]
    expect(student.locator(".site-nav a[href='/my-assignments']")).to_have_count(0)

    teacher = context.browser.new_context(base_url=live_server.base_url).new_page()
    try:
        login_home(teacher, live_server, live_server.account("teacher"), "/review")
        # D054 added the classes, D076 the prompts by band; D078 took the blind rating away.
        assert nav_texts(teacher) == [
            "Hàng đợi duyệt",
            "Lớp học",
            "Lộ trình luyện",
            "Đề đánh giá",
            "Thống kê",
        ]
        expect(teacher.locator(".site-nav a[href='/rate']")).to_have_count(0)
        teacher.get_by_role("link", name=re.compile("SpeakUp")).click()
        teacher.wait_for_url(lambda url: urlparse(url).path == "/review")
    finally:
        teacher.context.close()


def test_account_menu_holds_theme_and_sign_out(context, live_server):
    page = student_page(context, live_server, "/practice")
    menu = page.locator("details.account-menu")
    page.locator("details.account-menu > summary").click()
    # D064: no terms page any more, so no link to one.
    expect(menu.get_by_role("link", name="Điều khoản sử dụng")).to_have_count(0)
    expect(menu.get_by_role("button", name="Đăng xuất")).to_be_visible()
    before = page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.locator("#theme-toggle").click()
    after = page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert {before, after} == {"light", "dark"}
    page.keyboard.press("Escape")
    expect(menu).not_to_have_attribute("open", "")
    expect(menu.get_by_role("button", name="Đăng xuất")).to_be_hidden()


# ---------------------------------------------------------------- recorder


def test_recording_waits_for_listen_back_before_anything_is_sent(context, live_server):
    page = student_page(context, live_server, "/")
    if not recorder_ready(page):
        pytest.skip("máy chủ thiếu ffmpeg nên giao diện tắt ghi âm trực tiếp")
    sent = []
    page.on("request", lambda r: sent.append(r.url) if "/api/v1/responses" in r.url else None)

    page.get_by_role("button", name="Nói về đề này").click()  # D093: one step at a time
    page.get_by_role("button", name="Bắt đầu ghi âm").click()
    page.wait_for_timeout(1_500)
    page.get_by_role("button", name="Dừng ghi âm").click()

    expect(page.locator("#rec-preview")).to_be_visible()
    # Since D092 a take under the shortest length cannot be sent at all.
    expect(page.get_by_role("button", name="Nộp bài và chấm")).to_be_disabled()
    expect(page.get_by_role("button", name="Ghi lại")).to_be_visible()
    expect(page.locator("#rec-verdict")).to_contain_text("Bản ghi quá ngắn")
    # A second press of the space bar must neither discard nor send the take.
    page.mouse.click(5, 400)
    page.keyboard.press("Space")
    expect(page.locator("#rec")).to_have_attribute("data-state", "review")
    assert sent == []

    # Since D093 "Ghi lại" drops the take and waits; the mic starts the next one.
    page.get_by_role("button", name="Ghi lại").click()
    expect(page.locator("#rec")).to_have_attribute("data-state", "idle")
    page.get_by_role("button", name="Bắt đầu ghi âm").click()
    expect(page.locator("#rec")).to_have_attribute("data-state", "recording")
    page.get_by_role("button", name="Dừng ghi âm").click()
    expect(page.locator("#rec")).to_have_attribute("data-state", "review")
    assert sent == []


def test_uploaded_file_is_heard_back_then_submitted_to_a_report(context, live_server):
    page = student_page(context, live_server, "/")
    page.get_by_role("button", name="Nói về đề này").click()  # D093: one step at a time
    page.set_input_files("#audio", str(live_server.files / "full-35s.wav"))
    expect(page.locator("#rec-take")).to_contain_text("full-35s.wav")
    expect(page.locator("#rec-take")).to_contain_text("0:35")
    expect(page.get_by_role("button", name="Chọn file khác")).to_be_visible()
    page.get_by_role("button", name="Nộp bài và chấm").click()
    page.wait_for_url(re.compile(r"/report/[0-9a-f]+$"), timeout=30_000)
    # The next step sits in the result card: a practice link for a student.
    practise = page.locator("#report-summary .next-step a").first
    expect(practise).to_have_attribute("href", re.compile(r"^/practice"))
    # D068: four parts; the machine's workings are one fold at the foot.
    expect(page.locator("#report-evidence audio")).to_be_attached()
    expect(page.locator("details#report-detail summary")).to_contain_text("Chi tiết")
    expect(page.locator(".site-nav a[aria-current='page']")).to_have_text(re.compile("Kết quả"))


def test_chosen_prompt_sits_above_the_record_button(context, live_server):
    page = student_page(context, live_server, "/")
    tasks = page.locator(".task")
    expect(tasks).not_to_have_count(0)
    second = tasks.nth(1)
    prompt = second.locator(".task-prompt").text_content().strip()
    second.click()
    page.get_by_role("button", name="Nói về đề này").click()  # D093: one step at a time
    expect(page.locator("#chosen-prompt .prompt-text")).to_have_text(prompt)
    expect(page.get_by_role("button", name="Bắt đầu ghi âm")).to_be_visible()
    expect(page.locator("#task_id")).to_have_value(second.locator("input").get_attribute("value"))


# ---------------------------------------------------------------- student lists


def test_my_responses_lists_assessments_without_a_kind_filter(context, live_server):
    page = student_page(context, live_server, "/")
    submit_assessment(page, live_server)
    # D083: a practice task is refused; there is one kind of response left.
    r = page.request.post(
        "/api/v1/responses",
        multipart={
            "audio": {
                "name": "full-35s.wav",
                "mimeType": "audio/wav",
                "buffer": (live_server.files / "full-35s.wav").read_bytes(),
            },
            "task_id": "PR-COH-A2",
        },
    )
    assert r.status == 422

    page.goto("/my-responses")
    expect(page.locator(".response-item")).to_have_count(1)
    expect(page.locator("#list-filter")).to_have_count(0)


def test_teacher_opens_the_next_free_response_and_reads_names_not_codes(context, live_server):
    learner = student_page(context, live_server, "/")
    submit_assessment(learner, live_server)
    teacher = context.browser.new_context(base_url=live_server.base_url).new_page()
    try:
        gv = live_server.account("teacher")
        live_server.teach(gv, learner.request.get("/api/v1/me").json()["pseudonym"])
        login(teacher, live_server, gv, "/review")
        next_button = teacher.get_by_role("link", name="Duyệt bài tiếp theo")
        expect(next_button).not_to_have_attribute("aria-disabled", "true")
        next_button.click()
        teacher.wait_for_url(re.compile(r"/review/[0-9a-f]+$"))
        machine = teacher.locator("#machine-score")
        expect(machine).to_contain_text("Chờ giảng viên duyệt")
        assert not re.search(r"\b[A-Z]+(?:_[A-Z]+)+\b", machine.inner_text())
        chip = teacher.locator("[data-reason]").first
        chip.click()
        expect(teacher.locator("#ly")).to_have_value(chip.get_attribute("data-reason"))
    finally:
        teacher.context.close()


# ---------------------------------------------------------------- admin


def test_admin_edits_a_threshold_and_the_submit_page_follows(context, live_server):
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    admin.goto("/admin#config")
    field = admin.locator("#cfg-min_duration_s")
    expect(field).to_have_value("20")
    try:
        field.fill("15")
        admin.once("dialog", lambda d: d.accept())
        admin.get_by_role("button", name="Lưu ngưỡng mới").click()
        expect(admin.locator("#config-body")).to_contain_text("qc-")
        # "/" sends an administrator to the admin screen (D026); a student, in a
        # context of their own, reads the new threshold on the submit page.
        ctx = context.browser.new_context(base_url=live_server.base_url)
        try:
            submitter = student_page(ctx, live_server, "/")
            expect(submitter.locator(".rec-upload .field-hint")).to_contain_text("15 đến")
        finally:
            ctx.close()
    finally:
        admin.goto("/admin#config")
        admin.locator("#cfg-min_duration_s").fill("20")
        admin.once("dialog", lambda d: d.accept())
        admin.get_by_role("button", name="Lưu ngưỡng mới").click()
        expect(admin.locator("#cfg-min_duration_s")).to_have_value("20")


def test_admin_activation_asks_first_and_only_compatible_models_offer_it(context, live_server):
    admin = context.new_page()
    login(admin, live_server, live_server.account("admin"), "/admin")
    # Accounts is the first tab since D028; models are one click away.
    admin.get_by_role("tab", name="Mô hình").click()
    rows = admin.locator(".models-table tbody tr")
    expect(rows).not_to_have_count(0)
    active = admin.locator(".models-table tr.row-active")
    expect(active).to_have_count(1)
    for i in range(rows.count()):
        row = rows.nth(i)
        if "Không tương thích" in row.inner_text() or "Không nạp được" in row.inner_text():
            expect(row.get_by_role("button", name="Kích hoạt")).to_have_count(0)
    offer = admin.get_by_role("button", name="Kích hoạt").first
    if not offer.count():
        pytest.skip("chỉ có một mô hình dùng được")
    before = active.inner_text()
    admin.once("dialog", lambda d: d.dismiss())
    offer.click()
    expect(active).to_have_text(before)


# ---------------------------------------------------------------- phone


@pytest.mark.parametrize("path", ["/", "/my-responses", "/my-progress"])
def test_phone_student_pages_keep_a_bottom_tab_bar_and_no_sideways_scroll(
    context, live_server, path
):
    page = context.new_page()
    page.set_viewport_size({"width": 375, "height": 812})
    login(page, live_server, live_server.account(), "/practice")
    page.goto(path)
    page.wait_for_load_state("networkidle")
    # Since Thắng's student navigation (f84b377) the bar is its own element.
    nav = page.locator(".app-tabbar")
    assert nav.evaluate("n => getComputedStyle(n).position") == "fixed"
    box = nav.bounding_box()
    assert box and abs(box["y"] + box["height"] - 812) < 2
    assert page.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth")


def test_the_band_blocks_fit_a_narrow_phone(context, live_server):
    """The six 3D band blocks used to be wider than a phone and push the whole
    page sideways. The band page draws them with the same rules as the
    report's podium, which a fake-ASR answer (no score) does not reach."""
    page = context.new_page()
    page.set_viewport_size({"width": 340, "height": 740})
    login(page, live_server, live_server.account(), "/practice")
    page.goto("/bands")
    expect(page.locator(".cube-stage .cube").first).to_be_visible()
    assert page.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth")
    right = page.evaluate(
        "Math.max(...[...document.querySelectorAll('.cube-stage .cube')]"
        ".map(c => c.getBoundingClientRect().right))"
    )
    assert right <= 340


def test_a_header_tab_marks_its_section_and_leaves_its_heading_in_view(context):
    """The guest bar's tabs used to keep the first one underlined wherever they
    led, and the sticky header covered the top of the section they jumped to."""
    page = context.new_page()
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/")
    for name, section in (("Phương pháp", "scaffolding-method"), ("Giảng viên", "for-teachers")):
        page.locator(".site-nav").get_by_role("link", name=name).click()
        page.wait_for_url(f"**/#{section}")
        tab = page.locator(".site-nav a[aria-current]")
        expect(tab).to_have_count(1)
        expect(tab).to_have_text(name)
        header = page.locator(".site-header").bounding_box()
        heading = page.locator(f"#{section} h2")
        wait_until(
            page,
            f"Math.abs(document.getElementById('{section}').getBoundingClientRect().top - 64) < 4",
        )
        assert heading.bounding_box()["y"] >= header["y"] + header["height"]


def test_the_progress_page_prints_as_a_report_not_as_the_screen(context, live_server):
    """ "In báo cáo" (or Ctrl+P) prints one summary page, not the screen's cards."""
    page = student_page(context, live_server, "/my-progress")
    report = page.locator("#print-report")
    expect(report).to_contain_text("Báo cáo tiến độ")  # built once the page has loaded
    assert report.evaluate("e => getComputedStyle(e).display") == "none"
    for tool in page.locator(".page-tools .button").all():
        assert tool.bounding_box()["height"] < 40  # one line each, label and icon

    page.emulate_media(media="print")
    expect(report).to_be_visible()
    expect(report.locator("h2")).to_have_text(["Kết quả", "Cần luyện tiếp", "Thành tựu"])
    expect(report).to_contain_text("không phải chứng chỉ CEFR")
    for screen_only in ("#progress-panel", "#achievements", ".site-header", ".page-tools"):
        expect(page.locator(screen_only).first).to_be_hidden()
    assert report.evaluate("e => getComputedStyle(e).opacity") == "1"  # no half-run animation
