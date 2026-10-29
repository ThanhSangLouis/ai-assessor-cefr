"""The message bus between services: events, work queues and request-reply (D043).

Three ways one service hands something to another without calling it:

* **events** (`publish` / `subscribe`): "a response was scored". Every service
  that subscribed gets its own copy; the publisher does not know who listens.
* **work** (`send` / `consume`): a recording to score. Exactly one worker takes
  each message; with Redis the job waits in its queue until one does, so
  scoring survives a restart of either side.
* **request-reply** (`call` / `serve`): a lesson step to measure while the
  learner waits. The caller blocks for the answer, with a timeout.

Two adapters. `InlineBus` delivers in this process -- synchronously for events
and calls, through a `JobQueue` for work -- which is what the tests and a
single machine use. `RedisBus` (`redis_bus.py`, D050) uses Redis: BullMQ queues
for work (retries, priority, one job per response), Redis Streams with
consumer groups for events, and a list per queue for calls. It replaced
RabbitMQ: one piece of infrastructure instead of two.

Payloads are JSON objects. Nothing here carries audio: a recording goes into the
blob store and the message names its key.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from aicefr.ports import JobQueue

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]
Responder = Callable[[dict], dict]


class BusTimeout(Exception):
    """Nobody answered a `call` in time."""


class MessageBus(Protocol):
    # True when work sent survives a restart of the sender (a broker holds it).
    durable: bool

    def publish(self, topic: str, payload: dict) -> None: ...

    def subscribe(self, topic: str, group: str, handler: Handler) -> None: ...

    def send(self, queue: str, payload: dict) -> None: ...

    def consume(self, queue: str, handler: Handler, prefetch: int = 1) -> None: ...

    def call(self, queue: str, payload: dict, timeout: float = 120.0) -> dict: ...

    def serve(self, queue: str, responder: Responder, prefetch: int = 1) -> None: ...

    def start(self) -> None: ...

    def close(self) -> None: ...


class InlineBus:
    """Delivers in this process. Events and calls run on the caller's thread.

    Work sent to a queue in `background` goes through the job queue (a bounded
    pool, or the caller's thread in tests); any other queue is handled at once,
    in order -- a worker's "started" and "finished" must not overtake each other.
    """

    durable = False

    def __init__(self, jobs: JobQueue, background: frozenset[str] = frozenset({"speech.score"})):
        self.jobs = jobs
        self.background = background
        self._subscribers: dict[str, list[Handler]] = {}
        self._consumers: dict[str, Handler] = {}
        self._responders: dict[str, Responder] = {}

    def publish(self, topic: str, payload: dict) -> None:
        for handler in self._subscribers.get(topic, []):
            try:
                handler(payload)
            except Exception:  # noqa: BLE001 - a subscriber's failure is its own, as with a broker
                logger.exception("subscriber of %s failed", topic)

    def subscribe(self, topic: str, group: str, handler: Handler) -> None:
        self._subscribers.setdefault(topic, []).append(handler)

    def send(self, queue: str, payload: dict) -> None:
        handler = self._consumers.get(queue)
        if handler is None:
            logger.error("no consumer for %s; message dropped", queue)
            return
        if queue in self.background:
            self.jobs.enqueue(handler, payload)
            return
        try:
            handler(payload)
        except Exception:  # noqa: BLE001 - as with a broker, the sender is not told
            logger.exception("consumer of %s failed", queue)

    def consume(self, queue: str, handler: Handler, prefetch: int = 1) -> None:
        self._consumers[queue] = handler

    def call(self, queue: str, payload: dict, timeout: float = 120.0) -> dict:
        responder = self._responders.get(queue)
        if responder is None:
            raise BusTimeout(f"no service answers {queue}")
        return responder(payload)

    def serve(self, queue: str, responder: Responder, prefetch: int = 1) -> None:
        self._responders[queue] = responder

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass


def bus_from_url(url: str, jobs: JobQueue) -> MessageBus:
    """`inline` for this process, a `redis://` URL for Redis and BullMQ (D050)."""
    if url.startswith(("redis://", "rediss://")):
        from aicefr.platform.redis_bus import RedisBus

        return RedisBus(url)
    if url.startswith(("amqp://", "amqps://")):
        raise ValueError("RabbitMQ was replaced by Redis (D050): set AICEFR_BUS=redis://...")
    return InlineBus(jobs)
