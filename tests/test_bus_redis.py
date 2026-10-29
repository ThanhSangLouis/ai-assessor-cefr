"""The Redis bus against a real server (D050): events, work, request-reply, durability.

Runs only with AICEFR_TEST_REDIS set to a server's URL (CI starts one as a
service container; on a machine: `docker run -p 6379:6379 redis:7-alpine`).
Every test uses queue names of its own, so runs do not see each other.
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest

from aicefr.platform.bus import BusTimeout
from aicefr.platform.redis_bus import RedisBus

URL = os.getenv("AICEFR_TEST_REDIS")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not URL, reason="AICEFR_TEST_REDIS is not set"),
]


@pytest.fixture
def names():
    tag = uuid.uuid4().hex[:8]
    return lambda name: f"test.{tag}.{name}"


def _wait(event: threading.Event, seconds: float = 10.0) -> None:
    assert event.wait(seconds), "nothing arrived in time"


def test_work_sent_before_any_worker_waits_in_its_queue(names):
    queue = names("score")
    RedisBus(URL).send(queue, {"response_id": "r1"})  # no consumer yet: the broker keeps it

    got: list[dict] = []
    done = threading.Event()
    worker = RedisBus(URL)
    worker.consume(queue, lambda m: (got.append(m), done.set()))
    worker.start()
    try:
        _wait(done)
        assert got == [{"response_id": "r1"}]
    finally:
        worker.close()


def test_each_message_of_a_queue_goes_to_one_worker(names):
    queue = names("jobs")
    seen: list[str] = []
    lock = threading.Lock()
    all_in = threading.Event()

    def take(message: dict) -> None:
        with lock:
            seen.append(message["n"])
            if len(seen) == 6:
                all_in.set()

    workers = [RedisBus(URL), RedisBus(URL)]
    for w in workers:
        w.consume(queue, take)
        w.start()
    try:
        sender = RedisBus(URL)
        for n in range(6):
            sender.send(queue, {"n": str(n)})
        _wait(all_in)
        assert sorted(seen) == [str(n) for n in range(6)]  # each once
    finally:
        for w in workers:
            w.close()


def test_an_event_reaches_every_subscribing_service(names):
    topic = names("response.scored")
    arrived = {"assessment": threading.Event(), "learning": threading.Event()}
    buses = []
    for group, event in arrived.items():
        bus = RedisBus(URL)
        bus.subscribe(topic, names(group), lambda m, e=event: e.set())
        bus.start()
        buses.append(bus)
    try:
        # A subscriber's queue exists once its consumer has declared it.
        import time

        time.sleep(1.0)
        RedisBus(URL).publish(topic, {"account_id": "a", "research_use_allowed": False})
        for event in arrived.values():
            _wait(event)
    finally:
        for bus in buses:
            bus.close()


def test_a_call_gets_its_own_answer_and_a_silent_queue_times_out(names):
    queue = names("step")
    server = RedisBus(URL)
    server.serve(queue, lambda req: {"echo": req["x"] * 2})
    server.start()
    try:
        import time

        time.sleep(1.0)
        caller = RedisBus(URL)
        assert caller.call(queue, {"x": 21}, timeout=10) == {"echo": 42}
        assert caller.call(queue, {"x": 1}, timeout=10) == {"echo": 2}
    finally:
        server.close()
    with pytest.raises(BusTimeout):
        RedisBus(URL).call(names("nobody"), {"x": 1}, timeout=1.5)


def test_a_call_waits_past_the_client_default_socket_timeout(names):
    # redis-py 8 reads with a 5 s socket timeout by default, which cut every
    # BLPOP of call() at 5 s: a Whisper step took longer and the caller saw
    # "speech service unreachable" while the answer was on its way.
    queue = names("slow-step")
    server = RedisBus(URL)

    def slow(req: dict) -> dict:
        import time

        time.sleep(6.5)
        return {"echo": req["x"]}

    server.serve(queue, slow)
    server.start()
    try:
        assert RedisBus(URL).call(queue, {"x": 7}, timeout=20) == {"echo": 7}
    finally:
        server.close()
    with pytest.raises(BusTimeout):
        RedisBus(URL).call(names("nobody"), {"x": 1}, timeout=7)


def test_a_handler_that_fails_does_not_stop_the_queue(names):
    queue = names("mixed")
    done = threading.Event()
    seen: list[int] = []

    def handle(message: dict) -> None:
        if message["n"] == 0:
            raise RuntimeError("one bad message")
        seen.append(message["n"])
        done.set()

    worker = RedisBus(URL)
    worker.consume(queue, handle)
    worker.start()
    try:
        sender = RedisBus(URL)
        sender.send(queue, {"n": 0})
        sender.send(queue, {"n": 1})
        _wait(done)
        assert seen == [1]
    finally:
        worker.close()


def test_one_response_is_one_job_and_assessments_go_first(names):
    """Work sent twice for one response runs once; a lower priority number runs first."""
    queue = "speech.score"  # the deduplicated queue, with ids of this test only
    tag = names("r")
    got: list[str] = []
    done = threading.Event()
    sender = RedisBus(URL)
    sender.send(queue, {"response_id": f"{tag}-a", "priority": 5})
    sender.send(queue, {"response_id": f"{tag}-a", "priority": 5})  # the same response again
    sender.send(queue, {"response_id": f"{tag}-b", "priority": 1})

    def take(message: dict) -> None:
        if message["response_id"].startswith(tag):
            got.append(message["response_id"])
            if len(got) == 2:
                done.set()

    worker = RedisBus(URL)
    worker.consume(queue, take)
    worker.start()
    try:
        _wait(done)
        import time

        time.sleep(1.0)  # a duplicate would arrive meanwhile
        assert got == [f"{tag}-b", f"{tag}-a"]
    finally:
        worker.close()
