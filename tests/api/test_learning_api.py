from __future__ import annotations

import io
import json
import wave
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.contracts import ActorRole, Band
from aicefr.lessons.model import LearningPath, LearningUnit, Lesson, StepResult, StepResultStatus
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.practice.contracts import (
    MissionMeasurement,
    PracticePurpose,
    PracticeResult,
    PracticeStatus,
)


def _call(
    runtime, method, path, *, token, body=b"", content_type="", origin="http://127.0.0.1:8000"
):
    captured = {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "HTTP_HOST": "127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_ORIGIN": origin,
        "HTTP_COOKIE": f"aicefr_session={token}",
    }
    response = b"".join(
        runtime.app(
            environ, lambda status, headers: captured.update(status=status, headers=headers)
        )
    )
    captured["code"] = int(captured["status"].split()[0])
    captured["body"] = response
    captured["json"] = json.loads(response) if response else None
    return captured


def _json_call(runtime, method, path, *, token, values):
    return _call(
        runtime,
        method,
        path,
        token=token,
        body=json.dumps(values).encode(),
        content_type="application/json",
    )


def _attempt_multipart(mission, idempotency_key: str, content: bytes) -> tuple[bytes, str]:
    boundary = "learning-attempt-fixture"
    parts = []
    for name, value in (
        ("mission_id", mission.mission_id),
        ("prompt_version", mission.prompt_version),
        ("purpose", PracticePurpose.PRACTICE.value),
        ("idempotency_key", idempotency_key),
    ):
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    body = b"".join(parts)
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="attempt.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body += content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def _review_multipart(idempotency_key: str, content: bytes) -> tuple[bytes, str]:
    boundary = "learning-review-binding-fixture"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="idempotency_key"\r\n\r\n'
            f"{idempotency_key}\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; '
            'filename="review.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, f"multipart/form-data; boundary={boundary}"


def _review_audio() -> bytes:
    audio_file = io.BytesIO()
    with wave.open(audio_file, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * 32_000)
    return audio_file.getvalue()


def _create_due_review(instance, owner_id: str, kind: str, key: str, now: datetime):
    from aicefr.lessons.review import first_review

    repository = instance.learning_repository
    schedule = first_review(due_from=now - timedelta(days=2))
    if kind == "practice":
        mission = instance.practice.catalogue()[0]
        blob = instance.practice._blobs.store(b"source practice audio")
        source = repository.create_practice_attempt(
            owner_id,
            mission,
            PracticePurpose.PRACTICE,
            key,
            prompt_version=mission.prompt_version,
            blob_id=blob.blob_id,
            audio_content_type="audio/wav",
            sha256=blob.sha256,
            size_bytes=blob.size_bytes,
            now=now,
        )
        result = PracticeResult(
            mission_id=mission.mission_id,
            purpose=PracticePurpose.PRACTICE,
            status=PracticeStatus.PASS,
            measurements=tuple(
                MissionMeasurement(
                    goal_id=goal.goal_id,
                    measured_value=goal.target,
                    target=goal.target,
                    status=PracticeStatus.PASS,
                )
                for goal in mission.goals
            ),
            rules_version=mission.rules_version,
            word_count=1,
            audio_duration_s=1.0,
            speaking_s=0.0,
        )
        repository.complete_practice_attempt(
            owner_id,
            source.attempt_id,
            result,
            expected_revision=source.revision,
            now=now,
            review_source_kind="practice",
            review_content_key=f"{mission.mission_id}:{key}",
            review_schedule=schedule,
        )
    else:
        lesson = repository.get_lesson("lesson-a2-neighborhood", version=1)
        assert lesson is not None
        step = next(step for step in lesson.steps if step.kind.value != "free")
        blob = instance.practice._blobs.store(b"source step audio")
        source = repository.create_step_attempt(
            owner_id,
            lesson_id=lesson.lesson_id,
            lesson_version=lesson.version,
            step_id=step.step_id,
            rules_version=step.rules_version,
            idempotency_key=key,
            blob_id=blob.blob_id,
            sha256=blob.sha256,
            size_bytes=blob.size_bytes,
            audio_content_type="audio/wav",
            round_index=None,
            now=now,
        )
        result = StepResult(
            step_id=step.step_id,
            kind=step.kind,
            status=StepResultStatus.PASS,
            word_count=1,
            feedback="Passed.",
        )
        repository.complete_step_attempt(
            owner_id,
            source.attempt_id,
            result,
            expected_revision=source.revision,
            now=now,
            review_source_kind="step",
            review_content_key=f"{lesson.lesson_id}:{step.step_id}:{key}",
            review_schedule=schedule,
        )
    return next(
        item
        for item in repository.list_due_reviews(owner_id, as_of=now, limit=100)
        if item.source_attempt_id == source.attempt_id
    )


