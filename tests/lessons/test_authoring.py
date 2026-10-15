from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from aicefr.contracts import Band
from aicefr.lessons.authoring import (
    EXPORT_FORMAT,
    MAX_EXPORT_BYTES,
    MAX_PATH_EXPORT_BYTES,
    SCHEMA_VERSION,
    LearningPathBundle,
    LessonBundleEntry,
    export_lesson,
    export_path,
    import_lesson,
    import_path,
)
from aicefr.lessons.lint import lint_lesson
from aicefr.lessons.model import (
    FreePayload,
    FreeRound,
    GapPayload,
    KeywordsPayload,
    LearningPath,
    LearningUnit,
    Lesson,
    LessonStage,
    LessonStep,
    LookUpPayload,
    OutlinePayload,
    PictureChoice,
    PicturePayload,
    PublishedLessonVersion,
    ReadAloudPayload,
    RepeatPayload,
    StarterPayload,
    StepKind,
    Topic,
)

NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)


def step(kind: StepKind, payload, ordinal: int) -> LessonStep:
    stages = {
        StepKind.READ_ALOUD: LessonStage.MODEL,
        StepKind.REPEAT: LessonStage.MODEL,
        StepKind.LOOK_UP: LessonStage.CONTROLLED,
        StepKind.GAP: LessonStage.CONTROLLED,
        StepKind.KEYWORDS: LessonStage.GUIDED,
        StepKind.STARTER: LessonStage.GUIDED,
        StepKind.PICTURE: LessonStage.GUIDED,
        StepKind.OUTLINE: LessonStage.GUIDED,
        StepKind.FREE: LessonStage.FREE,
    }
    return LessonStep(
        step_id=f"step-{ordinal}",
        ordinal=ordinal,
        stage=stages[kind],
        kind=kind,
        instruction="Luyện tập.",
        payload=payload,
        rules_version="lesson-rules-v1",
    )


def nine_kind_lesson() -> Lesson:
    steps = (
        step(
            StepKind.READ_ALOUD,
            ReadAloudPayload(kind=StepKind.READ_ALOUD, text="Say hello.", max_seconds=5),
            1,
        ),
        step(StepKind.REPEAT, RepeatPayload(kind=StepKind.REPEAT, text="hello", max_seconds=5), 2),
        step(
            StepKind.LOOK_UP,
            LookUpPayload(kind=StepKind.LOOK_UP, text="hello", show_seconds=2, max_seconds=5),
            3,
        ),
        step(
            StepKind.GAP,
            GapPayload(kind=StepKind.GAP, text="Say ___", answers=("hello",), max_seconds=5),
            4,
        ),
        step(
            StepKind.KEYWORDS,
            KeywordsPayload(kind=StepKind.KEYWORDS, keywords=("hello",), max_seconds=5),
            5,
        ),
        step(
            StepKind.STARTER,
            StarterPayload(kind=StepKind.STARTER, text="Speak", starter="I am", max_seconds=5),
            6,
        ),
        step(
            StepKind.PICTURE,
            PicturePayload(
                kind=StepKind.PICTURE,
                prompt="Describe",
                pictures=(PictureChoice(choice_id="picture-a", description="A red kite"),),
                max_seconds=5,
            ),
            7,
        ),
        step(
            StepKind.OUTLINE,
            OutlinePayload(
                kind=StepKind.OUTLINE, text="Tell a story", points=("start",), max_seconds=5
            ),
            8,
        ),
        step(
            StepKind.FREE,
            FreePayload(
                kind=StepKind.FREE,
                rounds=(
                    FreeRound(duration_seconds=10, prompt="First"),
                    FreeRound(duration_seconds=5, prompt="Again"),
                ),
                max_seconds=10,
            ),
            9,
        ),
    )
    return Lesson(
        lesson_id="source-private-lesson-id",
        title="A lesson",
        summary="A safe summary.",
        band=Band.A2,
        steps=steps,
        revision=7,
        content_version="content-v7",
    )


