"""Live events to the browser over Server-Sent Events (D086).

A page that waits for something -- a response being scored, a queue a teacher
works through -- used to ask the server again and again. The core service now
tells the browser when that something happened, on one long-lived response per
open tab (`GET /api/v1/me/events`, `text/event-stream`).

Three pieces:

* `LiveEvent`: what happened (`kind`, a small `data` object) and who should
  hear of it -- some accounts by id, and every connection of some roles. It
  never carries a score or a name: a page that hears of an event asks the
  usual API, which applies the usual access rules (D071);
* `LiveHub`: the connections open in this process, each with its own bounded
  queue. `deliver` may be called from any thread (a bus consumer, a sync
  route); it hands the frame to the connection's event loop;
* a channel that carries an event to every process holding connections:
  `InlineLive` in one process, `RedisLive` through Redis pub/sub when the bus
  is Redis (D050), so a second core instance hears what the first one saw.

Everything here is best-effort. Pub/sub keeps nothing for a subscriber that is
not listening, a full queue drops the frame, and `notify` never raises: every
page that listens keeps working as before when no event comes (it still asks
the server, only less often).
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

# SEC-05: asks whether the session behind a stream still holds; returns None
# while it does, else why not (`session_revoked`, `account_disabled`, ...).
SessionCheck = Callable[[], str | None]

CHANNEL = "aicefr:live"
# How long a browser waits before reconnecting after the stream ends.
RETRY_MS = 5_000
# Frames waiting for one slow connection; past that they are dropped.
QUEUE_SIZE = 64
# Tabs one account may hold open at once; one more is refused with 429.
MAX_PER_ACCOUNT = 8


@dataclass(frozen=True)
class LiveEvent:
    kind: str
    data: dict = field(default_factory=dict)
    accounts: frozenset[str] = frozenset()
    roles: frozenset[str] = frozenset()

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "data": self.data,
                "accounts": sorted(self.accounts),
                "roles": sorted(self.roles),
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> LiveEvent:
        d = json.loads(text)
        return cls(
            kind=d["kind"],
            data=d.get("data") or {},
            accounts=frozenset(d.get("accounts") or ()),
            roles=frozenset(d.get("roles") or ()),
        )

    def frame(self) -> str:
        """The event as the browser's EventSource reads it."""
        return f"event: {self.kind}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


class TooManyConnections(Exception):
    """The account holds MAX_PER_ACCOUNT streams already."""


@dataclass(eq=False)
class Subscription:
    account_id: str
    role: str
    queue: asyncio.Queue  # frames, or None once the stream must end
    loop: asyncio.AbstractEventLoop

    def offer(self, frame: str) -> None:
        """On the subscription's loop: queue the frame, or drop it when full."""
        try:
            self.queue.put_nowait(frame)
        except asyncio.QueueFull:
            logger.debug("live queue of %s full; frame dropped", self.account_id)

    def end(self) -> None:
        """On the subscription's loop: end the stream, even past a full queue."""
        while True:
            try:
                self.queue.put_nowait(None)
                return
            except asyncio.QueueFull:
                self.queue.get_nowait()


class LiveHub:
    """The streams open in this process."""

    def __init__(self, max_per_account: int = MAX_PER_ACCOUNT) -> None:
        self.max_per_account = max_per_account
        self._subs: list[Subscription] = []
        self._lock = threading.Lock()

    def open(self, account_id: str, role: str) -> Subscription:
        """A stream for this account; called on the event loop that will read it."""
        sub = Subscription(account_id, role, asyncio.Queue(QUEUE_SIZE), asyncio.get_running_loop())
        with self._lock:
            held = sum(1 for s in self._subs if s.account_id == account_id)
            if held >= self.max_per_account:
                raise TooManyConnections(account_id)
            self._subs.append(sub)
        return sub

    def close(self, sub: Subscription) -> None:
        with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    def count(self, account_id: str | None = None) -> int:
        with self._lock:
            return sum(1 for s in self._subs if account_id in (None, s.account_id))

    def deliver(self, event: LiveEvent) -> int:
        """Hand the event to every stream it is for; returns how many. Any thread."""
        with self._lock:
            targets = [
                s for s in self._subs if s.account_id in event.accounts or s.role in event.roles
            ]
        frame = event.frame()
        for sub in targets:
            try:
                sub.loop.call_soon_threadsafe(sub.offer, frame)
            except RuntimeError:  # the loop is closed: the stream is going away
                self.close(sub)
        return len(targets)

    def end_all(self) -> None:
        """End every stream of this process (the process is stopping). Any thread."""
        with self._lock:
            subs = list(self._subs)
        for sub in subs:
            try:
                sub.loop.call_soon_threadsafe(sub.end)
            except RuntimeError:
                self.close(sub)


def end_streams_on_sigterm(hub: LiveHub) -> None:
    """End the streams as soon as the process is asked to stop.

    uvicorn waits for open responses before it stops, and a stream does not end
    by itself for minutes: without this, every deploy would wait out
    `--timeout-graceful-shutdown` and then cancel the streams with an error in
    the log. Ended here, each stream finishes cleanly and the browser reconnects
    to the new container. Chains to the handler already installed (uvicorn's);
    only the main thread may install one, so tests and the one-process app
    skip it.
    """
    if threading.current_thread() is not threading.main_thread():
        return
    previous = signal.getsignal(signal.SIGTERM)

    def on_term(signum, frame) -> None:
        hub.end_all()
        if callable(previous):
            previous(signum, frame)
        elif previous in (signal.SIG_DFL, None):
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.raise_signal(signal.SIGTERM)

    signal.signal(signal.SIGTERM, on_term)


