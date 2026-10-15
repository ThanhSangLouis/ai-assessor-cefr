from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import pytest

from aicefr.lessons.model import StepKind, StepResult, StepResultStatus
from aicefr.lessons.review import first_review, review_again
from aicefr.lessons.seed import sample_catalogue, seed_sample
from aicefr.practice.bank import PRACTICE_MISSIONS
from aicefr.practice.contracts import (
    MissionMeasurement,
    PracticePurpose,
    PracticeResult,
    PracticeStatus,
)
from aicefr.storage.learning import (
    LearningAttemptState,
    LearningConflict,
    LearningRepository,
)
from aicefr.storage.sqlite import SQLiteStore


@pytest.fixture
def repository(tmp_path: Path):
    store = SQLiteStore(tmp_path / "data")
    store.connection.executemany(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES(?,?,?)",
        (("student", "student", "hash"), ("teacher", "teacher", "hash")),
    )
    return store, LearningRepository(store)


def _practice_result(mission, purpose: PracticePurpose) -> PracticeResult:
    return PracticeResult(
        mission_id=mission.mission_id,
        purpose=purpose,
        status=PracticeStatus.PASS,
        measurements=tuple(
            MissionMeasurement(
                goal_id=goal.goal_id,
                target=goal.target,
                status=PracticeStatus.PASS,
                measured_value=goal.target,
            )
            for goal in mission.goals
        ),
        rules_version=mission.rules_version,
        word_count=3,
        audio_duration_s=4,
        speaking_s=2.5,
    )


def _create_practice(repo, mission, key: str, sha: str, now: datetime):
    return repo.create_practice_attempt(
        "student",
        mission,
        PracticePurpose.PRACTICE,
        key,
        prompt_version=mission.prompt_version,
        blob_id=f"blob-{sha[:8]}",
        audio_content_type="audio/wav",
        sha256=sha,
        size_bytes=100,
        now=now,
    )


def test_long_idempotency_keys_do_not_alias_after_eighty_characters(repository):
    _, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    prefix = "k" * 96
    first = _create_practice(repo, mission, prefix + "a", "a" * 64, now)
    second = _create_practice(repo, mission, prefix + "b", "b" * 64, now)
    assert first.attempt_id != second.attempt_id


def test_idempotent_retry_reuses_original_snapshot_and_conflicting_payload_fails(repository):
    _, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    first = _create_practice(repo, mission, "stable-replay", "c" * 64, now)
    replay = _create_practice(repo, mission, "stable-replay", "c" * 64, now)
    assert replay.attempt_id == first.attempt_id
    changed = mission.model_copy(update={"prompt_version": "changed-prompt"})
    with pytest.raises(LearningConflict, match="different request"):
        repo.create_practice_attempt(
            "student",
            changed,
            PracticePurpose.PRACTICE,
            "stable-replay",
            prompt_version=changed.prompt_version,
            blob_id="another-blob",
            audio_content_type="audio/wav",
            sha256="c" * 64,
            size_bytes=100,
            now=now,
        )


def test_duplicate_blob_reference_rolls_back_attempt_row(repository):
    store, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    _create_practice(repo, mission, "blob-owner-a", "9" * 64, now)
    with pytest.raises(sqlite3.IntegrityError):
        _create_practice(repo, mission, "blob-owner-b", "9" * 64, now)
    assert (
        store.connection.execute(
            "SELECT COUNT(*) FROM practice_attempts WHERE idempotency_key IN "
            "('blob-owner-a','blob-owner-b')"
        ).fetchone()[0]
        == 1
    )


def test_audio_artifact_rejects_missing_attempt_or_wrong_owner(repository):
    store, _ = repository
    now = datetime.now(UTC).isoformat()
    with pytest.raises(sqlite3.IntegrityError, match="audio owner must match its attempt"):
        store.connection.execute(
            """INSERT INTO learning_audio_artifacts(
                   artifact_id,owner_id,attempt_kind,practice_attempt_id,step_attempt_id,
                   blob_id,content_type,sha256,size_bytes,created_at
               ) VALUES('orphan','student','practice','missing',NULL,'orphan-blob',
                        'audio/wav',?,1,?)""",
            ("a" * 64, now),
        )
    assert (
        store.connection.execute("SELECT COUNT(*) FROM learning_audio_artifacts").fetchone()[0] == 0
    )


