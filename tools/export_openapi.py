"""Export the API description of the app to docs/sdd/api/.

Production turns /docs and /openapi.json off (AICEFR_ENV=production), so the API
diagram of the SDD is built from a committed copy instead:

- docs/sdd/api/openapi.json: the OpenAPI document FastAPI generates from the routes;
- docs/sdd/api/ENDPOINTS.md: every operation with its caller group (tag), the service
  the gateway sends it to (aicefr.platform.gateway.service_for) and its summary.

Run after adding or changing a route:
    python tools/export_openapi.py
tests/test_openapi_export.py fails when the committed copy no longer matches the code.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "sdd" / "api"
METHODS = ("get", "post", "put", "patch", "delete")


def build_spec() -> dict:
    from aicefr.api.main import app

    return app.openapi()


def operations(spec: dict) -> list[dict]:
    from aicefr.platform.gateway import service_for

    rows = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in METHODS:
                continue
            rows.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "tag": (op.get("tags") or ["page"])[0],
                    "service": service_for(path.replace("{", "").replace("}", "")) or "-",
                    "summary": (op.get("summary") or "").strip(),
                }
            )
    return rows


def render_index(rows: list[dict]) -> str:
    api = [r for r in rows if r["path"].startswith("/api/")]
    by_tag = Counter(r["tag"] for r in api)
    by_service = Counter(r["service"] for r in rows)
    lines = [
        "# Danh sách endpoint (sinh tự động)",
        "",
        "Sinh bằng `python tools/export_openapi.py` từ chính các route của ứng dụng;"
        " không sửa tay. Cột *Dịch vụ* là nơi gateway chuyển yêu cầu tới"
        " (`aicefr.platform.gateway.service_for`).",
        "",
        f"Tổng: **{len(rows)} thao tác**, trong đó **{len(api)}** dưới `/api/` và"
        f" {len(rows) - len(api)} trang HTML hoặc đường dẫn khác.",
        "",
        "| Nhóm người gọi (tag) | Số thao tác `/api/` |",
        "| --- | --- |",
        *[f"| `{t}` | {n} |" for t, n in by_tag.most_common()],
        "",
        "| Dịch vụ nhận | Số thao tác |",
        "| --- | --- |",
        *[f"| `{s}` | {n} |" for s, n in by_service.most_common()],
        "",
        "| Phương thức | Đường dẫn | Tag | Dịch vụ | Mô tả |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in sorted(rows, key=lambda r: (r["path"], r["method"])):
        summary = r["summary"].replace("|", "\\|")
        lines.append(f"| {r['method']} | `{r['path']}` | {r['tag']} | {r['service']} | {summary} |")
    return "\n".join(lines) + "\n"


def render_spec(spec: dict) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=1) + "\n"


def main() -> None:
    spec = build_spec()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "openapi.json").write_text(render_spec(spec), encoding="utf-8")
    (OUT / "ENDPOINTS.md").write_text(render_index(operations(spec)), encoding="utf-8")
    print(f"wrote {OUT / 'openapi.json'} and {OUT / 'ENDPOINTS.md'}")


if __name__ == "__main__":
    main()
