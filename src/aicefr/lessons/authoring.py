"""Bounded, data-only JSON codecs for lesson and learning-path authoring."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import Field

from aicefr.lessons.model import (
    LearningPath,
    LearningUnit,
    Lesson,
    PublishedLessonVersion,
)
from aicefr.practice.contracts import FrozenModel

EXPORT_FORMAT = "aicefr-lesson"
SCHEMA_VERSION = 1
MAX_EXPORT_BYTES = 1_048_576
MAX_PATH_EXPORT_BYTES = 2_097_152
MAX_JSON_DEPTH = 32
MAX_PATH_LESSONS = 31

_TOP_LEVEL_KEYS = frozenset({"format", "schema_version", "lesson_sha256", "lesson"})
_LESSON_KEYS = frozenset({"title", "summary", "band", "steps"})
_PATH_TOP_LEVEL_KEYS = frozenset({"format", "schema_version", "path_sha256", "bundle"})
_PATH_BUNDLE_KEYS = frozenset({"title", "description", "band_from", "band_to", "units"})
_PATH_UNIT_KEYS = frozenset({"ordinal", "title", "band", "topic", "learning_function", "lessons"})
_LOCATOR = re.compile(
    r"(?i)(?:https?|ftp|file|data|javascript|blob):|"
    r"(?<!\S)(?://[^\s]+|/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-][^\s]*|"
    r"[A-Za-z]:[\\/][^\s]+|\\\\[^\s]+)"
)
_FORBIDDEN_KEYS = frozenset(
    {
        "owner",
        "owner_id",
        "account",
        "account_id",
        "actor",
        "actor_id",
        "permission",
        "published",
        "published_at",
        "state",
        "content_hash",
        "url",
        "href",
        "blob",
        "blob_id",
        "media_path",
        "media_url",
        "filename",
    }
)


class LessonBundleEntry(FrozenModel):
    """Lesson snapshot associated with a source unit for path export."""

    unit_id: str = Field(min_length=1, max_length=128)
    lesson: Lesson | PublishedLessonVersion


class LearningPathBundle(FrozenModel):
    """A path plus typed lesson snapshots; IDs are association-only and never serialized."""

    path: LearningPath
    lessons: tuple[LessonBundleEntry, ...] = Field(max_length=MAX_PATH_LESSONS)


class ImportedPathDraft(FrozenModel):
    """Remapped path hierarchy ready for one repository transaction."""

    path: LearningPath
    lessons: tuple[Lesson, ...] = Field(max_length=MAX_PATH_LESSONS)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("lesson export contains non-JSON content") from exc


def _lesson_content(value: Lesson | PublishedLessonVersion) -> dict[str, Any]:
    if isinstance(value, (Lesson, PublishedLessonVersion)):
        return {
            "title": value.title,
            "summary": value.summary,
            "band": value.band.value,
            "steps": [step.model_dump(mode="json") for step in value.steps],
        }
    raise TypeError("export_lesson accepts only Lesson or PublishedLessonVersion")


def export_lesson(value: Lesson | PublishedLessonVersion) -> bytes:
    """Serialize typed content without identity, ownership, or publication authority."""
    content = _lesson_content(value)
    _check_tree(content)
    digest = hashlib.sha256(_canonical_json(content)).hexdigest()
    envelope = {
        "format": EXPORT_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "lesson_sha256": digest,
        "lesson": content,
    }
    result = _canonical_json(envelope)
    if len(result) > MAX_EXPORT_BYTES:
        raise ValueError(f"lesson export exceeds {MAX_EXPORT_BYTES} bytes")
    return result


def _path_bundle_content(value: LearningPathBundle) -> dict[str, Any]:
    if not isinstance(value, LearningPathBundle):
        raise TypeError("export_path accepts only LearningPathBundle")
    units_by_id = {unit.unit_id: unit for unit in value.path.units}
    if len(units_by_id) != len(value.path.units):
        raise ValueError("path unit ids must be unique")
    lessons_by_unit: dict[str, dict[str, Lesson | PublishedLessonVersion]] = {
        unit.unit_id: {} for unit in value.path.units
    }
    seen_lesson_ids: set[str] = set()
    for entry in value.lessons:
        if entry.unit_id not in units_by_id:
            raise ValueError("lesson bundle entry refers to a unit outside the path")
        lesson_id = entry.lesson.lesson_id
        if lesson_id in seen_lesson_ids:
            raise ValueError("lesson ids must be unique across a path bundle")
        seen_lesson_ids.add(lesson_id)
        lessons_by_unit[entry.unit_id][lesson_id] = entry.lesson

    expected = {lesson_id for unit in value.path.units for lesson_id in unit.lesson_ids}
    if expected != seen_lesson_ids:
        raise ValueError("path bundle must include every associated lesson exactly once")
    if len(seen_lesson_ids) > MAX_PATH_LESSONS:
        raise ValueError(f"path bundle is limited to {MAX_PATH_LESSONS} lessons")

    units: list[dict[str, Any]] = []
    for unit in value.path.units:
        by_id = lessons_by_unit[unit.unit_id]
        if set(by_id) != set(unit.lesson_ids):
            raise ValueError("lesson bundle unit association does not match path lesson ids")
        units.append(
            {
                "ordinal": unit.ordinal,
                "title": unit.title,
                "band": unit.band.value,
                "topic": unit.topic.value if unit.topic is not None else None,
                "learning_function": unit.learning_function,
                "lessons": [_lesson_content(by_id[lesson_id]) for lesson_id in unit.lesson_ids],
            }
        )
    return {
        "title": value.path.title,
        "description": value.path.description,
        "band_from": value.path.band_from.value,
        "band_to": value.path.band_to.value,
        "units": units,
    }


def export_path(value: LearningPathBundle) -> bytes:
    """Serialize an ordered path hierarchy without source identity or media authority."""
    content = _path_bundle_content(value)
    _check_tree(content)
    digest = hashlib.sha256(_canonical_json(content)).hexdigest()
    envelope = {
        "format": "aicefr-learning-path",
        "schema_version": SCHEMA_VERSION,
        "path_sha256": digest,
        "bundle": content,
    }
    result = _canonical_json(envelope)
    if len(result) > MAX_PATH_EXPORT_BYTES:
        raise ValueError(f"path export exceeds {MAX_PATH_EXPORT_BYTES} bytes")
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _check_nesting(raw: bytes) -> None:
    depth = 0
    quoted = False
    escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == ord("\\"):
                escaped = True
            elif byte == ord('"'):
                quoted = False
            continue
        if byte == ord('"'):
            quoted = True
        elif byte in (ord("{"), ord("[")):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
        elif byte in (ord("}"), ord("]")):
            depth -= 1


def _check_tree(value: Any, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key.casefold() in _FORBIDDEN_KEYS:
                raise ValueError(f"unsupported authoring field: {key}")
            _check_tree(child, depth + 1)
    elif isinstance(value, (tuple, list)):
        if len(value) > 100:
            raise ValueError("lesson content collections are limited to 100 items")
        for child in value:
            _check_tree(child, depth + 1)
    elif isinstance(value, str):
        if _LOCATOR.search(value):
            raise ValueError("external URLs and filesystem/blob references are not importable")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number is forbidden")


def _decode(
    data: bytes,
    *,
    max_bytes: int = MAX_EXPORT_BYTES,
    pre_tree_check: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if not isinstance(data, bytes):
        raise TypeError("lesson import input must be bytes")
    if not data:
        raise ValueError("lesson export is empty")
    if len(data) > max_bytes:
        raise ValueError(f"authoring export exceeds {max_bytes} bytes")
    _check_nesting(data)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("lesson export is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("lesson export root must be an object")
    if pre_tree_check is not None:
        pre_tree_check(value)
    _check_tree(value)
    return value


def import_lesson(data: bytes, *, lesson_id: str) -> Lesson:
    """Validate a bounded file and return draft content under a service-chosen ID."""
    if not isinstance(lesson_id, str) or not lesson_id or len(lesson_id) > 128:
        raise ValueError("service-selected lesson_id must contain 1–128 characters")
    envelope = _decode(data)
    if set(envelope) != _TOP_LEVEL_KEYS:
        raise ValueError("lesson export contains missing or unknown top-level fields")
    if envelope["format"] != EXPORT_FORMAT:
        raise ValueError("unsupported lesson export format")
    version = envelope["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError("unsupported lesson export schema version")
    content = envelope["lesson"]
    if not isinstance(content, dict) or set(content) != _LESSON_KEYS:
        raise ValueError("lesson export content contains missing or unknown fields")
    if not isinstance(content.get("steps"), list) or len(content["steps"]) > 40:
        raise ValueError("lesson export is limited to 40 steps")
    digest = envelope["lesson_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("lesson export checksum is malformed")
    actual = hashlib.sha256(_canonical_json(content)).hexdigest()
    if not hmac.compare_digest(digest, actual):
        raise ValueError("lesson export checksum does not match content")

    lesson_data = {
        **content,
        "lesson_id": lesson_id,
        "revision": 1,
        "content_version": "import-v1",
    }
    try:
        return Lesson.model_validate_json(_canonical_json(lesson_data), strict=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"lesson export content is invalid: {exc}") from exc


def import_path(
    data: bytes,
    *,
    id_factory: Callable[[str], str],
) -> ImportedPathDraft:
    """Validate a complete path bundle and remap every ID before repository insertion.

    The factory receives only ``path``, ``unit``, or ``lesson`` and is called in
    hierarchy order. Storage must validate the complete returned value before its
    transaction so malformed bundles cannot leave partial imports.
    """
    if not callable(id_factory):
        raise TypeError("id_factory must be callable")

    def check_unit_count(value: dict[str, Any]) -> None:
        bundle = value.get("bundle")
        units = bundle.get("units") if isinstance(bundle, dict) else None
        if isinstance(units, list) and len(units) > 100:
            raise ValueError("path export is limited to 100 units")

    envelope = _decode(
        data,
        max_bytes=MAX_PATH_EXPORT_BYTES,
        pre_tree_check=check_unit_count,
    )
    if set(envelope) != _PATH_TOP_LEVEL_KEYS:
        raise ValueError("path export contains missing or unknown top-level fields")
    if envelope["format"] != "aicefr-learning-path":
        raise ValueError("unsupported path export format")
    version = envelope["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError("unsupported path export schema version")
    content = envelope["bundle"]
    if not isinstance(content, dict) or set(content) != _PATH_BUNDLE_KEYS:
        raise ValueError("path export content contains missing or unknown fields")
    units_data = content["units"]
    if not isinstance(units_data, list) or len(units_data) > 100:
        raise ValueError("path export is limited to 100 units")
    if any(not isinstance(item, dict) or set(item) != _PATH_UNIT_KEYS for item in units_data):
        raise ValueError("path export unit contains missing or unknown fields")
    lesson_count = 0
    for unit in units_data:
        lessons = unit["lessons"]
        if not isinstance(lessons, list):
            raise ValueError("path unit lessons must be an array")
        lesson_count += len(lessons)
    if lesson_count > MAX_PATH_LESSONS:
        raise ValueError(f"path export is limited to {MAX_PATH_LESSONS} lessons")
    digest = envelope["path_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("path export checksum is malformed")
    actual = hashlib.sha256(_canonical_json(content)).hexdigest()
    if not hmac.compare_digest(digest, actual):
        raise ValueError("path export checksum does not match content")

    generated: set[str] = set()

    def new_id(kind: str) -> str:
        try:
            value = id_factory(kind)
        except Exception as exc:
            raise ValueError(f"id_factory failed for {kind}") from exc
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError(f"id_factory must return a 1–128 character {kind} id")
        if value in generated:
            raise ValueError("id_factory returned a duplicate id")
        generated.add(value)
        return value

    path_id = new_id("path")
    imported_units: list[LearningUnit] = []
    imported_lessons: list[Lesson] = []
    for unit_data in units_data:
        unit_id = new_id("unit")
        unit_lesson_ids: list[str] = []
        for lesson_data in unit_data["lessons"]:
            if not isinstance(lesson_data, dict) or set(lesson_data) != _LESSON_KEYS:
                raise ValueError("nested lesson contains missing or unknown fields")
            steps = lesson_data["steps"]
            if not isinstance(steps, list) or len(steps) > 40:
                raise ValueError("path lesson is limited to 40 steps")
            lesson_id = new_id("lesson")
            lesson = _validate_lesson_content(lesson_data, lesson_id=lesson_id)
            imported_lessons.append(lesson)
            unit_lesson_ids.append(lesson_id)
        try:
            imported_units.append(
                LearningUnit(
                    unit_id=unit_id,
                    path_id=path_id,
                    ordinal=unit_data["ordinal"],
                    title=unit_data["title"],
                    band=unit_data["band"],
                    topic=unit_data["topic"],
                    learning_function=unit_data["learning_function"],
                    lesson_ids=tuple(unit_lesson_ids),
                )
            )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"path unit content is invalid: {exc}") from exc
    try:
        path = LearningPath(
            path_id=path_id,
            title=content["title"],
            description=content["description"],
            band_from=content["band_from"],
            band_to=content["band_to"],
            units=tuple(imported_units),
            content_version="import-v1",
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(f"path content is invalid: {exc}") from exc
    return ImportedPathDraft(path=path, lessons=tuple(imported_lessons))


def _validate_lesson_content(content: dict[str, Any], *, lesson_id: str) -> Lesson:
    lesson_data = {
        **content,
        "lesson_id": lesson_id,
        "revision": 1,
        "content_version": "import-v1",
    }
    try:
        return Lesson.model_validate_json(_canonical_json(lesson_data), strict=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"lesson export content is invalid: {exc}") from exc
