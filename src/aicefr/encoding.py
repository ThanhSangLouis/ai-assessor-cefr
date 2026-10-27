"""Unpadded base64url (RFC 4648, section 5), as JWTs, PKCE and signed tokens use it."""

from __future__ import annotations

import base64


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """The bytes back; raises ValueError on text that is not base64url."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
