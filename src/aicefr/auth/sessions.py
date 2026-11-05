"""Login sessions as signed JSON Web Tokens. Implements part of FR-32 and NFR-07.

D091 (replaces QD-07): the session cookie carries a JWT (HS256) signed with a
key this deployment keeps (`AuthRepository.secret`). The token names the
account (`sub`), the session (`sid`) and when it ends (`exp`). A signature or
expiry that does not hold is refused before the database is asked anything.

A JWT alone cannot be revoked before it expires, and BR-09 needs logging out,
changing a password or disabling an account to end a session at once. So the
session row stays: a token is honoured only while the row of its `sid` exists.

Only the HASH of the `sid` is stored in the database, never the token or the
`sid` itself. If a database copy leaks, whoever reads it still cannot
impersonate any session, and without the key nobody can mint a token.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

COOKIE_NAME = "aicefr_session"
TOKEN_BYTES = 32
LIFETIME_HOURS = 8  # NFR-07: a session must expire after no more than 8 hours
# The only header this system issues or accepts. Comparing the whole header
# rules out "alg": "none" and every other algorithm in one place.
_HEADER = {"alg": "HS256", "typ": "JWT"}


def new_token() -> str:
    """A cryptographically secure random session id (the JWT's `sid`)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Hash a session id. Uses SHA-256 rather than bcrypt.

    Unlike a password, a session id is already a 32-byte random string, so it
    cannot be guessed with a dictionary. A slow hash such as bcrypt here would
    only make every request heavier without adding any security.
    """
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _part(value: dict) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _sign(key: bytes, signing_input: str) -> str:
    return _b64(hmac.new(key, signing_input.encode("ascii"), hashlib.sha256).digest())


def encode_jwt(key: bytes, account_id: str, sid: str, expires_at: str) -> str:
    """The cookie's value: a JWT for session `sid` of `account_id`, ending at `expires_at`."""
    claims = {
        "sub": account_id,
        "sid": sid,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(datetime.fromisoformat(expires_at).timestamp()),
    }
    signing_input = f"{_part(_HEADER)}.{_part(claims)}"
    return f"{signing_input}.{_sign(key, signing_input)}"


def decode_jwt(key: bytes, token: str | None) -> dict | None:
    """The claims of a token this deployment signed and that has not expired, else None."""
    try:
        header, payload, signature = (token or "").split(".")
        if not hmac.compare_digest(signature, _sign(key, f"{header}.{payload}")):
            return None
        if json.loads(_unb64(header)) != _HEADER:
            return None
        claims = json.loads(_unb64(payload))
        if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("sid"), str):
            return None
        if int(claims["exp"]) <= datetime.now(UTC).timestamp():
            return None
    except (ValueError, KeyError, TypeError, AttributeError):
        # Malformed in any way counts as no session. Never open the door
        # because of malformed data.
        return None
    return claims


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
