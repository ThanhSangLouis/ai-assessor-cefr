"""The administrator's side of the assessment service: models, thresholds, exports, erasure.

FR-08, FR-34..FR-36, FR-80 (D042). Erasure starts here, where the recordings
are, and reaches the learning service for lesson attempts (D043): one
participant's data goes everywhere it is, or the administrator is told what
could not be reached.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, require_login
from aicefr.api.schemas import EraseRequest, QueueItem
from aicefr.observability import count
from aicefr.platform.bus import BusTimeout
from aicefr.platform.rpc import RemoteError
from aicefr.qc import audio_qc
from aicefr.research.reliable_change import MIN_PAIRS as MIN_RETEST_PAIRS
from aicefr.research.reliable_change import (
    RELIABLE_CHANGE_VERSION,
    RETEST_WINDOW,
    retest_pairs,
    sem_from_pairs,
)
from aicefr.services.core.assessment.context import (
    ACTIVE_MODEL_KEY,
    CONFIG_VERSION,
    MEASUREMENT_ERROR_KEY,
    QC_CONFIG_KEY,
    QC_EDITABLE,
    active_model_name,
    active_qc,
    measurement_error,
    scorable_duration,
    svc,
)
from aicefr.storage.auth_repository import Account

logger = logging.getLogger(__name__)
router = APIRouter()

HEALTH_QUEUE = "speech.health"


@router.get("/api/v1/responses", response_model=list[QueueItem], tags=["admin"])
def list_responses(
    limit: int = Query(200, ge=1, le=500), account: Account = ADMIN_ONLY
) -> list[QueueItem]:
    """Every response with the machine's band."""
    return [QueueItem(**r) for r in svc().repo.list_all(limit)]


@router.get("/api/v1/stats", tags=["admin"])
def stats_summary(account: Account = ADMIN_ONLY) -> dict:
    return svc().repo.stats()


# ================================================================= models (FR-36)


@router.get("/api/v1/admin/models", tags=["admin"])
def list_models(account: Account = ADMIN_ONLY) -> list[dict]:
    """Scoring artifacts on disk, with the metrics each one reports. FR-36."""
    from aicefr.scoring import artifacts
    from aicefr.scoring.scorer import IncompatibleModelError, RidgeScorer, load_model

    active = active_model_name()
    out = []
    for stem in artifacts.available():
        # The CV+ calibration artifact (D022) sits in the same folder but is not a
        # scoring model; listing it as "incompatible" would mean nothing.
        if stem.startswith("conformal_"):
            continue
        try:
            m = load_model(stem)
        except Exception as e:  # noqa: BLE001 - a broken artifact must be listed, not hidden
            out.append({"name": stem, "usable": False, "error": str(e)})
            continue
        # An artifact can load fine and still be unusable here: `ridge_v3` was
        # fitted on whole exam sittings and reports a higher correlation for a
        # different task. Saying so stops an administrator activating it.
        try:
            RidgeScorer(stem)
            compatible, why = True, None
        except IncompatibleModelError as e:
            compatible, why = False, str(e)
        out.append(
            {
                "name": stem,
                "usable": True,
                "model_version": m.get("model_version"),
                "feature_version": m.get("feature_version"),
                "calibration_version": m.get("calibration_version"),
                "unit_of_inference": m.get("unit_of_inference"),
                "cv_pcc": m.get("cv_pcc"),
                "cv_rmse": m.get("cv_rmse"),
                "train_n": m.get("train_n"),
                "compatible": compatible,
                "incompatible_reason": why,
                "active": stem == active,
            }
        )
    return out


@router.post("/api/v1/admin/models/{name}/activate", tags=["admin"])
def activate_model(name: str, account: Account = ADMIN_ONLY) -> dict:
    """Grade new responses with a different artifact. FR-36.

    It refuses an artifact that does not load or is not compatible, it does not
    touch results already stored, and it is audited. The speech service builds
    the new pipeline on the next job, since every job names its model.
    """
    from aicefr.scoring import artifacts
    from aicefr.scoring.scorer import IncompatibleModelError, RidgeScorer

    if name not in artifacts.available():
        raise HTTPException(404, f"không có tệp mô hình tên {name!r}")
    try:
        scorer = RidgeScorer(name)
    except IncompatibleModelError as e:
        raise HTTPException(409, f"mô hình không dùng được cho hệ thống này: {e}") from e
    except Exception as e:  # noqa: BLE001 - a broken artifact must be reported, not raised raw
        raise HTTPException(422, f"không nạp được mô hình: {e}") from e

    repo = svc().repo
    before = active_model_name()
    repo.set_config(ACTIVE_MODEL_KEY, name, scorer.model_version, account.pseudonym)
    repo.write_audit(account.pseudonym, "model.activate", name, f"truoc={before} sau={name}")
    count("model_activations_total")
    return {
        "active_model": name,
        "previous_model": before,
        "model_version": scorer.model_version,
        "calibration_version": scorer.calibration_version,
        "note": "Báo cáo đã lưu giữ nguyên phiên bản mô hình cũ của chúng.",
    }


