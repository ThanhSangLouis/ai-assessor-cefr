#!/usr/bin/env python3
"""Benchmark the same typed trust evidence and policy used by runtime.

Each observation is precomputed output from actual language, guard, and
conformal predictors. The benchmark calls the shared ``TrustPolicy`` directly;
labels are read only after each policy decision has been produced. Reports
contain aggregate counts and hashes, never transcripts or per-example IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from typing import Any

from aicefr.contracts import ReasonCode
from aicefr.trust.contracts import ConformalSet, GuardEvidence, LanguageEvidence
from aicefr.trust.policy import TrustPolicy
from tools._trust_cli import InputError, ensure_distinct_paths, json_bytes, read_json, write_json

_DISPOSITIONS = {"CONTINUE", "REVIEW_REQUIRED", "NOT_EVALUATED", "REJECTED"}


def benchmark(manifest: dict[str, Any], *, manifest_sha256: str) -> dict[str, Any]:
    if manifest.get("version") != "refusal-manifest-v1":
        raise InputError("unsupported refusal manifest version")
    split_role = manifest.get("split_role")
    if split_role not in {"development", "confirmation"}:
        raise InputError("split_role must be development or confirmation")
    seed = manifest.get("seed")
    if type(seed) is not int:
        raise InputError("seed must be an integer")
    policy_version = manifest.get("policy_version")
    if policy_version != TrustPolicy.VERSION:
        raise InputError("manifest must use the current shared TrustPolicy version")
    examples = manifest.get("examples")
    if not isinstance(examples, list) or not examples:
        raise InputError("benchmark examples are required")
    decisions: Counter[str] = Counter()
    expected: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    correct = 0
    labelled = 0
    seen: set[str] = set()
    policy = TrustPolicy()
    for example in examples:
        if not isinstance(example, dict):
            raise InputError("each benchmark example must be an object")
        if any(key.casefold() in {"transcript", "text", "audio", "path"} for key in example):
            raise InputError("benchmark manifests must not include transcripts, audio, or paths")
        sample_id = example.get("sample_id")
        if (
            not isinstance(sample_id, str)
            or len(sample_id) != 64
            or any(char not in "0123456789abcdef" for char in sample_id)
        ):
            raise InputError("sample_id must be a pseudonymous lowercase SHA-256")
        if sample_id in seen:
            raise InputError("sample_id values must be unique")
        seen.add(sample_id)
        observation = example.get("observation")
        if not isinstance(observation, dict):
            raise InputError("typed prediction observations are required")
        if any(key.casefold() in {"transcript", "text", "audio", "path"} for key in observation):
            raise InputError("observations must not include transcripts, audio, or paths")
        language_data = observation.get("language")
        try:
            language = (
                LanguageEvidence.model_validate(language_data)
                if language_data is not None
                else None
            )
            guards_data = observation.get("guards", [])
            if not isinstance(guards_data, list):
                raise InputError("guards must be a list")
            guards = tuple(GuardEvidence.model_validate(item) for item in guards_data)
            conformal_data = observation.get("conformal")
            conformal = (
                ConformalSet.model_validate(conformal_data) if conformal_data is not None else None
            )
        except InputError:
            raise
        except Exception as exc:
            raise InputError("typed observation evidence is invalid") from exc
        calibration_state = observation.get("calibration_state", "ready")
        if calibration_state not in {"ready", "missing", "hash_mismatch", "invalid"}:
            raise InputError("calibration_state is invalid")
        prerequisites = calibration_state == "ready" and conformal is not None
        prerequisite_reason = {
            "missing": ReasonCode.CALIBRATION_MISSING,
            "hash_mismatch": ReasonCode.CALIBRATION_HASH_MISMATCH,
            "invalid": ReasonCode.CALIBRATION_INVALID,
        }.get(calibration_state)
        result = policy.decide(
            language,
            guards,
            conformal,
            prerequisites=prerequisites,
            prerequisite_reason=prerequisite_reason,
        )
        disposition = result.disposition.value
        decisions[disposition] += 1
        reason_counts.update(reason.value for reason in result.reasons)
        # The expected label is accessed only after the policy decision above.
        label = example.get("label")
        if label is not None:
            if (
                not isinstance(label, dict)
                or label.get("expected_disposition") not in _DISPOSITIONS
            ):
                raise InputError("label expected_disposition must use a known disposition")
            labelled += 1
            target = label["expected_disposition"]
            expected[target] += 1
            correct += disposition == target
    config_sha256 = hashlib.sha256(
        json_bytes({"policy_version": policy_version, "split_role": split_role, "seed": seed})
    ).hexdigest()
    return {
        "status": "EVALUATED",
        "method": "shared_trust_policy",
        "policy_version": policy_version,
        "config_sha256": config_sha256,
        "manifest_sha256": manifest_sha256,
        "seed": seed,
        "split_role": split_role,
        "sample_count": len(examples),
        "labelled_count": labelled,
        "decision_counts": dict(sorted(decisions.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "reference_counts": dict(sorted(expected.items())),
        "disposition_agreement": correct / labelled if labelled else None,
        "decision_source": "typed_predictor_evidence_and_shared_TrustPolicy_only",
        "confirmation_used_for_tuning": False,
        "empirical_coverage": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--output", required=True, help="aggregate report path; contains no raw examples"
    )
    args = parser.parse_args(argv)
    try:
        ensure_distinct_paths([args.manifest], [args.output])
        manifest, digest = read_json(args.manifest)
        if not isinstance(manifest, dict):
            raise InputError("manifest root must be an object")
        report = benchmark(manifest, manifest_sha256=digest)
        report["report_sha256"] = write_json(args.output, report)
        print(json.dumps(report, sort_keys=True))
        return 0
    except (InputError, OSError, ValueError, TypeError, KeyError) as exc:
        print(
            json.dumps({"status": "NOT_RUN", "reason": str(exc)}, sort_keys=True), file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
