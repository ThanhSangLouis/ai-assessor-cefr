"""Where the scoring artifacts live, and which bytes are trusted (W7-S01).

The scoring models and their calibration are statistics derived from the
Speak & Improve Corpus 2025, whose licence forbids publishing them without
CUP&A's permission. So they are not part of the code: they sit in a folder
outside Git, named by `AICEFR_MODEL_DIR`, and are read only when their SHA-256
matches a value pinned here -- a file swapped on disk is refused, never scored
with.

Tests set `AICEFR_MODEL_DIR` to `tests/fixtures/models`, synthetic artifacts
with the same shape and no corpus statistics (`tools/make_fake_models.py`), and
pin their hashes through `AICEFR_MODEL_PINS` ("name=sha256,..."). The pins in
this file are the real artifacts'; an extra pin can be added the same way, so
an administrator can activate a new model without a release.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MODEL_DIR_ENV = "AICEFR_MODEL_DIR"
PINS_ENV = "AICEFR_MODEL_PINS"

# The real artifacts (ThanhSangLouis/ai-assessor-cefr@0853c95; the same files
# the submission repository pins for M05 and M09).
PINNED_SHA256: dict[str, str] = {
    "ridge_resp_v2": "7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a",
    "ridge_resp_v1": "77da78ee1980a5e48b66e4a8f537124de64ac45d1a5e3b016d7e2940e29e68d3",
    "ridge_v3": "a765573b1bcbd291fd5676e844e67e9a5524183c86e58cc7a044bca70adcb465",
    "ridge_resp_v2_cal": "e19a59779e2933bae8922db8e75774ead2780fd017c784b4636f284cb2f92a1f",
    "conformal_resp_v2": "3c09d2583a26e8cc057c0cf36dfb7637d15dfdc901cf00c4e25faef9ce6ef885",
    "conformal_resp_v2_cal": "6c9879d910c0901a151bb88828847eb348fe5823a1495725b57a8799b745a6fb",
}


class ArtifactError(FileNotFoundError):
    """No usable artifact: the folder is not set, the file is missing, or its hash is wrong."""


def model_dir() -> Path:
    """The folder `AICEFR_MODEL_DIR` names; ArtifactError when it is not set."""
    raw = os.getenv(MODEL_DIR_ENV, "").strip()
    if not raw:
        raise ArtifactError(f"chưa đặt {MODEL_DIR_ENV}: thư mục artifact mô hình nằm ngoài repo")
    return Path(raw).expanduser()


def pins() -> dict[str, str]:
    """The pinned hashes, with any added through AICEFR_MODEL_PINS."""
    out = dict(PINNED_SHA256)
    for item in os.getenv(PINS_ENV, "").split(","):
        name, _, digest = item.strip().partition("=")
        if name and digest:
            out[name.strip()] = digest.strip().lower()
    return out


def artifact_path(name: str) -> Path:
    return model_dir() / f"{name}.json"


def available() -> list[str]:
    """Names of the artifacts in the folder, pinned or not (the admin's model list)."""
    try:
        folder = model_dir()
    except ArtifactError:
        return []
    return sorted(p.stem for p in folder.glob("*.json"))


def read_bytes(name: str) -> bytes:
    """The artifact's bytes, after checking them against the pinned hash."""
    path = artifact_path(name)
    if not path.is_file():
        raise ArtifactError(f"không tìm thấy artifact {path}")
    raw = path.read_bytes()
    expected = pins().get(name)
    if expected is None:
        raise ArtifactError(f"artifact {name!r} chưa được ghim SHA-256, không dùng")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise ArtifactError(f"SHA-256 của {path.name} là {digest}, khác giá trị ghim {expected}")
    return raw


def read_json(name: str) -> dict:
    return json.loads(read_bytes(name).decode("utf-8"))
