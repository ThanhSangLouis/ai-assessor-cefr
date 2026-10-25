from __future__ import annotations

import hashlib
import io
import json

import pytest

from aicefr.contracts import ActorRole, Band
from aicefr.lessons.authoring import LearningPathBundle, export_path
from aicefr.lessons.model import LearningPath
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.practice.contracts import PracticePurpose


class FixtureAsr:
    """Deterministic injected ASR; negative API cases must never use real weights."""

    def detect_language(self, _audio):
        return "en", 0.99

    def transcribe(self, _audio):
        raise AssertionError("validation case unexpectedly called ASR")


class FixtureVad:
    """Deterministic injected VAD; fixture deliberately returns no segments."""

    def segments(self, _samples, _sample_rate_hz):
        return ()


@pytest.fixture
def api_runtime(tmp_path):
    config = _demo_config()
    config["model_artifact"] = str(tmp_path / "missing-scorer.json")
    runtime = create_runtime(
        tmp_path / "learning-validation-runtime",
        config=config,
        asr_engine=FixtureAsr(),
        vad_engine=FixtureVad(),
    )
    actors = {}
    for role, name in (
        (ActorRole.STUDENT, "student"),
        (ActorRole.TEACHER, "teacher"),
        (ActorRole.ADMIN, "admin"),
    ):
        actor = runtime.auth.bootstrap_fixture_account(
            f"fixture-validation-{name}", role, "fixture-password"
        )
        actors[name] = actor
        if role is ActorRole.STUDENT:
            runtime.consents.activate(
                actor,
                str(config.get("consent_version", "consent-v2")),
                audio_storage_allowed=True,
            )
    tokens = {
        name: runtime.auth.login(actor.actor_id, "fixture-password")
        for name, actor in actors.items()
    }
    try:
        yield runtime, actors, tokens
    finally:
        runtime.close()


def request(
    runtime,
    method: str,
    path: str,
    *,
    token: str | None,
    body: bytes = b"",
    content_type: str = "application/json",
    origin: str | None = "http://127.0.0.1:8000",
    bearer: bool = False,
    query: str = "",
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
    }
    if token is not None:
        environ["HTTP_AUTHORIZATION" if bearer else "HTTP_COOKIE"] = (
            f"Bearer {token}" if bearer else f"aicefr_session={token}"
        )
    if origin is not None:
        environ["HTTP_ORIGIN"] = origin

    def start_response(status, headers):
        captured.update(status=status, headers=headers)

    response = b"".join(runtime.app(environ, start_response))
    captured["code"] = int(captured["status"].split()[0])
    captured["body"] = response
    captured["json"] = json.loads(response) if response else None
    return captured


def json_request(runtime, method: str, path: str, *, token: str, values: object, **kwargs):
    return request(
        runtime,
        method,
        path,
        token=token,
        body=json.dumps(values, ensure_ascii=False, allow_nan=False).encode(),
        **kwargs,
    )


def multipart(parts: list[tuple[str, bytes, str | None, str | None]], boundary: str = "validation"):
    body = bytearray()
    for name, value, filename, content_type in parts:
        body.extend(f"--{boundary}\r\n".encode())
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename is not None:
            disposition += f'; filename="{filename}"'
        body.extend(f"{disposition}\r\n".encode())
        if content_type is not None:
            body.extend(f"Content-Type: {content_type}\r\n".encode())
        body.extend(b"\r\n")
        body.extend(value)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def practice_parts(*, duplicate_mission=False, injected_field=False, mime="audio/wav"):
    parts = [
        ("mission_id", b"PR-FLU-A2", None, None),
        ("prompt_version", b"practice-v1", None, None),
        ("purpose", b"PRACTICE", None, None),
        ("idempotency_key", b"validation-attempt", None, None),
    ]
    if duplicate_mission:
        parts.append(("mission_id", b"PR-COH-A2", None, None))
    if injected_field:
        parts.append(("actor_id", b"admin", None, None))
    parts.append(("audio", b"not decoded for these cases", "fixture.wav", mime))
    return multipart(parts)


