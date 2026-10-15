from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aicefr.contracts import Band, ReasonCode
from aicefr.scoring.conformal import (
    PINNED_REFERENCE_MODEL_SHA256,
    PINNED_REFERENCE_SHA256,
    CalibrationArtifactError,
    _parse_pinned_reference,
    load_calibration_artifact,
    predict_conformal,
)

MODEL_SHA = "a" * 64
ORDER = ("x",)
THRESHOLDS = {"A2_B1": 2.75, "B1_B2": 3.75}


def artifact_payload(*, residuals=None, **overrides):
    rows = residuals or [
        {
            "sample_id": f"{i:064x}",
            "speaker_group": f"{i % 2 + 100:064x}",
            "fold_index": i % 2,
            "residual": 0.1,
        }
        for i in range(10)
    ]
    value = {
        "version": "cvplus-v1",
        "calibration_id": "fixture-cvplus",
        "model_sha256": MODEL_SHA,
        "feature_order": ["x"],
        "band_thresholds": THRESHOLDS,
        "folds": [
            {"fold_index": 0, "mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0},
            {"fold_index": 1, "mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0},
        ],
        "n_residuals": len(rows),
        "residuals": rows,
        "provenance": {
            "manifest_sha256": "b" * 64,
            "model_sha256": MODEL_SHA,
            "config_sha256": "c" * 64,
            "seed": 7,
            "split_role": "calibration",
            "training_recipe_version": "fixture-v1",
            "alpha_default": 0.1,
            "speaker_group_count": len({row["speaker_group"] for row in rows}),
        },
    }
    value.update(overrides)
    return value


def load_payload(tmp_path, value, *, raw=None, **kwargs):
    path = tmp_path / "calibration.json"
    contents = raw if raw is not None else json.dumps(value, allow_nan=False).encode()
    path.write_bytes(contents)
    return load_calibration_artifact(
        path,
        expected_sha256=hashlib.sha256(contents).hexdigest(),
        expected_model_sha256=MODEL_SHA,
        expected_feature_order=ORDER,
        expected_band_thresholds=THRESHOLDS,
        **kwargs,
    )


def test_predict_returns_single_band_from_cvplus_bounds(tmp_path):
    artifact = load_payload(tmp_path, artifact_payload())

    result = predict_conformal({"x": 0.2}, artifact)

    assert result.alpha == 0.1
    assert result.low == pytest.approx(2.9)
    assert result.high == pytest.approx(3.1)
    assert result.bands == (Band.B1,)
    assert result.calibration_id == "fixture-cvplus"
    assert result.checksum == artifact.checksum


def test_finite_sample_ranks_and_boundary_include_adjacent_bands(tmp_path):
    rows = [
        {
            "sample_id": f"{i:064x}",
            "speaker_group": f"{i + 100:064x}",
            "fold_index": i % 2,
            "residual": (i + 1) / 10,
        }
        for i in range(9)
    ]
    artifact = load_payload(tmp_path, artifact_payload(residuals=rows))
    result = predict_conformal([0.0], artifact, alpha=0.1)
    assert result.low == pytest.approx(2.1)  # floor(.1 * (9 + 1)) = rank 1
    assert result.high == pytest.approx(3.9)  # ceil(.9 * (9 + 1)) = rank 9
    assert result.bands == (Band.A2, Band.B1, Band.B2)

    boundary = artifact_payload(
        residuals=[
            {
                "sample_id": f"{i:064x}",
                "speaker_group": f"{i + 300:064x}",
                "fold_index": i % 2,
                "residual": 0.25,
            }
            for i in range(9)
        ]
    )
    boundary["folds"][0]["intercept"] = 3.0
    boundary["folds"][1]["intercept"] = 3.0
    boundary["band_thresholds"] = {"A2_B1": 2.75, "B1_B2": 3.75}
    rows = boundary["residuals"]
    rows = [{**row, "residual": 0.25} for row in rows]
    boundary["residuals"] = rows
    boundary["n_residuals"] = len(rows)
    # A model center of 3.0 and radius .25 gives exact endpoints 2.75 and 3.25.
    boundary_artifact = load_payload(tmp_path, boundary)
    boundary_set = predict_conformal([0.0], boundary_artifact)
    assert boundary_set.low == 2.75
    assert boundary_set.bands == (Band.A2, Band.B1)


@pytest.mark.parametrize(
    ("payload", "raw"),
    [
        (lambda data: data | {"model_sha256": "b" * 64}, None),
        (lambda data: data | {"feature_order": ["wrong"]}, None),
        (lambda data: data | {"n_residuals": 999}, None),
        (lambda data: data | {"residuals": [{**data["residuals"][0], "residual": -0.1}]}, None),
        (
            lambda data: data | {"folds": [data["folds"][0] | {"scale": [0.0]}, data["folds"][1]]},
            None,
        ),
        (lambda data: data, b'{"x":1,"x":2}'),
        (lambda data: data, b'{"x":NaN}'),
    ],
)
def test_loader_fails_closed_for_invalid_artifacts(tmp_path, payload, raw):
    value = payload(artifact_payload())
    with pytest.raises(CalibrationArtifactError):
        load_payload(tmp_path, value, raw=raw)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data | {"version": "unknown"},
        lambda data: data | {"calibration_id": "../private/path"},
        lambda data: data | {"feature_order": ["x", "x"]},
        lambda data: data | {"band_thresholds": {"A2_B1": 4.0, "B1_B2": 3.0}},
        lambda data: data | {"folds": data["folds"][:1]},
        lambda data: data | {"folds": [data["folds"][0], data["folds"][0]]},
        lambda data: data | {"provenance": None},
        lambda data: data | {"provenance": data["provenance"] | {"split_role": "confirmation"}},
        lambda data: data | {"provenance": data["provenance"] | {"speaker_group_count": 99}},
        lambda data: data | {"unexpected": True},
    ],
)
def test_loader_rejects_schema_provenance_and_fold_mutations(tmp_path, mutate):
    with pytest.raises(CalibrationArtifactError):
        load_payload(tmp_path, mutate(artifact_payload()))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: [],
        lambda data: data | {"model_sha256": "invalid"},
        lambda data: data | {"model_sha256": "d" * 64},
        lambda data: data | {"band_thresholds": {"wrong": 3.0}},
        lambda data: data | {"band_thresholds": {"A2_B1": 0.5, "B1_B2": 3.75}},
        lambda data: data | {"folds": [data["folds"][0] | {"extra": True}, data["folds"][1]]},
        lambda data: data | {"folds": [data["folds"][0] | {"fold_index": -1}, data["folds"][1]]},
        lambda data: data | {"residuals": [], "n_residuals": 0},
        lambda data: (
            data | {"residuals": [data["residuals"][0] | {"sample_id": "short"}], "n_residuals": 1}
        ),
        lambda data: (
            data | {"residuals": [data["residuals"][0] | {"fold_index": 9}], "n_residuals": 1}
        ),
        lambda data: data | {"residuals": [data["residuals"][0] | {"extra": 1}], "n_residuals": 1},
        lambda data: data | {"provenance": data["provenance"] | {"model_sha256": "d" * 64}},
        lambda data: data | {"provenance": data["provenance"] | {"config_sha256": "bad"}},
        lambda data: (
            data | {"provenance": data["provenance"] | {"training_recipe_version": "../x"}}
        ),
        lambda data: data | {"provenance": data["provenance"] | {"manifest_sha256": "bad"}},
    ],
)
def test_loader_rejects_tampered_schema_components(tmp_path, mutate):
    with pytest.raises(CalibrationArtifactError):
        load_payload(tmp_path, mutate(artifact_payload()))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: (
            data
            | {
                "residuals": [
                    data["residuals"][0] | {"sample_id": data["residuals"][1]["sample_id"]}
                ]
                + data["residuals"][1:],
                "n_residuals": len(data["residuals"]),
            }
        ),
        lambda data: data | {"folds": [None, data["folds"][1]]},
        lambda data: data | {"residuals": [None], "n_residuals": 1},
        lambda data: (
            data | {"residuals": [data["residuals"][0] | {"residual": -1.0}], "n_residuals": 1}
        ),
        lambda data: data | {"provenance": data["provenance"] | {"provenance_sha256": "bad"}},
        lambda data: (
            data
            | {
                "provenance": {
                    key: value
                    for key, value in data["provenance"].items()
                    if key != "manifest_sha256"
                }
            }
        ),
        lambda data: data | {"provenance": data["provenance"] | {"reference_sha256": "e" * 64}},
        lambda data: data | {"provenance": data["provenance"] | {"seed": True}},
        lambda data: data | {"provenance": data["provenance"] | {"alpha_default": 0.7}},
        lambda data: data | {"provenance": data["provenance"] | {"source_format": "../raw"}},
    ],
)
def test_loader_rejects_duplicate_rows_and_provenance_tampering(tmp_path, mutate):
    with pytest.raises(CalibrationArtifactError):
        load_payload(tmp_path, mutate(artifact_payload()))


