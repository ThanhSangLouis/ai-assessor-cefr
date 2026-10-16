from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tools._trust_cli import (
    MAX_INPUT_BYTES,
    InputError,
    ensure_distinct_paths,
    json_bytes,
    read_json,
    sha256_file,
    write_json,
)
from tools.calibrate_conformal import assemble
from tools.calibrate_conformal import main as calibrate_main
from tools.refusal_benchmark import benchmark
from tools.refusal_benchmark import main as refusal_main

from aicefr.trust.policy import TrustPolicy


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _model():
    return {
        "feature_order": ["f"],
        "band_thresholds": {"A2_B1": 2.75, "B1_B2": 3.75},
    }


def _calibration_manifest():
    group_a, group_b = _sha("speaker-a"), _sha("speaker-b")
    return {
        "version": "cvplus-manifest-v1",
        "split_role": "calibration",
        "seed": 47,
        "model_sha256": _sha("model"),
        "feature_order": ["f"],
        "training_recipe": {"version": "ridge-recipe-v1", "name": "synthetic fixture"},
        "folds": [
            {
                "fold_index": 0,
                "training_groups": [group_b],
                "model": {"mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0},
            },
            {
                "fold_index": 1,
                "training_groups": [group_a],
                "model": {"mean": [0.0], "scale": [1.0], "coef": [0.0], "intercept": 3.0},
            },
        ],
        "samples": [
            {
                "sample_id": _sha("sample-0"),
                "speaker_group": group_a,
                "fold_index": 0,
                "role": "calibration",
                "features": [0.5],
                "reference_score": 3.2,
            },
            {
                "sample_id": _sha("sample-1"),
                "speaker_group": group_b,
                "fold_index": 1,
                "role": "calibration",
                "features": [0.2],
                "reference_score": 2.8,
            },
        ],
    }


def test_calibration_assembly_is_deterministic_and_marks_no_coverage_claim():
    manifest = _calibration_manifest()
    kwargs = {
        "manifest_sha256": _sha("manifest"),
        "model": _model(),
        "model_sha256": _sha("model"),
        "alpha": 0.1,
    }
    first_artifact, first_report = assemble(manifest, **kwargs)
    second_artifact, second_report = assemble(manifest, **kwargs)
    assert json_bytes(first_artifact) == json_bytes(second_artifact)
    assert first_report == second_report
    assert first_artifact["n_residuals"] == 2
    assert all(row["residual"] >= 0 for row in first_artifact["residuals"])
    assert first_report["empirical_coverage"] == "NOT_EVALUATED"


def test_calibration_accepts_ordered_feature_mapping():
    manifest = _calibration_manifest()
    manifest["samples"][0]["features"] = {"f": 0.5}
    artifact, _ = assemble(
        manifest,
        manifest_sha256=_sha("manifest"),
        model=_model(),
        model_sha256=_sha("model"),
        alpha=0.1,
    )
    assert artifact["n_residuals"] == 2


def test_calibration_requires_at_least_two_speaker_groups():
    manifest = _calibration_manifest()
    shared = manifest["samples"][0]["speaker_group"]
    manifest["samples"][1]["speaker_group"] = shared
    manifest["samples"][1]["fold_index"] = 0
    with pytest.raises(InputError, match="at least two distinct"):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


def test_calibration_rejects_invalid_scorer_thresholds():
    with pytest.raises(InputError, match="thresholds"):
        assemble(
            _calibration_manifest(),
            manifest_sha256=_sha("manifest"),
            model=_model() | {"band_thresholds": {"A2_B1": 5.0, "B1_B2": 4.0}},
            model_sha256=_sha("model"),
            alpha=0.1,
        )


@pytest.mark.parametrize(
    "change",
    [
        {"split_role": "confirmation"},
        {"split_role": "development"},
    ],
)
def test_calibration_refuses_non_calibration_splits(change):
    manifest = _calibration_manifest() | change
    with pytest.raises(InputError, match="split_role"):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


def test_calibration_rejects_speaker_fold_leakage():
    manifest = _calibration_manifest()
    manifest["samples"][0]["speaker_group"] = manifest["samples"][1]["speaker_group"]
    with pytest.raises(InputError, match="training groups"):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


def test_calibration_rejects_training_group_overlap_and_sample_confirmation():
    manifest = _calibration_manifest()
    manifest["folds"][0]["training_groups"].append(manifest["samples"][0]["speaker_group"])
    with pytest.raises(InputError, match="training"):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data | {"version": "unknown"},
        lambda data: data | {"split_role": "confirmation"},
        lambda data: data | {"model_sha256": _sha("wrong model")},
        lambda data: data | {"seed": True},
        lambda data: data | {"training_recipe": {}},
        lambda data: data | {"feature_order": ["different"]},
        lambda data: data | {"samples": None},
        lambda data: data | {"samples": []},
        lambda data: (
            data
            | {
                "samples": [
                    data["samples"][0] | {"speaker_group": data["samples"][1]["speaker_group"]},
                    data["samples"][1] | {"speaker_group": data["samples"][1]["speaker_group"]},
                ],
                "folds": [
                    data["folds"][0] | {"training_groups": [_sha("train-0")]},
                    data["folds"][1] | {"training_groups": [_sha("train-1")]},
                ],
            }
        ),
        lambda data: (
            data
            | {
                "samples": [
                    data["samples"][0] | {"speaker_group": _sha("train-overlap")},
                    data["samples"][1],
                ],
                "folds": [
                    data["folds"][0] | {"training_groups": [_sha("train-overlap")]},
                    data["folds"][1],
                ],
            }
        ),
        lambda data: (
            data
            | {
                "folds": [
                    data["folds"][0]
                    | {
                        "model": data["folds"][0]["model"]
                        | {"intercept": 1e308, "coef": [1e308], "mean": [-1e308]}
                    },
                    data["folds"][1],
                ],
                "samples": [data["samples"][0] | {"features": [1e308]}, data["samples"][1]],
            }
        ),
        lambda data: (
            data
            | {
                "samples": [
                    data["samples"][0],
                    data["samples"][0]
                    | {
                        "sample_id": _sha("second"),
                        "speaker_group": data["samples"][0]["speaker_group"],
                    },
                ]
            }
        ),
        lambda data: data | {"folds": data["folds"][:1]},
        lambda data: (
            data | {"folds": [data["folds"][0] | {"training_groups": []}, data["folds"][1]]}
        ),
        lambda data: (
            data
            | {
                "folds": [
                    data["folds"][0] | {"model": data["folds"][0]["model"] | {"scale": [0.0]}},
                    data["folds"][1],
                ]
            }
        ),
        lambda data: data | {"samples": data["samples"] + [data["samples"][0]]},
        lambda data: (
            data | {"samples": [data["samples"][0] | {"features": [0.1, 0.2]}, data["samples"][1]]}
        ),
        lambda data: (
            data | {"samples": [data["samples"][0] | {"reference_score": 8.0}, data["samples"][1]]}
        ),
        lambda data: (
            data | {"samples": [data["samples"][0] | {"fold_index": 9}, data["samples"][1]]}
        ),
        lambda data: (
            data
            | {"samples": [data["samples"][0] | {"sample_id": "not-a-hash"}, data["samples"][1]]}
        ),
        lambda data: (
            data | {"samples": [data["samples"][0] | {"features": "invalid"}, data["samples"][1]]}
        ),
        lambda data: (
            data
            | {"samples": [data["samples"][0] | {"features": {"wrong": 1.0}}, data["samples"][1]]}
        ),
        lambda data: data | {"folds": [data["folds"][0] | {"fold_index": True}, data["folds"][1]]},
        lambda data: (
            data
            | {
                "folds": [
                    data["folds"][0]
                    | {"training_groups": [data["folds"][0]["training_groups"][0]] * 2},
                    data["folds"][1],
                ]
            }
        ),
        lambda data: data | {"folds": [data["folds"][0] | {"model": None}, data["folds"][1]]},
        lambda data: (
            data
            | {
                "folds": [
                    data["folds"][0] | {"model": data["folds"][0]["model"] | {"mean": []}},
                    data["folds"][1],
                ]
            }
        ),
        lambda data: (
            data
            | {
                "folds": [
                    data["folds"][0]
                    | {"model": data["folds"][0]["model"] | {"intercept": float("nan")}},
                    data["folds"][1],
                ]
            }
        ),
    ],
)
def test_calibration_rejects_invalid_model_split_or_sample_input(mutate):
    manifest = mutate(_calibration_manifest())
    with pytest.raises(InputError):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


