"""The uptime number in the report is successful checks over finished checks."""

import importlib.util
from pathlib import Path


def _load_tool(name: str):
    """Load tools/<name>.py by path; the `pytest` binary in CI does not put the repo root on
    sys.path, so `from tools...` only works locally under `python -m pytest`."""
    path = Path(__file__).resolve().parent.parent / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tools_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_tool = _load_tool("uptime_report")
summarize = _tool.summarize


def run(day: str, conclusion: str | None) -> dict:
    return {
        "createdAt": f"{day}T10:00:00Z",
        "conclusion": conclusion,
        "event": "schedule",
        "url": f"u-{day}",
    }


def test_uptime_counts_finished_checks_only():
    runs = [
        run("2026-11-28", "success"),
        run("2026-11-28", "success"),
        run("2026-11-29", "failure"),
        run("2026-11-29", "cancelled"),  # not a check of the site
        run("2026-11-30", None),  # still running
    ]
    s = summarize(runs, since=None)
    assert (s["checks"], s["up"]) == (3, 2)
    assert abs(s["uptime"] - 2 / 3) < 1e-9
    assert s["failed_runs"] == [("2026-11-29T10:00:00Z", "u-2026-11-29")]


def test_since_drops_older_runs_and_empty_period_has_no_uptime():
    runs = [run("2026-11-27", "failure"), run("2026-11-28", "success")]
    assert summarize(runs, since="2026-11-28")["uptime"] == 1.0
    assert summarize(runs, since="2026-12-01")["uptime"] is None
