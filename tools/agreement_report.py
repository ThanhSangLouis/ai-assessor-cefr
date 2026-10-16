"""Rebuild a pseudonymous agreement report using the batch's stored seed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aicefr.research.service import ResearchNotFound, ResearchService
from aicefr.storage.sqlite import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    store = SQLiteStore(args.data_dir)
    try:
        payload = ResearchService(store, tasks=None).rating_report(args.batch_id)
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.out:
            args.out.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except ResearchNotFound:
        parser.error("rating batch was not found")
    finally:
        store.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
