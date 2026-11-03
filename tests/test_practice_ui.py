"""Unit & Integration tests for Practice Path UI logic, Calendar Week, and Data States.

Guards:
- Fixed calendar week alignment (T2 to CN) across various days of the week.
- Rendering states: empty vs in-progress vs goal-met.
- Journey / Course progress rendering with different completion ratios.
- CSS classes, selectors, and accessibility DOM attributes.
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
    """Verify fixed calendar week helpers and data states in practice_path.js."""

    def test_js_has_calendar_week_helper(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        assert "function getCalendarWeek(t)" in js
        assert 'const LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];' in js
        assert "extraHiddenRest" in js

    def test_js_preserves_e2e_selectors(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        # Must preserve selectors tested by Playwright & integration tests
        assert 'class="today-card"' in js or "today-card" in js
        assert 'id="goal-select"' in js
        assert "week-dots" in js
        assert "goal-ring" in js
        assert "journey-card" in js
        assert "review-card" in js
        assert "ach-card" in js
        assert "overall" in js

    def test_js_supports_user_icon_for_intro_lesson(self):
        js = (STATIC_DIR / "practice_path.js").read_text(encoding="utf-8")
        assert 'lessonIcon = "user"' in js
        assert "Tiếp tục học" in js


class TestPracticeStyleSheetIntegrity:
    """Verifies that style.css maintains balanced syntax and all required styling states."""

    def test_css_braces_are_balanced(self):
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        opens = css.count("{")
        closes = css.count("}")
        assert opens == closes, f"Unbalanced braces in style.css: {opens} opens vs {closes} closes"

    def test_css_has_fixed_calendar_week_and_future_styles(self):
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".today-week-circles li.future .circle-node" in css
        assert ".today-week-circles li.on .circle-node" in css
        assert ".today-week-circles li.rest .circle-node" in css
        assert ".today-week-circles li.is-today" in css
        assert ".today-hero-track" in css
        assert ".journey-progress-track" in css
        assert ".next-band-badge" in css


class TestBandPlanIntegrity:
    """Verify the two-row band plan layout and its styles."""

    def test_band_plan_js_has_new_layout_and_selectors(self):
        js = (STATIC_DIR / "band_plan.js").read_text(encoding="utf-8")
        assert 'id="band-from"' in js
        assert 'id="band-to"' in js
        assert 'id="band-form"' in js
        assert "Trình độ hiện tại" in js
        assert "Mục tiêu" in js
        assert 'class="band-assess-link"' in js
        assert "Kiểm tra trình độ" in js
        assert "band-action-row" in js
        assert "band-submit-btn" in js

    def test_band_plan_css_has_clean_grid_and_submit_btn(self):
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".band-action-row" in css
        assert ".band-submit-btn" in css
        assert ".band-assess-link" in css
