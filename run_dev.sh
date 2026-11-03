#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Load local environment variables from .env
if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

export AICEFR_ENV="development"
export AICEFR_MODEL_DIR="${AICEFR_MODEL_DIR:-$PWD/tests/fixtures/models}"
if [ -f "$AICEFR_MODEL_DIR/SHA256SUMS" ]; then
  AICEFR_MODEL_PINS="$(awk '{sub(/\.json$/, "", $2); printf "%s%s=%s", sep, $2, $1; sep=","}' "$AICEFR_MODEL_DIR/SHA256SUMS")"
  export AICEFR_MODEL_PINS
fi

echo "Starting SpeakUp development server at http://localhost:8000 ..."
exec .venv/bin/uvicorn aicefr.api.main:app --reload --host 0.0.0.0 --port 8000
