"""The message bus on Redis (D050): BullMQ for work, Redis Streams for events, lists for calls.

The same three ways of handing something over as `InlineBus` (see `bus.py`):

* **work** (`send` / `consume`) goes through a BullMQ queue. A job waits in
  Redis until a worker takes it, is retried with exponential back-off when the
  worker dies or its handler raises, and is taken over by another worker when
  the one holding it stops renewing its lock. Work for the same response is one
  job (`jobId` = the response id), so a resubmission never scores twice, and an
  assessment goes before a practice attempt (BullMQ `priority`);
* **events** (`publish` / `subscribe`) go to a Redis Stream per topic. Each
  subscribing service is a consumer group, so each gets its own copy, and a
  message is acknowledged once handled;
* **request-reply** (`call` / `serve`), a lesson step measured while the learner
  waits: the request is pushed on a list with a deadline, the server pushes the
  answer on a key of its own, and the caller waits on that key with a timeout.

BullMQ's Python client is asyncio; one event loop runs on a thread of the bus
and every BullMQ object lives on it. Handlers are plain functions and run on
worker threads, so a recogniser holding the CPU never stalls the loop that
renews the job's lock. Payloads are JSON objects; nothing here carries audio.

`bullmq` (MIT) and `redis` (MIT) are the `services` extra.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from aicefr.platform.bus import BusTimeout, Handler, Responder

logger = logging.getLogger(__name__)

PREFIX = "aicefr"
# Work for one response is one job: a second send of the same response is dropped.
DEDUPLICATED = frozenset({"speech.score"})
ATTEMPTS = 3
BACKOFF_MS = 2_000
STREAM_MAXLEN = 10_000


def _libraries():
    try:
        import bullmq
        import redis
    except ImportError as e:  # pragma: no cover - depends on the install
        raise RuntimeError(
            "a Redis bus needs bullmq and redis: pip install 'aicefr[services]'"
        ) from e
    return bullmq, redis


class _Loop:
    """An asyncio loop on a thread of its own, for the BullMQ objects."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="bus-loop", daemon=True)
        self.thread.start()

    def run(self, coro: Coroutine, timeout: float | None = 30.0) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)


