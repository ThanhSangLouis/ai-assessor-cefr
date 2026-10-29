"""Hoi quy cho cac loi muc medium (10-20) tim duoc khi review toan repo ngay 03/10/2026.

Moi test tai hien dung kich ban da gay loi truoc khi sua.
"""

from __future__ import annotations

import pytest

from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    Evidence,
    EvidenceKind,
    Response,
    ResponseStatus,
    Transcript,
    Word,
)
from aicefr.retention import REDACTED_NOTE, apply_retention, orphaned_recordings
from aicefr.storage.repository import InvalidStateError, Repository

# Hang so thay vi viet thang vao JSON: gitleaks bao nham la khoa bi mat.
PASSWORD = "matkhau-kiem-thu"


def _report(rid: str, status: ResponseStatus = ResponseStatus.COMPLETED) -> Response:
    return Response(
        response_id=rid,
        status=status,
        config_version="v1",
        asr=Transcript(
            text="um my name is nguyen van a",
            words=[Word(text="um", start_s=0.0, end_s=0.2, prob=0.4)],
            engine="fake",
            model_version="fake-v1",
        ),
        assessment=Assessment(
            overall_0_6=3.2,
            overall_band=Band.B1,
            model_version="ridge_resp_v2",
            evidence=[
                Evidence(
                    criterion=Criterion.FLUENCY,
                    kind=EvidenceKind.FILLER,
                    start_s=0.0,
                    end_s=0.2,
                    snippet="um my name is nguyen van a",
                    note="Từ ngập ngừng 'um'.",
                ),
                Evidence(
                    criterion=Criterion.FLUENCY,
                    kind=EvidenceKind.PAUSE,
                    start_s=1.0,
                    end_s=3.0,
                    snippet="nguyen van a",
                    note="Ngừng 2.0 giây.",
                ),
            ],
        ),
    )


# ------------------------------------------- muc 11: retention con trich doan


def test_retention_also_removes_the_speech_quoted_in_evidence(tmp_path) -> None:
    repo = Repository(tmp_path / "t.db")
    repo.save(_report("r1"), "SV-001", "P3")
    apply_retention(repo, days=-1, dry_run=False)
    ev = repo.get("r1").assessment.evidence
    assert all(e.snippet is None for e in ev)
    assert ev[0].note == REDACTED_NOTE  # ghi chu trich nguyen tu 'um'
    assert ev[1].note == "Ngừng 2.0 giây."  # chi co so, giu nguyen
    assert "nguyen" not in repo.get("r1").model_dump_json()


def test_retention_clears_the_audio_pointer_of_a_rejected_recording(tmp_path) -> None:
    """Bai QC tu choi khong co transcript: truoc day file bi xoa ma con tro van con."""
    repo = Repository(tmp_path / "t.db")
    audio = tmp_path / "x.wav"
    audio.write_bytes(b"RIFF")
    repo.save(
        Response(response_id="r1", status=ResponseStatus.REJECTED, config_version="v1"),
        "SV-001",
        "P3",
        audio_path=str(audio),
    )
    apply_retention(repo, days=-1, dry_run=False)
    assert not audio.exists()
    assert repo.audio_path_of("r1") is None


# ------------------------------------------- muc 12: orphans xoa nham


def test_a_relative_audio_path_is_not_mistaken_for_an_orphan(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "live.wav").write_bytes(b"RIFF")
    repo = Repository(tmp_path / "t.db")
    repo.save(_report("r1"), "SV-001", "P3", audio_path="uploads/live.wav")  # tuong doi
    assert orphaned_recordings(repo, uploads.resolve()) == []


def test_an_upload_in_progress_is_not_an_orphan(tmp_path) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "abc.part").write_bytes(b"RIFF")
    assert orphaned_recordings(Repository(tmp_path / "t.db"), uploads) == []


# ------------------------------------------- muc 10: hai quyet dinh cung duoc chap nhan


