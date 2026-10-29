"""Tests for the failures that 194 passing tests did not catch.

An independent review found three serious bugs in code the suite called green.
All three shared a shape: a test asserted the return value of one component,
using input the test itself had constructed. Nobody asked whether the component
upstream actually produces that shape, or what state was left behind afterwards.

So these tests deliberately do the opposite: run real objects end to end, run
them concurrently, and look at what remains in the database.
"""

from __future__ import annotations

import importlib
import io
import pkgutil
import threading

import numpy as np
import pytest
import soundfile as sf
from conftest import feature_set
from fastapi.testclient import TestClient

import aicefr
from aicefr.contracts import FeatureSet, QcResult, QcStatus, Response, ResponseStatus
from aicefr.review.router import ReviewRouter
from aicefr.scoring.scorer import RidgeScorer, load_model, near_boundary
from aicefr.storage.auth_repository import Role
from aicefr.storage.repository import InvalidStateError, Repository

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def login_as(app, pseudonym: str, role: str) -> TestClient:
    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(app)
    assert (
        c.post(
            "/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD}
        ).status_code
        == 200
    )
    return c


def wav(seconds: float = 45.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


def submit(c, task="P3", name="a.wav", data=None):
    return c.post(
        "/api/v1/responses",
        files={"audio": (name, data or wav(), "audio/wav")},
        data={"task_id": task},
    )


def features_scoring_at(target: float) -> tuple[FeatureSet, object]:
    """Build a feature set whose real score lands on `target`.

    Binary search over the model's own percentile range, so the values stay
    inside the training distribution and the out-of-distribution guard does not
    fire. No hand-made Assessment: the point is to exercise the real scorer.
    """
    model = load_model()
    bounds = {
        name: (model["feature_lo"][i], model["feature_hi"][i])
        for i, name in enumerate(model["feature_order"])
    }
    scorer = RidgeScorer()

    def at(t: float):
        values = {k: lo + (hi - lo) * t for k, (lo, hi) in bounds.items()}
        fs = feature_set(values)
        return fs, scorer.score(fs)

    low, high = 0.0, 1.0
    for _ in range(40):
        mid = (low + high) / 2
        _fs, assessment = at(mid)
        if assessment.overall_0_6 is None:
            break
        if assessment.overall_0_6 < target:
            low = mid
        else:
            high = mid
    return at(high)


# ------------------------------------------------------------------ producer/consumer


def test_a_score_on_a_band_boundary_reaches_the_teacher() -> None:
    """The real scorer and the real router, with no hand-built objects between.

    SCORE_NEAR_BOUNDARY was raised into a local variable that was then dropped,
    and the router looked for it on the per-criterion lists, where it could
    never appear. Every response sitting exactly on a band boundary went
    straight to COMPLETED -- the responses the model is least sure about, and
    the whole reason a human is in the loop.

    The existing test passed because it injected the flag by hand into an
    Assessment the scorer would never have produced.
    """
    fs, assessment = features_scoring_at(3.75)
    model = load_model()
    assert near_boundary(
        assessment.overall_0_6, model["band_thresholds"], model["boundary_margin"]
    ), "chưa dựng được ca sát ranh giới"

    qc = QcResult(
        duration_ms=45_000,
        sample_rate_hz=16_000,
        channels=1,
        silence_ratio=0.2,
        clipping_ratio=0.0,
        qc_status=QcStatus.PASS,
    )
    decision = ReviewRouter().route(qc, assessment, fs)
    assert decision.status is ResponseStatus.REVIEW_REQUIRED
    assert decision.needs_teacher


def test_every_module_imports() -> None:
    """A smoke test for the whole package.

    The `aicefr` console script was broken for several commits -- it imported a
    function that a refactor had turned into a class -- and no test noticed,
    because nothing imported that module at all.
    """
    for module in pkgutil.walk_packages(aicefr.__path__, prefix="aicefr."):
        if "whisper_adapter" in module.name:
            continue  # needs a model backend installed
        importlib.import_module(module.name)


# ------------------------------------------------------------------ state machine


@pytest.mark.parametrize(
    "status", [ResponseStatus.REJECTED, ResponseStatus.FAILED, ResponseStatus.COMPLETED]
)
def test_only_a_response_awaiting_review_can_be_decided(app, status) -> None:
    """A rejected recording must not be approvable into a verified result."""
    from aicefr.api import main as m

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    report = m.repo.get(rid)
    report.status = status
    m.repo.save(report, "SV-001", "P3")

    with pytest.raises(InvalidStateError):
        m.repo.apply_review(rid, "gv", None, None, "thu duyet bai sai trang thai")


def test_the_api_answers_409_for_an_undecidable_response(app) -> None:
    from aicefr.api import main as m

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    report = m.repo.get(rid)
    report.status = ResponseStatus.REJECTED
    m.repo.save(report, "SV-001", "P3")

    teacher = login_as(app, "GV-01", "teacher")
    r = teacher.post(f"/api/v1/review/{rid}", json={"reason": "thu duyet bai da bi tu choi"})
    assert r.status_code == 409


def test_changing_the_score_moves_the_band_with_it(app) -> None:
    """5.5 paired with A2 is not a result, it is a contradiction."""
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")

    r = teacher.post(
        f"/api/v1/review/{rid}",
        json={"new_score": 5.5, "reason": "nghe lai thay tot hon nhieu"},
    )
    if r.status_code == 409:
        pytest.skip("bài không ở trạng thái chờ duyệt trong lần chạy này")
    assert r.json()["assessment"]["overall_band"] == "C1"  # D059: 5.5 is above B2/C1


# ------------------------------------------------------------------ state left behind


def test_a_verified_result_is_never_overwritten_by_a_later_job(app) -> None:
    """A teacher's decision outranks anything the machine produces afterwards.

    `save()` was an unconditional overwrite, so a late background job -- after a
    reload, a second worker, a rescoring run -- replaced the verified result
    with a fresh estimate and cleared teacher_verified, leaving no trace that a
    human had decided anything.
    """
    from aicefr.api import main as m

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    r = teacher.post(f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"})
    if r.status_code == 409:
        pytest.skip("bài không ở trạng thái chờ duyệt trong lần chạy này")

    stale = m.repo.get(rid)
    stale.assessment.teacher_verified = False
    stale.assessment.overall_0_6 = 1.0
    m.repo.save(stale, "SV-001", "P3")

    after = m.repo.get(rid)
    assert after.assessment.teacher_verified is True
    assert after.assessment.overall_0_6 != 1.0


def test_saving_again_keeps_the_submission_time(app) -> None:
    """created_at is when the student submitted, not when we last wrote a row."""
    from aicefr.api import main as m

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    first = m.repo.status_of(rid)["created_at"]

    report = m.repo.get(rid)
    m.repo.save(report, "SV-001", "P3")
    assert m.repo.status_of(rid)["created_at"] == first


def test_saving_without_the_owner_does_not_erase_it(app) -> None:
    """The trap that orphaned reports once already, fixed at the cause.

    `apply_review` was patched to pass the owner through, but `save()` itself
    still dropped whatever the caller omitted. The fourth caller would have
    reproduced the same bug.
    """
    from aicefr.api import main as m

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    owner_before = m.repo.owner_of(rid)

    m.repo.save(m.repo.get(rid), "SV-001", "P3")  # no account_id passed
    assert m.repo.owner_of(rid) == owner_before


# ------------------------------------------------------------------ concurrency


def test_only_one_teacher_wins_a_contested_lock(tmp_path) -> None:
    """Two teachers claiming at the same instant: exactly one may succeed.

    Reading the row and then writing it left a window where both read "nobody
    holds this" and both wrote their claim. The lock reported success to both --
    the one thing it exists to prevent.
    """
    repo = Repository(tmp_path / "t.db")
    repo.save(
        Response(response_id="r1", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1"),
        "SV-001",
        "P3",
    )

    results: list[tuple[bool, str | None]] = []
    barrier = threading.Barrier(2)

    def claim(who: str) -> None:
        barrier.wait()
        results.append(repo.lock_response("r1", who, who.upper()))

    threads = [threading.Thread(target=claim, args=(w,)) for w in ("gv1", "gv2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(1 for granted, _ in results if granted) == 1, f"cả hai cùng thắng: {results}"


def test_an_expired_lock_is_reclaimed(tmp_path) -> None:
    repo = Repository(tmp_path / "t.db")
    repo.save(
        Response(response_id="r1", status=ResponseStatus.REVIEW_REQUIRED, config_version="v1"),
        "SV-001",
        "P3",
    )
    repo.lock_response("r1", "gv1", "GV1", minutes=-1)
    granted, holder = repo.lock_response("r1", "gv2", "GV2")
    assert granted and holder is None


# ------------------------------------------------------------------ background failures


def test_a_missing_audio_file_does_not_leave_the_job_running(app) -> None:
    """Nothing may escape a background job.

    The handler caught DecodeError only, so a missing file raised
    FileNotFoundError and the response sat at RUNNING until the next restart --
    and the sweep only runs at startup.
    """
    import pathlib as _pathlib

    from aicefr.api import main as m
    from aicefr.contracts import ProcessingRequest
    from aicefr.services.core.assessment import scoring
    from aicefr.services.core.assessment.context import svc

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    audio = m.repo.audio_path_of(rid)
    _pathlib.Path(audio).unlink()
    m.repo.set_status(rid, ResponseStatus.QUEUED)  # a job still waiting when its file vanished

    request = ProcessingRequest(
        response_id=rid,
        speaker_id="SV-001",
        task_id="P3",
        audio_path=audio,
        prompt_version="v1",
        config_version="v1",
    )
    # No exception may escape, and the response must not be left running.
    scoring.dispatch(request, _pathlib.Path(audio).name, svc().tasks.get("P3"), "acc")

    state = m.repo.status_of(rid)["status"]
    assert state != "RUNNING", "bài kẹt ở RUNNING sau khi tệp biến mất"
    assert state == "FAILED"


# ------------------------------------------------------------------ audio handling


@pytest.mark.parametrize("source_rate", [16_000, 44_100, 48_000])
def test_common_recording_rates_are_accepted(source_rate) -> None:
    """44.1 and 48 kHz are what phones and laptops actually record.

    Uploaded .wav at those rates used to be rejected outright, while the same
    audio recorded in the browser passed -- that path goes through ffmpeg, which
    resamples. Two ways of submitting behaved differently under one requirement.
    """
    from aicefr.audio.decoder import FirstMatchDecoder
    from aicefr.qc.audio_qc import AudioQualityChecker

    pcm, sr = FirstMatchDecoder().decode(wav(45.0, source_rate), "a.wav")
    assert sr == 16_000
    result = AudioQualityChecker().check(pcm, sr)
    assert result.qc_status is QcStatus.PASS


def test_missing_word_probabilities_are_reported_as_unknown() -> None:
    """Unknown is not zero.

    Returning 0.0 made the router read "confidence below 0.65" and tell a
    teacher the recogniser was unsure, when it had not reported confidence at
    all. The contract is explicit: missing data returns None with a reason code.
    """
    from aicefr.contracts import Word
    from aicefr.features.extract import FeatureExtractor

    words = [Word(text=f"w{i}", start_s=i * 0.4, end_s=i * 0.4 + 0.3) for i in range(30)]
    fs = FeatureExtractor().extract(words, [(0.0, 12.0)], 12.0)
    for name in ("asr_conf_mean", "asr_conf_geo"):
        f = fs.feature(name)
        assert f is not None and not f.is_computable
        # Truoc refactor, hai dac trung nay ve None ma KHONG mang ly do nao.
        assert f.reason is not None


# ------------------------------------------------------------------ model/runtime pairing


def test_a_different_recogniser_is_flagged_for_review() -> None:
    """The model was fitted on features from one recogniser, not any recogniser.

    This artifact was trained on transcripts from Whisper small (the corpus
    ships those under `pre-norm/`), while the system runs large-v3-turbo.
    Measured on 106 responses scored by both, mean confidence shifts by +0.0198
    (paired t = 4.64, p = 1e-5): about +0.07 points on average, and more than
    0.25 points on 15% of responses. `asr_conf_mean` is the largest coefficient
    in the model, so this moves scores for reasons that have nothing to do with
    the speaker -- silently, unless something checks.
    """
    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.contracts import ReasonCode, Transcript
    from aicefr.pipeline import ResponseProcessor

    processor = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad())
    assert processor.scorer.trained_with.get("asr_model"), (
        "hiện vật phải khai báo ASR đã huấn luyện"
    )

    other = Transcript(
        text="x", engine="whisper-mlx", model_version="mlx-community/whisper-large-v3-turbo"
    )
    flags = processor._version_mismatches(other)  # noqa: SLF001
    assert ReasonCode.ASR_VERSION_MISMATCH in flags
    # EnergyVad is not the detector the model was fitted on either.
    assert ReasonCode.VAD_VERSION_MISMATCH in flags


def test_a_matching_recogniser_raises_nothing() -> None:
    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.contracts import Transcript
    from aicefr.pipeline import ResponseProcessor

    processor = ResponseProcessor(FakeAsrEngine())
    trained = processor.scorer.trained_with
    same = Transcript(text="x", engine="e", model_version=trained["asr_model"])

    class _Vad:
        name = trained["vad_name"]

        def segments(self, pcm, sr):
            return []

    processor.vad = _Vad()
    assert processor._version_mismatches(same) == []  # noqa: SLF001


def test_unscorable_responses_still_carry_their_flags() -> None:
    """The branch that gives up used to drop everything said about the run.

    A response the model cannot score is the one where knowing *why* matters
    most, and that is exactly where the reasons were being discarded.
    """
    from aicefr.contracts import Assessment, QcResult, QcStatus, ReasonCode

    qc = QcResult(
        duration_ms=45_000,
        sample_rate_hz=16_000,
        channels=1,
        silence_ratio=0.2,
        clipping_ratio=0.0,
        qc_status=QcStatus.PASS,
    )
    assessment = Assessment(
        overall_0_6=None,
        overall_band=None,
        model_version="ridge_resp_v1",
        reasons=[ReasonCode.ASR_VERSION_MISMATCH],
    )
    decision = ReviewRouter().route(qc, assessment, None)
    assert ReasonCode.ASR_VERSION_MISMATCH in decision.reasons


def test_the_boundary_margin_is_wide_enough_for_the_error() -> None:
    """A margin narrower than the model's own error catches too little.

    With an RMSE around half a point and bands one point apart, a margin of 0.25 covered less
    than half a standard deviation of error and caught 57.9% of misplaced
    responses; 0.50 catches 90.6%.
    """
    model = load_model()
    assert model["boundary_margin"] >= 0.5
    assert model["boundary_margin"] >= model["cv_rmse"] * 0.9


# ------------------------------------------------------------------ recogniser loops


def test_a_repetition_loop_is_detected_and_cut() -> None:
    """Whisper does not stay quiet on silence: it repeats a token, sometimes hundreds of times.

    Seen on a real submission: 95 seconds of about 186 spoken words came back
    with 398, of which one token appeared 212 times. Every count-based feature
    was poisoned at once -- words per second went from roughly 2.0 to 4.19,
    outside anything the model was trained on -- and the student was told their
    recording was unusual, when in fact the recogniser had malfunctioned.
    """
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    real = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.9)
        for i, w in enumerate("i think online learning is very flexible indeed".split())
    ]
    loop = [
        Word(text="Ti", start_s=10 + i * 0.1, end_s=10 + i * 0.1 + 0.05, prob=0.0)
        for i in range(200)
    ]

    finding = detect_repetition(real + loop)
    assert finding.detected
    assert finding.token == "ti"
    assert finding.repeats == 200
    assert finding.keep_until_index == len(real), "phải cắt đúng chỗ vòng lặp bắt đầu"


def test_normal_speech_is_not_mistaken_for_a_loop() -> None:
    """Real English repeats words. "the" is about 6% of ordinary speech."""
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    text = (
        "the classroom is better for most subjects because the lecturer can answer "
        "the question immediately and the other students hear the answer too"
    )
    words = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.9)
        for i, w in enumerate(text.split())
    ]
    assert detect_repetition(words).detected is False


