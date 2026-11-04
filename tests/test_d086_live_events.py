"""D086 integration layer: live events from the running application.

* the stream needs a session, carries the account's own events and nobody
  else's, and ends after AICEFR_LIVE_MAX_SECONDS;
* scoring tells the student, a flagged response and every lock or decision
  tells the reviewers, a decision tells the student -- with ids only;
* with Redis (AICEFR_TEST_REDIS), an event published by one process reaches
  the streams another process holds.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time

import pytest
from fastapi.testclient import TestClient
from test_billing import boot
from test_lessons_integration import account_id, login_as, submit_assessment

from aicefr.contracts import ReasonCode, Response, ResponseStatus
from aicefr.platform.live import LiveEvent, LiveHub
from aicefr.services.core.assessment import context, live_api

pytestmark = pytest.mark.integration


class Recorder:
    def __init__(self):
        self.events: list[LiveEvent] = []

    def publish(self, event: LiveEvent) -> None:
        self.events.append(event)

    def kinds(self) -> list[str]:
        return [e.kind for e in self.events]


@pytest.fixture
def m(tmp_path, monkeypatch):
    return boot(tmp_path, monkeypatch, AICEFR_LIVE_MAX_SECONDS="1.5", AICEFR_LIVE_HEARTBEAT="0.3")


@pytest.fixture
def recorder(m, monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(context.svc().live, "channel", rec)
    return rec


def test_the_stream_needs_a_session(m):
    assert TestClient(m.app).get("/api/v1/me/events").status_code == 401


def test_a_signed_in_tab_receives_its_own_events_on_the_stream(m):
    student = login_as(m, "SV-001")
    me = account_id(m, "SV-001")
    hub = context.svc().live.hub

    def tell_when_open():
        deadline = time.monotonic() + 5
        while hub.count(me) == 0 and time.monotonic() < deadline:
            time.sleep(0.02)
        live = context.svc().live
        live.notify("response.finished", {"response_id": "r-mine"}, accounts=[me])
        live.notify("response.finished", {"response_id": "r-other"}, accounts=["someone-else"])

    threading.Thread(target=tell_when_open, daemon=True).start()
    r = student.get("/api/v1/me/events")  # returns when the stream ends, after 1.5 s
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    assert "event: ready" in r.text and ": ping" in r.text
    assert "r-mine" in r.text and "r-other" not in r.text
    assert hub.count(me) == 0


def test_a_scored_response_tells_its_owner_by_id_only(m, recorder):
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    status = m.repo.status_of(rid)["status"]
    finished = [e for e in recorder.events if e.kind == live_api.RESPONSE_FINISHED]
    assert len(finished) == 1
    assert finished[0].accounts == {account_id(m, "SV-001")}
    assert finished[0].data == {"response_id": rid, "status": status}
    # Flagged for a teacher: the reviewers' queue changed too.
    assert (live_api.QUEUE_CHANGED in recorder.kinds()) == (status == "REVIEW_REQUIRED")


def test_locking_and_deciding_tell_the_reviewers_and_the_student(m, recorder):
    login_as(m, "SV-001")
    teacher = login_as(m, "GV-01", "teacher")
    student_id, teacher_id = account_id(m, "SV-001"), account_id(m, "GV-01")
    m.repo.save(
        Response(response_id="r-flag", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1",
                 reasons=[ReasonCode.LANGUAGE_NOT_ENGLISH]),
        "SV-001", "P3", account_id=student_id,
    )  # fmt: skip

    assert teacher.post("/api/v1/review/r-flag/lock").status_code == 200
    locked = recorder.events[-1]
    assert locked.kind == live_api.QUEUE_CHANGED
    assert teacher_id in locked.accounts and locked.roles == {"admin"} and locked.data == {}

    r = teacher.post("/api/v1/review/r-flag/close", json={"reason": "nói tiếng Việt, mời nộp lại"})
    assert r.status_code == 200
    done = [e for e in recorder.events if e.kind == live_api.REVIEW_DONE]
    assert len(done) == 1 and done[0].accounts == {student_id}
    assert done[0].data == {"response_id": "r-flag", "status": "REJECTED"}
    assert recorder.kinds()[-1] == live_api.QUEUE_CHANGED  # out of everyone's queue


def test_a_response_closed_by_the_timeout_sweep_tells_its_owner(m, recorder, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from aicefr.services.core.assessment import scoring

    login_as(m, "SV-001")
    me = account_id(m, "SV-001")
    m.repo.save(Response(response_id="r-hung", status=ResponseStatus.QUEUED, config_version="v1"),
                "SV-001", "P3", account_id=me)  # fmt: skip
    m.repo.mark_running("r-hung")
    later = datetime.now(UTC) + timedelta(seconds=context.svc().settings.job_timeout_s + 60)
    assert scoring.sweep_overdue(now=later) == ["r-hung"]
    assert recorder.events[-1].kind == live_api.RESPONSE_FINISHED
    assert recorder.events[-1].data == {"response_id": "r-hung", "status": "FAILED"}


@pytest.mark.skipif(not os.getenv("AICEFR_TEST_REDIS"), reason="AICEFR_TEST_REDIS is not set")
def test_an_event_published_in_one_process_reaches_the_streams_of_another():
    from aicefr.platform.live import RedisLive

    url = os.environ["AICEFR_TEST_REDIS"]

    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        listener = RedisLive(url, hub)  # the process holding the stream
        listener.start()
        try:
            other = RedisLive(url, LiveHub())  # the process that saw it happen
            deadline = time.monotonic() + 10
            while sub.queue.empty() and time.monotonic() < deadline:
                other.publish(LiveEvent("review.done", {"response_id": "r1"}, frozenset({"a1"})))
                await asyncio.sleep(0.2)  # until the listener has subscribed
            return await asyncio.wait_for(sub.queue.get(), 1)
        finally:
            listener.close()

    assert asyncio.run(run()) == 'event: review.done\ndata: {"response_id": "r1"}\n\n'


def test_a_failed_lookup_of_whom_to_tell_never_fails_the_action(m, recorder, monkeypatch):
    """The bus retries a handler that raised: a failure here would score twice."""
    login_as(m, "SV-001")
    student = login_as(m, "SV-002")

    def broken(*_args, **_kwargs):
        raise ConnectionError("the store is unreachable")

    monkeypatch.setattr(m.repo, "owner_of", broken)
    monkeypatch.setattr(context.svc().classrooms, "teachers_of", broken)
    rid = submit_assessment(student)  # scored in this process: on_scoring ran
    assert m.repo.status_of(rid)["status"] in ("COMPLETED", "REVIEW_REQUIRED")
    live_api.review_done(rid)
    live_api.queue_changed("someone")
