"""Adapters for `BlobStore`: local disk, or S3-compatible object storage (D051).

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

import io
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlsplit

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

    def size(self, key: str) -> int | None:
        path = self._path(key)
        return path.stat().st_size if path.is_file() else None

    def keys(self) -> Iterator[str]:
        """Every stored key: for the orphan sweep. Files still being written
        (`.part` younger than an hour) are not keys yet."""
        fresh = time.time() - 3600
        for p in self.root.iterdir():
            if not p.is_file() or p.name.startswith("."):
                continue
            if p.suffix == ".part" and p.stat().st_mtime > fresh:
                continue
            yield p.name


class S3BlobStore:
    """Recordings in an S3-compatible bucket (MinIO, AWS S3), through `minio` (Apache-2.0).

    What makes a second instance of a service correct: every instance reads and
    writes the same bucket. Objects have no local file, so `local_path` is None
    and the audio endpoints stream the bytes. The bucket is made on first use;
    it is private, and objects are never given a public URL.
    """

    name = "s3"

    def __init__(
        self, bucket: str, endpoint: str, access_key: str, secret_key: str, secure: bool = True
    ) -> None:
        try:
            from minio import Minio
        except ImportError as e:  # pragma: no cover - depends on the install
            raise RuntimeError("object storage needs minio: pip install 'aicefr[services]'") from e
        self.bucket = bucket
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        if not self.client.bucket_exists(bucket):
            try:
                self.client.make_bucket(bucket)
            except Exception:  # noqa: BLE001 - made by another instance meanwhile
                if not self.client.bucket_exists(bucket):
                    raise

    @staticmethod
    def _check(key: str) -> str:
        if not key or "/" in key or "\\" in key or key.startswith("."):
            raise ValueError(f"khóa không hợp lệ: {key!r}")
        return key

    def put(self, key: str, data: bytes) -> str:
        self.client.put_object(self.bucket, self._check(key), io.BytesIO(data), len(data))
        return key

    def get(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, self._check(key))
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def local_path(self, key: str) -> Path | None:
        return None

    def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, self._check(key))

    def _stat(self, key: str):
        from minio.error import S3Error

        try:
            return self.client.stat_object(self.bucket, self._check(key))
        except S3Error as e:
            if e.code in ("NoSuchKey", "NoSuchObject", "NoSuchBucket"):
                return None
            raise

    def exists(self, key: str) -> bool:
        return self._stat(key) is not None

    def size(self, key: str) -> int | None:
        stat = self._stat(key)
        return int(stat.size) if stat is not None else None

    def keys(self) -> Iterator[str]:
        for obj in self.client.list_objects(self.bucket):
            yield obj.object_name


def key_of(audio_path: str | None) -> str | None:
    """The blob key a stored recording reference names.

    A response keeps its recording's key; responses saved before D051 kept a
    full path under the upload folder, whose last part is the same key.
    """
    if not audio_path:
        return None
    return Path(audio_path).name


def blob_store(settings) -> LocalBlobStore | S3BlobStore:
    """The store the settings name: `AICEFR_BLOBS=s3://bucket`, else the upload folder.

    For S3, `AICEFR_S3_ENDPOINT` (host:port), `AICEFR_S3_ACCESS_KEY`,
    `AICEFR_S3_SECRET_KEY` and `AICEFR_S3_SECURE` (default on).
    """
    url = getattr(settings, "blob_url", "") or ""
    if url.startswith("s3://"):
        bucket = urlsplit(url).netloc
        endpoint = os.getenv("AICEFR_S3_ENDPOINT", "")
        if not bucket or not endpoint:
            raise RuntimeError("AICEFR_BLOBS=s3://<bucket> needs AICEFR_S3_ENDPOINT")
        return S3BlobStore(
            bucket,
            endpoint,
            os.getenv("AICEFR_S3_ACCESS_KEY", ""),
            os.getenv("AICEFR_S3_SECRET_KEY", ""),
            secure=os.getenv("AICEFR_S3_SECURE", "1").lower() not in ("0", "false", "no", "off"),
        )
    return LocalBlobStore(settings.upload_dir)


def audio_response(blobs, audio_path: str | None, filename: str):
    """The recording as an HTTP response: a file with Range support when the
    store has one, the bytes otherwise; 404 when it is gone."""
    from fastapi import HTTPException
    from fastapi.responses import FileResponse, Response

    key = key_of(audio_path)
    if key is None or not blobs.exists(key):
        raise HTTPException(404, "không còn tệp ghi âm của bài này")
    path = blobs.local_path(key)
    if path is not None:
        return FileResponse(path, media_type="audio/wav", filename=filename)
    return Response(
        blobs.get(key),
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