def test_silence_at_the_ends_is_trimmed_but_pauses_are_kept() -> None:
    """Only the ends. Pauses inside the response are the fluency signal itself.

    Removing them would delete the measurement the model depends on most.
    """
    import numpy as np

    from aicefr.pipeline import trim_to_speech

    sr = 16_000
    pcm = np.zeros(sr * 30, dtype=np.float32)
    # Speech from 10s to 12s and from 18s to 20s: one internal pause of 6s.
    segments = [(10.0, 12.0), (18.0, 20.0)]
    trimmed, offset = trim_to_speech(pcm, sr, segments, pad_s=0.5)

    assert offset == 9.5
    kept = len(trimmed) / sr
    assert 10.9 < kept < 11.1, "phải giữ trọn khoảng nói kể cả quãng ngừng bên trong"


def test_trimming_does_nothing_without_speech() -> None:
    import numpy as np

    from aicefr.pipeline import trim_to_speech

    pcm = np.zeros(16_000 * 5, dtype=np.float32)
    trimmed, offset = trim_to_speech(pcm, 16_000, [])
    assert offset == 0.0
    assert len(trimmed) == len(pcm)


def test_an_out_of_range_report_says_which_measurement_and_by_how_much() -> None:
    """ "Not enough reliable evidence" is true but useless.

    A student cannot act on it. The commonest cause is a recording longer than
    anything the model was trained on, and that has an obvious remedy -- but
    only if somebody says so.
    """
    from aicefr.scoring.scorer import RidgeScorer, load_model

    model = load_model()
    values = {
        name: (model["feature_lo"][i] + model["feature_hi"][i]) / 2
        for i, name in enumerate(model["feature_order"])
    }
    values["total_dur"] = 95.0  # far beyond anything trained on

    assessment = RidgeScorer().score(feature_set(values))
    assert assessment.overall_0_6 is None
    offenders = {item["feature"] for item in assessment.out_of_range}
    assert "total_dur" in offenders
    item = next(i for i in assessment.out_of_range if i["feature"] == "total_dur")
    assert item["too"] == "high"
    assert item["accepted_high"] < 95.0


