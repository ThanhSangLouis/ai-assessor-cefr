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
    """`?next=` used to accept any URL, including another host."""
    source = pathlib.Path("src/aicefr/api/static/login.js").read_text(encoding="utf-8")
    assert 'startsWith("/")' in source
    assert 'startsWith("//")' in source


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
