#!/usr/bin/env bash
# Shared constants and helpers for IntelliMate local Docker Postgres on the VM.
# CREATED_BY_AGENT
#
# Source from devops/scripts/*.sh:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/local_postgres_lib.sh"
#
# TODO: Replace grep-based read_database_field_from_config with a small Python helper
# that loads database.* via the same Pydantic path as the backend (app/utils/config.py).

readonly INTY_PG_CONTAINER="inty-pg"
readonly INTY_PG_CONTAINER_LEGACY="inty-dev-postgres"
readonly INTY_PG_VOLUME="inty-dev-postgres-data"
readonly INTY_PG_MAJOR_VERSION="17"
readonly INTY_PG_IMAGE="pgvector/pgvector:pg17"
readonly INTY_PG_PORT="5432"
readonly INTY_PG_VOLUME_LABEL="inty.critical=postgres-data"
readonly INTY_PG_CONTAINER_LABEL="inty.critical=postgres"
readonly INTY_PG_BACKUP_DIR="/opt/inty/backups/postgres"
readonly INTY_PG_BACKUP_RETENTION_DAYS="14"
readonly INTY_PG_DEV_DB="inty-dev"
readonly INTY_PG_PROD_DB="inty"
readonly INTY_PG_USER="postgres"

local_postgres_lib_dir() {
  cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
}

local_postgres_repo_root() {
  cd "$(local_postgres_lib_dir)/../.." && pwd
}

inty_pg_config_path_dev() {
  echo "$(local_postgres_repo_root)/devops/config.yaml.dev"
}

inty_pg_config_path_prod() {
  echo "$(local_postgres_repo_root)/devops/config.yaml.prod"
}

inty_pg_config_path_for_db() {
  local db="$1"
  case "${db}" in
    "${INTY_PG_DEV_DB}")
      inty_pg_config_path_dev
      ;;
    "${INTY_PG_PROD_DB}")
      inty_pg_config_path_prod
      ;;
    *)
      echo "unsupported database '${db}'; use ${INTY_PG_DEV_DB} or ${INTY_PG_PROD_DB}" >&2
      return 1
      ;;
  esac
}

