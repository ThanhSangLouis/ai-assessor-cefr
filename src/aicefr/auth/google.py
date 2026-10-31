"""Sign in with Google (D029): OpenID Connect, authorisation code flow with PKCE.

What this module does NOT do is as important as what it does:

* **The email is the account (D071).** Google says who the person is with a
  stable subject identifier (`sub`), kept only as a one-way hash
  (`subject_hash`), and with an email it has verified. That email is the same
  sign-in email a password account has, so signing in with Google opens the
  account with that address, or makes one (D063). The name Google gives fills
  an empty full name; the photo is never asked for.
* **It adds no dependency.** The ID token comes straight from Google's token
  endpoint over TLS in exchange for a code and the client secret; OpenID
  Connect Core 1.0 §3.1.3.7 allows TLS server validation to stand in for the
  token signature in exactly this case. The claims are still checked: issuer,
  audience, expiry, issue time and the nonce this browser was given.

Three random values protect the round trip: `state` (the callback belongs to a
flow this browser started), `nonce` (the token was minted for that flow) and
the PKCE verifier (the code can only be redeemed by whoever started the flow).
They travel in a short-lived HttpOnly cookie, never in a URL the server logs.

That cookie is signed (D036). A cookie can be written by more than this
server: a sibling subdomain can set one for the parent domain, a network on
plain HTTP can inject one. Unsigned, such a cookie could pair a person's own
session with a flow somebody else wrote -- a "link" flow naming their account
would link a stranger's Google account to their pseudonym. So the cookie
carries an HMAC-SHA256 under a key only this deployment holds, and a flow that
does not check out is refused before Google is asked anything.

The signature cannot stop a stranger planting a flow this server really did
sign -- one they started themselves -- to sign somebody in to the stranger's
own account. What stops that is the `__Host-` prefix, which no subdomain can
set: behind TLS the cookie always has it, and a deployment whose redirect
address is https but which has not said it runs behind TLS
(`AICEFR_HTTPS_ONLY`) does not start the round trip at all (`insecure`).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass

from aicefr.encoding import b64url_decode
from aicefr.encoding import b64url_encode as _b64

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
PROVIDER = "google"
SCOPE = "openid email profile"
COOKIE_NAME = "aicefr_oauth"
# Behind TLS: Secure, Path=/ and no Domain, so a subdomain cannot set it.
SECURE_COOKIE_NAME = "__Host-aicefr_oauth"
FLOW_SECONDS = 600
# Tolerance on token times, for a server clock a little off.
LEEWAY_S = 120


class GoogleError(Exception):
    """A sign-in that cannot go on. `code` picks the sentence the page shows."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


# What a person reads for each refusal. Fixed sentences, chosen by code: a page
# never echoes text that came back in a URL.
MESSAGES = {
    "not_configured": "Máy chủ chưa bật đăng nhập bằng Google.",
    "cancelled": "Bạn đã huỷ đăng nhập bằng Google.",
    "state": "Phiên đăng nhập Google đã hết hạn hoặc không khớp. Hãy thử lại.",
    "exchange": "Không đổi được mã đăng nhập với Google. Hãy thử lại sau.",
    "token": "Google trả về thông tin đăng nhập không hợp lệ.",
    "domain": "Tài khoản Google này không thuộc tên miền mà trường cho phép.",
    "unverified": "Email của tài khoản Google này chưa được xác minh.",
    "not_linked": (
        "Tài khoản Google này chưa liên kết với bút danh nào. Đăng nhập bằng bút danh và "
        "mật khẩu, rồi liên kết Google ở trang Tài khoản."
    ),
    "disabled": "Tài khoản này đã bị tắt. Hãy liên hệ quản trị viên.",
    "taken": "Tài khoản Google này đã liên kết với một bút danh khác.",
    "signin": "Cần đăng nhập bằng bút danh trước khi liên kết Google.",
    "insecure": (
        "Máy chủ chạy qua https nhưng chưa bật AICEFR_HTTPS_ONLY, nên chưa đăng nhập bằng "
        "Google được. Quản trị viên xem khung Đăng nhập bằng Google ở tab Cấu hình."
    ),
}


@dataclass(frozen=True)
class GoogleConfig:
    client_id: str
    client_secret: str
    # Restrict sign-in to one Google Workspace domain, e.g. "hcmute.edu.vn".
    allowed_domain: str | None = None


@dataclass(frozen=True)
class Flow:
    """One sign-in round trip, as carried by the cookie."""

    state: str
    nonce: str
    verifier: str
    mode: str  # "login" or "link"
    next: str
    account_id: str | None  # the account that started a "link"
    started: int


@dataclass(frozen=True)
class GoogleIdentity:
    subject_hash: str
    # D071: only an address Google marked verified; None otherwise.
    email: str | None
    name: str | None = None


def new_flow(mode: str, next_path: str, account_id: str | None = None) -> Flow:
    if mode not in ("login", "link"):
        raise ValueError(mode)
    return Flow(
        state=secrets.token_urlsafe(24),
        nonce=secrets.token_urlsafe(24),
        verifier=secrets.token_urlsafe(48),
        mode=mode,
        next=safe_next(next_path),
        account_id=account_id,
        started=int(time.time()),
    )


