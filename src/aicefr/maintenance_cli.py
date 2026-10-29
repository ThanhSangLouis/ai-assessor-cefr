"""Operational commands: retention, orphan cleanup, backup and restore.

Run:
    python -m aicefr.maintenance_cli retention --days 180          # xem trước
    python -m aicefr.maintenance_cli retention --days 180 --apply  # thực hiện
    python -m aicefr.maintenance_cli orphans
    python -m aicefr.maintenance_cli backup --to backups/aicefr.json
    python -m aicefr.maintenance_cli restore --from backups/aicefr-20261021T000000+0000.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aicefr.config import get_settings
from aicefr.infra.blobs import LocalBlobStore
from aicefr.retention import (
    DEFAULT_RETENTION_DAYS,
    apply_retention,
    backup,
    orphaned_recordings,
    restore_backup,
)
from aicefr.storage.db import collection_exists
from aicefr.storage.lesson_repository import LessonRepository
from aicefr.storage.repository import Repository


class WrongStore(Exception):
    """The command was about to run against a store that is not the one it needs."""


def _stores(args: argparse.Namespace) -> tuple[Repository, LessonRepository]:
    """The core service's store (D044), refused unless it already holds its collections.

    Retention and orphan cleanup read the responses and the lesson attempts,
    whose recordings share the upload folder. Opening a repository creates its
    collections, so a wrong address would look like an empty store -- and to
    `orphans --delete` every recording an empty store does not list is an
    orphan. So the store must already hold both collections.
    """
    target = args.db or get_settings().store("core")
    # D051: lesson attempts are in the learning part's store, which may be
    # its own database; on one machine, or with --db, the same store.
    learning = args.db or get_settings().store("learning")
    for store, name in ((target, "response"), (learning, "attempt")):
        if not collection_exists(store, name):
            raise WrongStore(f"kho {store!r} chưa có collection {name}: kiểm tra lại địa chỉ kho")
    return Repository(target), LessonRepository(learning, seed=False)


def _retention(args: argparse.Namespace) -> int:
    repo, lessons = _stores(args)
    report = apply_retention(
        repo,
        days=args.days,
        dry_run=not args.apply,
        upload_dir=Path(args.uploads) if args.uploads else None,
        lessons=lessons,
    )
    print(report.describe())
    if report.dry_run and (report.audio_deleted or report.transcripts_cleared):
        print("Đây mới là xem trước. Thêm --apply để thực hiện. Thao tác không hoàn tác được.")
    return 0


def _orphans(args: argparse.Namespace) -> int:
    repo, lessons = _stores(args)
    blobs = LocalBlobStore(args.uploads) if args.uploads else repo.blobs
    files = orphaned_recordings(repo, Path(args.uploads) if args.uploads else None, lessons)
    if not files:
        print("Không có tệp ghi âm mồ côi.")
        return 0
    total = sum(blobs.size(f.name) or 0 for f in files)
    print(f"Có {len(files)} tệp ghi âm không có bản ghi nào trỏ tới ({total / 1048576:.1f} MiB):")
    for f in files[:20]:
        print(f"  {f}")
    if len(files) > 20:
        print(f"  … và {len(files) - 20} tệp nữa")
    if args.delete:
        for f in files:
            blobs.delete(f.name)
        print(f"Đã xoá {len(files)} tệp.")
    else:
        print("Thêm --delete để xoá. Đây là giọng nói của người thật, không tệp nào được")
        print("liệt kê ở bất kỳ báo cáo nào, nên không yêu cầu xoá nào chạm tới chúng.")
    return 0


def _backup(args: argparse.Namespace) -> int:
    path = backup(Repository(args.db or get_settings().store("core")), Path(args.to))
    print(f"Đã sao lưu sang {path} ({path.stat().st_size / 1048576:.1f} MiB)")
    return 0


def _restore(args: argparse.Namespace) -> int:
    n = restore_backup(Repository(args.db or get_settings().store("core")), Path(args.source))
    print(f"Đã khôi phục {n} bản ghi từ {args.source}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bảo trì hệ thống AI Assessor CEFR")
    ap.add_argument(
        "--db",
        default=None,
        help="kho của dịch vụ core (URL mongodb://);"
        " mặc định AICEFR_CORE_DB, hoặc AICEFR_DB trên một máy",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("retention", help="xoá bản ghi và bản chép lời quá hạn lưu trữ")
    p.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS)
    p.add_argument("--apply", action="store_true", help="thực hiện thật, mặc định chỉ xem trước")
    p.add_argument("--uploads", default=None, help="thư mục tệp ghi âm của lượt luyện")
    p.set_defaults(func=_retention)

    p = sub.add_parser("orphans", help="tìm tệp ghi âm không có bản ghi nào trỏ tới")
    p.add_argument("--uploads", default=None)
    p.add_argument("--delete", action="store_true")
    p.set_defaults(func=_orphans)

    p = sub.add_parser("backup", help="sao lưu mọi collection ra một tệp JSON")
    p.add_argument("--to", default="backups/aicefr.json")
    p.set_defaults(func=_backup)

    p = sub.add_parser("restore", help="khôi phục tệp sao lưu vào một kho rỗng")
    p.add_argument("--from", dest="source", required=True)
    p.set_defaults(func=_restore)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001 - a maintenance command reports, never crashes
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
