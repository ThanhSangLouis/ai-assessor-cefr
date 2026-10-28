"""End-to-end pipeline tests, using a fake engine and a deterministic VAD."""

import numpy as np
import pytest

from aicefr.asr.base import AsrError
from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.contracts import ProcessingRequest, ReasonCode, Status
from aicefr.pipeline import ResponseProcessor


@pytest.fixture
def request_obj() -> ProcessingRequest:
    return ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P3",
        audio_path="khong-dung-den.wav",
        prompt_version="v1",
        config_version="v1",
    )


class BrokenAsr:
    name = "broken"

    def transcribe(self, pcm, sr):
        raise AsrError("simulated engine failure")


class EmptyAsr:
    name = "empty"

    def transcribe(self, pcm, sr):
        return FakeAsrEngine(transcript="  ").transcribe(pcm, sr)


def test_full_pipeline_returns_a_report(request_obj, tone, sr):
    r = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(request_obj, tone, sr)
    assert r.response_id == "r1"
    assert r.qc is not None and r.asr is not None and r.features is not None
    assert r.status in set(Status)


def test_broken_audio_rejected_without_calling_asr(request_obj, sr):
    class MustNotRun:
        name = "x"

        def transcribe(self, pcm, sr):  # pragma: no cover
            raise AssertionError("ASR must not be called when QC fails")

    r = ResponseProcessor(MustNotRun(), vad=EnergyVad()).process(
        request_obj, np.zeros(sr * 400, dtype=np.float32), sr
    )
    assert r.status is Status.REJECTED
    assert r.asr is None


def test_asr_error_reports_failure(request_obj, tone, sr):
    r = ResponseProcessor(BrokenAsr(), vad=EnergyVad()).process(request_obj, tone, sr)
    assert r.status is Status.FAILED
    assert ReasonCode.ASR_FAILED in r.reasons


def test_empty_transcript_goes_to_teacher(request_obj, tone, sr):
    r = ResponseProcessor(EmptyAsr(), vad=EnergyVad()).process(request_obj, tone, sr)
    assert r.status is Status.REVIEW_REQUIRED
    assert ReasonCode.ASR_EMPTY_TRANSCRIPT in r.reasons


def test_never_returns_teacher_verified_true(request_obj, tone, sr):
    r = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(request_obj, tone, sr)
    if r.assessment is not None:
        assert r.assessment.teacher_verified is False


def test_deterministic_result(request_obj, tone, sr):
    a = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(request_obj, tone, sr)
    b = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(request_obj, tone, sr)

    def without_clock(r) -> dict:
        # `scored_at` is when, not what: two runs a second apart differ there only.
        d = r.model_dump(mode="json")
        if d.get("assessment"):
            d["assessment"].pop("scored_at", None)
        return d

    assert without_clock(a) == without_clock(b)


def test_moc_thoi_gian_tu_nam_tren_dong_ho_cua_ban_ghi_goc(sr) -> None:
    """Chữ phải sáng đúng lúc nghe thấy tiếng, không chạy trước.

    Bản ghi thật hay có vài giây im lặng đầu bài. Hệ thống cắt phần im lặng đó
    trước khi đưa cho bộ nhận dạng — nếu không Whisper sẽ lặp một token hàng
    trăm lần. Nhưng trình phát ở trang báo cáo phát **bản gốc**, nên mốc thời
    gian trả về phải được cộng lại phần đã cắt.

    Thiếu bước cộng lại, chữ sáng sớm hơn tiếng đúng bằng số giây im lặng đầu
    bài, và nút "nghe đoạn này" của bằng chứng nhảy sai chỗ.
    """
    import numpy as np

    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor

    lang = np.zeros(int(sr * 3.0), dtype=np.float32)
    t = np.arange(int(sr * 40)) / sr
    noi = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    pcm = np.concatenate([lang, noi])

    # EnergyVad chứ không phải Silero: Silero là bộ dò *tiếng nói*, một sóng sin
    # 220 Hz với nó không phải tiếng người nên nó trả về rỗng và phép cắt không
    # chạy. Bộ dò theo năng lượng cho kết quả tất định trên tín hiệu tổng hợp.
    report = ResponseProcessor(asr_engine=FakeAsrEngine(), vad=EnergyVad()).process(
        ProcessingRequest(
            response_id="r-lech",
            speaker_id="SV-001",
            task_id="P3",
            audio_path="x.wav",
            prompt_version="v1",
            config_version="v1",
        ),
        pcm,
        sr,
    )

    assert report.asr is not None and report.asr.words
    dau_tien = report.asr.words[0]
    # Tiếng bắt đầu ở giây thứ 3; cho phép lệch vì phần đệm 0,5 giây khi cắt.
    assert 2.0 <= dau_tien.start_s <= 4.0, (
        f"từ đầu tiên ở {dau_tien.start_s}s trong khi tiếng bắt đầu ở 3.0s —"
        " mốc thời gian đang nằm trên đồng hồ của bản đã cắt"
    )
    assert report.asr.words[-1].end_s <= pcm.size / sr + 0.1


def test_do_tre_truoc_khi_noi_khong_bi_phan_cat_lam_phang(sr) -> None:
    """`vad_onset_delay` phải là độ trễ thật, không phải phần đệm khi cắt.

    Mô hình được huấn luyện trên dải 0,3–5,5 giây. Nếu mọi bài đều báo đúng
    0,5 giây — phần đệm — thì đặc trưng này không còn mang thông tin và đẩy
    mọi điểm lệch đi cùng một lượng, âm thầm.
    """
    import numpy as np

    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor

    t = np.arange(int(sr * 40)) / sr
    noi = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    pcm = np.concatenate([np.zeros(int(sr * 3.0), dtype=np.float32), noi])

    report = ResponseProcessor(asr_engine=FakeAsrEngine(), vad=EnergyVad()).process(
        ProcessingRequest(
            response_id="r-tre",
            speaker_id="SV-001",
            task_id="P3",
            audio_path="x.wav",
            prompt_version="v1",
            config_version="v1",
        ),
        pcm,
        sr,
    )
    onset = report.features.value_of("vad_onset_delay") if report.features else None
    assert onset is not None
    assert onset > 1.0, f"độ trễ báo về {onset}s, đã bị phép cắt làm phẳng"
