"""The D025 test plan and the D025 test code must name the same test cases.

Same rule as for D023 (`test_practice_traceability.py`): the plan in
`docs/test/TEST_PLAN_D025.md` maps every case to an acceptance criterion or a
requirement, and this check keeps that map honest in both directions. It also
checks the other promise of the SRS: every acceptance criterion of FR-45..FR-50
names a test, and that test exists.
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "test" / "TEST_PLAN_D025.md"
SRS = ROOT / "docs" / "srs" / "SRS.md"
LAYERS = {
    "TC-LS-U": ROOT / "tests" / "test_lessons_unit.py",
    "TC-LS-I": ROOT / "tests" / "test_lessons_integration.py",
    "TC-LS-E": ROOT / "tests" / "e2e" / "test_lessons_e2e.py",
}
ROW = re.compile(
    r"^\| (TC-LS-[UIE])\d{2} \| `(test_\w+)` \| (AC-(?:4[5-9]|50)\.\d|FR-(?:4[5-9]|50)) \|", re.M
)
CRITERION = re.compile(r"\*\*(AC-(?:4[5-9]|50)\.\d)\*\* — .*?\(`(test_\w+)`\)")


def _planned() -> dict[str, set[str]]:
    rows: dict[str, set[str]] = {prefix: set() for prefix in LAYERS}
    for prefix, name, _trace in ROW.findall(PLAN.read_text(encoding="utf-8")):
        rows[prefix].add(name)
    return rows


def _defined(path: pathlib.Path) -> set[str]:
    return set(re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M))


@pytest.mark.parametrize("prefix", sorted(LAYERS))
def test_every_test_in_the_layer_is_in_the_plan_and_back(prefix: str) -> None:
    code = _defined(LAYERS[prefix])
    planned = _planned()[prefix]
    assert code - planned == set(), f"{prefix}: test chưa có trong kế hoạch"
    assert planned - code == set(), f"{prefix}: kế hoạch nhắc test không còn trong mã"


def test_every_acceptance_criterion_of_d025_is_covered() -> None:
    criteria = {ac for ac, _name in CRITERION.findall(SRS.read_text(encoding="utf-8"))}
    traced = {t for _p, _n, t in ROW.findall(PLAN.read_text(encoding="utf-8"))}
    assert len(criteria) == 21, "SRS mục 3.9b phải có 21 tiêu chí chấp nhận AC-45.1..AC-50.2"
    assert criteria <= traced, sorted(criteria - traced)


def test_the_test_each_criterion_names_exists() -> None:
    code = set().union(*(_defined(path) for path in LAYERS.values()))
    named = dict((name, ac) for ac, name in CRITERION.findall(SRS.read_text(encoding="utf-8")))
    missing = sorted(f"{ac}: {name}" for name, ac in named.items() if name not in code)
    assert not missing, missing
