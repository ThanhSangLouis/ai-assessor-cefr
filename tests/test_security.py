"""Security regressions. Each test corresponds to a finding from the audit.

Written after a review found a stored XSS that reached a teacher's session, a
decompression bomb that could exhaust memory, and a login endpoint whose
response time revealed which accounts exist. None of those were caught by the
functional tests, because each is a property of the system rather than a result
it returns.
"""

from __future__ import annotations

import io
import pathlib
import re
import subprocess
import time

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from aicefr.audio.decoder import MAX_DECODE_SECONDS, FirstMatchDecoder, ffmpeg_available, sniff
from aicefr.auth.pseudonyms import validate_pseudonym
from aicefr.storage.auth_repository import Role

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib

    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def login_as(app, pseudonym: str, role: str) -> TestClient:
    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200
    return c


def wav(seconds: float = 40.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


# ---------------------------------------------------------------- headers


def test_every_page_carries_the_security_headers(app) -> None:
    r = TestClient(app).get("/login")
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "microphone=(self)" in r.headers["permissions-policy"]


def test_api_responses_are_never_cached(app) -> None:
    """Reports and recordings are personal data; no shared cache may keep them."""
    c = login_as(app, "SV-001", "student")
    assert "no-store" in c.get("/api/v1/tasks").headers["cache-control"]


def test_every_response_carries_a_request_id(app) -> None:
    assert TestClient(app).get("/login").headers["x-request-id"]


def test_an_inbound_request_id_is_kept(app) -> None:
    """So a trace started at the proxy survives into our logs."""
    r = TestClient(app).get("/login", headers={"x-request-id": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


# ---------------------------------------------------------------- XSS


def test_pseudonyms_cannot_carry_markup() -> None:
    """The pseudonym reaches a teacher screen, so it must not open a tag.

    An allowlist, not a blocklist: a blocklist of forbidden substrings has to
    anticipate every spelling of every identifier, and lets markup straight
    through.
    """
    for payload in ("<svg onload=alert(1)>", '"><script>x</script>', "a'b", "x y"):
        with pytest.raises(ValueError):
            validate_pseudonym(payload)


def test_queue_screen_escapes_every_user_value() -> None:
    """The review queue was the one screen missing escaping."""
    source = pathlib.Path("src/aicefr/api/static/queue.js").read_text(encoding="utf-8")
    for field in ("speaker_id", "locked_by", "overall_band"):
        assert f"escapeHtml(r.{field}" in source, f"{field} chua duoc escape"
    # D078: the prompt is shown by its band title, escaped like the rest.
    assert "escapeHtml(titles[r.task_id]" in source


def test_login_redirect_stays_on_this_site() -> None:
    """`?next=` used to accept any URL, including another host. It now goes through
    sitePath, which resolves the path against this origin: "//evil.example" and
    "/\\evil.example" (read by browsers as "//evil.example") are both refused (D092)."""
    common = pathlib.Path("src/aicefr/api/static/common.js").read_text(encoding="utf-8")
    assert "url.origin !== location.origin" in common
    source = pathlib.Path("src/aicefr/api/static/login.js").read_text(encoding="utf-8")
    assert "location.assign(location.origin + path)" in source


def test_readyz_names_a_failed_check_without_the_exception_text(app, monkeypatch) -> None:
    """/readyz is public: an exception's text (a host, a path, a connection string)
    goes to the log, the response only says which check failed."""
    import sys

    def broken() -> None:
        raise RuntimeError("mongodb://admin:secret@db.internal:27017")

    monkeypatch.setattr(sys.modules["aicefr.api.main"].repo, "stats", broken)
    r = TestClient(app).get("/readyz")
    assert r.status_code == 503
    assert r.json()["checks"]["database"] == "failed"
    assert "secret" not in r.text and "db.internal" not in r.text


@pytest.mark.parametrize("path", ["/retell/x&next=evil.example", "/billing/orders/x&a=b/receipt"])
def test_the_sign_in_detour_keeps_the_whole_path_in_next(app, path) -> None:
    """A path parameter is encoded into `next`, so it cannot add query parameters."""
    from urllib.parse import parse_qs, quote, urlsplit

    r = TestClient(app).get(quote(path, safe="/"), follow_redirects=False)
    assert r.status_code == 303
    query = parse_qs(urlsplit(r.headers["location"]).query)
    assert query == {"next": [path]}


# SEC-04: startsWith alone let through "/\evil", a tab or a newline, which the
# browser's URL parser still reads as another origin.
NEXT_CASES = [
    ("/practice", "/practice"),
    ("/practice?x=1#top", "/practice?x=1#top"),
    ("/my-progress?q=a%20b", "/my-progress?q=a%20b"),
    ("https://evil.example/", None),
    ("http://localhost:8000.evil.example/", None),
    ("//evil.example", None),
    ("/\\evil.example", None),
    ("\\/evil.example", None),
    ("\\\\evil.example", None),
    ("/%5Cevil.example", None),
    ("/%2F%2Fevil.example", None),
    ("/%2f/evil.example", None),
    ("/\t/evil.example", None),
    ("/\n/evil.example", None),
    ("/\r/evil.example", None),
    ("/%09/evil.example", None),
    ("/ /evil.example", None),
    ("/\x00/evil.example", None),
    ("javascript:alert(1)", None),
    ("JavaScript:alert(1)", None),
    ("data:text/html,x", None),
    ("", None),
    (None, None),
]


def test_login_next_is_resolved_against_this_origin() -> None:
    """SEC-04: `safeNext` in login.js keeps only paths of this origin."""
    import json
    import re
    import shutil

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed here")
    source = pathlib.Path("src/aicefr/api/static/login.js").read_text(encoding="utf-8")
    found = re.search(r"^function safeNext\(.*?^}$", source, re.S | re.M)
    assert found, "login.js must define a pure function safeNext(value, origin)"
    script = (
        found.group(0)
        + "\nconst cases = JSON.parse(process.argv[1]);"
        + "\nprocess.stdout.write(JSON.stringify("
        + "cases.map(([v]) => safeNext(v, 'http://localhost:8000'))));"
    )
    out = subprocess.run(
        [node, "-e", script, json.dumps(NEXT_CASES)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    got = json.loads(out.stdout)
    for (value, want), have in zip(NEXT_CASES, got, strict=True):
        assert have == want, f"safeNext({value!r}) = {have!r}, expected {want!r}"


# ---------------------------------------------------------------- uploads


def test_a_renamed_non_audio_file_is_rejected(app) -> None:
    """The server decides what a file is from its bytes, not from its name."""
    c = login_as(app, "SV-001", "student")
    r = c.post(
        "/api/v1/responses",
        files={"audio": ("voice.wav", b"MZ this is an executable, not audio", "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 415


def test_sniffing_recognises_the_formats_we_accept() -> None:
    assert sniff(wav(1)[:16]) == "wav"
    assert sniff(b"not audio at all") is None


def test_upload_is_capped_before_it_reaches_memory(app) -> None:
    """The size limit is counted while writing, not after reading it all in."""
    c = login_as(app, "SV-001", "student")
    oversized = b"RIFF" + b"x" * (26 * 1024 * 1024)
    r = c.post(
        "/api/v1/responses",
        files={"audio": ("big.wav", oversized, "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 413


def test_upload_over_the_decoded_budget_is_refused_before_queueing(app, monkeypatch) -> None:
    """SEC-02: mot WAV/FLAC nho co the khai header bung ra hang GB float32.

    Core doc header (khong doc mau) va tu choi 413 truoc khi luu blob/xep hang.
    """
    from aicefr import config

    c = login_as(app, "SV-001", "student")
    monkeypatch.setenv("AICEFR_MAX_DECODED_BYTES", "1000")
    config.get_settings.cache_clear()
    try:
        r = c.post(
            "/api/v1/responses",
            files={"audio": ("a.wav", wav(2), "audio/wav")},
            data={"task_id": "P3"},
        )
    finally:
        monkeypatch.delenv("AICEFR_MAX_DECODED_BYTES")
        config.get_settings.cache_clear()
    assert r.status_code == 413
    assert "giải mã" in r.json()["detail"]
    # Trong ngan sach mac dinh thi van nhan nhu cu.
    r = c.post(
        "/api/v1/responses",
        files={"audio": ("a.wav", wav(40), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202


@pytest.mark.skipif(not ffmpeg_available(), reason="may chay test khong co ffmpeg")
def test_a_decompression_bomb_is_capped(tmp_path) -> None:
    """A small Opus file can hold hours of audio; ffmpeg must stop early.

    Without the caps, 1 MiB of Opus expands into twenty minutes of PCM and
    about 73 MiB of float32 before the quality check ever sees it.
    """
    bomb = tmp_path / "bomb.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1200",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "libopus",
            "-b:a",
            "6k",
            str(bomb),
        ],
        check=True,
    )
    assert bomb.stat().st_size < 2 * 1024 * 1024, "tep moi phai nho"
    pcm, sr = FirstMatchDecoder().decode(bomb.read_bytes(), "bomb.webm")
    assert len(pcm) / sr <= MAX_DECODE_SECONDS + 1


# ---------------------------------------------------------------- auth


def test_unknown_and_known_accounts_take_similar_time(app) -> None:
    """Response time must not reveal whether a pseudonym exists.

    Without the dummy verification, an unknown pseudonym answered in about 5 ms
    and a known one in about 300 ms, because bcrypt only ran in the second case.
    """
    login_as(app, "SV-001", "student")
    c = TestClient(app)

    def elapsed(pseudonym: str) -> float:
        start = time.perf_counter()
        c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": "wrong"})
        return time.perf_counter() - start

    known = min(elapsed("SV-001") for _ in range(3))
    unknown = min(elapsed("KHONG-CO-THAT") for _ in range(3))
    assert unknown > known * 0.3, f"lo tai khoan: {unknown:.3f}s vs {known:.3f}s"


def test_too_many_logins_from_one_address_are_throttled(app) -> None:
    """The per-account lockout stops one account being ground down.

    This stops the other shape of the attack: the same guess against every
    account in turn.
    """
    c = TestClient(app)
    codes = [
        c.post("/api/v1/auth/login", json={"pseudonym": f"SV-{i:03d}", "password": "x"}).status_code
        for i in range(15)
    ]
    assert 429 in codes


def test_limit_cannot_be_used_to_pull_the_whole_table(app) -> None:
    c = login_as(app, "SV-001", "student")
    assert c.get("/api/v1/me/responses?limit=100000000").status_code == 422


def test_health_details_require_a_session(app) -> None:
    """Model version and configuration are not public reconnaissance material."""
    assert TestClient(app).get("/api/v1/health").status_code == 401
    assert TestClient(app).get("/healthz").status_code == 200


def test_runtime_assets_are_declared_as_package_data() -> None:
    """Templates and static files must ship in the wheel.

    They are not .py files, so setuptools leaves them out unless told. An
    editable install hides this completely: it points at the source tree. The
    failure only appears once the package is really built -- which is to say in
    the container, which is to say in production, where the app died on startup
    with "Directory ... does not exist".
    """
    config = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    for pattern in ("api/templates/*.html", "api/static/*.js"):
        assert pattern in config, f"thiếu {pattern} trong package-data"
    # The scoring artifacts are the opposite: corpus statistics that must never
    # ship (W7-S01). They are read from AICEFR_MODEL_DIR at run time.
    assert "scoring/models" not in config


def test_every_template_and_static_file_ships_in_the_wheel() -> None:
    """Each file under api/static and api/templates matches a package-data glob.

    Checking a few patterns by name missed the roadmap's art (D093): it lives
    in a folder of its own, nothing declared it, and production served 404s
    for every scene and mascot while every test passed.
    """
    config = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
    data = config[config.index("[tool.setuptools.package-data]") :]
    data = data[: data.index("]", data.index("aicefr = ["))]
    package = pathlib.Path("src/aicefr")
    shipped: set[pathlib.Path] = set()
    for pattern in re.findall(r'^\s*"([^"]+)"', data, re.MULTILINE):
        shipped.update(package.glob(pattern))
    left_out = [
        str(path.relative_to(package))
        for folder in ("api/static", "api/templates")
        for path in sorted((package / folder).rglob("*"))
        if path.is_file() and not path.name.startswith(".") and path not in shipped
    ]
    assert not left_out, f"thiếu trong package-data: {left_out[:10]}"
