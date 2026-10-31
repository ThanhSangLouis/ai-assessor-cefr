"""Fewer sidebar entries, each shown when it has something in it (D068).

A student's history and progress share one entry, "Kết quả"; "Bài được giao"
appears once the student is in a class and "Chấm mù" once a blind sheet waits.
The class statistics and the path insights share "Thống kê", and the two
measurements made for the study (teacher time, teacher-machine agreement) are
read by administrators only.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from aicefr.storage.auth_repository import Role

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def m(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main

    importlib.reload(main)
    return main


def login_as(m, pseudonym: str, role: str = "student") -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(m.app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def sidebar(page: str) -> str:
    return page.split('class="site-nav')[1].split("</nav>")[0]


def test_a_student_has_one_results_entry_for_history_and_progress(m):
    student = login_as(m, "SV-N01")
    for url, tab in (("/my-progress", "/my-progress"), ("/my-responses", "/my-responses")):
        page = student.get(url).text
        nav = sidebar(page)
        assert "Kết quả" in nav and "Tiến độ" not in nav and "Bài của tôi" not in nav
        assert nav.count('aria-current="page"') == 1
        subnav = page.split('class="subnav"')[1].split("</nav>")[0]
        assert f'href="{tab}" aria-current="page"' in subnav


def test_assignments_appear_only_for_a_student_in_a_class(m):
    student = login_as(m, "SV-N02")
    nav = sidebar(student.get("/practice").text)
    assert 'href="/my-assignments" data-nav-if="in_class" hidden' in nav
    assert student.get("/api/v1/me/badges").json()["in_class"] is False

    teacher = login_as(m, "GV-N02", "teacher")
    made = teacher.post("/api/v1/classes", json={"name": "Lớp thử"}).json()
    r = teacher.post(f"/api/v1/classes/{made['class_id']}/members", json={"pseudonyms": ["SV-N02"]})
    assert r.status_code == 200, r.text
    assert student.get("/api/v1/me/badges").json()["in_class"] is True
    # On its own page the entry is shown and current, whatever the badge says.
    nav = sidebar(student.get("/my-assignments").text)
    assert 'href="/my-assignments" data-nav-if="in_class" aria-current="page"' in nav


def test_blind_rating_appears_only_while_sheets_wait(m):
    teacher = login_as(m, "GV-N03", "teacher")
    nav = sidebar(teacher.get("/review").text)
    assert 'href="/rate" data-nav-if="ratings" hidden' in nav
    assert "Thống kê" in nav and "Thống kê lớp" not in nav


def test_practice_tasks_lead_to_the_lesson_path(m):
    student = login_as(m, "SV-N04")
    r = student.get("/practice/PR-FLU-B1", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/practice"
    practice = student.get("/practice").text
    assert 'id="my-plan"' not in practice  # learners no longer compose their own path


def test_the_study_measurements_are_for_administrators_only(m):
    teacher = login_as(m, "GV-N05", "teacher")
    assert 'id="teacher-time"' not in teacher.get("/review/stats").text
    admin = login_as(m, "QT-N05", "admin")
    assert 'id="teacher-time"' in admin.get("/review/stats").text
    for c in (teacher, admin):
        insights = c.get("/teach/insights").text
        assert 'href="/teach/insights" aria-current="page"' in insights
        assert 'href="/review/stats" aria-current="page"' in insights  # sidebar: Thống kê


def test_the_feedback_study_screen_no_longer_starts_one(m):
    """D068: a study holds feedback back from real learners; only closing remains."""
    admin = login_as(m, "QT-N06", "admin")
    page = admin.get("/admin/study").text
    assert 'id="study-form"' not in page and "Đã ngừng" in page
    assert "Thực nghiệm phản hồi (đã ngừng)" in admin.get("/admin").text
