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
import time
import uuid
from collections import Counter
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
# A tiny in-process counter set, exposed in Prometheus text format. Not a
# replacement for a real metrics backend, but enough to answer "is anything
# being submitted, and is anything failing?" without reading logs.

_counters: Counter[str] = Counter()
_started_at = time.time()


def count(name: str, value: int = 1) -> None:
    _counters[name] += value


def render_metrics() -> str:
    lines = [
        "# HELP aicefr_uptime_seconds Seconds since this process started.",
        "# TYPE aicefr_uptime_seconds gauge",
        f"aicefr_uptime_seconds {time.time() - _started_at:.0f}",
    ]
    for key in sorted(_counters):
        metric = f"aicefr_{key}"
        lines += [f"# TYPE {metric} counter", f"{metric} {_counters[key]}"]
    return "\n".join(lines) + "\n"
