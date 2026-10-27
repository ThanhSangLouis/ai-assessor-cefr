"""Choose the next practice task, with a reason that can be said out loud. D023.

This is step 3 of the feedback loop in outline section 2.5 ("suggest one next
practice task through a transparent rule"), and it is why this module is a pure
function rather than a model: a teacher can read the whole rule on one screen,
and every suggestion can answer "why this task".

The rule, in order:

1. The focus criterion is the WEAKEST criterion of the latest assessment -- only
   when that assessment carries per-criterion indicators (`weakest_criteria`
   not empty). Otherwise follow the path order `PATH_ORDER`.
2. The starting band is the band of the latest assessment (the teacher's band
   when a teacher changed it). With no assessment yet, start at A2 -- like the
   placement test of language-learning apps: the assessment is the placement.
3. Within the criterion being considered, pick the uncompleted task at the
   lowest band from the starting band upwards; then the lower bands; then move
   on to the next criterion.
4. When every task is completed, suggest reviewing the one left the longest.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from aicefr.contracts import Band, Criterion
from aicefr.practice.bank import BAND_ORDER, CRITERION_NAMES, PATH_ORDER


class PracticeTaskRef(Protocol):
    task_id: str
    criterion: Criterion | None
    band: Band | None


@dataclass(frozen=True)
class TaskProgress:
    """How far a learner has got with one practice task."""

    attempts: int = 0
    completed: bool = False
    last_attempt_at: str | None = None
    last_completed: bool | None = None


class RecommendationBasis(str, Enum):
    WEAKEST_CRITERION = "weakest_criterion"
    NO_ASSESSMENT = "no_assessment"
    CONTINUE_PATH = "continue_path"
    REVIEW = "review"


@dataclass(frozen=True)
class Recommendation:
    task_id: str
    basis: RecommendationBasis
    reason: str


def _later_bands(start: Band) -> list[Band]:
    """Bands from the starting one upwards, then the lower ones (nearest first)."""
    i = BAND_ORDER.index(start)
    return list(BAND_ORDER[i:]) + list(reversed(BAND_ORDER[:i]))


def recommend(
    tasks: list[PracticeTaskRef],
    progress: dict[str, TaskProgress],
    weakest: list[Criterion],
    band: Band | None,
) -> Recommendation | None:
    """The task to practise next. None when the bank holds no practice task."""
    by_cell = {(t.criterion, t.band): t.task_id for t in tasks if t.criterion and t.band}
    if not by_cell:
        return None

    focus = weakest[0] if weakest else None
    order = ([focus] if focus else []) + [c for c in PATH_ORDER if c is not focus]
    start = band or Band.A2

    for criterion in order:
        for b in _later_bands(start):
            task_id = by_cell.get((criterion, b))
            if task_id is None or progress.get(task_id, TaskProgress()).completed:
                continue
            name = CRITERION_NAMES[criterion]
            if criterion is focus:
                return Recommendation(
                    task_id,
                    RecommendationBasis.WEAKEST_CRITERION,
                    f"Bài đánh giá gần nhất cho thấy {name.lower()} là tiêu chí thấp nhất "
                    f"của bạn so với các bài nói tham chiếu, nên luyện {name.lower()} "
                    f"ở mức {b.value}.",
                )
            if band is None:
                return Recommendation(
                    task_id,
                    RecommendationBasis.NO_ASSESSMENT,
                    "Bạn chưa có bài đánh giá nào có kết quả, nên lộ trình bắt đầu từ mức "
                    "A2. Làm một bài ở trang Nộp bài để gợi ý sát trình độ của bạn hơn.",
                )
            return Recommendation(
                task_id,
                RecommendationBasis.CONTINUE_PATH,
                f"Tiếp tục lộ trình: nhiệm vụ {name.lower()} mức {b.value} bạn chưa hoàn thành.",
            )

    # Every task completed: review the one left untouched the longest.
    oldest = min(
        by_cell.values(), key=lambda tid: progress.get(tid, TaskProgress()).last_attempt_at or ""
    )
    return Recommendation(
        oldest,
        RecommendationBasis.REVIEW,
        "Bạn đã hoàn thành cả lộ trình. Ôn lại nhiệm vụ đã lâu nhất chưa luyện để giữ kỹ năng.",
    )


def needs_review(progress: dict[str, TaskProgress]) -> list[str]:
    """Tasks attempted whose latest attempt was not completed, oldest first.

    Like the "review mistakes" section of language-learning apps: what the
    learner just stumbled on is what is most worth practising again, and the
    longer it waits the more it is forgotten.
    """
    pending = [
        (p.last_attempt_at or "", tid)
        for tid, p in progress.items()
        if p.attempts and p.last_completed is False
    ]
    return [tid for _, tid in sorted(pending)]
