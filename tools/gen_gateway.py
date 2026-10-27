"""Write the gateway's nginx configuration from `aicefr.platform.gateway` (D043).

python tools/gen_gateway.py           # write deploy/gateway/default.conf.template
python tools/gen_gateway.py --check   # exit 1 when the committed file is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aicefr.platform.gateway import nginx_config

OUT = Path(__file__).resolve().parents[1] / "deploy" / "gateway" / "default.conf.template"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    text = nginx_config()
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT} is stale: run python tools/gen_gateway.py", file=sys.stderr)
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
