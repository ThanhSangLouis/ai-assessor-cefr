"""Structured logging with a request id, and counters for the metrics endpoint.

Two things a running system needs that a development one never misses:

1. **A request id on every line.** When a student reports "my submission
   failed at about 10am", the only way to find what happened is to pull every
   line belonging to that one request. Free-text logs without a correlation id
   make that impossible once there is more than one user.

2. **Logs that a machine can read.** JSON lines go straight into any log
   aggregator. Human-readable prose does not.

Privacy is not an afterthought here. This system handles voice recordings and
transcripts of identifiable people. NFR-09 forbids personal data in logs, so the
formatter redacts rather than trusting every call site to remember.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import time
import uuid
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Redaction patterns. Deliberately blunt: a false positive costs a masked log
# line, a false negative costs personal data sitting in a log file forever.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_LONG_DIGITS = re.compile(r"\b\d{7,12}\b")


def redact(text: str) -> str:
    """Mask anything that looks like an email address or a student number."""
    text = _EMAIL.sub("[email]", text)
    return _LONG_DIGITS.sub("[digits]", text)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the request id folded in."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "message": redact(record.getMessage()),
        }
        for key in ("method", "path", "status", "duration_ms", "event", "response_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Install the formatter on the root logger.

    Uvicorn installs its own handlers; replacing the root handler and letting
    its loggers propagate keeps every line in one format instead of two.
    """
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_output
        else logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


# --- counters ------------------------------------------------------------
# In-process counters and histograms, exposed in Prometheus text format and
# scraped by Prometheus (D051, docker-compose.observability.yml). Labels carry
# only bounded, non-personal values: a stage, a queue, a status, a route
# template -- never an account, a response id or a transcript.

Labels = tuple[tuple[str, str], ...]

_counters: Counter[tuple[str, Labels]] = Counter()
_histograms: dict[tuple[str, Labels], list[float]] = {}
_lock = threading.Lock()
_started_at = time.time()

# Seconds: a request, a pipeline stage, a recogniser call, a job in a queue.
BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)


def _labels(labels: dict[str, object]) -> Labels:
    return tuple(sorted((k, str(v)) for k, v in labels.items()))


def count(name: str, value: int = 1, **labels: object) -> None:
    with _lock:
        _counters[(name, _labels(labels))] += value


def observe(name: str, seconds: float, **labels: object) -> None:
    """One observation of a duration, into a histogram with fixed buckets."""
    key = (name, _labels(labels))
    with _lock:
        cells = _histograms.setdefault(key, [0.0] * (len(BUCKETS) + 2))
        for i, bound in enumerate(BUCKETS):
            if seconds <= bound:
                cells[i] += 1
        cells[-2] += seconds  # sum
        cells[-1] += 1  # count


@contextmanager
def timed(name: str, **labels: object) -> Iterator[None]:
    """Observe how long the block took, whether it returned or raised."""
    start = time.perf_counter()
    try:
        yield
    finally:
        observe(name, time.perf_counter() - start, **labels)


def _render_labels(labels: Labels, extra: tuple[str, str] | None = None) -> str:
    pairs = [*labels, *([extra] if extra else [])]
    if not pairs:
        return ""
    inner = ",".join(
        f'{k}="{v.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for k, v in pairs
    )
    return "{" + inner + "}"


def render_metrics() -> str:
    lines = [
        "# HELP aicefr_uptime_seconds Seconds since this process started.",
        "# TYPE aicefr_uptime_seconds gauge",
        f"aicefr_uptime_seconds {time.time() - _started_at:.0f}",
    ]
    with _lock:
        counters = dict(_counters)
        histograms = {k: list(v) for k, v in _histograms.items()}
    typed: set[str] = set()
    for (name, labels), value in sorted(counters.items()):
        metric = f"aicefr_{name}"
        if metric not in typed:
            lines.append(f"# TYPE {metric} counter")
            typed.add(metric)
        lines.append(f"{metric}{_render_labels(labels)} {value}")
    for (name, labels), cells in sorted(histograms.items()):
        metric = f"aicefr_{name}"
        if metric not in typed:
            lines.append(f"# TYPE {metric} histogram")
            typed.add(metric)
        for bound, n in zip(BUCKETS, cells, strict=False):
            lines.append(f"{metric}_bucket{_render_labels(labels, ('le', str(bound)))} {n:.0f}")
        lines.append(f"{metric}_bucket{_render_labels(labels, ('le', '+Inf'))} {cells[-1]:.0f}")
        lines.append(f"{metric}_sum{_render_labels(labels)} {cells[-2]:.6f}")
        lines.append(f"{metric}_count{_render_labels(labels)} {cells[-1]:.0f}")
    return "\n".join(lines) + "\n"
