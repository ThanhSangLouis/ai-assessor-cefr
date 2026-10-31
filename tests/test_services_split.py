"""The three services apart (D044): core, speech and web, each its own application,
behind a gateway that asks the core service who is calling.

The rest of the suite runs every service in one process (`aicefr.api.main`).
This module runs them as the containers do -- a FastAPI application per
service, the web service reaching the core's facades through `RemoteFacade`,
the account forwarded in the gateway's header -- with two stand-ins: a
`TestClient` per service instead of a socket, and the in-process bus instead
of Redis (the bus itself is tested against a real server in
`test_bus_redis.py`; `over_redis` wires the services to one).
"""

from __future__ import annotations

import io
import os
from contextlib import ExitStack
from http.cookies import SimpleCookie

import numpy as np
import pytest
import soundfile as sf
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from aicefr import config
from aicefr.asr.vad import EnergyVad
from aicefr.infra.queues import InlineJobQueue
from aicefr.platform.bus import InlineBus
from aicefr.platform.callers import ACCOUNT_HEADER, GATEWAY_HEADER, encode_account
from aicefr.platform.gateway import service_for
from aicefr.platform.rpc import INTERNAL_HEADER, RemoteFacade
from aicefr.services import Peers
from aicefr.storage.auth_repository import Account, Role

pytestmark = pytest.mark.integration

TOKEN = "kiem-thu-khoa-noi-bo-" + "x" * 24
GATEWAY_TOKEN = "kiem-thu-khoa-cong-vao-" + "y" * 24
PASSWORD = "matkhau-kiem-thu"
HEARD = "every morning I walk to the bus stop near my home"


def _wav(seconds: float) -> bytes:
    t = np.arange(int(16_000 * seconds)) / 16_000
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), 16_000, format="WAV")
    return buf.getvalue()


class Gateway:
    """What nginx does with deploy/gateway/default.conf.template, for one browser."""

    def __init__(self, clients: dict[str, TestClient]) -> None:
        self.clients = clients
        self.cookies: dict[str, str] = {}

    def _client(self, service: str) -> TestClient:
        """The service's client with an empty cookie jar: this browser's cookies only.

        The clients are shared by every Gateway of a test, and httpx keeps the
        cookies of each response in the client. Whether a request's own
        `cookies=` then wins over the jar depends on the httpx version (httpx2
        2.16 sent the last login's session instead), so the jar is cleared.
        """
        client = self.clients[service]
        client.cookies.clear()
        return client

    def _account_header(self) -> str:
        r = self._client("core").get(
            "/internal/identity/session",
            headers={GATEWAY_HEADER: GATEWAY_TOKEN},
            cookies=self.cookies,
        )
        assert r.status_code == 200, r.text
        return r.headers.get(ACCOUNT_HEADER, "")

    def request(self, method: str, path: str, **kwargs):
        service = service_for(path.split("?")[0])
        if service is None:
            return None
        headers = {
            **kwargs.pop("headers", {}),
            ACCOUNT_HEADER: self._account_header(),
            GATEWAY_HEADER: GATEWAY_TOKEN,
            INTERNAL_HEADER: "",  # nginx drops whatever the browser sent
        }
        r = self._client(service).request(
            method, path, headers=headers, cookies=self.cookies, **kwargs
        )
        for value in r.headers.get_list("set-cookie"):
            for name, morsel in SimpleCookie(value).items():
                if morsel.value:
                    self.cookies[name] = morsel.value
                else:
                    self.cookies.pop(name, None)
        return r

    def get(self, path: str, **kw):
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw):
        return self.request("POST", path, **kw)

    def login(self, pseudonym: str) -> Gateway:
        r = self.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return self


