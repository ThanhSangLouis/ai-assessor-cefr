"""Adapters for `JobQueue`. In-process today, a broker later.

`InProcessJobQueue` owns its own worker pool rather than borrowing the request's
background tasks. That is a deliberate shape choice: a real broker accepts work
and forgets the caller, so the in-process adapter behaves the same way. Swapping
one for the other then changes no calling code.

What this adapter cannot do, and what a broker would give:

  * survive a restart -- queued work dies with the process
  * be picked up by another instance
  * retry, or record why something failed for good
  * be observed from outside the process

Those four are the reasons to move, and the reason this interface exists now
rather than after the move becomes urgent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class InProcessJobQueue:
    """Runs jobs on a bounded worker pool inside this process.

    The bound matters more than it looks. Each job may hold a speech model in
    memory; run forty at once and the machine swaps, the pool starves, and every
    other endpoint -- login included -- stops answering. One student with a loop
    can cause that by accident.
    """

    name = "in-process"

    def __init__(self, max_concurrent: int = 2) -> None:
        self.max_concurrent = max_concurrent
        self._pool = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="aicefr-job")

    def enqueue(self, func: Callable, /, *args, **kwargs) -> None:
        self._pool.submit(self._guarded, func, *args, **kwargs)

    def _guarded(self, func: Callable, *args, **kwargs) -> None:
        try:
            func(*args, **kwargs)
        except BaseException:
            # Nothing may escape a background job. An escaped exception leaves
            # the work silently unfinished and the submitter waiting for ever.
            logger.exception("background job %s failed", getattr(func, "__name__", func))


class InlineJobQueue:
    """Runs the job immediately, on the calling thread.

    For tests, and for any deployment that genuinely wants synchronous
    behaviour. Having it as a separate adapter rather than a flag inside the
    other one keeps the test path and the production path honestly different:
    a test that passes here proves the job logic works, not that the queue does.
    """

    name = "inline"

    def enqueue(self, func: Callable, /, *args, **kwargs) -> None:
        try:
            func(*args, **kwargs)
        except BaseException:
            logger.exception("inline job %s failed", getattr(func, "__name__", func))
