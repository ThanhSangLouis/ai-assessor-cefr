"""Hai màn hình nhìn vào nhiều bài cùng lúc: tiến độ cá nhân và thống kê lớp.

FR-27 và FR-29.

Điều làm hai màn hình này khác mọi màn hình còn lại là chúng TỔNG HỢP. Một báo
cáo sai thì người đọc còn nghe lại được bản ghi để tự kiểm tra; một đường xu
hướng sai thì không có gì để đối chiếu, nên nó phải tự dè dặt. Vì vậy phần lớn
các kiểm thử dưới đây không kiểm tra "có ra số không" mà kiểm tra hệ thống có
biết IM LẶNG đúng lúc hay không:

* chưa đủ bài thì không vẽ xu hướng,
* chênh lệch nhỏ hơn sai số của chính mô hình thì không gọi là tiến bộ,
* chưa có lượt duyệt nào thì không quy ra tỷ lệ đồng ý,
* và không màn hình nào rò dữ liệu của người khác.
"""

from __future__ import annotations

import importlib
import io

import numpy as np
import pytest
import soundfile as sf
from dbutil import one_school, store
from fastapi.testclient import TestClient

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def login_as(app, pseudonym: str, role: str) -> TestClient:
    from aicefr.storage.auth_repository import Role

    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    one_school(pseudonym, role)
    c = TestClient(app)
    assert (
        c.post(
            "/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD}
        ).status_code
        == 200
    )
    return c


def _wav(seconds: float = 35.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, pcm, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _submit(client: TestClient, task: str = "P3", seconds: float = 35.0) -> str:
    r = client.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", _wav(seconds), "audio/wav")},
        data={"task_id": task},
    )
    return r.json()["response_id"]


def _force_score(app, response_id: str, score: float, band: str = "B1") -> None:
    """Ghi một điểm đã biết trước vào bài đã nộp.

    Bộ nhận dạng giả lập cộng với một tín hiệu hình sin không tạo ra điểm thật;
    mà thứ đang kiểm thử ở đây là phần TỔNG HỢP, không phải phần chấm. Đi qua
    chấm thật chỉ làm kiểm thử phụ thuộc vào mô hình đang dùng là bản nào.

    Sửa cả cột lẫn `report_json`. Chỉ sửa cột là một cái bẫy đã sập một lần:
    màn hình đọc cột, còn `apply_review` đọc lại báo cáo từ JSON, nên bài trông
    như đã có điểm nhưng lượt duyệt lại ghi `old_band = NULL` và biến mất khỏi
    thống kê đồng ý.
    """
    import json

    responses = store()["response"]
    report = json.loads(responses.find_one({"response_id": response_id})["report_json"])
    assessment = report.get("assessment") or {}
    assessment["overall_0_6"] = score
    assessment["overall_band"] = band
    for criterion in assessment.get("criteria", []):
        criterion["score_0_6"] = score
        criterion["band"] = band
    report["assessment"] = assessment
    responses.update_one(
        {"response_id": response_id},
        {"$set": {"overall_0_6": score, "overall_band": band, "report_json": json.dumps(report)}},
    )


# ---------------------------------------------------------------- FR-27


def test_chua_co_bai_nao_thi_khong_bia_ra_xu_huong(app) -> None:
    body = login_as(app, "SV-001", "student").get("/api/v1/me/progress").json()
    assert body["results"] == []
    assert body["trend"]["direction"] == "chua_du_du_lieu"
    assert body["trend"]["delta"] is None


def test_it_bai_thi_noi_thang_la_chua_du_du_lieu(app) -> None:
    """Hai điểm và một đường nối giữa chúng không phải là một xu hướng."""
    c = login_as(app, "SV-001", "student")
    for score in (3.0, 4.5):
        _force_score(app, _submit(c), score)

    body = c.get("/api/v1/me/progress").json()
    assert body["trend"]["direction"] == "chua_du_du_lieu"
    assert "ít nhất" in body["trend"]["note"]


def test_chenh_lech_nho_hon_sai_so_mo_hinh_thi_khong_goi_la_tien_bo(app) -> None:
    """Kiểm thử quan trọng nhất của màn hình này.

    `ridge_resp_v2` có RMSE 0,53 trên chính tập kiểm định của nó. Vẽ mũi tên đi
    lên cho chênh lệch 0,2 điểm là nói với sinh viên rằng họ tiến bộ, trong khi
    thứ duy nhất thay đổi là hôm nào ghi âm.
    """
    c = login_as(app, "SV-001", "student")
    for score in (3.0, 3.05, 3.1, 3.12, 3.15, 3.2):
        _force_score(app, _submit(c), score)

    trend = c.get("/api/v1/me/progress").json()["trend"]
    assert trend["direction"] == "chua_ro"
    assert "sai số" in trend["note"]


