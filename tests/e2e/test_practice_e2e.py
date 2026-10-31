"""Layer 3 -- E2E: a real user in a real browser, practice mode (D023).

Each test walks the learner's own path: log in through the form, click
buttons, pick a file or record with the fake microphone, wait for the page to
move on, read the exact text on screen. The server and browser fixtures are
defined below.

Run:  pytest -m e2e   (needs `pip install -e ".[e2e]"` and `playwright install chromium`)

Test case ids (TC-PR-Exx) are listed in `docs/test/TEST_PLAN_D023.md`.

Infrastructure (server and browser fixtures) lives in this module rather than in
a `conftest.py`: the older tests import helpers with `from conftest import ...`,
and a second module named `conftest` in a sub-folder shadows the first one when
the whole suite runs.

The server is uvicorn in its own process, with a temporary database and upload
folder, processing each submission inside the request (`AICEFR_JOB_MODE=inline`)
and a fake speech recogniser. The browser is Playwright's Chromium with a fake
microphone (`--use-fake-device-for-media-stream`) so the live recording path is
exercised too.

Runs on developer machines only (the project owner's choice, 06/10/2026): CI
does not install the `e2e` extra, so `pytest.importorskip` at the top of this
module skips the whole layer there.
"""

from __future__ import annotations

import io
import itertools
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pytest
import soundfile as sf

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect  # noqa: E402

PASSWORD = "matkhau-kiem-thu"
COH_TEXT = "I like pho because it is tasty and cheap but I do not like durian so I never eat it"
_counter = itertools.count(1)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def write_wav(path: Path, seconds: float) -> Path:
    sr = 16_000
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    path.write_bytes(buf.getvalue())
    return path


class LiveServer:
    password = PASSWORD

    def __init__(self, base_url: str, db_path: str, files: Path) -> None:
        self.base_url = base_url
        self.db_path = db_path
        self.files = files

    def url(self, path: str) -> str:
        return self.base_url + path

    def account(self, role: str = "student") -> str:
        """Create a fresh account for one test: every test gets its own data."""
        from aicefr.storage.auth_repository import AuthRepository, Role

        pseudonym = f"E2E-{role[:2].upper()}-{next(_counter):03d}"
        AuthRepository(self.db_path).create_account(pseudonym, PASSWORD, Role(role))
        return pseudonym


def e2e_store(label: str) -> str:
    """A database of its own on the MongoDB server the run was given (D048).

    The server under test is another process, so an in-memory store would be
    one it cannot see: E2E needs a real server, named by AICEFR_TEST_MONGO.
    """
    server = os.getenv("AICEFR_TEST_MONGO")
    if not server:
        pytest.skip("E2E cần một MongoDB thật: đặt AICEFR_TEST_MONGO=mongodb://...")
    return f"{server.rstrip('/')}/e2e_{label}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def live_server(tmp_path_factory) -> Iterator[LiveServer]:
    root = tmp_path_factory.mktemp("e2e")
    db = e2e_store("practice")
    port = _free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICEFR_")}
    env.update(
        AICEFR_DB=str(db),
        AICEFR_UPLOADS=str(root / "uploads"),
        AICEFR_JOB_MODE="inline",
        # The synthetic scoring artifacts tests/conftest.py points at (W7-S01).
        AICEFR_MODEL_DIR=os.environ["AICEFR_MODEL_DIR"],
        AICEFR_MODEL_PINS=os.environ["AICEFR_MODEL_PINS"],
        AICEFR_FAKE_TRANSCRIPT=COH_TEXT,
        # Every test logs in once from the same 127.0.0.1; the real limit
        # (10 per minute) is tested in tests/test_security.py, not by this layer.
        AICEFR_LOGIN_RATE="1000",
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "aicefr.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
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


# Module scope, not session: test_ui_e2e.py imports these fixtures, and two
# sync_playwright() sessions cannot be open at once in one process. Each module
# opens its browser and closes it before the next module starts.
@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
        )
        yield b
        b.close()


@pytest.fixture
def context(browser, live_server):
    """A fresh browser context per test: its own cookies, cache and microphone permission."""
    ctx = browser.new_context(base_url=live_server.base_url, locale="vi-VN")
    ctx.grant_permissions(["microphone"], origin=live_server.base_url)
    ctx.set_default_timeout(15_000)
    yield ctx
    ctx.close()


pytestmark = pytest.mark.e2e


def login(page, server, pseudonym: str, next_path: str = "/practice") -> None:
    """Log in through the real form, then wait for the target page."""
    page.goto(f"/login?next={next_path}")
    page.get_by_label("Mã bút danh").fill(pseudonym)
    page.get_by_label("Mật khẩu").fill(server.password)
    page.get_by_role("button", name="Đăng nhập").click()
    # Compare the PATH, not the URL's tail: "/login?next=/practice" also ends in
    # "/practice", and waiting on the tail lets the test go on before login is done.
    page.wait_for_url(lambda url: urlparse(url).path == next_path)


