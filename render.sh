#!/usr/bin/env bash
# Render every diagram under docs/sdd/diagrams to docs/sdd/images.
#
# Two renderers, because the sources are two formats on purpose: the class
# diagram is `.drawio` so it can be dragged into shape by hand, everything else
# is `.puml` where automatic layout is already good enough.
#
# PlantUML needs a real JRE. macOS ships only a stub at /usr/bin/java, so we
# point at the Homebrew JDK explicitly rather than relying on PATH.
set -euo pipefail

# Chay duoc tu bat ky thu muc nao: moi duong dan duoi day la tuong doi so voi
# goc repo, nen phai ve goc repo truoc.
cd "$(dirname "$0")"

JAVA="${JAVA:-/opt/homebrew/opt/openjdk/bin/java}"
JAR="${PLANTUML_JAR:-$HOME/.local/lib/plantuml.jar}"

if [ ! -x "$JAVA" ]; then
  echo "No JRE at $JAVA. Install one with:  brew install openjdk" >&2
  exit 1
fi
if [ ! -f "$JAR" ]; then
  echo "plantuml.jar not found at $JAR. Download it with:" >&2
  echo "  curl -L -o $JAR https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar" >&2
  exit 1
fi

mkdir -p docs/sdd/images
"$JAVA" -jar "$JAR" -tpng -o "$(pwd)/docs/sdd/images" docs/sdd/diagrams/*.puml

# draw.io. `--no-sandbox` is required when Electron runs without a desktop
# session; scale 2 keeps the 13pt labels readable once the page is fitted to A4.
if command -v drawio >/dev/null 2>&1; then
  for src in docs/sdd/diagrams/*.drawio; do
    drawio -x -f png --scale 2 --border 20 \
      -o "docs/sdd/images/$(basename "${src%.drawio}").png" "$src" --no-sandbox
  done
else
  echo "drawio CLI not found, skipping .drawio. Install it with:" >&2
  echo "  brew install --cask drawio" >&2
fi

echo "Rendered:"
ls -1 docs/sdd/images/*.png