# ================================================================= QC thresholds (FR-08)


@router.get("/api/v1/admin/config", tags=["admin"])
def read_config(account: Account = ADMIN_ONLY) -> dict:
    """Thresholds currently in force, and which of them may be changed. FR-08."""
    t, version = active_qc()
    row = svc().repo.get_config(QC_CONFIG_KEY)
    return {
        "qc_config_version": version,
        "editable_here": True,
        "editable_fields": {k: {"min": lo, "max": hi} for k, (lo, hi) in QC_EDITABLE.items()},
        "candidate_thresholds": True,
        "changed_by": row.updated_by if row else None,
        "changed_at": row.updated_at if row else None,
        "duration_s": {
            "reject_below": t.min_duration_s,
            "review_below": t.review_duration_s,
            "reject_above": t.max_duration_s,
        },
        "clipping_ratio": {
            "review_at": t.review_clipping_ratio,
            "reject_above": t.max_clipping_ratio,
        },
        "silence_ratio": {
            "review_at": t.review_silence_ratio,
            "reject_above": t.max_silence_ratio,
        },
        "snr_db": {"reject_below": t.min_snr_db, "review_below": t.review_snr_db},
        "max_bytes": audio_qc.MAX_BYTES,
    }


@router.post("/api/v1/admin/config", tags=["admin"])
def update_config(changes: dict[str, float], account: Account = ADMIN_ONLY) -> dict:
    """Change QC thresholds while the system runs. FR-08.

    Every change bumps the version, which every later report carries; ranges and
    the ordering of the three levels are checked, since a REVIEW band beneath the
    REJECT band silently disables the middle outcome.
    """
    unknown = sorted(set(changes) - set(QC_EDITABLE))
    if unknown:
        raise HTTPException(422, f"không sửa được ở đây: {unknown}")

    current, _ = active_qc()
    merged = {k: getattr(current, k) for k in QC_EDITABLE}
    for key, value in changes.items():
        lo, hi = QC_EDITABLE[key]
        if not lo <= float(value) <= hi:
            raise HTTPException(422, f"{key}={value} nằm ngoài khoảng cho phép [{lo}, {hi}]")
        merged[key] = float(value)

    if not merged["min_duration_s"] <= merged["review_duration_s"] <= merged["max_duration_s"]:
        raise HTTPException(
            422,
            "thứ tự ngưỡng thời lượng sai: cần min_duration_s <= review_duration_s"
            " <= max_duration_s",
        )
    if merged["review_clipping_ratio"] > merged["max_clipping_ratio"]:
        raise HTTPException(422, "review_clipping_ratio phải nhỏ hơn hoặc bằng max_clipping_ratio")
    if merged["review_silence_ratio"] > merged["max_silence_ratio"]:
        raise HTTPException(422, "review_silence_ratio phải nhỏ hơn hoặc bằng max_silence_ratio")
    if merged["min_snr_db"] > merged["review_snr_db"]:
        raise HTTPException(422, "min_snr_db phải nhỏ hơn hoặc bằng review_snr_db")

    version = f"qc-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    repo = svc().repo
    repo.set_config(QC_CONFIG_KEY, json.dumps(merged, sort_keys=True), version, account.pseudonym)
    repo.write_audit(
        account.pseudonym,
        "qc.config",
        version,
        " ".join(f"{k}={changes[k]}" for k in sorted(changes)),
    )
    count("qc_config_changes_total")
    return {"qc_config_version": version, "thresholds": merged}


# ================================================================= erasure (FR-35)


@router.get("/api/v1/admin/erase/{speaker_id}", tags=["admin"])
def preview_erasure(speaker_id: str, account: Account = ADMIN_ONLY) -> dict:
    """What an erasure would remove. Changes nothing. FR-35."""
    s = svc()
    preview = s.repo.erasure_preview(speaker_id)
    who = s.peers.identity.by_pseudonym(pseudonym=speaker_id)
    preview["lesson_attempts"] = (
        s.peers.learning.count_attempts(account_id=who["account_id"]) if who else 0
    )
    return preview


