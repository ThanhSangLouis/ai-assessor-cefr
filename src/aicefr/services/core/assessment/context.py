"""What every router of the assessment service shares (D043).

The stores of this service, the bus, the other services' facades, and the few
rules several routers apply: the QC thresholds and the scoring model in force,
Wired once when the service is built
(`configure`), read through `svc()`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from aicefr.config import Settings
from aicefr.platform.bus import MessageBus
from aicefr.ports import BlobStore
from aicefr.qc import audio_qc
from aicefr.services import Peers
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.classroom_repository import ClassroomRepository
from aicefr.storage.replay_repository import ReplayRepository
from aicefr.storage.repository import Repository
from aicefr.storage.task_repository import TaskRepository

CONFIG_VERSION = "v1"
# Preparation time before an assessed answer (D028): the 30 seconds of the
# survey protocol, KE_HOACH_KHAO_SAT.md §5.2.
PREP_SECONDS = 30

ACTIVE_MODEL_KEY = "active_model"
QC_CONFIG_KEY = "qc_thresholds"

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


# ================================================================= who sees whose work (D071)


def can_view(account: Account, owner_id: str | None) -> bool:
    """Whether this account may read a response owned by `owner_id`.

    D071: an administrator reads every response; a teacher reads the work of
    the members of the classes they teach, and nothing else -- a student in no
    class is the administrator's to review; a student reads their own.
    """
    if account.role is Role.ADMIN:
        return True
    if not owner_id:
        return False
    if account.role is Role.TEACHER:
        rooms = svc().classrooms
        return rooms is not None and rooms.teaches(account.account_id, owner_id)
    return owner_id == account.account_id


def in_view(account: Account, response_id: str) -> None:
    """404 unless `can_view`: someone else's response is not confirmed to exist."""
    if not can_view(account, svc().repo.owner_of(response_id)):
        raise HTTPException(404, "không tìm thấy bài này")


def students_in_view(account: Account) -> set[str] | None:
    """The owners whose work a staff account reviews; None for every owner (admin)."""
    if account.role is Role.ADMIN:
        return None
    rooms = svc().classrooms
    return rooms.students_of(account.account_id) if rooms is not None else set()


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
