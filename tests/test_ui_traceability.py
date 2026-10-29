"""The D024 test plan and the D024 test code must name the same test cases.

Same check as test_practice_traceability.py, for the interface redesign: a test
cannot be added to the UI E2E module without a row in
`docs/test/TEST_PLAN_UI.md`, a planned case cannot vanish from the code, and
every acceptance criterion of SPEC_WEB "Đợt 5" has at least one case.
"""

from __future__ import annotations

import pathlib
import re

import pytest

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "test" / "TEST_PLAN_UI.md"
SPEC = ROOT / "docs" / "web" / "SPEC_WEB.md"
E2E = ROOT / "tests" / "e2e" / "test_ui_e2e.py"
INTEGRATION = ROOT / "tests" / "test_progress_and_stats.py"
ROW = re.compile(r"^\| (TC-UI-[EI])\d{2} \| `(test_\w+)` \| (UX-\d{2}) \|", re.M)


def _rows() -> list[tuple[str, str, str]]:
    return ROW.findall(PLAN.read_text(encoding="utf-8"))


def _functions(path: pathlib.Path) -> set[str]:
    return set(re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M))


def test_every_ui_e2e_test_is_in_the_plan_and_back() -> None:
    planned = {name for prefix, name, _ux in _rows() if prefix == "TC-UI-E"}
    code = _functions(E2E)
    assert code - planned == set(), "test chưa có trong kế hoạch"
    assert planned - code == set(), "kế hoạch nhắc test không còn trong mã"


def test_planned_integration_cases_exist() -> None:
    planned = {name for prefix, name, _ux in _rows() if prefix == "TC-UI-I"}
    assert planned and planned <= _functions(INTEGRATION)


def test_every_criterion_of_the_redesign_is_covered() -> None:
    criteria = set(re.findall(r"\*\*(UX-\d{2})\*\*", SPEC.read_text(encoding="utf-8")))
    matrix = PLAN.read_text(encoding="utf-8").split("## 3.")[1].split("## 4.")[0]
    covered = {
        ux
        for ux, cases in re.findall(r"^\| (UX-\d{2}) \| (.+) \|$", matrix, re.M)
        if "TC-UI" in cases
    }
    assert criteria and criteria <= covered, sorted(criteria - covered)
    assert {ux for _p, _n, ux in _rows()} <= criteria