read_database_field_from_config() {
  local cfg="$1"
  local field="$2"
  assert_non_empty "${cfg}" "config path required"
  assert_non_empty "${field}" "field required"
  if [[ ! -f "${cfg}" ]]; then
    echo "config not found: ${cfg}" >&2
    return 1
  fi
  grep -A12 '^database:' "${cfg}" \
    | grep "${field}:" \
    | head -1 \
    | sed -E 's/^[[:space:]]*'"${field}"':[[:space:]]*"?([^"#]*)"?.*/\1/'
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

assert_dev_prod_database_server_credentials_match() {
  local dev_cfg prod_cfg
  local dev_host prod_host dev_port prod_port dev_user prod_user dev_pass prod_pass dev_db prod_db

  dev_cfg="$(inty_pg_config_path_dev)"
  prod_cfg="$(inty_pg_config_path_prod)"

  dev_host="$(read_database_field_from_config "${dev_cfg}" host)"
  prod_host="$(read_database_field_from_config "${prod_cfg}" host)"
  dev_port="$(read_database_field_from_config "${dev_cfg}" port)"
  prod_port="$(read_database_field_from_config "${prod_cfg}" port)"
  dev_user="$(read_database_field_from_config "${dev_cfg}" user)"
  prod_user="$(read_database_field_from_config "${prod_cfg}" user)"
  dev_pass="$(read_database_field_from_config "${dev_cfg}" password)"
  prod_pass="$(read_database_field_from_config "${prod_cfg}" password)"
  dev_db="$(read_database_field_from_config "${dev_cfg}" db)"
  prod_db="$(read_database_field_from_config "${prod_cfg}" db)"

  if [[ "${dev_host}" != "${prod_host}" || "${dev_port}" != "${prod_port}" \
    || "${dev_user}" != "${prod_user}" || "${dev_pass}" != "${prod_pass}" ]]; then
    echo "dev and prod database.host/port/user/password must match (same Postgres instance)." >&2
    echo "dev:  host=${dev_host} port=${dev_port} user=${dev_user}" >&2
    echo "prod: host=${prod_host} port=${prod_port} user=${prod_user}" >&2
    exit 1
  fi
  if [[ "${dev_db}" != "${INTY_PG_DEV_DB}" || "${prod_db}" != "${INTY_PG_PROD_DB}" ]]; then
    echo "expected dev db=${INTY_PG_DEV_DB} and prod db=${INTY_PG_PROD_DB} in config files." >&2
    exit 1
  fi
}

load_pg_password() {
  if [[ -n "${PGPASSWORD:-}" ]]; then
    return
  fi
  local cfg="${1:-$(inty_pg_config_path_dev)}"
  PGPASSWORD="$(read_database_field_from_config "${cfg}" password)"
  export PGPASSWORD
  assert_non_empty "${PGPASSWORD}" "could not read database.password from ${cfg}"
}

migrate_legacy_container_name() {
  if container_exists; then
    return
  fi
  if docker container inspect "${INTY_PG_CONTAINER_LEGACY}" >/dev/null 2>&1; then
    docker rename "${INTY_PG_CONTAINER_LEGACY}" "${INTY_PG_CONTAINER}"
    echo "container ${INTY_PG_CONTAINER_LEGACY}: renamed to ${INTY_PG_CONTAINER}"
  fi
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
  psql -h localhost -p "${INTY_PG_PORT}" -U "${INTY_PG_USER}" -d postgres -At -c 'SHOW server_version;' \
    | cut -d. -f1
}

volume_exists() {
  docker volume inspect "${INTY_PG_VOLUME}" >/dev/null 2>&1
}

database_fingerprint() {
  local db="$1"
  psql -h localhost -p "${INTY_PG_PORT}" -U "${INTY_PG_USER}" -d "${db}" -At -c \
    "SELECT pg_database_size('${db}')::text || ':' || (SELECT count(*)::text FROM pg_class WHERE relkind = 'r');"
}

wait_for_postgres_ready_via_docker() {
  local attempts="${1:-30}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if docker exec "${INTY_PG_CONTAINER}" \
      psql -U "${INTY_PG_USER}" -d postgres -At -c 'SELECT 1' >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Postgres not ready in container ${INTY_PG_CONTAINER} after ${attempts}s" >&2
  return 1
}

wait_for_postgres_ready() {
  local attempts="${1:-30}"
  local i
  load_pg_password
  for ((i = 1; i <= attempts; i++)); do
    if psql -h localhost -p "${INTY_PG_PORT}" -U "${INTY_PG_USER}" -d postgres -At -c 'SELECT 1' >/dev/null 2>&1; then
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
    psql -U "'"${INTY_PG_USER}"'" -d postgres -At -c "SELECT pg_reload_conf()" >/dev/null
  '
}

sql_escape_pg_literal() {
  local value="$1"
  value="${value//\'/\'\'}"
  printf '%s' "${value}"
}

align_postgres_superuser_password() {
  if ! container_running; then
    return
  fi
  load_pg_password
  wait_for_postgres_ready_via_docker
  local escaped_pass
  escaped_pass="$(sql_escape_pg_literal "${PGPASSWORD}")"
  docker exec "${INTY_PG_CONTAINER}" \
    psql -U "${INTY_PG_USER}" -d postgres -v ON_ERROR_STOP=1 -At \
    -c "ALTER USER ${INTY_PG_USER} PASSWORD '${escaped_pass}';" >/dev/null
}

postgres_host_auth_works() {
  load_pg_password
  psql -h localhost -p "${INTY_PG_PORT}" -U "${INTY_PG_USER}" -d postgres -At -c 'SELECT 1' \
    >/dev/null 2>&1
}

finalize_postgres_instance_access() {
  if ! container_running; then
    return
  fi
  wait_for_postgres_ready_via_docker
  ensure_pg_hba_host_access
  if postgres_host_auth_works; then
    return
  fi
  align_postgres_superuser_password
  wait_for_postgres_ready
}

prune_old_backups() {
  local retention_days="$1"
  assert_non_empty "${retention_days}" "retention_days required"
  if [[ ! -d "${INTY_PG_BACKUP_DIR}" ]]; then
    return
  fi
  find "${INTY_PG_BACKUP_DIR}" -name '*.dump' -mtime +"${retention_days}" -delete
}
