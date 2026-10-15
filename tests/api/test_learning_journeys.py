from __future__ import annotations

import hashlib
import io
import json
import struct
import wave
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.asr.service import EngineResult, RawWord
from aicefr.contracts import ActorRole, Band
from aicefr.lessons.model import LearningPath, LearningUnit, Lesson
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime


class FixtureAsr:
    """Injected deterministic ASR for HTTP journeys; no external weights are loaded."""

    def __init__(self):
        self.text = "Hello world"

    def detect_language(self, _audio):
        return "en", 0.99

    def transcribe(self, audio):
        terms = self.text.split()
        duration = max(audio.duration_s, 0.1)
        step = (duration - 0.2) / max(len(terms), 1)
        words = tuple(
            RawWord(
                text=term,
                start_s=0.1 + index * step,
                end_s=min(duration, 0.2 + index * step),
                prob=0.99,
            )
            for index, term in enumerate(terms)
        )
        return EngineResult(
            text=self.text,
            words=words,
            engine="fixture-asr",
            engine_version="fixture-v1",
            weight_name="fixture",
            test_only=True,
        )


class FixtureVad:
    """Injected fixture VAD returns one bounded speech island for valid WAV input."""

    def segments(self, _samples, sample_rate_hz):
        duration = len(_samples) / sample_rate_hz
        return ((0.1, min(1.9, duration - 0.05)),)


@pytest.fixture
def journey_runtime(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-scorer.json")
    asr = FixtureAsr()
    runtime = create_runtime(
        tmp_path / "learning-journey-runtime",
        config=config,
        asr_engine=asr,
        vad_engine=FixtureVad(),
    )
    actors = {}
    for role, name in (
        (ActorRole.STUDENT, "student"),
        (ActorRole.TEACHER, "teacher"),
        (ActorRole.ADMIN, "admin"),
    ):
        actor = runtime.auth.bootstrap_fixture_account(
            f"fixture-journey-{name}", role, "journey-password"
        )
        actors[name] = actor
        if role is ActorRole.STUDENT:
            runtime.consents.activate(actor, str(config.get("consent_version", "local-v1")))
    tokens = {
        name: runtime.auth.login(actor.actor_id, "journey-password")
        for name, actor in actors.items()
    }
    try:
        yield runtime, actors, tokens, asr
    finally:
        runtime.close()


def request(
    runtime,
    method,
    path,
    *,
    token,
    body=b"",
    content_type="application/json",
    query="",
):
    captured = {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_HOST": "127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_ORIGIN": "http://127.0.0.1:8000",
        "HTTP_COOKIE": f"aicefr_session={token}",
    }

    def start_response(status, headers):
        captured.update(status=status, headers=headers)

    captured["body"] = b"".join(runtime.app(environ, start_response))
    captured["code"] = int(captured["status"].split()[0])
    response_type = next(
        (value for name, value in captured["headers"] if name.lower() == "content-type"), ""
    )
    captured["json"] = (
        json.loads(captured["body"]) if captured["body"] and "json" in response_type else None
    )
    return captured


def json_request(runtime, method, path, *, token, values, query=""):
    return request(
        runtime,
        method,
        path,
        token=token,
        body=json.dumps(values, ensure_ascii=False, allow_nan=False).encode(),
        query=query,
    )


def multipart(parts, boundary="journey"):
    body = bytearray()
    for name, value, filename, mime in parts:
        body.extend(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disposition += f'; filename="{filename}"'
        body.extend(f"{disposition}\r\n".encode())
        if mime is not None:
            body.extend(f"Content-Type: {mime}\r\n".encode())
        body.extend(b"\r\n")
        body.extend(value)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def wav_fixture(duration_s=2.0):
    rate = 16_000
    frame_count = int(rate * duration_s)
    frames = b"".join(
        struct.pack("<h", 5_000 if index % 2 else -5_000) for index in range(frame_count)
    )
    output = io.BytesIO()
    with wave.open(output, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return output.getvalue()


def snapshot(runtime):
    tables = (
        "learning_paths",
        "learning_units",
        "learning_lessons",
        "lesson_versions",
        "lesson_steps",
        "learning_audio_artifacts",
        "step_attempts",
        "teacher_override_events",
        "audit",
    )
    counts = {
        table: runtime.store.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
    blobs = tuple(sorted(path.name for path in runtime.practice._blobs.root.iterdir()))
    return counts, blobs


def seed_lesson(runtime, *, path_id, unit_id, lesson_id, title):
    path = runtime.learning_repository.list_paths(published_only=True)[0]
    source_unit = path.units[0]
    source_lesson = runtime.lessons.lesson(source_unit.lesson_ids[0])
    assert source_lesson is not None
    steps = tuple(
        step.model_copy(update={"step_id": f"{lesson_id}-step-{index}", "ordinal": index})
        for index, step in enumerate(source_lesson.steps, start=1)
    )
    lesson = Lesson(
        lesson_id=lesson_id,
        title=title,
        summary=source_lesson.summary,
        band=source_lesson.band,
        steps=steps,
        content_version=f"{lesson_id}-content-v1",
    )
    draft_path = LearningPath(
        path_id=path_id,
        title=f"{title} path",
        description="Authoring API test path",
        band_from=Band.A2,
        band_to=Band.B1,
        units=(
            LearningUnit(
                unit_id=unit_id,
                path_id=path_id,
                ordinal=1,
                title="Unit one",
                band=Band.A2,
                lesson_ids=(lesson_id,),
            ),
        ),
        content_version=f"{path_id}-v1",
    )
    return draft_path, draft_path.units[0], lesson


def save_hierarchy(runtime, token, path, unit, lesson):
    created_path = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=token,
        values={"expected_revision": 0, "path": path.model_dump(mode="json")},
    )
    assert created_path["code"] == 201, created_path["json"]
    created_unit = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{path.path_id}/units",
        token=token,
        values={"expected_revision": 0, "unit": unit.model_dump(mode="json")},
    )
    assert created_unit["code"] == 201, created_unit["json"]
    saved_lesson = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/lessons",
        token=token,
        values={
            "unit_id": unit.unit_id,
            "expected_revision": 0,
            "lesson": lesson.model_dump(mode="json"),
        },
    )
    assert saved_lesson["code"] == 201, saved_lesson["json"]
    return created_path["json"], created_unit["json"], saved_lesson["json"]


def upload_sample(runtime, token, lesson_id, version, step_id, data):
    body, content_type = multipart(
        [
            ("media_kind", b"sample_audio", None, None),
            ("audio", data, "sample.wav", "audio/wav"),
        ]
    )
    return request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson_id}/versions/{version}/steps/{step_id}/media",
        token=token,
        body=body,
        content_type=content_type,
    )


