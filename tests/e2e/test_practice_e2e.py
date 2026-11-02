"""Layer 3 -- E2E: the server and browser fixtures every E2E module shares.

The practice cases of D023 that lived here went with the practice tasks
(D083); the other E2E modules import these fixtures and helpers by name. A
test walks the learner's own path: log in through the form, click buttons,
pick a file or record with the fake microphone, read the exact text on screen.

Run:  pytest -m e2e   (needs `pip install -e ".[e2e]"` and `playwright install chromium`)

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

    def teach(self, teacher: str, *students: str) -> str:
        """D071: a class the teacher teaches, with these students; returns its id."""
        from aicefr.storage.auth_repository import AuthRepository
        from aicefr.storage.classroom_repository import ClassroomRepository

        auth = AuthRepository(self.db_path)
        rooms = ClassroomRepository(self.db_path)
        made = rooms.create(f"Lớp của {teacher}", [auth.get_by_pseudonym(teacher)["account_id"]])
        for s in students:
            rooms.add_member(made["class_id"], auth.get_by_pseudonym(s)["account_id"])
        return made["class_id"]


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
    page.get_by_label("Email", exact=True).fill(pseudonym)
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
