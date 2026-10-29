"""The feedback study: does evidence-linked feedback help learners more than a score alone? (D040)

Two arms, assigned at random among students who allowed research use:

- `feedback`: the report as every learner sees it -- comments, evidence in the
  recording, priorities, the aspect to practise next;
- `score_only`: the estimated score and band, nothing else.

The outcome is each participant's gain: their last scored assessment at least
`min_days` after their first one inside the study, minus that first one. The
two arms are compared by the difference of mean gains with a bootstrap 95 %
interval (participants resampled within each arm) and Hedges' g. With the
20–30 participants a class gives, the study is exploratory: the interval is
the result, not a p-value, and a null result is a valid one.

Every function here is pure; the repository stores, this module decides and
computes. The seed is stored with the study, so the assignment and the
bootstrap can be run again and give the same numbers.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, stdev

STUDY_VERSION = "feedback-study-v1"
ARMS = ("feedback", "score_only")
ARM_NAMES = {"feedback": "Phản hồi đầy đủ", "score_only": "Chỉ điểm"}


class StudyStatus(str, Enum):
    """Where a study is: measuring, collecting the closing survey, or over."""

    RUNNING = "running"
    SURVEY = "survey"
    CLOSED = "closed"


STATUSES = tuple(s.value for s in StudyStatus)
MIN_PARTICIPANTS = 4
BOOTSTRAP_REPS = 2000

# Five-point agreement, 1 = hoàn toàn không đồng ý ... 5 = hoàn toàn đồng ý.
SURVEY_ITEMS = (
    ("knew_what_to_practise", "Kết quả giúp tôi biết mình cần luyện gì."),
    ("understood", "Tôi hiểu kết quả mà hệ thống đưa ra."),
    ("trusted", "Tôi tin kết quả phản ánh đúng bài nói của mình."),
    ("practised_more", "Sau khi xem kết quả, tôi đã luyện thêm."),
    ("would_continue", "Tôi muốn tiếp tục dùng hệ thống."),
)
SURVEY_KEYS = tuple(k for k, _ in SURVEY_ITEMS)


def assign_arms(account_ids: Iterable[str], seed: int) -> dict[str, str]:
    """Balanced random assignment: shuffle with the study's seed, then alternate arms."""
    ids = sorted(set(account_ids))
    rnd = random.Random(seed)
    rnd.shuffle(ids)
    return {a: ARMS[i % 2] for i, a in enumerate(ids)}


def _when(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def pre_post(
    scores: Sequence[tuple[str, float]], enrolled_at: str, min_days: int
) -> tuple[float, float] | None:
    """First scored assessment after enrolment, and the last one `min_days` or more after it."""
    start = _when(enrolled_at)
    inside = sorted((_when(t), s) for t, s in scores if _when(t) >= start)
    if len(inside) < 2:
        return None
    (t0, pre), later = inside[0], inside[1:]
    after = [s for t, s in later if t - t0 >= timedelta(days=min_days)]
    return (pre, after[-1]) if after else None


def hedges_g(a: list[float], b: list[float]) -> float | None:
    """Standardised difference of means (b − a), corrected for small samples."""
    if len(a) < 2 or len(b) < 2:
        return None
    na, nb = len(a), len(b)
    pooled = math.sqrt(((na - 1) * stdev(a) ** 2 + (nb - 1) * stdev(b) ** 2) / (na + nb - 2))
    if pooled == 0:
        return None
    d = (mean(b) - mean(a)) / pooled
    return d * (1 - 3 / (4 * (na + nb) - 9))


def bootstrap_difference(
    a: list[float], b: list[float], seed: int, reps: int = BOOTSTRAP_REPS
) -> tuple[float, float] | None:
    """95 % percentile interval of mean(b) − mean(a), resampling within each arm."""
    if len(a) < 2 or len(b) < 2:
        return None
    rnd = random.Random(seed)
    diffs = sorted(
        mean(rnd.choices(b, k=len(b))) - mean(rnd.choices(a, k=len(a))) for _ in range(reps)
    )
    return diffs[int(0.025 * reps)], diffs[int(0.975 * reps) - 1]


def analyse(
    participants: Sequence[Mapping],
    scores: Mapping[str, Sequence[tuple[str, float]]],
    practice: Mapping[str, int],
    surveys: Mapping[str, Mapping[str, int]],
    min_days: int,
    seed: int,
) -> dict:
    """The study's result: per arm and the difference feedback − score_only.

    `participants`: rows with `account_id`, `arm`, `enrolled_at`, `withdrawn_at`.
    Withdrawn participants are left out of every figure.
    """
    arms: dict[str, dict] = {}
    gains: dict[str, list[float]] = {a: [] for a in ARMS}
    for arm in ARMS:
        members = [p for p in participants if p["arm"] == arm and not p.get("withdrawn_at")]
        for p in members:
            pair = pre_post(scores.get(p["account_id"], ()), p["enrolled_at"], min_days)
            if pair:
                gains[arm].append(pair[1] - pair[0])
        answered = [surveys[p["account_id"]] for p in members if p["account_id"] in surveys]
        arms[arm] = {
            "name": ARM_NAMES[arm],
            "enrolled": len(members),
            "with_pre_post": len(gains[arm]),
            "mean_gain": round(mean(gains[arm]), 3) if gains[arm] else None,
            "sd_gain": round(stdev(gains[arm]), 3) if len(gains[arm]) > 1 else None,
            "mean_practice_attempts": (
                round(mean(practice.get(p["account_id"], 0) for p in members), 2)
                if members
                else None
            ),
            "survey_responses": len(answered),
            "survey": {
                key: round(mean(s[key] for s in answered), 2) if answered else None
                for key in SURVEY_KEYS
            },
        }
    control, treated = gains["score_only"], gains["feedback"]
    diff = round(mean(treated) - mean(control), 3) if control and treated else None
    ci = bootstrap_difference(control, treated, seed)
    g = hedges_g(control, treated)
    return {
        "version": STUDY_VERSION,
        "min_days": min_days,
        "arms": arms,
        "difference": {
            "label": "Phản hồi đầy đủ − Chỉ điểm (mức tăng điểm trung bình)",
            "value": diff,
            "ci95": [round(ci[0], 3), round(ci[1], 3)] if ci else None,
            "hedges_g": round(g, 3) if g is not None else None,
        },
        "survey_items": [{"key": k, "text": t} for k, t in SURVEY_ITEMS],
        "note": (
            "Nghiên cứu thăm dò với cỡ mẫu nhỏ: đọc khoảng tin cậy, "
            "không đọc riêng giá trị trung bình. Điểm là ước lượng của máy."
        ),
    }