def safe_next(path: str | None) -> str:
    """A same-site path to return to, or an empty string."""
    if path and path.startswith("/") and not path.startswith("//") and "\\" not in path:
        return path
    return ""


def cookie_name(secure: bool) -> str:
    return SECURE_COOKIE_NAME if secure else COOKIE_NAME


def _mac(key: bytes, payload: str) -> str:
    return _b64(hmac.new(key, b"google-flow|" + payload.encode("ascii"), hashlib.sha256).digest())


def encode_flow(flow: Flow, key: bytes) -> str:
    """The cookie's value: the flow, then its signature under this deployment's key."""
    payload = _b64(json.dumps(asdict(flow), separators=(",", ":")).encode("utf-8"))
    return f"{payload}.{_mac(key, payload)}"


def decode_flow(value: str | None, key: bytes, now: float | None = None) -> Flow | None:
    """The flow from the cookie, or None if missing, unsigned, altered, malformed or stale.

    Stale is older than ten minutes. The signature is checked first: nothing
    in a cookie this server did not write is read at all.
    """
    if not value or not value.isascii():
        return None
    payload, _, signature = value.rpartition(".")
    if not payload or not hmac.compare_digest(_mac(key, payload), signature):
        return None
    try:
        raw = b64url_decode(payload)
        flow = Flow(**json.loads(raw))
    except (ValueError, TypeError):
        return None
    if (now or time.time()) - flow.started > FLOW_SECONDS:
        return None
    return flow


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64(digest)


def authorization_url(config: GoogleConfig, flow: Flow, redirect_uri: str) -> str:
    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "state": flow.state,
        "nonce": flow.nonce,
        "code_challenge": _challenge(flow.verifier),
        "code_challenge_method": "S256",
        # Ask every time which Google account to use: on a shared lab computer
        # the account already signed in to the browser is often somebody else's.
        "prompt": "select_account",
    }
    if config.allowed_domain:
        params["hd"] = config.allowed_domain
    return f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, fields: dict[str, str]) -> dict:
    body = urllib.parse.urlencode(fields).encode("ascii")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # Only ever called with TOKEN_ENDPOINT, a fixed https URL.
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_code(
    config: GoogleConfig,
    code: str,
    flow: Flow,
    redirect_uri: str,
    post: Callable[[str, dict[str, str]], dict] | None = None,
) -> str:
    """Redeem the code at Google's token endpoint and return the ID token.

    `post` is looked up at call time, so a test can stand in for Google by
    replacing `_post_form` on this module.
    """
    try:
        reply = (post or _post_form)(
            TOKEN_ENDPOINT,
            {
                "code": code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": flow.verifier,
            },
        )
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        raise GoogleError("exchange", type(e).__name__) from e
    token = reply.get("id_token") if isinstance(reply, dict) else None
    if not token:
        raise GoogleError("exchange", "no id_token")
    return token


def _claims(id_token: str) -> dict:
    try:
        _header, payload, _signature = id_token.split(".")
        raw = b64url_decode(payload)
        claims = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise GoogleError("token", "malformed") from e
    if not isinstance(claims, dict):
        raise GoogleError("token", "not an object")
    return claims


def subject_hash(sub: str) -> str:
    """The only thing kept about a Google account: a one-way hash of its subject id."""
    return hashlib.sha256(f"{PROVIDER}|{sub}".encode()).hexdigest()


def verify_id_token(
    config: GoogleConfig, id_token: str, nonce: str, now: float | None = None
) -> GoogleIdentity:
    """Check the claims that matter and return who signed in, or raise GoogleError."""
    claims = _claims(id_token)
    now = now if now is not None else time.time()
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if claims.get("iss") not in ISSUERS:
        raise GoogleError("token", "issuer")
    if config.client_id not in audiences:
        raise GoogleError("token", "audience")
    if len(audiences) > 1 and claims.get("azp") != config.client_id:
        raise GoogleError("token", "authorized party")
    try:
        expires, issued = float(claims["exp"]), float(claims["iat"])
    except (KeyError, TypeError, ValueError) as e:
        raise GoogleError("token", "times") from e
    if expires < now - LEEWAY_S or issued > now + LEEWAY_S:
        raise GoogleError("token", "expired")
    if not secrets.compare_digest(str(claims.get("nonce", "")).encode(), nonce.encode()):
        raise GoogleError("token", "nonce")
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise GoogleError("token", "subject")
    verified = claims.get("email_verified") is True
    email = claims.get("email") if isinstance(claims.get("email"), str) and verified else None
    name = claims.get("name") if isinstance(claims.get("name"), str) else None
    if config.allowed_domain:
        if claims.get("hd") != config.allowed_domain:
            raise GoogleError("domain")
        if not verified:
            raise GoogleError("unverified")
    return GoogleIdentity(subject_hash=subject_hash(sub), email=email, name=name)
