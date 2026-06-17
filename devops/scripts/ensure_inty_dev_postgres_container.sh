#!/usr/bin/env bash
# Idempotent start or (re)create inty-dev-postgres bound to the canonical named volume.
# CREATED_BY_AGENT
#
# Safe operations only: never removes volumes, never runs docker volume prune.
#
# Usage (from repo root, on the VM):
#   devops/scripts/ensure_inty_dev_postgres_container.sh
#   devops/scripts/ensure_inty_dev_postgres_container.sh --check-only

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

MODE="ensure"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --check-only   verify container + volume wiring; do not start or create"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only)
        MODE="check"
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

assert_canonical_mount() {
  local mounted
  mounted="$(container_data_volume_name)"
  if [[ "${mounted}" != "${INTY_PG_VOLUME}" ]]; then
    echo "Container ${INTY_PG_CONTAINER} data mount is '${mounted:-<missing>}', expected named volume ${INTY_PG_VOLUME}." >&2
    echo "Do not docker rm and recreate manually. Fix mount or ask ops before proceeding." >&2
    exit 1
  fi
}

ensure_volume() {
  if volume_exists; then
    echo "volume ${INTY_PG_VOLUME}: exists"
    return
  fi
  if [[ "${MODE}" == "check" ]]; then
    echo "volume ${INTY_PG_VOLUME}: missing" >&2
    exit 1
  fi
  docker volume create \
    --label "${INTY_PG_VOLUME_LABEL}" \
    "${INTY_PG_VOLUME}"
  echo "volume ${INTY_PG_VOLUME}: created with label ${INTY_PG_VOLUME_LABEL}"
}

ensure_restart_policy() {
  if [[ "${MODE}" == "check" ]]; then
    return
  fi
  if ! container_exists; then
    return
  fi
  local restart_policy
  restart_policy="$(container_restart_policy)"
  if [[ "${restart_policy}" == "unless-stopped" ]]; then
    return
  fi
  docker update --restart unless-stopped "${INTY_PG_CONTAINER}" >/dev/null
  echo "container ${INTY_PG_CONTAINER}: restart policy ${restart_policy} -> unless-stopped"
}

run_postgres_container() {
  load_pg_password
  docker run -d \
    --name "${INTY_PG_CONTAINER}" \
    --restart unless-stopped \
    --label "${INTY_PG_CONTAINER_LABEL}" \
    --label "inty.volume=${INTY_PG_VOLUME}" \
    -e POSTGRES_USER=postgres \
    -e "POSTGRES_PASSWORD=${PGPASSWORD}" \
    -e "POSTGRES_DB=${INTY_PG_DEV_DB}" \
    -p "${INTY_PG_PORT}:5432" \
    -v "${INTY_PG_VOLUME}:/var/lib/postgresql/data" \
    "${INTY_PG_IMAGE}"
}

ensure_container() {
  if container_running; then
    assert_canonical_mount
    ensure_restart_policy
    echo "container ${INTY_PG_CONTAINER}: running (volume ${INTY_PG_VOLUME})"
    return
  fi

  if container_exists; then
    assert_canonical_mount
    ensure_restart_policy
    if [[ "${MODE}" == "check" ]]; then
      echo "container ${INTY_PG_CONTAINER}: stopped" >&2
      exit 1
    fi
    docker start "${INTY_PG_CONTAINER}" >/dev/null
    wait_for_postgres_ready
    echo "container ${INTY_PG_CONTAINER}: started"
    return
  fi

  if [[ "${MODE}" == "check" ]]; then
    echo "container ${INTY_PG_CONTAINER}: missing" >&2
    exit 1
  fi

  run_postgres_container
  wait_for_postgres_ready
  echo "container ${INTY_PG_CONTAINER}: created and running"
}

parse_args "$@"
require_docker
ensure_volume
ensure_container
