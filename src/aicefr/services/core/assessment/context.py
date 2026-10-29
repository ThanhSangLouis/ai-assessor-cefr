"""What every router of the assessment service shares (D043).

The stores of this service, the bus, the other services' facades, and the few
rules several routers apply: the blind-rating guard of D030, the QC thresholds
and the scoring model in force, the measurement error of D042. Wired once when
the service is built (`configure`), read through `svc()`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from aicefr.api.deps import require_plan
from aicefr.billing.plans import PlanFeature
from aicefr.config import Settings
from aicefr.platform.bus import MessageBus
from aicefr.ports import BlobStore
from aicefr.qc import audio_qc
from aicefr.services import Peers
from aicefr.storage.auth_repository import Account
from aicefr.storage.classroom_repository import ClassroomRepository
from aicefr.storage.rating_repository import RatingRepository
from aicefr.storage.replay_repository import ReplayRepository
from aicefr.storage.repository import Repository
from aicefr.storage.study_repository import StudyRepository
from aicefr.storage.task_repository import TaskRepository

CONFIG_VERSION = "v1"
# Preparation time before an assessed answer (D028): the 30 seconds of the
# survey protocol, KE_HOACH_KHAO_SAT.md §5.2.
PREP_SECONDS = 30

ACTIVE_MODEL_KEY = "active_model"
QC_CONFIG_KEY = "qc_thresholds"
MEASUREMENT_ERROR_KEY = "measurement_error"

# Only these may be changed at runtime, and each carries the range it must stay
# inside. A threshold set to an impossible value does not fail loudly -- it
# quietly rejects or accepts every recording, which is far harder to notice.
QC_EDITABLE: dict[str, tuple[float, float]] = {
    "min_duration_s": (1.0, 600.0),
    "review_duration_s": (1.0, 600.0),
    "max_duration_s": (10.0, 3600.0),
    "review_clipping_ratio": (0.0, 1.0),
    "max_clipping_ratio": (0.0, 1.0),
    "review_silence_ratio": (0.0, 1.0),
    "max_silence_ratio": (0.0, 1.0),
    "min_snr_db": (-20.0, 60.0),
    "review_snr_db": (-20.0, 60.0),
}


@dataclass
class Services:
    settings: Settings
    repo: Repository
    tasks: TaskRepository
    ratings: RatingRepository
    studies: StudyRepository
    blobs: BlobStore
    bus: MessageBus
    peers: Peers
    classrooms: ClassroomRepository | None = None  # D054
    replays: ReplayRepository | None = None  # D056

    @property
    def upload_dir(self) -> Path:
        return self.settings.upload_dir


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured when the service is built
        raise RuntimeError("assessment service used before configure()")
    return _services


def plan_allows(feature: PlanFeature) -> None:
    """403 when the plan in force does not include `feature` (D034)."""
    require_plan(svc().peers.billing, feature)


# ================================================================= blind rating (D030)


def blind(account: Account, response_id: str) -> None:
    """Refuse a teacher the machine's view of a response they still have to rate blind (D030).

    Seeing the machine's score first is exactly the anchoring the blind rating
    exists to avoid; once the rating is submitted, the response opens again.
    """
    if account.is_staff and svc().ratings.has_open(account.account_id, response_id):
        raise HTTPException(
            403,
            "bài này đang trong đợt chấm mù của bạn: chấm xong ở trang Chấm mù rồi mới xem"
            " được kết quả của máy",
        )


def saw(account: Account, response_id: str, via: str) -> None:
    """Note that a teacher or administrator now has the machine's result in view (D030).

    They are no longer blind to this response: they are not drawn to rate it
    in a later batch, and a sheet of theirs that is still owed -- in a batch
    closed for now -- stops taking a rating. Students are never raters.
    """
    if account.is_staff:
        svc().ratings.saw_machine(account.account_id, response_id, via)


# ================================================================= what is in force


def active_qc() -> tuple[audio_qc.QcThresholds, str]:
    """The QC thresholds in force, and the version label that names them.

    Falls back to the values in the SRS when nothing has been changed, so a
    fresh install behaves exactly as the specification describes.
    """
    row = svc().repo.get_config(QC_CONFIG_KEY)
    if row is None:
        return audio_qc.QcThresholds(), audio_qc.QC_CONFIG_VERSION
    return audio_qc.QcThresholds(**json.loads(row.value)), row.version


def active_model_name() -> str:
    """Which scoring artifact new responses are graded with. FR-36."""
    from aicefr.scoring.scorer import DEFAULT_MODEL

    row = svc().repo.get_config(ACTIVE_MODEL_KEY)
    return row.value if row else DEFAULT_MODEL


def measurement_error() -> dict | None:
    """The SEM in force, with where it came from; None until an administrator sets one (D042)."""
    row = svc().repo.get_config(MEASUREMENT_ERROR_KEY)
    return json.loads(row.value) if row else None


def scorable_duration(model: dict) -> dict:
    """The recording length this artifact can score, including its tolerance.

    Same arithmetic as the out-of-distribution guard, read from the same two
    numbers, so the warning shown before submission and the refusal shown after
    it can never disagree.
    """
    try:
        i = model["feature_order"].index("total_dur")
    except (KeyError, ValueError):
        return {}
    lo, hi = float(model["feature_lo"][i]), float(model["feature_hi"][i])
    tol = float(model.get("ood_tolerance", 0.5))
    span = hi - lo
    return {
        "trained_low": round(lo, 1),
        "trained_high": round(hi, 1),
        "accepted_low": round(max(0.0, lo - tol * span), 1),
        "accepted_high": round(hi + tol * span, 1),
    }
