"""Lesson completion from preserved step passes and distinct spoken FREE rounds."""

from __future__ import annotations

import math
from collections.abc import Sequence

from aicefr.lessons.model import (
    FreePayload,
    LessonProgress,
    LessonStep,
    StepAttemptStatus,
    StepCompletion,
    StepKind,
)

DEFAULT_COMPLETION_FRACTION = 0.8


def lesson_completion(
    *,
    steps: Sequence[LessonStep],
    attempts: Sequence[StepCompletion],
    required_fraction: float = DEFAULT_COMPLETION_FRACTION,
) -> LessonProgress:
    """Count each authored step once and require every FREE round to be complete.

    Only attempts whose step id and kind match this lesson are considered. A
    passing step remains complete after a later failed retry. Each authored FREE
    round counts once when any matching attempt contains positive speech duration,
    regardless of that attempt's rule status.
    """
    if not math.isfinite(required_fraction) or not 0 < required_fraction <= 1:
        raise ValueError("required_fraction must be finite and in (0, 1]")
    step_by_id = {step.step_id: step for step in steps}
    matching: dict[tuple[str, int | None], list[StepCompletion]] = {}
    for attempt in attempts:
        step = step_by_id.get(attempt.step_id)
        if step is None or step.kind is not attempt.kind:
            continue
        key = (attempt.step_id, attempt.round_index)
        matching.setdefault(key, []).append(attempt)

    completed: list[str] = []
    completed_free_rounds = 0
    required_free_rounds = 0
    for step in steps:
        if step.kind is StepKind.FREE:
            payload = step.payload
            assert isinstance(payload, FreePayload)
            required_free_rounds += len(payload.rounds)
            spoken_rounds = sum(
                any(attempt.speaking_s > 0 for attempt in matching.get((step.step_id, index), ()))
                for index in range(len(payload.rounds))
            )
            round_complete = spoken_rounds == len(payload.rounds)
            completed_free_rounds += spoken_rounds
            if round_complete:
                completed.append(step.step_id)
        else:
            step_attempts = matching.get((step.step_id, None), ())
            if any(attempt.status is StepAttemptStatus.COMPLETE for attempt in step_attempts):
                completed.append(step.step_id)

    required_count = len(steps)
    fraction = len(completed) / required_count if required_count else 0.0
    complete = (
        required_count > 0
        and len(completed) >= math.ceil(required_count * required_fraction)
        and completed_free_rounds == required_free_rounds
        and required_free_rounds > 0
    )
    return LessonProgress(
        completed_step_ids=tuple(completed),
        required_step_count=required_count,
        completion_fraction=fraction,
        completed_free_rounds=completed_free_rounds,
        required_free_rounds=required_free_rounds,
        complete=complete,
    )
