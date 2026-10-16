"""Deterministic generation of typed, editable sample lesson steps."""

from __future__ import annotations

from aicefr.contracts import Band
from aicefr.lessons.model import (
    FreePayload,
    FreeRound,
    GapPayload,
    KeywordsPayload,
    Lesson,
    LessonStage,
    LessonStep,
    ReadAloudPayload,
    RepeatPayload,
    StarterPayload,
    StepKind,
)
from aicefr.lessons.rules import LESSON_RULES_VERSION

RULES_VERSION = LESSON_RULES_VERSION


def build_lesson(
    *,
    lesson_id: str,
    title: str,
    summary: str,
    band: Band,
    model_text: str,
    free_prompt: str,
    keywords: tuple[str, ...],
    content_version: str = "sample-v1",
) -> Lesson:
    """Build a repeatable four-stage lesson with stable step ids."""
    if len(keywords) < 3:
        raise ValueError("lesson generation needs at least three keywords")
    steps = (
        LessonStep(
            step_id=f"{lesson_id}-s1",
            ordinal=1,
            stage=LessonStage.MODEL,
            kind=StepKind.READ_ALOUD,
            instruction="Đọc đoạn mẫu thành tiếng; từ gợi ý giúp bạn giữ đúng nhịp.",
            payload=ReadAloudPayload(
                kind=StepKind.READ_ALOUD,
                text=model_text,
                hint_words=keywords[:3],
                max_seconds=45,
            ),
            rules_version=RULES_VERSION,
        ),
        LessonStep(
            step_id=f"{lesson_id}-s2",
            ordinal=2,
            stage=LessonStage.MODEL,
            kind=StepKind.REPEAT,
            instruction="Nghe mẫu và nhắc lại bằng lời của bạn.",
            payload=RepeatPayload(kind=StepKind.REPEAT, text=model_text, max_seconds=45),
            rules_version=RULES_VERSION,
        ),
        LessonStep(
            step_id=f"{lesson_id}-s3",
            ordinal=3,
            stage=LessonStage.CONTROLLED,
            kind=StepKind.GAP,
            instruction="Hoàn thành câu mẫu rồi đọc lại cả câu.",
            payload=GapPayload(
                kind=StepKind.GAP,
                text=f"{keywords[0]} ___ {keywords[1]}.",
                answers=(keywords[2],),
                hint_words=keywords[:3],
                max_seconds=35,
            ),
            rules_version=RULES_VERSION,
        ),
        LessonStep(
            step_id=f"{lesson_id}-s4",
            ordinal=4,
            stage=LessonStage.GUIDED,
            kind=StepKind.KEYWORDS,
            instruction="Dùng các từ khóa để phát triển câu trả lời.",
            payload=KeywordsPayload(
                kind=StepKind.KEYWORDS,
                keywords=keywords[:3],
                min_words=8 if band is Band.A2 else 14,
                max_seconds=60,
            ),
            rules_version=RULES_VERSION,
        ),
        LessonStep(
            step_id=f"{lesson_id}-s5",
            ordinal=5,
            stage=LessonStage.GUIDED,
            kind=StepKind.STARTER,
            instruction="Bắt đầu bằng câu gợi ý, sau đó thêm lý do hoặc ví dụ.",
            payload=StarterPayload(
                kind=StepKind.STARTER,
                text=free_prompt,
                starter="I would like to explain that",
                min_words=8 if band is Band.A2 else 14,
                max_seconds=75,
            ),
            rules_version=RULES_VERSION,
        ),
        LessonStep(
            step_id=f"{lesson_id}-s6",
            ordinal=6,
            stage=LessonStage.FREE,
            kind=StepKind.FREE,
            instruction="Nói tự do qua các lượt, thêm chi tiết ở lượt đầu.",
            payload=FreePayload(
                kind=StepKind.FREE,
                rounds=(
                    FreeRound(duration_seconds=60, prompt=free_prompt),
                    FreeRound(
                        duration_seconds=40, prompt=f"Summarize your main point: {free_prompt}"
                    ),
                ),
                max_seconds=60,
            ),
            rules_version=RULES_VERSION,
        ),
    )
    return Lesson(
        lesson_id=lesson_id,
        title=title,
        summary=summary,
        band=band,
        steps=steps,
        revision=1,
        content_version=content_version,
    )
