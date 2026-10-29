"""Kiem thu hanh vi mo hinh cham, theo kieu CheckList (Ribeiro va cs., ACL 2020). D022.

Test don vi hoi "ham nay tra ve gi". O day hoi dieu ma nguoi dung va hoi dong
quan tam: he thong co hanh xu DUNG voi nhung tinh huong co the doan truoc khong.

  * MFT (minimum functionality): nhung ca phai bi tu choi -- khong bao gio ra
    band.
  * INV (invariance): thay doi khong lien quan toi nang luc noi -- am luong,
    chu hoa, dau cau -- khong duoc lam doi diem.
  * DIR (directional): thay doi CO lien quan phai day diem dung chieu --
    ngat nghi dai them thi diem khong duoc tang.

Mot ca CO Y ghi lai mot han che: mo hinh khong nhin noi dung (Aalto, SLaTE
2025). Trao loi noi sang chu de khac voi cung nhip thi diem khong doi -- va la
chan lac de phai bat duoc dung ca do.
"""

from __future__ import annotations

import numpy as np
import pytest

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import ProcessingRequest, ReasonCode, ResponseStatus, Word
from aicefr.features.extract import FeatureExtractor
from aicefr.features.relevance import validity_flags
from aicefr.pipeline import ResponseProcessor
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.task_repository import DEFAULT_TOPIC_KEYWORDS

SR = 16_000
EXAM = (
    "when i prepare for an exam i first make a schedule then i review my notes every "
    "morning and practise old questions finally i sleep early the night before the "
    "test so that my mind is fresh and i can remember the material easily"
).split()
FOOTBALL = (
    "my favourite football team is manchester united and i watch every match on "
    "saturday night with my friends we cheer loudly when the striker scores a goal "
    "and we argue about the referee after the game is over"
).split()


@pytest.fixture
def req() -> ProcessingRequest:
    return ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P4",
        audio_path="khong-dung-den.wav",
        prompt_version="v1",
        config_version="v1",
    )


def speechish(seconds: float = 45.0) -> np.ndarray:
    """Tieng 'co nhip': am 220 Hz bat tat 0,5 Hz, du de VAD thay doan noi va khoang ngung."""
    t = np.arange(int(seconds * SR)) / SR
    on = (np.sin(2 * np.pi * 0.5 * t) > -0.3).astype(np.float32)
    return (0.2 * np.sin(2 * np.pi * 220 * t) * on).astype(np.float32)


def run(pcm, req, engine=None):
    return ResponseProcessor(engine or FakeAsrEngine(), vad=EnergyVad()).process(req, pcm, SR)


def has_band(r) -> bool:
    return r.assessment is not None and r.assessment.overall_band is not None


def issued_without_teacher(r) -> bool:
    return r.status is ResponseStatus.COMPLETED and has_band(r)


# ----------------------------------------------------------------------- MFT


def test_mft_silence_is_never_scored(req) -> None:
    r = run(np.zeros(SR * 40, dtype=np.float32), req)
    assert r.status is ResponseStatus.REJECTED and not has_band(r)


def test_mft_a_recording_too_short_is_never_scored(req) -> None:
    r = run(speechish(5), req)
    assert r.status is ResponseStatus.REJECTED and not has_band(r)
    assert ReasonCode.AUDIO_TOO_SHORT in r.reasons


def test_mft_a_clipped_recording_is_not_issued_silently(req) -> None:
    t = np.arange(SR * 40) / SR
    square = np.sign(np.sin(2 * np.pi * 220 * t)).astype(np.float32)  # dinh day thang
    r = run(square, req)
    assert not issued_without_teacher(r)
    assert ReasonCode.CLIPPING_DETECTED in r.reasons


def test_mft_noise_or_music_that_yields_no_words_is_never_scored(req) -> None:
    """Whisper tren tieng on/nhac thuong tra ban chep rong; ban chep rong khong duoc ra band."""
    r = run(speechish(), req, FakeAsrEngine(transcript="  "))
    assert not has_band(r)
    assert ReasonCode.ASR_EMPTY_TRANSCRIPT in r.reasons


def test_mft_speech_in_vietnamese_is_never_scored(req) -> None:
    engine = FakeAsrEngine(language="vi", language_probability=0.95)
    r = run(speechish(), req, engine)
    assert not has_band(r) and ReasonCode.LANGUAGE_NOT_ENGLISH in r.reasons


def test_mft_a_recogniser_loop_is_cut_and_flagged(req) -> None:
    loop = " ".join(["thank you for watching"] * 15)
    r = run(speechish(), req, FakeAsrEngine(transcript="i like my school " + loop))
    assert ReasonCode.ASR_HALLUCINATION in r.reasons
    assert not issued_without_teacher(r)


