"""Runtime composition for M09 evidence and disposition.

Calibration artifacts are loaded once from trusted runtime configuration and
are bound to the active scoring artifact. Failure to load is retained as a
closed state so a normal response can still produce a reviewable report.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aicefr.asr.language import LanguageIdentifier
from aicefr.contracts import Assessment, Band, FeatureSet, ReasonCode, Transcript
from aicefr.features.relevance import ValidityShield
from aicefr.scoring.conformal import (
    CalibrationArtifact,
    CalibrationArtifactError,
    load_calibration_artifact,
    predict_conformal,
)
from aicefr.trust.contracts import CriterionIndicator, TrustAssessment
from aicefr.trust.policy import TrustPolicy


@dataclass(frozen=True)
class TaskTrustContext:
    prompt_text: str
    topic_keywords: tuple[str, ...] = ()


class RuntimeTrustEvaluator:
    """Evaluate independent trust evidence without changing score inputs."""

    def __init__(
        self,
        *,
        scorer: Any,
        config: Mapping[str, Any] | None,
        tasks: Any | None = None,
    ) -> None:
        self._scorer = scorer
        self._config = dict(config or {})
        self._task_provider = tasks
        self._policy = TrustPolicy()
        self._language = LanguageIdentifier()
        self._shield = ValidityShield()
        self._task_resolver = (
            tasks
            if not isinstance(tasks, Mapping) and callable(getattr(tasks, "get", None))
            else None
        )
        task_items = tasks.items() if isinstance(tasks, Mapping) else ()
        self._tasks = {
            key: (
                value
                if hasattr(value, "prompt_text") and hasattr(value, "topic_keywords")
                else TaskTrustContext(
                    prompt_text=str(value.get("prompt_text", ""))
                    if isinstance(value, Mapping)
                    else str(value),
                    topic_keywords=tuple(value.get("topic_keywords", ()))
                    if isinstance(value, Mapping)
                    else (),
                )
            )
            for key, value in task_items
        }
        settings = dict(self._config)
        try:
            raw_alpha = settings.get("alpha", 0.10)
            self.alpha = float(raw_alpha)
            alpha_valid = (
                not isinstance(raw_alpha, bool)
                and math.isfinite(self.alpha)
                and 0.0 < self.alpha < 0.5
            )
        except (TypeError, ValueError, OverflowError):
            self.alpha = 0.10
            alpha_valid = False
        self._calibration: CalibrationArtifact | None = None
        self._calibration_reason: ReasonCode | None = None

        if not alpha_valid:
            self._calibration_reason = ReasonCode.CALIBRATION_INVALID
            return

        path = settings.get("calibration_artifact")
        expected_sha = settings.get("expected_sha256")
        model = getattr(scorer, "artifact", None)
        if not path or not expected_sha:
            self._calibration_reason = ReasonCode.CALIBRATION_MISSING
            return
        if model is None:
            self._calibration_reason = ReasonCode.CALIBRATION_INVALID
            return
        try:
            calibration_path = Path(path)
        except TypeError:
            self._calibration_reason = ReasonCode.CALIBRATION_INVALID
            return
        try:
            self._calibration = load_calibration_artifact(
                calibration_path,
                expected_sha256=str(expected_sha),
                expected_model_sha256=model.sha256,
                expected_feature_order=model.feature_order,
                expected_band_thresholds=model.band_thresholds,
            )
        except CalibrationArtifactError as error:
            # Keep only a stable reason code: loader errors must not leak paths.
            self._calibration_reason = self._loader_reason(error, calibration_path)

    @property
    def ready(self) -> bool:
        return self._calibration is not None

    def rebind(self, scorer: Any) -> RuntimeTrustEvaluator:
        """Recheck the pinned artifact against a newly activated scorer."""
        return type(self)(scorer=scorer, config=self._config, tasks=self._task_provider)

    def assess(
        self,
        *,
        audio: Any,
        transcript: Transcript,
        features: FeatureSet,
        assessment: Assessment,
        task_id: str,
        task_version: str,
        asr: Any,
        conformal_sets: tuple[Any, ...] | None = None,
    ) -> TrustAssessment:
        engine = getattr(asr, "_engine", None)
        if engine is None:
            try:
                engine = asr._load_engine()
            except Exception:
                engine = None
        if transcript.language_method or transcript.language_version:
            language = self._language.evaluate_language(
                transcript.language,
                transcript.language_probability,
                method=transcript.language_method or LanguageIdentifier.METHOD,
                version=transcript.language_version or LanguageIdentifier.VERSION,
            )
        elif engine is not None and callable(getattr(engine, "detect_language", None)):
            language = self._language.evaluate(audio, engine)
        else:
            language = self._language.evaluate_language(None, None)
        task = (
            self._task_resolver.get(task_id, task_version)
            if self._task_resolver is not None
            else self._tasks.get((task_id, task_version))
        )
        guards = self._shield.evaluate(task or TaskTrustContext(prompt_text=""), transcript.words)

        prediction_set = None
        local_calibration_reason = self._calibration_reason
        if conformal_sets is not None:
            prediction_set = self._aggregate_sets(conformal_sets)
            if prediction_set is None and self._calibration is not None:
                local_calibration_reason = ReasonCode.CALIBRATION_INVALID
        elif self._calibration is not None:
            vector = {value.name: value.value for value in features.values}
            try:
                prediction_set = predict_conformal(vector, self._calibration, alpha=self.alpha)
            except CalibrationArtifactError:
                local_calibration_reason = ReasonCode.CALIBRATION_INVALID

        decision = self._policy.decide(
            language,
            guards,
            prediction_set,
            prerequisites=self._calibration is not None and prediction_set is not None,
            prerequisite_reason=local_calibration_reason,
        )
        reasons = decision.reasons
        indicators = tuple(
            CriterionIndicator(name=row.criterion, coverage=row.coverage)
            for row in assessment.criteria
        )
        return TrustAssessment(
            language=language,
            relevance=guards,
            prediction_set=prediction_set,
            criterion_indicators=indicators,
            reasons=reasons,
            disposition=decision.disposition,
        )

    def predict_windows(self, feature_sets: tuple[FeatureSet, ...]):
        """Return one CV+ set per supplied valid window, retaining failures closed."""
        if self._calibration is None:
            return None
        if not feature_sets:
            return ()
        sets = []
        for features in feature_sets:
            vector = {value.name: value.value for value in features.values}
            try:
                sets.append(predict_conformal(vector, self._calibration, alpha=self.alpha))
            except CalibrationArtifactError:
                return ()
        return tuple(sets)

    @staticmethod
    def _loader_reason(error: CalibrationArtifactError, path: Path) -> ReasonCode:
        reason = getattr(error, "reason", None)
        if isinstance(reason, ReasonCode):
            return reason
        value = getattr(reason, "value", reason)
        if value in {"CALIBRATION_MISSING", "missing"} or not path.is_file():
            return ReasonCode.CALIBRATION_MISSING
        if value in {"CALIBRATION_HASH_MISMATCH", "hash_mismatch"}:
            return ReasonCode.CALIBRATION_HASH_MISMATCH
        return ReasonCode.CALIBRATION_INVALID

    @staticmethod
    def _aggregate_sets(sets: tuple[Any, ...]):
        """Conservatively union all valid per-window sets."""
        if not sets:
            return None
        first = sets[0]
        if any(
            item.alpha != first.alpha
            or item.calibration_id != first.calibration_id
            or item.checksum != first.checksum
            for item in sets
        ):
            return None
        from aicefr.trust.contracts import ConformalSet

        selected = {band for item in sets for band in item.bands}
        return ConformalSet(
            alpha=first.alpha,
            bands=tuple(band for band in Band if band in selected),
            calibration_id=first.calibration_id,
            checksum=first.checksum,
            low=min(item.low for item in sets),
            high=max(item.high for item in sets),
        )