def test_same_idempotency_key_across_two_connections_creates_one_attempt(repository):
    store, repo = repository
    mission = PRACTICE_MISSIONS[0]
    barrier = Barrier(2)

    def create_from_second_connection():
        second_store = SQLiteStore(store.data_dir)
        try:
            second_repo = LearningRepository(second_store)
            barrier.wait(timeout=5)
            return _create_practice(
                second_repo, mission, "concurrent-replay", "f" * 64, datetime.now(UTC)
            ).attempt_id
        finally:
            second_store.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_from_second_connection) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert results[0] == results[1]
    assert (
        store.connection.execute(
            "SELECT COUNT(*) FROM practice_attempts WHERE owner_id='student' "
            "AND idempotency_key='concurrent-replay'"
        ).fetchone()[0]
        == 1
    )


def test_sample_seed_is_ordered_idempotent_and_preserves_teacher_changes(repository):
    store, repo = repository
    now = datetime.now(UTC)
    first_hash = seed_sample(repo, now=now)
    path = repo.get_path("path-sample")
    assert path is not None and len(path.units) == 18
    lessons = store.connection.execute(
        "SELECT COUNT(*) FROM learning_lessons WHERE unit_id IN "
        "(SELECT unit_id FROM learning_units WHERE path_id='path-sample')"
    ).fetchone()[0]
    assert lessons == 31
    first_unit_lessons = store.connection.execute(
        "SELECT lesson_id FROM learning_lessons WHERE unit_id='unit-sample-a2' ORDER BY ordinal"
    ).fetchall()
    assert [row[0] for row in first_unit_lessons] == [
        "lesson-a2-neighborhood",
        "lesson-pr-flu-a2",
        "lesson-pr-ran-a2",
        "lesson-pr-acc-a2",
    ]

    writes_before = store.connection.total_changes
    assert seed_sample(repo, now=now) == first_hash
    assert store.connection.total_changes == writes_before

    store.connection.execute(
        "UPDATE learning_lessons SET title='Teacher title',content_hash='teacher-edit' "
        "WHERE lesson_id='lesson-a2-neighborhood'"
    )
    store.connection.execute(
        "UPDATE learning_lessons SET unit_id='unit-a2-education',ordinal=99 "
        "WHERE lesson_id='lesson-pr-flu-a2'"
    )
    path_value, units, seed_lessons = sample_catalogue()
    changed_path = path_value.model_copy(update={"content_version": "sample-layout-3"})
    repo.seed_sample_catalogue(
        changed_path,
        units,
        seed_lessons,
        layout=3,
        seed_version="sample-layout-3",
        now=now,
    )
    title = store.connection.execute(
        "SELECT title FROM learning_lessons WHERE lesson_id='lesson-a2-neighborhood'"
    ).fetchone()[0]
    moved_unit = store.connection.execute(
        "SELECT unit_id FROM learning_lessons WHERE lesson_id='lesson-pr-flu-a2'"
    ).fetchone()[0]
    assert title == "Teacher title"
    assert moved_unit == "unit-a2-education"
    manifest_result = store.connection.execute(
        "SELECT result_json FROM learning_seed_manifest WHERE seed_name='path-sample'"
    ).fetchone()[0]
    assert '"skipped":31' in manifest_result