def envelope(content: dict, **extra) -> bytes:
    digest = hashlib.sha256(
        json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    value = {
        "format": EXPORT_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "lesson_sha256": digest,
        "lesson": content,
        **extra,
    }
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def content_from_file(data: bytes) -> dict:
    return json.loads(data)["lesson"]


def test_export_import_round_trips_all_nine_kinds_as_a_new_draft() -> None:
    source = nine_kind_lesson()
    original = source.model_dump(mode="json")
    exported = export_lesson(source)
    assert exported == export_lesson(source)
    assert b"source-private-lesson-id" not in exported
    assert b"content_version" not in exported and b"revision" not in exported

    imported = import_lesson(exported, lesson_id="service-selected-id")
    assert imported.lesson_id == "service-selected-id"
    assert imported.revision == 1 and imported.content_version == "import-v1"
    assert imported.title == source.title and imported.summary == source.summary
    assert imported.band is source.band
    assert tuple(item.kind for item in imported.steps) == tuple(StepKind)
    assert lint_lesson(imported).valid
    assert source.model_dump(mode="json") == original


def test_export_rejects_unsupported_objects_and_linked_content() -> None:
    with pytest.raises(TypeError, match="accepts only Lesson"):
        export_lesson(object())  # type: ignore[arg-type]
    lesson = nine_kind_lesson().model_copy(update={"summary": "Read https://example.test"})
    with pytest.raises(ValueError, match="URLs and filesystem/blob references"):
        export_lesson(lesson)


def test_export_accepts_published_snapshot_but_does_not_export_its_authority() -> None:
    from tests.lessons.test_domain import full_lesson

    published = PublishedLessonVersion.from_lesson(full_lesson(), version=3, published_at=NOW)
    data = export_lesson(published)
    assert b"published_at" not in data and b"content_hash" not in data
    clone = import_lesson(data, lesson_id="new-draft")
    assert clone.lesson_id == "new-draft"
    assert clone.revision == 1 and clone.content_version == "import-v1"


def test_import_rejects_bad_schema_duplicate_keys_and_checksum_tampering() -> None:
    valid = export_lesson(nine_kind_lesson())
    with pytest.raises(ValueError, match="not valid UTF-8 JSON"):
        import_lesson(b"not json", lesson_id="target")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        import_lesson(
            valid.replace(b'"format":', b'"format":"aicefr-lesson","format":'),
            lesson_id="target",
        )
    with pytest.raises(ValueError, match="unsupported lesson export schema"):
        import_lesson(
            valid.replace(b'"schema_version":1', b'"schema_version":2'), lesson_id="target"
        )
    with pytest.raises(ValueError, match="checksum does not match"):
        import_lesson(valid.replace(b"A lesson", b"B lesson"), lesson_id="target")
    with pytest.raises(TypeError, match="must be bytes"):
        import_lesson(valid.decode(), lesson_id="target")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="empty"):
        import_lesson(b"", lesson_id="target")
    with pytest.raises(ValueError, match="root must be an object"):
        import_lesson(b"[]", lesson_id="target")
    with pytest.raises(ValueError, match="unsupported lesson export format"):
        import_lesson(valid.replace(b"aicefr-lesson", b"other-format"), lesson_id="target")
    with pytest.raises(ValueError, match="checksum is malformed"):
        import_lesson(
            envelope(content_from_file(valid), lesson_sha256="z" * 64), lesson_id="target"
        )
    with pytest.raises(ValueError, match="service-selected lesson_id"):
        import_lesson(valid, lesson_id="x" * 129)


@pytest.mark.parametrize(
    "data",
    (
        b'{"format":"aicefr-lesson","schema_version":NaN}',
        b'{"format":"aicefr-lesson","schema_version":1e999}',
    ),
)
def test_import_rejects_nonfinite_numbers(data: bytes) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        import_lesson(data, lesson_id="target")


