#!/usr/bin/env bash
# Dump IntelliMate local Docker Postgres logical databases to host backup dir.
# CREATED_BY_AGENT
#
# Writes custom-format pg_dump files under /opt/inty/backups/postgres by default.
# Prunes dumps older than INTY_PG_BACKUP_RETENTION_DAYS after each run.
#
# Usage (from repo root, on the VM):
#   devops/scripts/backup_local_postgres.sh
#   devops/scripts/backup_local_postgres.sh --output-dir /opt/inty/backups/postgres

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

OUTPUT_DIR="${INTY_PG_BACKUP_DIR}"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --output-dir PATH   backup directory (default ${INTY_PG_BACKUP_DIR})"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output-dir)
        assert_non_empty "${2:-}" "--output-dir requires a value"
        OUTPUT_DIR="$2"
        shift 2
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

dump_database() {
  local db="$1"
  local stamp dest tmp_in_container
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  dest="${OUTPUT_DIR}/${db}-${stamp}.dump"
  tmp_in_container="/tmp/${db}-${stamp}.dump"

  docker exec -e PGPASSWORD="${PGPASSWORD}" "${INTY_PG_CONTAINER}" \
    pg_dump -U postgres -d "${db}" --format=custom -f "${tmp_in_container}"
  docker cp "${INTY_PG_CONTAINER}:${tmp_in_container}" "${dest}"
  docker exec "${INTY_PG_CONTAINER}" rm -f "${tmp_in_container}"
  echo "backup ${db}: ${dest} ($(du -h "${dest}" | awk '{print $1}'))"
}

parse_args "$@"
require_docker
if ! container_running; then
  echo "container ${INTY_PG_CONTAINER} is not running" >&2
  exit 1
fi

load_pg_password
mkdir -p "${OUTPUT_DIR}"
dump_database "${INTY_PG_DEV_DB}"
dump_database "${INTY_PG_PROD_DB}"
prune_old_backups "${INTY_PG_BACKUP_RETENTION_DAYS}"
echo "pruned dumps older than ${INTY_PG_BACKUP_RETENTION_DAYS} days under ${INTY_PG_BACKUP_DIR}"
