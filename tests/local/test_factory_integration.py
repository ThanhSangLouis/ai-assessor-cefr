from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from aicefr.api.student import SubmitRequest
from aicefr.contracts import (
    ActorRole,
    AssessmentStatus,
    Band,
    ReasonCode,
    ResponseStatus,
    ReviewAction,
)
from aicefr.local.__main__ import main
from aicefr.local.app import _LazyVad, create_runtime, load_config
from aicefr.report.sqlite import SQLiteReportRepository
from aicefr.review.service import ReviewActionRequest
from aicefr.review.sqlite import SQLiteReviewRepository
from aicefr.scoring.artifact import RIDGE_RESP_V2_SHA256

MODEL_DIR = os.environ.get("AICEFR_MODEL_DIR")
MODEL_PATH = Path(MODEL_DIR) / "ridge_resp_v2.json" if MODEL_DIR else None


def _config(*, model_path: Path | None) -> dict[str, object]:
    qc = {
        "version": "test-qc-v1",
        "accepted_formats": ["wav"],
        "max_input_bytes": 2_000_000,
        "min_duration_s": 1.0,
        "max_duration_s": 10.0,
        "max_input_sample_rate_hz": 16_000,
        "silence_threshold": 0.01,
        "clipping_threshold": 0.99,
        "review_silence_ratio": 0.5,
        "reject_silence_ratio": 0.95,
        "review_clipping_ratio": 0.1,
        "reject_clipping_ratio": 0.5,
    }
    result: dict[str, object] = {
        "consent_version": "consent-current",
        "allowed_media_types": ["audio/wav"],
        "tasks": [{"task_id": "fixture-speaking", "task_version": "v1"}],
        "qc": qc,
        "vad_enabled": True,
    }
    if model_path is not None:
        result["model_artifact"] = str(model_path)
    return result


def _wav(*, silence_ratio: float) -> bytes:
    rate = 16_000
    count = rate * 2
    audio = np.zeros(count, dtype=np.float32)
    active_start = int(count * silence_ratio)
    active_count = count - active_start
    audio[active_start:] = 0.2 * np.sin(
        np.arange(active_count, dtype=np.float32) * (2 * np.pi * 220 / rate)
    )
    output = io.BytesIO()
    sf.write(output, audio, rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def _submit(runtime, audio: bytes):
    actor_id = "fixture-student"
    token = runtime.auth.login(actor_id, "fixture-password")
    return runtime.app._student_api.submit(
        token,
        SubmitRequest(
            task_id="fixture-speaking",
            task_version="v1",
            consent_version="consent-current",
            filename="response.wav",
            content_type="audio/wav",
            audio_bytes=audio,
        ),
    )


def _provision_student(runtime) -> None:
    actor = runtime.auth.bootstrap_fixture_account(
        "fixture-student", ActorRole.STUDENT, "fixture-password"
    )
    runtime.consents.activate(actor, "consent-current")


def test_factory_missing_model_is_not_evaluated_and_persists_report_and_review(tmp_path):
    missing_path = tmp_path / "missing-model.json"
    runtime = create_runtime(
        tmp_path / "data-missing-model", config=_config(model_path=missing_path)
    )
    try:
        _provision_student(runtime)
        status = _submit(runtime, _wav(silence_ratio=0.0))
        report = SQLiteReportRepository(runtime.store).get(status.response_id)
        candidate = SQLiteReviewRepository(runtime.store).get(status.response_id)
        response = runtime.store.get_response(status.response_id)
        assert response is not None and response.status is ResponseStatus.REVIEW_REQUIRED
        assert report is not None
        assert report.assessment_status is AssessmentStatus.NOT_EVALUATED
        assert report.overall_score is None and report.overall_band is None
        assert ReasonCode.MODEL_VERSION_MISSING in report.reasons
        assert candidate is not None
        assert ReasonCode.MODEL_VERSION_MISSING in candidate.reasons
    finally:
        runtime.close()


@pytest.mark.skipif(
    MODEL_PATH is None or not MODEL_PATH.is_file(), reason="artifact path unavailable"
)
def test_factory_review_qc_bypasses_asr_pins_model_and_reopens_reviewed_report(tmp_path):
    runtime = create_runtime(tmp_path / "data-review", config=_config(model_path=MODEL_PATH))
    try:
        _provision_student(runtime)
        pipeline = runtime.app._student_api._service._pipeline
        assert pipeline._scorer.artifact.sha256 == RIDGE_RESP_V2_SHA256
        assert pipeline._asr._engine is None
        assert isinstance(pipeline._extractor._vad, _LazyVad)
        assert pipeline._extractor._vad._engine is None

        status = _submit(runtime, _wav(silence_ratio=0.7))
        assert pipeline._asr._engine is None
        response = runtime.store.get_response(status.response_id)
        report = SQLiteReportRepository(runtime.store).get(status.response_id)
        candidate = SQLiteReviewRepository(runtime.store).get(status.response_id)
        assert response is not None and response.status is ResponseStatus.REVIEW_REQUIRED
        assert report is not None
        assert report.assessment_status is AssessmentStatus.NOT_EVALUATED
        assert report.overall_score is None and report.overall_band is None
        assert ReasonCode.QC_SILENCE_REVIEW in report.reasons
        assert candidate is not None

        student_actor = runtime.store.get_account("fixture-student").actor
        runtime.auth.bootstrap_fixture_account(
            "fixture-teacher", ActorRole.TEACHER, "teacher-password"
        )
        token = runtime.auth.login("fixture-teacher", "teacher-password")
        claimed = runtime.app._review_api.claim(token, response.response_id, candidate.revision)
        runtime.app._review_api.decide(
            token,
            response.response_id,
            ReviewActionRequest(
                action=ReviewAction.OVERRIDE,
                expected_revision=claimed.revision,
                final_band=Band.B1,
                reason="Kiểm thử do nhóm tạo",
            ),
        )
        final_report = SQLiteReportRepository(runtime.store).get(response.response_id)
        assert final_report is not None and final_report.teacher_verified
        assert final_report.overall_score is None and final_report.overall_band is None
        assert final_report.teacher_final is not None
        assert final_report.teacher_final.overall_band is Band.B1
        assert student_actor.actor_id == "fixture-student"
    finally:
        runtime.close()

    reopened = create_runtime(tmp_path / "data-review", config=_config(model_path=MODEL_PATH))
    try:
        persisted = SQLiteReportRepository(reopened.store).get(response.response_id)
        assert persisted is not None and persisted.teacher_verified
        assert persisted.teacher_final is not None
        assert persisted.teacher_final.overall_band is Band.B1
        persisted_response = reopened.store.get_response(response.response_id)
        assert persisted_response is not None
        assert persisted_response.status is ResponseStatus.REVIEW_REQUIRED
    finally:
        reopened.close()


def test_load_config_and_cli_fail_closed_for_malformed_or_unsafe_startup(tmp_path, capsys):
    malformed = tmp_path / "bad-config.json"
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(malformed)

    repo_path = Path(__file__).resolve().parents[2]
    result = main(["serve", "--data-dir", str(repo_path / "must-not-create"), "--demo"])
    assert result == 2
    assert str(repo_path) not in capsys.readouterr().err

    with pytest.raises(SystemExit) as unsafe_bind:
        main(
            [
                "serve",
                "--data-dir",
                str(tmp_path / "unsafe-bind-data"),
                "--demo",
                "--bind",
                "0.0.0.0",
            ]
        )
    assert unsafe_bind.value.code == 2