def test_import_bounds_bytes_depth_lessons_steps_and_text_without_truncation() -> None:
    with pytest.raises(ValueError, match="exceeds 1048576 bytes"):
        import_lesson(b" " * (MAX_EXPORT_BYTES + 1), lesson_id="target")
    deep = b"[" * 33 + b"]" * 33
    with pytest.raises(ValueError, match="nesting exceeds 32"):
        import_lesson(deep, lesson_id="target")

    content = content_from_file(export_lesson(nine_kind_lesson()))
    too_many_steps = {**content, "steps": [content["steps"][0]] * 41}
    with pytest.raises(ValueError, match="limited to 40 steps"):
        import_lesson(envelope(too_many_steps), lesson_id="target")

    ref = content_from_file(export_lesson(nine_kind_lesson()))
    ref["steps"][1]["payload"]["text"] = "a " * 513
    with pytest.raises(ValueError, match="512 tokens"):
        import_lesson(envelope(ref), lesson_id="target")

    long_text = content_from_file(export_lesson(nine_kind_lesson()))
    long_text["steps"][0]["instruction"] = "x" * 4_097
    with pytest.raises(ValueError, match="4096 characters"):
        import_lesson(envelope(long_text), lesson_id="target")

    too_many_keywords = content_from_file(export_lesson(nine_kind_lesson()))
    too_many_keywords["steps"][4]["payload"]["keywords"] = ["word"] * 101
    with pytest.raises(ValueError, match="collections are limited to 100"):
        import_lesson(envelope(too_many_keywords), lesson_id="target")


def test_export_size_bound_and_json_depth_scanner_allow_delimiters_inside_strings() -> None:
    repeated = "x" * 2_048
    steps = tuple(
        LessonStep(
            step_id=f"keyword-{ordinal}",
            ordinal=ordinal,
            stage=LessonStage.GUIDED,
            kind=StepKind.KEYWORDS,
            instruction="Describe.",
            payload=KeywordsPayload(
                kind=StepKind.KEYWORDS,
                keywords=(repeated,) * 100,
                max_seconds=5,
            ),
            rules_version="lesson-rules-v1",
        )
        for ordinal in range(1, 7)
    )
    large = Lesson(lesson_id="large", title="Large", band=Band.A2, steps=steps)
    with pytest.raises(ValueError, match="exceeds 1048576 bytes"):
        export_lesson(large)

    content = content_from_file(export_lesson(nine_kind_lesson()))
    content["summary"] = 'A bracketed string: [ ] { "quoted" }.'
    restored = import_lesson(envelope(content), lesson_id="safe-string")
    assert restored.summary == content["summary"]


@pytest.mark.parametrize(
    "unsafe_value",
    (
        "https://example.test/media.wav",
        "file:///etc/passwd",
        "/home/student/audio.wav",
        "C:\\private\\audio.wav",
        "blob:secret-token",
    ),
)
def test_export_and_import_reject_external_or_filesystem_references(unsafe_value: str) -> None:
    content = content_from_file(export_lesson(nine_kind_lesson()))
    content["summary"] = unsafe_value
    with pytest.raises(ValueError, match="URLs and filesystem/blob references"):
        import_lesson(envelope(content), lesson_id="target")


def test_import_rejects_authority_identity_and_media_injection() -> None:
    content = content_from_file(export_lesson(nine_kind_lesson()))
    with pytest.raises(ValueError, match="unsupported authoring field"):
        import_lesson(envelope(content, owner_id="someone-else"), lesson_id="target")
    injected = {**content, "published_at": NOW.isoformat()}
    with pytest.raises(ValueError, match="unsupported authoring field"):
        import_lesson(envelope(injected), lesson_id="target")


