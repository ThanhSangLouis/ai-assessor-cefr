"""Export approved built-in imagegen terrain; never upscale native artwork."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/design/student/practice/adventure-worlds-v3-prompts.json"
OUTPUT = ROOT / "src/aicefr/api/static/art/adventure"


def main():
    manifest = json.loads(MANIFEST.read_text())
    for asset in manifest["assets"]:
        source = Path(asset["native_image"])
        image = Image.open(source).convert("RGB")
        if image.size != (1536, 1024):
            raise ValueError(f"Unexpected native size for {source}: {image.size}")
        asset["native_size"] = list(image.size)
        exports = []
        for width in (480, 768, 960, 1280, 1536):
            name = f"{asset['world']}-{asset['mode']}-{asset['segment']}-v3-{width}.webp"
            target = OUTPUT / name
            size = (width, round(width * image.height / image.width))
            if not target.exists():
                image.resize(size, Image.Resampling.LANCZOS).save(
                    target, quality=93 if width == 1536 else 90, method=6
                )
            with Image.open(target) as exported:
                assert exported.size == size, target
            exports.append(
                {
                    "file": str(target.relative_to(ROOT)),
                    "width": width,
                    "bytes": target.stat().st_size,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                }
            )
        asset["exports"] = exports
    manifest["native_resolution_limit"] = (
        "Native artwork is 1536x1024; exports are downsampled, never upscaled. "
        "Very wide desktop displays at DPR 2 can exceed native source density."
    )
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Exported/verified {len(manifest['assets']) * 5} WebP assets")


if __name__ == "__main__":
    main()