def _system(monkeypatch, bus_for):
    """Three applications, wired the way docker-compose wires the containers.

    `bus_for(name)` is each service's bus: one in-process bus shared by all
    (`system`), or a Redis bus of each service's own (`over_redis`, D050).
    """
    from aicefr.services import PARTS
    from aicefr.services.core import app as core
    from aicefr.services.runtime import standalone
    from aicefr.services.speech import app as speech
    from aicefr.services.web import app as web

    monkeypatch.setenv("AICEFR_INTERNAL_TOKEN", TOKEN)
    monkeypatch.setenv("AICEFR_GATEWAY_TOKEN", GATEWAY_TOKEN)
    monkeypatch.setenv("AICEFR_FAKE_TRANSCRIPT", HEARD)
    monkeypatch.setattr("aicefr.pipeline.default_vad", EnergyVad)
    config.get_settings.cache_clear()
    settings = config.get_settings()

    clients: dict[str, TestClient] = {}

    def to_core(method: str, path: str, body: dict | None):
        r = clients["core"].request(method, path, json=body, headers={INTERNAL_HEADER: TOKEN})
        return r.status_code, r.json()

    apps = {
        "core": standalone("core", core.build, settings, peers=Peers(), bus=bus_for("core"),
                           login_rate_limit=True),
        "speech": standalone("speech", speech.build, settings, peers=Peers(),
                             bus=bus_for("speech")),
        "web": standalone(
            "web",
            web.build,
            settings,
            peers=Peers(**{part: RemoteFacade(part, to_core) for part in PARTS}),
            bus=bus_for("web"),
            static=True,
        ),
    }  # fmt: skip
    for name, app in apps.items():
        clients[name] = TestClient(app)
    auth = apps["core"].state.auth_repo
    for pseudonym, role in (
        ("SV-001", Role.STUDENT),
        ("GV-01", Role.TEACHER),
        ("QT-01", Role.ADMIN),
    ):
        auth.create_account(pseudonym, PASSWORD, role)
    return {"apps": apps, "clients": clients, "settings": settings}


@pytest.fixture
def system(monkeypatch, tmp_path):
    bus = InlineBus(InlineJobQueue())  # one in-process bus, every service on it
    yield _system(monkeypatch, lambda _name: bus)
    config.get_settings.cache_clear()


REDIS = os.getenv("AICEFR_TEST_REDIS")


@pytest.fixture
def over_redis(monkeypatch, tmp_path):
    """Each service with a Redis bus of its own, started as its container starts it."""
    if not REDIS:
        pytest.skip("AICEFR_TEST_REDIS is not set")
    import redis

    from aicefr.platform.redis_bus import RedisBus

    redis.Redis.from_url(REDIS).flushdb()  # a test server: queues of earlier runs go
    buses = {}
    built = _system(monkeypatch, lambda name: buses.setdefault(name, RedisBus(REDIS)))
    with ExitStack() as stack:
        # Entering a client runs the application's lifespan, which starts its bus.
        built["clients"] = {
            name: stack.enter_context(TestClient(app)) for name, app in built["apps"].items()
        }
        yield built
    config.get_settings.cache_clear()


# ================================================================= routing


def test_every_route_of_every_service_reaches_that_service_through_the_gateway(system):
    for name, app in system["apps"].items():
        for route in app.routes:
            if not isinstance(route, APIRoute) or route.path in ("/healthz", "/readyz", "/metrics"):
                continue
            path = route.path.replace("{", "").replace("}", "")
            expected = None if path.startswith("/internal/") else name
            assert service_for(path) == expected, f"{route.path} of {name}"


def test_the_committed_gateway_configuration_is_generated_from_the_table():
    import subprocess
    import sys
    from pathlib import Path

    tool = Path(__file__).resolve().parents[1] / "tools" / "gen_gateway.py"
    assert subprocess.run([sys.executable, str(tool), "--check"]).returncode == 0


# ================================================================= trust


def test_an_account_header_is_trusted_only_beside_the_gateway_key(system):
    forged = encode_account(Account("x", "QT-99", Role.ADMIN))
    assessment = system["clients"]["core"]
    assert assessment.get("/api/v1/stats", headers={ACCOUNT_HEADER: forged}).status_code == 401
    # The internal key -- what a service holds for its calls -- is not the gateway's.
    with_internal = assessment.get(
        "/api/v1/stats", headers={ACCOUNT_HEADER: forged, INTERNAL_HEADER: TOKEN}
    )
    assert with_internal.status_code == 401
    odd = assessment.get(
        "/api/v1/stats", headers={ACCOUNT_HEADER: forged, GATEWAY_HEADER: "ê".encode("latin-1")}
    )
    assert odd.status_code == 401  # refused, not a 500
    # And the session check answers the gateway only.
    identity = system["clients"]["core"]
    assert identity.get("/internal/identity/session").status_code == 403
    assert (
        identity.get("/internal/identity/session", headers={INTERNAL_HEADER: TOKEN}).status_code
        == 403
    )


