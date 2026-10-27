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
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aicefr.config import get_settings
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.repository import Repository, _now

logger = logging.getLogger(__name__)

# The default window. Long enough to cover a semester plus an appeals period,
# short enough that nothing accumulates between cohorts.
DEFAULT_RETENTION_DAYS = 180


# File .part moi hon nguong nay co the dang duoc upload, khong phai mo coi.
PART_GRACE_S = 3600

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
    """
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="seconds")

    with repo._conn() as c:  # noqa: SLF001 - retention is part of the storage layer
        rows = c.execute(
            "SELECT response_id, audio_path, report_json FROM response WHERE created_at < ?",
            (cutoff,),
        ).fetchall()

    audio_deleted = transcripts_cleared = bytes_freed = 0

    for row in rows:
        path = Path(row["audio_path"]) if row["audio_path"] else None
        if path and path.is_file():
            bytes_freed += path.stat().st_size
            audio_deleted += 1
            if not dry_run:
                path.unlink(missing_ok=True)

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
        if not dry_run and (changed or row["audio_path"]):
            with repo._conn() as c:  # noqa: SLF001
                c.execute(
                    "UPDATE response SET report_json=?, audio_path=NULL WHERE response_id=?",
                    (json.dumps(report, ensure_ascii=False), row["response_id"]),
                )

    lessons = lessons or LessonRepository(repo.db_path, seed=False)
    attempts, lesson_audio, lesson_cleared, lesson_freed = lessons.forget_older_than(
        cutoff, Path(upload_dir or get_settings().upload_dir), dry_run
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


def orphaned_recordings(
    repo: Repository, upload_dir: Path, lessons: LessonRepository | None = None
) -> list[Path]:
    """Files on disk that no row points at.

    These are the dangerous ones: nothing lists them, no erasure request finds
    them, and they are somebody's voice. They appear whenever a submission fails
    after the file is written.
    """
    with repo._conn() as c:  # noqa: SLF001
        known = {
            row["audio_path"]
            for row in c.execute("SELECT audio_path FROM response WHERE audio_path IS NOT NULL")
        }
    if not upload_dir.is_dir():
        return []
    # So duong dan DA CHUAN HOA o ca hai phia. audio_path luu nguyen dang luc ghi
    # (tuong doi "uploads/x.wav" o che do dev), nen so chuoi voi duong dan tuyet
    # doi tung liet ke -- va `orphans --delete` xoa -- ca ghi am dang dung.
    known_resolved = {str(Path(k).resolve()) for k in known}
    # The lesson path keeps its recordings and the teachers' model audio and
    # pictures in the same folder, under flat keys. Leaving them out listed
    # every one of them here -- and `orphans --delete` deleted them.
    lessons = lessons or LessonRepository(repo.db_path, seed=False)
    known_resolved |= {str((upload_dir / k).resolve()) for k in lessons.blob_keys()}
    fresh = time.time() - PART_GRACE_S
    return [
        p
        for p in upload_dir.iterdir()
        if p.is_file()
        and str(p.resolve()) not in known_resolved
        # File .part dang duoc ghi boi mot luot upload chua xong.
        and not (p.suffix == ".part" and p.stat().st_mtime > fresh)
    ]


def backup(repo: Repository, destination: Path) -> Path:
    """Copy the database while it is in use, using SQLite's own backup API.

    Copying the file with `cp` while a writer is mid-transaction produces a
    corrupt copy that looks fine until the day it is needed. The backup API
    takes a consistent snapshot instead.
    """

    if repo.on_postgres:
        raise ValueError("a PostgreSQL store is backed up with pg_dump, not with this command")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stamped = destination.with_name(
        f"{destination.stem}-{_now().replace(':', '').replace('-', '')}{destination.suffix}"
    )
    source = sqlite3.connect(repo.db_path)
    target = sqlite3.connect(stamped)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return stamped
