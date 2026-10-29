"""Offline synthetic checks for the Week 1 data-management plan.

The script creates only temporary synthetic records and removes the temporary
directory automatically. It does not inspect or modify participant data.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

CONFIG_VERSION = "week1-dmp-check-v1"
REQUIRED_MANIFEST_FIELDS = {
    "participant_id",
    "speaker_id",
    "response_id",
    "task_id",
    "audio_id",
    "prompt_version",
    "consent_version",
    "qc_status",
}
FORBIDDEN_LOG_FIELDS = {
    "name",
    "email",
    "student_id",
    "mssv",
    "audio",
    "transcript",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_manifest(record: dict[str, Any]) -> list[str]:
    return sorted(REQUIRED_MANIFEST_FIELDS.difference(record))


def assert_no_direct_identity(root: Path, forbidden_values: set[str]) -> None:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        searchable = path.name + "\n" + path.read_bytes().decode("utf-8", errors="ignore")
        lowered = searchable.lower()
        for value in forbidden_values:
            if value.lower() in lowered:
                raise AssertionError(f"Direct identity leaked into research workspace: {path.name}")


def assert_log_is_minimal(log_record: dict[str, Any]) -> None:
    leaked_fields = FORBIDDEN_LOG_FIELDS.intersection(key.lower() for key in log_record)
    if leaked_fields:
        raise AssertionError(f"Forbidden log fields: {sorted(leaked_fields)}")


def run_checks() -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    temp_parent = Path(__file__).resolve().parent / ".tmp"
    temp_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="week1_dmp_synthetic_", dir=temp_parent) as temp_name:
        root = Path(temp_name)
        identity_root = root / "secure_identity"
        research_root = root / "research_data"
        backup_root = root / "backup"

        participant_id = "PTEST-0001"
        speaker_id = "STEST-0001"
        response_id = "RTEST-0001"
        direct_identity = {
            "participant_id": participant_id,
            "name": "Synthetic Participant",
            "email": "synthetic.invalid@example.invalid",
            "student_id": "SYNTHETIC-NOT-REAL",
        }
        forbidden_values = {
            direct_identity["name"],
            direct_identity["email"],
            direct_identity["student_id"],
        }

        write_json(identity_root / "identity_map.synthetic.json", direct_identity)

        manifest = {
            "participant_id": participant_id,
            "speaker_id": speaker_id,
            "response_id": response_id,
            "task_id": "TASK_A",
            "audio_id": "ATEST-0001",
            "prompt_version": "prompt-a-v1",
            "consent_version": "synthetic-consent-v1",
            "qc_status": "PASS_SYNTHETIC",
        }
        manifest_path = research_root / "metadata" / f"{response_id}.json"
        write_json(manifest_path, manifest)
        audio_path = research_root / "raw_audio" / f"{response_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"RIFF-SYNTHETIC-NOT-AUDIO")
        rating_path = research_root / "ratings_raw" / f"{response_id}.json"
        write_json(
            rating_path,
            {
                "response_id": response_id,
                "rater_id": "RATER-TEST-01",
                "rubric_version": "rubric-v0-synthetic",
                "rating_status": "SYNTHETIC_ONLY",
                "evidence_ids": [],
            },
        )

        assert_no_direct_identity(research_root, forbidden_values)
        results.append(("identity_separation", "PASS"))

        if validate_manifest(manifest):
            raise AssertionError("Valid manifest was rejected")
        invalid_manifest = dict(manifest)
        invalid_manifest.pop("prompt_version")
        if validate_manifest(invalid_manifest) != ["prompt_version"]:
            raise AssertionError("Missing manifest field was not rejected deterministically")
        results.append(("boundary_schema", "PASS"))

        log_record = {
            "participant_id": participant_id,
            "response_id": response_id,
            "config_version": CONFIG_VERSION,
            "status": "SYNTHETIC_CHECK",
            "reason_code": "NONE",
        }
        assert_log_is_minimal(log_record)
        write_json(research_root / "logs" / "synthetic_check.json", log_record)
        assert_no_direct_identity(research_root, forbidden_values)
        results.append(("log_privacy", "PASS"))

        checksum_before = sha256(audio_path)
        snapshot_path = backup_root / "snapshot" / audio_path.name
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(audio_path, snapshot_path)
        if sha256(snapshot_path) != checksum_before:
            raise AssertionError("Backup checksum mismatch")
        if sha256(audio_path) != checksum_before:
            raise AssertionError("Raw artifact changed during snapshot")
        results.append(("snapshot_checksum_restore", "PASS"))

        deletion_targets = [manifest_path, audio_path, rating_path]
        for target in deletion_targets:
            target.unlink()
        (identity_root / "identity_map.synthetic.json").unlink()
        deletion_log = {
            "participant_id": participant_id,
            "request_type": "SYNTHETIC_WITHDRAWAL_TEST",
            "status": "COMPLETED",
            "reason_code": "TEST_ONLY",
            "config_version": CONFIG_VERSION,
            "deleted_artifact_count": len(deletion_targets) + 1,
        }
        assert_log_is_minimal(deletion_log)
        write_json(research_root / "logs" / "deletion.synthetic.json", deletion_log)
        if any(target.exists() for target in deletion_targets):
            raise AssertionError("A withdrawal target still exists")
        if (identity_root / "identity_map.synthetic.json").exists():
            raise AssertionError("Synthetic identity mapping still exists")
        results.append(("withdrawal_deletion", "PASS"))

    results.append(("temporary_workspace_cleanup", "PASS"))
    results.append(("encryption_at_rest", "NOT_TESTED_REQUIRES_APPROVED_STORAGE"))
    results.append(("role_access_control", "NOT_TESTED_REQUIRES_REAL_ACCOUNTS"))
    if temp_parent.exists() and not any(temp_parent.iterdir()):
        temp_parent.rmdir()
    return results


def main() -> int:
    print(f"config_version={CONFIG_VERSION}")
    for check, status in run_checks():
        print(f"{check}={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