def reseal_path(bundle):
    canonical = json.dumps(
        bundle, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()
    envelope = {
        "format": "aicefr-learning-path",
        "schema_version": 1,
        "path_sha256": hashlib.sha256(canonical).hexdigest(),
        "bundle": bundle,
    }
    return json.dumps(envelope, ensure_ascii=False).encode()


def test_teacher_publish_media_republish_preserves_old_student_version(journey_runtime):
    runtime, _actors, tokens, _asr = journey_runtime
    path, unit, lesson = seed_lesson(
        runtime,
        path_id="journey-published-path",
        unit_id="journey-published-unit",
        lesson_id="journey-published-lesson",
        title="Published before edit",
    )
    path_record, unit_record, saved = save_hierarchy(runtime, tokens["teacher"], path, unit, lesson)
    linted = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/lint",
        token=tokens["teacher"],
        values={"lesson": saved, "for_publish": True},
    )
    assert linted["code"] == 200, linted["json"]
    assert linted["json"]["valid"] is True

    first_step = lesson.steps[0]
    original_media = wav_fixture()
    uploaded = upload_sample(
        runtime,
        tokens["teacher"],
        lesson.lesson_id,
        saved["revision"],
        first_step.step_id,
        original_media,
    )
    assert uploaded["code"] == 201, uploaded["json"]
    draft_media = request(
        runtime,
        "GET",
        uploaded["json"]["url"],
        token=tokens["teacher"],
    )
    assert draft_media["code"] == 200
    assert draft_media["body"] == original_media

    first_publish = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": saved["revision"]},
    )
    assert first_publish["code"] == 201, first_publish["json"]
    first_version = first_publish["json"]["version"]
    first_path_publish = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{path.path_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": path_record["revision"]},
    )
    assert first_path_publish["code"] == 201, first_path_publish["json"]
    path_revision = runtime.store.connection.execute(
        "SELECT revision FROM learning_paths WHERE path_id=?", (path.path_id,)
    ).fetchone()[0]
    assert path_revision == first_path_publish["json"]["revision"]
    student_catalogue = request(
        runtime,
        "GET",
        "/api/v1/learn/path",
        token=tokens["student"],
    )
    published_path = next(
        item for item in student_catalogue["json"]["paths"] if item["path_id"] == path.path_id
    )
    assert published_path["units"][0]["lesson_ids"] == [lesson.lesson_id]

    student_v1 = request(
        runtime,
        "GET",
        f"/api/v1/learn/lessons/{lesson.lesson_id}/versions/{first_version}",
        token=tokens["student"],
    )
    assert student_v1["code"] == 200, student_v1["json"]
    assert student_v1["json"]["title"] == "Published before edit"
    assert student_v1["json"]["sample_media"][0]["sha256"] == uploaded["json"]["sha256"]
    student_v1_media = request(
        runtime,
        "GET",
        student_v1["json"]["sample_media"][0]["url"],
        token=tokens["student"],
    )
    assert student_v1_media["body"] == original_media

    changed = Lesson.model_validate(saved).model_dump(mode="json")
    changed["title"] = "Published after edit"
    changed["steps"][0]["instruction"] = "Read the updated example aloud."
    edited = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/lessons",
        token=tokens["teacher"],
        values={"unit_id": unit.unit_id, "expected_revision": saved["revision"], "lesson": changed},
    )
    assert edited["code"] == 201, edited["json"]
    replacement_media = wav_fixture(2.25)
    uploaded_v2 = upload_sample(
        runtime,
        tokens["teacher"],
        lesson.lesson_id,
        edited["json"]["revision"],
        first_step.step_id,
        replacement_media,
    )
    assert uploaded_v2["code"] == 201, uploaded_v2["json"]
    second_publish = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": edited["json"]["revision"]},
    )
    assert second_publish["code"] == 201, second_publish["json"]
    student_v1_again = request(
        runtime,
        "GET",
        f"/api/v1/learn/lessons/{lesson.lesson_id}/versions/{first_version}",
        token=tokens["student"],
    )
    student_v2 = request(
        runtime,
        "GET",
        f"/api/v1/learn/lessons/{lesson.lesson_id}/versions/2",
        token=tokens["student"],
    )
    assert student_v1_again["json"]["title"] == "Published before edit"
    assert student_v1_again["json"]["sample_media"][0]["sha256"] == uploaded["json"]["sha256"]
    assert student_v2["json"]["title"] == "Published after edit"
    assert student_v2["json"]["sample_media"][0]["sha256"] == uploaded_v2["json"]["sha256"]
    old_media_after_republish = request(
        runtime,
        "GET",
        student_v1_again["json"]["sample_media"][0]["url"],
        token=tokens["student"],
    )
    new_media = request(
        runtime,
        "GET",
        student_v2["json"]["sample_media"][0]["url"],
        token=tokens["student"],
    )
    assert old_media_after_republish["body"] == original_media
    assert new_media["body"] == replacement_media


