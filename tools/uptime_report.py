"""Uptime of the public demo, computed from the run history of .github/workflows/uptime.yml.

Each scheduled run of that workflow calls https://speakup.fit/healthz and the home page;
a run that succeeds is one check where the demo was up. This script counts the runs with
the GitHub CLI and prints the share of successful checks, so the number in the report can
be traced back to the runs it came from.

Usage:
    python tools/uptime_report.py              # all recorded runs
    python tools/uptime_report.py --since 2026-11-28

Needs `gh` signed in with read access to the repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter


def fetch_runs(limit: int) -> list[dict]:
    out = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            "uptime.yml",
            "--limit",
            str(limit),
            "--json",
            "conclusion,createdAt,event,url",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def summarize(runs: list[dict], since: str | None) -> dict:
    """Share of finished checks that succeeded; runs still going or cancelled are left out."""
    picked = [r for r in runs if since is None or r["createdAt"][:10] >= since]
    counts = Counter(r["conclusion"] or "in_progress" for r in picked)
    finished = counts["success"] + counts["failure"] + counts["timed_out"]
    failed = [r for r in picked if r["conclusion"] in ("failure", "timed_out")]
    return {
        "checks": finished,
        "up": counts["success"],
        "uptime": counts["success"] / finished if finished else None,
        "first": min((r["createdAt"] for r in picked), default=None),
        "last": max((r["createdAt"] for r in picked), default=None),
        "failed_runs": [(r["createdAt"], r["url"]) for r in failed],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", help="only runs on or after this date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    s = summarize(fetch_runs(args.limit), args.since)
    if not s["checks"]:
        print("No finished uptime checks yet.")
        return
    print(f"Period: {s['first']} .. {s['last']}")
    print(f"Checks: {s['checks']}, up: {s['up']}, uptime: {s['uptime']:.2%}")
    for when, url in s["failed_runs"]:
        print(f"  down at {when}: {url}")


if __name__ == "__main__":
    main()