async def _session_ended(check: SessionCheck, session_id: str) -> str | None:
    """Why the stream's session no longer holds, or None while it does.

    Run off the loop: the check reads the session store. A check that fails is
    an ended session -- the browser reconnects and is checked again at the door.
    """
    try:
        reason = await asyncio.to_thread(check)
    except Exception:  # noqa: BLE001 - see the docstring
        logger.warning("live session check failed", exc_info=True)
        reason = "check_failed"
    if reason:
        logger.info("session.stream_closed reason=%s session=%s", reason, session_id or "-")
    return reason


async def stream(
    hub: LiveHub,
    sub: Subscription,
    *,
    heartbeat_s: float,
    lifetime_s: float,
    check: SessionCheck | None = None,
    recheck_s: float = 30.0,
    session_id: str = "",
) -> AsyncIterator[str]:
    """The frames of one open stream, until the browser leaves or `lifetime_s` passes.

    The stream ends on purpose after `lifetime_s`: the browser reconnects on its
    own, through the gateway, so a session ended meanwhile stops receiving. A
    comment line every `heartbeat_s` keeps proxies from closing an idle
    connection.

    SEC-05: with a `check`, the stream also asks every `recheck_s`, and before
    each event, whether the session that opened it still holds; when it does
    not, the stream ends there and the event is not sent. `session_id` names
    the session in the log only (a prefix of the token's hash, never the token).
    """
    loop = asyncio.get_running_loop()
    now = loop.time()
    deadline = now + lifetime_s
    next_ping = now + heartbeat_s
    next_check = now + recheck_s if check is not None else float("inf")
    try:
        yield f"retry: {RETRY_MS}\nevent: ready\ndata: {{}}\n\n"
        while (left := deadline - (now := loop.time())) > 0:
            wait = max(0.0, min(left, next_ping - now, next_check - now))
            try:
                frame = await asyncio.wait_for(sub.queue.get(), timeout=wait)
            except TimeoutError:
                frame = ""
            if frame is None:  # `end`: the process is stopping
                return
            now = loop.time()
            if check is not None and (frame or now >= next_check):
                if await _session_ended(check, session_id):
                    return
                next_check = loop.time() + recheck_s
            if frame:
                yield frame
                next_ping = loop.time() + heartbeat_s
            elif now >= next_ping:
                yield ": ping\n\n"
                next_ping = loop.time() + heartbeat_s
    finally:
        hub.close(sub)


# ================================================================= channels


class LiveChannel(Protocol):
    def publish(self, event: LiveEvent) -> None: ...

    def start(self) -> None: ...

    def close(self) -> None: ...


class InlineLive:
    """Every connection is in this process."""

    def __init__(self, hub: LiveHub) -> None:
        self.hub = hub

    def publish(self, event: LiveEvent) -> None:
        self.hub.deliver(event)

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass


class RedisLive:
    """Redis pub/sub: every process publishes, and delivers what any process published."""

    def __init__(self, url: str, hub: LiveHub) -> None:
        import redis

        self.hub = hub
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def publish(self, event: LiveEvent) -> None:
        self._redis.publish(CHANNEL, event.to_json())

    def _listen(self) -> None:
        while not self._stop.is_set():
            pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            try:
                pubsub.subscribe(CHANNEL)
                while not self._stop.is_set():
                    message = pubsub.get_message(timeout=1.0)
                    if message and message.get("type") == "message":
                        try:
                            self.hub.deliver(LiveEvent.from_json(message["data"]))
                        except Exception:  # noqa: BLE001 - one bad message, not the listener
                            logger.exception("could not deliver a live event")
            except Exception:  # noqa: BLE001 - the listener must not die; Redis may come back
                logger.exception("live listener lost Redis; retrying in 3 s")
                self._stop.wait(3.0)
            finally:
                try:
                    pubsub.close()
                except Exception:  # noqa: BLE001
                    logger.debug("closing the live pubsub failed", exc_info=True)

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._listen, name="live-listener", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()


def live_from_url(url: str, hub: LiveHub) -> LiveChannel:
    """Redis pub/sub beside a Redis bus (D050); this process otherwise."""
    if url.startswith(("redis://", "rediss://")):
        return RedisLive(url, hub)
    return InlineLive(hub)


class Live:
    """What the routes use: the hub of this process and the channel to all of them."""

    def __init__(self, hub: LiveHub, channel: LiveChannel) -> None:
        self.hub = hub
        self.channel = channel

    def notify(
        self,
        kind: str,
        data: dict | None = None,
        *,
        accounts: Iterable[str | None] = (),
        roles: Iterable[str] = (),
    ) -> None:
        """Publish one event; never raises -- the action that caused it is already done."""
        event = LiveEvent(
            kind,
            data or {},
            frozenset(a for a in accounts if a),
            frozenset(roles),
        )
        if not event.accounts and not event.roles:
            return
        try:
            self.channel.publish(event)
        except Exception:  # noqa: BLE001 - see the docstring
            logger.exception("could not publish live event %s", kind)
