"""Bounded immutable blobs with same-filesystem staging and SHA-256 verification."""

from __future__ import annotations

import hashlib
import os
import stat
import uuid
from pathlib import Path

from aicefr.contracts import BlobRef
from aicefr.storage.paths import external_data_dir


class BlobIntegrityError(Exception):
    """Blob is absent, corrupt, or outside the approved storage contract."""


class BlobStore:
    def __init__(self, data_dir: Path | str, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("positive max_bytes required")
        self.root = external_data_dir(data_dir) / "blobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes

    def _path(self, blob_id: str) -> Path:
        # The ID is always generated or validated by BlobRef before this boundary.
        BlobRef(blob_id=blob_id, sha256="0" * 64, size_bytes=1)
        return self.root / blob_id

    def store(self, data: bytes) -> BlobRef:
        if not isinstance(data, bytes) or not 0 < len(data) <= self.max_bytes:
            raise ValueError("blob size outside configured limit")
        blob_id = uuid.uuid4().hex
        staging = self.root / f"tmp-{blob_id}.part"
        final = self._path(blob_id)
        digest = hashlib.sha256(data).hexdigest()
        try:
            with staging.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staging, final)
            # Windows does not permit opening a directory descriptor for fsync.
            # The staged file itself was flushed above and ``os.replace`` remains
            # atomic on the same volume; POSIX additionally flushes the directory
            # entry for crash durability.
            if os.name != "nt":
                directory_fd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            staging.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            raise
        return BlobRef(blob_id=blob_id, sha256=digest, size_bytes=len(data))

    def read(self, blob: BlobRef) -> bytes:
        try:
            descriptor = os.open(
                self._path(blob.blob_id),
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                details = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_size != blob.size_bytes
                    or details.st_size > self.max_bytes
                ):
                    raise BlobIntegrityError("blob integrity failure")
                data = os.read(descriptor, blob.size_bytes + 1)
            finally:
                os.close(descriptor)
        except OSError:
            raise BlobIntegrityError("blob unavailable") from None
        if len(data) != blob.size_bytes or hashlib.sha256(data).hexdigest() != blob.sha256:
            raise BlobIntegrityError("blob integrity failure")
        return data

    def compensate(self, blob: BlobRef) -> None:
        self._path(blob.blob_id).unlink(missing_ok=True)

    def orphan_ids(self, referenced_ids: set[str]) -> tuple[str, ...]:
        return tuple(
            sorted(
                path.name
                for path in self.root.iterdir()
                if path.is_file()
                and (
                    path.name.startswith("tmp-")
                    and path.name.endswith(".part")
                    or len(path.name) == 32
                    and path.name not in referenced_ids
                )
            )
        )
