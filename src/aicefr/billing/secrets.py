"""Local, permission-checked key storage for billing signatures."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

from aicefr.storage.paths import external_data_dir
from aicefr.storage.private_files import is_private_file


class KeyStoreError(RuntimeError):
    """Raised without exposing key bytes or filesystem details to callers."""


class KeyRing:
    """A single versioned local key with HMAC domain separation.

    The private key file is deliberately opaque to the public API. Separate
    domain strings ensure a sandbox event signature cannot be reused as a
    license signature.
    """

    filename = "billing-hmac.key"
    version = 1
    _prefix = b"AICEFR-BILLING-KEY-V1\0"

    def __init__(self, data_dir: Path | str, *, key: bytes | None = None) -> None:
        self._key: bytes
        if key is not None:
            if not isinstance(key, bytes) or len(key) < 32:
                raise KeyStoreError("invalid key material")
            self._key = key
            return
        try:
            directory = external_data_dir(data_dir)
        except (OSError, TypeError, ValueError):
            raise KeyStoreError("billing key storage unavailable") from None
        try:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            path = directory / self.filename
            try:
                fd = os.open(
                    path,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_BINARY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                )
            except FileExistsError:
                self._key = self._read_existing(path)
            else:
                try:
                    if not is_private_file(path, descriptor=fd):
                        raise KeyStoreError("unsafe billing key permissions")
                    raw = secrets.token_bytes(32)
                    data = self._prefix + base64.urlsafe_b64encode(raw) + b"\n"
                    view = memoryview(data)
                    while view:
                        written = os.write(fd, view)
                        if written <= 0:
                            raise OSError("short key write")
                        view = view[written:]
                    os.fsync(fd)
                    self._key = raw
                finally:
                    os.close(fd)
                try:
                    dfd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                    try:
                        os.fsync(dfd)
                    finally:
                        os.close(dfd)
                except OSError:
                    # Directory fsync is unavailable on some supported filesystems.
                    pass
        except KeyStoreError:
            raise
        except OSError as exc:
            raise KeyStoreError("billing key storage unavailable") from exc

    @classmethod
    def _read_existing(cls, path: Path) -> bytes:
        try:
            if not is_private_file(path):
                raise KeyStoreError("unsafe billing key permissions")
            fd = os.open(
                path,
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                if not is_private_file(path, descriptor=fd):
                    raise KeyStoreError("unsafe billing key file")
                data = os.read(fd, 512)
                if os.read(fd, 1):
                    raise KeyStoreError("invalid billing key file")
            finally:
                os.close(fd)
            prefix = cls._prefix
            if not data.startswith(prefix):
                raise KeyStoreError("invalid billing key version")
            encoded = data[len(prefix) :].strip()
            raw = base64.b64decode(encoded, altchars=b"-_", validate=True)
            if len(raw) != 32:
                raise KeyStoreError("invalid billing key material")
            return raw
        except KeyStoreError:
            raise
        except (OSError, ValueError) as exc:
            raise KeyStoreError("billing key storage unavailable") from exc

    @staticmethod
    def _message(domain: str, payload: bytes) -> bytes:
        if not isinstance(domain, str) or not domain or len(domain) > 96:
            raise ValueError("invalid signature domain")
        if not isinstance(payload, bytes) or len(payload) > 65_536:
            raise ValueError("invalid signature payload")
        return b"AICEFR\0" + domain.encode("ascii", "strict") + b"\0" + payload

    def sign(self, domain: str, payload: bytes) -> str:
        return hmac.new(self._key, self._message(domain, payload), hashlib.sha256).hexdigest()

    def verify(self, domain: str, payload: bytes, signature: str) -> bool:
        if not isinstance(signature, str) or len(signature) != 64:
            return False
        try:
            expected = self.sign(domain, payload)
        except (TypeError, ValueError, UnicodeError):
            return False
        return hmac.compare_digest(expected, signature.lower())

    def sign_license(self, payload: bytes) -> str:
        return self.sign("license:v1", payload)

    def verify_license(self, payload: bytes, signature: str) -> bool:
        return self.verify("license:v1", payload, signature)

    def sign_gateway_event(self, payload: bytes) -> str:
        return self.sign("gateway-event:v1", payload)

    def verify_gateway_event(self, payload: bytes, signature: str) -> bool:
        return self.verify("gateway-event:v1", payload, signature)
