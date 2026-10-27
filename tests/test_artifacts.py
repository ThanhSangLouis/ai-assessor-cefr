"""Scoring artifacts come from outside the repository and only with a pinned hash (W7-S01)."""

import shutil
from pathlib import Path

import pytest

from aicefr.scoring import artifacts
from aicefr.scoring.scorer import ModelNotFoundError, load_model

ROOT = Path(__file__).resolve().parents[1]


def test_no_artifact_ships_with_the_code() -> None:
    """Corpus statistics never sit in the package (Speak & Improve licence)."""
    assert not list((ROOT / "src").rglob("ridge_*.json"))
    assert not list((ROOT / "src").rglob("conformal_*.json"))


def test_without_a_folder_there_is_no_model(monkeypatch) -> None:
    monkeypatch.delenv(artifacts.MODEL_DIR_ENV)
    assert artifacts.available() == []
    with pytest.raises(ModelNotFoundError):
        load_model("ridge_resp_v2")


def test_a_file_changed_on_disk_is_refused(tmp_path, monkeypatch) -> None:
    for path in artifacts.model_dir().glob("*.json"):
        shutil.copy(path, tmp_path / path.name)
    target = tmp_path / "ridge_resp_v2.json"
    target.write_text(target.read_text(encoding="utf-8").replace("2.75", "2.70", 1))
    monkeypatch.setenv(artifacts.MODEL_DIR_ENV, str(tmp_path))
    with pytest.raises(artifacts.ArtifactError, match="khác giá trị ghim"):
        artifacts.read_json("ridge_resp_v2")


def test_an_unpinned_file_is_refused(tmp_path, monkeypatch) -> None:
    (tmp_path / "ridge_homemade.json").write_text("{}")
    monkeypatch.setenv(artifacts.MODEL_DIR_ENV, str(tmp_path))
    assert "ridge_homemade" in artifacts.available()
    with pytest.raises(artifacts.ArtifactError, match="chưa được ghim"):
        artifacts.read_json("ridge_homemade")


def test_a_pin_can_be_added_without_a_release(tmp_path, monkeypatch) -> None:
    import hashlib

    raw = b'{"model_version": "ridge_homemade"}'
    (tmp_path / "ridge_homemade.json").write_bytes(raw)
    monkeypatch.setenv(artifacts.MODEL_DIR_ENV, str(tmp_path))
    monkeypatch.setenv(artifacts.PINS_ENV, f"ridge_homemade={hashlib.sha256(raw).hexdigest()}")
    assert artifacts.read_json("ridge_homemade") == {"model_version": "ridge_homemade"}


def test_the_test_suite_runs_on_the_synthetic_artifacts() -> None:
    assert artifacts.model_dir() == ROOT / "tests" / "fixtures" / "models"
    assert "không lấy từ Speak & Improve" in load_model("ridge_resp_v2")["train_set"]