def test_chenh_lech_that_su_lon_thi_moi_bao_la_di_len(app) -> None:
    c = login_as(app, "SV-001", "student")
    for score in (2.0, 2.1, 2.2, 4.3, 4.4, 4.5):
        _force_score(app, _submit(c), score)

    trend = c.get("/api/v1/me/progress").json()["trend"]
    assert trend["direction"] == "tang"
    assert trend["delta"] > 0


def test_tien_do_khong_lan_sang_nguoi_khac(app) -> None:
    """Cùng một lỗi mà bản xuất dữ liệu cá nhân từng mắc, ở một màn hình khác."""
    a = login_as(app, "SV-001", "student")
    b = login_as(app, "SV-002", "student")
    _force_score(app, _submit(a), 5.0)
    _force_score(app, _submit(b), 2.0)

    body = b.get("/api/v1/me/progress").json()
    assert len(body["results"]) == 1
    assert body["results"][0]["overall_0_6"] == 2.0


def test_tien_do_dem_rieng_so_bai_giang_vien_da_xac_nhan(app) -> None:
    """Điểm máy và điểm đã xác nhận phải phân biệt được, không gộp làm một."""
    c = login_as(app, "SV-001", "student")
    _force_score(app, _submit(c), 3.5)
    body = c.get("/api/v1/me/progress").json()
    assert body["verified_count"] == 0
    assert body["results"][0]["teacher_verified"] == 0


def test_khong_dang_nhap_thi_khong_xem_duoc_tien_do(app) -> None:
    assert TestClient(app).get("/api/v1/me/progress").status_code == 401


# ---------------------------------------------------------------- FR-29


def test_thong_ke_lop_dem_dung_so_bai_va_so_nguoi(app) -> None:
    a = login_as(app, "SV-001", "student")
    b = login_as(app, "SV-002", "student")
    _force_score(app, _submit(a), 3.5)
    _force_score(app, _submit(a, task="P4"), 4.0)
    _force_score(app, _submit(b), 2.5, band="A2")

    s = login_as(app, "GV-01", "teacher").get("/api/v1/review/stats").json()
    assert s["responses"] == 3
    assert s["scored"] == 3
    assert s["speakers"] == 2
    assert s["by_band"] == {"B1": 2, "A2": 1}


def test_so_bai_da_nop_va_so_bai_cham_duoc_la_hai_con_so_khac_nhau(app) -> None:
    """Bài máy từ chối chấm vẫn là bài đã nộp, và vẫn đang chờ giảng viên.

    Gộp hai con số làm một khiến "7 bài" đứng cạnh "13 bài chờ duyệt" trông như
    một lỗi hiển thị, trong khi thật ra chính những bài không chấm được mới là
    những bài cần người nhất.
    """
    c = login_as(app, "SV-001", "student")
    _submit(c)  # không ép điểm: máy không chấm được
    _force_score(app, _submit(c), 3.5)

    s = login_as(app, "GV-01", "teacher").get("/api/v1/review/stats").json()
    assert s["responses"] == 2
    assert s["scored"] == 1


def test_chua_ai_duyet_thi_khong_quy_ra_ty_le_dong_y(app) -> None:
    """0% và "chưa có số liệu" là hai câu hoàn toàn khác nhau.

    Trả về 0,0 sẽ đọc thành "giảng viên không bao giờ đồng ý với máy".
    """
    c = login_as(app, "SV-001", "student")
    _force_score(app, _submit(c), 3.5)

    ag = login_as(app, "GV-01", "teacher").get("/api/v1/review/stats").json()["agreement"]
    assert ag["decisions"] == 0
    assert ag["rate"] is None


def test_giu_nguyen_band_duoc_tinh_la_dong_y(app) -> None:
    student = login_as(app, "SV-001", "student")
    rid = _submit(student)
    _force_score(app, rid, 3.5)

    teacher = login_as(app, "GV-01", "teacher")
    teacher.post(f"/api/v1/review/{rid}/lock")
    r = teacher.post(
        f"/api/v1/review/{rid}",
        json={"reason": "Nghe lại, đồng ý với band mà mô hình đề xuất."},
    )
    assert r.status_code == 200, r.text

    ag = teacher.get("/api/v1/review/stats").json()["agreement"]
    assert ag["decisions"] == 1
    assert ag["band_kept"] == 1
    assert ag["rate"] == 1.0