@pytest.mark.parametrize("alpha", [0.0, 0.5, float("nan")])
def test_calibration_rejects_invalid_alpha(alpha):
    with pytest.raises(InputError, match="alpha"):
        assemble(
            _calibration_manifest(),
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=alpha,
        )


def test_calibration_cli_returns_not_run_for_bad_alpha_and_non_object_manifest(tmp_path, capsys):
    manifest_path = tmp_path / "manifest.json"
    model_path = tmp_path / "model.json"
    manifest_path.write_bytes(json_bytes(_calibration_manifest()))
    model_path.write_bytes(json_bytes(_model()))
    output_path = tmp_path / "artifact.json"
    assert (
        calibrate_main(
            [
                "--manifest",
                str(manifest_path),
                "--model-artifact",
                str(model_path),
                "--output",
                str(output_path),
                "--alpha",
                "0.0",
            ]
        )
        == 2
    )
    capsys.readouterr()
    manifest_path.write_bytes(json_bytes([]))
    assert (
        calibrate_main(
            [
                "--manifest",
                str(manifest_path),
                "--model-artifact",
                str(model_path),
                "--output",
                str(output_path),
            ]
        )
        == 2
    )
    capsys.readouterr()

    manifest = _calibration_manifest()
    manifest["samples"][0]["role"] = "confirmation"
    with pytest.raises(InputError, match="role=calibration"):
        assemble(
            manifest,
            manifest_sha256=_sha("manifest"),
            model=_model(),
            model_sha256=_sha("model"),
            alpha=0.1,
        )