def test_two_concurrent_decisions_cannot_both_win(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    repo = Repository(tmp_path / "t.db")
    for i in range(30):
        repo.save(_report(f"r{i}", ResponseStatus.REVIEW_REQUIRED), "SV-001", "P3")

    def decide(args):
        rid, who = args
        try:
            repo.apply_review(rid, who, None, None, "giu nguyen ket qua")
            return 1
        except InvalidStateError:
            return 0

    jobs = [(f"r{i}", who) for i in range(30) for who in ("gv1", "gv2")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        wins = list(pool.map(decide, jobs))
    assert sum(wins) == 30
    for i in range(30):
        assert len(repo.review_history(f"r{i}")) == 1


# ------------------------------------------- muc 19: diem va band mau thuan


def test_a_score_and_a_band_that_disagree_are_refused(tmp_path) -> None:
    repo = Repository(tmp_path / "t.db")
    repo.save(_report("r1", ResponseStatus.REVIEW_REQUIRED), "SV-001", "P3")
    with pytest.raises(InvalidStateError):
        repo.apply_review("r1", "gv1", 5.5, "A2", "diem cao ma band thap")
    assert repo.get("r1").status is ResponseStatus.REVIEW_REQUIRED


# ------------------------------------------- muc 20: export cat truoc khi loc


def test_the_research_export_filters_before_it_limits(tmp_path) -> None:
    repo = Repository(tmp_path / "t.db")
    for i in range(3):
        repo.save(_report(f"cu{i}"), "SV-X", "P3", account_id="khong-dong-y")
    for i in range(2):
        repo.save(_report(f"moi{i}"), "SV-Y", "P3", account_id="dong-y")
    rows = repo.research_rows({"dong-y"}, limit=2)
    assert {r["response_id"] for r in rows} == {"moi0", "moi1"}


# ------------------------------------------- muc 14: transcript lot vao log


def test_a_repetition_loop_is_logged_without_the_words(tmp_path, caplog) -> None:
    import logging

    import numpy as np

    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor

    secret = "toi ten la nguyen van a"
    engine = FakeAsrEngine(transcript="hello " + " ".join([secret] * 12))
    req = ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P3",
        audio_path="x",
        prompt_version="v1",
        config_version="v1",
    )
    t = np.arange(16_000 * 40) / 16_000
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    with caplog.at_level(logging.WARNING):
        ResponseProcessor(engine, vad=EnergyVad()).process(req, pcm, 16_000)
    assert "repetition loop" in caplog.text
    assert "nguyen" not in caplog.text


# ------------------------------------------- muc 15: uu tien luyen tap khi khong cham


def test_no_practice_priorities_are_given_when_the_machine_did_not_score(tmp_path) -> None:
    import numpy as np

    from aicefr.asr.fake import FakeAsrEngine
    from aicefr.asr.vad import EnergyVad
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor

    req = ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P3",
        audio_path="x",
        prompt_version="v7",
        config_version="v1",
    )
    t = np.arange(16_000 * 40) / 16_000
    pcm = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    # Ban chep gia lap 24 tu cho bai 40 giay: ngoai phan bo, may khong cham.
    r = ResponseProcessor(FakeAsrEngine(), vad=EnergyVad()).process(req, pcm, 16_000)
    assert r.assessment is not None and r.assessment.overall_0_6 is None
    assert r.assessment.priorities == []
    # muc 16: ban de di theo ket qua
    assert r.prompt_version == "v7"


# ------------------------------------------- muc 13: nguong band theo mo hinh cua bai


def test_band_thresholds_follow_the_model_that_scored_the_response() -> None:
    from aicefr.scoring.band_map import thresholds_of
    from aicefr.scoring.scorer import load_model
    from aicefr.storage.repository import _band_thresholds

    old = thresholds_of(load_model("ridge_resp_v1")["band_thresholds"])
    assert _band_thresholds("ridge_resp_v1") == old
    assert _band_thresholds("teacher") == thresholds_of(load_model()["band_thresholds"])
    assert _band_thresholds(None) == thresholds_of(load_model()["band_thresholds"])


def test_the_model_list_hides_the_calibration_artifact(tmp_path) -> None:
    import importlib

    from fastapi.testclient import TestClient

    from aicefr.api import main as m
    from aicefr.storage.auth_repository import Role

    importlib.reload(m)
    m.app.state.auth_repo.create_account("QT-01", PASSWORD, Role.ADMIN)
    c = TestClient(m.app)
    c.post("/api/v1/auth/login", json={"pseudonym": "QT-01", "password": PASSWORD})
    names = {x["name"] for x in c.get("/api/v1/admin/models").json()}
    assert "conformal_resp_v2" not in names and "ridge_resp_v2" in names


# ------------------------------------------- muc 18: AICEFR_MAX_UPLOAD


def test_the_upload_limit_comes_from_the_environment(monkeypatch) -> None:
    import importlib
    import inspect

    from aicefr import config
    from aicefr.qc import audio_qc
    from aicefr.services.core.assessment import responses_api

    monkeypatch.setenv("AICEFR_MAX_UPLOAD", str(3 * 1024 * 1024))
    config.get_settings.cache_clear()
    try:
        importlib.reload(audio_qc)
        assert audio_qc.MAX_BYTES == 3 * 1024 * 1024
        # The submission reads the limit there, not from a copy taken at import.
        assert "audio_qc.MAX_BYTES" in inspect.getsource(responses_api.submit_response)
    finally:
        monkeypatch.delenv("AICEFR_MAX_UPLOAD")
        config.get_settings.cache_clear()
        importlib.reload(audio_qc)


# ------------------------------------------- muc 17: train_scorer khong tai lap artifact


def test_the_training_script_writes_the_metadata_of_the_deployed_model() -> None:
    import importlib.util
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("train_scorer", root / "tools/train_scorer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # import khong duoc chdir hay doc sys.argv
    deployed = json.loads(mod.DEFAULT_OUT.read_text(encoding="utf-8"))
    for key, value in mod.ARTIFACT_META.items():
        assert deployed[key] == value, key