def snapshot(runtime):
    tables = (
        "learning_paths",
        "learning_units",
        "learning_lessons",
        "lesson_versions",
        "lesson_steps",
        "practice_attempts",
        "step_attempts",
        "learning_audio_artifacts",
        "audit",
    )
    counts = {
        table: runtime.store.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
    blobs = tuple(sorted(path.name for path in runtime.practice._blobs.root.iterdir()))
    return counts, blobs


def exported_path_file() -> bytes:
    return export_path(
        LearningPathBundle(
            path=LearningPath(
                path_id="private-source-id",
                title="Validation fixture path",
                description="No private metadata.",
                band_from=Band.A2,
                band_to=Band.B1,
                units=(),
                content_version="fixture-v1",
            ),
            lessons=(),
        )
    )


def reseal_path(bundle: dict) -> bytes:
    canonical = json.dumps(
        bundle, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return json.dumps(
        {
            "format": "aicefr-learning-path",
            "schema_version": 1,
            "path_sha256": hashlib.sha256(canonical).hexdigest(),
            "bundle": bundle,
        },
        ensure_ascii=False,
    ).encode()


def _import_request(runtime, token, path_bytes: bytes):
    return json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=token,
        values={"path_json": path_bytes.decode("utf-8")},
    )


def test_duplicate_and_injected_multipart_fields_are_controlled_and_side_effect_free(api_runtime):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    for body, content_type in (
        practice_parts(duplicate_mission=True),
        practice_parts(injected_field=True),
    ):
        response = request(
            runtime,
            "POST",
            "/api/v1/practice/attempts",
            token=tokens["student"],
            body=body,
            content_type=content_type,
        )
        assert response["code"] == 400
        assert response["json"] == {"error": "INVALID_MULTIPART"}
        assert before == snapshot(runtime)
        assert b"admin" not in response["body"]


def test_malformed_multipart_and_unsupported_mime_do_not_create_attempts_or_blobs(api_runtime):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    malformed = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=b"this is not a multipart body",
        content_type="multipart/form-data; boundary=missing",
    )
    assert malformed["code"] == 400
    assert malformed["json"] == {"error": "INVALID_MULTIPART"}

    body, content_type = practice_parts(mime="text/plain")
    unsupported = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert unsupported["code"] == 415
    assert unsupported["json"] == {"error": "UNSUPPORTED_REQUEST_FORMAT"}
    assert before == snapshot(runtime)


@pytest.mark.parametrize("field_value", [True, 1.75])
def test_path_revision_rejects_boolean_and_fractional_json_without_mutation(
    api_runtime, field_value
):
    runtime, _, tokens = api_runtime
    path_id = f"revision-{str(field_value).lower().replace('.', '-')}"
    path = {
        "path_id": path_id,
        "title": "Original title",
        "description": "",
        "band_from": "A2",
        "band_to": "B1",
        "units": [],
        "content_version": "fixture-v1",
    }
    created = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={"expected_revision": 0, "path": path},
    )
    assert created["code"] == 201
    before = snapshot(runtime)
    before_row = runtime.store.connection.execute(
        "SELECT revision,title FROM learning_paths WHERE path_id=?", (path_id,)
    ).fetchone()
    path["title"] = "Tampered title"
    response = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths",
        token=tokens["teacher"],
        values={"expected_revision": field_value, "path": path},
    )
    assert response["code"] == 400
    assert response["json"] == {"error": "INVALID_REQUEST"}
    assert before == snapshot(runtime)
    after_row = runtime.store.connection.execute(
        "SELECT revision,title FROM learning_paths WHERE path_id=?", (path_id,)
    ).fetchone()
    assert tuple(before_row) == tuple(after_row)


@pytest.mark.parametrize("variant", ["checksum", "schema", "owner", "publication", "deep"])
def test_path_import_rejects_malformed_or_authority_injection_without_any_write(
    api_runtime, variant
):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    source = json.loads(exported_path_file())
    if variant == "checksum":
        source["bundle"]["title"] = "Tampered without reseal"
        payload = json.dumps(source).encode()
    elif variant == "schema":
        source["schema_version"] = 2
        payload = json.dumps(source).encode()
    elif variant in {"owner", "publication"}:
        key = "owner_id" if variant == "owner" else "published_at"
        source["bundle"][key] = "untrusted"
        payload = reseal_path(source["bundle"])
    else:
        deep: object = "too-deep"
        for _ in range(34):
            deep = [deep]
        source["bundle"]["untrusted"] = deep
        payload = reseal_path(source["bundle"])
    response = _import_request(runtime, tokens["teacher"], payload)
    assert response["code"] == 422
    assert response["json"] == {"error": "INVALID_REQUEST"}
    assert before == snapshot(runtime)
    assert b"untrusted" not in response["body"]


def test_oversized_json_audio_and_lesson_text_are_rejected_before_storage(api_runtime):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    too_large_bundle = b" " * (2_097_153)
    oversized = _import_request(runtime, tokens["teacher"], too_large_bundle)
    assert oversized["code"] == 422
    assert before == snapshot(runtime)

    audio_limit = runtime.practice._blobs.max_bytes
    body, content_type = multipart(
        [
            ("mission_id", b"PR-FLU-A2", None, None),
            ("prompt_version", b"practice-v1", None, None),
            ("purpose", b"PRACTICE", None, None),
            ("idempotency_key", b"oversized-audio", None, None),
            ("audio", b"x" * (audio_limit + 1), "large.wav", "audio/wav"),
        ]
    )
    oversized_audio = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert oversized_audio["code"] == 422
    assert before == snapshot(runtime)

    huge_body = b"x" * (runtime.app._max_request_bytes + 1)
    oversized_request = request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["teacher"],
        body=huge_body,
        content_type="application/json",
    )
    assert oversized_request["code"] == 413
    assert oversized_request["json"] == {"error": "REQUEST_TOO_LARGE"}
    assert before == snapshot(runtime)

    source = json.loads(exported_path_file())
    source["bundle"]["description"] = "x" * 4_097
    response = _import_request(runtime, tokens["teacher"], reseal_path(source["bundle"]))
    assert response["code"] == 422
    assert before == snapshot(runtime)


