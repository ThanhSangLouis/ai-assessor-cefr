#!/usr/bin/env bash
# Ship this working tree to the server and (re)start the production stack (D047).
# Run from the repository root on your own machine:
#
#   deploy/vps/deploy.sh aicefr@HOST [/srv/aicefr]
#
# Copies the code with rsync (never .env, data, recordings, the research corpus
# or local caches), refuses to go on when the server has no .env of its own,
# builds and starts the stack with docker-compose.prod.yml, then waits until
# https://$AICEFR_DOMAIN/healthz answers. The server's .env is the only source
# of its secrets; this script never reads or copies the local one.
set -euo pipefail

usage() {
  echo "usage: $0 user@host [remote-dir]   (remote-dir defaults to /srv/aicefr)" >&2
  exit 2
}

[[ $# -ge 1 && $# -le 2 ]] || usage
TARGET="$1"
REMOTE_DIR="${2:-/srv/aicefr}"
WAIT_SECONDS="${WAIT_SECONDS:-300}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -f "$ROOT/docker-compose.yml" && -f "$ROOT/docker-compose.prod.yml" ]] || {
  echo "deploy.sh: cannot find docker-compose.yml and docker-compose.prod.yml in $ROOT" >&2
  exit 1
}

step() { printf '\n==> %s\n' "$*"; }

step "Checking ${TARGET}:${REMOTE_DIR}/.env"
# The remote directory travels as an argument, never spliced into the script.
if ! ssh "$TARGET" bash -s -- "$REMOTE_DIR" <<'REMOTE'
set -euo pipefail
dir="$1"
if [[ ! -f "$dir/.env" ]]; then
  echo "deploy.sh: $dir/.env does not exist on the server." >&2
  echo "Create it from .env.production.example first (docs/plan/TRIEN_KHAI_VPS.md, step 4)." >&2
  exit 1
fi
if ! grep -qE '^AICEFR_DOMAIN=.+' "$dir/.env"; then
  echo "deploy.sh: AICEFR_DOMAIN is not set in $dir/.env." >&2
  exit 1
fi
REMOTE
then
  exit 1
fi

step "Copying the code (rsync)"
# Excluded paths are also protected from --delete on the server, so its .env,
# uploads and anything else listed here are never removed by a deploy.
rsync -az --delete \
  --include='/.env.example' \
  --include='/.env.production.example' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='*.py[cod]' \
  --exclude='*.db' \
  --exclude='*.db-*' \
  --exclude='*.sqlite' \
  --exclude='*.sqlite3' \
  --exclude='/data/' \
  --exclude='/uploads/' \
  --exclude='graphify-out/' \
  --exclude='.pytest_cache/' \
  --exclude='.pytest-run/' \
  --exclude='.ruff_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='.coverage' \
  --exclude='coverage.xml' \
  --exclude='htmlcov/' \
  --exclude='test-results/' \
  --exclude='playwright-report/' \
  --exclude='.tmp/' \
  --exclude='.cache/' \
  --exclude='.claude/' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  --exclude='*.key' \
  --exclude='*.pem' \
  --exclude='.secrets/' \
  --exclude='credentials.json' \
  --exclude='secrets.json' \
  --exclude='secure_identity/' \
  --exclude='research_data/' \
  --exclude='external_data/' \
  --exclude='sandi-work/' \
  --exclude='sandi-corpus-2025*/' \
  --exclude='artifacts/reports/' \
  --exclude='*.wav' \
  --exclude='*.flac' \
  --exclude='*.mp3' \
  --exclude='*.m4a' \
  --exclude='*.aac' \
  --exclude='*.ogg' \
  "$ROOT/" "${TARGET}:${REMOTE_DIR}/"

step "Building and starting the stack"
DOMAIN="$(ssh "$TARGET" bash -s -- "$REMOTE_DIR" <<'REMOTE'
set -euo pipefail
cd "$1"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans >&2
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps >&2
# The domain, as compose reads it: last assignment wins, quotes stripped.
sed -n 's/^AICEFR_DOMAIN=//p' .env | tail -n 1 | tr -d "\"' \r"
REMOTE
)"
[[ -n "$DOMAIN" ]] || {
  echo "deploy.sh: could not read AICEFR_DOMAIN from the server's .env" >&2
  exit 1
}

URL="https://${DOMAIN}"
step "Waiting for ${URL}/healthz (up to ${WAIT_SECONDS}s; the first certificate takes a moment)"
deadline=$((SECONDS + WAIT_SECONDS))
until curl -fsS --max-time 10 "${URL}/healthz" >/dev/null 2>&1; do
  if ((SECONDS >= deadline)); then
    echo "deploy.sh: ${URL}/healthz did not answer in ${WAIT_SECONDS}s." >&2
    echo "Check DNS (an A record to this server), ports 80/443, and:" >&2
    echo "  ssh ${TARGET} 'cd ${REMOTE_DIR} && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50 caddy core web'" >&2
    exit 1
  fi
  sleep 5
done

# D063: the seed accounts (QT-01, GV-01..03, SV-001..010), only those still
# missing, and only when the server's .env sets AICEFR_SEED_PASSWORD. The
# password is read on the server and handed to the one command that needs it;
# it never travels back here or into a log.
step "Seeding missing accounts"
ssh "$TARGET" bash -s -- "$REMOTE_DIR" <<'REMOTE'
set -euo pipefail
cd "$1"
seed="$(sed -n 's/^AICEFR_SEED_PASSWORD=//p' .env | tail -n 1 | tr -d "\"' \r")"
if [[ -z "$seed" ]]; then
  echo "AICEFR_SEED_PASSWORD is not set in .env: no accounts seeded."
  exit 0
fi
# Passed by name, not as NAME=value, so the password is not in any argv.
AICEFR_SEED_PASSWORD="$seed" docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T -e AICEFR_SEED_PASSWORD core python -m aicefr.accounts_cli seed
REMOTE

step "Deployed"
echo "${URL}"