def test_loader_rejects_invalid_trusted_values_and_oversized_json(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(CalibrationArtifactError) as error:
        load_calibration_artifact(
            path,
            expected_sha256="bad",
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )
    assert error.value.reason is ReasonCode.CALIBRATION_INVALID
    path.write_bytes(b" " * (2 * 1024 * 1024 + 1))
    with pytest.raises(CalibrationArtifactError, match="too large"):
        load_calibration_artifact(
            path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )


@pytest.mark.parametrize("raw", [b"{invalid", b"\xff"])
def test_loader_rejects_malformed_utf8_or_json(tmp_path, raw):
    with pytest.raises(CalibrationArtifactError) as error:
        load_payload(tmp_path, {}, raw=raw)
    assert error.value.reason is ReasonCode.CALIBRATION_INVALID


def test_loader_fails_closed_on_deeply_nested_json(tmp_path):
    raw = b"[" * 1500 + b"]" * 1500
    path = tmp_path / "deep-calibration.json"
    path.write_bytes(raw)

    with pytest.raises(CalibrationArtifactError) as error:
        load_calibration_artifact(
            path,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )

    assert error.value.reason is ReasonCode.CALIBRATION_INVALID
    assert "deep-calibration.json" not in str(error.value)


def test_loader_exact_hash_dispatches_only_to_pinned_schema_adapter(tmp_path, monkeypatch):
    import aicefr.scoring.conformal as conformal

    raw = json.dumps(_legacy_payload(), separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    path = tmp_path / "legacy.json"
    path.write_bytes(raw)
    monkeypatch.setattr(conformal, "PINNED_REFERENCE_SHA256", digest)
    monkeypatch.setattr(conformal, "PINNED_REFERENCE_MODEL_SHA256", PINNED_REFERENCE_MODEL_SHA256)
    loaded = load_calibration_artifact(
        path,
        expected_sha256=digest,
        expected_model_sha256=PINNED_REFERENCE_MODEL_SHA256,
        expected_feature_order=("x",),
        expected_band_thresholds=THRESHOLDS,
    )
    assert loaded.fold_of == (1, 0)


def test_loader_maps_io_error_to_missing_reason(tmp_path, monkeypatch):
    path = tmp_path / "read-error.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(OSError("private")))
    with pytest.raises(CalibrationArtifactError) as error:
        load_calibration_artifact(
            path,
            expected_sha256="0" * 64,
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )
    assert error.value.reason is ReasonCode.CALIBRATION_MISSING
    assert "private" not in str(error.value)


def test_loader_binds_trusted_hash_scorer_and_thresholds(tmp_path):
    value = artifact_payload()
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(CalibrationArtifactError, match="checksum mismatch") as hash_error:
        load_calibration_artifact(
            path,
            expected_sha256="0" * 64,
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )
    assert hash_error.value.reason is ReasonCode.CALIBRATION_HASH_MISMATCH
    with pytest.raises(CalibrationArtifactError, match="loaded scorer"):
        load_calibration_artifact(
            path,
            expected_sha256=digest,
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds={"A2_B1": 2.5, "B1_B2": 3.5},
        )


def test_missing_artifact_has_stable_reason_without_path_leak(tmp_path):
    path = tmp_path / "secret-private-path" / "missing.json"
    with pytest.raises(CalibrationArtifactError) as error:
        load_calibration_artifact(
            path,
            expected_sha256="0" * 64,
            expected_model_sha256=MODEL_SHA,
            expected_feature_order=ORDER,
            expected_band_thresholds=THRESHOLDS,
        )
    assert error.value.reason is ReasonCode.CALIBRATION_MISSING
    assert "secret-private-path" not in str(error.value)


@pytest.mark.parametrize(
    "features", [{}, {"x": 0.0, "extra": 1.0}, {"x": float("nan")}, [float("inf")]]
)
def test_predict_rejects_missing_misordered_or_nonfinite_features(tmp_path, features):
    artifact = load_payload(tmp_path, artifact_payload())
    with pytest.raises(CalibrationArtifactError):
        predict_conformal(features, artifact)


@pytest.mark.parametrize("features", [[], "not-a-vector"])
def test_predict_rejects_wrong_vector_shape_or_type(tmp_path, features):
    artifact = load_payload(tmp_path, artifact_payload())
    with pytest.raises(CalibrationArtifactError):
        predict_conformal(features, artifact)


def test_predict_rejects_invalid_alpha_and_overflow(tmp_path):
    artifact = load_payload(tmp_path, artifact_payload())
    with pytest.raises(CalibrationArtifactError, match="alpha"):
        predict_conformal([0.0], artifact, alpha=0.75)
    overflow = artifact_payload()
    overflow["folds"][0]["coef"] = [1e308]
    overflow["folds"][0]["mean"] = [-1e308]
    artifact = load_payload(tmp_path, overflow)
    with pytest.raises(CalibrationArtifactError, match="overflow"):
        predict_conformal([1e308], artifact)


def test_small_sample_finite_ranks_return_full_safe_score_range(tmp_path):
    rows = [
        {
            "sample_id": f"{i:064x}",
            "speaker_group": f"{i + 900:064x}",
            "fold_index": i,
            "residual": 0.1,
        }
        for i in range(2)
    ]
    artifact = load_payload(tmp_path, artifact_payload(residuals=rows))
    result = predict_conformal([0.0], artifact, alpha=0.1)
    assert result.low == 1.0
    assert result.high == 6.0
    assert result.bands == (Band.A2, Band.B1, Band.B2)


def test_loader_rejects_speaker_groups_assigned_to_multiple_folds(tmp_path):
    rows = artifact_payload()["residuals"]
    rows[0]["speaker_group"] = rows[1]["speaker_group"]
    with pytest.raises(CalibrationArtifactError, match="speaker group"):
        load_payload(tmp_path, artifact_payload(residuals=rows))


def test_pinned_legacy_adapter_preserves_fold_index_and_leaves_group_unknown():
    legacy = _legacy_payload()
    adapted = _parse_pinned_reference(
        legacy,
        digest=PINNED_REFERENCE_SHA256,
        expected_model_sha256=PINNED_REFERENCE_MODEL_SHA256,
        expected_feature_order=("x",),
        expected_band_thresholds=THRESHOLDS,
    )
    assert adapted.version == "cvplus_resp_v2_fixture"
    assert adapted.method == "cv+"
    assert adapted.fold_of == (1, 0)
    assert tuple(row.residual for row in adapted.residuals) == (0.2, 0.3)
    assert all(row.sample_id is None and row.speaker_group is None for row in adapted.residuals)


def _legacy_payload():
    return {
        "conformal_version": "cvplus_resp_v2_fixture",
        "method": "cv+",
        "model_sha256": PINNED_REFERENCE_MODEL_SHA256,
        "feature_order": ["x"],
        "n": 2,
        "n_folds": 2,
        "alpha_default": 0.1,
        "folds": [
            {"mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0},
            {"mean": [1.0], "scale": [2.0], "coef": [1.0], "intercept": 3.0},
        ],
        "fold_of": [1, 0],
        "residuals": [0.2, 0.3],
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data | {"method": "split"},
        lambda data: data | {"conformal_version": "../path"},
        lambda data: data | {"model_sha256": "d" * 64},
        lambda data: data | {"feature_order": ["wrong"]},
        lambda data: data | {"n_folds": 9},
        lambda data: data | {"n": 3},
        lambda data: data | {"fold_of": [2, 0]},
        lambda data: data | {"residuals": [-0.1, 0.3]},
        lambda data: data | {"alpha_default": 0.8},
    ],
)
def test_pinned_legacy_adapter_rejects_invalid_reference_metadata(mutate):
    with pytest.raises(CalibrationArtifactError):
        _parse_pinned_reference(
            mutate(_legacy_payload()),
            digest=PINNED_REFERENCE_SHA256,
            expected_model_sha256=PINNED_REFERENCE_MODEL_SHA256,
            expected_feature_order=("x",),
            expected_band_thresholds=THRESHOLDS,
        )
