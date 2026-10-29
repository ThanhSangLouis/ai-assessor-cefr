"""Adapters for `RateLimiter`. In-memory today, shared later.

The in-memory counter is not only a scaling limit, it is a correctness one:
with several instances behind a load balancer, "ten per minute" silently becomes
"ten per minute per instance", so the protection weakens exactly as the
deployment grows. Behind the port, swapping in a shared counter is one adapter.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowCounter:
    """So lan thu trong 60 giay gan nhat theo tung khoa, bo nho CO TRAN.

    Truoc day la mot `defaultdict` khong gioi han: moi dia chi gia la mot khoa
    moi, nen ke tan cong doi IP lien tuc lam bo nho phinh mai. Vuot `max_keys`
    thi bo khoa het han truoc, roi bo khoa cu nhat.
    """

    def __init__(self, window_s: float = 60.0, max_keys: int = 10_000) -> None:
        self.window_s = window_s
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float, limit: int) -> bool:
        hits = self._hits.get(key)
        if hits is None:
            self._make_room(now)
            hits = self._hits[key] = deque()
        while hits and now - hits[0] > self.window_s:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def _make_room(self, now: float) -> None:
        if len(self._hits) < self.max_keys:
            return
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] > self.window_s]:
            del self._hits[key]
        while len(self._hits) >= self.max_keys:
            del self._hits[next(iter(self._hits))]

    def forget(self, key: str) -> None:
        self._hits.pop(key, None)

    def __len__(self) -> int:
        return len(self._hits)


class InMemoryRateLimiter:
    """Sliding window per key, held in this process, with a memory ceiling."""

    name = "in-memory"

    def __init__(self) -> None:
        self._windows: dict[int, SlidingWindowCounter] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        with self._lock:
            window = self._windows.get(window_seconds)
            if window is None:
                window = self._windows[window_seconds] = SlidingWindowCounter(window_seconds)
            return window.allow(key, time.time(), limit)

    def forget(self, key: str) -> None:
        with self._lock:
            for window in self._windows.values():
                window.forget(key)