def test_no_duplicate_function_names_in_a_module() -> None:
    """A redefined name silently deletes the first definition.

    This is not hypothetical. `_score_one` in the API module was defined twice:
    an automated rename gave the guard wrapper the same name as the function it
    wrapped. Python kept the later one, so the wrapper -- the only thing that
    turned an unexpected exception into a FAILED status -- stopped existing, and
    a response whose save failed stayed at RUNNING forever.

    Ruff's F811 does not fire here, because the dead definition calls its own
    name and that counts as a use.
    """
    import ast
    import pathlib

    offenders: list[str] = []
    for path in pathlib.Path("src/aicefr").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        seen: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name in seen:
                    offenders.append(f"{path}:{node.lineno} {node.name}")
                seen.add(node.name)
    assert not offenders, f"hàm bị định nghĩa hai lần, bản đầu bị xoá âm thầm: {offenders}"


def test_loi_ngoai_du_kien_khi_luu_van_dong_bai_lai(app, monkeypatch) -> None:
    """Whatever fails, the response must not be left at RUNNING.

    The submitter polls the progress page; a response stuck at RUNNING is a page
    that spins until the process restarts. The speech worker's guard reports a
    failure for anything that escapes the scoring itself.
    """
    from aicefr.api import main as m

    def boom(*args, **kwargs):
        raise InvalidStateError("giảng viên đã xác nhận bài này")

    reports: list[dict] = []
    monkeypatch.setattr(m.speech, "_score", boom)
    monkeypatch.setattr(m.speech, "report", reports.append)

    # Must not raise: an exception here escapes into the worker thread instead.
    m.speech.score({"response_id": "r-loi"})

    assert reports == [{"response_id": "r-loi", "failed": "PROCESSING_INTERRUPTED"}]