def path_bundle() -> LearningPathBundle:
    first = nine_kind_lesson()
    second = first.model_copy(update={"lesson_id": "second-source-lesson", "title": "Second"})
    path = LearningPath(
        path_id="private-source-path",
        title="Ordered path",
        description="A path description.",
        band_from=Band.A2,
        band_to=Band.B2,
        units=(
            LearningUnit(
                unit_id="private-unit-a",
                path_id="private-source-path",
                ordinal=1,
                title="First unit",
                band=Band.A2,
                topic=Topic.DAILY_LIFE,
                learning_function="introduce",
                lesson_ids=(first.lesson_id,),
            ),
            LearningUnit(
                unit_id="private-unit-b",
                path_id="private-source-path",
                ordinal=2,
                title="Second unit",
                band=Band.B1,
                topic=Topic.TRAVEL,
                learning_function="extend",
                lesson_ids=(second.lesson_id,),
            ),
        ),
        content_version="source-v7",
    )
    return LearningPathBundle(
        path=path,
        lessons=(
            LessonBundleEntry(unit_id="private-unit-a", lesson=first),
            LessonBundleEntry(unit_id="private-unit-b", lesson=second),
        ),
    )


def test_path_export_import_round_trips_hierarchy_in_order_with_fresh_ids() -> None:
    source = path_bundle()
    original = source.model_dump(mode="json")
    data = export_path(source)
    assert data == export_path(source)
    for private_id in (
        "private-source-path",
        "private-unit-a",
        "private-source-lesson-id",
        "second-source-lesson",
        "source-v7",
    ):
        assert private_id.encode() not in data

    kinds: list[str] = []

    def allocate(kind: str) -> str:
        kinds.append(kind)
        return f"destination-{kind}-{len(kinds)}"

    imported = import_path(data, id_factory=allocate)
    assert kinds == ["path", "unit", "lesson", "unit", "lesson"]
    assert imported.path.path_id == "destination-path-1"
    assert imported.path.content_version == "import-v1"
    assert [unit.ordinal for unit in imported.path.units] == [1, 2]
    assert [unit.title for unit in imported.path.units] == ["First unit", "Second unit"]
    assert imported.path.units[0].lesson_ids == ("destination-lesson-3",)
    assert imported.path.units[1].lesson_ids == ("destination-lesson-5",)
    assert [lesson.title for lesson in imported.lessons] == ["A lesson", "Second"]
    assert all(
        lesson.revision == 1 and lesson.content_version == "import-v1"
        for lesson in imported.lessons
    )
    assert tuple(step.kind for step in imported.lessons[0].steps) == tuple(StepKind)
    assert source.model_dump(mode="json") == original


def test_path_bundle_rejects_incomplete_or_invalid_hierarchy_before_returning_draft() -> None:
    source = path_bundle()
    with pytest.raises(ValueError, match="include every associated lesson"):
        export_path(source.model_copy(update={"lessons": source.lessons[:1]}))

    data = export_path(source)
    envelope_data = json.loads(data)
    envelope_data["bundle"]["units"][1]["ordinal"] = 1
    tampered = json.dumps(envelope_data, ensure_ascii=False).encode()
    with pytest.raises(ValueError, match="checksum does not match"):
        import_path(tampered, id_factory=lambda kind: f"new-{kind}")

    with pytest.raises(ValueError, match="duplicate id"):
        import_path(data, id_factory=lambda _kind: "same-id")
    with pytest.raises(TypeError, match="id_factory must be callable"):
        import_path(data, id_factory=None)  # type: ignore[arg-type]


def test_path_import_rejects_boundedness_schema_and_forbidden_media_fields() -> None:
    with pytest.raises(ValueError, match="exceeds 2097152 bytes"):
        import_path(b" " * (MAX_PATH_EXPORT_BYTES + 1), id_factory=lambda kind: kind)
    data = export_path(path_bundle())
    content = json.loads(data)["bundle"]
    content["units"][0]["lessons"][0]["steps"][0]["payload"]["blob_id"] = "private"
    with pytest.raises(ValueError, match="unsupported authoring field"):
        import_path(
            json.dumps(
                {
                    "format": "aicefr-learning-path",
                    "schema_version": SCHEMA_VERSION,
                    "path_sha256": "0" * 64,
                    "bundle": content,
                }
            ).encode(),
            id_factory=lambda kind: f"new-{kind}",
        )