def test_sinh_vien_khong_xem_duoc_thong_ke_lop(app) -> None:
    assert login_as(app, "SV-001", "student").get("/api/v1/review/stats").status_code == 403


def test_signed_in_pages_mark_the_current_nav_item_for_each_role(app) -> None:
    """`aria-current` on every screen of each role's own navigation.

    Since the 2026-10 redesign each role sees only its own links, so a student
    page is checked as a student and a teacher page as a teacher; and exactly
    one item is current, which /review/stats used to break by also marking
    /review.
    """
    student = login_as(app, "SV-001", "student")
    for url in ("/practice", "/", "/my-responses", "/my-progress"):
        html = student.get(url).text
        nav = html.split('class="site-nav"')[1].split("</nav>")[0]
        assert nav.count('aria-current="page"') == 1, url
    teacher = login_as(app, "GV-01", "teacher")
    for url in ("/review", "/review/stats"):
        html = teacher.get(url).text
        nav = html.split('class="site-nav"')[1].split("</nav>")[0]
        assert nav.count('aria-current="page"') == 1, url
        assert "/my-responses" not in nav and "/practice" not in nav, url


# ---------------------------------------------------------------- FR-35 (tự xoá)


def test_nguoi_hoc_tu_xoa_duoc_bai_cua_minh(app, tmp_path) -> None:
    """Quyền xoá phải tự thực hiện được, không phải xin ai.

    Erasure by participant đã có ở `/api/v1/admin/erase`, nhưng đó là việc của
    quản trị viên khi có người rút đồng thuận. Trường hợp thường ngày — một bản
    ghi nói vấp muốn bỏ đi — mà phải nhờ người khác thì quyền đó biến thành một
    hàng đợi.
    """
    c = login_as(app, "SV-001", "student")
    rid = _submit(c)

    assert c.delete(f"/api/v1/responses/{rid}").status_code == 200
    assert c.get("/api/v1/me/responses").json() == []


def test_xoa_bai_thi_xoa_ca_tep_ghi_am(app) -> None:
    """Xoá dòng mà để lại tệp thì lời hứa xoá là lời nói dối.

    Giọng nói của một người là dữ liệu cá nhân dù còn dòng nào trỏ tới nó hay không.
    """
    import pathlib

    c = login_as(app, "SV-001", "student")
    rid = _submit(c)
    path = app.state.repo.audio_path_of(rid) if hasattr(app.state, "repo") else None
    if path is None:
        from aicefr.api import main as m

        path = m.repo.audio_path_of(rid)
    assert path and pathlib.Path(path).is_file()

    c.delete(f"/api/v1/responses/{rid}")
    assert not pathlib.Path(path).exists()


def test_khong_xoa_duoc_bai_cua_nguoi_khac_va_tra_404_chu_khong_403(app) -> None:
    """403 tự nó đã là một tiết lộ: nó xác nhận mã bài đó có thật."""
    a = login_as(app, "SV-001", "student")
    b = login_as(app, "SV-002", "student")
    rid = _submit(a)

    assert b.delete(f"/api/v1/responses/{rid}").status_code == 404
    assert len(a.get("/api/v1/me/responses").json()) == 1


def test_bai_giang_vien_da_xac_nhan_thi_khong_tu_xoa_duoc(app) -> None:
    """Kết quả đã xác nhận là bản ghi của một quyết định có người chịu trách nhiệm.

    Nhật ký kiểm toán đứng sau nó phải còn trỏ tới một thứ có thật.
    """
    student = login_as(app, "SV-001", "student")
    rid = _submit(student)
    _force_score(app, rid, 3.5)

    teacher = login_as(app, "GV-01", "teacher")
    teacher.post(f"/api/v1/review/{rid}/lock")
    teacher.post(f"/api/v1/review/{rid}", json={"reason": "Nghe lại, đồng ý với máy."})

    r = student.delete(f"/api/v1/responses/{rid}")
    assert r.status_code == 409
    assert "giảng viên" in r.json()["detail"]


def test_tu_xoa_bai_duoc_ghi_vao_nhat_ky_kiem_toan(app) -> None:
    """Ghi lại rằng đã có một lần xoá, nhưng không ghi lại nội dung đã xoá."""
    c = login_as(app, "SV-001", "student")
    rid = _submit(c)
    c.delete(f"/api/v1/responses/{rid}")

    rows = login_as(app, "QT-01", "admin").get("/api/v1/audit").json()
    entry = next(r for r in rows if r["action"] == "ERASE_OWN_RESPONSE")
    assert entry["target_id"] == rid
    assert entry["actor_id"]
