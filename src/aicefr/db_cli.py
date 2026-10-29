"""Structure of the core store (D045, D048): which versions are applied, apply the rest.

    python -m aicefr.db_cli status
    python -m aicefr.db_cli migrate
    python -m aicefr.db_cli snapshot > docs/db/schema_core.json

The core service migrates on start, so `migrate` is for a store about to be
restored into, or checked, before the service runs. `snapshot` prints the
collections and indexes of a fresh store, the reference `tests/test_schema.py`
holds the code to.
"""

from __future__ import annotations

import argparse
import sys
import uuid

from aicefr.config import get_settings
from aicefr.storage.migrations import LATEST, MIGRATIONS, applied, migrate, snapshot


def fresh_snapshot() -> str:
    """The structure of a store built from nothing, in memory."""
    target = f"mongomock://snapshot_{uuid.uuid4().hex[:12]}"
    migrate(target)
    return snapshot(target)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cấu trúc kho dữ liệu của dịch vụ core (D045, D048)")
    ap.add_argument("--db", default=None, help="mặc định AICEFR_CORE_DB, hoặc AICEFR_DB")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="các phiên bản đã áp dụng và còn chờ")
    sub.add_parser("migrate", help="áp dụng các phiên bản còn chờ")
    sub.add_parser("snapshot", help="in các collection và chỉ mục của một kho mới")
    args = ap.parse_args(argv)
    target = args.db or get_settings().store("core")

    if args.command == "snapshot":
        sys.stdout.write(fresh_snapshot())
        return 0
    if args.command == "migrate":
        ran = migrate(target)
        print(f"Đã áp dụng: {ran}" if ran else f"Kho đã ở phiên bản {LATEST}.")
        return 0
    done = applied(target)
    for m in MIGRATIONS:
        mark = f"đã áp dụng {done[m.version]}" if m.version in done else "CHƯA áp dụng"
        print(f"{m.version:>4}  {mark:<40}  {m.name}")
    return 0 if all(m.version in done for m in MIGRATIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