def path_file(content: dict, **overrides) -> bytes:
    envelope_data = {
        "format": "aicefr-learning-path",
        "schema_version": SCHEMA_VERSION,
        "path_sha256": hashlib.sha256(
            json.dumps(
                content,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "bundle": content,
        **overrides,
    }
    return json.dumps(envelope_data, ensure_ascii=False, allow_nan=False).encode()


def test_path_import_rejects_schema_bounds_and_invalid_nested_content() -> None:
    content = json.loads(export_path(path_bundle()))["bundle"]
    unit = content["units"][0]
    lesson = unit["lessons"][0]
    valid = path_file(content)
    ids = iter(range(100))

    def fresh_id(kind: str) -> str:
        return f"{kind}-{next(ids)}"

    with pytest.raises(TypeError, match="must be bytes"):
        import_path(valid.decode(), id_factory=fresh_id)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="top-level fields"):
        import_path(path_file(content, unexpected=True), id_factory=fresh_id)
    with pytest.raises(ValueError, match="unsupported path export format"):
        import_path(path_file(content, format="other"), id_factory=fresh_id)
    with pytest.raises(ValueError, match="schema version"):
        import_path(path_file(content, schema_version=True), id_factory=fresh_id)
    with pytest.raises(ValueError, match="unsupported authoring field"):
        import_path(path_file({**content, "owner_id": "foreign"}), id_factory=fresh_id)
    with pytest.raises(ValueError, match="limited to 100 units"):
        import_path(path_file({**content, "units": [{}] * 101}), id_factory=fresh_id)
    with pytest.raises(ValueError, match="unit contains missing or unknown"):
        import_path(
            path_file({**content, "units": [{**unit, "extra": "value"}]}),
            id_factory=fresh_id,
        )
    with pytest.raises(ValueError, match="lessons must be an array"):
        import_path(
            path_file({**content, "units": [{**unit, "lessons": "none"}]}),
            id_factory=fresh_id,
        )
    with pytest.raises(ValueError, match="limited to 31 lessons"):
        import_path(
            path_file({**content, "units": [{**unit, "lessons": [lesson] * 32}]}),
            id_factory=fresh_id,
        )
    with pytest.raises(ValueError, match="checksum is malformed"):
        import_path(path_file(content, path_sha256="bad"), id_factory=fresh_id)
    with pytest.raises(ValueError, match="checksum does not match"):
        tampered = json.loads(valid)
        tampered["bundle"]["title"] = "changed"
        import_path(json.dumps(tampered).encode(), id_factory=fresh_id)
    with pytest.raises(ValueError, match="nested lesson contains missing or unknown"):
        bad = {**content, "units": [{**unit, "lessons": [{**lesson, "extra": "x"}]}]}
        import_path(path_file(bad), id_factory=fresh_id)
    with pytest.raises(ValueError, match="limited to 40 steps"):
        bad_lesson = {**lesson, "steps": [lesson["steps"][0]] * 41}
        bad = {**content, "units": [{**unit, "lessons": [bad_lesson]}]}
        import_path(path_file(bad), id_factory=fresh_id)
    with pytest.raises(ValueError, match="lesson export content is invalid"):
        bad_lesson = {**lesson, "band": "A1"}
        bad = {**content, "units": [{**unit, "lessons": [bad_lesson]}]}
        import_path(path_file(bad), id_factory=fresh_id)
    with pytest.raises(ValueError, match="path unit content is invalid"):
        bad = {**content, "units": [{**unit, "ordinal": 0}]}
        import_path(path_file(bad), id_factory=fresh_id)
    with pytest.raises(ValueError, match="path content is invalid"):
        bad = {**content, "title": ""}
        import_path(path_file(bad), id_factory=fresh_id)

    with pytest.raises(ValueError, match="id_factory failed"):
        import_path(valid, id_factory=lambda _kind: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(ValueError, match="id_factory must return"):
        import_path(valid, id_factory=lambda _kind: "")
    injected = content_from_file(export_lesson(nine_kind_lesson()))
    injected["steps"][6]["payload"]["pictures"][0]["blob_id"] = "blob-private"
    with pytest.raises(ValueError, match="unsupported authoring field"):
        import_lesson(envelope(injected), lesson_id="target")
