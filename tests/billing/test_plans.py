import aicefr.billing.plans as policy
from aicefr.billing.contracts import Plan
from aicefr.billing.errors import BillingError
from aicefr.billing.plans import LEARNING_FEATURES, PLANS, get_plan


def test_plan_ladder_is_monotonic_and_preserves_learning_rights():
    plans = tuple(PLANS.values())
    for lower, upper in zip(plans, plans[1:], strict=False):
        assert lower.features <= upper.features
        assert lower.student_limit <= upper.student_limit
    assert all(LEARNING_FEATURES <= plan.features for plan in plans)
    assert PLANS["FREE"].student_limit == 30
    assert PLANS["ADVANCED"].student_limit == 500


def test_plan_lookup_rejects_unknown_values():
    for value in ("enterprise", "standard", None, 1):
        try:
            get_plan(value)
        except BillingError as exc:
            assert exc.code == "unknown_plan"
        else:
            raise AssertionError("unknown plan was accepted")


def test_plan_lookup_and_ladder_validation_accept_valid_policy():
    assert get_plan("STANDARD") == PLANS["STANDARD"]
    policy.validate_plan_ladder()


def test_plan_ladder_validation_rejects_feature_or_seat_regressions(monkeypatch):
    baseline = PLANS["FREE"]
    less_features = Plan("OTHER", "Other", 1, 40, 90, frozenset())
    monkeypatch.setattr(policy, "PLANS", {"FREE": baseline, "OTHER": less_features})
    try:
        policy.validate_plan_ladder()
    except RuntimeError as exc:
        assert "features" in str(exc)
    else:
        raise AssertionError("feature regression was accepted")

    more_features_fewer_seats = Plan("OTHER", "Other", 1, 10, 90, baseline.features | {"extra"})
    monkeypatch.setattr(policy, "PLANS", {"FREE": baseline, "OTHER": more_features_fewer_seats})
    try:
        policy.validate_plan_ladder()
    except RuntimeError as exc:
        assert "limits" in str(exc)
    else:
        raise AssertionError("student limit regression was accepted")
