"""Google OIDC authorization-code/PKCE service for already-provisioned accounts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import time
import urllib.parse
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from aicefr.auth.errors import LockoutError
from aicefr.auth.google_transport import (
    JWKS_URL,
    TOKEN_URL,
    GoogleHttpsTransport,
    JsonTransport,
)
from aicefr.storage.google_identity import GoogleIdentityRepository, google_subject_hash
from aicefr.storage.paths import external_data_dir

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
FLOW_TTL = timedelta(minutes=10)
MAX_FLOW_COOKIE = 4096
MAX_JWT_BYTES = 16_384
MAX_PROVIDER_CODE = 4096
MAX_CLOCK_SKEW_SECONDS = 60
_STATE_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_KID_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


class GoogleIdentityError(RuntimeError):
    """Safe OAuth denial; messages deliberately contain no provider detail."""

    def __init__(self, code: str, *, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class GoogleConfig:
    enabled: bool = False
    client_id: str = ""
    client_secret: str = field(default="", repr=False)
    redirect_uri: str = ""
    allowed_domain: str | None = None
    data_dir: Path | str | None = None
    secure_deployment: bool = False

    @property
    def cookie_secure(self) -> bool:
        return self.secure_deployment or not _is_loopback_http(self.redirect_uri)

    def missing_fields(self) -> tuple[str, ...]:
        missing = []
        if not self.enabled:
            missing.append("enabled")
        if (
            not self.client_id
            or len(self.client_id) > 512
            or any(ord(c) < 0x21 for c in self.client_id)
        ):
            missing.append("client_id")
        if (
            not self.client_secret
            or len(self.client_secret) > 4096
            or any(ord(c) < 0x20 for c in self.client_secret)
        ):
            missing.append("client_secret")
        if not self.redirect_uri:
            missing.append("redirect_uri")
        if self.data_dir is None:
            missing.append("data_dir")
        if not _valid_redirect(self.redirect_uri, self.secure_deployment):
            missing.append("secure_redirect_uri")
        if self.allowed_domain is not None and not _valid_domain(self.allowed_domain):
            missing.append("allowed_domain")
        return tuple(dict.fromkeys(missing))

    def status(self) -> dict[str, object]:
        missing = self.missing_fields()
        crypto_available = _crypto_available()
        if not crypto_available:
            missing = (*missing, "cryptography")
        return {
            "enabled": self.enabled,
            "ready": not missing,
            "redirect_uri": self.redirect_uri
            if _valid_redirect(self.redirect_uri, self.secure_deployment)
            else "",
            "scopes": ["openid"],
            "domain": self.allowed_domain,
            "missing_fields": list(missing),
            "client_secret_set": bool(self.client_secret),
        }


@dataclass(frozen=True)
class GoogleStartResult:
    authorization_url: str
    flow_cookie: str = field(repr=False)


@dataclass(frozen=True)
class GoogleCallbackResult:
    outcome: str
    session_token: str | None = field(default=None, repr=False)
    actor_id: str | None = None


class GoogleIdentityService:
    """Validates Google identity assertions and maps them to local accounts."""

    def __init__(
        self,
        auth: Any,
        repository: GoogleIdentityRepository | Any,
        config: GoogleConfig,
        *,
        key: bytes | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        random_bytes: Callable[[int], bytes] = secrets.token_bytes,
        transport: JsonTransport | None = None,
        verifier: Callable[[str], Mapping[str, object]] | None = None,
    ) -> None:
        self.auth = auth
        storage = getattr(repository, "storage", None)
        self.repository = (
            repository
            if isinstance(repository, GoogleIdentityRepository)
            else GoogleIdentityRepository(storage)
        )
        if self.repository.storage is None:
            raise ValueError("identity repository storage required")
        self.config = config
        self._clock = clock
        self._random_bytes = random_bytes
        self._transport = transport or GoogleHttpsTransport()
        self._injected_verifier = verifier
        self._hmac_key = (
            key
            if key is not None
            else self._load_or_create_key()
            if config.status()["ready"]
            else None
        )
        self._jwks: dict[str, dict[str, object]] = {}
        self._jwks_expires = 0.0

    @property
    def cookie_secure(self) -> bool:
        return self.config.cookie_secure

    def status(self) -> dict[str, object]:
        result = self.config.status()
        if self._hmac_key is None:
            result["ready"] = False
            missing = list(result["missing_fields"])
            if "flow_key" not in missing:
                missing.append("flow_key")
            result["missing_fields"] = missing
        return result

    def start(self, intent: str = "login", token: str | None = None) -> GoogleStartResult:
        self._require_ready()
        if intent not in ("login", "link"):
            raise GoogleIdentityError("google_flow_invalid")
        actor_id: str | None = None
        session_binding: str | None = None
        if intent == "link":
            if not token:
                raise GoogleIdentityError("session_unavailable", status_code=401)
            try:
                actor = self.auth.resolve(token)
            except Exception:
                raise GoogleIdentityError("session_unavailable", status_code=401) from None
            actor_id = actor.actor_id
            session_binding = _session_binding(token)
        state = _b64u(self._random_bytes(32))
        nonce = _b64u(self._random_bytes(32))
        verifier = _b64u(self._random_bytes(48))
        now = self._clock()
        expires = now + FLOW_TTL
        state_hash = hashlib.sha256(state.encode("ascii")).hexdigest()
        self.repository.reserve_flow(state_hash, expires, now=now)
        claims = {
            "v": 1,
            "intent": intent,
            "state_hash": state_hash,
            "nonce": nonce,
            "verifier": verifier,
            "actor_id": actor_id,
            "session_binding": session_binding,
            "issued_at": int(now.timestamp()),
        }
        cookie = self._sign_flow(claims)
        challenge = _b64u(hashlib.sha256(verifier.encode("ascii")).digest())
        query = urllib.parse.urlencode(
            {
                "client_id": self.config.client_id,
                "redirect_uri": self.config.redirect_uri,
                "response_type": "code",
                "scope": "openid",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return GoogleStartResult(f"{AUTHORIZATION_URL}?{query}", cookie)

    def callback(
        self,
        flow_cookie: str,
        state: str,
        code: str,
        token: str | None = None,
    ) -> GoogleCallbackResult:
        self._require_ready()
        now = self._clock()
        claims = self._verify_flow(flow_cookie, now)
        if not isinstance(state, str) or not _STATE_RE.fullmatch(state):
            raise GoogleIdentityError("google_flow_invalid")
        state_hash = hashlib.sha256(state.encode("ascii")).hexdigest()
        if not hmac.compare_digest(state_hash, str(claims["state_hash"])):
            raise GoogleIdentityError("google_flow_invalid")
        intent = claims.get("intent")
        actor_id = claims.get("actor_id")
        if intent == "link":
            if not isinstance(token, str) or not token:
                raise GoogleIdentityError("session_unavailable", status_code=401)
            try:
                actor = self.auth.resolve(token)
            except Exception:
                raise GoogleIdentityError("session_unavailable", status_code=401) from None
            if actor.actor_id != actor_id or not hmac.compare_digest(
                _session_binding(token), str(claims.get("session_binding", ""))
            ):
                raise GoogleIdentityError("google_flow_invalid")
        elif intent != "login" or actor_id is not None:
            raise GoogleIdentityError("google_flow_invalid")
        if (
            not isinstance(code, str)
            or not code
            or len(code) > MAX_PROVIDER_CODE
            or any(ord(c) < 0x21 for c in code)
        ):
            raise GoogleIdentityError("google_flow_invalid")
        # Consume before exchanging the code. The SQLite write lock gives one callback the win.
        if not self.repository.consume_flow(state_hash, now):
            raise GoogleIdentityError("google_flow_replayed")
        try:
            token_response = self._transport.request_json(
                "POST",
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code_verifier": str(claims["verifier"]),
                },
                timeout=5.0,
                max_bytes=MAX_JWT_BYTES * 2,
            )
        except Exception:
            raise GoogleIdentityError("google_provider_unavailable", status_code=503) from None
        id_token = token_response.get("id_token")
        if not isinstance(id_token, str) or len(id_token.encode("utf-8")) > MAX_JWT_BYTES:
            raise GoogleIdentityError("google_assertion_invalid")
        try:
            identity = self._verified_claims(id_token)
        except GoogleIdentityError:
            raise
        except Exception:
            raise GoogleIdentityError("google_assertion_invalid") from None
        self._validate_claims(identity, str(claims["nonce"]), now)
        sub = identity.get("sub")
        if not isinstance(sub, str) or not sub or len(sub) > 255 or "\x00" in sub:
            raise GoogleIdentityError("google_assertion_invalid")
        subject_hash = google_subject_hash(sub)
        if intent == "link":
            try:
                # Recheck after the provider round trip; the original session may have
                # expired, been revoked, or lost account access while the user was away.
                actor = self.auth.resolve(str(token))
            except Exception:
                raise GoogleIdentityError("session_unavailable", status_code=401) from None
            if actor.actor_id != actor_id or not hmac.compare_digest(
                _session_binding(str(token)), str(claims.get("session_binding", ""))
            ):
                raise GoogleIdentityError("google_flow_invalid")
            try:
                self.repository.link_subject(str(actor_id), subject_hash, now)
            except Exception:
                # The unique provider+subject and account+provider indexes are the race-safe gate.
                raise GoogleIdentityError(
                    "google_identity_already_linked", status_code=409
                ) from None
            return GoogleCallbackResult("linked", actor_id=str(actor_id))
        linked_actor = self.repository.account_for_subject(subject_hash)
        if linked_actor is None:
            raise GoogleIdentityError("google_identity_unlinked", status_code=401)
        try:
            issued = self.auth.issue_session(linked_actor, method="google")
        except LockoutError:
            raise
        except Exception:
            raise GoogleIdentityError("account_unavailable", status_code=401) from None
        return GoogleCallbackResult("authenticated", session_token=issued, actor_id=linked_actor)

    def unlink(self, token: str) -> None:
        try:
            actor = self.auth.resolve(token)
        except Exception:
            raise GoogleIdentityError("session_unavailable", status_code=401) from None
        self.repository.unlink_subject(actor.actor_id, self._clock())

    def is_linked(self, token: str) -> bool:
        try:
            actor = self.auth.resolve(token)
        except Exception:
            raise GoogleIdentityError("session_unavailable", status_code=401) from None
        return self.repository.account_is_linked(actor.actor_id)

    def _require_ready(self) -> None:
        status = self.status()
        if not status["ready"]:
            raise GoogleIdentityError("google_unavailable", status_code=503)
        if self._hmac_key is None or len(self._hmac_key) < 32:
            raise GoogleIdentityError("google_unavailable", status_code=503)

    def _sign_flow(self, claims: dict[str, object]) -> str:
        payload = _b64u(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signed = f"v1.{payload}"
        signature = _b64u(hmac.new(self._hmac_key, signed.encode("ascii"), hashlib.sha256).digest())
        cookie = f"{signed}.{signature}"
        if len(cookie) > MAX_FLOW_COOKIE:
            raise GoogleIdentityError("google_flow_invalid")
        return cookie

    def _verify_flow(self, cookie: str, now: datetime) -> dict[str, object]:
        if not isinstance(cookie, str) or len(cookie) > MAX_FLOW_COOKIE:
            raise GoogleIdentityError("google_flow_invalid")
        try:
            version, payload, signature = cookie.split(".")
            signed = f"{version}.{payload}"
            expected = _b64u(
                hmac.new(self._hmac_key, signed.encode("ascii"), hashlib.sha256).digest()
            )
            if version != "v1" or not hmac.compare_digest(signature, expected):
                raise ValueError("signature")
            claims = _strict_json(_b64u_decode(payload))
            if not isinstance(claims, dict) or set(claims) != {
                "v",
                "intent",
                "state_hash",
                "nonce",
                "verifier",
                "actor_id",
                "session_binding",
                "issued_at",
            }:
                raise ValueError("shape")
            issued_at = claims["issued_at"]
            if type(issued_at) is not int:
                raise ValueError("time")
            age = now.timestamp() - issued_at
            if age < -MAX_CLOCK_SKEW_SECONDS or age >= FLOW_TTL.total_seconds():
                raise ValueError("stale")
            if claims["v"] != 1 or not re.fullmatch(r"[0-9a-f]{64}", str(claims["state_hash"])):
                raise ValueError("claims")
            if not all(
                isinstance(claims[name], str) and claims[name] for name in ("nonce", "verifier")
            ):
                raise ValueError("secrets")
            return claims
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            raise GoogleIdentityError("google_flow_invalid") from None

    def _verified_claims(self, id_token: str) -> Mapping[str, object]:
        if self._injected_verifier is not None:
            return self._injected_verifier(id_token)
        parts = id_token.split(".")
        if len(parts) != 3 or len(id_token.encode("utf-8")) > MAX_JWT_BYTES:
            raise ValueError("jwt shape")
        header = _strict_json(_b64u_decode(parts[0]))
        if not isinstance(header, dict) or set(header) - {"alg", "kid", "typ"}:
            raise ValueError("jwt header")
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise ValueError("jwt algorithm")
        kid = str(header["kid"])
        if not _KID_RE.fullmatch(kid):
            raise ValueError("jwt kid")
        claims = _strict_json(_b64u_decode(parts[1]))
        if not isinstance(claims, dict):
            raise ValueError("jwt claims")
        try:
            signature = _b64u_decode(parts[2])
            signed = f"{parts[0]}.{parts[1]}".encode("ascii")
            jwk = self._get_jwk(kid)
            _verify_rs256(jwk, signed, signature)
        except Exception:
            raise ValueError("jwt signature") from None
        return claims

    def _get_jwk(self, kid: str) -> dict[str, object]:
        now = time.monotonic()
        if now >= self._jwks_expires or kid not in self._jwks:
            self._refresh_jwks()
        jwk = self._jwks.get(kid)
        if jwk is None:
            self._refresh_jwks()
            jwk = self._jwks.get(kid)
        if jwk is None:
            raise ValueError("unknown kid")
        return jwk

    def _refresh_jwks(self) -> None:
        response = self._transport.request_json("GET", JWKS_URL, timeout=5.0, max_bytes=256 * 1024)
        keys = response.get("keys")
        if not isinstance(keys, list) or len(keys) > 100:
            raise ValueError("invalid jwks")
        parsed: dict[str, dict[str, object]] = {}
        for item in keys:
            if not isinstance(item, dict):
                continue
            kid = item.get("kid")
            if (
                item.get("kty") == "RSA"
                and item.get("alg", "RS256") == "RS256"
                and item.get("use", "sig") == "sig"
                and isinstance(kid, str)
                and _KID_RE.fullmatch(kid)
                and isinstance(item.get("n"), str)
                and isinstance(item.get("e"), str)
            ):
                parsed[kid] = item
        self._jwks = parsed
        self._jwks_expires = time.monotonic() + 300

    def _validate_claims(self, claims: Mapping[str, object], nonce: str, now: datetime) -> None:
        issuer = claims.get("iss")
        if issuer not in ("https://accounts.google.com", "accounts.google.com"):
            raise GoogleIdentityError("google_assertion_invalid")
        audience = claims.get("aud")
        if isinstance(audience, list):
            if len(audience) != 1 or not isinstance(audience[0], str):
                raise GoogleIdentityError("google_assertion_invalid")
            audience = audience[0]
        if audience != self.config.client_id:
            raise GoogleIdentityError("google_assertion_invalid")
        if "azp" in claims and claims.get("azp") != self.config.client_id:
            raise GoogleIdentityError("google_assertion_invalid")
        exp = claims.get("exp")
        issued = claims.get("iat")
        if type(exp) is not int or type(issued) is not int:
            raise GoogleIdentityError("google_assertion_invalid")
        now_s = int(now.timestamp())
        if exp <= now_s - MAX_CLOCK_SKEW_SECONDS or issued > now_s + MAX_CLOCK_SKEW_SECONDS:
            raise GoogleIdentityError("google_assertion_invalid")
        if exp <= issued or exp - issued > 2 * 60 * 60:
            raise GoogleIdentityError("google_assertion_invalid")
        if not isinstance(claims.get("nonce"), str) or not hmac.compare_digest(
            str(claims["nonce"]), nonce
        ):
            raise GoogleIdentityError("google_assertion_invalid")
        if self.config.allowed_domain is not None:
            hosted = claims.get("hd")
            if not isinstance(hosted, str) or hosted.lower() != self.config.allowed_domain.lower():
                raise GoogleIdentityError("google_domain_rejected")

    def _load_or_create_key(self) -> bytes | None:
        if self.config.data_dir is None:
            return None
        try:
            root = external_data_dir(self.config.data_dir)
            path = root / "google-flow-hmac.key"
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(path, flags)
            except FileNotFoundError:
                try:
                    fd = os.open(
                        path,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                    )
                except FileExistsError:
                    fd = os.open(path, flags)
                else:
                    try:
                        os.write(fd, self._random_bytes(32))
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    fd = os.open(path, flags)
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_nlink != 1
                    or info.st_uid != os.geteuid()
                ):
                    return None
                key = os.read(fd, 33)
            finally:
                os.close(fd)
            return key if len(key) == 32 else None
        except (OSError, ValueError):
            return None


def _verify_rs256(jwk: Mapping[str, object], message: bytes, signature: bytes) -> None:
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        modulus = int.from_bytes(_b64u_decode(str(jwk["n"])), "big")
        exponent = int.from_bytes(_b64u_decode(str(jwk["e"])), "big")
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key()
        if public_key.key_size < 2048 or public_key.key_size > 8192:
            raise ValueError("RSA key size rejected")
        public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
    except ImportError:
        raise RuntimeError("cryptography is required") from None


def _crypto_available() -> bool:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return False
    return True


def _is_loopback_http(uri: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(uri)
    except ValueError:
        return False
    return parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")


def _valid_redirect(uri: str, secure_deployment: bool) -> bool:
    try:
        parsed = urllib.parse.urlsplit(uri)
        if parsed.username or parsed.password or parsed.fragment or not parsed.path:
            return False
        if secure_deployment and parsed.scheme == "https" and parsed.hostname and parsed.netloc:
            return True
        return not secure_deployment and _is_loopback_http(uri) and parsed.netloc
    except ValueError:
        return False


def _valid_domain(domain: str) -> bool:
    return bool(
        re.fullmatch(
            r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}",
            domain,
        )
    )


def _strict_json(raw: bytes) -> object:
    def unique(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=unique)


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(value: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]*", value):
        raise ValueError("invalid base64url")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _session_binding(token: str) -> str:
    return hashlib.sha256(b"aicefr:google-link-session:v1\0" + token.encode("utf-8")).hexdigest()