# ----------------------------------------------------------------------- INV


@pytest.mark.parametrize("gain", [0.5, 2.0])  # -6 dB va +6 dB
def test_inv_loudness_does_not_change_the_score(req, gain) -> None:
    base = run(speechish(), req)
    louder = run((speechish() * gain).astype(np.float32), req)
    assert [f.value for f in louder.features.items] == [f.value for f in base.features.items]
    assert louder.assessment.overall_0_6 == base.assessment.overall_0_6


def test_inv_case_and_punctuation_do_not_change_the_features() -> None:
    def words(text):
        return [
            Word(text=w, start_s=i * 0.6, end_s=i * 0.6 + 0.4, prob=0.9)
            for i, w in enumerate(text.split())
        ]

    ex = FeatureExtractor()
    a = ex.extract(words("I think, Online learning is GOOD. I think"), [(0.0, 5.0)], 5.0)
    b = ex.extract(words("i think online learning is good i think"), [(0.0, 5.0)], 5.0)
    assert [f.value for f in a.items] == [f.value for f in b.items]


def test_inv_the_result_is_deterministic(req) -> None:
    a, b = run(speechish(), req), run(speechish(), req)
    assert a.model_dump(exclude={"assessment": {"scored_at"}}) == b.model_dump(
        exclude={"assessment": {"scored_at"}}
    )


# ----------------------------------------------------------------------- DIR


def _timed(tokens: list[str], pause_after: int | None = None, pause_s: float = 0.0):
    """Tu cach deu 0,45 s; tuy chon chen mot khoang ngung sau tu thu `pause_after`."""
    words, segs, t = [], [], 0.3
    seg_start = t
    for i, w in enumerate(tokens):
        words.append(Word(text=w, start_s=round(t, 3), end_s=round(t + 0.35, 3), prob=0.9))
        t += 0.45
        if pause_after is not None and i == pause_after:
            segs.append((seg_start, t - 0.1))
            t += pause_s
            seg_start = t
    segs.append((seg_start, t))
    return words, segs, t + 0.3


def test_dir_longer_pauses_never_raise_the_score() -> None:
    """Cung loi noi, khoang ngung giua bai dai dan 0 -> 1,5 -> 2 -> 3 giay.

    Bai van nam trong phan bo huan luyen o moi muc (co diem that, khong phai
    None) -- mot test DIR tren bai OOD thi khong kiem gi ca.
    """
    ex, scorer = FeatureExtractor(), RidgeScorer()
    scores, pauses = [], []
    for pause_s in (0.0, 1.5, 2.0, 3.0):
        w, s, d = _timed(EXAM, None if pause_s == 0 else len(EXAM) // 2, pause_s)
        feats = ex.extract(w, s, d)
        a = scorer.score(feats)
        assert a.overall_0_6 is not None, f"bai ngoai phan bo o muc ngung {pause_s} s"
        scores.append(a.overall_0_6)
        pauses.append(feats.value_of("vad_mean_pause"))
    assert pauses == sorted(pauses)
    assert scores == sorted(scores, reverse=True)
    assert scores[-1] < scores[0]


# ------------------------------------------------- han che da biet + la chan


def test_known_limit_content_is_invisible_to_the_score_but_the_shield_sees_it() -> None:
    """Cung nhip, khac chu de: diem KHONG doi (han che), nhung co lac de PHAI bat.

    Day la ly do la chan ton tai. Neu mot ngay test nay hong o ve dau tien --
    diem bat dau doi theo noi dung -- thi mo hinh da khac va can xem lai.
    """
    n = min(len(EXAM), len(FOOTBALL))
    ex, scorer = FeatureExtractor(), RidgeScorer()
    on_w, segs, dur = _timed(EXAM[:n])
    off_w, _, _ = _timed(FOOTBALL[:n])
    on, off = ex.extract(on_w, segs, dur), ex.extract(off_w, segs, dur)
    assert scorer.score(on).overall_0_6 == pytest.approx(scorer.score(off).overall_0_6, abs=0.35)

    class P4:
        prompt_text = "Hãy mô tả một quy trình bạn quen thuộc."
        topic_keywords = tuple(k.strip() for k in DEFAULT_TOPIC_KEYWORDS["P4"].split(","))

    assert validity_flags(" ".join(FOOTBALL[:n]), P4) == ["OFF_TOPIC_SUSPECTED"]
    assert validity_flags(" ".join(EXAM[:n]), P4) == []