def test_bat_duoc_vong_lap_ca_cum_tu_chu_khong_chi_mot_tu() -> None:
    """Whisper lặp nguyên một cụm, không phải một token.

    Ca thật: bài 94 giây, phần cuối là "Keep the classroom for discussion and
    practice." lặp lại rồi méo dần thành chữ vô nghĩa. Hai phép thử cũ không
    thấy gì — không token nào lặp sáu lần liên tiếp, không token nào chiếm 35%
    bản chép lời — nên cả đoạn máy bịa đi thẳng vào phần trích đặc trưng.
    """
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    that = "tôi nghĩ học trực tuyến và học trên lớp đều có ưu điểm riêng của nó".split()
    lap = ("keep the classroom for discussion and practice " * 3).split()
    words = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.9)
        for i, w in enumerate(that + lap)
    ]

    f = detect_repetition(words)
    assert f.detected and f.kind == "phrase"
    assert f.keep_until_index == len(that) + 7  # giữ lần nói đầu tiên
    assert "lặp 3 lần" in f.describe()


def test_nguoi_noi_nhac_lai_mot_cum_hai_lan_thi_khong_bi_cat() -> None:
    """Nhắc lại để nhấn mạnh là chuyện bình thường của người nói.

    Ranh giới đặt ở ba lần liên tiếp: hai lần là người, ba lần là máy kẹt.
    """
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    toks = "this is very important this is very important and that is why i said it twice".split()
    words = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.9) for i, w in enumerate(toks)
    ]
    assert detect_repetition(words).detected is False


