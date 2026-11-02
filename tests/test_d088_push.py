"""D088 integration layer: the installable app and Web Push in the running application.

* the manifest and the service worker are served from the site's root, the
  worker never cached, every page links the manifest;
* a signed-in learner registers a browser only on a push service and with
  well-formed keys; signing it off removes it; without VAPID keys nothing is
  offered;
* a response scored or reviewed reaches the learner's devices when no SpeakUp
  tab of theirs is open, and only then;
* erasing a participant forgets their browsers.
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient
from test_billing import boot
from test_lessons_integration import account_id, login_as, submit_assessment

from aicefr.api.web import STATIC_DIR
from aicefr.contracts import ReasonCode, Response, ResponseStatus
from aicefr.notify.push import generate_vapid_keys
from aicefr.services.core.assessment import context

pytestmark = pytest.mark.integration

ENDPOINT = "https://fcm.googleapis.com/fcm/send/device-1"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def browser_keys() -> dict:
    point = base64.urlsafe_b64decode(generate_vapid_keys()[0] + "=")  # any P-256 point
    return {"p256dh": _b64(point), "auth": _b64(b"0123456789abcdef")}


@pytest.fixture
def m(tmp_path, monkeypatch):
    public, private = generate_vapid_keys()
    return boot(
        tmp_path, monkeypatch, AICEFR_VAPID_PUBLIC_KEY=public, AICEFR_VAPID_PRIVATE_KEY=private
    )


@pytest.fixture
def sent(m, monkeypatch):
    """Every message the push services would receive, sent at once."""
    out: list[tuple[str, dict]] = []
    push = context.svc().push
    monkeypatch.setattr(push, "_run", lambda job: job())
    monkeypatch.setattr(
        push, "_send", lambda info, data: out.append((info["endpoint"], json.loads(data))) or 201
    )
    return out


def subscribe(client: TestClient, endpoint: str = ENDPOINT):
    return client.put("/api/v1/me/push", json={"endpoint": endpoint, "keys": browser_keys()})


def test_the_app_is_installable_from_the_sites_root(m):
    c = TestClient(m.app)
    manifest = c.get("/manifest.webmanifest")
    assert manifest.headers["content-type"].startswith("application/manifest+json")
    d = manifest.json()
    assert (d["short_name"], d["display"], d["start_url"], d["lang"]) == (
        "SpeakUp",
        "standalone",
        "/",
        "vi",
    )
    sizes = {(i["sizes"], i.get("purpose", "any")) for i in d["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= sizes
    for icon in d["icons"]:  # every icon named is there
        assert (STATIC_DIR / icon["src"].removeprefix("/static/")).is_file()
    worker = c.get("/sw.js")
    assert worker.headers["content-type"].startswith("text/javascript")
    assert worker.headers["cache-control"] == "no-cache"
    assert worker.headers["service-worker-allowed"] == "/"
    assert 'addEventListener("push"' in worker.text
    page = c.get("/login").text
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert 'name="theme-color"' in page


def test_a_learner_registers_a_browser_on_a_push_service_only(m):
    assert TestClient(m.app).get("/api/v1/me/push").status_code == 401
    student = login_as(m, "SV-001")
    me = account_id(m, "SV-001")
    config = student.get("/api/v1/me/push").json()
    assert config["enabled"] is True and config["public_key"] == context.svc().push.public_key

    assert subscribe(student).status_code == 200
    store = context.svc().push.store
    assert [s.endpoint for s in store.of(me)] == [ENDPOINT]
    assert subscribe(student).status_code == 200  # the same browser again: still one
    assert len(store.of(me)) == 1

    for endpoint in ("https://169.254.169.254/latest/meta-data", "http://fcm.googleapis.com/x/y"):
        assert subscribe(student, endpoint).status_code == 422
    bad = {"endpoint": ENDPOINT, "keys": {"p256dh": "A" * 87, "auth": "B" * 22}}
    assert student.put("/api/v1/me/push", json=bad).status_code == 422
    assert len(store.of(me)) == 1

    out = student.request("DELETE", "/api/v1/me/push", json={"endpoint": ENDPOINT})
    assert out.json() == {"removed": True} and store.of(me) == []


def test_without_vapid_keys_notifications_are_not_offered(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_VAPID_PUBLIC_KEY="", AICEFR_VAPID_PRIVATE_KEY="")
    student = login_as(m, "SV-001")
    assert student.get("/api/v1/me/push").json() == {"enabled": False, "public_key": None}
    assert subscribe(student).status_code == 503


def test_a_scored_response_reaches_the_learners_devices_when_no_tab_is_open(m, sent):
    student = login_as(m, "SV-001")
    subscribe(student)
    rid = submit_assessment(student)
    assert len(sent) == 1
    endpoint, message = sent[0]
    assert endpoint == ENDPOINT
    assert set(message) == {"title", "body", "url", "tag"}  # no score, no name
    assert message["url"] == f"/report/{rid}" and message["tag"] == f"response-{rid}"
    assert message["title"] in ("Bài nói đã chấm xong", "Bài nói đã có điểm tạm")


def test_an_open_tab_hears_it_on_the_live_stream_instead(m, sent, monkeypatch):
    student = login_as(m, "SV-001")
    subscribe(student)
    hub = context.svc().live.hub
    me = account_id(m, "SV-001")
    monkeypatch.setattr(hub, "count", lambda account=None: 1 if account == me else 0)
    submit_assessment(student)
    assert sent == []


def test_a_teachers_decision_reaches_the_learners_devices(m, sent):
    student = login_as(m, "SV-001")
    subscribe(student)
    teacher = login_as(m, "GV-01", "teacher")
    m.repo.save(
        Response(response_id="r-flag", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1",
                 reasons=[ReasonCode.LANGUAGE_NOT_ENGLISH]),
        "SV-001", "P3", account_id=account_id(m, "SV-001"),
    )  # fmt: skip
    teacher.post("/api/v1/review/r-flag/lock")
    r = teacher.post("/api/v1/review/r-flag/close", json={"reason": "nói tiếng Việt, mời nộp lại"})
    assert r.status_code == 200
    assert [msg["title"] for _e, msg in sent] == ["Giảng viên đã duyệt bài nói"]
    assert sent[0][1]["url"] == "/report/r-flag"


def test_erasing_a_participant_forgets_their_browsers(m):
    student = login_as(m, "SV-001")
    subscribe(student)
    admin = login_as(m, "QT-01", "admin")
    r = admin.post(
        "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
    )
    assert r.status_code == 200
    assert context.svc().push.store.of(account_id(m, "SV-001")) == []