def test_calibration_cli_repeats_artifact_and_report_hashes(tmp_path, capsys):
    model_path = tmp_path / "model.json"
    model_bytes = json_bytes(_model())
    model_path.write_bytes(model_bytes)
    manifest = _calibration_manifest() | {"model_sha256": hashlib.sha256(model_bytes).hexdigest()}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(json_bytes(manifest))
    outputs = []
    reports = []
    for index in range(2):
        output, report = tmp_path / f"artifact-{index}.json", tmp_path / f"report-{index}.json"
        assert (
            calibrate_main(
                [
                    "--manifest",
                    str(manifest_path),
                    "--model-artifact",
                    str(model_path),
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                ]
            )
            == 0
        )
        outputs.append(output.read_bytes())
        reports.append(json.loads(report.read_text(encoding="utf-8")))
        capsys.readouterr()
    assert outputs[0] == outputs[1]
    assert reports[0] == reports[1]
    assert reports[0]["empirical_coverage"] == "NOT_EVALUATED"


def test_refusal_cli_repeats_aggregate_hash(tmp_path, capsys):
    manifest_path = tmp_path / "refusal.json"
    manifest_path.write_bytes(json_bytes(_refusal_manifest()))
    outputs = []
    for index in range(2):
        output = tmp_path / f"refusal-report-{index}.json"
        assert refusal_main(["--manifest", str(manifest_path), "--output", str(output)]) == 0
        outputs.append(output.read_bytes())
        capsys.readouterr()
    assert outputs[0] == outputs[1]


