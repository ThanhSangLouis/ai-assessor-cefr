"""Unit & Integration tests for Practice Path UI logic, Calendar Week, and Data States.

Guards:
- Fixed calendar week alignment (T2 to CN) across various days of the week.
- Rendering states: empty vs in-progress vs goal-met.
- The selectors other tests read, and the parts of the mockup (D092).
- The page's stylesheet: themes, breakpoints, nothing left in style.css.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "src" / "aicefr" / "api" / "static"


def get_calendar_week_py(
    today_date: date,
    week_records: list[dict[str, object]] | None = None,
    rest_days: list[str] | None = None,
) -> list[dict[str, object]]:
    """Python reference implementation of getCalendarWeek() in practice_path.js."""
    weekday = today_date.weekday()  # 0 is Mon, 6 is Sun
    monday = today_date - timedelta(days=weekday)
    labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    week_map = {w["date"]: w.get("seconds", 0) for w in (week_records or [])}
    rest_set = set(rest_days or [])

    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        iso = d.isoformat()
        is_today = d == today_date
        is_future = d > today_date
        seconds = week_map.get(iso, 0)
        is_done = seconds > 0
        is_rest = not is_done and not is_future and iso in rest_set

        days.append(
            {
                "date": iso,
                "dayName": labels[i],
                "isToday": is_today,
                "isFuture": is_future,
                "seconds": seconds,
                "isDone": is_done,
                "isRest": is_rest,
            }
        )
    return days


class TestCalendarWeekLogic:
    """Verifies that fixed calendar week (T2 -> CN) behaves correctly for every day of the week."""

    def test_wednesday_calendar_week(self):
        wednesday = date(2026, 11, 4)
        week = get_calendar_week_py(wednesday)

        assert len(week) == 7
        assert [d["dayName"] for d in week] == ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        # Mon & Tue are past
        assert not week[0]["isToday"] and not week[0]["isFuture"]
        assert not week[1]["isToday"] and not week[1]["isFuture"]
        # Wed is today
        assert week[2]["isToday"] and not week[2]["isFuture"]
        assert week[2]["dayName"] == "T4"
        # Thu to Sun are future
        for i in range(3, 7):
            assert not week[i]["isToday"] and week[i]["isFuture"]

    def test_monday_calendar_week(self):
        monday = date(2026, 11, 2)
        week = get_calendar_week_py(monday)

        assert week[0]["dayName"] == "T2"
        assert week[0]["isToday"] and not week[0]["isFuture"]
        for i in range(1, 7):
            assert not week[i]["isToday"] and week[i]["isFuture"]

    def test_sunday_calendar_week(self):
        sunday = date(2026, 11, 8)
        week = get_calendar_week_py(sunday)

        # All 6 previous days are past
        for i in range(6):
            assert not week[i]["isToday"] and not week[i]["isFuture"]
        # Sunday is today
        assert week[6]["dayName"] == "CN"
        assert week[6]["isToday"] and not week[6]["isFuture"]

    def test_week_with_practice_and_rest_days(self):
        wednesday = date(2026, 11, 4)
        records = [
            {"date": "2026-11-02", "seconds": 120.0},
            {"date": "2026-11-03", "seconds": 0.0},
            {"date": "2026-11-04", "seconds": 150.0},
        ]
        rest_days = ["2026-11-03"]

        week = get_calendar_week_py(wednesday, records, rest_days)
        # T2: done
        assert week[0]["isDone"] and not week[0]["isRest"]
        assert week[0]["seconds"] == 120.0
        # T3: rest day
        assert not week[1]["isDone"] and week[1]["isRest"]
        # T4: today and done
        assert week[2]["isToday"] and week[2]["isDone"]
        assert week[2]["seconds"] == 150.0
        # T5: future, not done, not rest
        assert week[3]["isFuture"] and not week[3]["isDone"] and not week[3]["isRest"]


class TestPracticePathJavaScriptIntegrity:
    """Verify fixed calendar week helpers and the selectors other tests rely on."""

    def test_js_has_calendar_week_helper(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        assert "function getCalendarWeek(t)" in js
        assert 'const LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];' in js
        assert "extraHiddenRest" in js

    def test_js_preserves_e2e_selectors(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        # Selectors read by the Playwright tests (tests/e2e).
        for hook in (
            "today-card",
            'id="goal-select"',
            "week-dots",
            "goal-ring",
            "next-card",
            "review-card",
            "review-count",
            "overall",
            "path-part",
            "lesson-node",
            "node-coin",
            "node-flag",
            "lesson-state",
            'card.id = "node-card"',
        ):
            assert hook in js, hook

    def test_js_draws_the_mockup_parts(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        # D092: the start flag, the lesson card beside it and the scenery.
        assert "Bắt đầu" in js
        assert "rm-bubble" in js
        assert "Tiếp tục học" in js
        assert "window.rmMascots.ART[cast.name]" in js
        assert "/static/art/mascot_girl.png" in js
        assert "rm-reward-emblem" in js
        assert "i === part.lessons.length - 1" in js
        assert "rm-victory-lock" not in js
        assert "rm-adventure-finish" not in js

    def test_js_draws_the_plan_when_there_is_one(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        # D074: the roadmap follows the plan band_plan.js announces.
        assert 'addEventListener("bandplan"' in js
        assert "plan.units" in js


class TestRoadmapCompanions:
    """A companion and a tip beside every band's part (D092)."""

    def test_every_band_has_a_companion_and_a_tip(self):
        js = (STATIC_DIR / "practice_mascots.js").read_text(encoding="utf-8")
        for band in ("A1", "A2", "B1", "B2", "C1", "C2"):
            assert f"{band}: {{ name:" in js, band
        for name in ("forest", "volcano", "snow", "river", "desert", "flowers"):
            asset = STATIC_DIR / "art" / "adventure" / f"mascot-{name}-v3.webp"
            assert f"mascot-{name}-v3.webp" in js, name
            assert asset.is_file(), name

    def test_the_page_loads_the_companions_before_the_roadmap(self):
        html = (STATIC_DIR.parent / "templates" / "practice_path.html").read_text(encoding="utf-8")
        assert html.index("practice_mascots.js") < html.index("practice_path.js")


