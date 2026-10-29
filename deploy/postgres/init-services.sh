#!/bin/sh
# One PostgreSQL database, and one role and one schema for the core service (D044).
#
# The core service connects as its own role, which owns its schema and nothing
# else; PUBLIC loses its default rights. Run once, by the postgres image, when
# the data volume is first created. The password comes from the environment.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "REVOKE ALL ON SCHEMA public FROM PUBLIC" \
  -c "REVOKE ALL ON DATABASE \"$POSTGRES_DB\" FROM PUBLIC"

if [ -z "${CORE_DB_PASSWORD:-}" ]; then
  echo "init-services: CORE_DB_PASSWORD is not set" >&2
  exit 1
fi
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v role=core -v password="$CORE_DB_PASSWORD" -v db="$POSTGRES_DB" <<'SQL'
CREATE ROLE :"role" LOGIN PASSWORD :'password';
GRANT CONNECT ON DATABASE :"db" TO :"role";
CREATE SCHEMA :"role" AUTHORIZATION :"role";
ALTER ROLE :"role" SET search_path = :"role";
SQL
