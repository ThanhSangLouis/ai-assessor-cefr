#!/usr/bin/env python3
"""Assemble a CV+ artifact from supplied out-of-fold models and held-out data.

This command never fits a model. Its inputs must provide fold models trained by
the declared recipe and a calibration-only manifest with speaker-group splits.
The resulting artifact is a private derivative; write it outside the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from typing import Any

from tools._trust_cli import (
    InputError,
    bounded_string,
    ensure_distinct_paths,
    finite_number,
    json_bytes,
    read_json,
    require_sha256,
    sha256_file,
    write_json,
)


def assemble(
    manifest: dict[str, Any],
    *,
    manifest_sha256: str,
    model: dict[str, Any],
    model_sha256: str,
    alpha: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_sha256(manifest_sha256, "manifest SHA-256")
    require_sha256(model_sha256, "model SHA-256")
    if not math.isfinite(alpha) or not 0.0 < alpha < 0.5:
        raise InputError("alpha must be finite and between zero and 0.5")
    if manifest.get("version") != "cvplus-manifest-v1":
        raise InputError("unsupported manifest version")
    if manifest.get("split_role") != "calibration":
        raise InputError(
            "calibration assembly requires split_role=calibration; confirmation data is forbidden"
        )
    if manifest.get("model_sha256") != model_sha256:
        raise InputError("manifest model SHA-256 does not match supplied scorer artifact")
    if not isinstance(manifest.get("seed"), int) or isinstance(manifest.get("seed"), bool):
        raise InputError("manifest seed must be an integer")
    recipe = manifest.get("training_recipe")
    if (
        not isinstance(recipe, dict)
        or not isinstance(recipe.get("version"), str)
        or not recipe["version"].strip()
    ):
        raise InputError("versioned training_recipe is required")
    feature_order = _feature_order(manifest.get("feature_order"))
    model_feature_order = _feature_order(model.get("feature_order"))
    if feature_order != model_feature_order:
        raise InputError("manifest feature_order differs from the loaded scorer")
    thresholds = model.get("band_thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != {"A2_B1", "B1_B2"}:
        raise InputError("scorer artifact has invalid band thresholds")
    band_thresholds = {key: finite_number(thresholds[key], key) for key in ("A2_B1", "B1_B2")}
    if not (1.0 <= band_thresholds["A2_B1"] < band_thresholds["B1_B2"] <= 6.0):
        raise InputError("scorer band thresholds must be ordered inside [1, 6]")
    fold_specs = manifest.get("folds")
    if not isinstance(fold_specs, list) or not 2 <= len(fold_specs) <= 100:
        raise InputError("fold model count must be between 2 and 100")
    folds = [
        _validate_fold(item, index, len(feature_order)) for index, item in enumerate(fold_specs)
    ]
    training_groups = [set(fold["training_groups"]) for fold in folds]
    if len({fold["fold_index"] for fold in folds}) != len(folds):
        raise InputError("fold indices must be unique")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise InputError("held-out calibration samples are required")
    seen_samples: set[str] = set()
    speaker_fold: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for sample in samples:
        if not isinstance(sample, dict) or sample.get("role") != "calibration":
            raise InputError("each sample must be explicitly marked role=calibration")
        sample_id = _opaque_id(sample.get("sample_id"), "sample_id")
        speaker_group = _opaque_id(sample.get("speaker_group"), "speaker_group")
        if sample_id in seen_samples:
            raise InputError("sample_id must be unique")
        seen_samples.add(sample_id)
        fold_index = sample.get("fold_index")
        if type(fold_index) is not int or not 0 <= fold_index < len(folds):
            raise InputError("sample fold_index is outside supplied fold models")
        prior_fold = speaker_fold.setdefault(speaker_group, fold_index)
        if prior_fold != fold_index:
            raise InputError("each speaker_group must be held out by exactly one fold")
        if speaker_group in training_groups[fold_index]:
            raise InputError("held-out speaker_group appears in that fold's training groups")
        vector = _sample_vector(sample.get("features"), feature_order)
        score = finite_number(sample.get("reference_score"), "reference_score")
        if not 1.0 <= score <= 6.0:
            raise InputError("reference_score must be inside [1, 6]")
        model_fold = folds[fold_index]["model"]
        heldout_prediction = _predict(vector, model_fold)
        rows.append(
            {
                "sample_id": sample_id,
                "speaker_group": speaker_group,
                "fold_index": fold_index,
                "residual": abs(score - heldout_prediction),
            }
        )
        if len(rows) > 100_000:
            raise InputError("calibration sample count exceeds 100000")
    if len(speaker_fold) < 2:
        raise InputError("at least two distinct speaker groups are required")
    for index, heldout_groups in enumerate(
        {
            fold_index: {
                speaker for speaker, assigned in speaker_fold.items() if assigned == fold_index
            }
            for fold_index in range(len(folds))
        }.values()
    ):
        if heldout_groups & training_groups[index]:
            raise InputError("fold train and held-out speaker groups overlap")
    fold_models = [{"fold_index": fold["fold_index"], **fold["model"]} for fold in folds]
    identity = {
        "manifest_sha256": manifest_sha256,
        "model_sha256": model_sha256,
        "seed": manifest["seed"],
        "training_recipe": recipe,
        "alpha": alpha,
    }
    config_sha256 = hashlib.sha256(json_bytes(identity)).hexdigest()
    calibration_id = "cvplus-" + config_sha256[:20]
    artifact: dict[str, Any] = {
        "version": "cvplus-v1",
        "calibration_id": calibration_id,
        "model_sha256": model_sha256,
        "feature_order": list(feature_order),
        "band_thresholds": band_thresholds,
        "folds": fold_models,
        "n_residuals": len(rows),
        "residuals": rows,
        "provenance": {
            "manifest_sha256": manifest_sha256,
            "model_sha256": model_sha256,
            "config_sha256": config_sha256,
            "seed": manifest["seed"],
            "split_role": "calibration",
            "training_recipe_version": recipe["version"],
            "alpha_default": alpha,
            "speaker_group_count": len(speaker_fold),
        },
    }
    report = {
        "status": "ASSEMBLED",
        "method": "CV+",
        "calibration_id": calibration_id,
        "alpha_default": alpha,
        "n_residuals": len(rows),
        "speaker_group_count": len(speaker_fold),
        "manifest_sha256": manifest_sha256,
        "model_sha256": model_sha256,
        "config_sha256": config_sha256,
        "seed": manifest["seed"],
        "split_role": "calibration",
        "empirical_coverage": "NOT_EVALUATED",
        "claim": (
            "Artifact assembly from supplied fold models and calibration data; "
            "no retraining or coverage claim."
        ),
    }
    return artifact, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="calibration-only JSON manifest")
    parser.add_argument(
        "--model-artifact", required=True, help="loaded scorer artifact used by this manifest"
    )
    parser.add_argument(
        "--output", required=True, help="private artifact output path outside the repository"
    )
    parser.add_argument("--report", help="optional deterministic JSON summary output path")
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args(argv)
    try:
        ensure_distinct_paths(
            [args.manifest, args.model_artifact],
            [args.output, *([args.report] if args.report else [])],
        )
        if not math.isfinite(args.alpha) or not 0.0 < args.alpha < 0.5:
            raise InputError("alpha must be finite and between zero and 0.5")
        manifest_value, manifest_sha256 = read_json(args.manifest)
        model_value, _ = read_json(args.model_artifact)
        if not isinstance(manifest_value, dict) or not isinstance(model_value, dict):
            raise InputError("manifest and scorer artifact roots must be objects")
        model_sha256 = sha256_file(args.model_artifact)
        model_sha256 = require_sha256(model_sha256, "model SHA-256")
        artifact, report = assemble(
            manifest_value,
            manifest_sha256=manifest_sha256,
            model=model_value,
            model_sha256=model_sha256,
            alpha=args.alpha,
        )
        artifact_sha256 = write_json(args.output, artifact)
        report["artifact_sha256"] = artifact_sha256
        if args.report:
            report["report_sha256"] = write_json(args.report, report)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (InputError, OSError, ValueError, TypeError, KeyError) as exc:
        # Avoid including user-supplied paths, transcripts, or raw input values.
        print(
            json.dumps({"status": "NOT_RUN", "reason": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2


def _validate_fold(value: Any, expected_index: int, feature_count: int) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or type(value.get("fold_index")) is not int
        or value.get("fold_index") != expected_index
    ):
        raise InputError("folds must be ordered by contiguous fold_index")
    model_value = value.get("model")
    if not isinstance(model_value, dict):
        raise InputError("each fold requires an explicitly supplied model")
    training_groups = value.get("training_groups")
    if not isinstance(training_groups, list) or not training_groups:
        raise InputError("each fold requires training_groups provenance")
    groups = [_opaque_id(group, "training group") for group in training_groups]
    if len(set(groups)) != len(groups):
        raise InputError("training_groups must be unique within each fold")
    vectors: dict[str, list[float]] = {}
    for name in ("mean", "scale", "coef"):
        raw = model_value.get(name)
        if not isinstance(raw, list) or len(raw) != feature_count:
            raise InputError(f"fold {name} vector must match feature_order")
        vectors[name] = [finite_number(item, f"fold {name}") for item in raw]
    if any(value <= 0 for value in vectors["scale"]):
        raise InputError("fold scales must be greater than zero")
    model = {
        **vectors,
        "intercept": finite_number(model_value.get("intercept"), "fold intercept"),
    }
    return {"fold_index": expected_index, "model": model, "training_groups": groups}


def _feature_order(value: Any) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise InputError("feature_order must contain non-empty feature names")
    if len(set(value)) != len(value):
        raise InputError("feature_order names must be unique")
    return tuple(value)


def _sample_vector(value: Any, feature_order: tuple[str, ...]) -> tuple[float, ...]:
    if isinstance(value, list):
        if len(value) != len(feature_order):
            raise InputError("sample feature vector has the wrong size")
        return tuple(finite_number(item, "sample feature") for item in value)
    if isinstance(value, dict):
        if tuple(value.keys()) != feature_order:
            raise InputError("sample feature mapping must use exact feature_order")
        return tuple(finite_number(value[name], "sample feature") for name in feature_order)
    raise InputError("sample features must be an ordered vector or mapping")


def _predict(vector: tuple[float, ...], model: dict[str, Any]) -> float:
    score = model["intercept"]
    for value, mean, scale, coef in zip(
        vector, model["mean"], model["scale"], model["coef"], strict=True
    ):
        score += coef * (value - mean) / scale
        if not math.isfinite(score):
            raise InputError("fold prediction overflowed")
    return min(6.0, max(1.0, score))


def _opaque_id(value: Any, name: str) -> str:
    identifier = bounded_string(value, name)
    # Manifests carry pseudonymous SHA-256 IDs, never names or transcript text.
    require_sha256(identifier, name)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