@pytest.fixture
def runtime(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-scorer.json")
    instance = create_runtime(tmp_path / "runtime", config=config)
    actors = {}
    for role, name in (
        (ActorRole.STUDENT, "student"),
        (ActorRole.TEACHER, "teacher"),
        (ActorRole.ADMIN, "admin"),
    ):
        actor = instance.auth.bootstrap_fixture_account(
            f"fixture-learning-{name}", role, "test-password"
        )
        actors[name] = actor
        if role is ActorRole.STUDENT:
            instance.consents.activate(
                actor,
                str(config.get("consent_version", "consent-v2")),
                audio_storage_allowed=True,
            )
    tokens = {
        name: instance.auth.login(actor.actor_id, "test-password") for name, actor in actors.items()
    }
    try:
        yield instance, actors, tokens
    finally:
        instance.close()


def test_student_catalogue_and_resource_boundaries(runtime):
    instance, actors, tokens = runtime
    catalogue = _call(instance, "GET", "/api/v1/learn/path", token=tokens["student"])
    assert catalogue["code"] == 200
    assert len(catalogue["json"]["paths"][0]["units"]) == 18

    absent_mission = _call(
        instance,
        "GET",
        "/api/v1/practice/missions/not-a-mission",
        token=tokens["student"],
    )
    mission = instance.practice.catalogue()[0]
    audio = instance.practice._blobs.store(b"fixture audio bytes")
    foreign_record = instance.learning_repository.create_practice_attempt(
        actors["admin"].actor_id,
        mission,
        PracticePurpose.PRACTICE,
        "foreign-owner-fixture",
        prompt_version=mission.prompt_version,
        blob_id=audio.blob_id,
        audio_content_type="audio/wav",
        sha256=audio.sha256,
        size_bytes=audio.size_bytes,
        now=datetime.now(UTC),
    )
    foreign_attempt = _call(
        instance,
        "GET",
        f"/api/v1/practice/attempts/{foreign_record.attempt_id}",
        token=tokens["student"],
    )
    assert absent_mission["code"] == foreign_attempt["code"] == 404
    assert (
        absent_mission["json"]["error"]
        == foreign_attempt["json"]["error"]
        == "RESOURCE_UNAVAILABLE"
    )

    boundary = "learning-api-fixture"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="mission_id"\r\n\r\n'
            "missing-mission\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="prompt_version"\r\n\r\n'
            "fixture-v1\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\n'
            "PRACTICE\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="idempotency_key"\r\n\r\n'
            "unknown-mission-submit\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="x.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        + b"fixture"
        + f"\r\n--{boundary}--\r\n".encode()
    )
    absent_submit = _call(
        instance,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    assert absent_submit["code"] == 404
    assert absent_submit["json"]["error"] == "RESOURCE_UNAVAILABLE"


def test_practice_submit_replay_and_conflict_stay_out_of_assessment_pipeline(runtime):
    instance, actors, tokens = runtime
    mission = instance.practice.catalogue()[0]
    audio_file = io.BytesIO()
    with wave.open(audio_file, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * 32_000)
    audio = audio_file.getvalue()
    body, content_type = _attempt_multipart(mission, "practice-api-idempotent", audio)

    submitted = _call(
        instance,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert submitted["code"] == 201, submitted["json"]
    assert submitted["json"]["state"] == "NOT_EVALUATED"
    assert "score" not in submitted["json"] and "band" not in submitted["json"]

    replay = _call(
        instance,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert replay["code"] == 201, replay["json"]
    assert replay["json"]["attempt_id"] == submitted["json"]["attempt_id"]
    assert len(instance.practice.attempts(actors["student"].actor_id)) == 1

    changed_body, changed_type = _attempt_multipart(
        mission, "practice-api-idempotent", audio[:-2] + b"\x01\x00"
    )
    conflict = _call(
        instance,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=changed_body,
        content_type=changed_type,
    )
    assert conflict["code"] == 409
    assert len(instance.practice.attempts(actors["student"].actor_id)) == 1
    assert (
        instance.store.connection.execute(
            "SELECT COUNT(*) FROM learning_audio_artifacts WHERE owner_id=?",
            (actors["student"].actor_id,),
        ).fetchone()[0]
        == 1
    )
    assert instance.store.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
    assert instance.control.pipeline._scorer.artifact is None


def test_due_review_api_uses_saved_result_and_returns_not_evaluated_without_asr(runtime):
    instance, actors, tokens = runtime
    now = datetime.now(UTC)
    mission = instance.practice.catalogue()[0]
    audio = instance.practice._blobs.store(b"source audio")
    source = instance.learning_repository.create_practice_attempt(
        actors["student"].actor_id,
        mission,
        PracticePurpose.PRACTICE,
        "review-api-source",
        prompt_version=mission.prompt_version,
        blob_id=audio.blob_id,
        audio_content_type="audio/wav",
        sha256=audio.sha256,
        size_bytes=audio.size_bytes,
        now=now,
    )
    result = PracticeResult(
        mission_id=mission.mission_id,
        purpose=PracticePurpose.PRACTICE,
        status=PracticeStatus.PASS,
        measurements=tuple(
            MissionMeasurement(
                goal_id=goal.goal_id,
                measured_value=goal.target,
                target=goal.target,
                status=PracticeStatus.PASS,
            )
            for goal in mission.goals
        ),
        rules_version=mission.rules_version,
        word_count=1,
        audio_duration_s=1.0,
        speaking_s=0.0,
    )
    from aicefr.lessons.review import first_review

    due_schedule = first_review(due_from=now - timedelta(days=2))
    instance.learning_repository.complete_practice_attempt(
        actors["student"].actor_id,
        source.attempt_id,
        result,
        expected_revision=source.revision,
        review_source_kind="practice",
        review_content_key=mission.mission_id,
        review_schedule=due_schedule,
        now=now,
    )
    due = instance.learning_repository.list_due_reviews(
        actors["student"].actor_id,
        as_of=due_schedule.due_at,
        limit=10,
    )
    assert len(due) == 1

    visible = _call(instance, "GET", "/api/v1/learn/reviews/due", token=tokens["student"])
    assert visible["code"] == 200
    assert visible["json"]["reviews"][0]["review_id"] == due[0].review_id

    audio_file = io.BytesIO()
    with wave.open(audio_file, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * 32_000)
    boundary = "learning-review-fixture"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="idempotency_key"\r\n\r\n'
            "review-api-submit\r\n"
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; '
            'filename="review.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode()
        + audio_file.getvalue()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    content_type = f"multipart/form-data; boundary={boundary}"
    reviewed = _call(
        instance,
        "POST",
        f"/api/v1/learn/reviews/{due[0].review_id}/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert reviewed["code"] == 201, reviewed["json"]
    assert reviewed["json"]["purpose"] == PracticePurpose.LEARNING.value
    assert reviewed["json"]["state"] == "NOT_EVALUATED"
    assert instance.store.connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 0
    assert instance.control.pipeline._scorer.artifact is None


@pytest.mark.parametrize("kind", ["practice", "step"])
def test_review_replay_is_bound_to_url_review_even_after_advance(runtime, kind):
    instance, actors, tokens = runtime
    owner_id = actors["student"].actor_id
    now = datetime.now(UTC)
    first = _create_due_review(instance, owner_id, kind, f"{kind}-review-source-a", now)
    other = _create_due_review(instance, owner_id, kind, f"{kind}-review-source-b", now)
    body, content_type = _review_multipart(f"{kind}-review-key", _review_audio())

    url = f"/api/v1/learn/reviews/{first.review_id}/attempts"
    submitted = _call(
        instance, "POST", url, token=tokens["student"], body=body, content_type=content_type
    )
    assert submitted["code"] == 201, submitted["json"]
    assert submitted["json"]["state"] == "NOT_EVALUATED"

    # Advance the source review out of the due queue. A correct idempotent replay
    # still resolves its stable review ID and returns the original attempt.
    from aicefr.lessons.review import ReviewSchedule

    advanced = ReviewSchedule.create(2, now + timedelta(days=3))
    if kind == "practice":
        instance.learning_repository.upsert_review_item(
            owner_id, first.source_attempt_id, first.content_key, advanced, now=now
        )
    else:
        instance.learning_repository.upsert_step_review_item(
            owner_id, first.source_attempt_id, first.content_key, advanced, now=now
        )
    replay = _call(
        instance, "POST", url, token=tokens["student"], body=body, content_type=content_type
    )
    assert replay["code"] == 201, replay["json"]
    assert replay["json"]["attempt_id"] == submitted["json"]["attempt_id"]

    conflict = _call(
        instance,
        "POST",
        f"/api/v1/learn/reviews/{other.review_id}/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert conflict["code"] == 409, conflict["json"]
    missing = _call(
        instance,
        "POST",
        "/api/v1/learn/reviews/unknown-review-item/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert missing["code"] == 404, missing["json"]
    table = "practice_attempts" if kind == "practice" else "step_attempts"
    assert (
        instance.store.connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE owner_id=? AND idempotency_key=?",
            (owner_id, f"{kind}-review-key"),
        ).fetchone()[0]
        == 1
    )


def test_staff_student_role_separation_and_csrf(runtime):
    instance, _, tokens = runtime
    student_on_teacher_route = _call(
        instance,
        "GET",
        "/api/v1/teacher/learn/paths/absent",
        token=tokens["student"],
    )
    teacher_on_student_route = _call(
        instance,
        "GET",
        "/api/v1/practice/missions",
        token=tokens["teacher"],
    )
    forged_origin = _call(
        instance,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        origin="https://attacker.example",
    )
    assert student_on_teacher_route["code"] == 403
    assert teacher_on_student_route["code"] == 403
    assert forged_origin["code"] == 403


def test_withdrawn_consent_blocks_learning_catalogue(runtime):
    instance, actors, tokens = runtime
    instance.consents.withdraw(actors["student"])
    blocked = _call(instance, "GET", "/api/v1/practice", token=tokens["student"])
    assert blocked["code"] == 401


def test_teacher_can_author_publish_and_student_reads_published_hierarchy(runtime):
    instance, _, tokens = runtime
    source_path = instance.learning_repository.list_paths(published_only=True)[0]
    source_lesson_id = next(
        lesson_id for unit in source_path.units for lesson_id in unit.lesson_ids
    )
    source_lesson = instance.lessons.lesson(source_lesson_id)
    assert source_lesson is not None

    path_id = "api-authoring-path"
    unit_id = "api-authoring-unit"
    lesson_id = "api-authoring-lesson"
    path = LearningPath(
        path_id=path_id,
        title="API authoring journey",
        band_from=Band.A2,
        band_to=Band.B1,
        content_version="api-authoring-v1",
        units=(
            LearningUnit(
                unit_id=unit_id,
                path_id=path_id,
                ordinal=1,
                title="First unit",
                band=Band.A2,
                lesson_ids=(lesson_id,),
            ),
        ),
    )
    created_path = _json_call(
        instance,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={"expected_revision": 0, "path": path.model_dump(mode="json")},
    )
    assert created_path["code"] == 201
    created_unit = _json_call(
        instance,
        "POST",
        f"/api/v1/teacher/learn/paths/{path_id}/units",
        token=tokens["teacher"],
        values={
            "expected_revision": 0,
            "unit": path.units[0].model_dump(mode="json"),
        },
    )
    assert created_unit["code"] == 201
    assert created_unit["json"]["revision"] == 1

    draft_lesson = Lesson(
        lesson_id=lesson_id,
        title=source_lesson.title,
        summary=source_lesson.summary,
        band=source_lesson.band,
        steps=source_lesson.steps,
        revision=1,
        content_version="api-authoring-v1",
    )
    saved_lesson = _json_call(
        instance,
        "POST",
        "/api/v1/teacher/learn/lessons",
        token=tokens["teacher"],
        values={
            "unit_id": unit_id,
            "expected_revision": 0,
            "lesson": draft_lesson.model_dump(mode="json"),
        },
    )
    assert saved_lesson["code"] == 201, saved_lesson["json"]
    published_lesson = _json_call(
        instance,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": saved_lesson["json"]["revision"]},
    )
    assert published_lesson["code"] == 201

    author_path = _call(
        instance, "GET", f"/api/v1/teacher/learn/paths/{path_id}", token=tokens["teacher"]
    )
    assert author_path["code"] == 200
    assert author_path["json"]["revision"] == created_path["json"]["revision"]
    assert author_path["json"]["units"][0]["revision"] == created_unit["json"]["revision"]
    stale_revision = author_path["json"]["revision"]
    revised_path = path.model_copy(update={"title": "API authoring journey updated"})
    saved_path = _json_call(
        instance,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={"expected_revision": stale_revision, "path": revised_path.model_dump(mode="json")},
    )
    assert saved_path["code"] == 201
    stale_update = _json_call(
        instance,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={
            "expected_revision": stale_revision,
            "path": path.model_dump(mode="json"),
        },
    )
    assert stale_update["code"] == 409
    author_path = _call(
        instance, "GET", f"/api/v1/teacher/learn/paths/{path_id}", token=tokens["teacher"]
    )
    assert author_path["json"]["title"] == "API authoring journey updated"
    assert author_path["json"]["revision"] == saved_path["json"]["revision"]
    published_path = _json_call(
        instance,
        "POST",
        f"/api/v1/teacher/learn/paths/{path_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": author_path["json"]["revision"]},
    )
    assert published_path["code"] == 201

    catalogue = _call(instance, "GET", "/api/v1/learn/path", token=tokens["student"])
    published = next(row for row in catalogue["json"]["paths"] if row["path_id"] == path_id)
    assert published["units"][0]["lesson_ids"] == [lesson_id]
    student_lesson = _call(
        instance,
        "GET",
        f"/api/v1/learn/lessons/{lesson_id}/versions/{published_lesson['json']['version']}",
        token=tokens["student"],
    )
    assert student_lesson["code"] == 200
    assert student_lesson["json"]["lesson_id"] == lesson_id