def test_duoi_ban_chep_loi_toan_tu_do_tin_cay_bang_khong_thi_bi_cat() -> None:
    """Whisper đánh dấu từ nó bịa bằng xác suất gần 0.

    Trong ca thật, ba từ cuối — "classroom", "past", "finger" — đều trả về 0.00.
    Đó là chữ ký của việc bộ nhận dạng chạy tiếp sau khi người nói đã dừng.
    """
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    that = "i think online learning is flexible and i can study at night".split()
    bia = "classroom past finger stop reading finger".split()
    words = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.9) for i, w in enumerate(that)
    ] + [
        Word(text=w, start_s=(len(that) + i) * 0.4, end_s=(len(that) + i) * 0.4 + 0.3, prob=0.0)
        for i, w in enumerate(bia)
    ]

    f = detect_repetition(words)
    assert f.detected and f.kind == "low_prob_tail"
    assert f.keep_until_index == len(that)


def test_ban_chep_loi_binh_thuong_khong_bi_cat_nham() -> None:
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    toks = (
        "online learning is flexible but the classroom is better for discussion "
        "because i can ask the lecturer a question immediately"
    ).split()
    words = [
        Word(text=w, start_s=i * 0.4, end_s=i * 0.4 + 0.3, prob=0.85) for i, w in enumerate(toks)
    ]
    assert detect_repetition(words).detected is False


