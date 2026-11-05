"""D086 unit layer: the hub, the stream, the channel and the gateway route.

* the hub hands an event to the streams it is addressed to -- an account, or
  every stream of a role -- and to no other; a slow stream drops frames, an
  account holds at most MAX_PER_ACCOUNT streams;
* a stream starts with `ready`, carries events and heartbeats, and ends after
  its lifetime so the browser reconnects through the gateway;
* publishing never raises; an event crosses processes unchanged;
* the gateway sends the stream unbuffered to the core service.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from aicefr.platform.gateway import STREAMS, nginx_config, service_for
from aicefr.platform.live import (
    Live,
    LiveEvent,
    LiveHub,
    TooManyConnections,
    live_from_url,
    stream,
)

pytestmark = pytest.mark.unit


def _drain(sub) -> list[str]:
    frames = []
    while not sub.queue.empty():
        frames.append(sub.queue.get_nowait())
    return frames


def test_an_event_reaches_its_accounts_and_roles_and_nobody_else():
    async def run():
        hub = LiveHub()
        student = hub.open("a1", "student")
        other = hub.open("a2", "student")
        teacher = hub.open("t1", "teacher")
        admin = hub.open("q1", "admin")
        hub.deliver(
            LiveEvent("queue.changed", accounts=frozenset({"t1"}), roles=frozenset({"admin"}))
        )
        hub.deliver(
            LiveEvent("response.finished", {"response_id": "r1"}, accounts=frozenset({"a1"}))
        )
        await asyncio.sleep(0)  # the frames are handed over on the loop
        return [_drain(s) for s in (student, other, teacher, admin)]

    student, other, teacher, admin = asyncio.run(run())
    assert student == ['event: response.finished\ndata: {"response_id": "r1"}\n\n']
    assert other == []
    assert teacher == admin == ["event: queue.changed\ndata: {}\n\n"]


def test_an_account_holds_a_bounded_number_of_streams_and_a_full_queue_drops():
    async def run():
        hub = LiveHub(max_per_account=2)
        first = hub.open("a1", "student")
        hub.open("a1", "student")
        with pytest.raises(TooManyConnections):
            hub.open("a1", "student")
        hub.close(first)
        third = hub.open("a1", "student")  # a closed stream frees its place
        for _ in range(third.queue.maxsize + 5):
            hub.deliver(LiveEvent("x", accounts=frozenset({"a1"})))
        await asyncio.sleep(0)
        return third.queue.qsize(), third.queue.maxsize, hub.count("a1")

    size, limit, open_streams = asyncio.run(run())
    assert size == limit and open_streams == 2


def test_a_stream_says_ready_carries_events_and_heartbeats_and_ends_on_time():
    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        frames = []
        started = time.monotonic()
        async for frame in stream(hub, sub, heartbeat_s=0.05, lifetime_s=0.3):
            frames.append(frame)
            if len(frames) == 1:
                hub.deliver(
                    LiveEvent("review.done", {"response_id": "r1"}, accounts=frozenset({"a1"}))
                )
        return frames, time.monotonic() - started, hub.count()

    frames, took, left = asyncio.run(run())
    assert frames[0].startswith("retry: ") and "event: ready" in frames[0]
    assert 'event: review.done\ndata: {"response_id": "r1"}\n\n' in frames
    assert ": ping\n\n" in frames
    assert 0.25 < took < 2 and left == 0  # ended by itself, and let go of its place


def test_publishing_never_raises_and_an_event_for_nobody_is_not_sent():
    sent = []

    class Broken:
        def publish(self, event):
            sent.append(event)
            raise ConnectionError("redis is down")

    live = Live(LiveHub(), Broken())
    live.notify("queue.changed", accounts=[None])  # nobody to tell
    assert sent == []
    live.notify("queue.changed", accounts=["t1"])  # the action that caused it is done
    assert len(sent) == 1


def test_an_event_crosses_processes_unchanged_and_the_channel_follows_the_bus():
    event = LiveEvent("review.done", {"response_id": "r1", "status": "COMPLETED"},
                      frozenset({"a1"}), frozenset({"admin"}))  # fmt: skip
    assert LiveEvent.from_json(event.to_json()) == event
    assert type(live_from_url("inline", LiveHub())).__name__ == "InlineLive"
    pytest.importorskip("redis")
    assert type(live_from_url("redis://localhost:6379/0", LiveHub())).__name__ == "RedisLive"


def test_the_gateway_streams_the_events_to_core_unbuffered():
    assert service_for("/api/v1/me/events") == "core"
    conf = nginx_config()
    block = conf.split("location = /api/v1/me/events {", 1)[1].split("\n    }", 1)[0]
    assert "auth_request /_session;" in block
    assert "proxy_buffering off;" in block and "proxy_read_timeout 1h;" in block
    # Only the stream: every other route keeps nginx's buffering.
    assert conf.count("proxy_buffering off;") == len(STREAMS) == 1


def test_stopping_the_process_ends_every_stream_at_once_even_a_full_one():
    async def run():
        hub = LiveHub()
        busy = hub.open("a1", "student")
        for _ in range(busy.queue.maxsize):
            busy.queue.put_nowait(": old\n\n")  # a stream that fell behind
        quiet = hub.open("a2", "student")
        started = time.monotonic()

        async def frames(sub):
            return [f async for f in stream(hub, sub, heartbeat_s=5, lifetime_s=60)]

        hub.end_all()  # SIGTERM: the container is being replaced
        await asyncio.sleep(0)  # handed over on the loop, onto a full queue
        reading = [asyncio.create_task(frames(s)) for s in (busy, quiet)]
        done = await asyncio.wait_for(asyncio.gather(*reading), 2)
        return done, time.monotonic() - started, hub.count()

    (busy, quiet), took, left = asyncio.run(run())
    assert took < 1 and left == 0  # not the 60 s lifetime, not uvicorn's cancel
    assert quiet == ["retry: 5000\nevent: ready\ndata: {}\n\n"]
    # A full queue gives up its oldest frame for the end; the rest is still sent.
    assert busy[0].startswith("retry:") and busy[1:] == [": old\n\n"] * (64 - 1)


# ======================================================== SEC-05: the session behind a stream


class Session:
    """A stand-in for the session check: valid until `reason` names why it ended."""

    def __init__(self) -> None:
        self.reason: str | None = None
        self.calls = 0

    def __call__(self) -> str | None:
        self.calls += 1
        return self.reason


def test_a_stream_ends_soon_after_its_session_does_and_carries_nothing_after():
    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        session = Session()
        frames = []
        started = time.monotonic()
        async for frame in stream(
            hub, sub, heartbeat_s=5, lifetime_s=30, check=session, recheck_s=0.05
        ):
            frames.append(frame)
            if len(frames) == 1:
                session.reason = "session_revoked"  # signed out in another tab
                hub.deliver(LiveEvent("review.done", {"response_id": "r1"}, frozenset({"a1"})))
        return frames, time.monotonic() - started, hub.count()

    frames, took, left = asyncio.run(run())
    assert frames == ["retry: 5000\nevent: ready\ndata: {}\n\n"]  # r1 was not told
    assert took < 1 and left == 0  # not the 30 s lifetime


def test_a_stream_rechecks_its_session_on_its_own_while_no_event_comes(caplog):
    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        session = Session()

        async def end_later():
            await asyncio.sleep(0.15)
            session.reason = "account_disabled"

        ending = asyncio.create_task(end_later())
        started = time.monotonic()
        frames = [
            f
            async for f in stream(
                hub, sub, heartbeat_s=5, lifetime_s=30, check=session, recheck_s=0.05,
                session_id="abcdef0123456789",
            )
        ]  # fmt: skip
        await ending
        return frames, time.monotonic() - started, session.calls

    with caplog.at_level("INFO", logger="aicefr.platform.live"):
        frames, took, calls = asyncio.run(run())
    assert len(frames) == 1 and took < 1 and calls >= 2
    closed = [r for r in caplog.records if "session.stream_closed" in r.getMessage()]
    assert len(closed) == 1
    assert "account_disabled" in closed[0].getMessage()
    assert "abcdef0123456789" in closed[0].getMessage()


def test_a_stream_whose_session_holds_keeps_its_events_and_heartbeats():
    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        session = Session()
        frames = []
        async for frame in stream(
            hub, sub, heartbeat_s=0.05, lifetime_s=0.3, check=session, recheck_s=0.02
        ):
            frames.append(frame)
            if len(frames) == 1:
                hub.deliver(LiveEvent("review.done", {"response_id": "r1"}, frozenset({"a1"})))
        return frames, session.calls

    frames, calls = asyncio.run(run())
    assert 'event: review.done\ndata: {"response_id": "r1"}\n\n' in frames
    assert ": ping\n\n" in frames and calls >= 3


def test_a_session_check_that_fails_ends_the_stream_rather_than_keeping_it():
    def broken() -> str | None:
        raise ConnectionError("the store is unreachable")

    async def run():
        hub = LiveHub()
        sub = hub.open("a1", "student")
        frames = [
            f
            async for f in stream(
                hub, sub, heartbeat_s=5, lifetime_s=30, check=broken, recheck_s=0.02
            )
        ]
        return frames, hub.count()

    frames, left = asyncio.run(asyncio.wait_for(run(), 2))
    assert len(frames) == 1 and left == 0