def test_student_media_requires_published_parent_path(journey_runtime):
    runtime, _actors, tokens, _asr = journey_runtime
    path, unit, lesson = seed_lesson(
        runtime,
        path_id="journey-private-media-path",
        unit_id="journey-private-media-unit",
        lesson_id="journey-private-media-lesson",
        title="Lesson under draft path",
    )
    path_record, _unit_record, saved = save_hierarchy(
        runtime, tokens["teacher"], path, unit, lesson
    )
    step = lesson.steps[0]
    audio = wav_fixture()
    uploaded = upload_sample(
        runtime, tokens["teacher"], lesson.lesson_id, saved["revision"], step.step_id, audio
    )
    assert uploaded["code"] == 201, uploaded["json"]
    lesson_published = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": saved["revision"]},
    )
    assert lesson_published["code"] == 201, lesson_published["json"]

    student_media_url = uploaded["json"]["url"].replace("/api/v1/teacher/learn/", "/api/v1/learn/")
    hidden = request(runtime, "GET", student_media_url, token=tokens["student"])
    assert hidden["code"] == 404

    path_published = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{path.path_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": path_record["revision"]},
    )
    assert path_published["code"] == 201, path_published["json"]
    visible = request(runtime, "GET", student_media_url, token=tokens["student"])
    assert visible["code"] == 200
    assert visible["body"] == audio