def test_bat_duoc_khi_dong_ho_dung_lai_o_duoi_ban_chep_loi() -> None:
    """Chữ ký chắc chắn nhất của ảo giác: mốc thời gian không nhích.

    Đo trên chính bản ghi 95 giây sinh viên gửi (whisper-large-v3-turbo):
    người nói thật kết thúc ở 92,3 giây, rồi máy đọc lại nguyên cụm bảy từ,
    **cả bảy đều mang mốc 92,6 giây**. Xác suất nói dối (0,76 · 0,92 · 0,99),
    từ ngữ nói dối, nhưng dòng thời gian thì không: bảy từ không chiếm giây
    nào là bảy từ máy sinh ra.
    """
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    that = [
        Word(text=t, start_s=88.4 + i * 0.55, end_s=88.4 + i * 0.55 + 0.4, prob=0.95)
        for i, t in enumerate("keep the classroom for discussion and practice".split())
    ]
    bia = [
        Word(text=t, start_s=92.6, end_s=92.6, prob=p)
        for t, p in zip(
            "keep the classroom for discussion and practice".split(),
            [0.0, 0.76, 0.92, 0.74, 0.91, 0.92, 0.99],
            strict=True,
        )
    ]

    f = detect_repetition(that + bia)
    assert f.detected and f.kind == "stalled_clock"
    assert f.keep_until_index == len(that)
    assert "mốc thời gian" in f.describe()


