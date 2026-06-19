#!/usr/bin/env bash
# Idempotent start or (re)create inty-dev-postgres bound to the canonical named volume.
# CREATED_BY_AGENT
#
# Safe operations only: never removes volumes, never runs docker volume prune.
#
# Usage (from repo root, on the VM):
#   devops/scripts/ensure_inty_dev_postgres_container.sh
#   devops/scripts/ensure_inty_dev_postgres_container.sh --check-only
#   devops/scripts/ensure_inty_dev_postgres_container.sh --recreate-after-upgrade

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=local_postgres_lib.sh
source "${SCRIPT_DIR}/local_postgres_lib.sh"

MODE="ensure"
RECREATE_AFTER_UPGRADE="false"

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \?//'
  echo
  echo "Options:"
  echo "  --check-only              verify container + volume wiring; do not start or create"
  echo "  --recreate-after-upgrade  remove stopped container and create fresh on INTY_PG_IMAGE"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only)
        MODE="check"
        shift
        ;;
      --recreate-after-upgrade)
        RECREATE_AFTER_UPGRADE="true"
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

assert_image_matches_canonical() {
  if ! container_exists; then
    return
  fi
  local image
  image="$(container_image)"
  if [[ "${image}" == "${INTY_PG_IMAGE}" ]]; then
    return
  fi
  if [[ "${RECREATE_AFTER_UPGRADE}" == "true" && "${MODE}" != "check" ]]; then
    if container_running; then
      docker stop "${INTY_PG_CONTAINER}" >/dev/null
    fi
    assert_canonical_mount
    docker rm "${INTY_PG_CONTAINER}" >/dev/null
    echo "container ${INTY_PG_CONTAINER}: removed for recreate (${image} -> ${INTY_PG_IMAGE})"
    return
  fi
  echo "Container ${INTY_PG_CONTAINER} image is '${image}', expected ${INTY_PG_IMAGE}." >&2
  echo "Run devops/scripts/upgrade_inty_dev_postgres_major.sh or ensure with --recreate-after-upgrade after pg_upgrade." >&2
  exit 1
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
  assert_image_matches_canonical

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
    ensure_pg_hba_host_access
    echo "container ${INTY_PG_CONTAINER}: started"
    return
  fi

  if [[ "${MODE}" == "check" ]]; then
    echo "container ${INTY_PG_CONTAINER}: missing" >&2
    exit 1
  fi

  run_postgres_container
  wait_for_postgres_ready
  ensure_pg_hba_host_access
  echo "container ${INTY_PG_CONTAINER}: created and running"
}

parse_args "$@"
require_docker
ensure_volume
ensure_container