def test_internal_calls_need_the_key(system):
    identity = system["clients"]["core"]
    assert (
        identity.post("/internal/identity/count_role", json={"role": "student"}).status_code == 403
    )
    wrong = identity.post(
        "/internal/identity/count_role", json={"role": "student"}, headers={INTERNAL_HEADER: "no"}
    )
    assert wrong.status_code == 403
    right = identity.post(
        "/internal/identity/count_role", json={"role": "student"}, headers={INTERNAL_HEADER: TOKEN}
    )
    assert right.json() == {"result": 1}
    hidden = identity.post("/internal/identity/__init__", json={}, headers={INTERNAL_HEADER: TOKEN})
    assert hidden.status_code == 404


def test_the_gateway_never_forwards_internal_paths(system):
    assert Gateway(system["clients"]).get("/internal/identity/session") is None


# ================================================================= one day, across the services


def test_a_student_submits_practises_and_is_erased_across_the_services(system):
    clients = system["clients"]
    student = Gateway(clients).login("SV-001")
    assert student.get("/api/v1/me").json()["pseudonym"] == "SV-001"

    # core -> speech (bus) -> core: the response is scored and saved.
    r = student.post(
        "/api/v1/responses",
        files={"audio": ("a.wav", _wav(35), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    rid = r.json()["response_id"]
    status = student.get(f"/api/v1/responses/{rid}/status").json()
    assert status["is_pending"] is False and status["status"] != "FAILED"

    # learning -> speech (request-reply) -> learning.
    lesson = "lesson-a2-neighborhood"
    r = student.post(
        f"/api/v1/learn/lessons/{lesson}/steps/{lesson}-s5/attempts",
        files={"audio": ("s.wav", _wav(4), "audio/wav")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["missing"] == []

    # web: the sidebar asks assessment and learning; reminders ask metering too (D055).
    assert set(student.get("/api/v1/me/badges").json()) == {
        "assignments",
        "in_class",  # D068: the sidebar's "Bài được giao" waits for a class
        "results",
        "results_seen_at",
        "reviews_due",
    }
    assert student.get("/api/v1/me/nudges").status_code == 200
    # web: a page drawn with the limits assessment applies.
    page = student.get("/practice/lessons/lesson-a2-neighborhood")
    assert page.status_code == 200 and "SV-001" in page.text

    # assessment: the export gathers the account's responses and learning's attempts.
    export = student.get("/api/v1/me/export.json").json()
    assert export["response_count"] == 1 and export["lesson_attempt_count"] == 1

    admin = Gateway(clients).login("QT-01")
    # identity merges every service's audit log.
    actions = [e["action"] for e in admin.get("/api/v1/audit").json()]
    assert {"auth.login", "export.personal"} <= set(actions)

    # assessment erases, and reaches learning for the lesson attempts.
    preview = admin.get("/api/v1/admin/erase/SV-001").json()
    assert preview["lesson_attempts"] == 1
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["lesson_attempts"] == 1
    assert student.get("/api/v1/me/export.json").json()["lesson_attempt_count"] == 0


# ================================================================= over Redis (D050)


def test_a_submission_is_scored_and_a_step_measured_through_redis(over_redis):
    """core -> BullMQ -> speech -> BullMQ -> core, and a lesson step by request-reply."""
    import time

    student = Gateway(over_redis["clients"]).login("SV-001")
    r = student.post(
        "/api/v1/responses",
        files={"audio": ("a.wav", _wav(35), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    rid = r.json()["response_id"]
    deadline = time.monotonic() + 60
    status = {}
    while time.monotonic() < deadline:
        status = student.get(f"/api/v1/responses/{rid}/status").json()
        if not status["is_pending"]:
            break
        time.sleep(0.5)
    assert status["is_pending"] is False and status["status"] != "FAILED", status

    lesson = "lesson-a2-neighborhood"
    r = student.post(
        f"/api/v1/learn/lessons/{lesson}/steps/{lesson}-s5/attempts",
        files={"audio": ("s.wav", _wav(4), "audio/wav")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"]["missing"] == []


def test_each_service_serves_metrics_and_the_gateway_never_forwards_them(system):
    """D051: Prometheus scrapes inside the network; the gateway answers 404 outside."""
    from pathlib import Path

    for name, client in system["clients"].items():
        body = client.get("/metrics")
        assert body.status_code == 200 and "aicefr_uptime_seconds" in body.text, name
    conf = (
        Path(__file__).resolve().parents[1] / "deploy/gateway/default.conf.template"
    ).read_text()
    assert "location = /metrics {\n        return 404;" in conf
