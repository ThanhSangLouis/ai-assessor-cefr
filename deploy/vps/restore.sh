#!/usr/bin/env bash
# Restore a backup made by deploy/vps/backup.sh (D047). Run on the server:
#
#   deploy/vps/restore.sh /srv/aicefr-backups/20261014T031500Z [--yes]
#
# REPLACES the current database and every recording with the backup's. Stops
# core, web and speech first so nothing writes meanwhile, and starts them again
# afterwards. Asks for confirmation unless --yes is given.
set -euo pipefail

usage() {
  echo "usage: $0 <backup-dir> [--yes]" >&2
  exit 2
}

BACKUP=""
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --yes | -y) ASSUME_YES=1 ;;
    -h | --help) usage ;;
    -*) usage ;;
    *)
      [[ -z "$BACKUP" ]] || usage
      BACKUP="$arg"
      ;;
  esac
done
[[ -n "$BACKUP" ]] || usage

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BACKUP="$(cd "$BACKUP" && pwd)"

compose() { docker compose -f docker-compose.yml -f docker-compose.prod.yml "$@"; }
step() { printf '\n==> %s\n' "$*"; }

for f in db.archive.gz uploads.tar.gz; do
  [[ -s "$BACKUP/$f" ]] || {
    echo "restore.sh: $BACKUP/$f is missing or empty" >&2
    exit 1
  }
done
if [[ -f "$BACKUP/SHA256SUMS" ]]; then
  step "Checking checksums"
  (cd "$BACKUP" && sha256sum -c SHA256SUMS)
fi
gzip -t "$BACKUP/db.archive.gz"

cd "$APP_DIR"
if [[ "$ASSUME_YES" -ne 1 ]]; then
  echo "This replaces the database and all recordings of the stack in $APP_DIR"
  echo "with the backup in $BACKUP. Anything written since then is lost."
  read -r -p "Type 'restore' to continue: " answer
  [[ "$answer" == "restore" ]] || {
    echo "Cancelled."
    exit 1
  }
fi

core_id="$(compose ps -a -q core)"
if [[ -z "$core_id" ]]; then
  echo "restore.sh: no core container; deploy the stack once (deploy.sh) before restoring" >&2
  exit 1
fi

step "Stopping core, web and speech"
compose stop core web speech
# Whatever happens below, bring the services back.
trap 'step "Starting core, web and speech"; compose up -d core web speech' EXIT

step "Making sure MongoDB is up"
compose up -d mongo
for _ in $(seq 1 60); do
  compose exec -T mongo mongosh --quiet --eval "db.adminCommand('ping').ok" >/dev/null 2>&1 && break
  sleep 2
done

step "Restoring the databases"
# --drop replaces each collection the archive holds. The core user lives in the
# aicefr database and is not in the dump: init-core-user.js made it once.
# Backups from before D051 have db.archive.gz only.
restore() {
  [[ -s "$BACKUP/$2" ]] || return 0
  compose exec -T -e DB="$1" mongo sh -c 'mongorestore --quiet -u "$MONGO_INITDB_ROOT_USERNAME" \
    -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --drop \
    --nsInclude "$DB.*" --archive --gzip' <"$BACKUP/$2"
}
restore aicefr db.archive.gz
restore aicefr_learning learning.archive.gz
restore aicefr_metering metering.archive.gz

step "Restoring the uploads volume"
docker run --rm --volumes-from "$core_id" -v "$BACKUP:/backup:ro" alpine:3 \
  sh -c 'find /data/uploads -mindepth 1 -delete && tar xzf /backup/uploads.tar.gz -C /data/uploads'

step "Restored from $BACKUP"