def test_calibration_cli_refuses_to_overwrite_its_manifest(tmp_path, capsys):
    model_path = tmp_path / "model.json"
    model_bytes = json_bytes(_model())
    model_path.write_bytes(model_bytes)
    manifest = _calibration_manifest() | {"model_sha256": hashlib.sha256(model_bytes).hexdigest()}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(json_bytes(manifest))
    before = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert (
        calibrate_main(
            [
                "--manifest",
                str(manifest_path),
                "--model-artifact",
                str(model_path),
                "--output",
                str(manifest_path),
            ]
        )
        == 2
    )
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == before
    capsys.readouterr()


def test_refusal_cli_refuses_to_overwrite_its_manifest(tmp_path, capsys):
    manifest_path = tmp_path / "refusal.json"
    manifest_path.write_bytes(json_bytes(_refusal_manifest()))
    before = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert refusal_main(["--manifest", str(manifest_path), "--output", str(manifest_path)]) == 2
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == before
    capsys.readouterr()


def test_tool_output_cannot_write_private_artifact_inside_repository():
    repository = Path(__file__).resolve().parents[2]
    with pytest.raises(InputError, match="outside the repository"):
        write_json(repository / "must-not-be-created.json", {"fixture": True})


def test_shared_cli_helpers_reject_bad_json_and_oversized_inputs(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(InputError, match="duplicate"):
        read_json(path)
    path.write_text('{"a":NaN}', encoding="utf-8")
    with pytest.raises(InputError, match="non-finite"):
        read_json(path)
    path.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
    with pytest.raises(InputError, match="size limit"):
        read_json(path)


def test_shared_cli_helper_rejects_deeply_nested_json_without_parser_leak(tmp_path):
    path = tmp_path / "deep.json"
    path.write_bytes(b"[" * 1500 + b"]" * 1500)
    with pytest.raises(InputError, match="nesting exceeds the depth limit") as error:
        read_json(path)
    assert "RecursionError" not in str(error.value)
    assert str(path) not in str(error.value)


def test_clis_fail_closed_on_deep_json_without_traceback_or_mutation(tmp_path, capsys):
    manifest = tmp_path / "deep.json"
    manifest.write_bytes(b"[" * 1500 + b"]" * 1500)
    model = tmp_path / "model.json"
    model.write_bytes(json_bytes(_model()))
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"existing artifact\n")
    report = tmp_path / "report.json"
    report.write_bytes(b"existing report\n")
    input_hashes = {
        manifest: hashlib.sha256(manifest.read_bytes()).hexdigest(),
        model: hashlib.sha256(model.read_bytes()).hexdigest(),
    }
    output_bytes = {artifact: artifact.read_bytes(), report: report.read_bytes()}

    assert (
        calibrate_main(
            [
                "--manifest",
                str(manifest),
                "--model-artifact",
                str(model),
                "--output",
                str(artifact),
                "--report",
                str(report),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "NOT_RUN" in captured.err
    assert "Traceback" not in captured.err and "RecursionError" not in captured.err
    assert str(tmp_path) not in captured.err

    assert refusal_main(["--manifest", str(manifest), "--output", str(report)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "NOT_RUN" in captured.err
    assert "Traceback" not in captured.err and "RecursionError" not in captured.err
    assert str(tmp_path) not in captured.err

    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in input_hashes
    } == input_hashes
    assert {path: path.read_bytes() for path in output_bytes} == output_bytes


def test_shared_cli_helpers_hash_existing_files_and_guard_collisions(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    assert sha256_file(source) == hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(InputError, match="missing"):
        sha256_file(tmp_path / "missing.json")
    with pytest.raises(InputError, match="overwrite"):
        ensure_distinct_paths([source], [source])
    with pytest.raises(InputError, match="distinct"):
        ensure_distinct_paths([], [source, source])


def test_shared_cli_helpers_validate_finite_and_bounded_inputs(tmp_path):
    from tools._trust_cli import bounded_string, finite_number, require_sha256

    assert finite_number(1, "value") == 1.0
    assert bounded_string("safe", "id") == "safe"
    assert require_sha256(_sha("id"), "id") == _sha("id")
    for value in (True, "1"):
        with pytest.raises(InputError, match="numeric"):
            finite_number(value, "value")
    with pytest.raises(InputError, match="finite"):
        finite_number(float("inf"), "value")
    with pytest.raises(InputError, match="bounded"):
        bounded_string("  ", "id")
    with pytest.raises(InputError, match="SHA-256"):
        require_sha256("bad", "id")


def test_shared_cli_helpers_handle_read_races_and_atomic_write_failures(tmp_path, monkeypatch):
    from tools import _trust_cli

    source = tmp_path / "racy.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"x" * (MAX_INPUT_BYTES + 1))
    with pytest.raises(InputError, match="exceeds the size limit"):
        read_json(source)
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(OSError()))
    with pytest.raises(InputError, match="unavailable"):
        read_json(source)
    with pytest.raises(InputError, match="unavailable"):
        sha256_file(source)

    monkeypatch.undo()
    target = tmp_path / "atomic.json"
    monkeypatch.setattr(_trust_cli.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError()))
    with pytest.raises(InputError, match="cannot be written"):
        write_json(target, {"safe": True})
    assert list(tmp_path.glob(".atomic.json.*.tmp")) == []


def test_shared_cli_atomic_writer_returns_exact_payload_hash(tmp_path):
    target = tmp_path / "nested" / "report.json"
    digest = write_json(target, {"status": "OK", "count": 2})
    assert digest == hashlib.sha256(target.read_bytes()).hexdigest()
    assert json.loads(target.read_text(encoding="utf-8")) == {"count": 2, "status": "OK"}


def _refusal_manifest():
    return {
        "version": "refusal-manifest-v1",
        "split_role": "confirmation",
        "seed": 9,
        "policy_version": TrustPolicy.VERSION,
        "examples": [
            {
                "sample_id": _sha("a"),
                "observation": {
                    "language": {
                        "method": "fixture-lid",
                        "version": "1",
                        "language": "en",
                        "confidence": 0.95,
                        "decision": "ENGLISH",
                    },
                    "conformal": {
                        "alpha": 0.1,
                        "bands": ["B1"],
                        "calibration_id": "fixture",
                        "checksum": _sha("calibration"),
                        "low": 3.0,
                        "high": 3.2,
                    },
                },
                "label": {"expected_disposition": "CONTINUE"},
            },
            {
                "sample_id": _sha("b"),
                "observation": {
                    "language": {
                        "method": "fixture-lid",
                        "version": "1",
                        "language": "vi",
                        "confidence": 0.99,
                        "decision": "NON_ENGLISH",
                    },
                    "conformal": {
                        "alpha": 0.1,
                        "bands": ["B1"],
                        "calibration_id": "fixture",
                        "checksum": _sha("calibration"),
                        "low": 3.0,
                        "high": 3.2,
                    },
                },
                "label": {"expected_disposition": "REJECTED"},
            },
        ],
    }


def test_refusal_benchmark_decisions_are_from_observations_and_frozen_policy():
    result = benchmark(_refusal_manifest(), manifest_sha256=_sha("manifest"))
    assert result["decision_source"] == "typed_predictor_evidence_and_shared_TrustPolicy_only"
    assert result["confirmation_used_for_tuning"] is False
    assert result["decision_counts"] == {"CONTINUE": 1, "REJECTED": 1}
    assert result["disposition_agreement"] == 1.0
    assert result["empirical_coverage"] == "NOT_EVALUATED"


def test_refusal_benchmark_does_not_accept_transcript_or_text_fields():
    manifest = _refusal_manifest()
    manifest["examples"][0]["transcript"] = "secret text"
    with pytest.raises(InputError, match="transcripts"):
        benchmark(manifest, manifest_sha256=_sha("manifest"))


def test_refusal_benchmark_cannot_use_confirmation_labels_as_decisions():
    manifest = _refusal_manifest()
    manifest["examples"][0]["label"]["expected_disposition"] = "REJECTED"
    result = benchmark(manifest, manifest_sha256=_sha("manifest"))
    assert result["decision_counts"] == {"CONTINUE": 1, "REJECTED": 1}
    assert result["disposition_agreement"] == 0.5


def test_refusal_benchmark_reuses_shared_policy_boundary_and_missing_calibration():
    manifest = _refusal_manifest()
    manifest["examples"][0]["observation"]["language"]["confidence"] = 0.8
    manifest["examples"][0]["observation"]["language"]["decision"] = "UNCERTAIN"
    manifest["examples"][1]["observation"]["calibration_state"] = "missing"
    manifest["examples"][1]["observation"]["language"]["language"] = "en"
    manifest["examples"][1]["observation"]["language"]["decision"] = "ENGLISH"
    manifest["examples"][1]["observation"]["conformal"] = None
    result = benchmark(manifest, manifest_sha256=_sha("manifest"))
    assert result["decision_counts"] == {"NOT_EVALUATED": 1, "REVIEW_REQUIRED": 1}
    assert result["reason_counts"] == {"CALIBRATION_MISSING": 1, "LANGUAGE_UNCERTAIN": 1}


def test_refusal_benchmark_uses_typed_guards_and_conformal_boundary():
    manifest = _refusal_manifest()
    manifest["examples"][0]["observation"]["guards"] = [
        {
            "kind": "off_topic",
            "value": 0.0,
            "threshold_version": "guard-v1",
            "decision": "suspected",
            "spans": [],
        }
    ]
    manifest["examples"][0]["observation"]["conformal"]["bands"] = ["A2", "B1"]
    result = benchmark(manifest, manifest_sha256=_sha("manifest"))
    assert result["decision_counts"] == {"REJECTED": 1, "REVIEW_REQUIRED": 1}
    assert result["reason_counts"] == {
        "LANGUAGE_NOT_ENGLISH": 1,
        "OFF_TOPIC_SUSPECTED": 1,
        "SCORE_NEAR_BOUNDARY": 1,
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data | {"version": "unknown"},
        lambda data: data | {"split_role": "calibration"},
        lambda data: data | {"policy_version": "unrecognized"},
        lambda data: data | {"seed": True},
        lambda data: data | {"examples": []},
        lambda data: data | {"examples": [data["examples"][0] | {"sample_id": "unsafe"}]},
        lambda data: (
            data
            | {
                "examples": [
                    data["examples"][0] | {"observation": {"language": {"decision": "NOPE"}}}
                ]
            }
        ),
        lambda data: (
            data
            | {"examples": [data["examples"][0] | {"label": {"expected_disposition": "UNKNOWN"}}]}
        ),
        lambda data: data | {"examples": [None]},
        lambda data: data | {"examples": [data["examples"][0], data["examples"][0]]},
        lambda data: data | {"examples": [data["examples"][0] | {"observation": None}]},
        lambda data: (
            data | {"examples": [data["examples"][0] | {"observation": {"text": "private"}}]}
        ),
        lambda data: (
            data
            | {
                "examples": [
                    data["examples"][0]
                    | {"observation": {**data["examples"][0]["observation"], "guards": "invalid"}}
                ]
            }
        ),
        lambda data: (
            data
            | {
                "examples": [
                    data["examples"][0]
                    | {
                        "observation": {
                            **data["examples"][0]["observation"],
                            "calibration_state": "unknown",
                        }
                    }
                ]
            }
        ),
    ],
)
def test_refusal_benchmark_rejects_invalid_manifest_or_evidence(mutate):
    with pytest.raises(InputError):
        benchmark(mutate(_refusal_manifest()), manifest_sha256=_sha("manifest"))


def test_refusal_benchmark_allows_unlabelled_evidence_with_null_agreement():
    manifest = _refusal_manifest()
    manifest["examples"][0].pop("label")
    manifest["examples"][1].pop("label")
    result = benchmark(manifest, manifest_sha256=_sha("manifest"))
    assert result["labelled_count"] == 0
    assert result["disposition_agreement"] is None
