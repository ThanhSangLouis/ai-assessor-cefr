#!/usr/bin/env bash
# Back up the production database and recordings (D047). Run on the server, as
# the deploy user, from anywhere; cron-able:
#
#   15 3 * * * /srv/aicefr/deploy/vps/backup.sh >>/srv/aicefr-backups/backup.log 2>&1
#
# Writes /srv/aicefr-backups/<UTC timestamp>/ with
#   db.archive.gz        mongodump of the aicefr database (D048; restore drops and
#                        replaces each collection, so it suits an existing or an empty server)
#   learning.archive.gz  the learning part's database, aicefr_learning (D051)
#   metering.archive.gz  the metering ledger's database, aicefr_metering (D051)
#   uploads.tar.gz  the uploads volume (recordings: personal data)
#   SHA256SUMS
# and deletes backups older than KEEP_DAYS (14). Restore: deploy/vps/restore.sh.
# These files are personal data: keep the directory private and copy it off the
# server (another machine, encrypted) -- a backup on the same disk is not one.
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BACKUP_ROOT="${BACKUP_ROOT:-/srv/aicefr-backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"

compose() { docker compose -f docker-compose.yml -f docker-compose.prod.yml "$@"; }
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

cd "$APP_DIR"
umask 077
mkdir -p "$BACKUP_ROOT"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dest="$BACKUP_ROOT/$stamp"
work="$dest.partial"
# A failed run leaves no directory that looks like a finished backup.
trap 'rm -rf "$work"' EXIT
mkdir "$work"

# One archive per database (D051: a database per service). The root credentials
# live in the mongo container's environment, never on this command line.
dump() {
  log "database $1 -> $dest/$2"
  compose exec -T -e DB="$1" mongo sh -c 'mongodump --quiet -u "$MONGO_INITDB_ROOT_USERNAME" \
    -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --db "$DB" \
    --archive --gzip' >"$work/$2"
}
dump aicefr db.archive.gz
dump aicefr_learning learning.archive.gz
dump aicefr_metering metering.archive.gz

log "uploads volume -> $dest/uploads.tar.gz"
core_id="$(compose ps -a -q core)"
if [[ -z "$core_id" ]]; then
  echo "backup.sh: no core container; is the stack deployed in $APP_DIR?" >&2
  exit 1
fi
# A throwaway container that sees the same uploads volume, read only.
docker run --rm --volumes-from "$core_id:ro" -v "$work:/backup" alpine:3 \
  tar czf /backup/uploads.tar.gz -C /data/uploads .

(cd "$work" && sha256sum ./*.archive.gz uploads.tar.gz >SHA256SUMS)
mv "$work" "$dest"
trap - EXIT
log "done: $(du -sh "$dest" | cut -f1) in $dest"

log "deleting backups older than $KEEP_DAYS days"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20*T*Z' -mtime "+$KEEP_DAYS" \
  -print -exec rm -rf {} +