def test_teacher_step_crud_reorder_stale_cas_delete_and_export_import(journey_runtime):
    runtime, _actors, tokens, _asr = journey_runtime
    path, unit, lesson = seed_lesson(
        runtime,
        path_id="journey-crud-path",
        unit_id="journey-crud-unit",
        lesson_id="journey-crud-lesson",
        title="CRUD lesson",
    )
    path_record, unit_record, saved = save_hierarchy(runtime, tokens["teacher"], path, unit, lesson)
    original_ids = [step["step_id"] for step in saved["steps"]]
    reordered = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/steps/reorder",
        token=tokens["teacher"],
        values={"expected_revision": saved["revision"], "step_ids": list(reversed(original_ids))},
    )
    assert reordered["code"] == 200, reordered["json"]
    current_revision = reordered["json"]["revision"]
    stale = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/steps/reorder",
        token=tokens["teacher"],
        values={"expected_revision": saved["revision"], "step_ids": original_ids},
    )
    assert stale["code"] == 409

    removed_step_id = original_ids[0]
    deleted_step = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/steps/{removed_step_id}",
        token=tokens["teacher"],
        query=f"expected_revision={current_revision}",
    )
    assert deleted_step["code"] == 200, deleted_step["json"]
    assert removed_step_id not in {row["step_id"] for row in deleted_step["json"]["steps"]}

    exported = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/export",
        token=tokens["teacher"],
    )
    assert exported["code"] == 200
    before_import = snapshot(runtime)
    imported_lesson = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/lessons/import",
        token=tokens["teacher"],
        values={
            "unit_id": unit.unit_id,
            "expected_revision": 0,
            "lesson_json": json.dumps(exported["json"]),
        },
    )
    assert imported_lesson["code"] == 201, imported_lesson["json"]
    assert imported_lesson["json"]["lesson_id"] != lesson.lesson_id
    assert [step["instruction"] for step in imported_lesson["json"]["steps"]] == [
        step["instruction"] for step in deleted_step["json"]["steps"]
    ]

    bundle = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/paths/{path.path_id}/export",
        token=tokens["teacher"],
    )
    assert bundle["code"] == 200
    before_bad_import = snapshot(runtime)
    invalid_bundle = json.loads(json.dumps(bundle["json"]["bundle"]))
    invalid_bundle["units"][0]["lessons"][0]["steps"][0]["kind"] = "unknown-kind"
    rejected = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["teacher"],
        values={"path_json": reseal_path(invalid_bundle).decode()},
    )
    assert rejected["code"] == 422
    assert before_bad_import == snapshot(runtime)
    assert before_import != snapshot(runtime)

    imported_path = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["teacher"],
        values={"path_json": json.dumps(bundle["json"])},
    )
    assert imported_path["code"] == 201, imported_path["json"]
    assert imported_path["json"]["path_id"] != path.path_id
    assert imported_path["json"]["units"][0]["ordinal"] == 1
    imported_path_id = imported_path["json"]["path_id"]
    reloaded = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/paths/{imported_path_id}",
        token=tokens["teacher"],
    )
    assert reloaded["code"] == 200
    assert reloaded["json"]["title"] == path.title
    assert reloaded["json"]["units"][0]["title"] == unit.title
    imported_lesson_id = reloaded["json"]["units"][0]["lesson_ids"][0]
    assert imported_lesson_id != lesson.lesson_id
    imported_path_lesson = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/lessons/{imported_lesson_id}",
        token=tokens["teacher"],
    )
    assert imported_path_lesson["code"] == 200
    source_path_lesson = bundle["json"]["bundle"]["units"][0]["lessons"][0]
    assert [step["instruction"] for step in imported_path_lesson["json"]["steps"]] == [
        step["instruction"] for step in source_path_lesson["steps"]
    ]

    deleted_imported_lesson = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/lessons/{imported_lesson['json']['lesson_id']}",
        token=tokens["teacher"],
        query=f"expected_revision={imported_lesson['json']['revision']}",
    )
    assert deleted_imported_lesson["code"] == 200
    deleted_source_lesson = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}",
        token=tokens["teacher"],
        query=f"expected_revision={deleted_step['json']['revision']}",
    )
    assert deleted_source_lesson["code"] == 200
    deleted_unit = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/paths/{path.path_id}/units/{unit.unit_id}",
        token=tokens["teacher"],
        query=f"expected_revision={unit_record['revision']}",
    )
    assert deleted_unit["code"] == 200
    remaining_path = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/paths/{path.path_id}",
        token=tokens["teacher"],
    )
    deleted_path = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/paths/{path.path_id}",
        token=tokens["teacher"],
        query=f"expected_revision={remaining_path['json']['revision']}",
    )
    assert deleted_path["code"] == 200

    second_path = LearningPath(
        path_id="journey-delete-path",
        title="Delete path",
        band_from=Band.A2,
        band_to=Band.B1,
        content_version="delete-v1",
        units=(),
    )
    created_empty = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={"expected_revision": 0, "path": second_path.model_dump(mode="json")},
    )
    assert created_empty["code"] == 201
    unit_a = LearningUnit(
        unit_id="journey-delete-unit-a",
        path_id=second_path.path_id,
        ordinal=1,
        title="Unit A",
        band=Band.A2,
    )
    unit_b = LearningUnit(
        unit_id="journey-delete-unit-b",
        path_id=second_path.path_id,
        ordinal=2,
        title="Unit B",
        band=Band.A2,
    )
    for unit_value in (unit_a, unit_b):
        created_unit = json_request(
            runtime,
            "POST",
            f"/api/v1/teacher/learn/paths/{second_path.path_id}/units",
            token=tokens["teacher"],
            values={"expected_revision": 0, "unit": unit_value.model_dump(mode="json")},
        )
        assert created_unit["code"] == 201, created_unit["json"]
    ordered = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}/reorder",
        token=tokens["teacher"],
        values={
            "expected_revision": created_empty["json"]["revision"],
            "unit_ids": [unit_b.unit_id, unit_a.unit_id],
        },
    )
    assert ordered["code"] == 200, ordered["json"]
    stale_order = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}/reorder",
        token=tokens["teacher"],
        values={
            "expected_revision": created_empty["json"]["revision"],
            "unit_ids": [unit_a.unit_id, unit_b.unit_id],
        },
    )
    assert stale_order["code"] == 409
    ordered_path = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}",
        token=tokens["teacher"],
    )
    assert [row["unit_id"] for row in ordered_path["json"]["units"]] == [
        unit_b.unit_id,
        unit_a.unit_id,
    ]
    deleted_unit_a = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}/units/{unit_a.unit_id}",
        token=tokens["teacher"],
        query=f"expected_revision={ordered_path['json']['units'][1]['revision']}",
    )
    assert deleted_unit_a["code"] == 200
    remaining_empty_path = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}",
        token=tokens["teacher"],
    )
    deleted_empty = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/paths/{second_path.path_id}",
        token=tokens["teacher"],
        query=f"expected_revision={remaining_empty_path['json']['revision']}",
    )
    assert deleted_empty["code"] == 200, deleted_empty["json"]

    admin_path = LearningPath(
        path_id="journey-admin-path",
        title="Admin authoring path",
        band_from=Band.A2,
        band_to=Band.B1,
        content_version="admin-v1",
    )
    admin_created = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["admin"],
        values={"expected_revision": 0, "path": admin_path.model_dump(mode="json")},
    )
    assert admin_created["code"] == 201, admin_created["json"]
    admin_deleted = request(
        runtime,
        "DELETE",
        f"/api/v1/teacher/learn/paths/{admin_path.path_id}",
        token=tokens["admin"],
        query=f"expected_revision={admin_created['json']['revision']}",
    )
    assert admin_deleted["code"] == 200


