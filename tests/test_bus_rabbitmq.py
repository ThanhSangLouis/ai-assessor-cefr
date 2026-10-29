"""The RabbitMQ bus against a real broker (D043): events, work, request-reply, durability.

Runs only with AICEFR_TEST_AMQP set to a broker's URL (CI starts one as a
service container; on a machine: `docker run -p 5672:5672 rabbitmq:4-alpine`).
Every test uses queue names of its own, so runs do not see each other.
"""

from __future__ import annotations

import os
import threading
import uuid

import pytest

from aicefr.platform.bus import BusTimeout, RabbitBus

URL = os.getenv("AICEFR_TEST_AMQP")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not URL, reason="AICEFR_TEST_AMQP is not set"),
]


@pytest.fixture
def names():
    tag = uuid.uuid4().hex[:8]
    return lambda name: f"test.{tag}.{name}"


def _wait(event: threading.Event, seconds: float = 10.0) -> None:
    assert event.wait(seconds), "nothing arrived in time"


def test_work_sent_before_any_worker_waits_in_its_queue(names):
    queue = names("score")
    RabbitBus(URL).send(queue, {"response_id": "r1"})  # no consumer yet: the broker keeps it

    got: list[dict] = []
    done = threading.Event()
    worker = RabbitBus(URL)
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

    workers = [RabbitBus(URL), RabbitBus(URL)]
    for w in workers:
        w.consume(queue, take)
        w.start()
    try:
        sender = RabbitBus(URL)
        for n in range(6):
            sender.send(queue, {"n": str(n)})
        _wait(all_in)
        assert sorted(seen) == [str(n) for n in range(6)]  # each once
    finally:
        for w in workers:
            w.close()


def test_an_event_reaches_every_subscribing_service(names):
    topic = names("consent.changed")
    arrived = {"assessment": threading.Event(), "learning": threading.Event()}
    buses = []
    for group, event in arrived.items():
        bus = RabbitBus(URL)
        bus.subscribe(topic, names(group), lambda m, e=event: e.set())
        bus.start()
        buses.append(bus)
    try:
        # A subscriber's queue exists once its consumer has declared it.
        import time

        time.sleep(1.0)
        RabbitBus(URL).publish(topic, {"account_id": "a", "research_use_allowed": False})
        for event in arrived.values():
            _wait(event)
    finally:
        for bus in buses:
            bus.close()


def test_a_call_gets_its_own_answer_and_a_silent_queue_times_out(names):
    queue = names("step")
    server = RabbitBus(URL)
    server.serve(queue, lambda req: {"echo": req["x"] * 2})
    server.start()
    try:
        import time

        time.sleep(1.0)
        caller = RabbitBus(URL)
        assert caller.call(queue, {"x": 21}, timeout=10) == {"echo": 42}
        assert caller.call(queue, {"x": 1}, timeout=10) == {"echo": 2}
    finally:
        server.close()
    with pytest.raises(BusTimeout):
        RabbitBus(URL).call(names("nobody"), {"x": 1}, timeout=1.5)


def test_a_handler_that_fails_does_not_stop_the_queue(names):
    queue = names("mixed")
    done = threading.Event()
    seen: list[int] = []

    def handle(message: dict) -> None:
        if message["n"] == 0:
            raise RuntimeError("one bad message")
        seen.append(message["n"])
        done.set()

    worker = RabbitBus(URL)
    worker.consume(queue, handle)
    worker.start()
    try:
        sender = RabbitBus(URL)
        sender.send(queue, {"n": 0})
        sender.send(queue, {"n": 1})
        _wait(done)
        assert seen == [1]
    finally:
        worker.close()
