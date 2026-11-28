"""The uptime number in the report is successful checks over finished checks."""

from tools.uptime_report import summarize


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
