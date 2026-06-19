#!/usr/bin/env bash
# Verify IntelliMate local Postgres volume durability wiring on the VM.
# CREATED_BY_AGENT
#
# Checks named-volume mount, restart policy, DB connectivity, and optional restart survival.
#
# Usage (from repo root, on the VM):
#   devops/scripts/verify_local_postgres_durability.sh
#   devops/scripts/verify_local_postgres_durability.sh --restart-test

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

VERIFY_TAG="[inty-local-postgres-verify]"
RESTART_TEST="false"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --restart-test   docker restart container and confirm DB fingerprints unchanged"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --restart-test)
        RESTART_TEST="true"
        shift
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

emit_result() {
  local ok="$1"
  local detail="$2"
  if [[ "${ok}" == "true" ]]; then
    echo "${VERIFY_TAG} RESULT: PASS — ${detail}"
  else
    echo "${VERIFY_TAG} RESULT: FAIL — ${detail}" >&2
    exit 1
  fi
}

check_container_wiring() {
  require_docker
  if ! container_running; then
    emit_result false "container ${INTY_PG_CONTAINER} is not running"
  fi

  local restart_policy mounted
  restart_policy="$(container_restart_policy)"
  mounted="$(container_data_volume_name)"

  if [[ "${restart_policy}" != "unless-stopped" ]]; then
    emit_result false "restart policy is '${restart_policy}', expected unless-stopped"
  fi
  if [[ "${mounted}" != "${INTY_PG_VOLUME}" ]]; then
    emit_result false "data volume is '${mounted:-<missing>}', expected ${INTY_PG_VOLUME}"
  fi
  if ! volume_exists; then
    emit_result false "named volume ${INTY_PG_VOLUME} missing"
  fi

  echo "wiring: restart=${restart_policy} volume=${mounted}"
}

check_server_version() {
  load_pg_password
  if ! command -v psql >/dev/null 2>&1; then
    echo "psql not installed on host; skipping server_version check" >&2
    return
  fi
  local major
  major="$(postgres_server_version_major)"
  echo "server_version major: ${major}"
  if [[ "${major}" != "${INTY_PG_MAJOR_VERSION}" ]]; then
    emit_result false "server_version major is ${major}, expected ${INTY_PG_MAJOR_VERSION}"
  fi
}

check_database_connectivity() {
  load_pg_password
  if ! command -v psql >/dev/null 2>&1; then
    echo "psql not installed on host; skipping DB fingerprint checks" >&2
    return
  fi

  local dev_fp prod_fp
  dev_fp="$(database_fingerprint "${INTY_PG_DEV_DB}")"
  prod_fp="$(database_fingerprint "${INTY_PG_PROD_DB}")"
  echo "fingerprint ${INTY_PG_DEV_DB}: ${dev_fp}"
  echo "fingerprint ${INTY_PG_PROD_DB}: ${prod_fp}"

  if [[ "${RESTART_TEST}" != "true" ]]; then
    return
  fi

  local dev_before="${dev_fp}" prod_before="${prod_fp}"
  docker restart "${INTY_PG_CONTAINER}" >/dev/null
  wait_for_postgres_ready_via_docker
  finalize_postgres_instance_access

  dev_fp="$(database_fingerprint "${INTY_PG_DEV_DB}")"
  prod_fp="$(database_fingerprint "${INTY_PG_PROD_DB}")"
  echo "fingerprint ${INTY_PG_DEV_DB} after restart: ${dev_fp}"
  echo "fingerprint ${INTY_PG_PROD_DB} after restart: ${prod_fp}"

  if [[ "${dev_fp}" != "${dev_before}" || "${prod_fp}" != "${prod_before}" ]]; then
    emit_result false "database fingerprint changed after restart"
  fi
}

parse_args "$@"
assert_dev_prod_database_server_credentials_match
check_container_wiring
check_server_version
check_database_connectivity
emit_result true "container wiring OK; databases reachable"