def wait_until(page, expression: str, timeout_s: float = 10.0) -> None:
    """Wait for a JS expression to become true, polling through `evaluate`.

    Not `page.wait_for_function`: it polls with `new Function` inside the page,
    and the app's CSP (`script-src 'self'`, no 'unsafe-eval') blocks exactly that
    -- a sign the CSP is doing its job.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if page.evaluate(expression):
            return
        page.wait_for_timeout(100)
    raise AssertionError(f"timed out waiting for: {expression}")


@pytest.fixture
def student(context, live_server):
    """A new student, logged in, on the practice home."""
    page = context.new_page()
    login(page, live_server, live_server.account())
    page.goto("/practice")
    return page


def submit_file(page, live_server, task_id: str, name: str = "full-35s.wav") -> None:
    """A practice attempt sent the way an earlier task page sent it, then its result page.

    The task pages are folded into the lesson path (D068); results of practice
    attempts are still read on /practice/results/<id>.
    """
    r = page.request.post(
        "/api/v1/responses",
        multipart={
            "audio": {
                "name": name,
                "mimeType": "audio/wav",
                "buffer": (live_server.files / name).read_bytes(),
            },
            "task_id": task_id,
        },
    )
    assert r.ok, r.text()
    page.goto(f"/practice/results/{r.json()['response_id']}")


# The practice home of D023 (suggestion, goal ring, 15-task path) was replaced
# by the lesson path of D025; its cases live in tests/e2e/test_lessons_e2e.py.
# The task pages went in D068: their cases (TC-PR-E02, E03, E09, E14) went with them.


def test_uploading_a_file_leads_to_a_result_with_evidence(student, live_server):
    submit_file(student, live_server, "PR-COH-A2")
    expect(student.locator(".practice-banner")).to_contain_text("Hoàn thành nhiệm vụ")
    expect(student.locator(".practice-banner")).to_contain_text("2/2 mục tiêu")
    expect(student.locator(".mission.met")).to_have_count(2)
    expect(student.locator(".hit-seek").filter(has_text="because")).to_have_count(1)
    expect(student.locator(".takeaway")).to_contain_text("hoàn thành mọi mục tiêu")


def test_clicking_evidence_seeks_the_recording(student, live_server):
    submit_file(student, live_server, "PR-COH-A2")
    chip = student.locator(".hit-seek").filter(has_text="because")
    seconds = float(chip.get_attribute("data-seconds"))
    wait_until(student, "document.getElementById('player').readyState >= 1")
    chip.click()
    at = student.evaluate("document.getElementById('player').currentTime")
    assert at == pytest.approx(max(0.0, seconds - 0.3), abs=0.6)


def test_continue_button_opens_the_lesson_path(student, live_server):
    submit_file(student, live_server, "PR-COH-A2")
    student.get_by_role("link", name="Luyện tiếp theo lộ trình").click()
    student.wait_for_url(lambda url: urlparse(url).path == "/practice")


def test_too_short_file_is_rejected_with_reason_and_not_counted(student, live_server):
    submit_file(student, live_server, "PR-COH-A2", name="short-10s.wav")
    expect(student.locator(".practice-banner")).to_contain_text("Bản ghi chưa dùng được")
    expect(student.locator(".practice-banner")).to_contain_text("quá ngắn")
    daily = student.request.get("/api/v1/practice").json()["daily"]
    assert daily["today"] == 0


def test_another_learner_cannot_see_your_result(student, live_server, browser):
    submit_file(student, live_server, "PR-COH-A2")
    url = student.url
    other_ctx = browser.new_context(base_url=live_server.base_url)
    try:
        other = other_ctx.new_page()
        login(other, live_server, live_server.account())
        other.goto(url)
        expect(other.locator("#practice-result")).to_contain_text("Không tìm thấy lần luyện này")
        expect(other.locator(".mission")).to_have_count(0)
    finally:
        other_ctx.close()


def test_my_responses_tags_practice_and_opens_its_result(student, live_server):
    submit_file(student, live_server, "PR-COH-A2")
    result_url = student.url
    student.goto("/my-responses")
    row = student.locator(".response-item", has_text="Luyện tập · Mạch lạc A2")
    expect(row).to_have_count(1)
    expect(row).to_contain_text("Không chấm")
    row.get_by_role("link").first.click()
    student.wait_for_url(result_url)


def test_teacher_sees_class_practice_without_per_student_rows(student, live_server, browser):
    submit_file(student, live_server, "PR-COH-A2")
    ctx = browser.new_context(base_url=live_server.base_url)
    try:
        teacher = ctx.new_page()
        login(teacher, live_server, live_server.account("teacher"), "/review/stats")
        section = teacher.get_by_role("heading", name="Luyện tập của lớp")
        expect(section).to_be_visible()
        expect(teacher.locator("#stats-panel")).to_contain_text("lần luyện đã xử lý")
        assert "E2E-ST" not in teacher.locator("#stats-panel").inner_text()
    finally:
        ctx.close()


def test_states_are_readable_by_screen_readers(student, live_server):
    submit_file(student, live_server, "PR-COH-A2")
    hidden = student.locator(".mission .visually-hidden").first
    expect(hidden).to_have_text(re.compile("Hoàn thành"))