@router.post("/api/v1/admin/erase", tags=["admin"])
def erase_participant(body: EraseRequest, account: Account = ADMIN_ONLY) -> dict:
    """Delete one participant's recordings and reports. Irreversible. FR-35.

    The id has to be sent twice and the two have to match: this deletes audio
    from disk and cannot be undone.
    """
    if body.speaker_id != body.confirm_speaker_id:
        raise HTTPException(422, "hai lần nhập mã không khớp")
    s = svc()
    result = s.repo.erase_speaker(body.speaker_id, account.account_id)
    who = s.peers.identity.by_pseudonym(pseudonym=body.speaker_id)
    result["lesson_attempts"] = 0
    if who:
        # Lesson attempts (D025) live in the learning service; erase them there,
        # recordings included.
        try:
            result["lesson_attempts"] = s.peers.learning.erase_account(account_id=who["account_id"])
        except RemoteError as e:
            logger.error("erasure did not reach the learning service: %s", e)
            raise HTTPException(
                502,
                "đã xoá bài đánh giá nhưng chưa xoá được bài học: dịch vụ bài học không trả lời."
                " Chạy lại thao tác xoá khi dịch vụ đã chạy.",
            ) from e
        s.repo.forget_study_participant(who["account_id"])
        if s.classrooms is not None:
            s.classrooms.forget_account(who["account_id"])
        if s.replays is not None:
            s.replays.forget_account(who["account_id"])
    result["cutoff_note"] = (
        "Đã xóa bản ghi và báo cáo. Dữ liệu đã dùng để huấn luyện các mô hình phát hành "
        "trước thời điểm này KHÔNG bị gỡ khỏi mô hình đó; việc gỡ chỉ áp dụng cho các "
        "lần huấn luyện sau."
    )
    return result


# ================================================================= measurement error (D042)


class MeasurementIn(BaseModel):
    use: str = Field(pattern="^(retest|manual)$")
    sem: float | None = Field(default=None, gt=0, le=3)
    note: str | None = Field(default=None, max_length=300)


@router.get("/api/v1/admin/measurement-error", tags=["admin"])
def get_measurement_error(account: Account = ADMIN_ONLY) -> dict:
    """The SEM in force and the one today's test-retest pairs would give. FR-80."""
    pairs = retest_pairs(svc().repo.scored_assessments(machine_only=True))
    return {
        "current": measurement_error(),
        "candidate": {"pairs": len(pairs), "sem": sem_from_pairs(pairs)},
        "min_pairs": MIN_RETEST_PAIRS,
        "window_hours": int(RETEST_WINDOW.total_seconds() // 3600),
    }


@router.post("/api/v1/admin/measurement-error", tags=["admin"])
def set_measurement_error(body: MeasurementIn, account: Account = ADMIN_ONLY) -> dict:
    """Put an SEM in force: from today's test-retest pairs, or typed in with a source. FR-80.

    A typed value must say where it comes from (`note`), so the progress page
    never shows a bar for "progress" whose origin nobody can trace.
    """
    repo = svc().repo
    if body.use == "retest":
        pairs = retest_pairs(repo.scored_assessments(machine_only=True))
        sem = sem_from_pairs(pairs)
        if sem is None:
            raise HTTPException(
                422,
                f"Mới có {len(pairs)} cặp bài thử lại, cần ít nhất {MIN_RETEST_PAIRS} cặp.",
            )
        value = {"sem": round(sem, 4), "source": "retest", "pairs": len(pairs), "note": None}
    else:
        if body.sem is None or not (body.note or "").strip():
            raise HTTPException(422, "Nhập sai số đo và ghi rõ nguồn của con số.")
        value = {"sem": body.sem, "source": "manual", "pairs": None, "note": body.note.strip()}
    value["set_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    repo.set_config(
        MEASUREMENT_ERROR_KEY, json.dumps(value), RELIABLE_CHANGE_VERSION, account.pseudonym
    )
    repo.write_audit(
        account.pseudonym, "measurement_error.set", value["source"], f"sem={value['sem']}"
    )
    return value


# ================================================================= health


def speech_health() -> dict:
    """What the speech service reports about its recogniser; empty when it does not answer."""
    try:
        return svc().bus.call(HEALTH_QUEUE, {}, timeout=5.0)
    except BusTimeout:
        return {}
    except Exception:  # noqa: BLE001 - a broker that is down is an answer, not a 500
        logger.exception("speech health check failed")
        return {}


@router.get("/api/v1/health", tags=["admin"])
def health(account: Account = Depends(require_login)) -> dict:
    from aicefr.scoring.scorer import load_model

    # The model that will grade the response: the duration the submission page
    # accepts is that model's, not the default's.
    m = load_model(active_model_name())
    speech = speech_health()
    return {
        "status": "ok",
        "asr_engine": speech.get("asr_engine"),
        "asr_is_real": bool(speech.get("asr_is_real")),
        # "fallback" or a fixed temperature; None for the fake engine.
        "asr_decoding": speech.get("asr_decoding"),
        "config_version": CONFIG_VERSION,
        "model_version": m["model_version"],
        "unit_of_inference": m["unit_of_inference"],
        "cv_pcc": m["cv_pcc"],
        # How long a recording this model can actually score, so the interface
        # can warn before a 94-second upload rather than after.
        "scorable_duration_s": scorable_duration(m),
        # FR-39: the interface hides the record button when this is false.
        "recording_enabled": bool(speech.get("recording_enabled")),
    }
