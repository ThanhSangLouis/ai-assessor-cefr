"""CLI for core database schema and migrations (D045, D048).

Usage:
    python -m aicefr.db_cli status [--db TARGET]
    python -m aicefr.db_cli migrate [--db TARGET]
    python -m aicefr.db_cli snapshot [--db TARGET]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from aicefr.storage.migrations import (
    applied,
    migrate,
    pending,
    snapshot,
)


def fresh_snapshot() -> str:
    """Return JSON schema snapshot of a freshly migrated database."""
    target = "mongomock://schema_fresh"
    migrate(target)
    return snapshot(target)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage core MongoDB schema migrations.")
    parser.add_argument(
        "--db",
        dest="target",
        default="aicefr.db",
        help="Database target URL or path (default: aicefr.db)",
    )
    parser.add_argument(
        "command",
        choices=["status", "migrate", "snapshot"],
        help="Command to execute",
    )

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        sys.stdout.write(snapshot(args.target))
        return 0

    if args.command == "migrate":
        ran = migrate(args.target)
        if ran:
            print(f"Đã áp dụng các phiên bản migration: {ran}")
        else:
            print("Cơ sở dữ liệu đã ở phiên bản mới nhất.")
        return 0

    if args.command == "status":
        p = pending(args.target)
        a = applied(args.target)
        if p:
            print(f"Có {len(p)} migration CHƯA áp dụng: {p}")
            return 1
        print(f"Toàn bộ {len(a)} migration đã được áp dụng.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
