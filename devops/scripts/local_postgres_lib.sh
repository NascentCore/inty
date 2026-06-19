#!/usr/bin/env bash
# Shared constants and helpers for IntelliMate local Docker Postgres on the VM.
# CREATED_BY_AGENT
#
# Source from devops/scripts/*.sh:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/local_postgres_lib.sh"

readonly INTY_PG_CONTAINER="inty-dev-postgres"
readonly INTY_PG_VOLUME="inty-dev-postgres-data"
readonly INTY_PG_MAJOR_VERSION="17"
readonly INTY_PG_IMAGE="pgvector/pgvector:pg17"
readonly INTY_PG_IMAGE_PREVIOUS="pgvector/pgvector:pg16"
readonly INTY_PG_PORT="5432"
readonly INTY_PG_VOLUME_LABEL="inty.critical=postgres-data"
readonly INTY_PG_CONTAINER_LABEL="inty.critical=postgres"
readonly INTY_PG_BACKUP_DIR="/opt/inty/backups/postgres"
readonly INTY_PG_BACKUP_RETENTION_DAYS="14"
readonly INTY_PG_DEV_DB="inty-dev"
readonly INTY_PG_PROD_DB="inty"

local_postgres_lib_dir() {
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

local_postgres_repo_root() {
  cd "$(local_postgres_lib_dir)/../.." && pwd
}

assert_non_empty() {
  if [[ -z "$1" ]]; then
    echo "$2" >&2
    exit 1
  fi
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found in PATH" >&2
    exit 1
  fi
}

load_pg_password() {
  if [[ -n "${PGPASSWORD:-}" ]]; then
    return
  fi
  local cfg="${1:-$(local_postgres_repo_root)/devops/config.yaml.dev}"
  assert_non_empty "${cfg}" "config path required"
  if [[ ! -f "${cfg}" ]]; then
    echo "config not found: ${cfg}" >&2
    exit 1
  fi
  PGPASSWORD="$(
    grep -A8 '^database:' "${cfg}" \
      | grep 'password:' \
      | head -1 \
      | sed -E 's/^[[:space:]]*password:[[:space:]]*"?([^"#]*)"?.*/\1/'
  )"
  export PGPASSWORD
  assert_non_empty "${PGPASSWORD}" "could not read database.password from ${cfg}"
}

container_exists() {
  docker container inspect "${INTY_PG_CONTAINER}" >/dev/null 2>&1
}

container_running() {
  container_exists \
    && [[ "$(docker inspect -f '{{.State.Running}}' "${INTY_PG_CONTAINER}" 2>/dev/null)" == "true" ]]
}

container_restart_policy() {
  docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "${INTY_PG_CONTAINER}" 2>/dev/null
}

container_data_volume_name() {
  docker inspect -f \
    '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{if eq .Type "volume"}}{{.Name}}{{end}}{{end}}{{end}}' \
    "${INTY_PG_CONTAINER}" 2>/dev/null
}

container_image() {
  docker inspect -f '{{.Config.Image}}' "${INTY_PG_CONTAINER}" 2>/dev/null
}

postgres_server_version_major() {
  psql -h localhost -p "${INTY_PG_PORT}" -U postgres -d postgres -At -c 'SHOW server_version;' \
    | cut -d. -f1
}

volume_exists() {
  docker volume inspect "${INTY_PG_VOLUME}" >/dev/null 2>&1
}

database_fingerprint() {
  local db="$1"
  psql -h localhost -p "${INTY_PG_PORT}" -U postgres -d "${db}" -At -c \
    "SELECT pg_database_size('${db}')::text || ':' || (SELECT count(*)::text FROM pg_class WHERE relkind = 'r');"
}

wait_for_postgres_ready() {
  local attempts="${1:-30}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if psql -h localhost -p "${INTY_PG_PORT}" -U postgres -d postgres -At -c 'SELECT 1' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Postgres not ready on localhost:${INTY_PG_PORT} after ${attempts}s" >&2
  return 1
}

ensure_pg_hba_host_access() {
  if ! container_running; then
    return
  fi
  docker exec "${INTY_PG_CONTAINER}" bash -c '
    set -euo pipefail
    hba="${PGDATA}/pg_hba.conf"
    if grep -qE "^host[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]+" "${hba}"; then
      exit 0
    fi
    echo "host all all all scram-sha-256" >> "${hba}"
    psql -U postgres -d postgres -At -c "SELECT pg_reload_conf()" >/dev/null
  '
}

prune_old_backups() {
  local retention_days="$1"
  assert_non_empty "${retention_days}" "retention_days required"
  if [[ ! -d "${INTY_PG_BACKUP_DIR}" ]]; then
    return
  fi
  find "${INTY_PG_BACKUP_DIR}" -name '*.dump' -mtime +"${retention_days}" -delete
}
