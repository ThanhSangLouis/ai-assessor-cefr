"""Storage limitation: delete recordings once they are no longer needed.

A system that only ever deletes on request is not compliant with anything. The
principle is storage limitation: personal data is kept for as long as the stated
purpose requires and no longer. Voice recordings identify the person who made
them, so "we kept everything forever because nobody asked us to delete it" is
not a defensible position.

What this deletes and what it keeps is a deliberate split:

    audio          deleted   the most identifying artifact, and the largest
    transcript     deleted   contains what the student actually said
    score + band   kept      the academic record the assessment existed to produce
    audit entries  kept      accountability outlives the data it describes

So a report older than the retention window keeps its result and loses its
evidence. That is the trade the policy is meant to make.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aicefr.infra.blobs import LocalBlobStore, key_of
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.repository import Repository, _now

logger = logging.getLogger(__name__)

# The default window. Long enough to cover a semester plus an appeals period,
# short enough that nothing accumulates between cohorts.
DEFAULT_RETENTION_DAYS = 180


# Loai bang chung co trich nguyen van loi noi trong ghi chu (report/evidence.py).
QUOTING_KINDS = {"filler", "low_confidence_word"}
REDACTED_NOTE = "Đã xoá trích đoạn lời nói theo thời hạn lưu trữ."


@dataclass(frozen=True)
class RetentionReport:
    """What a run did, or would do."""

    cutoff: str
    considered: int
    audio_deleted: int
    transcripts_cleared: int
    bytes_freed: int
    dry_run: bool
    # Attempts of the lesson path (D025), counted into the totals above too.
    lesson_attempts: int = 0

    def describe(self) -> str:
        verb = "sẽ xoá" if self.dry_run else "đã xoá"
        return (
            f"Mốc: trước {self.cutoff}. Xét {self.considered} bài và "
            f"{self.lesson_attempts} lượt luyện theo bài học, "
            f"{verb} {self.audio_deleted} tệp ghi âm ({self.bytes_freed / 1048576:.1f} MiB) "
            f"và {verb} bản chép lời của {self.transcripts_cleared} bài. "
            "Điểm số và nhật ký kiểm toán được giữ nguyên."
        )


# Hai ten khoa, mot y nghia. `Transcript.text` truoc day ten la `transcript`;
# nhung hang ghi truoc luc doi ten van con khoa cu trong `report_json`. Cho nay
# lam viec tren JSON tho nen khong duoc huong alias cua Pydantic. Chi tim mot
# khoa thi nhung hang do khong bao gio duoc xoa ban chep -- va do la loi rieng
# tu, khong phai loi hien thi.
TEXT_KEYS = ("text", "transcript")


def apply_retention(
    repo: Repository,
    days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = True,
    upload_dir: Path | None = None,
    lessons: LessonRepository | None = None,
) -> RetentionReport:
    """Remove audio and transcripts older than `days`.

    Defaults to a dry run. Deleting personal data is correct but irreversible,
    so the default has to be the one that cannot destroy anything by accident:
    an operator who runs this by mistake should get a report, not a loss.

    Covers lesson attempts (D025) too, through the learning service's store
    (`lessons`; the same store as `repo` unless given, as on one machine);
    their recordings are files in `upload_dir`, the settings' unless given.
    Recordings live in the blob store (D051): the repository's, or the upload
    folder named here.
    """
    blobs = LocalBlobStore(upload_dir) if upload_dir else repo.blobs
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")

    responses = repo.col("response")  # retention is part of the storage layer
    rows = list(
        responses.find(
            {"created_at": {"$lt": cutoff}}, {"response_id": 1, "audio_path": 1, "report_json": 1}
        )
    )

    audio_deleted = transcripts_cleared = bytes_freed = 0

    for row in rows:
        size = _recording_size(blobs, row.get("audio_path"))
        if size is not None:
            bytes_freed += size
            audio_deleted += 1
            if not dry_run:
                _drop_recording(blobs, row.get("audio_path"))

        report = json.loads(row["report_json"])
        changed = False
        asr = report.get("asr")
        if asr and (any(asr.get(k) for k in TEXT_KEYS) or asr.get("words")):
            transcripts_cleared += 1
            changed = True
            # Keep the shape of the record, drop its content: the report
            # still says which engine ran, so provenance survives.
            for k in TEXT_KEYS:
                if k in asr:
                    asr[k] = ""
            asr["words"] = []
            report["asr"] = asr
        # Bang chung cung chua loi noi: `snippet` la toi 9 tu quanh moi moc, va
        # ghi chu cua tu ngap ngung / tu nghe khong ro trich nguyen tu do. Xoa
        # transcript ma giu nhung trich doan nay la xoa nua voi.
        for ev in (report.get("assessment") or {}).get("evidence") or []:
            if ev.get("snippet"):
                ev["snippet"] = None
                changed = True
            if ev.get("kind") in QUOTING_KINDS and ev.get("note") != REDACTED_NOTE:
                ev["note"] = REDACTED_NOTE
                changed = True
        # Con tro audio phai bo moi khi file da bi xoa (hoac da mat), ke ca bai QC
        # tu choi khong co transcript -- truoc day chi bo trong nhanh co transcript.
        if not dry_run and (changed or row.get("audio_path")):
            responses.update_one(
                {"response_id": row["response_id"]},
                {
                    "$set": {
                        "report_json": json.dumps(report, ensure_ascii=False),
                        "audio_path": None,
                    }
                },
            )

    lessons = lessons or LessonRepository(repo.db_path, seed=False)
    attempts, lesson_audio, lesson_cleared, lesson_freed = lessons.forget_older_than(
        cutoff, blobs, dry_run
    )
    audio_deleted += lesson_audio
    transcripts_cleared += lesson_cleared
    bytes_freed += lesson_freed

    if not dry_run and (audio_deleted or transcripts_cleared):
        repo.write_audit(
            "system",
            "RETENTION_SWEEP",
            None,
            f"{audio_deleted} audio, {transcripts_cleared} transcripts, before {cutoff}",
        )
        logger.info(
            "retention sweep removed %d recordings and %d transcripts",
            audio_deleted,
            transcripts_cleared,
        )

    return RetentionReport(
        cutoff=cutoff,
        considered=len(rows),
        audio_deleted=audio_deleted,
        transcripts_cleared=transcripts_cleared,
        bytes_freed=bytes_freed,
        dry_run=dry_run,
        lesson_attempts=attempts,
    )


def _legacy_file(audio_path: str | None) -> Path | None:
    """The file a response saved before D051 names by its absolute path, if it exists."""
    if audio_path and Path(audio_path).is_absolute() and Path(audio_path).is_file():
        return Path(audio_path)
    return None


def _recording_size(blobs, audio_path: str | None) -> int | None:
    legacy = _legacy_file(audio_path)
    if legacy is not None:
        return legacy.stat().st_size
    key = key_of(audio_path)
    return blobs.size(key) if key else None


def _drop_recording(blobs, audio_path: str | None) -> None:
    legacy = _legacy_file(audio_path)
    if legacy is not None:
        legacy.unlink(missing_ok=True)
    key = key_of(audio_path)
    if key:
        blobs.delete(key)


def orphaned_recordings(
    repo: Repository, upload_dir: Path | None = None, lessons: LessonRepository | None = None
) -> list[Path]:
    """Recordings in the blob store that no document points at.

    These are the dangerous ones: nothing lists them, no erasure request finds
    them, and they are somebody's voice. They appear whenever a submission fails
    after the recording is stored. Returns each as a path: the file when the
    store is a folder, the bare key when it is object storage (D051).
    """
    blobs = LocalBlobStore(upload_dir) if upload_dir else repo.blobs
    if upload_dir is not None and not Path(upload_dir).is_dir():
        return []
    # Keys on both sides: a response keeps its recording's key, one saved
    # before D051 a path (absolute or relative) whose last part is that key.
    known = {
        key_of(p)
        for p in repo.col("response").distinct("audio_path", {"audio_path": {"$ne": None}})
    }
    # The lesson path keeps its recordings and the teachers' model audio and
    # pictures in the same store, under flat keys. Leaving them out listed
    # every one of them here -- and `orphans --delete` deleted them.
    lessons = lessons or LessonRepository(repo.db_path, seed=False)
    known |= set(lessons.blob_keys())
    return [blobs.local_path(k) or Path(k) for k in sorted(blobs.keys()) if k not in known]


def backup(repo: Repository, destination: Path) -> Path:
    """Write every collection of the store to one JSON file, stamped with the time.

    For a store small enough to copy while it runs: Extended JSON keeps the
    types MongoDB stores, so `restore_backup` puts back exactly what was read.
    A server in production is backed up with `mongodump`, which this does not
    replace (deploy/vps/backup.sh).
    """
    from bson import json_util

    destination.parent.mkdir(parents=True, exist_ok=True)
    stamped = destination.with_name(
        f"{destination.stem}-{_now().replace(':', '').replace('-', '')}{destination.suffix}"
    )
    db = repo.db
    dump = {name: list(db[name].find()) for name in sorted(db.list_collection_names())}
    stamped.write_text(json_util.dumps(dump, ensure_ascii=False), encoding="utf-8")
    return stamped


def restore_backup(repo: Repository, source: Path) -> int:
    """Put a `backup` file back into an EMPTY store; the documents restored.

    Refuses a store that already holds data: merging a backup into live data
    would bring erased recordings' reports back.
    """
    from bson import json_util

    db = repo.db
    if any(db[name].estimated_document_count() for name in db.list_collection_names()):
        raise ValueError("kho đích đã có dữ liệu: chỉ khôi phục vào kho rỗng")
    dump = json_util.loads(source.read_text(encoding="utf-8"))
    total = 0
    for name, documents in dump.items():
        if documents:
            db[name].insert_many(documents)
            total += len(documents)
    return total
