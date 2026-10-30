"""The D028..D049 test plans and their test code must name the same test cases.

Same rule as for D023 and D025: each plan maps every case to an acceptance
criterion or a requirement, and this check keeps that map honest in both
directions. It also checks the other promise of the SRS: every acceptance
criterion of FR-51..FR-85 names a test, and that test exists.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

import pytest

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRS = ROOT / "docs" / "srs" / "SRS.md"


@dataclass(frozen=True)
class Plan:
    name: str
    path: pathlib.Path
    layers: dict[str, pathlib.Path]
    requirements: str  # regex alternation for the FR numbers, e.g. "5[1-5]"
    criteria: int

    @property
    def row(self) -> re.Pattern:
        prefixes = "|".join(re.escape(p) for p in self.layers)
        return re.compile(
            rf"^\| ({prefixes})\d{{2}} \| `(test_\w+)` \| "
            rf"(AC-(?:{self.requirements})\.\d+|FR-(?:{self.requirements})) \|",
            re.M,
        )

    @property
    def criterion(self) -> re.Pattern:
        # \d+, not \d: a requirement can have ten criteria or more (AC-62.10).
        return re.compile(rf"\*\*(AC-(?:{self.requirements})\.\d+)\*\* — .*?\(`(test_\w+)`\)")


PLANS = [
    Plan(
        "D028",
        ROOT / "docs" / "test" / "TEST_PLAN_D028.md",
        {
            "TC-PC-I": ROOT / "tests" / "test_accounts.py",
            "TC-PC-E": ROOT / "tests" / "e2e" / "test_accounts_e2e.py",
            "TC-PC-A": ROOT / "tests" / "test_admin_access.py",
        },
        "5[1-5]",
        19,
    ),
    Plan(
        "D029",
        ROOT / "docs" / "test" / "TEST_PLAN_D029.md",
        {
            "TC-PF-U": ROOT / "tests" / "test_google_unit.py",
            "TC-PF-I": ROOT / "tests" / "test_profile.py",
            "TC-PF-E": ROOT / "tests" / "e2e" / "test_profile_e2e.py",
        },
        "5[6-9]|60",
        21,
    ),
    Plan(
        "D030",
        ROOT / "docs" / "test" / "TEST_PLAN_D030.md",
        {
            "TC-BR-U": ROOT / "tests" / "test_assign_unit.py",
            "TC-BR-S": ROOT / "tests" / "test_agreement.py",
            "TC-BR-I": ROOT / "tests" / "test_ratings.py",
            "TC-BR-E": ROOT / "tests" / "e2e" / "test_ratings_e2e.py",
        },
        "6[1-4]",
        20,  # AC-64.2 (withdrawn consent) dropped with D058
    ),
    Plan(
        "D032",
        ROOT / "docs" / "test" / "TEST_PLAN_D032.md",
        {
            "TC-TT-U": ROOT / "tests" / "test_achievements_unit.py",
            "TC-TT-I": ROOT / "tests" / "test_achievements.py",
            "TC-TT-E": ROOT / "tests" / "e2e" / "test_achievements_e2e.py",
        },
        "6[5-6]",
        14,
    ),
    Plan(
        "D034",
        ROOT / "docs" / "test" / "TEST_PLAN_D034.md",
        {
            "TC-GD-U": ROOT / "tests" / "test_billing_unit.py",
            "TC-GD-I": ROOT / "tests" / "test_billing.py",
            "TC-GD-E": ROOT / "tests" / "e2e" / "test_billing_e2e.py",
        },
        "6[7-9]|70",
        24,
    ),
    Plan(
        "D035",
        ROOT / "docs" / "test" / "TEST_PLAN_D035.md",
        {
            "TC-CT-U": ROOT / "tests" / "test_gateways_unit.py",
            "TC-CT-I": ROOT / "tests" / "test_gateways.py",
            "TC-CT-E": ROOT / "tests" / "e2e" / "test_gateways_e2e.py",
        },
        "7[1-3]",
        21,
    ),
    Plan(
        "D036",
        ROOT / "docs" / "test" / "TEST_PLAN_D036.md",
        {
            "TC-GG-U": ROOT / "tests" / "test_google_flow_unit.py",
            "TC-GG-I": ROOT / "tests" / "test_google_flow.py",
            "TC-GG-E": ROOT / "tests" / "e2e" / "test_google_setup_e2e.py",
        },
        "74",
        8,
    ),
    Plan(
        "D039-D042",
        ROOT / "docs" / "test" / "TEST_PLAN_D039_D042.md",
        {
            "TC-LE-U": ROOT / "tests" / "test_learning_evidence_unit.py",
            "TC-LE-I": ROOT / "tests" / "test_learning_evidence.py",
            "TC-LE-E": ROOT / "tests" / "e2e" / "test_learning_evidence_e2e.py",
        },
        "7[5-9]|80",
        33,  # AC-77.6 (withdrawing research consent) dropped with D058
    ),
    Plan(
        "D045-D047",
        ROOT / "docs" / "test" / "TEST_PLAN_D045_D047.md",
        {
            "TC-LP-U": ROOT / "tests" / "test_path_composer_unit.py",
            "TC-LP-I": ROOT / "tests" / "test_learning_plans.py",
            "TC-LP-E": ROOT / "tests" / "e2e" / "test_learning_plans_e2e.py",
            "TC-DB-I": ROOT / "tests" / "test_schema.py",
            "TC-DP-U": ROOT / "tests" / "test_deploy_config.py",
        },
        "8[1-4]",
        26,
    ),
    Plan(
        "D049",
        ROOT / "docs" / "test" / "TEST_PLAN_D049.md",
        {
            "TC-ME-U": ROOT / "tests" / "test_metering_unit.py",
            "TC-ME-I": ROOT / "tests" / "test_metering.py",
        },
        "85",
        10,
    ),
]
LAYERS = [(plan, prefix) for plan in PLANS for prefix in plan.layers]


def _planned(plan: Plan, prefix: str) -> set[str]:
    rows = plan.row.findall(plan.path.read_text(encoding="utf-8"))
    return {name for p, name, _trace in rows if p == prefix}


def _defined(path: pathlib.Path) -> set[str]:
    return set(re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M))


@pytest.mark.parametrize("plan, prefix", LAYERS, ids=lambda x: getattr(x, "name", x))
def test_every_test_in_the_layer_is_in_the_plan_and_back(plan: Plan, prefix: str) -> None:
    code = _defined(plan.layers[prefix])
    planned = _planned(plan, prefix)
    assert code - planned == set(), f"{plan.name} {prefix}: test chưa có trong kế hoạch"
    assert planned - code == set(), f"{plan.name} {prefix}: kế hoạch nhắc test không còn trong mã"


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.name)
def test_every_acceptance_criterion_is_covered(plan: Plan) -> None:
    criteria = {ac for ac, _name in plan.criterion.findall(SRS.read_text(encoding="utf-8"))}
    traced = {t for _p, _n, t in plan.row.findall(plan.path.read_text(encoding="utf-8"))}
    assert len(criteria) == plan.criteria, f"SRS phải có {plan.criteria} tiêu chí cho {plan.name}"
    assert criteria <= traced, sorted(criteria - traced)


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.name)
def test_the_test_each_criterion_names_exists(plan: Plan) -> None:
    code = set().union(*(_defined(path) for path in plan.layers.values()))
    srs = SRS.read_text(encoding="utf-8")
    named = {name: ac for ac, name in plan.criterion.findall(srs)}
    missing = sorted(f"{ac}: {name}" for name, ac in named.items() if name not in code)
    assert not missing, missing