class RedisBus:
    durable = True

    def __init__(self, url: str) -> None:
        bullmq, redis = _libraries()
        self.url = url
        self._bullmq = bullmq
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._loop: _Loop | None = None
        self._queues: dict[str, Any] = {}
        self._workers: list[Any] = []
        self._consumers: list[tuple[str, Handler, int]] = []
        self._subscribers: list[tuple[str, str, Handler]] = []
        self._responders: list[tuple[str, Responder, int]] = []
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ the loop

    def _ensure_loop(self) -> _Loop:
        with self._lock:
            if self._loop is None:
                self._loop = _Loop()
            return self._loop

    def _connection(self) -> dict:
        return {"connection": self.url, "prefix": PREFIX}

    def _queue(self, name: str):
        """The BullMQ queue `name`, made on the loop the first time."""
        loop = self._ensure_loop()
        with self._lock:
            queue = self._queues.get(name)
        if queue is None:

            async def make():
                return self._bullmq.Queue(name, self._connection())

            queue = loop.run(make())
            with self._lock:
                queue = self._queues.setdefault(name, queue)
        return queue

    # ------------------------------------------------------------ work

    def send(self, queue: str, payload: dict) -> None:
        opts: dict = {
            "attempts": ATTEMPTS,
            "backoff": {"type": "exponential", "delay": BACKOFF_MS},
            "removeOnComplete": 1_000,
            "removeOnFail": 5_000,
        }
        if queue in DEDUPLICATED and payload.get("response_id"):
            opts["jobId"] = str(payload["response_id"])
        if isinstance(payload.get("priority"), int):
            opts["priority"] = payload["priority"]
        q = self._queue(queue)
        self._ensure_loop().run(q.add(queue, payload, opts))

    def consume(self, queue: str, handler: Handler, prefetch: int = 1) -> None:
        self._consumers.append((queue, handler, max(1, prefetch)))

    def _start_worker(self, name: str, handler: Handler, concurrency: int) -> None:
        loop = self._ensure_loop()

        async def process(job, _token):
            # On a worker thread: the loop keeps renewing the job's lock meanwhile.
            try:
                await asyncio.to_thread(handler, dict(job.data))
            except Exception:
                logger.exception("handler for %s failed (attempt %s)", name, job.attemptsMade + 1)
                raise  # BullMQ retries it, then keeps it among the failed

        async def make():
            return self._bullmq.Worker(
                name, process, {**self._connection(), "concurrency": concurrency}
            )

        self._workers.append(loop.run(make()))

    # ------------------------------------------------------------ events

    def _stream(self, topic: str) -> str:
        return f"{PREFIX}:events:{topic}"

    def publish(self, topic: str, payload: dict) -> None:
        self._redis.xadd(
            self._stream(topic),
            {"payload": json.dumps(payload, ensure_ascii=False)},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )

    def subscribe(self, topic: str, group: str, handler: Handler) -> None:
        self._subscribers.append((topic, group, handler))

    def _read_events(self, topic: str, group: str, handler: Handler) -> None:
        stream = self._stream(topic)
        consumer = f"{group}-{uuid.uuid4().hex[:8]}"
        try:
            # "$": a service that subscribes for the first time starts from now,
            # not from the whole history of the topic.
            self._redis.xgroup_create(stream, group, id="$", mkstream=True)
        except Exception as e:  # noqa: BLE001 - BUSYGROUP: the group exists already
            if "BUSYGROUP" not in str(e):
                raise
        while not self._stop.is_set():
            try:
                batches = self._redis.xreadgroup(
                    group, consumer, {stream: ">"}, count=10, block=1_000
                )
            except Exception:  # noqa: BLE001 - a reader thread must not die
                logger.exception("reading %s failed; retrying in 3 s", stream)
                time.sleep(3)
                continue
            for _stream, messages in batches or []:
                for message_id, fields in messages:
                    try:
                        handler(json.loads(fields["payload"]))
                    except Exception:  # noqa: BLE001 - a subscriber's failure is its own
                        logger.exception("subscriber %s of %s failed", group, topic)
                    self._redis.xack(stream, group, message_id)

    # ------------------------------------------------------------ request-reply

    def _requests(self, queue: str) -> str:
        return f"{PREFIX}:rpc:{queue}"

    def call(self, queue: str, payload: dict, timeout: float = 120.0) -> dict:
        request_id = uuid.uuid4().hex
        reply_key = f"{PREFIX}:rpc:reply:{request_id}"
        self._redis.lpush(
            self._requests(queue),
            json.dumps(
                {"id": request_id, "deadline": time.time() + timeout, "payload": payload},
                ensure_ascii=False,
            ),
        )
        answer = self._redis.blpop([reply_key], timeout=max(1, int(round(timeout))))
        if answer is None:
            raise BusTimeout(f"{queue} did not answer within {timeout:.0f} s")
        return json.loads(answer[1])

    def serve(self, queue: str, responder: Responder, prefetch: int = 1) -> None:
        self._responders.append((queue, responder, max(1, prefetch)))

    def _answer(self, queue: str, responder: Responder) -> None:
        requests = self._requests(queue)
        while not self._stop.is_set():
            try:
                item = self._redis.brpop([requests], timeout=1)
            except Exception:  # noqa: BLE001 - a server thread must not die
                logger.exception("reading %s failed; retrying in 3 s", requests)
                time.sleep(3)
                continue
            if item is None:
                continue
            request = json.loads(item[1])
            if request["deadline"] < time.time():
                continue  # its caller gave up already
            try:
                result = responder(request["payload"])
            except Exception as e:  # noqa: BLE001 - the caller gets an answer now, not at its timeout
                logger.exception("responder for %s failed", queue)
                result = {"error": "internal", "detail": type(e).__name__}
            reply_key = f"{PREFIX}:rpc:reply:{request['id']}"
            self._redis.rpush(reply_key, json.dumps(result, ensure_ascii=False))
            self._redis.expire(reply_key, 60)

    # ------------------------------------------------------------ running

    def _thread(self, target: Callable, *args, name: str) -> None:
        t = threading.Thread(target=target, args=args, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def start(self) -> None:
        for name, handler, concurrency in self._consumers:
            self._start_worker(name, handler, concurrency)
        for topic, group, handler in self._subscribers:
            self._thread(self._read_events, topic, group, handler, name=f"events-{topic}")
        for queue, responder, threads in self._responders:
            for i in range(threads):
                self._thread(self._answer, queue, responder, name=f"rpc-{queue}-{i}")

    def run_forever(self) -> None:
        """For a worker process: consume until stopped."""
        self.start()
        while not self._stop.wait(1.0):
            pass

    def close(self) -> None:
        self._stop.set()
        if self._loop is None:
            return
        for worker in self._workers:
            try:
                self._loop.run(worker.close(), timeout=10)
            except Exception:  # noqa: BLE001 - closing what is closing anyway
                logger.debug("closing a worker failed", exc_info=True)
        for queue in list(self._queues.values()):
            try:
                self._loop.run(queue.close(), timeout=10)
            except Exception:  # noqa: BLE001
                logger.debug("closing a queue failed", exc_info=True)
        self._loop.stop()