class TestPracticeStyleSheetIntegrity:
    """The page's own stylesheet: balanced, both themes, every layout."""

    def test_css_braces_are_balanced(self):
        for name in ("style.css", "practice_path.css"):
            css = (STATIC_DIR / name).read_text(encoding="utf-8")
            assert css.count("{") == css.count("}"), f"Unbalanced braces in {name}"

    def test_css_has_both_themes_and_the_week_states(self):
        css = (STATIC_DIR / "practice_path.css").read_text(encoding="utf-8")
        assert "@media (prefers-color-scheme: dark)" in css
        assert ':root[data-theme="dark"] body:has(.roadmap-page)' in css
        assert ".rm-week li.future .rm-day" in css
        assert ".rm-week li.on .rm-day" in css
        assert ".rm-week li.rest .rm-day" in css
        assert ".rm-week li.is-today" in css

    def test_css_has_the_breakpoints_of_the_mockups(self):
        css = (STATIC_DIR / "practice_path.css").read_text(encoding="utf-8")
        for width in ("1440px", "1280px", "1100px", "700px"):
            assert f"@media (max-width: {width})" in css, width

    def test_old_roadmap_styles_are_gone_from_the_shared_sheet(self):
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        for gone in (".today-card", ".next-card", ".lesson-node", ".band-plan", ".path-side"):
            assert gone not in css, gone


class TestBandPlanIntegrity:
    """The band bar of the mockup and its hooks."""

    def test_band_plan_js_has_the_bar_and_selectors(self):
        js = (STATIC_DIR / "band_plan.js").read_text(encoding="utf-8")
        assert 'id="band-from"' in js
        assert 'id="band-to"' in js
        assert 'id="band-form"' in js
        assert "Trình độ hiện tại" in js
        assert "Mục tiêu" in js
        assert "Kiểm tra trình độ" in js
        assert "Tạo lộ trình" in js
        assert 'new CustomEvent("bandplan"' in js

    def test_band_plan_css_has_the_bar(self):
        css = (STATIC_DIR / "practice_path.css").read_text(encoding="utf-8")
        assert ".rm-band-bar" in css
        assert ".rm-btn-orange" in css
        assert ".rm-btn-outline" in css
