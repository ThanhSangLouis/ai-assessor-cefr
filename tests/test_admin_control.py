"""Runtime control an administrator has, and its limits. FR-08, FR-34, FR-36.

Three capabilities that all share one shape: they change what the system does
*to data already collected*, so each one has to be attributable, reversible in
meaning, and unable to rewrite the past.
"""

from __future__ import annotations

import importlib
import io

import numpy as np
import pytest
import soundfile as sf
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
    c = TestClient(app)
    assert (
        c.post(
            "/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/v1/me/consent",
            data={"audio_storage_allowed": "true", "research_use_allowed": "true"},
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


def _submit(client: TestClient, seconds: float = 35.0):
    return client.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", _wav(seconds), "audio/wav")},
        data={"task_id": "P3"},
    )


# ---------------------------------------------------------------- FR-34


def test_xuat_du_lieu_ca_nhan_co_du_so_bai(app) -> None:
    """AC-34.1."""
    c = login_as(app, "SV-001", "student")
    _submit(c)
    _submit(c)

    body = c.get("/api/v1/me/export.json").json()
    assert body["response_count"] == 2
    assert len(body["responses"]) == 2


def test_xuat_du_lieu_ca_nhan_khong_lan_sang_nguoi_khac(app) -> None:
    """AC-34.2. The bug this guards against is one the project already had once."""
    a = login_as(app, "SV-001", "student")
    b = login_as(app, "SV-002", "student")
    _submit(a)
    _submit(b)

    body = b.get("/api/v1/me/export.json").json()
    assert body["response_count"] == 1
    assert all(r["response_id"] != "" for r in body["responses"])
    assert body["speaker_id"] == "SV-002"


def test_moi_truong_du_lieu_deu_co_giai_thich_muc_dich(app) -> None:
    """AC-34.3.

    A person has the right to know *why* their voice is kept, not only that it
    is. An export without this block answers the easy half of the question.
    """
    c = login_as(app, "SV-001", "student")
    _submit(c)
    body = c.get("/api/v1/me/export.json").json()

    fields = body["fields"]
    for key in ("speaker_id", "consent", "transcript", "features", "review_history", "audio"):
        assert key in fields and fields[key].strip()


def test_xuat_du_lieu_co_ca_lich_su_dong_thuan(app) -> None:
    c = login_as(app, "SV-001", "student")
    c.post("/api/v1/me/consent/withdraw")
    body = c.get("/api/v1/me/export.json").json()

    assert len(body["consent"]) == 1
    assert body["consent"][0]["withdrawn_at"] is not None


def test_khong_dang_nhap_thi_khong_xuat_duoc(app) -> None:
    assert TestClient(app).get("/api/v1/me/export.json").status_code == 401


# ---------------------------------------------------------------- FR-36


def test_kich_hoat_mo_hinh_khong_ton_tai_tra_404(app) -> None:
    """AC-36.3."""
    admin = login_as(app, "QT-01", "admin")
    r = admin.post("/api/v1/admin/models/khong-co-that/activate")
    assert r.status_code == 404
    assert admin.get("/api/v1/admin/config").status_code == 200  # hệ thống vẫn chạy


def test_kich_hoat_mo_hinh_sai_don_vi_suy_luan_bi_tu_choi(app) -> None:
    """`ridge_v3` scores whole exam sittings, not single responses.

    It also reports a *higher* correlation, which is exactly why activating it
    has to be refused rather than left to an administrator's judgement.
    """
    from aicefr.scoring.scorer import MODEL_DIR

    if not (MODEL_DIR / "ridge_v3.json").is_file():
        pytest.skip("không có artifact ridge_v3 trong repo")
    admin = login_as(app, "QT-01", "admin")
    assert admin.post("/api/v1/admin/models/ridge_v3/activate").status_code == 409


def test_kich_hoat_lai_chinh_mo_hinh_dang_dung_van_duoc_ghi_nhat_ky(app) -> None:
    """AC-36.4: the log answers "which model graded Tuesday's batch"."""
    admin = login_as(app, "QT-01", "admin")
    r = admin.post("/api/v1/admin/models/ridge_resp_v1/activate")
    assert r.status_code == 200, r.text
    assert r.json()["active_model"] == "ridge_resp_v1"

    actions = [row["action"] for row in admin.get("/api/v1/audit").json()]
    assert "model.activate" in actions


def test_bao_cao_da_luu_giu_nguyen_phien_ban_mo_hinh_cu(app) -> None:
    """AC-36.2. Re-reading an old report must not re-attribute it."""
    student = login_as(app, "SV-001", "student")
    rid = _submit(student).json()["response_id"]
    before = student.get(f"/api/v1/responses/{rid}").json()

    login_as(app, "QT-01", "admin").post("/api/v1/admin/models/ridge_resp_v1/activate")

    after = student.get(f"/api/v1/responses/{rid}").json()
    assert after == before


def test_giang_vien_khong_kich_hoat_duoc_mo_hinh(app) -> None:
    teacher = login_as(app, "GV-01", "teacher")
    assert teacher.post("/api/v1/admin/models/ridge_resp_v1/activate").status_code == 403


# ---------------------------------------------------------------- FR-08


def test_doi_nguong_qc_thi_bump_phien_ban_va_ghi_nguoi_doi(app) -> None:
    admin = login_as(app, "QT-01", "admin")
    r = admin.post("/api/v1/admin/config", json={"min_duration_s": 15.0})
    assert r.status_code == 200, r.text
    assert r.json()["qc_config_version"] != "qc-v1"

    cfg = admin.get("/api/v1/admin/config").json()
    assert cfg["duration_s"]["reject_below"] == 15.0
    assert cfg["changed_by"] == "QT-01"
    assert cfg["changed_at"]


def test_nguong_moi_duoc_ap_ngay_cho_bai_nop_sau_do(app) -> None:
    """The point of the feature: a 25-second recording that was REVIEW becomes PASS.

    Checked through a submitted response rather than through the config
    endpoint, because "the number changed in the table" and "the number changed
    the decision" are different claims.
    """
    student = login_as(app, "SV-001", "student")
    admin = login_as(app, "QT-01", "admin")

    rid = _submit(student, seconds=25.0).json()["response_id"]
    before = student.get(f"/api/v1/responses/{rid}").json()
    assert before["qc"]["qc_status"] == "REVIEW"

    admin.post("/api/v1/admin/config", json={"review_duration_s": 20.0})

    rid2 = _submit(student, seconds=25.0).json()["response_id"]
    after = student.get(f"/api/v1/responses/{rid2}").json()
    assert after["qc"]["qc_status"] == "PASS"
    assert after["qc"]["qc_config_version"] != before["qc"]["qc_config_version"]


def test_nguong_ngoai_khoang_cho_phep_bi_tu_choi(app) -> None:
    """A silence ratio of 5.0 is not a stricter rule, it is a rule that never fires."""
    admin = login_as(app, "QT-01", "admin")
    assert admin.post("/api/v1/admin/config", json={"max_silence_ratio": 5.0}).status_code == 422


def test_thu_tu_nguong_thoi_luong_sai_bi_tu_choi(app) -> None:
    """review_below under reject_below would disable the middle outcome entirely."""
    admin = login_as(app, "QT-01", "admin")
    r = admin.post("/api/v1/admin/config", json={"review_duration_s": 5.0})
    assert r.status_code == 422
    assert "thứ tự" in r.json()["detail"]


def test_khong_sua_duoc_truong_ngoai_danh_sach(app) -> None:
    admin = login_as(app, "QT-01", "admin")
    assert admin.post("/api/v1/admin/config", json={"silence_dbfs": -10.0}).status_code == 422


def test_giang_vien_khong_doi_duoc_nguong(app) -> None:
    teacher = login_as(app, "GV-01", "teacher")
    assert teacher.post("/api/v1/admin/config", json={"min_duration_s": 15.0}).status_code == 403


def test_trang_nop_bai_hien_dung_nguong_dang_ap_dung(app) -> None:
    """The screen and the rule must not drift apart.

    Before FR-08 the page read module constants; once thresholds became
    editable, that would have shown a student 20 seconds while the machine
    applied 15.
    """
    admin = login_as(app, "QT-01", "admin")
    admin.post("/api/v1/admin/config", json={"min_duration_s": 12.0})

    html = login_as(app, "SV-001", "student").get("/").text
    assert "12" in html
