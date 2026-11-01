"""Regressions for the review of D039-D043 (13/10/2026).

Each test replays the scenario that went wrong before the fix.
"""

from __future__ import annotations

from aicefr import maintenance_cli
from aicefr.contracts import Assessment, Band, Response, ResponseStatus
from aicefr.pronunciation.vietnamese import Pattern, opportunities
from aicefr.storage.repository import Repository

# ------------------------------------------------- maintenance on a wrong store


def test_orphan_cleanup_refuses_a_store_without_its_tables(tmp_path, capsys) -> None:
    """A mistyped store opened empty: every recording would look like an orphan."""
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    recording = uploads / "r1.wav"
    recording.write_bytes(b"RIFF")

    code = maintenance_cli.main(
        ["--db", str(tmp_path / "typo.db"), "orphans", "--uploads", str(uploads), "--delete"]
    )

    assert code == 2
    assert "chưa có collection" in capsys.readouterr().err
    assert recording.exists()


def test_orphan_cleanup_runs_on_the_real_store(tmp_path, capsys) -> None:
    db = tmp_path / "core.db"
    Repository(db)
    from aicefr.storage.lesson_repository import LessonRepository

    LessonRepository(db, seed=False)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    assert maintenance_cli.main(["--db", str(db), "orphans", "--uploads", str(uploads)]) == 0
    assert "Không có tệp ghi âm mồ côi" in capsys.readouterr().out


# ------------------------------------------------- a late write never undoes a result


def _queued(rid: str) -> Response:
    return Response(response_id=rid, status=ResponseStatus.QUEUED, config_version="v1")


def _completed(rid: str, score: float) -> Response:
    return Response(
        response_id=rid,
        status=ResponseStatus.COMPLETED,
        config_version="v1",
        assessment=Assessment(overall_0_6=score, overall_band=Band.B1, model_version="m"),
    )


def test_the_overdue_sweep_does_not_fail_a_response_that_just_finished(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3", account_id="acc1")
    repo.save(_completed("r1", 3.0), "SV-001", "P3", account_id="acc1", must_exist=True)

    changed = repo.set_status(
        "r1", ResponseStatus.FAILED, only_from=(ResponseStatus.QUEUED, ResponseStatus.RUNNING)
    )

    assert changed is False
    assert repo.get("r1").status == ResponseStatus.COMPLETED


def test_the_sweep_still_fails_a_response_that_waits(tmp_path) -> None:
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3", account_id="acc1")
    assert repo.set_status(
        "r1", ResponseStatus.FAILED, only_from=(ResponseStatus.QUEUED, ResponseStatus.RUNNING)
    )
    assert repo.get("r1").status == ResponseStatus.FAILED


def test_a_second_worker_result_does_not_replace_the_first(tmp_path) -> None:
    """A redelivered job: the worker's write lands only on a response still waiting."""
    repo = Repository(tmp_path / "a.db")
    repo.save(_queued("r1"), "SV-001", "P3", account_id="acc1")
    assert repo.save(_completed("r1", 3.0), "SV-001", "P3", account_id="acc1", must_exist=True)

    again = repo.save(_completed("r1", 5.0), "SV-001", "P3", account_id="acc1", must_exist=True)

    assert again is False
    assert repo.get("r1").assessment.overall_0_6 == 3.0


# ------------------------------------------------- D039: what a word gives a chance to show


def test_words_spelt_like_an_ending_are_not_endings() -> None:
    for word in ("need", "speed", "hundred", "shed"):
        assert Pattern.ED_ENDING not in opportunities(word), word
    for word in ("was", "his", "this", "always", "news"):
        assert Pattern.S_ENDING not in opportunities(word), word
    assert Pattern.ED_ENDING in opportunities("agreed")
    assert Pattern.ED_ENDING in opportunities("worked")
    assert Pattern.S_ENDING in opportunities("books")


def test_letters_that_are_not_said_are_not_final_consonants() -> None:
    for word in ("how", "new", "for", "here", "high", "oh"):
        assert Pattern.FINAL_CONSONANT not in opportunities(word), word
    for word in ("much", "fish", "with", "cat"):
        assert Pattern.FINAL_CONSONANT in opportunities(word), word


# ------------------------------------------------- D041: what counts as a review done

# ------------------------------------------------- D042: a pair is one instrument
