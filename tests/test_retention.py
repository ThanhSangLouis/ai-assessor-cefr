"""Storage limitation: recordings must not accumulate for ever.

A system that deletes only on request is not compliant with anything. These
tests pin down what a retention sweep removes and, just as importantly, what it
keeps.
"""

from __future__ import annotations

import json

import pytest

from aicefr.contracts import Assessment, Band, Response, Status, Transcript, Word
from aicefr.retention import apply_retention, backup, orphaned_recordings, restore_backup
from aicefr.storage.repository import Repository


def _report(rid: str) -> Response:
    return Response(
        response_id=rid,
        status=Status.COMPLETED,
        config_version="v1",
        asr=Transcript(
            text="i think online learning is flexible",
            words=[Word(text="i", start_s=0.0, end_s=0.2, prob=0.9)],
            engine="whisper-mlx",
            model_version="large-v3-turbo",
        ),
        assessment=Assessment(
            overall_0_6=4.25, overall_band=Band.B2, model_version="ridge_resp_v1"
        ),
    )


@pytest.fixture
def repo_with_recording(tmp_path):
    repo = Repository(tmp_path / "t.db")
    audio = tmp_path / "old.wav"
    audio.write_bytes(b"RIFF" + b"x" * 2048)
    repo.save(_report("old1"), "SV-001", "P3", account_id="acc", audio_path=str(audio))
    return repo, audio


def test_a_dry_run_changes_nothing(repo_with_recording) -> None:
    """Deleting personal data is right, but it is irreversible.

    The default must be the one that cannot destroy anything by accident: an
    operator who runs this by mistake should get a report, not a loss.
    """
    repo, audio = repo_with_recording
    report = apply_retention(repo, days=-1, dry_run=True)

    assert report.audio_deleted == 1
    assert report.dry_run is True
    assert audio.is_file(), "xem trước mà đã xoá tệp"
    assert repo.get("old1").asr.text != ""


def test_a_sweep_removes_the_recording_and_the_transcript(repo_with_recording) -> None:
    repo, audio = repo_with_recording
    apply_retention(repo, days=-1, dry_run=False)

    assert not audio.is_file()
    stored = repo.get("old1")
    assert stored.asr.text == ""
    assert stored.asr.words == []


def test_a_sweep_keeps_the_academic_result(repo_with_recording) -> None:
    """The score is the record the assessment existed to produce.

    Retention removes the evidence, not the outcome: a student's band from last
    semester stays, the recording of their voice does not.
    """
    repo, _audio = repo_with_recording
    apply_retention(repo, days=-1, dry_run=False)

    stored = repo.get("old1")
    assert stored.assessment.overall_0_6 == 4.25
    assert stored.assessment.overall_band is Band.B2
    # Provenance survives too: the report still says which engine ran.
    assert stored.asr.engine == "whisper-mlx"


def test_a_sweep_clears_rows_written_before_the_field_was_renamed(tmp_path) -> None:
    """`Transcript.text` used to be called `transcript`. Old rows still say so.

    The sweep works on the raw JSON, not on the model, so it does not get the
    validation alias for free. A version that looked only for the new key would
    report `transcripts_cleared == 0` on a database full of old recordings and
    leave every one of them on disk -- passing silently, because nothing in the
    fixture set uses the old spelling.
    """
    repo = Repository(tmp_path / "t.db")
    audio = tmp_path / "legacy.wav"
    audio.write_bytes(b"RIFF" + b"x" * 2048)
    repo.save(_report("legacy1"), "SV-002", "P3", account_id="acc", audio_path=str(audio))

    # Rewrite the stored row the way the pre-rename code wrote it.
    responses = repo.col("response")
    raw = json.loads(responses.find_one({"response_id": "legacy1"})["report_json"])
    raw["asr"]["transcript"] = raw["asr"].pop("text")
    responses.update_one(
        {"response_id": "legacy1"}, {"$set": {"report_json": json.dumps(raw, ensure_ascii=False)}}
    )

    # The alias keeps the old row readable...
    assert repo.get("legacy1").asr.text == "i think online learning is flexible"

    # ...and the sweep still empties it.
    report = apply_retention(repo, days=-1, dry_run=False)
    assert report.transcripts_cleared == 1
    assert repo.get("legacy1").asr.text == ""
    assert not audio.is_file()


def test_a_sweep_is_recorded_in_the_audit_log(repo_with_recording) -> None:
    repo, _audio = repo_with_recording
    apply_retention(repo, days=-1, dry_run=False)
    assert any(e["action"] == "RETENTION_SWEEP" for e in repo.audit())


def test_recent_recordings_are_left_alone(repo_with_recording) -> None:
    repo, audio = repo_with_recording
    report = apply_retention(repo, days=365, dry_run=False)
    assert report.considered == 0
    assert audio.is_file()


def test_orphaned_recordings_are_found(tmp_path) -> None:
    """Files nothing points at are the dangerous ones.

    Nothing lists them, no erasure request finds them, and they are somebody's
    voice. They appear whenever a submission fails after the file is written.
    """
    repo = Repository(tmp_path / "t.db")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    known = uploads / "known.wav"
    known.write_bytes(b"RIFF")
    (uploads / "orphan.wav").write_bytes(b"RIFF")
    repo.save(_report("r1"), "SV-001", "P3", audio_path=str(known))

    found = orphaned_recordings(repo, uploads)
    assert [p.name for p in found] == ["orphan.wav"]


def test_backup_produces_a_readable_copy(tmp_path) -> None:
    """A backup is only worth something once it has been restored and read."""
    repo = Repository(tmp_path / "t.db")
    repo.save(_report("r1"), "SV-001", "P3")

    copy = backup(repo, tmp_path / "backups" / "aicefr.json")
    assert copy.is_file()
    restored = Repository(tmp_path / "restored.db")
    assert restore_backup(restored, copy) > 0
    assert restored.get("r1") is not None
    with pytest.raises(ValueError):
        restore_backup(repo, copy)  # never merged into a store holding data


def test_report_json_stays_valid_after_a_sweep(repo_with_recording) -> None:
    repo, _audio = repo_with_recording
    apply_retention(repo, days=-1, dry_run=False)
    raw = repo.col("response").find_one({"response_id": "old1"})
    json.loads(raw["report_json"])  # phải phân tích được
