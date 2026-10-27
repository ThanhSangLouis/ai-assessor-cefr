"""Generating and hashing login session tokens. Implements part of FR-32 and NFR-07.

Decision QD-07: carry the session token in a cookie and look it up against the
server-side auth_sessions table instead of using JWT. Reason: a JWT cannot be
revoked before it expires, so logging out would not invalidate the token — and
this system has a teacher role that can change scores.

Only the HASH of the session token is stored in the database, never the token
itself. If a database copy leaks, whoever reads it still cannot impersonate any
session.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

COOKIE_NAME = "aicefr_session"
TOKEN_BYTES = 32
LIFETIME_HOURS = 8  # NFR-07: a session must expire after no more than 8 hours


def new_token() -> str:
    """A cryptographically secure random session token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Hash a session token. Uses SHA-256 rather than bcrypt.

    Unlike a password, a session token is already a 32-byte random string, so it
    cannot be guessed with a dictionary. A slow hash such as bcrypt here would
    only make every request heavier without adding any security.
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def new_expiry(hours: int = LIFETIME_HOURS) -> str:
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat(timespec="seconds")


def is_expired(cutoff: str) -> bool:
    try:
        return datetime.fromisoformat(cutoff) <= datetime.now(UTC)
    except ValueError:
        # A corrupted timestamp counts as expired. Never open the door because
        # of malformed data.
        return True


def device_label(user_agent: str | None) -> str | None:
    """A coarse name for the device a session was opened on, e.g. "Chrome · macOS".

    Kept coarse on purpose (D029): enough for a person to recognise "my phone"
    in their list of sessions, not a fingerprint. The full user-agent string is
    never stored.
    """
    if not user_agent:
        return None
    ua = user_agent.lower()
    if "edg/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "firefox/" in ua or "fxios" in ua:
        browser = "Firefox"
    elif "chrome/" in ua or "crios" in ua:
        browser = "Chrome"
    elif "safari/" in ua:
        browser = "Safari"
    else:
        browser = "Trình duyệt khác"
    if "iphone" in ua or "ipad" in ua:
        system = "iPhone/iPad"
    elif "android" in ua:
        system = "Android"
    elif "mac os x" in ua or "macintosh" in ua:
        system = "macOS"
    elif "windows" in ua:
        system = "Windows"
    elif "linux" in ua:
        system = "Linux"
    else:
        system = "hệ điều hành khác"
    return f"{browser} · {system}"
