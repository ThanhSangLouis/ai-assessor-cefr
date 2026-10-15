"""Fail-closed CV+ calibration artifact loading and prediction-set construction.

Calibration artifacts are private derivatives and are expected outside the Git
tree. The file hash passed to :func:`load_calibration_artifact` must come from
trusted server configuration; the artifact's own checksum is never trusted.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aicefr.contracts import Band, ReasonCode
from aicefr.trust.contracts import ConformalSet

MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_JSON_DEPTH = 64
ARTIFACT_VERSION = "cvplus-v1"
PINNED_REFERENCE_SHA256 = "3c09d2583a26e8cc057c0cf36dfb7637d15dfdc901cf00c4e25faef9ce6ef885"
PINNED_REFERENCE_MODEL_SHA256 = "7cdeb2a04aa0db770d52d6ff20b49cc371b9cb690f0ace89e5233b5d65bb521a"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_BANDS = (Band.A2, Band.B1, Band.B2)


class CalibrationArtifactError(ValueError):
    """Raised when a calibration artifact cannot be verified or used."""

    def __init__(self, reason: ReasonCode | str, message: str | None = None) -> None:
        if message is None:
            message = str(reason)
            reason = ReasonCode.CALIBRATION_INVALID
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class FoldModel:
    fold_index: int
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coef: tuple[float, ...]
    intercept: float


@dataclass(frozen=True)
class CalibrationResidual:
    sample_id: str | None
    speaker_group: str | None
    fold_index: int
    residual: float


@dataclass(frozen=True)
class CalibrationArtifact:
    version: str
    method: str
    calibration_id: str
    checksum: str
    model_sha256: str
    feature_order: tuple[str, ...]
    band_thresholds: tuple[float, float]
    folds: tuple[FoldModel, ...]
    residuals: tuple[CalibrationResidual, ...]
    fold_of: tuple[int, ...]


def load_calibration_artifact(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_model_sha256: str,
    expected_feature_order: Sequence[str],
    expected_band_thresholds: Mapping[str, float],
) -> CalibrationArtifact:
    """Read a bounded JSON artifact and bind it to trusted scorer identity."""
    if not _valid_sha(expected_sha256) or not _valid_sha(expected_model_sha256):
        raise CalibrationArtifactError(ReasonCode.CALIBRATION_INVALID, "trusted hashes are invalid")
    file_path = Path(path)
    try:
        if not file_path.is_file():
            raise CalibrationArtifactError(
                ReasonCode.CALIBRATION_MISSING, "calibration artifact is missing"
            )
        if file_path.stat().st_size > MAX_ARTIFACT_BYTES:
            raise CalibrationArtifactError(
                ReasonCode.CALIBRATION_INVALID, "calibration artifact is too large"
            )
        raw = file_path.read_bytes()
    except OSError as exc:
        raise CalibrationArtifactError(
            ReasonCode.CALIBRATION_MISSING, "calibration artifact is unavailable"
        ) from exc
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise CalibrationArtifactError(
            ReasonCode.CALIBRATION_INVALID, "calibration artifact is too large"
        )
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise CalibrationArtifactError(
            ReasonCode.CALIBRATION_HASH_MISMATCH, "calibration artifact checksum mismatch"
        )
    try:
        text = raw.decode("utf-8")
        _ensure_json_depth(text)
        data = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
        if digest == PINNED_REFERENCE_SHA256:
            return _parse_pinned_reference(
                data,
                digest=digest,
                expected_model_sha256=expected_model_sha256,
                expected_feature_order=tuple(expected_feature_order),
                expected_band_thresholds=expected_band_thresholds,
            )
        return _parse_artifact(
            data,
            digest=digest,
            expected_model_sha256=expected_model_sha256,
            expected_feature_order=tuple(expected_feature_order),
            expected_band_thresholds=expected_band_thresholds,
        )
    except CalibrationArtifactError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        KeyError,
        ValueError,
        OverflowError,
        RecursionError,
    ) as exc:
        raise CalibrationArtifactError(
            ReasonCode.CALIBRATION_INVALID, "calibration artifact schema is invalid"
        ) from exc


def _ensure_json_depth(text: str) -> None:
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
                raise ValueError("JSON nesting exceeds the depth limit")
        elif char in "]}":
            depth -= 1


def predict_conformal(
    features: Mapping[str, float] | Sequence[float],
    artifact: CalibrationArtifact,
    *,
    alpha: float = 0.10,
) -> ConformalSet:
    """Compute CV+ interval endpoints and conservatively map them to CEFR bands.

    CV+ lower and upper scores use finite-sample ranks floor(alpha*(n+1)) and
    ceil((1-alpha)*(n+1)), respectively. Endpoints are not rounded before band
    inclusion; an endpoint on a boundary includes both adjacent bands.
    """
    if not math.isfinite(alpha) or not 0.0 < alpha < 0.5:
        raise CalibrationArtifactError(ReasonCode.CALIBRATION_INVALID, "alpha is invalid")
    vector = _ordered_features(features, artifact.feature_order)
    fold_by_index = {model.fold_index: model for model in artifact.folds}
    lower_candidates: list[float] = []
    upper_candidates: list[float] = []
    for residual in artifact.residuals:
        model = fold_by_index[residual.fold_index]
        center = _fold_predict(vector, model)
        radius = abs(residual.residual)
        # Residuals are finite and centers are clipped to [1, 6], so these
        # sums remain finite even at the largest representable residual.
        lower_candidates.append(center - radius)
        upper_candidates.append(center + radius)
    n = len(artifact.residuals)
    low_rank = math.floor(alpha * (n + 1))
    high_rank = math.ceil((1.0 - alpha) * (n + 1))
    low = _finite_sample_order_statistic(lower_candidates, low_rank, lower=True)
    high = _finite_sample_order_statistic(upper_candidates, high_rank, lower=False)
    # The production scorer's range is [1, 6]. Clipping to that declared range
    # is conservative for band membership and keeps API endpoints finite.
    low, high = max(1.0, low), min(6.0, high)
    if low > high:
        raise CalibrationArtifactError(ReasonCode.CALIBRATION_INVALID, "CV+ interval is invalid")
    thresholds = artifact.band_thresholds
    included: list[Band] = []
    band_intervals = (
        (Band.A2, 1.0, thresholds[0]),
        (Band.B1, thresholds[0], thresholds[1]),
        (Band.B2, thresholds[1], 6.0),
    )
    for band, band_low, band_high in band_intervals:
        if low <= band_high and high >= band_low:
            included.append(band)
    return ConformalSet(
        alpha=alpha,
        bands=tuple(included),
        calibration_id=artifact.calibration_id,
        checksum=artifact.checksum,
        low=low,
        high=high,
    )


def _parse_artifact(
    data: Any,
    *,
    digest: str,
    expected_model_sha256: str,
    expected_feature_order: tuple[str, ...],
    expected_band_thresholds: Mapping[str, float],
) -> CalibrationArtifact:
    if not isinstance(data, dict):
        raise CalibrationArtifactError("artifact root must be an object")
    allowed_keys = {
        "version",
        "calibration_id",
        "model_sha256",
        "feature_order",
        "band_thresholds",
        "folds",
        "n_residuals",
        "residuals",
        "provenance",
    }
    if set(data) - allowed_keys:
        raise CalibrationArtifactError("calibration artifact contains unknown fields")
    if data.get("version") != ARTIFACT_VERSION:
        raise CalibrationArtifactError("unsupported calibration artifact version")
    calibration_id = _required_opaque_id(data.get("calibration_id"), "calibration_id")
    model_sha256 = _required_sha(data.get("model_sha256"), "model_sha256")
    if model_sha256 != expected_model_sha256:
        raise CalibrationArtifactError("calibration artifact belongs to another scorer")
    feature_order = _feature_order(data.get("feature_order"))
    if not expected_feature_order or feature_order != expected_feature_order:
        raise CalibrationArtifactError("calibration feature order does not match loaded scorer")
    thresholds_data = data.get("band_thresholds")
    if not isinstance(thresholds_data, dict) or set(thresholds_data) != {"A2_B1", "B1_B2"}:
        raise CalibrationArtifactError("band_thresholds must define A2_B1 and B1_B2")
    thresholds = (
        _finite_number(thresholds_data["A2_B1"], "A2_B1"),
        _finite_number(thresholds_data["B1_B2"], "B1_B2"),
    )
    if not (1.0 <= thresholds[0] < thresholds[1] <= 6.0):
        raise CalibrationArtifactError("band thresholds must be ordered inside [1, 6]")
    trusted_thresholds = _validate_trusted_thresholds(expected_band_thresholds, thresholds)
    folds_data = data.get("folds")
    if not isinstance(folds_data, list) or not 2 <= len(folds_data) <= 100:
        raise CalibrationArtifactError("fold model count must be between 2 and 100")
    folds = tuple(_parse_fold(item, len(feature_order)) for item in folds_data)
    fold_indices = [fold.fold_index for fold in folds]
    if sorted(fold_indices) != list(range(len(folds))):
        raise CalibrationArtifactError("fold indices must be unique contiguous integers")
    residuals_data = data.get("residuals")
    if not isinstance(residuals_data, list) or not 1 <= len(residuals_data) <= 100_000:
        raise CalibrationArtifactError("residual count must be between 1 and 100000")
    declared_count = data.get("n_residuals")
    if type(declared_count) is not int or declared_count != len(residuals_data):
        raise CalibrationArtifactError("n_residuals does not match residual rows")
    residuals = tuple(_parse_residual(item, len(folds)) for item in residuals_data)
    sample_ids = [row.sample_id for row in residuals]
    if len(set(sample_ids)) != len(residuals):
        raise CalibrationArtifactError("sample_id values must be unique")
    speaker_folds: dict[str, int] = {}
    for row in residuals:
        prior_fold = speaker_folds.setdefault(row.speaker_group, row.fold_index)
        if prior_fold != row.fold_index:
            raise CalibrationArtifactError(
                "each speaker group must map to exactly one held-out fold"
            )
    _validate_provenance(data.get("provenance"), model_sha256, len(speaker_folds))
    return CalibrationArtifact(
        version=ARTIFACT_VERSION,
        method="cv+",
        calibration_id=calibration_id,
        checksum=digest,
        model_sha256=model_sha256,
        feature_order=feature_order,
        band_thresholds=trusted_thresholds,
        folds=folds,
        residuals=residuals,
        fold_of=tuple(row.fold_index for row in residuals),
    )


def _parse_pinned_reference(
    data: Any,
    *,
    digest: str,
    expected_model_sha256: str,
    expected_feature_order: tuple[str, ...],
    expected_band_thresholds: Mapping[str, float],
) -> CalibrationArtifact:
    """Explicit compatibility adapter for the pinned Sang CV+ JSON schema.

    That source contains fold assignments/residuals but no sample or speaker
    identifiers. Those identities remain unavailable; runtime CV+ prediction
    only needs the indexed fold model and residual. No group identity is made up.
    """
    if digest != PINNED_REFERENCE_SHA256 or expected_model_sha256 != PINNED_REFERENCE_MODEL_SHA256:
        raise CalibrationArtifactError(
            ReasonCode.CALIBRATION_INVALID, "legacy reference is not pinned"
        )
    if not isinstance(data, dict) or data.get("method") != "cv+":
        raise CalibrationArtifactError("pinned reference method is invalid")
    version = data.get("conformal_version")
    if not isinstance(version, str) or _OPAQUE_ID.fullmatch(version) is None:
        raise CalibrationArtifactError("pinned reference version is invalid")
    if data.get("model_sha256") != PINNED_REFERENCE_MODEL_SHA256:
        raise CalibrationArtifactError("pinned reference model hash is invalid")
    feature_order = _feature_order(data.get("feature_order"))
    if feature_order != expected_feature_order:
        raise CalibrationArtifactError("pinned reference feature order differs from loaded scorer")
    _validate_trusted_thresholds(expected_band_thresholds, None)
    source_folds = data.get("folds")
    n_folds = data.get("n_folds")
    if (
        type(n_folds) is not int
        or not 2 <= n_folds <= 100
        or not isinstance(source_folds, list)
        or len(source_folds) != n_folds
    ):
        raise CalibrationArtifactError("pinned reference fold count is invalid")
    folds = tuple(
        _parse_fold({"fold_index": index, **fold}, len(feature_order))
        for index, fold in enumerate(source_folds)
    )
    n = data.get("n")
    fold_of_data = data.get("fold_of")
    residual_data = data.get("residuals")
    if (
        type(n) is not int
        or not 1 <= n <= 100_000
        or not isinstance(fold_of_data, list)
        or len(fold_of_data) != n
        or not isinstance(residual_data, list)
        or len(residual_data) != n
    ):
        raise CalibrationArtifactError("pinned reference n/fold_of/residuals are inconsistent")
    fold_of: list[int] = []
    residuals: list[CalibrationResidual] = []
    for fold_index, residual in zip(fold_of_data, residual_data, strict=True):
        if type(fold_index) is not int or not 0 <= fold_index < n_folds:
            raise CalibrationArtifactError("pinned reference fold_of contains an invalid index")
        value = _finite_number(residual, "pinned residual")
        if value < 0.0:
            raise CalibrationArtifactError("pinned CV+ residuals must be absolute and non-negative")
        fold_of.append(fold_index)
        residuals.append(CalibrationResidual(None, None, fold_index, value))
    alpha = _finite_number(data.get("alpha_default"), "pinned alpha_default")
    if not 0.0 < alpha < 0.5:
        raise CalibrationArtifactError("pinned alpha_default is invalid")
    calibration_id = "reference-" + hashlib.sha256(version.encode()).hexdigest()[:16]
    return CalibrationArtifact(
        version=version,
        method="cv+",
        calibration_id=calibration_id,
        checksum=digest,
        model_sha256=PINNED_REFERENCE_MODEL_SHA256,
        feature_order=feature_order,
        band_thresholds=_validate_trusted_thresholds(expected_band_thresholds, None),
        folds=folds,
        residuals=tuple(residuals),
        fold_of=tuple(fold_of),
    )


def _parse_fold(value: Any, vector_size: int) -> FoldModel:
    if not isinstance(value, dict):
        raise CalibrationArtifactError("fold model must be an object")
    if set(value) != {"fold_index", "mean", "scale", "coef", "intercept"}:
        raise CalibrationArtifactError("fold model contains missing or unknown fields")
    index = value.get("fold_index")
    if type(index) is not int or index < 0:
        raise CalibrationArtifactError("fold_index must be a non-negative integer")
    mean = _vector(value.get("mean"), "mean", vector_size)
    scale = _vector(value.get("scale"), "scale", vector_size)
    coef = _vector(value.get("coef"), "coef", vector_size)
    if any(number <= 0.0 for number in scale):
        raise CalibrationArtifactError("fold scale values must be greater than zero")
    return FoldModel(index, mean, scale, coef, _finite_number(value.get("intercept"), "intercept"))


def _parse_residual(value: Any, fold_count: int) -> CalibrationResidual:
    if not isinstance(value, dict):
        raise CalibrationArtifactError("residual row must be an object")
    if set(value) != {"sample_id", "speaker_group", "fold_index", "residual"}:
        raise CalibrationArtifactError("residual row contains missing or unknown fields")
    sample_id = _required_sha(value.get("sample_id"), "sample_id")
    speaker_group = _required_sha(value.get("speaker_group"), "speaker_group")
    fold_index = value.get("fold_index")
    if type(fold_index) is not int or not 0 <= fold_index < fold_count:
        raise CalibrationArtifactError("residual fold_index is outside the fold model list")
    residual_value = _finite_number(value.get("residual"), "residual")
    if residual_value < 0.0:
        raise CalibrationArtifactError("CV+ residuals must be absolute and non-negative")
    return CalibrationResidual(
        sample_id=sample_id,
        speaker_group=speaker_group,
        fold_index=fold_index,
        residual=residual_value,
    )


def _ordered_features(
    features: Mapping[str, float] | Sequence[float], feature_order: tuple[str, ...]
) -> tuple[float, ...]:
    if isinstance(features, Mapping):
        if tuple(features.keys()) != feature_order:
            raise CalibrationArtifactError(
                "feature mapping must use the exact scorer feature order"
            )
        raw_values = tuple(features[name] for name in feature_order)
    elif isinstance(features, Sequence) and not isinstance(features, (str, bytes)):
        raw_values = tuple(features)
        if len(raw_values) != len(feature_order):
            raise CalibrationArtifactError("feature vector size does not match calibration model")
    else:
        raise CalibrationArtifactError("features must be an ordered mapping or numeric sequence")
    return tuple(_finite_number(value, "feature") for value in raw_values)


def _fold_predict(vector: tuple[float, ...], model: FoldModel) -> float:
    score = model.intercept
    for value, mean, scale, coef in zip(vector, model.mean, model.scale, model.coef, strict=True):
        score += coef * (value - mean) / scale
        if not math.isfinite(score):
            raise CalibrationArtifactError("fold prediction overflowed")
    return min(6.0, max(1.0, score))


def _finite_sample_order_statistic(values: list[float], rank: int, *, lower: bool) -> float:
    ordered = sorted(values)
    if lower and rank <= 0:
        return float("-inf")
    if not lower and rank > len(ordered):
        return float("inf")
    return ordered[min(max(rank, 1), len(ordered)) - 1]


def _feature_order(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise CalibrationArtifactError("feature_order must be a non-empty list")
    names = tuple(_required_string(item, "feature name") for item in value)
    if len(set(names)) != len(names):
        raise CalibrationArtifactError("feature_order names must be unique")
    return names


def _validate_trusted_thresholds(
    expected: Mapping[str, float], artifact: tuple[float, float] | None
) -> tuple[float, float]:
    if set(expected) != {"A2_B1", "B1_B2"}:
        raise CalibrationArtifactError("trusted scorer band thresholds are required")
    trusted = (
        _finite_number(expected["A2_B1"], "trusted A2_B1"),
        _finite_number(expected["B1_B2"], "trusted B1_B2"),
    )
    if not (1.0 <= trusted[0] < trusted[1] <= 6.0):
        raise CalibrationArtifactError("trusted scorer band thresholds are invalid")
    if artifact is not None and artifact != trusted:
        raise CalibrationArtifactError("calibration band thresholds differ from loaded scorer")
    return trusted


def _vector(value: Any, name: str, expected_size: int) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != expected_size:
        raise CalibrationArtifactError(f"{name} size must match feature_order")
    return tuple(_finite_number(item, name) for item in value)


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationArtifactError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CalibrationArtifactError(f"{name} must be finite")
    return result


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise CalibrationArtifactError(f"{name} must be a bounded non-empty string")
    return value


def _required_opaque_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or _OPAQUE_ID.fullmatch(value) is None:
        raise CalibrationArtifactError(f"{name} must be a bounded opaque identifier")
    return value


def _validate_provenance(value: Any, model_sha256: str, group_count_expected: int) -> None:
    if not isinstance(value, dict):
        raise CalibrationArtifactError("artifact provenance is required")
    allowed = {
        "manifest_sha256",
        "model_sha256",
        "config_sha256",
        "seed",
        "split_role",
        "training_recipe_version",
        "alpha_default",
        "speaker_group_count",
        "reference_sha256",
        "provenance_sha256",
        "source_format",
    }
    if set(value) - allowed:
        raise CalibrationArtifactError("artifact provenance contains unknown fields")
    if value.get("model_sha256") != model_sha256:
        raise CalibrationArtifactError("provenance model hash does not match artifact")
    if value.get("split_role") != "calibration":
        raise CalibrationArtifactError("artifact split role must be calibration")
    _required_sha(value.get("config_sha256"), "config_sha256")
    if "manifest_sha256" in value:
        _required_sha(value["manifest_sha256"], "manifest_sha256")
    if "provenance_sha256" in value:
        _required_sha(value["provenance_sha256"], "provenance_sha256")
    if "reference_sha256" in value and value["reference_sha256"] != PINNED_REFERENCE_SHA256:
        raise CalibrationArtifactError("provenance reference hash is not pinned")
    if "manifest_sha256" not in value and "provenance_sha256" not in value:
        raise CalibrationArtifactError("manifest or reference provenance hash is required")
    if type(value.get("seed")) is not int:
        raise CalibrationArtifactError("provenance seed must be an integer")
    _required_opaque_id(value.get("training_recipe_version"), "training_recipe_version")
    alpha = _finite_number(value.get("alpha_default"), "alpha_default")
    if not 0.0 < alpha < 0.5:
        raise CalibrationArtifactError("provenance alpha_default is invalid")
    group_count = value.get("speaker_group_count")
    if type(group_count) is not int or group_count != group_count_expected:
        raise CalibrationArtifactError("provenance speaker_group_count is invalid")
    if "source_format" in value:
        _required_opaque_id(value["source_format"], "source_format")


def _required_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _valid_sha(value):
        raise CalibrationArtifactError(f"{name} must be a lowercase SHA-256")
    return value


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CalibrationArtifactError("duplicate JSON keys are forbidden")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CalibrationArtifactError(f"non-finite JSON value {value} is forbidden")