def test_method_role_and_cookie_csrf_boundaries_do_not_mutate_learning_storage(api_runtime):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    student_authoring = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["student"],
        values={"path_json": exported_path_file().decode()},
    )
    assert student_authoring["code"] == 403

    missing_cookie_origin = json_request(
        runtime,
        "POST",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["teacher"],
        values={"path_json": exported_path_file().decode()},
        origin=None,
    )
    assert missing_cookie_origin["code"] == 403

    wrong_method = request(
        runtime,
        "PUT",
        "/api/v1/teacher/learn/paths/import",
        token=tokens["teacher"],
        body=b"{}",
    )
    assert wrong_method["code"] == 404
    assert wrong_method["json"] == {"error": "ROUTE_NOT_FOUND"}

    no_session = request(runtime, "GET", "/api/v1/learn/path", token=None)
    assert no_session["code"] == 401
    assert before == snapshot(runtime)


def test_unknown_mission_version_step_and_round_are_controlled_without_side_effects(api_runtime):
    runtime, _, tokens = api_runtime
    before = snapshot(runtime)
    mission = runtime.practice.catalogue()[0]
    wrong_kind_body, wrong_kind_type = multipart(
        [
            ("mission_id", mission.mission_id.encode(), None, None),
            ("prompt_version", mission.prompt_version.encode(), None, None),
            ("purpose", b"UNKNOWN_KIND", None, None),
            ("idempotency_key", b"unknown-kind", None, None),
            ("audio", b"fixture", "fixture.wav", "audio/wav"),
        ]
    )
    wrong_kind = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=wrong_kind_body,
        content_type=wrong_kind_type,
    )
    assert wrong_kind["code"] == 400
    assert before == snapshot(runtime)

    unknown_mission_body, unknown_mission_type = multipart(
        [
            ("mission_id", b"unknown-mission", None, None),
            ("prompt_version", mission.prompt_version.encode(), None, None),
            ("purpose", PracticePurpose.PRACTICE.value.encode(), None, None),
            ("idempotency_key", b"unknown-mission", None, None),
            ("audio", b"fixture", "fixture.wav", "audio/wav"),
        ]
    )
    unknown_mission = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=unknown_mission_body,
        content_type=unknown_mission_type,
    )
    assert unknown_mission["code"] == 404
    assert before == snapshot(runtime)

    body, content_type = multipart(
        [
            ("mission_id", mission.mission_id.encode(), None, None),
            ("prompt_version", b"unsupported-prompt-version", None, None),
            ("purpose", PracticePurpose.PRACTICE.value.encode(), None, None),
            ("idempotency_key", b"unknown-prompt", None, None),
            ("audio", b"fixture", "fixture.wav", "audio/wav"),
        ]
    )
    bad_mission_version = request(
        runtime,
        "POST",
        "/api/v1/practice/attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert bad_mission_version["code"] == 422
    assert before == snapshot(runtime)

    path = runtime.learning_repository.list_paths(published_only=True)[0]
    lesson_id = next(lesson_id for unit in path.units for lesson_id in unit.lesson_ids)
    lesson = runtime.lessons.lesson(lesson_id)
    assert lesson is not None
    fields = [
        ("lesson_id", lesson_id.encode(), None, None),
        ("lesson_version", str(lesson.version).encode(), None, None),
        ("step_id", b"unknown-step", None, None),
        ("idempotency_key", b"unknown-step-key", None, None),
        ("audio", b"fixture", "fixture.wav", "audio/wav"),
    ]
    body, content_type = multipart(fields)
    unknown_step = request(
        runtime,
        "POST",
        "/api/v1/learn/step-attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert unknown_step["code"] == 404
    assert before == snapshot(runtime)

    free_step = next(step for step in lesson.steps if step.kind.value == "free")
    fields = [
        ("lesson_id", lesson_id.encode(), None, None),
        ("lesson_version", str(lesson.version).encode(), None, None),
        ("step_id", free_step.step_id.encode(), None, None),
        ("round_index", b"99", None, None),
        ("idempotency_key", b"unknown-round-key", None, None),
        ("audio", b"fixture", "fixture.wav", "audio/wav"),
    ]
    body, content_type = multipart(fields)
    unknown_round = request(
        runtime,
        "POST",
        "/api/v1/learn/step-attempts",
        token=tokens["student"],
        body=body,
        content_type=content_type,
    )
    assert unknown_round["code"] == 422
    assert unknown_round["json"] == {"error": "INVALID_REQUEST"}
    assert before == snapshot(runtime)