def test_same_free_key_cannot_be_reused_for_another_round(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    path = repo.get_path("path-sample")
    assert path is not None
    lesson = next(
        repo.get_lesson(lesson_id)
        for unit in path.units
        for lesson_id in unit.lesson_ids
        if any(step.kind is StepKind.FREE for step in repo.get_lesson(lesson_id).steps)
    )
    free = next(step for step in lesson.steps if step.kind is StepKind.FREE)
    common = dict(
        owner_id="student",
        lesson_id=lesson.lesson_id,
        lesson_version=1,
        step_id=free.step_id,
        rules_version=free.rules_version,
        idempotency_key="same-free-key",
        blob_id="free-blob",
        sha256="c" * 64,
        size_bytes=100,
        audio_content_type="audio/wav",
        now=now,
    )
    repo.create_step_attempt(**common, round_index=0)
    with pytest.raises(LearningConflict, match="different request"):
        repo.create_step_attempt(**common, round_index=1)


def test_progress_preserves_prior_pass_and_any_positive_free_speech(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    path = repo.get_path("path-sample")
    assert path is not None
    lesson = next(
        repo.get_lesson(lesson_id)
        for unit in path.units
        for lesson_id in unit.lesson_ids
        if any(step.kind is StepKind.FREE for step in repo.get_lesson(lesson_id).steps)
        and any(step.kind is not StepKind.FREE for step in repo.get_lesson(lesson_id).steps)
    )
    ordinary = next(step for step in lesson.steps if step.kind is not StepKind.FREE)
    free = next(step for step in lesson.steps if step.kind is StepKind.FREE)

    def save(step, key, status, *, round_index=None, speaking_s=0.0):
        record = repo.create_step_attempt(
            "student",
            lesson_id=lesson.lesson_id,
            lesson_version=1,
            step_id=step.step_id,
            rules_version=step.rules_version,
            idempotency_key=key,
            blob_id=f"blob-{key}",
            audio_content_type="audio/wav",
            sha256=(key.encode().hex() * 32)[:64],
            size_bytes=100,
            round_index=round_index,
            now=now,
        )
        result = StepResult(
            step_id=step.step_id,
            kind=step.kind,
            status=status,
            round_index=round_index,
            round_count=len(step.payload.rounds) if step.kind is StepKind.FREE else None,
            elapsed_seconds=5 if step.kind is StepKind.FREE else None,
            speaking_s=speaking_s,
            word_count=1,
            feedback="Recorded.",
        )
        repo.complete_step_attempt(
            "student",
            record.attempt_id,
            result,
            expected_revision=record.revision,
            now=now,
        )

    save(ordinary, "pass-ordinary", StepResultStatus.PASS)
    save(ordinary, "retry-ordinary", StepResultStatus.FAIL)
    save(free, "spoken-fail", StepResultStatus.FAIL, round_index=0, speaking_s=0.4)
    completions = repo.list_lesson_progress_completions("student", lesson.lesson_id, 1)
    assert (
        next(item for item in completions if item.step_id == ordinary.step_id).status.value
        == "COMPLETE"
    )
    free_completion = next(item for item in completions if item.step_id == free.step_id)
    assert free_completion.status.value == "COMPLETE"
    assert free_completion.speaking_s == pytest.approx(0.4)


def test_review_completion_is_atomic_and_stale_second_attempt_conflicts(repository):
    _, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    first = _create_practice(repo, mission, "first", "d" * 64, now)
    first_schedule = first_review(due_from=now)
    repo.complete_practice_attempt(
        "student",
        first.attempt_id,
        _practice_result(mission, PracticePurpose.PRACTICE),
        expected_revision=first.revision,
        now=now,
        review_source_kind="practice",
        review_content_key=mission.mission_id,
        review_schedule=first_schedule,
    )
    due = repo.list_due_reviews("student", as_of=first_schedule.due_at, limit=1)[0]
    retries = [
        repo.create_practice_attempt(
            "student",
            mission,
            PracticePurpose.LEARNING,
            f"review-{index}",
            prompt_version=mission.prompt_version,
            blob_id=f"review-blob-{index}",
            audio_content_type="audio/wav",
            sha256=hex(index + 1)[2:] * 64,
            size_bytes=100,
            now=first_schedule.due_at,
            review_source_kind=due.source_kind,
            review_source_attempt_id=due.source_attempt_id,
            review_content_key=due.content_key,
            expected_review_revision=due.revision,
            review_box=due.box,
        )
        for index in range(2)
    ]
    next_schedule = review_again(box=due.box, passed=True, reviewed_at=first_schedule.due_at)
    repo.complete_practice_attempt(
        "student",
        retries[0].attempt_id,
        _practice_result(mission, PracticePurpose.LEARNING),
        expected_revision=retries[0].revision,
        now=first_schedule.due_at,
        review_schedule=next_schedule,
    )
    with pytest.raises(LearningConflict, match="revision is stale|currently due|concurrently"):
        repo.complete_practice_attempt(
            "student",
            retries[1].attempt_id,
            _practice_result(mission, PracticePurpose.LEARNING),
            expected_revision=retries[1].revision,
            now=first_schedule.due_at,
            review_schedule=next_schedule,
        )
    still_queued = repo.get_practice_attempt("student", retries[1].attempt_id)
    assert still_queued is not None and still_queued.state is LearningAttemptState.QUEUED


def test_review_completion_race_across_connections_has_one_due_occurrence_winner(repository):
    store, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    source = _create_practice(repo, mission, "race-source", "a" * 64, now)
    due_schedule = first_review(due_from=now)
    repo.complete_practice_attempt(
        "student",
        source.attempt_id,
        _practice_result(mission, PracticePurpose.PRACTICE),
        expected_revision=source.revision,
        now=now,
        review_source_kind="practice",
        review_content_key=mission.mission_id,
        review_schedule=due_schedule,
    )
    due = repo.list_due_reviews("student", as_of=due_schedule.due_at, limit=1)[0]
    retries = [
        repo.create_practice_attempt(
            "student",
            mission,
            PracticePurpose.LEARNING,
            f"race-review-{index}",
            prompt_version=mission.prompt_version,
            blob_id=f"race-review-blob-{index}",
            audio_content_type="audio/wav",
            sha256=str(index + 1) * 64,
            size_bytes=100,
            now=due_schedule.due_at,
            review_source_kind=due.source_kind,
            review_source_attempt_id=due.source_attempt_id,
            review_content_key=due.content_key,
            expected_review_revision=due.revision,
            review_box=due.box,
        )
        for index in range(2)
    ]
    schedule = review_again(box=due.box, passed=True, reviewed_at=due_schedule.due_at)
    barrier = Barrier(2)

    def complete_on_second_connection(record):
        second_store = SQLiteStore(store.data_dir)
        try:
            barrier.wait(timeout=5)
            second_repo = LearningRepository(second_store)
            try:
                second_repo.complete_practice_attempt(
                    "student",
                    record.attempt_id,
                    _practice_result(mission, PracticePurpose.LEARNING),
                    expected_revision=record.revision,
                    now=due_schedule.due_at,
                    review_schedule=schedule,
                )
                return "complete"
            except LearningConflict:
                return "conflict"
        finally:
            second_store.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(complete_on_second_connection, retries))
    assert sorted(outcomes) == ["complete", "conflict"]
    final = [repo.get_practice_attempt("student", item.attempt_id) for item in retries]
    assert sorted(item.state.value for item in final) == ["COMPLETED", "QUEUED"]


def test_published_lesson_edit_reads_draft_and_preserves_old_version(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    original = repo.get_lesson("lesson-a2-neighborhood", published_only=False)
    assert original is not None
    changed = original.model_copy(update={"title": "Teacher revision"})
    saved = repo.save_draft_lesson(
        "teacher", "unit-sample-a2", changed, expected_revision=1, now=now
    )
    preview = repo.get_lesson("lesson-a2-neighborhood", published_only=False)
    assert preview is not None and preview.title == "Teacher revision"
    assert saved.revision == 2
    published = repo.publish_lesson(
        "teacher", "lesson-a2-neighborhood", expected_revision=2, now=now
    )
    assert published.version == 2
    old = repo.get_lesson("lesson-a2-neighborhood", version=1)
    assert old is not None and old.title != "Teacher revision"


def test_new_path_publishes_only_after_every_lesson_has_a_frozen_version(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    source = repo.get_lesson("lesson-a2-neighborhood", version=1)
    source_path = repo.get_path("path-sample")
    assert source is not None
    assert source_path is not None
    path = repo.save_draft_path(
        "teacher",
        source_path.model_copy(
            update={
                "path_id": "teacher-path",
                "title": "Teacher path",
                "units": (),
                "content_version": "teacher-v1",
            }
        ),
        expected_revision=0,
        now=now,
    )
    assert path.path_id == "teacher-path"
    assert repo.path_revision("teacher-path") == 1
    assert repo.path_revision("unknown-path") is None
    unit = repo.save_draft_unit(
        "teacher",
        "teacher-path",
        source_path.units[0].model_copy(
            update={
                "unit_id": "teacher-unit",
                "path_id": "teacher-path",
                "ordinal": 1,
                "title": "Teacher unit",
                "lesson_ids": ("teacher-lesson",),
            }
        ),
        expected_revision=0,
        now=now,
    )
    assert repo.unit_revision("teacher-unit") == 1
    assert repo.unit_revision("unknown-unit") is None
    lesson = source.model_copy(
        update={"lesson_id": "teacher-lesson", "revision": 1, "content_version": "teacher-v1"}
    )
    repo.save_draft_lesson("teacher", unit.unit_id, lesson, expected_revision=0, now=now)
    with pytest.raises(ValueError, match="published snapshot"):
        repo.publish_path("teacher", "teacher-path", expected_revision=1, now=now)
    assert repo.get_path("teacher-path") is None
    repo.publish_lesson("teacher", "teacher-lesson", expected_revision=1, now=now)
    published_path = repo.publish_path("teacher", "teacher-path", expected_revision=1, now=now)
    assert published_path.path_id == "teacher-path"
    assert repo.path_revision("teacher-path") == 2
    visible = repo.get_path("teacher-path")
    assert visible is not None and visible.units[0].lesson_ids == ("teacher-lesson",)
    with pytest.raises(LearningConflict, match="published path"):
        repo.save_draft_path("teacher", published_path, expected_revision=2, now=now)


def test_draft_hierarchy_reorder_and_delete_use_persisted_cas_revisions(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    template = repo.get_path("path-sample")
    assert template is not None
    repo.save_draft_path(
        "teacher",
        template.model_copy(update={"path_id": "cas-path", "title": "CAS path", "units": ()}),
        expected_revision=0,
        now=now,
    )
    for unit_id, ordinal in (("cas-unit-1", 1), ("cas-unit-2", 2)):
        repo.save_draft_unit(
            "teacher",
            "cas-path",
            template.units[0].model_copy(
                update={
                    "unit_id": unit_id,
                    "path_id": "cas-path",
                    "ordinal": ordinal,
                    "lesson_ids": (),
                }
            ),
            expected_revision=0,
            now=now,
        )
    with pytest.raises(LearningConflict, match="revision is stale"):
        repo.reorder_units("teacher", "cas-path", ("cas-unit-2", "cas-unit-1"), 0, now)
    assert repo.reorder_units("teacher", "cas-path", ("cas-unit-2", "cas-unit-1"), 1, now) == 2
    projection = repo.get_path("cas-path", published_only=False)
    assert projection is not None and projection.revision == 2
    assert [unit.unit_id for unit in projection.units] == ["cas-unit-2", "cas-unit-1"]
    assert all(unit.revision == 2 for unit in projection.units)
    with pytest.raises(LearningConflict, match="revision is stale"):
        repo.delete_draft_unit("teacher", "cas-path", "cas-unit-1", expected_revision=1, now=now)
    assert repo.delete_draft_unit("teacher", "cas-path", "cas-unit-1", expected_revision=2, now=now)
    assert repo.delete_draft_unit("teacher", "cas-path", "cas-unit-2", expected_revision=2, now=now)
    assert repo.delete_draft_path("teacher", "cas-path", expected_revision=2, now=now)
    assert repo.get_path("cas-path", published_only=False) is None


def test_path_bundle_import_is_atomic_and_media_free(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    from aicefr.lessons.authoring import export_path, import_path

    bundle = repo.export_path_bundle("path-sample")
    assert bundle is not None
    payload = export_path(bundle)
    counter = 0

    def id_factory(kind: str) -> str:
        nonlocal counter
        counter += 1
        return f"copy-{kind}-{counter}"

    imported = import_path(payload, id_factory=id_factory)
    assert repo.import_draft_path_bundle("teacher", imported, now=now).path_id == "copy-path-1"
    count = repo._store.connection.execute("SELECT COUNT(*) FROM learning_paths").fetchone()[0]
    invalid = imported.model_copy(update={"lessons": imported.lessons[:-1]})
    with pytest.raises(ValueError, match="lesson"):
        repo.import_draft_path_bundle("teacher", invalid, now=now)
    assert (
        repo._store.connection.execute("SELECT COUNT(*) FROM learning_paths").fetchone()[0] == count
    )


def test_teacher_override_is_audited_without_changing_raw_result_or_progress(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    lesson = repo.get_lesson("lesson-a2-neighborhood", version=1)
    assert lesson is not None
    step = lesson.steps[0]
    attempt = repo.create_step_attempt(
        "student",
        lesson_id=lesson.lesson_id,
        lesson_version=1,
        step_id=step.step_id,
        rules_version=step.rules_version,
        idempotency_key="override-attempt",
        blob_id="override-blob",
        audio_content_type="audio/wav",
        sha256="e" * 64,
        size_bytes=100,
        round_index=None,
        now=now,
    )
    result = StepResult(
        step_id=step.step_id,
        kind=step.kind,
        status=StepResultStatus.PASS,
        word_count=2,
        feedback="Passed.",
    )
    completed = repo.complete_step_attempt(
        "student",
        attempt.attempt_id,
        result,
        expected_revision=attempt.revision,
        now=now,
    )
    updated = repo.append_step_override(
        "teacher",
        "student",
        attempt.attempt_id,
        new_value="FAIL",
        reason="manual review",
        expected_revision=completed.revision,
        now=now,
    )
    assert updated.result == result
    assert updated.teacher_override == "FAIL"
    events = repo.list_step_override_events("student", attempt.attempt_id)
    assert len(events) == 1 and events[0].old_value is None
    assert events[0].new_value == "FAIL" and events[0].actor_id == "teacher"
    progress = repo.list_lesson_progress_completions("student", lesson.lesson_id, 1)
    assert (
        next(item for item in progress if item.step_id == step.step_id).status.value == "COMPLETE"
    )


def test_step_review_source_uses_exact_step_attempt_and_schedule(repository):
    _, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    lesson = repo.get_lesson("lesson-a2-neighborhood", version=1)
    assert lesson is not None
    step = lesson.steps[0]
    attempt = repo.create_step_attempt(
        "student",
        lesson_id=lesson.lesson_id,
        lesson_version=1,
        step_id=step.step_id,
        rules_version=step.rules_version,
        idempotency_key="step-review-source",
        blob_id="step-review-source-audio",
        sha256="f" * 64,
        size_bytes=100,
        audio_content_type="audio/wav",
        round_index=None,
        now=now,
    )
    result = StepResult(
        step_id=step.step_id,
        kind=step.kind,
        status=StepResultStatus.PASS,
        word_count=2,
        feedback="Passed.",
    )
    schedule = first_review(due_from=now)
    repo.complete_step_attempt(
        "student",
        attempt.attempt_id,
        result,
        expected_revision=attempt.revision,
        now=now,
        review_source_kind="step",
        review_content_key=f"{lesson.lesson_id}:{step.step_id}",
        review_schedule=schedule,
    )
    due = repo.list_due_reviews("student", as_of=schedule.due_at, limit=5)
    assert len(due) == 1
    assert due[0].source_kind == "step" and due[0].source_attempt_id == attempt.attempt_id
    assert due[0].content_key == f"{lesson.lesson_id}:{step.step_id}"


def test_step_review_due_occurrence_has_single_cas_winner(repository):
    store, repo = repository
    now = datetime.now(UTC)
    seed_sample(repo, now=now)
    lesson = repo.get_lesson("lesson-a2-neighborhood", version=1)
    assert lesson is not None
    step = next(step for step in lesson.steps if step.kind is not StepKind.FREE)
    source = repo.create_step_attempt(
        "student",
        lesson_id=lesson.lesson_id,
        lesson_version=1,
        step_id=step.step_id,
        rules_version=step.rules_version,
        idempotency_key="step-review-cas-source",
        blob_id="step-review-cas-source-audio",
        sha256="a" * 64,
        size_bytes=100,
        audio_content_type="audio/wav",
        round_index=None,
        now=now,
    )
    source_result = StepResult(
        step_id=step.step_id,
        kind=step.kind,
        status=StepResultStatus.PASS,
        word_count=2,
        feedback="Passed.",
    )
    first_schedule = first_review(due_from=now)
    content_key = f"{lesson.lesson_id}:{step.step_id}"
    repo.complete_step_attempt(
        "student",
        source.attempt_id,
        source_result,
        expected_revision=source.revision,
        now=now,
        review_source_kind="step",
        review_content_key=content_key,
        review_schedule=first_schedule,
    )
    due = repo.list_due_reviews("student", as_of=first_schedule.due_at, limit=5)[0]
    retries = [
        repo.create_step_attempt(
            "student",
            lesson_id=lesson.lesson_id,
            lesson_version=1,
            step_id=step.step_id,
            rules_version=step.rules_version,
            idempotency_key=f"step-review-cas-{index}",
            blob_id=f"step-review-cas-audio-{index}",
            sha256=str(index) * 64,
            size_bytes=100,
            audio_content_type="audio/wav",
            round_index=None,
            now=first_schedule.due_at,
            review_source_kind="step",
            review_source_attempt_id=due.source_attempt_id,
            review_content_key=due.content_key,
            expected_review_revision=due.revision,
            review_box=due.box,
        )
        for index in (1, 2)
    ]
    next_schedule = review_again(box=due.box, passed=True, reviewed_at=first_schedule.due_at)
    review_result = source_result
    barrier = Barrier(2)

    def complete_on_second_connection(record):
        second_store = SQLiteStore(store.data_dir)
        try:
            barrier.wait(timeout=5)
            second_repo = LearningRepository(second_store)
            try:
                second_repo.complete_step_attempt(
                    "student",
                    record.attempt_id,
                    review_result,
                    expected_revision=record.revision,
                    now=first_schedule.due_at,
                    review_schedule=next_schedule,
                )
                return "complete"
            except LearningConflict:
                return "conflict"
        finally:
            second_store.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(complete_on_second_connection, retries))
    assert sorted(outcomes) == ["complete", "conflict"]
    final = [repo.get_step_attempt("student", item.attempt_id) for item in retries]
    assert sorted(item.state.value for item in final) == ["COMPLETED", "QUEUED"]


def test_attempt_deletion_removes_audio_reference_and_queues_cleanup(repository):
    store, repo = repository
    now = datetime.now(UTC)
    mission = PRACTICE_MISSIONS[0]
    record = _create_practice(repo, mission, "delete-attempt", "b" * 64, now)
    assert repo.delete_practice_attempt(
        "student", record.attempt_id, expected_revision=record.revision, now=now
    )
    assert repo.get_practice_attempt("student", record.attempt_id) is None
    assert (
        store.connection.execute(
            "SELECT 1 FROM learning_audio_artifacts WHERE practice_attempt_id=?",
            (record.attempt_id,),
        ).fetchone()
        is None
    )
    assert (
        store.connection.execute(
            "SELECT state FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
            (record.audio.blob_id,),
        ).fetchone()[0]
        == "pending"
    )
    seed_sample(repo, now=now)
    lesson = repo.get_lesson("lesson-a2-neighborhood", version=1)
    assert lesson is not None
    step = lesson.steps[0]
    step_attempt = repo.create_step_attempt(
        "student",
        lesson_id=lesson.lesson_id,
        lesson_version=1,
        step_id=step.step_id,
        rules_version=step.rules_version,
        idempotency_key="delete-step-attempt",
        blob_id="delete-step-audio",
        sha256="8" * 64,
        size_bytes=100,
        audio_content_type="audio/wav",
        round_index=None,
        now=now,
    )
    assert repo.delete_step_attempt(
        "student",
        step_attempt.attempt_id,
        expected_revision=step_attempt.revision,
        now=now,
    )
    assert repo.get_step_attempt("student", step_attempt.attempt_id) is None
    assert (
        store.connection.execute(
            "SELECT 1 FROM learning_audio_artifacts WHERE step_attempt_id=?",
            (step_attempt.attempt_id,),
        ).fetchone()
        is None
    )


def test_owner_export_and_erasure_remain_scoped_and_queue_audio_cleanup(repository):
    store, repo = repository
    now = datetime.now(UTC)
    store.connection.execute(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES('other','student','hash')"
    )
    mission = PRACTICE_MISSIONS[0]
    own = _create_practice(repo, mission, "privacy-own", "d" * 64, now)
    other = repo.create_practice_attempt(
        "other",
        mission,
        PracticePurpose.PRACTICE,
        "privacy-other",
        prompt_version=mission.prompt_version,
        blob_id="privacy-other-audio",
        audio_content_type="audio/wav",
        sha256="e" * 64,
        size_bytes=100,
        now=now,
    )
    payload = repo.export_owner_learning_data("student")
    assert [item["attempt_id"] for item in payload["practice_attempts"]] == [own.attempt_id]
    repo.delete_owner_learning_data("student", now=now)
    assert repo.export_owner_learning_data("student")["practice_attempts"] == []
    assert repo.get_practice_attempt("other", other.attempt_id) is not None
    assert (
        store.connection.execute(
            "SELECT COUNT(*) FROM learning_audio_artifacts WHERE owner_id='student'"
        ).fetchone()[0]
        == 0
    )
    assert (
        store.connection.execute(
            "SELECT COUNT(*) FROM cleanup_intents WHERE resource_kind='privacy_erasure' "
            "AND owner_id='student' AND state='running'"
        ).fetchone()[0]
        == 1
    )