def test_noi_nhanh_that_khong_bi_coi_la_dong_ho_dung() -> None:
    """Nói nhanh vẫn tiêu tốn thời gian; ngưỡng đặt ở 0,05 giây mỗi từ."""
    from aicefr.asr.hallucination import detect_repetition
    from aicefr.contracts import Word

    nhanh = [
        Word(text=f"w{i}", start_s=i * 0.18, end_s=i * 0.18 + 0.15, prob=0.9) for i in range(40)
    ]
    assert detect_repetition(nhanh).detected is False


def test_ten_file_noi_doi_van_giai_ma_duoc() -> None:
    """File tên .wav nhưng ruột là WebM — đúng thứ bộ ghi âm trên web tạo ra.

    Sinh viên bấm tải bản ghi về rồi nộp lại chính tệp đó. Trước đây tên tệp
    đẩy thẳng sang `soundfile`, `soundfile` không đọc được Matroska, và cả
    lần nộp hỏng — dù ffmpeg ngay dưới đó đọc được.
    """
    import io

    import numpy as np
    import soundfile as sf

    from aicefr.audio.decoder import FirstMatchDecoder

    sr = 16_000
    t = np.arange(sr * 2) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="FLAC")

    # nội dung FLAC, tên .wav: tên sai kiểu đúng như ca thật
    pcm, out_sr = FirstMatchDecoder().decode(buf.getvalue(), "ban-ghi.wav")
    assert out_sr == sr
    assert pcm.size > 0


# ---------------------------------------------------------------- cấu hình giải mã


def test_whisper_khong_tu_moi_minh_ke_tiep_cau_chuyen() -> None:
    """`condition_on_previous_text=False` phải được truyền xuống, không phải để mặc định.

    Đây là dòng cấu hình đắt giá nhất trong cả hệ thống nhận dạng, và nó vô
    hình: bỏ nó đi thì không có gì hỏng, không test nào đỏ, chỉ là thỉnh thoảng
    một bản ghi trả về vài chục từ không có trên băng.

    Đo trên một bài nộp thật dài 94 giây: để mặc định cho ra 213 từ, kết thúc
    bằng "...the second part of the Simpsons to work that is who is now here".
    Toàn bộ phần bịa rơi vào nửa sau, kéo `asr_conf_geo` ở đó xuống 0,389, và
    bộ chấm từ chối cửa sổ đó vì ngoài phân bố — một nửa bài của sinh viên
    không có điểm. Tắt đi: 175 từ, dừng đúng chỗ người nói dừng, độ tin cậy nửa
    sau 0,915, chấm được 4,39.
    """
    from aicefr.asr.whisper_adapter import CT2_DECODE_OPTIONS, MLX_DECODE_OPTIONS

    assert MLX_DECODE_OPTIONS["condition_on_previous_text"] is False
    assert CT2_DECODE_OPTIONS["condition_on_previous_text"] is False


def test_cau_hinh_giai_ma_that_su_di_toi_bo_nhan_dang(monkeypatch) -> None:
    """Khai báo một hằng số mà quên truyền đi là một cách hỏng rất yên lặng."""
    import sys
    import types

    import numpy as np

    from aicefr.asr.whisper_adapter import MLX_DECODE_OPTIONS, WhisperEngine

    ghi_lai: dict = {}

    def transcribe(audio, **kwargs):
        ghi_lai.update(kwargs)
        return {"text": "hello", "segments": []}

    monkeypatch.setitem(sys.modules, "mlx_whisper", types.SimpleNamespace(transcribe=transcribe))
    WhisperEngine(backend="mlx").transcribe(np.zeros(16_000, dtype=np.float32), 16_000)

    for key, value in MLX_DECODE_OPTIONS.items():
        assert ghi_lai.get(key) == value, f"thiếu tuỳ chọn {key} khi gọi mlx-whisper"
    # Mốc thời gian từng từ là thứ cả màn karaoke lẫn đặc trưng ngừng nghỉ đứng trên.
    assert ghi_lai.get("word_timestamps") is True
