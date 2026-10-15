"""Server-owned sandbox plan policy and monotonic entitlement features."""

from __future__ import annotations

from aicefr.billing.contracts import Plan
from aicefr.billing.errors import BillingError

LEARNING_FEATURES = frozenset({"learning", "practice", "personal_data"})
_TRIAL_FEATURES = frozenset({"lesson_authoring"})
_STANDARD_FEATURES = frozenset({"class_insights"})
_ADVANCED_FEATURES = frozenset({"blind_rating", "advanced_reports", "bulk_operations"})

PLANS: dict[str, Plan] = {
    "FREE": Plan("FREE", "Free", 0, 30, 80, LEARNING_FEATURES),
    "TRIAL": Plan("TRIAL", "Trial", 0, 30, 100, LEARNING_FEATURES | _TRIAL_FEATURES),
    "STANDARD": Plan(
        "STANDARD",
        "Standard",
        99_000,
        100,
        1_000,
        LEARNING_FEATURES | _TRIAL_FEATURES | _STANDARD_FEATURES,
    ),
    "ADVANCED": Plan(
        "ADVANCED",
        "Advanced",
        199_000,
        500,
        5_000,
        LEARNING_FEATURES | _TRIAL_FEATURES | _STANDARD_FEATURES | _ADVANCED_FEATURES,
    ),
}


def get_plan(code: str) -> Plan:
    if not isinstance(code, str) or code not in PLANS:
        raise BillingError("unknown_plan")
    return PLANS[code]


def validate_plan_ladder() -> None:
    ordered = tuple(PLANS.values())
    if any(not (a.features <= b.features) for a, b in zip(ordered, ordered[1:], strict=False)):
        raise RuntimeError("billing plan features must be monotonic")
    if any(
        not (a.student_limit <= b.student_limit) for a, b in zip(ordered, ordered[1:], strict=False)
    ):
        raise RuntimeError("billing plan limits must be monotonic")


validate_plan_ladder()
