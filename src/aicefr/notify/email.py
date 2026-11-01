"""Sending email (D079): Resend in production, an in-memory outbox elsewhere.

`AICEFR_EMAIL_PROVIDER` picks the sender: `resend` (needs `AICEFR_RESEND_API_KEY`
and a sender on a domain verified at Resend, `AICEFR_EMAIL_FROM`), `outbox`
(kept in memory, for tests and a machine without a key) or `off`. With no
sender nothing is sent and the pages say so; the recovery code (D065) still
works.

The message never carries a password, a session or anything but the code or
the reminder: a mailbox is read on many devices.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
TIMEOUT_S = 10


class EmailError(Exception):
    """The provider refused or did not answer; the caller says so, never pretends."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str
    html: str
    # Headers such as List-Unsubscribe for a reminder.
    headers: dict[str, str] = field(default_factory=dict)


class EmailSender(Protocol):
    name: str

    def send(self, email: Email) -> None: ...


class Outbox:
    """Keeps what would have been sent: tests read it, nothing leaves the machine."""

    name = "outbox"

    def __init__(self) -> None:
        self.sent: list[Email] = []

    def send(self, email: Email) -> None:
        self.sent.append(email)
        logger.info("email kept in the outbox for %s: %s", email.to, email.subject)


class ResendSender:
    name = "resend"

    def __init__(self, api_key: str, sender: str) -> None:
        self.api_key = api_key
        self.sender = sender

    def send(self, email: Email) -> None:
        body = {
            "from": self.sender,
            "to": [email.to],
            "subject": email.subject,
            "text": email.text,
            "html": email.html,
        }
        if email.headers:
            body["headers"] = email.headers
        request = urllib.request.Request(
            RESEND_URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "aicefr",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as r:  # noqa: S310 - fixed https host
                r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            raise EmailError(f"Resend trả lỗi {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise EmailError(f"không gọi được Resend: {e}") from e


_outbox = Outbox()


def sender_from(settings) -> EmailSender | None:
    """The sender the settings ask for, or None when email is off or not set up."""
    provider = settings.email_provider
    if provider == "outbox":
        return _outbox
    if provider == "resend":
        if not settings.resend_api_key or not settings.email_from:
            logger.warning("email: AICEFR_RESEND_API_KEY or AICEFR_EMAIL_FROM is missing")
            return None
        return ResendSender(settings.resend_api_key, settings.email_from)
    return None


def outbox() -> Outbox:
    """The shared outbox, for tests."""
    return _outbox
