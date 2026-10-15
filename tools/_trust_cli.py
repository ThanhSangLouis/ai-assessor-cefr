"""Shared strict JSON and provenance helpers for SCRUM-69 offline tools."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class InputError(ValueError):
    """Manifest/configuration input is incomplete or unsafe."""


def read_json(path: str | Path) -> tuple[Any, str]:
    file_path = Path(path)
    try:
        if not file_path.is_file() or file_path.stat().st_size > MAX_INPUT_BYTES:
            raise InputError("input file is missing or exceeds the size limit")
        raw = file_path.read_bytes()
    except OSError as exc:
        raise InputError("input file is unavailable") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise InputError("input file exceeds the size limit")
    try:
        text = raw.decode("utf-8")
        ensure_json_depth(text)
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InputError("input must be valid UTF-8 JSON without NaN/Infinity") from exc
    return value, hashlib.sha256(raw).hexdigest()


def ensure_json_depth(text: str) -> None:
    """Reject excessive container nesting before the JSON parser builds objects."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise InputError("input JSON nesting exceeds the depth limit")
        elif char in "]}":
            depth -= 1


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate JSON keys are forbidden")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise InputError(f"non-finite JSON value {value} is forbidden")


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    try:
        if not file_path.is_file() or file_path.stat().st_size > MAX_INPUT_BYTES:
            raise InputError("model file is missing or exceeds the size limit")
        return hashlib.sha256(file_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise InputError("model file is unavailable") from exc


def finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{name} must be finite")
    return result


def bounded_string(value: Any, name: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise InputError(f"{name} must be a bounded non-empty string")
    return value


def require_sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise InputError(f"{name} must be a lowercase SHA-256")
    return value


def write_json(path: str | Path, value: Any) -> str:
    output = Path(path)
    repository_root = Path(__file__).resolve().parent.parent
    resolved_output = output.resolve()
    if resolved_output.is_relative_to(repository_root):
        raise InputError("full artifacts and reports must be written outside the repository")
    payload = json_bytes(value)
    temporary: str | None = None
    try:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=resolved_output.parent,
            prefix=f".{resolved_output.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, resolved_output)
    except OSError as exc:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise InputError("output cannot be written") from exc
    return hashlib.sha256(payload).hexdigest()


def ensure_distinct_paths(inputs: list[str | Path], outputs: list[str | Path]) -> None:
    """Prevent a CLI output from replacing any input or another output."""
    input_paths = {Path(value).resolve() for value in inputs}
    output_paths = [Path(value).resolve() for value in outputs]
    if len(set(output_paths)) != len(output_paths):
        raise InputError("output paths must be distinct")
    if input_paths.intersection(output_paths):
        raise InputError("output paths must not overwrite input files")
