"""Adapters for `RateLimiter`. In-memory today, shared later.

The in-memory counter is not only a scaling limit, it is a correctness one:
with several instances behind a load balancer, "ten per minute" silently becomes
"ten per minute per instance", so the protection weakens exactly as the
deployment grows. Behind the port, swapping in a shared counter is one adapter.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Sliding window per key, held in this process."""

    name = "in-memory"

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def forget(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
