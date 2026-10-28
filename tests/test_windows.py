"""Cutting a long recording into scorable windows. FR-05a, the duration ceiling.

The reason this module exists at all is a measurement limit, not a product wish:
`ridge_resp_v2` was fitted on responses of 26.7-60.7 seconds, so a 95-second
recording has no score the model can defend. Cutting it into pieces the model
DOES know is the only honest way to give the speaker a number -- and the tests
below are mostly about the ways that cut can quietly produce a wrong one.

Three invariants carry the whole design, and each has a test that fails loudly
rather than a comment that asks to be trusted:

1. every window ends up inside the model's trained range,
2. the windows tile the recording exactly -- no gap, no overlap,
3. the aggregated score is labelled as aggregated and never reaches a student
   without a teacher.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from aicefr.contracts import AnalysisWindow, ProcessingRequest, ReasonCode, Status
from aicefr.scoring.windows import (
    MAX_WINDOW_S,
    MAX_WINDOWS,
    MIN_TAIL_S,
    MIN_WINDOW_S,
    clip_segments,
    plan_windows,
)


def _even_segments(total: float, on: float = 8.0, off: float = 1.2) -> list[tuple[float, float]]:
    """Speech with a regular pause every `on` seconds, so cuts have somewhere to land."""
    out, t = [], 0.0
    while t < total:
        out.append((round(t, 3), round(min(t + on, total), 3)))
        t += on + off
    return out


# ---------------------------------------------------------------- kế hoạch cắt


@pytest.mark.parametrize("total", [20.0, 45.0, 60.0])
def test_bai_ngan_thi_khong_cat(total: float) -> None:
    """Anything the model can already score is left exactly as it is.

    Cutting a 45-second response would replace one measurement the model was
    trained on with two it was not -- strictly worse, for no gain.
    """
    windows = plan_windows(total, _even_segments(total))
    assert len(windows) == 1
    assert (windows[0].start_s, windows[0].end_s) == (0.0, total)


@pytest.mark.parametrize("total", [61.0, 78.0, 95.0, 120.0, 162.0, 240.0, 300.0])
def test_moi_cua_so_nam_trong_dai_mo_hinh_chiu_duoc(total: float) -> None:
    """The invariant the whole mechanism exists for.

    A 12-second window is not a small window. It is a window outside everything
    the model has ever seen -- the same fault as the 95-second recording, just
    from the other side. Only the very last window may fall to MIN_TAIL_S.
    """
    windows = plan_windows(total, _even_segments(total))
    assert windows, "bài dài mà không sinh ra cửa sổ nào"
    for w in windows:
        floor = MIN_TAIL_S if w is windows[-1] else MIN_WINDOW_S
        assert floor <= w.duration_s <= MAX_WINDOW_S, f"cửa sổ {w.index} dài {w.duration_s:.1f}s"


@pytest.mark.parametrize("total", [95.0, 162.0, 300.0])
def test_cac_cua_so_phu_kin_ban_ghi_khong_chong_nhau_khong_bo_sot(total: float) -> None:
    """A speaker must not lose a sentence at a boundary, nor be counted twice."""
    windows = plan_windows(total, _even_segments(total))
    assert windows[0].start_s == pytest.approx(0.0)
    assert windows[-1].end_s == pytest.approx(total)
    for before, after in zip(windows, windows[1:], strict=False):
        assert after.start_s == pytest.approx(before.end_s)
    assert sum(w.duration_s for w in windows) == pytest.approx(total)


def test_khong_co_doan_noi_nao_thi_van_cat_deu_duoc() -> None:
    """No voice activity segments is a degraded input, not a reason to refuse.

    Even division is worse than cutting at pauses -- a boundary can fall inside
    a word -- but it still keeps every window inside the model's range, which
    refusing to score does not.
    """
    windows = plan_windows(300.0, [])
    assert len(windows) > 1
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)


def test_cat_roi_vao_khoang_lang_chu_khong_giua_tu() -> None:
    """A boundary inside a word truncates it here and orphans it there.

    Every count-based feature moves when that happens, so the cut is pulled to
    the middle of a real silence whenever one is close enough.
    """
    segments = _even_segments(120.0, on=9.0, off=3.0)
    windows = plan_windows(120.0, segments)
    for w in windows[1:]:
        inside_speech = any(s < w.start_s < e for s, e in segments)
        assert not inside_speech, f"cắt ở {w.start_s}s rơi vào giữa một đoạn nói"


def test_khong_co_khoang_lang_gan_thi_thoi_khong_keo_bien_di_xa() -> None:
    """Snapping to the nearest pause *at any distance* is its own bug.

    One long unbroken stretch would drag a boundary tens of seconds away and
    leave a window far longer than the model accepts -- defeating the cut. Past
    the tolerance the even cut is the lesser evil.
    """
    # Nói liền một mạch 100 giây, chỉ có đúng một khoảng lặng ở giây thứ 5.
    segments = [(0.0, 5.0), (7.0, 160.0)]
    windows = plan_windows(160.0, segments)
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)


def test_duoi_ngan_bi_gop_vao_cua_so_truoc() -> None:
    """Scoring a 6-second tail would drag the median with a number of its own."""
    windows = plan_windows(66.0, _even_segments(66.0))
    assert all(w.duration_s >= MIN_TAIL_S for w in windows)


def test_tran_qc_300_giay_van_nam_trong_so_cua_so_toi_da() -> None:
    """300 seconds is the QC ceiling, and 300 / 30 is exactly MAX_WINDOWS.

    Past that many windows the submission is no longer one spoken answer to one
    prompt and a median across it stops meaning anything -- which is why the
    ceiling and the window count are set against each other deliberately.
    """
    assert len(plan_windows(300.0, _even_segments(300.0))) <= MAX_WINDOWS


def test_qua_tran_thi_uu_tien_giu_dai_cua_so_chu_khong_giu_so_luong() -> None:
    """Which invariant wins when the two cannot both hold.

    Audio longer than the QC ceiling is rejected before it ever reaches here, so
    this case is unreachable in the running system. If it ever became reachable,
    exceeding the window count produces a report a teacher can question, while
    exceeding the trained range produces a number nobody can defend. The
    duration invariant wins, and it does so on purpose rather than by accident.
    """
    windows = plan_windows(3_000.0, [])
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)


def test_gop_cua_so_ngan_vao_hang_xom_nho_hon_truoc() -> None:
    """The backstop that merges an under-length window into a neighbour.

    Reached here by tightening `min_tail_s` past what the defaults allow. That
    is not a contrived setting: with the shipped defaults the snapping rule
    already guarantees every cut sits at least `min_s` after the previous one
    and the arithmetic keeps the final piece above 20 seconds, so the merge
    cannot currently fire. It stays in the code because it is the only thing
    enforcing the invariant if any of those numbers is ever retuned -- and a
    guard nobody has ever executed is a guard nobody knows works.

    The merge goes into the SMALLER neighbour on purpose. Merging into the
    larger one is the obvious choice and the wrong one: it pushes that side past
    the 60-second ceiling, and the final split guard then has to cut it again,
    undoing the merge.
    """
    # min_s cao hơn nửa bản ghi: cắt đôi kiểu gì cũng ra hai cửa sổ "quá ngắn",
    # nên nhánh gộp buộc phải chạy.
    windows = plan_windows(95.0, _even_segments(95.0), min_s=50.0, min_tail_s=44.0)

    assert sum(w.duration_s for w in windows) == pytest.approx(95.0)
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)
    assert windows[0].start_s == 0.0
    assert windows[-1].end_s == pytest.approx(95.0)


@pytest.mark.parametrize(
    ("total", "on", "off", "min_s"),
    [
        (160.0, 7.0, 2.0, 50.0),
        (200.0, 6.0, 3.0, 55.0),
        (140.0, 11.0, 4.0, 48.0),
        # Trường hợp hàng xóm bên TRÁI nhỏ hơn, nên gộp về bên trái. Bộ số này
        # tìm được bằng cách quét, không phải chọn tay: hình dạng nào rơi vào
        # nhánh nào phụ thuộc hoàn toàn vào chỗ các khoảng lặng nằm.
        (170.0, 7.0, 1.5, 45.0),
    ],
)
def test_gop_o_giua_day_van_ra_ke_hoach_phu_kin(total, on, off, min_s) -> None:
    """A short window in the MIDDLE has two neighbours, and picks the smaller.

    The middle case is the one with a real choice to make, and the one where a
    wrong choice compounds: merge into the larger side and that side overflows,
    the split guard cuts it, and the plan can end up worse than before any
    merging. Run across several shapes because which window comes out short
    depends entirely on where the pauses happen to fall.
    """
    segments, at = [], 0.0
    while at < total:
        segments.append((round(at, 3), round(min(at + on, total), 3)))
        at += on + off

    windows = plan_windows(total, segments, min_s=min_s)

    assert sum(w.duration_s for w in windows) == pytest.approx(total)
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)
    for before, after in zip(windows, windows[1:], strict=False):
        assert after.start_s == pytest.approx(before.end_s)


def test_gop_xong_van_khong_de_cua_so_dai_qua_tran() -> None:
    """Merging and the ceiling pull in opposite directions; the ceiling wins.

    Merging two 47-second windows makes one of 95, which the model cannot score
    -- so the final split guard cuts it again. The point of the test is that the
    two rules compose into something valid rather than fighting to a stalemate
    or looping.
    """
    windows = plan_windows(95.0, _even_segments(95.0), min_s=50.0, min_tail_s=50.0)
    assert all(w.duration_s <= MAX_WINDOW_S for w in windows)
    assert sum(w.duration_s for w in windows) == pytest.approx(95.0)


def test_duoi_ngan_khong_bao_gio_xuat_hien_voi_tham_so_mac_dinh() -> None:
    """The property that makes the merge above unreachable in production.

    Worth pinning separately: it is the reason the backstop never fires, and if
    a retune breaks it the failure should name the cause rather than show up as
    a strange window somewhere downstream.
    """
    for total in (61.0, 79.0, 96.0, 120.0, 155.0, 200.0, 260.0, 300.0):
        windows = plan_windows(total, _even_segments(total))
        assert windows[-1].duration_s >= MIN_TAIL_S, (total, windows[-1].duration_s)
        assert all(w.duration_s >= MIN_WINDOW_S for w in windows[:-1]), total


@pytest.mark.parametrize("total", [61.0, 66.0, 73.0, 88.0, 101.0, 134.0, 187.0, 249.0, 300.0])
def test_moi_do_dai_deu_ra_ke_hoach_hop_le_du_khoang_lang_nam_o_dau(total: float) -> None:
    """Sweep, because the failures here were all specific arithmetic accidents.

    Two real defects came out of this exact shape: pause snapping that produced
    windows under 30 seconds, and a stretch with no pauses that left one window
    of 166 seconds. Neither showed up on the lengths that were being tried by
    hand at the time.
    """
    for step in (5.0, 9.0, 13.0):
        segments, at = [], 0.0
        while at < total:
            segments.append((at, min(at + step, total)))
            at += step + 1.4
        windows = plan_windows(total, segments)
        for i, w in enumerate(windows):
            floor = MIN_TAIL_S if i == len(windows) - 1 else MIN_WINDOW_S
            assert floor <= w.duration_s <= MAX_WINDOW_S, (total, step, w)
        assert sum(w.duration_s for w in windows) == pytest.approx(total)


# ---------------------------------------------------------------- clip_segments


def test_doan_noi_duoc_doi_ve_dong_ho_rieng_cua_cua_so() -> None:
    """`vad_onset_delay` measures the delay before speaking.

    Left on the original clock, every window after the first would report
    "started talking 132 seconds in" and the model would read every one of them
    as a speaker who froze.
    """
    segments = [(0.0, 40.0), (50.0, 90.0)]
    got = clip_segments(segments, AnalysisWindow(index=1, start_s=48.0, end_s=95.0))
    assert got == [(2.0, 42.0)]


def test_doan_noi_bi_cat_ngang_thi_chi_lay_phan_nam_trong_cua_so() -> None:
    got = clip_segments([(30.0, 70.0)], AnalysisWindow(index=0, start_s=0.0, end_s=48.0))
    assert got == [(30.0, 48.0)]


def test_doan_noi_ngoai_cua_so_thi_bien_mat() -> None:
    assert clip_segments([(0.0, 10.0)], AnalysisWindow(index=2, start_s=100.0, end_s=140.0)) == []


# ---------------------------------------------------------------- toàn tuyến


def _paused_tone(seconds: float, sr: int = 16_000) -> np.ndarray:
    """A synthetic signal shaped like a speaker, not like a test tone.

    An unbroken sine wave is a bad stand-in here for a reason that has nothing
    to do with windowing: the detector reports it as one segment tens of seconds
    long, `vad_mean_seg_len` lands far outside anything in the training data,
    and every window is refused as out of distribution. The refusal would be
    correct -- no human speaks for 47 seconds without drawing breath -- and the
    test would be measuring the signal instead of the code.

    So the tone runs in 3-second bursts with 1-second gaps: roughly the phrase
    and pause rhythm of the training corpus, and inside the model's range on
    every pause feature.
    """
    n = int(sr * seconds)
    out = np.zeros(n, dtype=np.float32)
    t = np.arange(n) / sr
    tone = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    at = 0.0
    while at < seconds:
        lo, hi = int(at * sr), int(min(at + 3.0, seconds) * sr)
        out[lo:hi] = tone[lo:hi]
        at += 4.0
    return out


def _varied_transcript(n_words: int) -> str:
    """Distinct tokens, because a repeated one is a different measurement.

    `ttr` and `log_uniq` count vocabulary. Repeating "hello world" to fill a
    minute produces a type-token ratio no real speaker reaches, and the window
    is refused for that rather than for anything under test.
    """
    rng = random.Random(7)
    return " ".join(rng.choice([f"w{i}" for i in range(400)]) for _ in range(n_words))


def _process(seconds: float, sr: int = 16_000):
    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.pipeline import ResponseProcessor

    # EnergyVad, not the production Silero detector: Silero is trained on human
    # speech and correctly finds none in a synthetic tone, which would leave
    # every window with no voice segments -- a fact about the test signal, not
    # about the windowing under test.
    engine = FakeAsrEngine(transcript=_varied_transcript(round(seconds * 2.4)))
    return ResponseProcessor(asr_engine=engine, vad=EnergyVad()).process(
        ProcessingRequest(
            response_id="r-dai",
            speaker_id="SV-001",
            task_id="P5",
            audio_path="dai.wav",
            prompt_version="v1",
            config_version="v1",
        ),
        _paused_tone(seconds, sr),
        sr,
    )


def test_bai_dai_van_co_diem_thay_vi_bi_tu_choi() -> None:
    """The behaviour the whole feature was approved for.

    Before this, a 95-second recording produced a report with no score at all:
    OUT_OF_DISTRIBUTION and nothing else. A student who spoke for a minute and a
    half got less than one who spoke for forty seconds.
    """
    report = _process(95.0)
    a = report.assessment
    assert a is not None
    assert a.overall_0_6 is not None, "bài dài vẫn không được chấm"
    assert len(a.windows) >= 2
    assert ReasonCode.SCORE_AGGREGATED in a.reasons


def test_diem_gop_luon_qua_giang_vien() -> None:
    """Approved rule: show a provisional score, labelled as unvalidated.

    "Provisional" is not a word on a screen -- it is this routing decision. The
    median across windows is a rule nobody has measured yet, so no long
    recording reaches a student as a finished result.
    """
    assert _process(95.0).status is Status.REVIEW_REQUIRED


def test_bai_dai_khong_con_bao_ngoai_phan_bo() -> None:
    """The report must not carry a score and "too long to score" side by side.

    The whole-recording pass is run only for provenance -- which model version
    touched this audio -- and it naturally reports OUT_OF_DISTRIBUTION. Letting
    that reason through made the report contradict itself.
    """
    report = _process(95.0)
    a = report.assessment
    assert a is not None
    assert ReasonCode.OUT_OF_DISTRIBUTION not in a.reasons
    assert a.out_of_range == []
    # The per-criterion lists too. They are a separate copy of the same
    # finding, and the review screen reads them -- so leaving them alone put
    # the flag back on the teacher's screen next to the score.
    for c in a.criteria:
        assert ReasonCode.OUT_OF_DISTRIBUTION not in c.reasons, c.criterion
    # And the routing decision, which gathers from both.
    assert ReasonCode.OUT_OF_DISTRIBUTION not in report.reasons


def test_bao_cao_noi_ro_cac_cua_so_lech_nhau_bao_nhieu() -> None:
    """A teacher's first question is whether the parts agreed with each other."""
    a = _process(95.0).assessment
    assert a is not None
    assert a.window_spread is not None
    scores = [w.overall_0_6 for w in a.windows if w.overall_0_6 is not None]
    assert a.window_spread == pytest.approx(round(max(scores) - min(scores), 2))


def test_bai_ngan_khong_gan_nhan_gop() -> None:
    """A 40-second response is scored whole, and must not be labelled otherwise."""
    a = _process(40.0).assessment
    assert a is not None
    assert a.windows == []
    assert ReasonCode.SCORE_AGGREGATED not in a.reasons
