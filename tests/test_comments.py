"""Feedback sentences and practice priorities. Covers FR-25 and FR-26.

The property under test is not "does it produce nice text". It is: **every
sentence the report shows can be traced back to a measurement in that same
report**, and **advice disappears when the measurement behind it is not
trusted**. Those two are what separate feedback from generated filler.
"""

from __future__ import annotations

import pytest
from conftest import feature_set

from aicefr.contracts import Criterion, Evidence, FeatureSet, ReasonCode
from aicefr.report.comments import MAX_PRIORITIES, CommentBuilder

FEATURES = {
    "n_words": 90.0,
    "words_per_sec": 1.6,
    "total_dur": 55.0,
    "ttr": 0.55,
    "vad_pause_per_min": 14.0,
    "asr_conf_mean": 0.86,
}


def _features(**over) -> FeatureSet:
    values = {**FEATURES, **over}
    return feature_set(values)


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            evidence_id="ev-01",
            criterion=Criterion.FLUENCY,
            kind="pause",
            start_s=3.0,
            end_s=5.2,
            note="Ngừng 2,2 giây giữa chừng.",
        ),
        Evidence(
            evidence_id="ev-02",
            criterion=Criterion.RANGE,
            kind="lexical",
            note="Tỷ lệ từ khác nhau thấp.",
        ),
    ]


# ---------- FR-25 ----------


def test_moi_cau_nhan_xet_deu_tro_toi_bang_chung_co_that() -> None:
    """AC-25.1. A citation that points at nothing is worse than no citation."""
    ev = _evidence()
    ids = {e.evidence_id for e in ev}
    comments = CommentBuilder().comments(_features(), ev, 0.86, [])

    assert comments
    for c in comments:
        assert c.evidence_refs, f"câu không có bằng chứng: {c.text}"
        assert set(c.evidence_refs) <= ids


def test_khong_co_bang_chung_thi_khong_sinh_cau_nao() -> None:
    """Three honest sentences beat four where the fourth is decoration."""
    assert CommentBuilder().comments(_features(), [], 0.86, []) == []


def test_do_tin_cay_thap_thi_noi_ro_can_giang_vien_xac_nhan() -> None:
    """AC-25.2."""
    comments = CommentBuilder().comments(_features(asr_conf_mean=0.30), _evidence(), 0.30, [])
    joined = " ".join(c.text for c in comments)
    assert "giảng viên xác nhận" in joined


def test_khong_co_doan_noi_thi_khong_bia_cau_ve_do_troi_chay() -> None:
    """AC-25.3.

    A recording with no speech segments has no pause rate. Saying "0 lần ngừng
    mỗi phút" would read as praise for a recording that contains nothing.
    """
    features = _features()
    features = feature_set(
        {f.name: f.value for f in features.items if f.name != "vad_pause_per_min"}
    )
    comments = CommentBuilder().comments(features, _evidence(), 0.86, [])
    assert all("ngừng mỗi phút" not in c.text for c in comments)


def test_lech_phien_ban_nhan_dang_thi_bao_cao_noi_ro_dieu_do() -> None:
    comments = CommentBuilder().comments(
        _features(), _evidence(), 0.86, [ReasonCode.ASR_VERSION_MISMATCH]
    )
    assert any("khác bộ đã dùng lúc huấn luyện" in c.text for c in comments)


# ---------- FR-26 ----------


def test_uu_tien_chinh_la_dac_trung_keo_diem_xuong_nhieu_nhat() -> None:
    """AC-26.1, in the model's own terms: most negative contribution first."""
    contributions = {
        "ttr": -0.42,
        "vad_pause_per_min": -0.11,
        "n_words": +0.30,  # helping, must never appear as something to fix
    }
    ps = CommentBuilder().priorities(contributions, 0.86)

    assert [p.feature_name for p in ps] == ["ttr", "vad_pause_per_min"]
    assert ps[0].impact == pytest.approx(0.42)


def test_khong_bao_gio_qua_hai_uu_tien() -> None:
    """AC-26.2. Five things to fix is a list nobody starts."""
    contributions = {
        "ttr": -0.9,
        "vad_pause_per_min": -0.8,
        "n_words": -0.7,
        "asr_conf_mean": -0.6,
        "mean_word_len": -0.5,
    }
    assert len(CommentBuilder().priorities(contributions, 0.86)) == MAX_PRIORITIES


def test_do_tin_cay_thap_thi_khong_dua_uu_tien_nao() -> None:
    """AC-26.3. Advice from a measurement we distrust is worse than silence."""
    assert CommentBuilder().priorities({"ttr": -0.9}, 0.30) == []


def test_dac_trung_dang_giup_thi_khong_bi_liet_ke_de_sua() -> None:
    assert CommentBuilder().priorities({"ttr": +0.5, "n_words": +0.2}, 0.86) == []


def test_lech_khong_dang_ke_thi_khong_dua_loi_khuyen() -> None:
    """Advice that appears no matter what you do is advice nobody acts on."""
    assert CommentBuilder().priorities({"ttr": -0.01}, 0.86) == []


def test_hai_do_do_cung_mot_loi_khuyen_thi_chi_hien_mot_lan() -> None:
    """`vad_silence_ratio` and `vad_pause_per_min` both mean "you paused a lot"."""
    ps = CommentBuilder().priorities({"log_uniq": -0.5, "ttr": -0.4}, 0.86)
    assert len({p.text for p in ps}) == len(ps)


def test_scorer_khong_giai_thich_duoc_thi_bao_cao_khong_co_uu_tien() -> None:
    """A scorer that cannot explain itself must not make the report invent one."""
    assert CommentBuilder().priorities({}, 0.86) == []


# ---------- toàn tuyến ----------


def test_bao_cao_that_co_nhan_xet_va_uu_tien(tone, sr) -> None:
    """End to end through the real pipeline, not a hand-built Assessment.

    A unit test on the builder cannot catch the wiring being absent, which is
    exactly the class of bug that let `SCORE_NEAR_BOUNDARY` disappear before.
    """
    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor

    report = ResponseProcessor(asr_engine=FakeAsrEngine()).process(
        ProcessingRequest(
            response_id="r-1",
            speaker_id="SV-001",
            task_id="P3",
            audio_path="x.wav",
            prompt_version="v1",
            config_version="v1",
        ),
        tone,
        sr,
    )
    a = report.assessment
    assert a is not None
    assert a.comments, "pipeline không gắn nhận xét vào báo cáo"
    ids = {e.evidence_id for e in a.evidence}
    for c in a.comments:
        assert set(c.evidence_refs) <= ids


def test_every_feature_name_advice_can_emit_is_a_real_feature():
    """`Priority.feature_name` la mot THAM CHIEU THEO TEN, nen phai kiem o day.

    Lop `Priority` khong tu kiem duoc: danh sach dac trung nam trong tep mo
    hinh, khong nam trong ma. Nhung `ADVICE` la noi DUY NHAT sinh ra cac ten
    do, nen doi chieu khoa cua no voi `feature_order` cua tep mo hinh la cho
    dat duoc phep kiem -- va no bat duoc dung cai loi "con tro treo": mot loi
    khuyen tro toi mot dac trung khong con ton tai sau khi doi tep mo hinh.
    """
    from aicefr.report.comments import ADVICE
    from aicefr.scoring.scorer import load_model

    known = set(load_model()["feature_order"])
    treo = sorted(set(ADVICE) - known)
    assert not treo, f"lời khuyên trỏ tới đặc trưng không có trong tệp mô hình: {treo}"