def test_student_attempt_teacher_insights_and_append_only_override(journey_runtime):
    runtime, actors, tokens, asr = journey_runtime
    path, unit, lesson = seed_lesson(
        runtime,
        path_id="journey-insights-path",
        unit_id="journey-insights-unit",
        lesson_id="journey-insights-lesson",
        title="Insights lesson",
    )
    path_record, _unit_record, saved = save_hierarchy(
        runtime, tokens["teacher"], path, unit, lesson
    )
    published = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/lessons/{lesson.lesson_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": saved["revision"]},
    )
    assert published["code"] == 201, published["json"]
    path_published = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/paths/{path.path_id}/publish",
        token=tokens["teacher"],
        values={"expected_revision": path_record["revision"]},
    )
    assert path_published["code"] == 201, path_published["json"]
    first_read_step = next(step for step in lesson.steps if step.kind.value == "read_aloud")
    asr.text = first_read_step.payload.text
    audio = wav_fixture()
    body, content_type = multipart(
        [
            ("lesson_id", lesson.lesson_id.encode(), None, None),
            ("lesson_version", str(published["json"]["version"]).encode(), None, None),
            ("step_id", first_read_step.step_id.encode(), None, None),
            ("idempotency_key", b"journey-insight-attempt", None, None),
            ("audio", audio, "answer.wav", "audio/wav"),
        ]
    )
    attempt = request(
        runtime,
        "POST",
        "/api/v1/learn/step-attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert attempt["code"] == 201, attempt["json"]
    assert attempt["json"]["state"] == "COMPLETED"
    assert attempt["json"]["result"]["status"] in {"PASS", "FAIL"}
    assert attempt["json"]["result"]["evidence"]
    assert "assessment" not in attempt["json"]
    assert "overall_score" not in attempt["json"]
    assert "band" not in attempt["json"]
    raw_result = json.dumps(attempt["json"]["result"], sort_keys=True)

    insight = request(
        runtime,
        "GET",
        f"/api/v1/teacher/learn/insights/{actors['student'].actor_id}",
        token=tokens["teacher"],
    )
    assert insight["code"] == 200, insight["json"]
    assert insight["json"]["step_completed"] == 1
    assert insight["json"]["audio_artifacts"] == 1
    assert "transcript" not in json.dumps(insight["json"]).lower()

    runtime.lessons._clock = lambda: datetime.now(UTC) + timedelta(days=2)
    due = request(
        runtime,
        "GET",
        "/api/v1/learn/reviews/due",
        token=tokens["student"],
    )
    assert due["code"] == 200, due["json"]
    assert len(due["json"]["reviews"]) == 1
    assert due["json"]["reviews"][0]["source_attempt_id"] == attempt["json"]["attempt_id"]

    override = json_request(
        runtime,
        "POST",
        f"/api/v1/teacher/learn/step-attempts/{attempt['json']['attempt_id']}/override",
        token=tokens["teacher"],
        values={
            "owner_id": actors["student"].actor_id,
            "new_value": "FAIL",
            "reason": "Teacher reviewed this speaking evidence.",
            "expected_revision": attempt["json"]["revision"],
        },
    )
    assert override["code"] == 200, override["json"]
    assert override["json"]["teacher_override"] == "FAIL"
    assert json.dumps(override["json"]["result"], sort_keys=True) == raw_result
    event = runtime.store.connection.execute(
        """SELECT actor_id,owner_id,old_value,new_value,reason,recorded_at
           FROM teacher_override_events WHERE attempt_id=?""",
        (attempt["json"]["attempt_id"],),
    ).fetchone()
    assert event[0] == actors["teacher"].actor_id
    assert event[1] == actors["student"].actor_id
    assert event[2] is None
    assert event[3] == "FAIL"
    assert event[4] == "Teacher reviewed this speaking evidence."
    assert datetime.fromisoformat(event[5]).tzinfo is not None

    learner_read = request(
        runtime,
        "GET",
        f"/api/v1/learn/step-attempts/{attempt['json']['attempt_id']}",
        token=tokens["student"],
    )
    assert learner_read["code"] == 200
    assert learner_read["json"]["teacher_override"] == "FAIL"
    assert json.dumps(learner_read["json"]["result"], sort_keys=True) == raw_result
