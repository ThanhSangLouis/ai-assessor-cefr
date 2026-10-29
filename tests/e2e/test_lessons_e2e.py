"""Layer 3 -- E2E for the lesson path (D025): a learner climbs a lesson, a teacher
authors one and corrects the machine.

Test case ids (TC-LS-Exx) are listed in `docs/test/TEST_PLAN_D025.md`.

This module starts its own server rather than importing the shared one, for two
reasons that both come from measuring speech:

- the voice activity detector is the energy one, as in the integration tests:
  Silero (present wherever torch is installed) does not take a sine wave for
  speech, so every step would come back "not measured" on one machine and
  measured on another;
- the fake recogniser "hears" the read-aloud text of the first sample lesson, so
  a learner can pass its steps and complete it, which is the path worth walking.

Run:  pytest -m e2e   (developer machines only; CI skips this layer)
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402
from test_practice_e2e import (  # noqa: E402, F401  (fixtures are used by name)
    LiveServer,
    _free_port,
    browser,
    e2e_store,
    login,
    write_wav,
)

pytestmark = pytest.mark.e2e

LESSON = "lesson-a2-neighborhood"
# What the fake recogniser returns for every recording: the passage of the
# first step of LESSON, word for word.
HEARD = (
    "I live in a small apartment near the city center. My street is quiet, but there are "
    "many shops and a park nearby. Every morning, I walk to the bus stop. I like my "
    "neighborhood because the people are friendly and the food is cheap. The only problem "
    "is the traffic in the evening."
)
# Boot uvicorn with the energy detector swapped in, the way the integration
# tests swap it, without adding a setting to the product for a test's sake.
BOOT = (
    "import sys, uvicorn\n"
    "import aicefr.pipeline as pipeline\n"
    "from aicefr.asr.vad import EnergyVad\n"
    "pipeline.default_vad = EnergyVad\n"
    "uvicorn.run('aicefr.api.main:app', host='127.0.0.1', port=int(sys.argv[1]),"
    " log_level='warning')\n"
)


@pytest.fixture(scope="module")
def live_server(tmp_path_factory) -> Iterator[LiveServer]:
    root = tmp_path_factory.mktemp("e2e-lessons")
    db = e2e_store("lessons")
    port = _free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICEFR_")}
    env.update(
        AICEFR_DB=str(db),
        AICEFR_UPLOADS=str(root / "uploads"),
        AICEFR_JOB_MODE="inline",
        # The synthetic scoring artifacts tests/conftest.py points at (W7-S01).
        AICEFR_MODEL_DIR=os.environ["AICEFR_MODEL_DIR"],
        AICEFR_MODEL_PINS=os.environ["AICEFR_MODEL_PINS"],
        AICEFR_FAKE_TRANSCRIPT=HEARD,
        AICEFR_LOGIN_RATE="1000",
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", BOOT, str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"E2E server exited early: {proc.stderr.read().decode()[-2000:]}")
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=1) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("E2E server not ready after 60 seconds")
    files = root / "files"
    files.mkdir()
    write_wav(files / "full-35s.wav", 35)
    write_wav(files / "short-10s.wav", 10)
    try:
        yield LiveServer(base, db, files)
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture
def context(browser, live_server):
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.grant_permissions(["microphone"], origin=live_server.base_url)
    ctx.set_default_timeout(20_000)
    yield ctx
    ctx.close()


@pytest.fixture
def student(context, live_server):
    """A new student, logged in, the terms accepted, on the lesson path."""
    page = context.new_page()
    login(page, live_server, live_server.account())
    page.goto("/practice")
    return page


def teacher_page(browser, live_server):
    """A teacher in a context of their own, so two roles can act side by side."""
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.set_default_timeout(20_000)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    login(page, live_server, live_server.account("teacher"), "/teach")
    return page


def answer(page, live_server, name: str = "full-35s.wav") -> None:
    """Pick a file for the step on screen, listen-back step, submit, wait for feedback."""
    # The step must be on screen first: drawing it resets the recorder, and a file
    # picked while the lesson was still loading would be dropped (a person cannot
    # pick one then: the recorder is hidden until the lesson has loaded).
    expect(page.locator("#step-h")).to_be_visible()
    expect(page.locator("#rec")).to_have_attribute("data-state", "idle")
    page.set_input_files("#audio", str(live_server.files / name))
    expect(page.locator("#rec-take")).to_contain_text(name)
    page.get_by_role("button", name="Nộp lượt này").click()
    expect(page.locator("#step-feedback")).to_be_visible()


# The first lesson of the sample path, A1 fluency (D059).
FIRST_TITLE = "Giới thiệu bản thân thật liền"


def open_step(page, title: str) -> None:
    page.locator(".rail-step", has_text=title).click()
    expect(page.locator("#step-h")).to_have_text(title)


# ---------------------------------------------------------------- learner


def test_new_learner_sees_the_path_and_the_first_lesson_next(student):
    # D059: the sample path starts at A1.
    expect(student.locator(".next-card h2")).to_have_text(FIRST_TITLE)
    expect(student.locator(".lesson-node")).to_have_count(46)
    expect(student.locator(".lesson-node.new")).to_have_count(46)
    expect(student.locator(".path-part")).to_have_count(6)  # A1 to C2
    expect(student.locator(".lesson-node.next .node-flag")).to_have_text("Bắt đầu")
    expect(student.locator(".today-card .goal-ring")).to_contain_text("0/180 giây")
    expect(student.locator(".review-count")).to_contain_text("0")
    assert "band" not in student.locator("#path-page").inner_text().lower()


def test_read_aloud_step_marks_words_and_moves_on(student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    expect(student.locator("#step-h")).to_have_text("Đọc to có từ gợi ý")
    expect(student.locator(".read-text .hint-word")).to_have_count(6)
    answer(student, live_server)
    # The server runs the simulated recogniser: the result must say so where it
    # is read, not only in the banner at the top of the page.
    expect(student.locator("#step-feedback .notice-danger")).to_contain_text("Kết quả giả lập")
    expect(student.locator(".verdict")).to_have_text("Đạt bước này.")
    expect(student.locator("#step-feedback .w.heard")).not_to_have_count(0)
    expect(student.locator("#step-feedback .w.missed")).to_have_count(0)
    expect(student.locator(".step-rail li").first).to_have_class(re.compile(r"\bpassed\b"))
    student.get_by_role("button", name="Bước tiếp").click()
    expect(student.locator("#step-h")).to_have_text("Nghe và nhắc lại")


def test_free_step_runs_in_shrinking_rounds_and_compares_them(student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    open_step(student, "Nói tự do")
    expect(student.locator(".round-pills li.now")).to_have_text("Lượt 1 · 45 giây")
    answer(student, live_server)
    student.get_by_role("button", name="Lượt 2 · 35 giây").click()
    expect(student.locator(".round-pills li.now")).to_have_text("Lượt 2 · 35 giây")
    answer(student, live_server, "short-10s.wav")
    expect(student.locator("#step-feedback")).to_contain_text("So với lượt 1")
    expect(student.locator("#step-feedback .change-list li").first).to_contain_text(
        "Số từ mỗi phút"
    )


def test_completing_a_lesson_marks_it_done_on_the_path(student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    for _ in range(6):
        answer(student, live_server)
        student.get_by_role("button", name="Bước tiếp").click()
    # The last step is free speech; one round of it is enough to finish.
    expect(student.locator("#step-h")).to_have_text("Nói tự do")
    answer(student, live_server)
    student.goto("/practice")
    done = student.locator(
        ".lesson-node", has=student.locator(f'.node-coin[data-lesson="{LESSON}"]')
    )
    expect(done).to_have_class(re.compile(r"\bcompleted\b"))
    expect(done.locator(".lesson-state")).to_have_text("Đã hoàn thành")
    expect(student.locator(".overall")).to_contain_text("1/46 bài đã hoàn thành")
    expect(student.locator(".today-card .goal-ring")).not_to_contain_text("0/180")
    expect(student.locator(".next-card h2")).not_to_have_text("Khu phố của tôi")


def test_a_coin_on_the_trail_opens_its_card_and_then_the_lesson(student):
    coin = student.locator(".lesson-node").first.locator(".node-coin")
    coin.click()
    card = student.locator("#node-card")
    expect(card).to_be_visible()
    expect(card.locator("h3")).to_have_text(FIRST_TITLE)
    expect(coin).to_have_attribute("aria-expanded", "true")
    student.keyboard.press("Escape")
    expect(card).to_have_count(0)
    coin.click()
    card.get_by_role("link", name="Bắt đầu").click()
    first = "/practice/lessons/lesson-pr-flu-a1"
    student.wait_for_url(lambda url: urlparse(url).path == first)


def test_navigation_is_a_sidebar_on_the_left_with_icons(student):
    sidebar = student.locator(".app-sidebar")
    box = sidebar.bounding_box()
    width = student.viewport_size["width"]
    assert box and abs(box["x"]) < 1 and box["x"] + box["width"] < width / 2
    main = student.locator("main").bounding_box()
    assert main and main["x"] >= box["width"] - 1  # the page starts after the sidebar
    links = sidebar.locator(".site-nav a")
    expect(links).to_have_count(5)  # D054 added "Bài được giao"
    expect(links.first.locator("svg use")).to_have_attribute(
        "href", re.compile(r"icons\.svg.*#i-path$")
    )
    expect(sidebar.locator(".site-nav a[aria-current='page']")).to_have_text("Luyện tập")


def test_review_page_without_due_items_says_when_the_next_one_comes(student, live_server):
    # The recogniser "hears" the A2 passage, so the B1 lesson's hint words are
    # missed and come back in the review, tomorrow.
    student.goto("/practice/lessons/lesson-b1-trip")
    answer(student, live_server)
    student.goto("/practice/review")
    tomorrow = (dt.datetime.now(dt.timezone(dt.timedelta(hours=7))) + dt.timedelta(days=1)).date()
    summary = student.locator("#lesson-summary")
    expect(summary).to_contain_text("Không có mục nào đến hạn hôm nay", timeout=15_000)
    expect(summary).to_contain_text(tomorrow.strftime("%d/%m/%Y"))


def test_phone_layout_of_the_path_and_a_lesson_has_no_sideways_scroll(context, live_server):
    page = context.new_page()
    page.set_viewport_size({"width": 375, "height": 812})
    login(page, live_server, live_server.account())
    for path in ("/practice", f"/practice/lessons/{LESSON}"):
        page.goto(path)
        page.wait_for_load_state("networkidle")
        assert page.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth"), path
    rail = page.locator(".step-rail ol")
    assert rail.evaluate("n => getComputedStyle(n).display") == "flex"


# ---------------------------------------------------------------- teacher


def test_teacher_builds_a_lesson_from_a_text_and_publishes_it(browser, live_server):
    teacher = teacher_page(browser, live_server)
    try:
        expect(teacher.locator(".t-path")).not_to_have_count(0)
        teacher.locator("#new-path").click()
        teacher.fill("#path-title", "Lộ trình lớp K22")
        teacher.locator("#path-form button[type=submit]").click()
        card = teacher.locator(".t-path", has_text="Lộ trình lớp K22")
        card.get_by_role("button", name="Thêm chặng").click()
        teacher.fill("#unit-title", "Kể về trải nghiệm")
        teacher.select_option("#unit-band", "B1")
        teacher.locator("#unit-form button[type=submit]").click()
        card.get_by_role("button", name="Thêm bài học").click()
        teacher.fill("#lesson-title", "Chuyến đi cuối tuần")
        teacher.fill(
            "#lesson-text",
            "Last weekend I went to the beach with my friends. We took the bus early in the "
            "morning. The weather was sunny and the water was warm. In the evening we watched "
            "the sunset together. It was a wonderful trip.",
        )
        teacher.fill("#lesson-keywords", "beach, weather, sunset, wonderful")
        teacher.fill("#lesson-prompt", "Kể về một chuyến đi ngắn gần đây của bạn.")
        teacher.locator("#lesson-form button[type=submit]").click()
        teacher.wait_for_url(re.compile(r"/teach/lessons/l[0-9a-f]+$"))
        # B1: read aloud, gap, look up, key words, outline, free.
        expect(teacher.locator("#step-list li")).to_have_count(6)
        expect(teacher.locator("#step-list li").last).to_contain_text("Nói tự do")
        # A digit in the passage: the linter says so once the draft is saved.
        teacher.fill("#e-text", "Last weekend I went to the beach with 3 friends.")
        expect(teacher.locator("#lint-list")).to_contain_text("chữ số", timeout=10_000)
        expect(teacher.locator("#save-state")).to_contain_text("Đã lưu nháp")
        teacher.locator("#publish").click()
        expect(teacher.locator("#builder-head")).to_contain_text("Đã xuất bản v1")
        teacher.locator("#preview").click()
        teacher.wait_for_url(re.compile(r"\?preview=1$"))
        expect(teacher.locator("#preview-note")).to_contain_text("Xem thử bản nháp")
        expect(teacher.locator("#step-h")).to_have_text("Đọc to có từ gợi ý")
    finally:
        teacher.context.close()


def test_students_see_the_published_version_until_the_teacher_publishes_again(
    browser, student, live_server
):
    teacher = teacher_page(browser, live_server)
    try:
        api = teacher.request
        pid = api.post("/api/v1/teach/paths", data={"title": "Lộ trình phiên bản"}).json()[
            "path_id"
        ]
        assert api.patch(f"/api/v1/teach/paths/{pid}", data={"status": "published"}).ok
        uid = api.post(
            f"/api/v1/teach/paths/{pid}/units", data={"title": "Chặng một", "band": "A2"}
        ).json()["unit_id"]
        lid = api.post(
            f"/api/v1/teach/units/{uid}/lessons",
            data={"title": "Tên cũ", "keywords": ["market", "cheap", "fresh"]},
        ).json()["lesson_id"]
        assert api.post(f"/api/v1/teach/lessons/{lid}/publish").ok

        teacher.goto(f"/teach/lessons/{lid}")
        teacher.fill("#f-title", "Tên mới")
        expect(teacher.locator("#save-state")).to_contain_text("Đã lưu nháp", timeout=10_000)

        student.goto(f"/practice?path={pid}")
        expect(student.locator(".lesson-title")).to_have_text("Tên cũ")

        teacher.locator("#publish").click()
        expect(teacher.locator("#builder-head")).to_contain_text("Đã xuất bản v2")
        student.reload()
        expect(student.locator(".lesson-title")).to_have_text("Tên mới")
    finally:
        teacher.context.close()


def test_teacher_corrects_a_word_and_the_learner_sees_the_review(browser, student, live_server):
    student.goto(f"/practice/lessons/{LESSON}")
    answer(student, live_server)
    teacher = teacher_page(browser, live_server)
    try:
        teacher.goto("/teach/insights?path=path-sample")
        teacher.locator("[data-attempt]").first.click()
        expect(teacher.locator("#attempt-dialog")).to_be_visible()
        first = teacher.locator("#override-words .w").first
        expect(first).to_have_class(re.compile(r"\bheard\b"))
        first.click()
        expect(teacher.locator("#override-words .w").first).to_have_class(
            re.compile(r"\bunsure\b.*\bteacher\b")
        )
        teacher.fill("#override-note", "Cô nghe rõ cả đoạn, chỉ từ đầu hơi nhỏ.")
        teacher.locator("#override-save").click()
        expect(teacher.locator("#attempt-dialog")).to_be_hidden()
        expect(teacher.locator(".ins-recent tbody tr").first).to_contain_text("Đã xem lại")
    finally:
        teacher.context.close()

    student.reload()
    # Back on the lesson, the page opens at the first step not yet passed.
    open_step(student, "Đọc to có từ gợi ý")
    expect(student.locator(".last-try")).to_contain_text("Giáo viên đã xem lại")
    student.get_by_role("button", name="Xem lại kết quả").click()
    expect(student.locator("#step-feedback")).to_contain_text("Giáo viên đã xem lại lượt này")
    expect(student.locator("#step-feedback")).to_contain_text("chỉ từ đầu hơi nhỏ")
    expect(student.locator("#step-feedback .w.teacher")).to_have_count(1)


def test_students_get_no_authoring_rights(student):
    student.goto("/teach")
    expect(student.locator("#teach-paths")).to_contain_text("không có quyền soạn bài")
    r = student.request.post("/api/v1/teach/paths", data={"title": "Không được"})
    assert r.status == 403
    assert urlparse(student.url).path == "/teach"


def test_teacher_pages_fit_a_phone(browser, live_server):
    teacher = teacher_page(browser, live_server)
    try:
        teacher.set_viewport_size({"width": 375, "height": 812})
        for path in ("/teach", "/teach/insights", f"/teach/lessons/{LESSON}"):
            teacher.goto(path)
            teacher.wait_for_load_state("networkidle")
            assert teacher.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth"), (
                path
            )
    finally:
        teacher.context.close()
