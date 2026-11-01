"""Hoi quy cho cac loi critical/high tim duoc khi review toan repo ngay 03/10/2026.

Moi test o day TAI HIEN dung kich ban da gay loi truoc khi sua.
"""

from __future__ import annotations

from aicefr.contracts import Assessment, Band, Response, ResponseStatus, Transcript, Word
from aicefr.storage.repository import Repository

# Dat mat khau thu vao hang so nhu cac file test khac: gitleaks bao nham
# "password": "<chuoi>" la khoa bi mat.
PASSWORD = "matkhau-kiem-thu"


def _queued(rid: str) -> Response:
    return Response(response_id=rid, status=ResponseStatus.QUEUED, config_version="v1")


def _scored(rid: str, text: str = "my name is Nguyen Van A") -> Response:
    return Response(
        response_id=rid,
        status=ResponseStatus.COMPLETED,
        config_version="v1",
        asr=Transcript(
            text=text,
            words=[Word(text="my", start_s=0.0, end_s=0.2, prob=0.9)],
            engine="fake",
            model_version="fake-v1",
        ),
        assessment=Assessment(overall_0_6=3.2, overall_band=Band.B1, model_version="m"),
    )


# ------------------------------------------------- muc 1: bai da xoa song lai


def test_erasing_a_speaker_also_beats_a_late_worker(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3", account_id="acc1")
    repo.erase_speaker("SV-001", actor_id="admin")
    repo.save(_scored("r1"), "SV-001", "P3", account_id="acc1", must_exist=True)
    assert repo.get("r1") is None


def test_a_worker_still_stores_its_result_normally(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3", account_id="acc1")
    assert repo.save(_scored("r1"), "SV-001", "P3", must_exist=True) is True
    got = repo.get("r1")
    assert got is not None and got.status is ResponseStatus.COMPLETED


def test_a_late_worker_does_not_overwrite_a_finished_response(tmp_path) -> None:
    """Hai worker cung mot bai: ket qua thu hai den sau khong de len ket qua da xong."""
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3")
    repo.save(_scored("r1", "first"), "SV-001", "P3", must_exist=True)
    assert repo.save(_scored("r1", "second"), "SV-001", "P3", must_exist=True) is False
    assert repo.get("r1").asr.text == "first"


# ------------------------------------------------- muc 2: bom giai nen FLAC/OGG


def test_a_tiny_flac_holding_ten_minutes_is_cut_like_the_ffmpeg_path() -> None:
    """600 giay im lang nen FLAC chi vai chuc KB; khong duoc giai ma het."""
    import io

    import numpy as np
    import soundfile as sf

    from aicefr.audio.decoder import MAX_DECODE_SECONDS, SoundFileDecoder

    buf = io.BytesIO()
    sf.write(buf, np.zeros(16_000 * 600, dtype=np.float32), 16_000, format="FLAC")
    data = buf.getvalue()
    assert len(data) < 200_000  # nho, nhung mo ra thanh 10 phut

    pcm, sr = SoundFileDecoder().decode(data, "bom.flac")
    assert pcm.size / sr <= MAX_DECODE_SECONDS


def test_an_absurd_header_is_refused_before_reading(tmp_path) -> None:
    import io

    import numpy as np
    import pytest
    import soundfile as sf

    from aicefr.audio.decoder import DecodeError, SoundFileDecoder

    buf = io.BytesIO()
    sf.write(buf, np.zeros((100, 16), dtype=np.float32), 16_000, format="WAV")
    with pytest.raises(DecodeError):
        SoundFileDecoder().decode(buf.getvalue(), "nhieu-kenh.wav")


# ------------------------------------------------- muc 3: gia mao X-Forwarded-For


def test_the_container_does_not_trust_forwarded_headers_from_anyone() -> None:
    import pathlib

    cmd = pathlib.Path("Dockerfile").read_text(encoding="utf-8")
    assert '"--forwarded-allow-ips", "*"' not in cmd


def test_the_login_counter_has_a_memory_ceiling() -> None:
    """Moi request mot IP gia khong duoc lam bo dem phinh mai."""
    from aicefr.infra.limits import SlidingWindowCounter

    w = SlidingWindowCounter(max_keys=100)
    for i in range(5_000):
        w.allow(f"10.0.{i // 256}.{i % 256}", now=1000.0, limit=10)
    assert len(w) <= 100


def test_the_login_counter_still_limits_one_address() -> None:
    from aicefr.infra.limits import SlidingWindowCounter

    w = SlidingWindowCounter()
    assert all(w.allow("1.2.3.4", now=0.0 + i, limit=10) for i in range(10))
    assert not w.allow("1.2.3.4", now=11.0, limit=10)
    assert w.allow("1.2.3.4", now=75.0, limit=10)  # cua so da troi qua


# ------------------------------------------------- muc 4: khoa tai khoan song song


def test_parallel_wrong_passwords_still_lock_the_account(tmp_path) -> None:
    """20 lan sai song song truoc day chi dem duoc 1 va khong bao gio khoa."""
    from concurrent.futures import ThreadPoolExecutor

    from aicefr.storage.auth_repository import (
        MAX_FAILED_ATTEMPTS,
        AccountLocked,
        AuthRepository,
        Role,
    )

    repo = AuthRepository(tmp_path / "auth.db")
    repo.create_account("GV-01", PASSWORD, Role.TEACHER)

    def attempt(_):
        try:
            return repo.login("GV-01", "sai")
        except AccountLocked:
            return "locked"

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(attempt, range(20)))

    row = repo.get_by_pseudonym("GV-01")
    assert row["failed_attempts"] >= MAX_FAILED_ATTEMPTS
    assert row["locked_until"] is not None


# ------------------------------------------------- muc 6: accounts_cli va AICEFR_DB


def test_the_account_tool_writes_where_the_app_reads(tmp_path, monkeypatch) -> None:
    from aicefr import accounts_cli, config
    from aicefr.storage.auth_repository import AuthRepository

    db = tmp_path / "data" / "aicefr.db"
    db.parent.mkdir()
    monkeypatch.setenv("AICEFR_DB", str(db))
    monkeypatch.delenv("AICEFR_CORE_DB")  # the core service on AICEFR_DB
    config.get_settings.cache_clear()
    accounts_cli.main(
        ["them", "--but-danh", "GV-09", "--vai-tro", "teacher", "--mat-khau", "x" * 12]
    )
    assert AuthRepository(db).get_by_pseudonym("GV-09") is not None


# ------------------------------------------------- muc 7: bai khong cham duoc


def _unscored(rid: str) -> Response:
    from aicefr.contracts import ReasonCode

    return Response(
        response_id=rid,
        status=ResponseStatus.REVIEW_REQUIRED,
        config_version="v1",
        reasons=[ReasonCode.LANGUAGE_NOT_ENGLISH],
    )


def test_a_teacher_can_score_a_response_the_machine_could_not(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_unscored("r1"), "SV-001", "P3", account_id="acc1")
    out = repo.apply_review("r1", "gv1", 3.0, None, "nghe lai: noi tieng Anh ro")
    assert out is not None and out.status is ResponseStatus.COMPLETED
    a = repo.get("r1").assessment
    assert a.model_version == "teacher" and a.teacher_verified
    assert a.overall_0_6 == 3.0 and a.overall_band is Band.B1


def test_an_unscored_response_needs_a_score_or_band(tmp_path) -> None:
    import pytest

    from aicefr.storage.repository import InvalidStateError

    repo = Repository(tmp_path / "a.db")
    repo.save(_unscored("r1"), "SV-001", "P3")
    with pytest.raises(InvalidStateError):
        repo.apply_review("r1", "gv1", None, None, "khong nhap gi ca")


def test_a_teacher_can_close_an_unscorable_response(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_unscored("r1"), "SV-001", "P3", account_id="acc1")
    out = repo.close_unscorable("r1", "gv1", "noi tieng Viet, moi nop lai")
    assert out.status is ResponseStatus.REJECTED
    got = repo.get("r1")
    assert got.status is ResponseStatus.REJECTED and got.assessment is None
    assert repo.cohort_stats()["agreement"]["band_kept"] == 0  # dong bai khong phai "dong y"


def test_closing_is_refused_for_a_scored_response(tmp_path) -> None:
    import pytest

    from aicefr.storage.repository import InvalidStateError

    repo = Repository(tmp_path / "a.db")
    report = _scored("r1")
    report.status = ResponseStatus.REVIEW_REQUIRED
    repo.save(report, "SV-001", "P3")
    with pytest.raises(InvalidStateError):
        repo.close_unscorable("r1", "gv1", "khong duoc dong bai da cham")


def test_the_close_endpoint_takes_an_unscored_response_out_of_the_queue(tmp_path) -> None:
    import importlib

    from fastapi.testclient import TestClient

    from aicefr.api import main as m
    from aicefr.storage.auth_repository import Role

    importlib.reload(m)
    m.repo.save(_unscored("r9"), "SV-001", "P3")
    # D071: a response of nobody's class is the administrator's to close.
    m.app.state.auth_repo.create_account("QT-01", PASSWORD, Role.ADMIN)
    c = TestClient(m.app)
    c.post("/api/v1/auth/login", json={"pseudonym": "QT-01", "password": PASSWORD})
    r = c.post("/api/v1/review/r9/close", json={"reason": "khong phai tieng Anh"})
    assert r.status_code == 200
    assert m.repo.get("r9").status is ResponseStatus.REJECTED


# ------------------------------------------------- muc 8: ty le dong thuan


def test_correcting_only_the_score_counts_as_a_band_change(tmp_path) -> None:
    """Sua 3,2 (B1) thanh 2,0 (A2): truoc day van tinh la 'giu nguyen band'."""
    repo = Repository(tmp_path / "a.db")
    report = _scored("r1")
    report.status = ResponseStatus.REVIEW_REQUIRED
    repo.save(report, "SV-001", "P3")
    repo.apply_review("r1", "gv1", 2.0, None, "doc ngap ngung nhieu hon may nghe")
    agreement = repo.cohort_stats()["agreement"]
    assert agreement["band_changed"] == 1 and agreement["band_kept"] == 0
    assert repo.review_history("r1")[0].new_band is Band.A2


def test_a_restart_fails_every_pending_job_not_only_old_ones(monkeypatch) -> None:
    """Bai vua nop 1 phut truoc ma server restart thi job da mat; khong duoc ket mai."""
    import importlib

    from fastapi.testclient import TestClient

    from aicefr.api import main as m

    importlib.reload(m)
    m.repo.save(_queued("moi-nop"), "SV-001", "P3")
    with TestClient(m.app):  # chay lifespan, nhu luc khoi dong
        pass
    assert m.repo.get("moi-nop").status is ResponseStatus.FAILED


def test_a_job_running_past_the_timeout_is_closed_and_its_late_result_dropped(
    monkeypatch,
) -> None:
    import importlib
    from datetime import UTC, datetime, timedelta

    from aicefr import config
    from aicefr.api import main as m
    from aicefr.services.core.assessment import scoring

    monkeypatch.setenv("AICEFR_JOB_TIMEOUT", "60")
    config.get_settings.cache_clear()
    importlib.reload(m)
    m.repo.save(_queued("treo"), "SV-001", "P3")
    assert m.repo.mark_running("treo")

    later = datetime.now(UTC) + timedelta(seconds=61)
    assert scoring.sweep_overdue(later) == ["treo"]
    assert m.repo.get("treo").status is ResponseStatus.FAILED
    # The speech service answers at last: the result is dropped, the response stays FAILED.
    assert m.repo.save(_scored("treo"), "SV-001", "P3", must_exist=True) is False
    assert m.repo.get("treo").status is ResponseStatus.FAILED


def test_a_job_within_the_timeout_is_left_alone(monkeypatch) -> None:
    import importlib

    from aicefr.api import main as m
    from aicefr.services.core.assessment import scoring

    importlib.reload(m)
    m.repo.save(_queued("dang-chay"), "SV-001", "P3")
    assert m.repo.mark_running("dang-chay")
    assert scoring.sweep_overdue() == []
    assert m.repo.get("dang-chay").status is ResponseStatus.RUNNING
