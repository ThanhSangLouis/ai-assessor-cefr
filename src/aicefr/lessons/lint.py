"""Draft and publish-time validation for immutable lesson content."""

from __future__ import annotations

from aicefr.lessons.model import (
    STAGE_ORDER,
    FreePayload,
    Lesson,
    LessonLintIssue,
    LessonStage,
    LessonValidation,
)
from aicefr.lessons.rules import SUPPORTED_LESSON_RULES_VERSIONS


def lint_lesson(lesson: Lesson, *, for_publish: bool = False) -> LessonValidation:
    issues: list[LessonLintIssue] = []
    if not lesson.steps:
        issues.append(LessonLintIssue(code="NO_STEPS", message="Bài học cần ít nhất một bước."))
    seen_stage_indices: list[int] = []
    for step in lesson.steps:
        seen_stage_indices.append(STAGE_ORDER.index(step.stage))
        if isinstance(step.payload, FreePayload):
            durations = [round_.duration_seconds for round_ in step.payload.rounds]
            if len(durations) not in (2, 3) or any(
                later >= earlier for earlier, later in zip(durations, durations[1:], strict=False)
            ):
                issues.append(
                    LessonLintIssue(
                        code="FREE_ROUND_BUDGET",
                        step_id=step.step_id,
                        message="Bước Tự do cần hai hoặc ba lượt với thời lượng giảm dần.",
                    )
                )
    if for_publish:
        present = {step.stage for step in lesson.steps}
        missing = [stage.value for stage in STAGE_ORDER if stage not in present]
        if missing:
            issues.append(
                LessonLintIssue(code="MISSING_STAGE", message=f"Thiếu stage: {', '.join(missing)}.")
            )
        if any(
            later < earlier
            for earlier, later in zip(seen_stage_indices, seen_stage_indices[1:], strict=False)
        ):
            issues.append(
                LessonLintIssue(
                    code="STAGE_ORDER", message="Bốn stage phải theo đúng thứ tự Mẫu → Tự do."
                )
            )
        if not any(step.stage is LessonStage.FREE for step in lesson.steps):
            issues.append(
                LessonLintIssue(code="NO_FREE_STEP", message="Bài publish phải có bước Tự do.")
            )
        for step in lesson.steps:
            if step.rules_version not in SUPPORTED_LESSON_RULES_VERSIONS:
                issues.append(
                    LessonLintIssue(
                        code="RULES_VERSION_UNSUPPORTED",
                        step_id=step.step_id,
                        message=f"Phiên bản luật {step.rules_version!r} chưa được hỗ trợ.",
                    )
                )
    return LessonValidation(valid=not issues, errors=tuple(issues))
