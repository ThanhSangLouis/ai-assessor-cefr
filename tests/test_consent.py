"""Consent to take part in the study. Covers FR-01 and FR-35.

These tests exist because consent is the one rule where "it mostly works" is
not a defence. A recording taken without permission cannot be fixed afterwards
by deleting it, and a study that cannot show what each participant agreed to
has no data it is allowed to analyse.

The acceptance criteria are AC-C1 … AC-C4 in docs/plan/SPEC_HOAN_THIEN.md.
"""

from __future__ import annotations

import importlib
import io
from pathlib import Path

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


def _client(app, pseudonym: str = "SV-001", role: str = "student") -> TestClient:
    """Logged in, but deliberately WITHOUT signing consent."""
    from aicefr.storage.auth_repository import Role

    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(app)
    assert (
        c.post(
            "/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD}
        ).status_code
        == 200
    )
    return c


def _wav(seconds: float = 20.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, pcm, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _submit(client: TestClient):
    return client.post(
        "/api/v1/responses",
        files={"audio": ("bai.wav", _wav(), "audio/wav")},
        data={"task_id": "P3"},
    )


def _sign(client: TestClient, *, audio: bool = True, research: bool = True):
    return client.post(
        "/api/v1/me/consent",
        data={
            "audio_storage_allowed": "true" if audio else "false",
            "research_use_allowed": "true" if research else "false",
        },
    )


# ---------- AC-C1 ----------


def test_khong_co_dong_thuan_thi_khong_nop_duoc_bai(app) -> None:
    c = _client(app)
    r = _submit(c)
    assert r.status_code == 403
    assert "CONSENT_MISSING" in r.text


def test_khong_co_dong_thuan_thi_khong_ghi_tep_nao_xuong_dia(app, tmp_path) -> None:
    """The check runs before the upload is streamed to disk, not after.

    Writing the recording and then refusing is exactly the order that makes the
    refusal meaningless: the file already exists.
    """
    c = _client(app)
    _submit(c)
    uploads = Path(tmp_path) / "uploads"
    assert not uploads.exists() or not list(uploads.iterdir())


def test_chi_cho_phep_nghien_cuu_ma_khong_cho_luu_ban_ghi_thi_van_bi_chan(app) -> None:
    """Refusing storage is a valid choice, and it means no submission.

    Not an error on the student's part -- there is simply nothing the system can
    do with a recording it may not keep.
    """
    c = _client(app)
    _sign(c, audio=False, research=True)
    assert _submit(c).status_code == 403


# ---------- AC-C2 ----------


def test_dong_thuan_luu_ban_ghi_nhung_tu_choi_nghien_cuu_van_cham_duoc(app) -> None:
    c = _client(app)
    _sign(c, audio=True, research=False)
    r = _submit(c)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "QUEUED"


def test_ban_ghi_tu_choi_nghien_cuu_khong_vao_tap_xuat(app) -> None:
    student = _client(app)
    _sign(student, audio=True, research=False)
    assert _submit(student).status_code == 202

    admin = _client(app, "QT-01", "admin")
    r = admin.get("/api/v1/admin/export/research.json")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accounts_allowing_research"] == 0
    assert body["row_count"] == 0


def test_tap_xuat_nghien_cuu_khong_chua_ban_chep_loi(app) -> None:
    """The export answers "does the machine agree with the raters".

    That question needs numbers. Shipping transcripts around adds risk and
    answers nothing, so the export must not carry them even for people who did
    consent to research use.
    """
    student = _client(app)
    _sign(student, audio=True, research=True)
    assert _submit(student).status_code == 202

    admin = _client(app, "QT-01", "admin")
    body = admin.get("/api/v1/admin/export/research.json").json()
    assert body["row_count"] == 1
    assert all("transcript" not in row for row in body["rows"])


# ---------- AC-C3 ----------


def test_rut_dong_thuan_thi_khong_nop_them_duoc_nhung_van_xem_duoc_bai_cu(app) -> None:
    c = _client(app)
    _sign(c)
    first = _submit(c)
    assert first.status_code == 202
    rid = first.json()["response_id"]

    assert c.post("/api/v1/me/consent/withdraw").json()["withdrawn"] is True

    assert _submit(c).status_code == 403
    assert c.get(f"/api/v1/responses/{rid}").status_code == 200


def test_rut_dong_thuan_thi_bien_mat_khoi_tap_xuat_nghien_cuu(app) -> None:
    student = _client(app)
    _sign(student)
    assert _submit(student).status_code == 202

    admin = _client(app, "QT-01", "admin")
    assert admin.get("/api/v1/admin/export/research.json").json()["row_count"] == 1

    student.post("/api/v1/me/consent/withdraw")
    after = admin.get("/api/v1/admin/export/research.json").json()
    assert after["row_count"] == 0
    assert after["accounts_allowing_research"] == 0


def test_rut_khi_chua_tung_ky_thi_khong_bao_loi(app) -> None:
    c = _client(app)
    assert c.post("/api/v1/me/consent/withdraw").json()["withdrawn"] is False


# ---------- AC-C4 ----------


def test_nhat_ky_kiem_toan_ghi_ca_lan_ky_va_lan_rut(app) -> None:
    student = _client(app)
    _sign(student)
    student.post("/api/v1/me/consent/withdraw")

    admin = _client(app, "QT-01", "admin")
    actions = [row["action"] for row in admin.get("/api/v1/audit").json()]
    assert "consent.sign" in actions
    assert "consent.withdraw" in actions


def test_phien_ban_van_ban_dong_thuan_duoc_luu_theo_tung_ban_ghi(app) -> None:
    """Editing the consent page later must not rewrite what someone already signed.

    So the version is copied into the row at signing time, and read back from
    there -- never looked up from whatever the current wording happens to be.
    """
    from aicefr.storage.consent_repository import CURRENT_CONSENT_VERSION, ConsentRepository

    repo = ConsentRepository("aicefr.db")
    repo.sign(
        "acc-1", audio_storage_allowed=True, research_use_allowed=True, consent_version="dt-v0"
    )
    keep = repo.current("acc-1")
    assert keep is not None and keep.consent_version == "dt-v0" != CURRENT_CONSENT_VERSION


def test_ky_lai_thi_ban_cu_duoc_danh_dau_da_rut_chu_khong_bi_ghi_de(app) -> None:
    """History has to survive a change of mind, or it is not history."""
    from aicefr.storage.consent_repository import ConsentRepository

    repo = ConsentRepository("aicefr.db")
    repo.sign("acc-1", audio_storage_allowed=True, research_use_allowed=False)
    repo.sign("acc-1", audio_storage_allowed=True, research_use_allowed=True)

    history = repo.history("acc-1")
    assert len(history) == 2
    assert history[0].withdrawn_at is not None
    assert history[1].withdrawn_at is None
    assert repo.current("acc-1").research_use_allowed is True


# ---------- màn hình ----------


def test_trang_dong_thuan_hien_thi_duoc(app) -> None:
    c = _client(app)
    r = c.get("/consent")
    assert r.status_code == 200
    assert "Đồng thuận" in r.text


def test_trang_dong_thuan_khong_gop_hai_lua_chon_thanh_mot_nut(app) -> None:
    """Two separate permissions, two separate checkboxes.

    A single "I agree to everything" control makes it impossible to show later
    which of the two things the participant actually meant.
    """
    c = _client(app)
    html = c.get("/consent").text
    assert 'id="audio"' in html
    assert 'id="research"' in html


# ---------------------------------------------------------------- nói trước, không nói sau


def test_trang_nop_bai_co_cho_bao_chua_ky_dong_thuan(app) -> None:
    """Máy chủ từ chối là đúng, nhưng nó từ chối quá muộn.

    Người học chọn đề, ghi âm một phút, bấm nộp — rồi mới biết là chưa ký đồng
    thuận. Thông tin đó có sẵn ngay lúc mở trang. Ô thông báo phải tồn tại
    trong trang để `submit.js` điền vào, chứ không dựng ra giữa chừng.
    """
    html = _client(app).get("/").text
    assert 'id="consent-gate"' in html


def test_submit_js_hoi_trang_thai_dong_thuan_luc_tai_trang(app) -> None:
    """Nếu màn hình không hỏi thì ô thông báo ở trên mãi mãi rỗng."""
    from pathlib import Path

    js = (
        Path(__file__).resolve().parents[1] / "src" / "aicefr" / "api" / "static" / "submit.js"
    ).read_text(encoding="utf-8")
    assert "/api/v1/me/consent" in js
    assert "consent-gate" in js


def test_may_submit_phan_biet_chua_ky_voi_da_ky_ma_tu_choi_luu(app) -> None:
    """Hai tình huống khác nhau, và màn hình nói khác nhau cho từng tình huống.

    "Chưa ký gì cả" là quên. "Đã ký nhưng không cho lưu bản ghi" là một lựa
    chọn có chủ ý, nên không được nói với người ta như thể họ quên.
    """
    c = _client(app)

    chua_ky = c.get("/api/v1/me/consent").json()
    assert chua_ky["signed"] is False
    assert chua_ky["may_submit"] is False

    c.post(
        "/api/v1/me/consent",
        data={"audio_storage_allowed": "false", "research_use_allowed": "true"},
    )
    da_ky = c.get("/api/v1/me/consent").json()
    assert da_ky["signed"] is True
    assert da_ky["audio_storage_allowed"] is False
    assert da_ky["may_submit"] is False
