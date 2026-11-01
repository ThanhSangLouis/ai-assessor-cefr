"""The D023 test plan and the D023 test code must name the same test cases.

Rubric TC2.5 asks for test cases traceable to acceptance criteria. The plan in
`docs/test/TEST_PLAN_D023.md` maps every case to an AC; this check keeps that
map honest in both directions, so a test cannot be added without being traced
and a traced case cannot silently disappear from the code.
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "test" / "TEST_PLAN_D023.md"
LAYERS = {
    "TC-PR-U": ROOT / "tests" / "test_practice_unit.py",
    "TC-PR-E": ROOT / "tests" / "e2e" / "test_practice_e2e.py",
}
ROW = re.compile(r"^\| (TC-PR-[UIE])\d{2} \| `(test_\w+)` \| (AC-4\d\.\d|FR-4\d) \|", re.M)


def _planned() -> dict[str, set[str]]:
    rows: dict[str, set[str]] = {prefix: set() for prefix in LAYERS}
    for prefix, name, _trace in ROW.findall(PLAN.read_text(encoding="utf-8")):
        rows[prefix].add(name)
    return rows


@pytest.mark.parametrize("prefix", sorted(LAYERS))
def test_every_test_in_the_layer_is_in_the_plan_and_back(prefix: str) -> None:
    code = set(re.findall(r"^def (test_\w+)\(", LAYERS[prefix].read_text(encoding="utf-8"), re.M))
    planned = _planned()[prefix]
    assert code - planned == set(), f"{prefix}: test chưa có trong kế hoạch"
    assert planned - code == set(), f"{prefix}: kế hoạch nhắc test không còn trong mã"


def test_every_acceptance_criterion_of_d023_is_covered() -> None:
    srs = (ROOT / "docs" / "srs" / "SRS.md").read_text(encoding="utf-8")
    criteria = set(re.findall(r"\*\*(AC-4[0-4]\.\d)\*\*", srs))
    traced = {t for _p, _n, t in ROW.findall(PLAN.read_text(encoding="utf-8"))}
    assert criteria and criteria <= traced, sorted(criteria - traced)
