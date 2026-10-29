"""The message bus between services: events, work queues and request-reply (D043).

Three ways one service hands something to another without calling it:

* **events** (`publish` / `subscribe`): "consent changed", "a response was
  scored". Every service that subscribed gets its own copy; the publisher does
  not know who listens.
* **work** (`send` / `consume`): a recording to score. Exactly one worker takes
  each message; with RabbitMQ the message waits in a durable queue until one
  does, so scoring survives a restart of either side.
* **request-reply** (`call` / `serve`): a lesson step to measure while the
  learner waits. The caller blocks for the answer, with a timeout.

Two adapters. `InlineBus` delivers in this process -- synchronously for events
and calls, through a `JobQueue` for work -- which is what the tests and a
single machine use. `RabbitBus` speaks AMQP 0-9-1 to RabbitMQ through `pika`
(the `services` extra): a durable topic exchange for events, durable queues for
work, and RabbitMQ's direct reply-to for calls. Handlers run on a thread of
their own and acknowledge only once done, so a crash mid-way hands the message
to the next worker rather than losing it.

Payloads are JSON objects. Nothing here carries audio: a recording goes into the
blob store and the message names its key.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections.abc import Callable
from typing import Protocol

from aicefr.ports import JobQueue

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]
Responder = Callable[[dict], dict]

EVENTS_EXCHANGE = "aicefr.events"


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


# ================================================================= RabbitMQ


def _pika():
    try:
        import pika
    except ImportError as e:  # pragma: no cover - depends on the install
        raise RuntimeError("a RabbitMQ bus needs pika: pip install 'aicefr[services]'") from e
    return pika


def _encode(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode()


class RabbitBus:
    """AMQP through pika. One connection per consumer thread, one per publishing thread.

    pika's blocking connection is not thread-safe, so nothing here shares one
    across threads: publishers keep a connection per thread, each consumer runs
    on a thread with its own, and a handler running on a worker thread hands its
    acknowledgement back to the connection's thread.
    """

    durable = True

    def __init__(self, url: str) -> None:
        self.url = url
        self._local = threading.local()
        # (name, declare the queue and return its name, handler, responder, prefetch)
        self._consumers: list[tuple[str, Callable, Handler | None, Responder | None, int]] = []
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    # ------------------------------------------------------------ connections

    def _connect(self):
        pika = _pika()
        params = pika.URLParameters(self.url)
        params.heartbeat = 60
        params.blocked_connection_timeout = 30
        return pika.BlockingConnection(params)

    def _channel(self):
        ch = getattr(self._local, "channel", None)
        if ch is None or ch.is_closed or ch.connection.is_closed:
            conn = self._connect()
            ch = conn.channel()
            # Publisher confirms: a publish returns only once the broker has the
            # message, and raises otherwise. Without them a publish written to a
            # connection the broker already dropped -- an idle publisher misses
            # its heartbeats -- is lost without a word.
            ch.confirm_delivery()
            ch.exchange_declare(EVENTS_EXCHANGE, exchange_type="topic", durable=True)
            self._local.channel = ch
        return ch

    def _publish(
        self, exchange: str, routing_key: str, body: bytes, declare: str | None = None
    ) -> None:
        """Publish, on a fresh connection once if the kept one turns out to be dead."""
        pika = _pika()
        properties = pika.BasicProperties(content_type="application/json", delivery_mode=2)
        for attempt in (1, 2):
            try:
                ch = self._channel()
                if declare:
                    ch.queue_declare(declare, durable=True)
                ch.basic_publish(exchange, routing_key, body, properties)
                return
            except pika.exceptions.AMQPError:
                self._local.channel = None
                if attempt == 2:
                    raise

    def _release_thread_connection(self) -> None:
        ch = getattr(self._local, "channel", None)
        self._local.channel = None
        if ch is not None and ch.connection.is_open:
            try:
                ch.connection.close()
            except Exception:  # noqa: BLE001 - closing is best effort
                logger.debug("could not close a publishing connection", exc_info=True)

    # ------------------------------------------------------------ the three patterns

    def publish(self, topic: str, payload: dict) -> None:
        self._publish(EVENTS_EXCHANGE, topic, _encode(payload))

    def subscribe(self, topic: str, group: str, handler: Handler) -> None:
        def declare(ch) -> str:
            queue = f"{group}.{topic}"
            ch.exchange_declare(EVENTS_EXCHANGE, exchange_type="topic", durable=True)
            ch.queue_declare(queue, durable=True)
            ch.queue_bind(queue, EVENTS_EXCHANGE, routing_key=topic)
            return queue

        self._consumers.append((topic, declare, handler, None, 1))

    def send(self, queue: str, payload: dict) -> None:
        self._publish("", queue, _encode(payload), declare=queue)

    def consume(self, queue: str, handler: Handler, prefetch: int = 1) -> None:
        """`prefetch`: how many messages of this queue are handled at once in this process."""

        def declare(ch) -> str:
            ch.queue_declare(queue, durable=True)
            return queue

        self._consumers.append((queue, declare, handler, None, prefetch))

    def serve(self, queue: str, responder: Responder, prefetch: int = 1) -> None:
        def declare(ch) -> str:
            ch.queue_declare(queue, durable=True)
            return queue

        self._consumers.append((queue, declare, None, responder, prefetch))

    def call(self, queue: str, payload: dict, timeout: float = 120.0) -> dict:
        """Request-reply over RabbitMQ's direct reply-to, on a connection of its own."""
        pika = _pika()
        conn = self._connect()
        try:
            ch = conn.channel()
            answer: dict = {}
            correlation = uuid.uuid4().hex

            def on_reply(_ch, _method, props, body) -> None:
                if props.correlation_id == correlation:
                    answer["body"] = json.loads(body)

            ch.basic_consume("amq.rabbitmq.reply-to", on_reply, auto_ack=True)
            ch.basic_publish(
                "",
                queue,
                _encode(payload),
                pika.BasicProperties(
                    content_type="application/json",
                    reply_to="amq.rabbitmq.reply-to",
                    correlation_id=correlation,
                    expiration=str(int(timeout * 1000)),
                ),
            )
            deadline = time.monotonic() + timeout
            while "body" not in answer:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise BusTimeout(f"{queue} did not answer within {timeout:.0f} s")
                conn.process_data_events(time_limit=min(left, 1.0))
            return answer["body"]
        finally:
            conn.close()

    # ------------------------------------------------------------ consuming

    def start(self) -> None:
        """One thread per consumer, each reconnecting on its own after a failure."""
        for name, *spec in self._consumers:
            t = threading.Thread(
                target=self._consume_forever, args=tuple(spec), name=f"bus-{name}", daemon=True
            )
            t.start()
            self._threads.append(t)

    def run_forever(self) -> None:
        """For a worker process: consume until stopped."""
        self.start()
        while not self._stop.wait(1.0):
            pass

    def close(self) -> None:
        self._stop.set()

    def _consume_forever(
        self,
        declare: Callable,
        handler: Handler | None,
        responder: Responder | None,
        prefetch: int,
    ) -> None:
        pika = _pika()
        while not self._stop.is_set():
            try:
                self._consume_once(declare, handler, responder, prefetch)
            except pika.exceptions.AMQPError as e:
                logger.warning("bus connection lost (%s); reconnecting in 3 s", e)
                time.sleep(3)
            except Exception:  # noqa: BLE001 - a consumer thread must not die
                logger.exception("bus consumer failed; restarting in 3 s")
                time.sleep(3)

    def _consume_once(
        self,
        declare: Callable,
        handler: Handler | None,
        responder: Responder | None,
        prefetch: int,
    ) -> None:
        pika = _pika()
        conn = self._connect()
        ch = conn.channel()
        ch.basic_qos(prefetch_count=prefetch)
        queue = declare(ch)

        def finish(tag: int, ok: bool, reply: tuple[str, str, bytes] | None) -> None:
            if reply is not None:
                to, correlation, body = reply
                ch.basic_publish(
                    "",
                    to,
                    body,
                    pika.BasicProperties(
                        content_type="application/json", correlation_id=correlation
                    ),
                )
            if ok:
                ch.basic_ack(tag)
            else:
                # Not requeued: a message that fails every time would loop for ever.
                ch.basic_nack(tag, requeue=False)

        def work(tag: int, props, body: bytes) -> None:
            ok, reply = True, None
            try:
                payload = json.loads(body)
                if responder is not None:
                    result = responder(payload)
                    if props.reply_to:
                        reply = (props.reply_to, props.correlation_id, _encode(result))
                else:
                    handler(payload)
            except Exception as e:  # noqa: BLE001 - logged, and the message is dead-lettered
                logger.exception("handler for %s failed", queue)
                ok = False
                # A caller waiting for an answer gets one now, not at its timeout.
                if responder is not None and props.reply_to:
                    failure = {"error": "internal", "detail": type(e).__name__}
                    reply = (props.reply_to, props.correlation_id, _encode(failure))
            finally:
                # The handler may have published (a worker's report), opening a
                # connection for this thread; the thread ends here, so must it.
                self._release_thread_connection()
            conn.add_callback_threadsafe(lambda: finish(tag, ok, reply))

        def on_message(_ch, method, props, body) -> None:
            threading.Thread(
                target=work, args=(method.delivery_tag, props, body), daemon=True
            ).start()

        ch.basic_consume(queue, on_message)
        try:
            while not self._stop.is_set():
                conn.process_data_events(time_limit=1.0)
        finally:
            if conn.is_open:
                conn.close()


def bus_from_url(url: str, jobs: JobQueue) -> MessageBus:
    """`inline` for this process, an `amqp://` URL for RabbitMQ."""
    if url.startswith(("amqp://", "amqps://")):
        return RabbitBus(url)
    return InlineBus(jobs)
