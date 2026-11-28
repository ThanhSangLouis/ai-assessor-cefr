"""docs/sdd/api/ is the API diagram's source while production hides /openapi.json.

The committed copy has to match the routes in the code; regenerate it with
`python tools/export_openapi.py` after adding or changing a route.
"""

import importlib.util
import json
from pathlib import Path


def _load_tool(name: str):
    """Load tools/<name>.py by path; the `pytest` binary in CI does not put the repo root on
    sys.path, so `from tools...` only works locally under `python -m pytest`."""
    path = Path(__file__).resolve().parent.parent / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tools_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_tool = _load_tool("export_openapi")
OUT = _tool.OUT
build_spec = _tool.build_spec
operations = _tool.operations
render_index = _tool.render_index


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
