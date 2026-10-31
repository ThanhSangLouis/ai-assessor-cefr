"""Presentation layer tests. Cross-reference docs/web/SPEC_WEB.md section 9.

The three screens used to live inside Python strings with no test touching them, so all
three could break completely while the test suite stayed green.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aicefr.api.main import app
from aicefr.api.web import TEMPLATE_DIR
from aicefr.qc import audio_qc

client = TestClient(app)

PAGES = [
    "/",
    "/login",
    "/review",
    "/review/stats",
    "/report/abc123",
    "/progress/abc123",
    "/my-responses",
    "/my-progress",
    "/admin",
    "/practice",
    "/practice/PR-FLU-A2",
    "/practice/results/abc123",
]

# SRS section 11.3 forbids any wording that implies the system issues a certificate or
# an official result. Only AFFIRMATIVE forms are listed here: a negation inside a
# mandatory disclaimer such as "Khong cap chung chi" is correct, not a violation.
FORBIDDEN_PHRASES = [
    "cấp chứng chỉ CEFR",
    "chứng chỉ CEFR chính thức",
    "kết quả chính thức",
    "đạt/không đạt",
    "certified",
]


@pytest.mark.parametrize("url", PAGES)
def test_every_page_renders(url: str) -> None:
    r = client.get(url)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


@pytest.mark.parametrize("url", PAGES)
def test_every_page_carries_required_disclaimer(url: str) -> None:
    """A study-support tool, no certificate issued, the teacher has the final say."""
    t = client.get(url).text
    assert "Không cấp chứng chỉ" in t
    assert "Giảng viên quyết định cuối cùng" in t


@pytest.mark.parametrize("path", sorted(Path(TEMPLATE_DIR).glob("*.html")))
def test_templates_contain_no_forbidden_phrases(path: Path) -> None:
    content = path.read_text(encoding="utf-8").lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.lower() not in content, f"{path.name} contains forbidden phrase {phrase!r}"


def test_displayed_thresholds_match_qc_module() -> None:
    """The page must read its thresholds from the QC module rather than hardcoding them.

    Hardcoded values mean that every threshold change forgets the display, and the user
    reads one number while the machine applies another.
    """
    # The submission page, where a student reads them before recording; the
    # product page no longer quotes them (D068).
    import importlib

    from aicefr.api import main
    from aicefr.storage.auth_repository import Role

    importlib.reload(main)  # this test's own store, as conftest prepared it
    main.app.state.auth_repo.create_account("SV-QC1", "matkhau-kiem-thu", Role.STUDENT)
    student = TestClient(main.app)
    body = {"pseudonym": "SV-QC1", "password": "matkhau-kiem-thu"}
    assert student.post("/api/v1/auth/login", json=body).status_code == 200
    t = student.get("/").text
    assert f"{int(audio_qc.MIN_DURATION_S)} đến {int(audio_qc.MAX_DURATION_S)} giây" in t
    assert f"{audio_qc.MAX_BYTES // (1024 * 1024)} MiB" in t


def test_static_files_are_served() -> None:
    for path in ("/static/style.css", "/static/submit.js", "/static/report.js"):
        assert client.get(path).status_code == 200


def test_no_external_resources_embedded() -> None:
    """W-NFR-2: the lab machines at school may have outside network access blocked.

    If a font or a script fails to load during the demo in front of the committee, the
    session is ruined.
    """
    for url in PAGES:
        t = client.get(url).text
        assert "http://" not in t
        assert "https://" not in t


def test_report_page_carries_the_response_id() -> None:
    t = client.get("/report/xyz789").text
    assert "xyz789" in t


def test_class_stats_page_is_not_mistaken_for_a_response_id() -> None:
    """Route ordering, pinned.

    `/review/{response_id}` and `/review/stats` are both valid matches for
    this path, and FastAPI takes whichever was declared first. With the
    parameterised route ahead of it, the statistics screen silently renders as
    "duyệt bài stats" and then "không tìm thấy bài này" -- a page that is
    wrong in a way no 404 or exception ever reports.
    """
    body = client.get("/review/stats").text
    assert "Thống kê lớp" in body
    assert "Duyệt bài" not in body


def test_trang_nop_bai_danh_dau_muc_dieu_huong_dang_xem() -> None:
    """`aria-current` is how a screen reader answers "where am I".

    Without it the navigation is a row of identical links whose only cue is a
    colour a screen reader cannot see. Checked here on the one page whose nav
    item is visible to a signed-out visitor; the signed-in pages are covered in
    tests/test_progress_and_stats.py, where there is an account to sign in as.
    """
    assert 'aria-current="page"' in client.get("/").text


def test_khong_con_tieu_de_h3_mo_coi_trong_trang_thai_rong() -> None:
    """An empty state is usually the first thing under the page h1.

    An h3 there leaves a hole in the heading outline: someone moving by
    headings hears level 1, then level 3, and has to wonder what was skipped.
    """
    static = Path(__file__).resolve().parents[1] / "src" / "aicefr" / "api" / "static"
    for js in static.glob("*.js"):
        text = js.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines()):
            if "empty-mark" not in line:
                continue
            window = "\n".join(text.splitlines()[i : i + 4])
            assert "<h3>" not in window, f"{js.name}:{i + 1} dùng h3 trong trạng thái rỗng"


def test_tep_tinh_deu_mang_phien_ban_de_khong_dung_ban_cu_trong_cache() -> None:
    """A cached script is an old screen talking to a new API.

    This is not hypothetical: a screen here kept rendering without a block that
    was demonstrably in the file on disk and in the HTTP response, because the
    browser never asked again. The version query makes a changed file a
    different URL.
    """
    # The sign-in page: the one page every visitor loads, with a script of its own.
    body = client.get("/login").text
    assert "/static/login.js?v=" in body
    assert "/static/style.css?v=" in body


def test_asset_thieu_tep_van_tra_ve_duong_dan_chu_khong_no() -> None:
    """A 404 on a script is a bug to fix, not a reason for the page to fail."""
    from aicefr.api.web import asset

    assert asset("khong-co-that.js") == "/static/khong-co-that.js"


def test_moi_ma_ly_do_deu_co_ten_tieng_viet_tren_man_duyet() -> None:
    """A teacher reading a raw enum name is reading the code, not the system.

    Pinned as a test because the failure mode is silent: adding a ReasonCode
    without adding its name leaves the screen showing SCORE_AGGREGATED in the
    middle of Vietnamese prose, and nothing breaks.
    """
    import re

    from aicefr.contracts import ReasonCode

    # The names live in common.js (window.ui.REASON_NAMES), shared by the queue
    # and the review screen since the 2026-10 interface redesign.
    js = (
        Path(__file__).resolve().parents[1] / "src" / "aicefr" / "api" / "static" / "common.js"
    ).read_text(encoding="utf-8")
    named = set(re.findall(r'^\s*([A-Z_]+):\s*"', js, re.M))
    missing = sorted(r.value for r in ReasonCode if r.value not in named)
    assert not missing, f"common.js chưa đặt tên tiếng Việt cho: {missing}"


def test_kieu_in_khong_an_toan_bo_nut() -> None:
    """`button { display: none }` trong `@media print` từng xoá mất bằng chứng.

    Thẻ bằng chứng và ô cửa sổ đều là `<button>`, vì bấm vào chúng là tua bản
    ghi tới đúng chỗ đó. Một quy tắc ẩn mọi `button` khi in vì thế xoá luôn phần
    có ích nhất của báo cáo khỏi mọi bản in và mọi tệp PDF — mà không có gì báo
    lỗi, vì trên màn hình vẫn đúng.
    """
    import re

    css = (
        Path(__file__).resolve().parents[1] / "src" / "aicefr" / "api" / "static" / "style.css"
    ).read_text(encoding="utf-8")
    block = css[css.index("@media print") :]
    for rule in re.findall(r"([^{}]+)\{[^{}]*display:\s*none[^{}]*\}", block):
        selectors = [s.strip() for s in rule.split(",")]
        assert "button" not in selectors, "kiểu in đang ẩn mọi <button>, kể cả thẻ bằng chứng"


def test_login_page_says_why_google_is_missing_outside_production() -> None:
    """Without the Google keys the button is hidden; on a developer's machine the
    page says why, so a missing key is not taken for a broken feature."""
    t = client.get("/login").text
    assert 'id="google-off"' in t
    assert "AICEFR_GOOGLE_CLIENT_ID" in t
