"""docs/sdd/api/ is the API diagram's source while production hides /openapi.json.

The committed copy has to match the routes in the code; regenerate it with
`python tools/export_openapi.py` after adding or changing a route.
"""

import json
from pathlib import Path

from tools.export_openapi import OUT, build_spec, operations, render_index

ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_endpoint_list_matches_the_routes():
    committed = (OUT / "ENDPOINTS.md").read_text(encoding="utf-8")
    assert committed == render_index(operations(build_spec())), (
        "docs/sdd/api/ENDPOINTS.md is stale: run python tools/export_openapi.py"
    )


def test_the_committed_openapi_has_the_same_operations():
    committed = json.loads((OUT / "openapi.json").read_text(encoding="utf-8"))
    current = build_spec()

    def ops(spec):
        return {(m, p) for p, item in spec["paths"].items() for m in item}

    assert ops(committed) == ops(current)
