"""Adapters for `BlobStore`. Local disk today, object storage later.

The interesting part is not the local adapter -- it is a thin wrapper over
`pathlib` -- but the shape of the interface it has to satisfy, which was chosen
so that an S3 adapter can satisfy it too:

  * keys are opaque strings, not paths, so nothing may build a filename out of
    user input or assume directories exist;
  * `local_path` may return None, so callers must already cope with a backend
    that has no file to hand to `FileResponse`;
  * `put` returns the key, not a URL, so no caller can start depending on a
    layout that object storage will not have.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalBlobStore:
    """Recordings on the local filesystem.

    Correct and cheap while one process serves everything. It stops being
    correct the moment a second instance runs: that instance has no access to
    these files, so the audio endpoint answers 404 on one node out of two.
    """

    name = "local"

    def __init__(self, root: Path | str = "uploads") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # Recordings of identifiable people: readable by this user only.
        try:
            self.root.chmod(0o700)
        except OSError:  # pragma: no cover - filesystem may not support it
            logger.warning("could not restrict permissions on %s", self.root)

    def _path(self, key: str) -> Path:
        # Keys are opaque. Refuse anything that could climb out of the root,
        # even though every key is currently generated server-side.
        if "/" in key or "\\" in key or key.startswith("."):
            raise ValueError(f"khóa không hợp lệ: {key!r}")
        return self.root / key

    def put(self, key: str, data: bytes) -> str:
        self._path(key).write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def local_path(self, key: str) -> Path | None:
        path = self._path(key)
        return path if path.is_file() else None

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
